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
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "event_log@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "spark.stage.task_duration",
        "spark.stage.task_input",
        "spark.stage.spill",
        "spark.stage.gc",
        "spark.stage.task_count",
        "spark.cluster.cores",
        "spark.executor.lost",
        "spark.unresolved",
        "spark.log_analyzed",
    }
)

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
    peak_cores = 0
    peak_executor_count = 0
    app_id = ""

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
            if event == "SparkListenerApplicationStart":
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

            # Outros eventos (SparkListenerJobStart/End, BlockManagerAdded,
            # SparkListenerEnvironmentUpdate, SparkListenerApplicationEnd...)
            # sao ignorados de proposito: nao alimentam nenhum dos fact kinds
            # emitidos por este extrator.

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

    facts.append(
        Fact(
            kind="spark.cluster.cores",
            subject={"type": "job_run", "symbol": app_id},
            measures={"available_cores": peak_cores, "executor_count": peak_executor_count},
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
