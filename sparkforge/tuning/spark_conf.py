"""O valor que a medida sustenta, e a procedencia de cada propriedade.

O documento de origem poe em letras grandes: `spark.sql.shuffle.partitions`
passa a ser DERIVED, e nao HARDCODED. Desde 2026-09-14 sao oito derivacoes --
shuffle, overhead, heap, split de leitura, threshold de broadcast, speculation,
network timeout e broadcast timeout --, cada uma com a formula e a base medida,
e cada uma recusada por NOME quando a medida falta, com o que a destravaria.
Listar a recusa e a diferenca entre "nao sei" e "nao perguntei". Toda proposta
e PISO medido (ou a estimativa que o proprio Spark compara, no broadcast, ou a
relacao entre os defaults, no network timeout) e sai `REVIEW`: nada aqui e
ganho estimado.

NAO E EXTRATOR, e nada aqui vira Fact. Custo (E) e categoria de timeout (F) sao
fact porque sao aritmetica sobre medida, sem escolha; um valor PROPOSTO de
configuracao e escolha, porque existe um alvo de tamanho de particao e alvo e
decisao. Por isso este modulo segue o precedente de `capacity` e `finops`:
composicao com verbo proprio.

O QUE ESTE MODULO RECUSA:
  - Aplicar. Nenhum caminho do codigo escreve configuracao em lugar nenhum.
  - Derivar sem base medida. Trocar um numero magico por outro com aparencia de
    calculo e exatamente o que a seccao 10 do documento recusa.
  - Ordenar proposta por ganho estimado. Mesmo contrafactual que o subprojeto E
    recusa por escrito.
"""
from __future__ import annotations

import functools
import math
import re
import statistics
from collections.abc import Sequence
from typing import Any

import yaml

from sparkforge.facts.timeout_diagnosis import _segundos
from sparkforge.findings.models import Fact
from sparkforge.rules.loader import CatalogError, catalog_dir, safe_catalog_file

_MIB = 1024 * 1024

_CHAVE_SHUFFLE = "spark.sql.shuffle.partitions"
_CHAVE_ALVO = "spark.sql.adaptive.advisoryPartitionSizeInBytes"

# Default documentado do Spark para o tamanho que o AQE persegue ao coalescer
# particao pos-shuffle. Nao e gosto: e o alvo que o proprio motor usa, e ele
# viaja dentro da resposta como `target_partition_bytes`.
_ALVO_DEFAULT_BYTES = 64 * _MIB

# Default documentado da propria propriedade derivada. Serve para uma coisa so:
# reconhecer configuracao escrita a mao com o valor do default, que e o sintoma
# que a seccao 36 persegue -- alguem escreveu, ninguem mais entende, e nao muda
# nada.
_DEFAULT_SHUFFLE_PARTITIONS = "200"

# AQE e default a partir do Spark 3.2. `knowledge/glue/runtime-matrix.md`
# registra a consequencia: default em Glue 4.0 e 5.x, e NAO em Glue 3.0, que
# roda Spark 3.1.1. Recomendar "confie no AQE" para Glue 3.0 e erro de versao.
_AQE_DEFAULT_DESDE = (3, 2)

_SPARK_POR_GLUE = {
    "6.0": "4.1.1",
    "5.1": "3.5.6",
    "5.0": "3.5.4",
    "4.0": "3.3.0",
    "3.0": "3.1.1",
}

# Niveis do 34 do documento. Paralelismo de shuffle e REVIEW pela lista dele:
# muda a forma do trabalho, nao o resultado, e nunca entra em producao sem
# alguem olhar.
_CHAVE_OVERHEAD = "spark.executor.memoryOverhead"
_CHAVE_MEMORIA = "spark.executor.memory"
_CHAVE_PYSPARK_MEMORIA = "spark.executor.pyspark.memory"
_CHAVE_SPLIT = "spark.sql.files.maxPartitionBytes"
_CHAVE_BROADCAST = "spark.sql.autoBroadcastJoinThreshold"
_CHAVE_SPECULATION = "spark.speculation"
_CHAVE_NETWORK = "spark.network.timeout"
_CHAVE_BROADCAST_TIMEOUT = "spark.sql.broadcastTimeout"

_SEGURANCA_POR_CHAVE = {
    _CHAVE_SHUFFLE: "REVIEW",
    _CHAVE_OVERHEAD: "REVIEW",
    _CHAVE_MEMORIA: "REVIEW",
    _CHAVE_SPLIT: "REVIEW",
    _CHAVE_BROADCAST: "REVIEW",
    _CHAVE_SPECULATION: "REVIEW",
    _CHAVE_NETWORK: "REVIEW",
    _CHAVE_BROADCAST_TIMEOUT: "REVIEW",
}

