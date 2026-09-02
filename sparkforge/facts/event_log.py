"""Extrator de Spark event log (JSON Lines) em Facts.

Um Spark event log e um arquivo JSON Lines: um objeto JSON por linha, cada um
com um campo "Event". AWS Glue escreve esses arquivos em S3 quando
`--enable-spark-ui` e `--spark-event-logs-path` estao configurados (coleta do
S3 para local e responsabilidade de outra camada; este modulo so le arquivo
ja presente no disco).

Como `pyspark_ast.py`, este extrator e puro e deterministico: nunca aplica
limiar, nunca atribui severidade, nunca baixa nada de rede.

Diferenca de `pyspark_ast.py`: aqui o insumo pode ter centenas de MB (event
log de um job Glue real rodando por horas), entao `extract_event_log` nunca
materializa o arquivo inteiro em memoria. Recebe um `Iterable[str]` --
tipicamente um file handle aberto -- e consome uma linha por vez, mantendo em
memoria apenas os acumuladores por stage (listas de duracao/bytes das tasks
daquele stage), nunca o texto bruto das linhas ja processadas.

Campos do Spark event log usam nomes com maiuscula e espaco ("Task Metrics",
"Executor Run Time"): reproduzidos aqui exatamente como o Spark escreve, nao
"normalizados" para snake_case ou minusculo.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from sparkforge.facts.secrets import redact
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "event_log@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "spark.stage.task_duration",
        "spark.stage.task_input",
        "spark.stage.spill",
        "spark.stage.shuffle",
        "spark.stage.gc",
        "spark.stage.task_count",
        "spark.stage.failure",
        "spark.stage.callsite",
        "spark.cluster.cores",
        "spark.executor.lost",
        "spark.executor.memory_usage",
        "spark.job.spill_summary",
        "spark.runtime_version",
        "spark.conf_effective",
        "spark.conf_excluded",
        "spark.unresolved",
        "spark.log_analyzed",
    }
)

# Versao aceitavel: comeca por digito e so contem caracteres de versao.
# Aceita "3.5.4" e "3.5.4-amzn-0" (o que Glue reporta); rejeita "", "unknown",
# "v3.5.4" e qualquer texto livre. O extrator nao normaliza o que aceita -- o
# sufixo de vendor e parte da versao que o run reportou, e apagar isso seria
# transformar observacao em interpretacao.
_VERSION_PATTERN = re.compile(r"^\d[0-9A-Za-z._+-]*$")


def _clean_version(raw: Any) -> str:
    """Devolve a versao utilizavel, ou "" se o campo nao der para interpretar."""
    if not isinstance(raw, str):
        return ""
    value = raw.strip()
    return value if _VERSION_PATTERN.match(value) else ""


# Metricas de memoria de `SparkListenerStageExecutorMetrics` -> nome da measure.
# So as de MEMORIA: o evento carrega dezenas de campos (GC, disco, shuffle) e
# copiar todos transformaria o fact num despejo do evento em vez de uma
# observacao com significado. `ProcessTreePythonRSSMemory` esta aqui porque em
# job PySpark a memoria do interpretador Python vive FORA do heap da JVM: um
# executor pode morrer por limite de container com heap folgado, e sem esta
# measure o diagnostico apontaria para o lugar errado.
_EXECUTOR_MEMORY_METRICS: dict[str, str] = {
    "JVMHeapMemory": "peak_jvm_heap_bytes",
    "JVMOffHeapMemory": "peak_jvm_offheap_bytes",
    "OnHeapExecutionMemory": "peak_onheap_execution_bytes",
    "OffHeapExecutionMemory": "peak_offheap_execution_bytes",
    "OnHeapStorageMemory": "peak_onheap_storage_bytes",
    "ProcessTreePythonRSSMemory": "peak_python_rss_bytes",
}

# Assinaturas de OOM de heap JVM no texto livre de "Removed Reason". Presenca
# de qualquer uma classifica o executor perdido como heap_oom_in_log=True.
# Ausencia com o executor removido mesmo assim aponta para estouro de
# container/overhead (fora do heap: worker Python, buffers Arrow, buffers de
# rede, metaspace) -- a correcao nesse caso e spark.executor.memoryOverhead,
# nao spark.executor.memory. Ver knowledge/spark/memory-and-oom.md secao 2,
# classe container/overhead, e SF-UI-005 em rules/catalog/spark-ui.yaml.
_HEAP_OOM_SIGNATURES = (
    "java.lang.OutOfMemoryError",
    "GC overhead limit",
    "Java heap space",
)


def _as_text(value: Any) -> str:
    """Valor de propriedade como texto, sem interpretar.

    O event log serializa "Spark Properties" com valores string, mas um log
    sintetico ou reserializado pode trazer bool e numero. Normalizar para texto
    mantem o fact comparavel com as outras quatro fontes de configuracao, que
    tambem carregam `attrs.value` como string. `True` vira `"True"` e nao
    `"true"` de proposito: o extrator nao inventa a forma que o Spark usaria --
    quem le sabe que o valor nao veio como string do artefato.
    """
    if isinstance(value, str):
        return value
    return str(value)


def _is_heap_oom(reason: str) -> bool:
    return any(sig in reason for sig in _HEAP_OOM_SIGNATURES)


def _nearest_rank(sorted_values: list[int], pct: int) -> int:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Aritmetica inteira (`-(-a // b)` e o idioma de ceil division para inteiros
    positivos em Python) para o resultado nao depender de arredondamento de
    ponto flutuante -- o mesmo `sorted_values` sempre produz o mesmo indice,
    em qualquer maquina. Para n=1 todo percentil devolve o unico valor: rank
    fica sempre 1, nunca ha divisao por zero em nenhum caminho.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


class _StageAccumulator:
    """Acumula metricas de task de um stage enquanto o log e varrido.

    Tasks com `Task Info.Failed = True` sao excluidas de toda agregacao aqui:
    uma tentativa falha ou reexecutada nao representa trabalho concluido, e
    sua duracao/bytes muitas vezes nao tem relacao com o custo real de
    processar a particao (uma task pode falhar em milissegundos por uma
    excecao antes de ler qualquer dado) -- inclui-la distorceria p50 e max
    sem refletir skew genuino.
    """

    __slots__ = (
        "durations_ms",
        "input_bytes",
        "memory_spill_bytes",
        "disk_spill_bytes",
        "gc_ms",
        "executor_run_ms",
        "task_seen",
        "failed_seen",
        "shuffle_read_records",
        "shuffle_remote_bytes",
        "shuffle_local_bytes",
        "shuffle_fetch_wait_ms",
        "shuffle_write_bytes",
        "shuffle_write_records",
        "shuffle_write_time_ns",
        "shuffle_read_seen",
        "shuffle_write_seen",
    )

    def __init__(self) -> None:
        self.durations_ms: list[int] = []
        self.input_bytes: list[int] = []
        self.memory_spill_bytes = 0
        self.disk_spill_bytes = 0
        self.gc_ms = 0
        self.executor_run_ms = 0
        self.task_seen = 0
        self.failed_seen = 0
        self.shuffle_read_records = 0
        self.shuffle_remote_bytes = 0
        self.shuffle_local_bytes = 0
        self.shuffle_fetch_wait_ms = 0
        self.shuffle_write_bytes = 0
        self.shuffle_write_records = 0
        self.shuffle_write_time_ns = 0
        self.shuffle_read_seen = False
        self.shuffle_write_seen = False

    def add(self, task_info: dict[str, Any], metrics: dict[str, Any]) -> None:
        if task_info.get("Failed"):
            self.failed_seen += 1
            return
        self.task_seen += 1

        launch = task_info.get("Launch Time")
        finish = task_info.get("Finish Time")
        if isinstance(launch, int | float) and isinstance(finish, int | float):
            self.durations_ms.append(max(0, int(finish) - int(launch)))

        input_metrics = metrics.get("Input Metrics") or {}
        bytes_read = input_metrics.get("Bytes Read")
        if isinstance(bytes_read, int | float):
            self.input_bytes.append(int(bytes_read))

        self.memory_spill_bytes += int(metrics.get("Memory Bytes Spilled") or 0)
        self.disk_spill_bytes += int(metrics.get("Disk Bytes Spilled") or 0)
        self.gc_ms += int(metrics.get("JVM GC Time") or 0)
        self.executor_run_ms += int(metrics.get("Executor Run Time") or 0)

        # `Shuffle Read Metrics` e `Shuffle Write Metrics` estao dentro do
        # MESMO `Task Metrics` que este acumulador ja le para input e spill.
        # A presenca de cada bloco e o que distingue "stage sem shuffle" de
        # "shuffle de zero byte": o primeiro nao produz fact nenhum, o segundo
        # produz um fact com zero medido.
        leitura = metrics.get("Shuffle Read Metrics")
        if isinstance(leitura, dict):
            self.shuffle_read_seen = True
            self.shuffle_remote_bytes += int(leitura.get("Remote Bytes Read") or 0)
            self.shuffle_local_bytes += int(leitura.get("Local Bytes Read") or 0)
            self.shuffle_read_records += int(leitura.get("Total Records Read") or 0)
            self.shuffle_fetch_wait_ms += int(leitura.get("Fetch Wait Time") or 0)

        escrita = metrics.get("Shuffle Write Metrics")
        if isinstance(escrita, dict):
            self.shuffle_write_seen = True
            self.shuffle_write_bytes += int(escrita.get("Shuffle Bytes Written") or 0)
            self.shuffle_write_records += int(escrita.get("Shuffle Records Written") or 0)
            self.shuffle_write_time_ns += int(escrita.get("Shuffle Write Time") or 0)


def _line_subject(path: str, line_no: int, snippet: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line_no,
        "col": 0,
        "symbol": "",
        "snippet": snippet,
    }


def _stage_subject(stage_id: int, stage_name: str) -> dict[str, Any]:
    return {"type": "stage", "symbol": stage_name, "stage_id": stage_id}


# O Spark escreve o nome do stage no formato de CALLSITE:
# `<metodo> at <arquivo>:<linha>` -- `collect at job.py:42`. E a mesma
# string que aparece na Spark UI, e ela e a UNICA ancora que liga um stage
# de execucao a uma linha de codigo-fonte.
#
# O grupo do arquivo aceita qualquer caminho sem espaco; a decisao de so
# aceitar `.py` e tomada DEPOIS, para que o motivo da recusa possa ser
# `arquivo_nao_python` em vez de "nao casou".
_CALLSITE = re.compile(r"^(?P<metodo>.+?) at (?P<arquivo>\S+):(?P<linha>[^:\s]+)$")


def _callsite_do_stage(stage_id: int, stage_name: str, provenance: dict[str, Any]) -> Fact:
    """O callsite que o nome do stage carrega, ou a recusa NOMEADA.

    ## Por que derivado, e nao regex no `when` da regra

    `engine._where_matches` nao casa padrao. Por a decisao na regra faria cada
    regra nova reimplementar o parse, que e a divida que a area `SF-GRAPH` ja
    pagou em 2026-08-31. O extrator decide UMA vez e emite o kind ja decidido,
    no molde de `tf.graphframes.jar` e `ctm.event_logic`.

    ## As tres recusas, e por que `arquivo_nao_python` nao e lacuna

    - `sem_forma_de_callsite` -- o nome nao tem ` at <arquivo>:<linha>`.
    - `arquivo_nao_python` -- `count at GraphFrame.scala:112`. O stage nasceu
      DENTRO da biblioteca, e nao ha linha no `.py` do operador para apontar.
      Inventar uma seria pior que recusar: mandaria quem le olhar para um
      arquivo que nao causou nada.
    - `linha_nao_numerica` -- ` at job.py:<unknown>`, que o Spark escreve
      quando nao consegue resolver a linha.

    Nenhuma das tres e defeito. Todas saem como fato com `resolved: False` e
    `attrs.reason`, nunca como ausencia -- ausencia se le como 'nao ha
    callsite', e o que ha e 'nao consegui nomear este'.
    """
    subject = _stage_subject(stage_id, stage_name)
    casou = _CALLSITE.match(stage_name.strip())

    if casou is None:
        return Fact(
            kind="spark.stage.callsite",
            subject=subject,
            measures={},
            attrs={"resolved": False, "reason": "sem_forma_de_callsite"},
            provenance=provenance,
        )

    arquivo = casou.group("arquivo")
    linha_txt = casou.group("linha")
    if not arquivo.endswith(".py"):
        return Fact(
            kind="spark.stage.callsite",
            subject=subject,
            measures={},
            attrs={
                "resolved": False,
                "reason": "arquivo_nao_python",
                "file": arquivo,
            },
            provenance=provenance,
        )

    if not linha_txt.isdigit():
        return Fact(
            kind="spark.stage.callsite",
            subject=subject,
            measures={},
            attrs={
                "resolved": False,
                "reason": "linha_nao_numerica",
                "file": arquivo,
            },
            provenance=provenance,
        )

    return Fact(
        kind="spark.stage.callsite",
        subject=subject,
        measures={"line": int(linha_txt)},
        attrs={
            "resolved": True,
            "method": casou.group("metodo"),
            # `file` sai como BASENAME e tambem inteiro. O basename e o que
            # casa com `fact.subject.file` do lado estatico, que e relativo ao
            # artefato; o caminho inteiro fica porque descarta-lo perderia a
            # unica pista de pacote que o event log da.
            "file": arquivo.replace("\\", "/").rsplit("/", 1)[-1],
            "path": arquivo,
        },
        provenance=provenance,
    )


def _stage_facts(
    stage_id: int,
    stage_name: str,
    acc: _StageAccumulator,
    declared_task_count: int | None,
    available_cores: int | None,
    provenance: dict[str, Any],
) -> list[Fact]:
    facts: list[Fact] = []
    subject = _stage_subject(stage_id, stage_name)

    # SEMPRE, inclusive quando o nome nao tem callsite: a recusa nomeada e o
    # que distingue 'este stage nao diz de onde veio' de 'ninguem perguntou'.
    facts.append(_callsite_do_stage(stage_id, stage_name, provenance))

    if acc.durations_ms:
        values = sorted(acc.durations_ms)
        n = len(values)
        facts.append(
            Fact(
                kind="spark.stage.task_duration",
                subject=subject,
                measures={
                    "min_ms": values[0],
                    "p50_ms": _nearest_rank(values, 50),
                    "p95_ms": _nearest_rank(values, 95),
                    "max_ms": values[-1],
                    "mean_ms": sum(values) / n,
                    "task_count": n,
                },
                provenance=provenance,
            )
        )

    if acc.input_bytes:
        values = sorted(acc.input_bytes)
        facts.append(
            Fact(
                kind="spark.stage.task_input",
                subject=subject,
                measures={
                    "min_bytes": values[0],
                    "p50_bytes": _nearest_rank(values, 50),
                    "p95_bytes": _nearest_rank(values, 95),
                    "max_bytes": values[-1],
                    "total_bytes": sum(values),
                },
                provenance=provenance,
            )
        )

    if acc.task_seen:
        facts.append(
            Fact(
                kind="spark.stage.spill",
                subject=subject,
                measures={
                    "memory_spill_bytes": acc.memory_spill_bytes,
                    "disk_spill_bytes": acc.disk_spill_bytes,
                    "input_bytes": sum(acc.input_bytes),
                },
                provenance=provenance,
            )
        )
        facts.append(
            Fact(
                kind="spark.stage.gc",
                subject=subject,
                measures={
                    "gc_ms": acc.gc_ms,
                    "executor_run_ms": acc.executor_run_ms,
                },
                provenance=provenance,
            )
        )

    if acc.shuffle_read_seen or acc.shuffle_write_seen:
        medidas: dict[str, Any] = {}
        if acc.shuffle_read_seen:
            medidas.update(
                {
                    "read_bytes": acc.shuffle_remote_bytes + acc.shuffle_local_bytes,
                    "remote_read_bytes": acc.shuffle_remote_bytes,
                    "local_read_bytes": acc.shuffle_local_bytes,
                    "read_records": acc.shuffle_read_records,
                    "fetch_wait_ms": acc.shuffle_fetch_wait_ms,
                }
            )
        if acc.shuffle_write_seen:
            medidas.update(
                {
                    "write_bytes": acc.shuffle_write_bytes,
                    "write_records": acc.shuffle_write_records,
                    # `Shuffle Write Time` vem em NANOSSEGUNDOS no event log,
                    # ao contrario de `Fetch Wait Time`, que vem em ms.
                    # Converter aqui e o que impede um consumidor de comparar os
                    # dois como se fossem a mesma unidade.
                    "write_time_ms": acc.shuffle_write_time_ns // 1_000_000,
                }
            )
        facts.append(
            Fact(
                kind="spark.stage.shuffle",
                subject=subject,
                measures=medidas,
                provenance=provenance,
            )
        )

    task_count = declared_task_count
    if task_count is None:
        task_count = acc.task_seen + acc.failed_seen
    task_count_measures: dict[str, Any] = {"task_count": task_count}
    if available_cores is not None:
        task_count_measures["available_cores"] = available_cores
    facts.append(
        Fact(
            kind="spark.stage.task_count",
            subject=subject,
            measures=task_count_measures,
            provenance=provenance,
        )
    )

    return facts


def extract_event_log(lines: Iterable[str], path: str) -> list[Fact]:
    """Extrai Facts de um Spark event log dado como `Iterable[str]`.

    Uma linha por vez: `lines` e tipicamente um file handle aberto, e cada
    linha e descartada logo apos ser processada. O arquivo inteiro nunca vira
    uma unica string na memoria -- event logs de jobs Glue reais chegam a
    centenas de MB.

    Uma linha invalida nunca aborta o parse: vira um Fact `spark.unresolved`
    e a leitura continua, pelo mesmo motivo que `pyspark_ast.extract_tree` nao
    deixa um arquivo ruim apagar a analise de todos os outros. `attrs.reason`
    e um de:
      - "malformed_json": a linha nao e JSON valido.
      - "missing_event_field": JSON valido, mas sem chave "Event" no nivel
        raiz, ou evento reconhecido cuja estrutura interna esperada
        (ex.: "Task Info", "Stage Info", "Executor ID") esta ausente ou tem
        tipo incompativel.
      - "read_error": o iteravel de linhas quebrou no meio da leitura (ex.:
        erro de decode do file handle subjacente).
      - "conflicting_runtime_version": um segundo "SparkListenerLogStart"
        declarou uma versao de Spark diferente da primeira. Ver o tratamento
        de "SparkListenerLogStart" abaixo para por que isso nao vira escolha
        silenciosa.
    """
    provenance = {"artifact": path, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    stage_acc: dict[int, _StageAccumulator] = {}
    stage_names: dict[int, str] = {}
    declared_task_counts: dict[int, int] = {}
    completed_stage_ids: set[int] = set()

    # Cores disponiveis e medido como o pico de soma de "Total Cores" dos
    # executores simultaneamente vivos, observado ao longo do log inteiro --
    # nao o valor no fim do log, que pode ja refletir executores removidos.
    # E a leitura mais defensavel de "capacidade do cluster" para comparar
    # contra contagem de tasks (SF-UI-006): a pergunta e "quantos cores o job
    # chegou a ter disponiveis", nao "quantos sobraram no ultimo instante".
    active_executor_cores: dict[str, int] = {}
    executor_peak_memory: dict[str, dict[str, int]] = {}
    peak_cores = 0
    peak_executor_count = 0
    app_id = ""
    spark_version = ""

    # Configuracao efetiva, de "SparkListenerEnvironmentUpdate".
    #
    # `spark_properties` guarda o que a PRIMEIRA ocorrencia declarou. O evento e
    # emitido uma vez por aplicacao, mas log concatenado de dois runs traz dois
    # -- o mesmo caso que "SparkListenerLogStart" ja trata para a versao. A
    # regra aqui e a mesma: o primeiro vence, e a divergencia vira ponto cego
    # ancorado na linha que discordou, nunca escolha silenciosa.
    #
    # `excluded_sections` conta o que este extrator NAO desmonta. Ver o bloco
    # de "SparkListenerEnvironmentUpdate" no laco para o recorte e a razao.
    spark_properties: dict[str, str] = {}
    excluded_sections: dict[str, int] = {}
    seen_environment_update = False

    line_count = 0
    event_count = 0
    unresolved_count = 0

    line_iter: Iterator[str] = iter(lines)
    while True:
        try:
            raw_line = next(line_iter)
        except StopIteration:
            break
        except Exception as exc:  # iterador quebrou no meio (ex.: decode do file handle)
            facts.append(
                Fact(
                    kind="spark.unresolved",
                    subject=_line_subject(path, line_count + 1, ""),
                    attrs={"reason": "read_error", "detail": str(exc)},
                    provenance=provenance,
                )
            )
            unresolved_count += 1
            break

        line_count += 1
        stripped = raw_line.strip()
        if not stripped:
            continue

        try:
            event_obj = json.loads(stripped)
        except json.JSONDecodeError:
            facts.append(
                Fact(
                    kind="spark.unresolved",
                    subject=_line_subject(path, line_count, stripped[:200]),
                    attrs={"reason": "malformed_json"},
                    provenance=provenance,
                )
            )
            unresolved_count += 1
            continue

        if not isinstance(event_obj, dict) or "Event" not in event_obj:
            facts.append(
                Fact(
                    kind="spark.unresolved",
                    subject=_line_subject(path, line_count, stripped[:200]),
                    attrs={"reason": "missing_event_field"},
                    provenance=provenance,
                )
            )
            unresolved_count += 1
            continue

        event_count += 1
        event = event_obj.get("Event")

        try:
            if event == "SparkListenerLogStart":
                # Primeira linha de todo event log moderno, escrita pelo proprio
                # EventLoggingListener antes de qualquer evento do job. E a
                # leitura mais confiavel da versao de Spark porque nao e uma
                # propriedade que o job possa definir: "spark.version" dentro de
                # "Spark Properties" (SparkListenerEnvironmentUpdate) e apenas o
                # eco de uma conf, e qualquer `--conf spark.version=...` apareceria
                # ali com valor arbitrario. Ver `detect_runtime`: a fonte
                # "event_log" tem a maior precedencia justamente por ser o que o
                # run reportou, nao o que alguem declarou.
                raw_version = event_obj.get("Spark Version")
                version = _clean_version(raw_version)
                if not version:
                    facts.append(
                        Fact(
                            kind="spark.unresolved",
                            subject=_line_subject(path, line_count, stripped[:200]),
                            attrs={
                                "reason": "missing_event_field",
                                "detail": f"Spark Version ausente ou invalido: {raw_version!r}",
                            },
                            provenance=provenance,
                        )
                    )
                    unresolved_count += 1
                elif not spark_version:
                    spark_version = version
                elif version != spark_version:
                    # Duas versoes num unico log significam partes de runs
                    # diferentes concatenadas. Escolher em silencio deixaria a
                    # versao errada gatilhar as regras versionadas de `judge`;
                    # abortar jogaria fora o log inteiro. O primeiro cabecalho
                    # vence (e o que o arquivo abriu) e a divergencia vira ponto
                    # cego ancorado na linha que discordou. Repeticao com o MESMO
                    # valor nao e anomalia: event log rolante
                    # (`spark.eventLog.rolling.enabled`) repete o cabecalho em
                    # cada parte.
                    facts.append(
                        Fact(
                            kind="spark.unresolved",
                            subject=_line_subject(path, line_count, stripped[:200]),
                            attrs={
                                "reason": "conflicting_runtime_version",
                                "detail": (
                                    f"Spark Version divergente: {spark_version} "
                                    f"(primeiro) != {version}"
                                ),
                            },
                            provenance=provenance,
                        )
                    )
                    unresolved_count += 1

            elif event == "SparkListenerApplicationStart":
                app_id = str(event_obj.get("App ID") or app_id)

            elif event == "SparkListenerExecutorAdded":
                executor_id = str(event_obj["Executor ID"])
                cores = int(event_obj.get("Executor Info", {}).get("Total Cores") or 0)
                active_executor_cores[executor_id] = cores
                peak_cores = max(peak_cores, sum(active_executor_cores.values()))
                peak_executor_count = max(peak_executor_count, len(active_executor_cores))

            elif event == "SparkListenerExecutorRemoved":
                executor_id = str(event_obj["Executor ID"])
                reason = str(event_obj.get("Removed Reason") or "")
                active_executor_cores.pop(executor_id, None)
                facts.append(
                    Fact(
                        kind="spark.executor.lost",
                        subject={"type": "job_run", "symbol": executor_id},
                        attrs={"reason": reason, "heap_oom_in_log": _is_heap_oom(reason)},
                        provenance=provenance,
                    )
                )

            elif event == "SparkListenerStageExecutorMetrics":
                # Pico de memoria por executor, por stage. E a unica fonte no
                # event log que diz quanto de heap o executor REALMENTE usou --
                # `spark.executor.lost` diz que ele morreu, nao o quao perto do
                # limite os que sobreviveram chegaram. SF-GLUE-005 depende
                # disto para separar "precisa de worker maior" de "trocaram o
                # worker sem evidencia nenhuma".
                executor_id = str(event_obj["Executor ID"])
                metrics = event_obj.get("Executor Metrics") or {}
                peaks = executor_peak_memory.setdefault(executor_id, {})
                for source, name in _EXECUTOR_MEMORY_METRICS.items():
                    value = metrics.get(source)
                    if isinstance(value, int | float) and not isinstance(value, bool):
                        peaks[name] = max(peaks.get(name, 0), int(value))

            elif event == "SparkListenerTaskEnd":
                stage_id = int(event_obj["Stage ID"])
                task_info = event_obj.get("Task Info") or {}
                metrics = event_obj.get("Task Metrics") or {}
                acc = stage_acc.setdefault(stage_id, _StageAccumulator())
                acc.add(task_info, metrics)

            elif event == "SparkListenerStageCompleted":
                stage_info = event_obj.get("Stage Info") or {}
                stage_id = int(stage_info["Stage ID"])
                stage_names[stage_id] = str(stage_info.get("Stage Name") or "")
                num_tasks = stage_info.get("Number of Tasks")
                if isinstance(num_tasks, int | float):
                    declared_task_counts[stage_id] = int(num_tasks)
                completed_stage_ids.add(stage_id)

                # A razao da falha, quando houve falha. E a UNICA fonte no
                # event log que separa timeout de broadcast de timeout de rede:
                # as duas frases -- "Could not execute broadcast in N secs" e
                # "Futures timed out after [N seconds]" -- sao escritas aqui, e
                # em lugar nenhum mais. `spark.executor.lost` cobre heartbeat,
                # e o estado do `glue.job_run` cobre o relogio de parede.
                #
                # Chave ausente e chave vazia sao o mesmo caso para o produtor
                # (nao houve falha) e o fact nao e emitido em nenhum dos dois:
                # fact de falha com razao vazia seria uma falha que ninguem
                # relatou.
                #
                # Redigido pelo mesmo caminho de `spark.conf_effective`: razao
                # de falha carrega URL de JDBC com senha dentro com a mesma
                # facilidade que configuracao carrega, e `facts.json` e
                # commitado como barramento de handoff.
                failure_reason = str(stage_info.get("Failure Reason") or "")
                if failure_reason:
                    reason_value, reason_redacted = redact("Failure Reason", failure_reason)
                    failure_attrs = {"reason": reason_value}
                    if reason_redacted:
                        failure_attrs["redacted"] = True
                    facts.append(
                        Fact(
                            kind="spark.stage.failure",
                            subject=_stage_subject(
                                stage_id, str(stage_info.get("Stage Name") or "")
                            ),
                            attrs=failure_attrs,
                            provenance=provenance,
                        )
                    )

            elif event == "SparkListenerEnvironmentUpdate":
                # A configuracao EFETIVA do run: o que o motor de fato aplicou,
                # depois de resolver defaults, `--conf`, config de cluster e
                # chamadas no codigo. E a unica fonte no projeto que responde
                # "o que valeu", contra as outras quatro que dizem "o que foi
                # pedido" (pyspark.conf_set, tf.spark_conf, emr.configuration,
                # emrs.configuration).
                #
                # O QUE ESTE FACT NAO E, e vale repetir porque a linha do
                # "SparkListenerLogStart" acima ja carrega o argumento para um
                # caso particular: isto e o que o RUN REPORTOU como suas
                # propriedades, nao uma medicao independente do motor. Um
                # `--conf spark.qualquer.coisa=x` aparece aqui com valor
                # arbitrario, e foi exatamente por isso que a versao de Spark
                # NAO e lida daqui. Para configuracao de tuning a distincao e
                # menos grave -- o valor reportado E o que o driver resolveu --
                # mas ela nao some, e a explicacao da regra carrega isso.
                #
                # RECORTE: so "Spark Properties". O evento tambem traz "JVM
                # Information", "System Properties", "Classpath Entries",
                # "Hadoop Properties" e "Metrics Properties". Desmontar tudo
                # multiplicaria o numero de facts por dez sem responder pergunta
                # de tuning de Spark, e classpath num `facts.json` commitado e
                # superficie de informacao sem contrapartida. O que ficou de
                # fora e CONTADO em `spark.conf_excluded`, no mesmo padrao de
                # `opaque_caller_function_count`: exclusao contada, nunca
                # silenciosa -- quem le sabe que existia mais e quanto.
                raw_props = event_obj.get("Spark Properties")
                if not isinstance(raw_props, dict):
                    facts.append(
                        Fact(
                            kind="spark.unresolved",
                            subject=_line_subject(path, line_count, stripped[:200]),
                            attrs={
                                "reason": "missing_event_field",
                                "detail": (
                                    "SparkListenerEnvironmentUpdate sem 'Spark Properties' "
                                    f"utilizavel: {type(raw_props).__name__}"
                                ),
                            },
                            provenance=provenance,
                        )
                    )
                    unresolved_count += 1
                else:
                    novo = {str(k): _as_text(v) for k, v in raw_props.items()}
                    if not seen_environment_update:
                        seen_environment_update = True
                        spark_properties = novo
                        for secao, conteudo in sorted(event_obj.items()):
                            if secao in ("Event", "Spark Properties"):
                                continue
                            if isinstance(conteudo, dict):
                                excluded_sections[secao] = len(conteudo)
                            elif isinstance(conteudo, list):
                                excluded_sections[secao] = len(conteudo)
                    elif novo != spark_properties:
                        # Dois runs concatenados. Escolher em silencio faria a
                        # configuracao de um run julgar o outro.
                        facts.append(
                            Fact(
                                kind="spark.unresolved",
                                subject=_line_subject(path, line_count, stripped[:200]),
                                attrs={
                                    "reason": "conflicting_environment_update",
                                    "detail": (
                                        "segundo SparkListenerEnvironmentUpdate com "
                                        "'Spark Properties' diferente; o primeiro prevalece"
                                    ),
                                },
                                provenance=provenance,
                            )
                        )
                        unresolved_count += 1

            # Outros eventos (SparkListenerJobStart/End, BlockManagerAdded,
            # SparkListenerApplicationEnd...) sao ignorados de proposito: nao
            # alimentam nenhum dos fact kinds emitidos por este extrator.

        except (KeyError, TypeError, ValueError) as exc:
            facts.append(
                Fact(
                    kind="spark.unresolved",
                    subject=_line_subject(path, line_count, stripped[:200]),
                    attrs={"reason": "missing_event_field", "detail": str(exc)},
                    provenance=provenance,
                )
            )
            unresolved_count += 1

    # Stages que receberam SparkListenerStageCompleted usam o nome e a
    # contagem declarada em "Stage Info". Um stage presente so via TaskEnd
    # (log truncado -- job morto no meio da execucao) ainda produz Facts,
    # com nome vazio e task_count de melhor esforco: um blind spot parcial
    # e mais honesto que descartar o stage inteiro.
    for stage_id in sorted(stage_acc.keys() | completed_stage_ids):
        acc = stage_acc.get(stage_id, _StageAccumulator())
        stage_name = stage_names.get(stage_id, "")
        declared = declared_task_counts.get(stage_id)
        facts.extend(
            _stage_facts(stage_id, stage_name, acc, declared, peak_cores or None, provenance)
        )

    # Visao de JOB do spill, alem da de stage.
    #
    # `spark.stage.spill` e emitido para todo stage analisado, inclusive com
    # zero byte -- e informacao legitima ("este stage nao derramou"). O efeito
    # colateral e que `absent: spark.stage.spill` nunca vale num log de
    # verdade, entao nao ha como uma regra perguntar "o job inteiro derramou
    # alguma coisa?" com o vocabulario por stage: `fact:` casa se ALGUM fact
    # satisfaz a condicao, e um job com um stage limpo e outro derramando
    # satisfaria "existe stage sem spill". SF-GLUE-005 precisa exatamente da
    # pergunta oposta, e por isso ela vive aqui, num unico fact por job.
    total_memory_spill = 0
    total_disk_spill = 0
    stages_with_spill = 0
    for fact in facts:
        if fact.kind != "spark.stage.spill":
            continue
        memory_spill = int(fact.measures.get("memory_spill_bytes") or 0)
        disk_spill = int(fact.measures.get("disk_spill_bytes") or 0)
        total_memory_spill += memory_spill
        total_disk_spill += disk_spill
        if memory_spill or disk_spill:
            stages_with_spill += 1

    facts.append(
        Fact(
            kind="spark.job.spill_summary",
            subject={"type": "job_run", "symbol": app_id},
            measures={
                "stages_with_spill": stages_with_spill,
                "total_memory_spill_bytes": total_memory_spill,
                "total_disk_spill_bytes": total_disk_spill,
            },
            provenance=provenance,
        )
    )

    # Um fact por executor, com o pico de cada metrica ao longo de todos os
    # stages. Agregar tudo num unico fact do job esconderia o caso que mais
    # importa: um executor no limite entre dez folgados vira media confortavel,
    # e e ele que vai morrer.
    for executor_id, peaks in sorted(executor_peak_memory.items()):
        if not peaks:
            continue
        facts.append(
            Fact(
                kind="spark.executor.memory_usage",
                subject={"type": "job_run", "symbol": executor_id},
                measures=dict(sorted(peaks.items())),
                attrs={"executor_id": executor_id},
                provenance=provenance,
            )
        )

    # Versao de Spark observada no run. Emitido so quando o log de fato
    # declarou uma: event log sem SparkListenerLogStart (log truncado pelo
    # inicio, recorte, log sintetico) e event log valido, e ausencia de versao
    # e silencio, nao ponto cego -- um fact com versao vazia seria pior que
    # nenhum, porque `detect_runtime` o trataria como observacao da fonte de
    # maior precedencia.
    if spark_version:
        facts.append(
            Fact(
                kind="spark.runtime_version",
                subject={"type": "job_run", "symbol": app_id},
                attrs={
                    "component": "spark",
                    "version": spark_version,
                    "source_event": "SparkListenerLogStart",
                },
                provenance=provenance,
            )
        )

    facts.append(
        Fact(
            kind="spark.cluster.cores",
            subject={"type": "job_run", "symbol": app_id},
            measures={"available_cores": peak_cores, "executor_count": peak_executor_count},
            provenance=provenance,
        )
    )

    # Um fact por propriedade de "Spark Properties".
    #
    # `subject.symbol` e a CHAVE, nao o app id. `Fact.id` e hash de (kind,
    # subject, measures), e estes facts nao tem measures: com o app id no
    # symbol, duzias de propriedades colidiriam num id so e o `facts.json`
    # perderia todas menos uma. E o mesmo defeito que `_SymbolPool` resolve em
    # `emr_cluster.py` para duas propriedades da mesma classificacao. O app id
    # continua legivel em `attrs.app_id`.
    #
    # Valor com forma de credencial e redigido antes de entrar no fact. Nao e
    # zelo generico: `facts.json` e commitado como barramento de handoff (§8.1
    # da spec da Fase 0), e configuracao de Spark carrega
    # `spark.hadoop.fs.s3a.secret.key` e senha dentro de URL de JDBC.
    for key in sorted(spark_properties):
        value, redacted = redact(key, spark_properties[key])
        attrs = {
            "key": key,
            "value": value,
            "app_id": app_id,
            "source_event": "SparkListenerEnvironmentUpdate",
        }
        if redacted:
            attrs["redacted"] = True
        facts.append(
            Fact(
                kind="spark.conf_effective",
                subject={"type": "job_run", "symbol": key},
                attrs=attrs,
                provenance=provenance,
            )
        )

    # O que o evento trazia e este extrator nao desmontou, contado por secao.
    #
    # Sem isto, "spark.conf_effective ausente para a chave X" seria ambiguo
    # entre "o run nao tinha X" e "X vive numa secao que ninguem le" -- o falso
    # negativo silencioso que o item 4 do README do catalogo persegue. So e
    # emitido quando houve `SparkListenerEnvironmentUpdate`: em log sem o
    # evento, quem responde e a ausencia de `spark.conf_effective`.
    if seen_environment_update:
        facts.append(
            Fact(
                kind="spark.conf_excluded",
                subject={"type": "job_run", "symbol": app_id},
                measures={
                    "extracted_property_count": len(spark_properties),
                    "excluded_section_count": len(excluded_sections),
                    "excluded_entry_count": sum(excluded_sections.values()),
                },
                attrs={
                    "extracted_section": "Spark Properties",
                    "excluded_sections": dict(sorted(excluded_sections.items())),
                },
                provenance=provenance,
            )
        )

    # Sentinela: prova de que a extracao rodou sobre este log. Sem isso, uma
    # condicao `absent: X` do catalogo seria vazamente verdadeira quando o
    # extrator nunca rodou, nao so quando genuinamente nao encontrou X. Mirror
    # de `pyspark.module_analyzed` em pyspark_ast.py.
    facts.append(
        Fact(
            kind="spark.log_analyzed",
            subject={
                "type": "source_location",
                "file": path,
                "line": 0,
                "col": 0,
                "symbol": "",
                "snippet": "",
            },
            measures={
                "line_count": line_count,
                "event_count": event_count,
                "unresolved_count": unresolved_count,
            },
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_event_log_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo de event log, ancorando o path relativo a `repo_root`.

    Abre com `utf-8-sig` (mesma convencao de `pyspark_ast.extract_path`, para
    tolerar BOM) e repassa o file handle direto para `extract_event_log`, que
    consome uma linha por vez -- o arquivo nunca e lido inteiro para a
    memoria de uma vez.

    Falha ao abrir o arquivo (permissao, arquivo inexistente, encoding
    irrecuperavel na abertura) vira um unico Fact `spark.unresolved` com
    reason "read_error", nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return extract_event_log(handle, anchor)
    except OSError as exc:
        return [
            Fact(
                kind="spark.unresolved",
                subject=_line_subject(anchor, 0, ""),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={
                    "artifact": anchor,
                    "artifact_sha256": "",
                    "extractor": EXTRACTOR_ID,
                },
            )
        ]