# Razao entre os defaults documentados: `spark.network.timeout` 120s
# (`config/Network.scala`) sobre `spark.executor.heartbeatInterval` 10s
# (`config/package.scala`). E a folga que o proprio Spark escolheu para o
# heartbeat caber varias vezes na espera do driver.
_RAZAO_REDE_HEARTBEAT = 12
# `SQLConf.BROADCAST_TIMEOUT`: 300 segundos de default.
_BROADCAST_TIMEOUT_DEFAULT_S = 300.0
# Medida do `spark.timeout.diagnosis` -> chave de limiar da `SF-TIMEOUT-001`.
_SINTOMAS = (
    ("skew_p95_over_p50", "skew_ratio"),
    ("spill_over_input", "spill_ratio"),
    ("gc_ratio", "gc_ratio"),
    ("executor_lost_count", "executor_lost_min"),
)

# Documentacao de configuracao do Spark: overhead default =
# `spark.executor.memory * spark.executor.memoryOverheadFactor` (0.10), com
# minimo `spark.executor.minMemoryOverhead` (384m). So serve para mostrar o
# efetivo ao lado do piso medido.
_MIN_OVERHEAD_MIB = 384
_FATOR_OVERHEAD = 0.10
# `config-reference.md`: default 10MB; e 8 GB e o limite duro do Spark
# ("Cannot broadcast the table that is larger than 8GB").
_BROADCAST_DEFAULT_BYTES = 10 * _MIB
_BROADCAST_TETO_BYTES = 8 * 1024 * _MIB
_TAMANHO_RE = re.compile(r"^\s*(-?[0-9]+(?:\.[0-9]+)?)\s*([kmgtp]?)(?:i?b)?\s*$", re.IGNORECASE)
_POTENCIA = {"": 0, "k": 1, "m": 2, "g": 3, "t": 4, "p": 5}

_EXPLICACOES = {
    _CHAVE_OVERHEAD: (
        "Piso do pior executor medido: memoria fora do heap da JVM mais o processo "
        "Python (que so conta aqui sem `spark.executor.pyspark.memory`). E piso, nao "
        "alvo: um executor abaixo dele morre por limite de container sem OOM no log. "
        "No Glue a memoria do worker e fixa por tipo, e o piso diz quanto o job pediu "
        "fora do heap, nao que o worker deva crescer."
    ),
    _CHAVE_MEMORIA: (
        "Piso do pior executor medido no heap da JVM. Abaixo dele o heap nao cabe o que "
        "o run ja usou; acima, e escolha de quem aprova."
    ),
    _CHAVE_SPLIT: (
        "Alinha o split de leitura ao row group mediano COMPRIMIDO da fonte: split "
        "menor que o row group faz tasks disputarem o mesmo row group, e o Parquet so "
        "e dividido nessa unidade."
    ),
    _CHAVE_BROADCAST: (
        "Piso da ESTIMATIVA do otimizador para o lado menor do unico join candidato -- "
        "e contra a estimativa, e nao contra o tamanho serializado, que o Spark "
        "compara o threshold. O tamanho medido do broadcast, quando existe, vem ao lado "
        "como conferencia da estimativa, nunca como base da proposta."
    ),
    _CHAVE_SPECULATION: (
        "Ha executor com task lenta em varios stages sem ter lido mais que a mediana "
        "do stage (input mais shuffle lido): "
        "a lentidao e do NO, e nao da particao. Speculation relanca a task lenta em "
        "outro executor, e isso so ajuda quando o no e o problema -- ao custo de "
        "duplicar trabalho e I/O. Investigar o worker vem antes (`SF-UI-007`)."
    ),
    _CHAVE_NETWORK: (
        "A relacao estava quebrada: o heartbeat pedido nao cabia na espera do driver, "
        "e executor vivo seria declarado morto. O valor devolve a folga dos defaults "
        "(12 vezes o heartbeat) mantendo o heartbeat que alguem pediu (regra 16)."
    ),
    _CHAVE_BROADCAST_TIMEOUT: (
        "O broadcast estourou sem outra categoria e sem sintoma acima dos limiares da "
        "`SF-TIMEOUT-001`, e o mesmo broadcast ja completou num run medido. O piso e "
        "o maior tempo medido (coletar, montar e distribuir), com a folga declarada; "
        "com sintoma ao lado, subir o limite so adiaria a falha (regra 15)."
    ),
}


def _confs_por_chave(facts: Sequence[Fact], kind: str) -> dict[str, Fact]:
    saida: dict[str, Fact] = {}
    for fact in facts:
        if fact.kind != kind:
            continue
        chave = str(fact.attrs.get("key") or "")
        if chave:
            saida.setdefault(chave, fact)
    return saida


def _spark_version(runtime: dict[str, Any]) -> str:
    direto = str(runtime.get("spark") or "")
    if direto:
        return direto
    return _SPARK_POR_GLUE.get(str(runtime.get("glue") or ""), "")


def _aqe_por_default(spark_version: str) -> bool:
    partes = spark_version.split(".")
    try:
        maior, menor = int(partes[0]), int(partes[1])
    except (IndexError, ValueError):
        return False
    return (maior, menor) >= _AQE_DEFAULT_DESDE


def _procedencia(
    chave: str,
    efetivo: dict[str, Fact],
    codigo: dict[str, Fact],
    terraform: dict[str, Fact],
) -> tuple[str, str, list[str]]:
    """Devolve `(valor, classe, evidencia)`.

    A precedencia responde QUEM PEDIU, e nao quem venceu: `spark.conf_effective`
    diz o que o motor aplicou, e as outras duas dizem quem escreveu. Uma
    propriedade efetiva que ninguem no repositorio pediu veio do cluster ou do
    default, e isso muda o que fazer com ela.
    """
    fato_efetivo = efetivo.get(chave)
    valor = str(fato_efetivo.attrs.get("value")) if fato_efetivo else ""
    evidencia = [fato_efetivo.id] if fato_efetivo else []

    pedido = codigo.get(chave) or terraform.get(chave)
    if pedido is not None:
        evidencia.append(pedido.id)
        valor = valor or str(pedido.attrs.get("value") or "")
        if chave == _CHAVE_SHUFFLE and valor == _DEFAULT_SHUFFLE_PARTITIONS:
            return valor, "spark_default_explicit", evidencia
        return valor, "code" if chave in codigo else "terraform", evidencia

    if fato_efetivo is not None:
        return valor, "runtime_or_cluster", evidencia
    return "", "unset", evidencia


def _alvo(efetivo: dict[str, Fact]) -> tuple[float, str]:
    declarado = efetivo.get(_CHAVE_ALVO)
    if declarado is not None:
        try:
            return float(str(declarado.attrs.get("value"))), "declared"
        except ValueError:
            # Valor ilegivel nao vira default em silencio: cair no default
            # faria a resposta afirmar um alvo que o operador nao pediu.
            pass
    return float(_ALVO_DEFAULT_BYTES), "spark_default"


def _explicacao(aqe: bool) -> str:
    if aqe:
        return (
            "Com AQE ligado por default nesta versao, este numero e o PISO de "
            "paralelismo inicial: o motor coalesce as particoes pos-shuffle com "
            "estatistica real e chega perto do alvo sozinho. Derivar o piso "
            "alto demais custa tarefas curtas; derivar baixo demais o AQE nao "
            "conserta, porque ele so junta particao, nunca divide."
        )
    return (
        "AQE NAO e default nesta versao (o default comeca no Spark 3.2), entao "
        "este numero e o numero FINAL de particoes pos-shuffle. Nada o ajusta "
        "depois com estatistica real, e por isso ele importa mais aqui do que "
        "numa versao com AQE."
    )


def _bytes_de_config(valor: str, unidade_sem_sufixo: int) -> float | None:
    """`10MB`, `2g`, `4096` -> bytes. Sem sufixo, a unidade que a chave documenta."""
    casou = _TAMANHO_RE.match(valor or "")
    if not casou:
        return None
    numero = float(casou[1])
    potencia = casou[2].lower()
    if not potencia:
        return numero * unidade_sem_sufixo
    return numero * (1024 ** _POTENCIA[potencia])


def _recusa(reason: str, chave: str, detail: str) -> dict[str, Any]:
    return {"reason": reason, "property": chave, "detail": detail}


def _pedido(
    chave: str, efetivo: dict[str, Fact], codigo: dict[str, Fact], terraform: dict[str, Fact]
) -> str:
    return _procedencia(chave, efetivo, codigo, terraform)[0]


def _proposta(
    chave: str,
    confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]],
    valor: int | str,
    formula: str,
    base: dict[str, Any],
) -> dict[str, Any]:
    atual, classe, evidencia = _procedencia(chave, *confs)
    return {
        "key": chave,
        "current": {"value": atual, "provenance": classe, "evidence": evidencia},
        "derived": {"value": valor, "formula": formula, "basis": base},
        "safety": _SEGURANCA_POR_CHAVE[chave],
        "supported_in_runtime": True,
        "explanation": _EXPLICACOES[chave],
    }


_SEM_MEMORIA = (
    "Nenhum `spark.executor.memory_usage` nos facts. `sparkforge analyze event-log` o "
    "produz a partir de `SparkListenerStageExecutorMetrics`, um fact por executor."
)


def _executor(fact: Fact) -> str:
    return str(fact.attrs.get("executor_id") or fact.subject.get("symbol") or "")


def _overhead(
    facts: Sequence[Fact],
    confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]],
    headroom: float | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    usos = [f for f in facts if f.kind == "spark.executor.memory_usage"]
    if not usos:
        return None, _recusa("sem_memoria_por_executor", _CHAVE_OVERHEAD, _SEM_MEMORIA)
    python_fora = bool(_pedido(_CHAVE_PYSPARK_MEMORIA, *confs))
    if not python_fora and not any(
        f.measures.get("peak_python_rss_bytes") is not None for f in usos
    ):
        return None, _recusa(
            "sem_process_tree",
            _CHAVE_OVERHEAD,
            "O event log nao traz `ProcessTreePythonRSSMemory`, e sem o processo Python o "
            "pico fora do heap e metade da medida. Ligue "
            "`spark.executor.processTreeMetrics.enabled=true` (default `false`) e colete "
            "o event log de novo.",
        )

    def fora_do_heap(fact: Fact) -> float:
        python = 0.0 if python_fora else float(fact.measures.get("peak_python_rss_bytes") or 0)
        return float(fact.measures.get("peak_jvm_offheap_bytes") or 0) + python

    pior = max(usos, key=lambda f: (fora_do_heap(f), _executor(f)))
    folga = float(headroom or 0.0)
    base: dict[str, Any] = {
        "worst_executor": _executor(pior),
        "executors_measured": len(usos),
        "peak_jvm_offheap_bytes": float(pior.measures.get("peak_jvm_offheap_bytes") or 0),
        "peak_python_rss_bytes": float(pior.measures.get("peak_python_rss_bytes") or 0),
        "python_counted": not python_fora,
        "headroom": folga,
        "headroom_source": "declared" if headroom else "none",
    }
    memoria = _bytes_de_config(_pedido(_CHAVE_MEMORIA, *confs), _MIB)
    if memoria:
        base["effective_default_mib"] = max(
            _MIN_OVERHEAD_MIB, math.ceil(_FATOR_OVERHEAD * memoria / _MIB)
        )
    formula = (
        "ceil(max_executor(peak_jvm_offheap_bytes"
        + ("" if python_fora else " + peak_python_rss_bytes")
        + ") * (1 + headroom) / MiB)"
    )
    valor = math.ceil(fora_do_heap(pior) * (1.0 + folga) / _MIB)
    return _proposta(_CHAVE_OVERHEAD, confs, valor, formula, base), None


def _memoria(
    facts: Sequence[Fact], confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    usos = [f for f in facts if f.kind == "spark.executor.memory_usage"]
    if not usos:
        return None, _recusa("sem_memoria_por_executor", _CHAVE_MEMORIA, _SEM_MEMORIA)
    com_heap = [f for f in usos if f.measures.get("peak_jvm_heap_bytes") is not None]
    if not com_heap:
        return None, _recusa(
            "sem_pico_de_heap",
            _CHAVE_MEMORIA,
            "Nenhum executor com `JVMHeapMemory` no event log: sem o pico de heap nao ha "
            "piso a propor.",
        )
    pior = max(com_heap, key=lambda f: (float(f.measures["peak_jvm_heap_bytes"]), _executor(f)))
    pico = float(pior.measures["peak_jvm_heap_bytes"])
    base = {"worst_executor": _executor(pior), "executors_measured": len(com_heap),
            "peak_jvm_heap_bytes": pico}
    valor = math.ceil(pico / _MIB)
    return _proposta(
        _CHAVE_MEMORIA, confs, valor, "ceil(max_executor(peak_jvm_heap_bytes) / MiB)", base
    ), None


def _split(
    facts: Sequence[Fact], confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    por_fonte: dict[str, list[float]] = {}
    for fact in facts:
        comprimido = float(fact.attrs.get("total_compressed_bytes") or 0)
        if fact.kind == "parquet.row_group" and comprimido > 0:
            por_fonte.setdefault(str(fact.attrs.get("prefix") or ""), []).append(comprimido)
    if not por_fonte:
        return None, _recusa(
            "sem_footer",
            _CHAVE_SPLIT,
            "Nenhum `parquet.row_group` com tamanho comprimido. `sparkforge collect "
            "parquet-footer --prefix <fonte>` e `sparkforge analyze parquet-footer` o produzem.",
        )
    medianas = {fonte: math.ceil(statistics.median(v)) for fonte, v in sorted(por_fonte.items())}
    if len(medianas) > 1:
        return None, _recusa(
            "fontes_divergentes",
            _CHAVE_SPLIT,
            "A propriedade e uma so para o job, e cada fonte pede a sua: "
            + "; ".join(f"{fonte}: {mediana} bytes" for fonte, mediana in medianas.items())
            + ". Uma media esconderia a fonte que importa; a escolha e de quem aprova.",
        )
    fonte, mediana = next(iter(medianas.items()))
    tamanhos = por_fonte[fonte]
    base = {"source": fonte, "row_groups": len(tamanhos),
            "median_compressed_row_group_bytes": mediana,
            "min_compressed_row_group_bytes": math.ceil(min(tamanhos)),
            "max_compressed_row_group_bytes": math.ceil(max(tamanhos))}
    return _proposta(
        _CHAVE_SPLIT, confs, mediana, "ceil(median(row_group.total_compressed_bytes))", base
    ), None


def _menor_lado(join: Fact) -> float | None:
    lados = [
        float(join.measures[chave])
        for chave, tem in (("left_bytes", "left_has_stats"), ("right_bytes", "right_has_stats"))
        if join.attrs.get(tem) and join.measures.get(chave) is not None
    ]
    return min(lados) if lados else None


def _broadcast(
    facts: Sequence[Fact], confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    joins = [f for f in facts if f.kind == "plan.join_side_stats"]
    if not joins:
        return None, _recusa(
            "sem_explain_cost",
            _CHAVE_BROADCAST,
            "Nenhuma estimativa de join. Gere o plano com `df.explain(\"cost\")` (ou "
            "`EXPLAIN COST`) e extraia com `sparkforge analyze plan`.",
        )
    pedido = _pedido(_CHAVE_BROADCAST, *confs)
    limiar = _bytes_de_config(pedido, 1) if pedido else None
    origem = "configured" if limiar is not None else "spark_default"
    limiar = _BROADCAST_DEFAULT_BYTES if limiar is None else limiar
    if limiar < 0:
        return None, _recusa(
            "broadcast_desligado",
            _CHAVE_BROADCAST,
            "O threshold esta em -1: alguem desligou o broadcast automatico de proposito. "
            "Religar e decisao de quem desligou, nao derivacao.",
        )
    menores = [(join, _menor_lado(join)) for join in joins]
    candidatos = [
        (j, m) for j, m in menores if m is not None and limiar < m < _BROADCAST_TETO_BYTES
    ]
    if len(candidatos) > 1:
        return None, _recusa(
            "joins_divergentes",
            _CHAVE_BROADCAST,
            "O threshold vale para o job inteiro, e mais de um join pede o seu piso: "
            + "; ".join(
                f"linha {j.subject.get('line')}: {math.ceil(m / _MIB) * _MIB} bytes"
                for j, m in candidatos
            )
            + ". Escolher um ligaria o broadcast dos outros junto.",
        )
    if not candidatos:
        if any(m is not None and m >= _BROADCAST_TETO_BYTES for _, m in menores):
            return None, _recusa(
                "lado_acima_de_8gb",
                _CHAVE_BROADCAST,
                "O lado menor passa do limite duro de 8 GB do Spark para broadcast.",
            )
        if all(m is None for _, m in menores):
            return None, _recusa(
                "estimativa_sem_estatistica",
                _CHAVE_BROADCAST,
                "Nenhum lado de join tem estatistica: a estimativa e o default do Spark "
                "(8.0 EiB). Rode `ANALYZE TABLE <tabela> COMPUTE STATISTICS` na tabela menor "
                "e gere o EXPLAIN COST de novo.",
            )
        return None, _recusa(
            "ja_cabe_no_threshold",
            _CHAVE_BROADCAST,
            "O lado menor de todo join estimado ja cabe no threshold efetivo: a estimativa "
            "nao e o que impede o broadcast.",
        )
    join, menor = candidatos[0]
    medidos = sorted(
        (
            dict(sorted(f.measures.items()))
            for f in facts
            if f.kind == "spark.sql.broadcast_exchange"
        ),
        key=lambda m: sorted(m.items()),
    )
    base = {
        "join_line": join.subject.get("line"),
        "join_type": join.attrs.get("join_type"),
        "smaller_side_bytes": menor,
        "effective_threshold_bytes": limiar,
        "threshold_source": origem,
        "measured_broadcasts": medidos,
    }
    valor = math.ceil(menor / _MIB) * _MIB
    return _proposta(
        _CHAVE_BROADCAST, confs, valor, "ceil(smaller_side_estimated_bytes / MiB) * MiB", base
    ), None


def _speculation(
    facts: Sequence[Fact], confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if _pedido(_CHAVE_SPECULATION, *confs).strip().lower() == "true":
        return None, _recusa(
            "speculation_ja_ligada",
            _CHAVE_SPECULATION,
            "`spark.speculation` ja esta pedido como `true`: nao ha o que propor.",
        )
    nos = sorted(
        (f for f in facts if f.kind == "spark.executor.slow_node"),
        key=lambda f: str(f.attrs.get("executor_id") or ""),
    )
    lentas = [f for f in facts if f.kind == "spark.stage.slow_tasks"]
    if not nos:
        return None, _sem_no_lento(facts, lentas)
    criterio = min(lentas, key=lambda f: f.id).attrs if lentas else {}
    base = {
        "slow_nodes": [
            {
                "executor_id": f.attrs.get("executor_id"),
                "host": f.attrs.get("host"),
                "stages_slow": f.measures.get("stages_slow"),
                "stage_ids": f.attrs.get("stage_ids"),
            }
            for f in nos
        ],
        "criterion": {
            chave: criterio.get(chave)
            for chave in ("multiplier", "quantile", "min_task_ms", "criterion_source")
        },
    }
    return _proposta(
        _CHAVE_SPECULATION,
        confs,
        "true",
        "slow_node: mesmo executor com task > max(multiplier * mediana, min_task_ms) "
        "em >= 2 stages, com input <= mediana do stage",
        base,
    ), None


def _sem_no_lento(facts: Sequence[Fact], lentas: list[Fact]) -> dict[str, Any]:
    """Nomeia POR QUE nao ha no lento, na ordem em que a medida falta."""
    if not lentas:
        if not any(f.kind == "spark.stage.task_duration" for f in facts):
            return _recusa(
                "sem_tasks_por_executor",
                _CHAVE_SPECULATION,
                "Nenhuma duracao de task nos facts. `sparkforge analyze event-log` a extrai "
                "de `SparkListenerTaskEnd`, com o executor de cada task.",
            )
        if not any(f.kind == "spark.runtime_version" for f in facts):
            return _recusa(
                "criterio_de_especulacao_desconhecido",
                _CHAVE_SPECULATION,
                "O log nao declara a versao do Spark (`SparkListenerLogStart`) nem os tres "
                "parametros de speculation, e o criterio de task lenta muda no Spark 4.0 "
                "(multiplier 1.5 e quantile 0.75 antes, 3 e 0.9 depois).",
            )
        return _recusa(
            "sem_tasks_lentas",
            _CHAVE_SPECULATION,
            "Nenhuma task passou do criterio do Spark para copia especulativa "
            "(max(multiplier * mediana, tempo minimo)): nao ha o que relancar.",
        )
    estagios: dict[str, set[Any]] = {}
    for fato in lentas:
        for executor in fato.attrs.get("by_executor") or {}:
            estagios.setdefault(str(executor), set()).add(fato.subject.get("stage_id"))
    repetidos = sorted(e for e, s in estagios.items() if len(s) >= 2)
    if repetidos:
        return _recusa(
            "lentidao_da_particao",
            _CHAVE_SPECULATION,
            f"Executor(es) {', '.join(repetidos)} lento(s) em mais de um stage, mas as "
            "tasks lentas leram mais que a mediana do stage (input mais shuffle lido), ou a "
            "leitura nao foi medida: a particao explica a lentidao, e speculation so "
            "duplicaria o trabalho grande.",
        )
    return _recusa(
        "lentidao_espalhada",
        _CHAVE_SPECULATION,
        "As tasks lentas caem em executores diferentes a cada stage: nenhum no se repete, "
        "e nao ha no para contornar.",
    )


def _network(
    facts: Sequence[Fact], confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    relacoes = sorted((f for f in facts if f.kind == "spark.timeout.relation"), key=lambda f: f.id)
    if not relacoes:
        return None, _recusa(
            "sem_relacao_observada",
            _CHAVE_NETWORK,
            "Sem `spark.timeout.relation`: o run nao reportou `spark.executor.heartbeatInterval` "
            "e `spark.network.timeout` juntos em `spark.conf_effective`. `sparkforge analyze "
            "event-log` seguido de `sparkforge fuse` a produz.",
        )
    relacao = relacoes[0]
    heartbeat = float(relacao.measures.get("heartbeat_s") or 0.0)
    rede = float(relacao.measures.get("network_timeout_s") or 0.0)
    if heartbeat < rede:
        return None, _recusa(
            "relacao_ok",
            _CHAVE_NETWORK,
            f"Heartbeat de {heartbeat:g}s cabe na espera de {rede:g}s: a relacao que a "
            "`SF-TIMEOUT-002` confere esta de pe, e o valor isolado nao e certo nem errado "
            "(regra 16).",
        )
    base = {
        "heartbeat_s": heartbeat,
        "network_timeout_s": rede,
        "ratio": _RAZAO_REDE_HEARTBEAT,
        "ratio_source": "spark_defaults_120s_over_10s",
    }
    valor = math.ceil(heartbeat * _RAZAO_REDE_HEARTBEAT)
    return _proposta(_CHAVE_NETWORK, confs, valor, "ceil(heartbeat_s * 12)", base), None


@functools.lru_cache(maxsize=1)
def _limiares_de_sintoma() -> tuple[tuple[str, float], ...] | None:
    """Os limiares da `SF-TIMEOUT-001`, lidos do catalogo e de nenhum outro lugar.

    Limiar e regra (regra 11): copia-lo aqui divergiria na primeira mudanca do
    catalogo. So `timeout.yaml` e lido, pelo caminho contido do loader.
    """
    try:
        caminho = safe_catalog_file(catalog_dir(), "timeout.yaml")
        documento = yaml.safe_load(caminho.read_text(encoding="utf-8-sig")) or {}
    except (OSError, yaml.YAMLError, CatalogError):
        return None
    regra = next(
        (r for r in documento.get("rules") or [] if r.get("id") == "SF-TIMEOUT-001"), None
    )
    limiar = (regra or {}).get("threshold")
    if not isinstance(limiar, dict):
        return None
    return tuple(sorted((str(k), float(v)) for k, v in limiar.items()))


def _broadcast_timeout(
    facts: Sequence[Fact],
    confs: tuple[dict[str, Fact], dict[str, Fact], dict[str, Fact]],
    headroom: float | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    diagnosticos = sorted(
        (f for f in facts if f.kind == "spark.timeout.diagnosis"), key=lambda f: f.id
    )
    de_broadcast = [f for f in diagnosticos if f.attrs.get("category") == "broadcast"]
    if not de_broadcast:
        vistas = sorted({str(f.attrs.get("category")) for f in diagnosticos})
        return None, _recusa(
            "sem_diagnostico_de_broadcast",
            _CHAVE_BROADCAST_TIMEOUT,
            "Nenhum `spark.timeout.diagnosis` com categoria `broadcast`"
            + (f" (visto: {', '.join(vistas)})" if vistas else "")
            + ". Sem o broadcast estourando o limite nao tem o que sustentar; `wall_clock` e "
            "`heartbeat` nunca tem valor proposto (regra 15).",
        )
    diagnostico = de_broadcast[0]
    outras = [str(c) for c in diagnostico.attrs.get("also_seen") or []]
    if outras:
        return None, _recusa(
            "broadcast_com_outra_categoria",
            _CHAVE_BROADCAST_TIMEOUT,
            f"O broadcast estourou junto de {', '.join(outras)}: a outra categoria pode ser "
            "a causa, e subir o limite do broadcast a mascararia.",
        )
    limiares = _limiares_de_sintoma()
    if limiares is None:
        return None, _recusa(
            "limiar_indisponivel",
            _CHAVE_BROADCAST_TIMEOUT,
            "Os limiares de sintoma da `SF-TIMEOUT-001` nao foram lidos de "
            "`rules/catalog/timeout.yaml`; sem eles nao da para dizer que nao ha sintoma.",
        )
    por_chave = dict(limiares)
    acima = [
        f"{medida}={float(diagnostico.measures[medida]):g} (limiar {por_chave[chave]:g})"
        for medida, chave in _SINTOMAS
        if medida in diagnostico.measures
        and chave in por_chave
        and float(diagnostico.measures[medida]) >= por_chave[chave]
    ]
    if acima:
        return None, _recusa(
            "sintoma_ao_lado",
            _CHAVE_BROADCAST_TIMEOUT,
            "Sintoma medido ao lado do timeout: " + "; ".join(acima) + ". Subir o limite "
            "troca uma falha rapida por uma cara (`SF-TIMEOUT-001`, regra 15).",
        )
    medidos = sorted(
        sum(float(f.measures.get(k) or 0.0) for k in ("collect_ms", "build_ms", "broadcast_ms"))
        for f in facts
        if f.kind == "spark.sql.broadcast_exchange"
    )
    medidos = [m for m in medidos if m > 0]
    if not medidos:
        return None, _recusa(
            "sem_broadcast_medido",
            _CHAVE_BROADCAST_TIMEOUT,
            "Nenhum `spark.sql.broadcast_exchange` com tempo medido: o piso sai do broadcast "
            "que COMPLETOU, num run bem-sucedido. `sparkforge analyze sql-metrics` sobre o "
            "event log dele o produz.",
        )
    folga = float(headroom or 0.0)
    piso_ms = medidos[-1]
    valor = math.ceil(piso_ms * (1.0 + folga) / 1000.0)
    pedido = _pedido(_CHAVE_BROADCAST_TIMEOUT, *confs)
    atual = _segundos(pedido) if pedido else None
    origem = "configured" if atual is not None else "spark_default"
    atual = _BROADCAST_TIMEOUT_DEFAULT_S if atual is None else atual
    if atual >= valor:
        return None, _recusa(
            "ja_cabe_no_timeout",
            _CHAVE_BROADCAST_TIMEOUT,
            f"O limite efetivo de {atual:g}s ja passa do piso medido de {valor}s: o broadcast "
            "que completou coube nele, e o estouro nao e falta de tempo medida.",
        )
    base = {
        "measured_broadcast_ms": piso_ms,
        "broadcasts_measured": len(medidos),
        "effective_timeout_s": atual,
        "timeout_source": origem,
        "headroom": folga,
        "headroom_source": "declared" if headroom else "none",
        "diagnosis_basis": diagnostico.attrs.get("basis"),
    }
    return _proposta(
        _CHAVE_BROADCAST_TIMEOUT,
        confs,
        valor,
        "ceil(max(collect_ms + build_ms + broadcast_ms) * (1 + headroom) / 1000)",
        base,
    ), None


def build_conf_advice(
    facts: Sequence[Fact],
    *,
    runtime: dict[str, Any],
    headroom: float | None = None,
) -> dict[str, Any]:
    """Deriva o que a medida sustenta, e recusa por nome o resto."""
    spark_version = _spark_version(runtime)
    aqe = _aqe_por_default(spark_version)

    efetivo = _confs_por_chave(facts, "spark.conf_effective")
    codigo = _confs_por_chave(facts, "pyspark.conf_set")
    terraform = _confs_por_chave(facts, "tf.spark_conf")

    recusas: list[dict[str, Any]] = []
    propriedades: list[dict[str, Any]] = []

    shuffle_bytes = sum(
        float(f.measures.get("write_bytes") or 0.0)
        for f in facts
        if f.kind == "spark.stage.shuffle"
    )

    if not spark_version:
        recusas.append(
            {
                "reason": "runtime_unknown",
                "property": _CHAVE_SHUFFLE,
                "detail": (
                    "Sem versao de Glue ou de Spark nao da para dizer se AQE e "
                    "default, e o mesmo numero significa piso inicial numa "
                    "versao e numero final na outra. `sparkforge runtime detect` "
                    "resolve a versao a partir dos artefatos."
                ),
            }
        )
    elif shuffle_bytes <= 0:
        recusas.append(
            {
                "reason": "no_shuffle_measured",
                "property": _CHAVE_SHUFFLE,
                "detail": (
                    "Nenhum `spark.stage.shuffle` com `write_bytes` acima de "
                    "zero. Zero particoes nao e configuracao, e um job sem "
                    "shuffle nao tem o que paralelizar aqui. "
                    "`sparkforge analyze event-log` produz a medida."
                ),
            }
        )
    else:
        alvo_bytes, alvo_origem = _alvo(efetivo)
        valor, classe, evidencia = _procedencia(_CHAVE_SHUFFLE, efetivo, codigo, terraform)
        propriedades.append(
            {
                "key": _CHAVE_SHUFFLE,
                "current": {"value": valor, "provenance": classe, "evidence": evidencia},
                "derived": {
                    "value": math.ceil(shuffle_bytes / alvo_bytes),
                    "formula": "ceil(shuffle_write_bytes / target_partition_bytes)",
                    "basis": {
                        "shuffle_write_bytes": shuffle_bytes,
                        "target_partition_bytes": alvo_bytes,
                        "target_source": alvo_origem,
                    },
                },
                "safety": _SEGURANCA_POR_CHAVE[_CHAVE_SHUFFLE],
                "supported_in_runtime": True,
                "explanation": _explicacao(aqe),
            }
        )

    confs = (efetivo, codigo, terraform)
    for proposta, recusa in (
        _overhead(facts, confs, headroom),
        _memoria(facts, confs),
        _split(facts, confs),
        _broadcast(facts, confs),
        _speculation(facts, confs),
        _network(facts, confs),
        _broadcast_timeout(facts, confs, headroom),
    ):
        if proposta is not None:
            propriedades.append(proposta)
        if recusa is not None:
            recusas.append(recusa)

    return {
        "runtime": {
            "glue_version": str(runtime.get("glue") or ""),
            "spark_version": spark_version,
            "aqe_default": aqe,
        },
        "properties": propriedades,
        "refused": recusas,
    }
