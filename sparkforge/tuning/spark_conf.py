"""O valor que a medida sustenta, e a procedencia de cada propriedade.

O documento de origem poe em letras grandes: `spark.sql.shuffle.partitions`
passa a ser DERIVED, e nao HARDCODED. Desde 2026-09-14 sao cinco derivacoes --
shuffle, overhead, heap, split de leitura e threshold de broadcast --, cada uma
com a formula e a base medida; o resto do 11 entra como recusa NOMEADA, com a
medida que a destravaria. Listar a recusa e a diferenca entre "nao sei" e "nao
perguntei". Toda proposta e PISO medido (ou a estimativa que o proprio Spark
compara, no broadcast) e sai `REVIEW`: nada aqui e ganho estimado.

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

import math
import re
import statistics
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact

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

# As propriedades que o 11 lista e que NENHUMA fonte de hoje sustenta, com a
# medida que destravaria cada uma. A lista e explicita porque omissao silenciosa
# e o defeito que este bloco existe para evitar.
_SEM_BASE_MEDIDA = {
    "spark.speculation": (
        "O documento de origem recusa explicitamente a inferencia "
        "`skew detectado -> speculation=true`: speculation duplica trabalho e "
        "aumenta I/O e custo. A decisao exige saber se a lentidao e do NO ou "
        "da PARTICAO, e nenhuma fonte de hoje separa os dois."
    ),
    "spark.sql.broadcastTimeout": (
        "Subir timeout nao e conserto de performance -- e a `SF-TIMEOUT-001`, "
        "do subprojeto F. O diagnostico de timeout nomeia a categoria; propor "
        "um numero novo aqui contradiria a regra."
    ),
    "spark.network.timeout": (
        "Mesma razao de `spark.sql.broadcastTimeout`. A relacao com "
        "`spark.executor.heartbeatInterval` e conferida por `SF-TIMEOUT-002`, "
        "que julga a RELACAO e nao o valor."
    ),
}

# Niveis do 34 do documento. Paralelismo de shuffle e REVIEW pela lista dele:
# muda a forma do trabalho, nao o resultado, e nunca entra em producao sem
# alguem olhar.
_CHAVE_OVERHEAD = "spark.executor.memoryOverhead"
_CHAVE_MEMORIA = "spark.executor.memory"
_CHAVE_PYSPARK_MEMORIA = "spark.executor.pyspark.memory"
_CHAVE_SPLIT = "spark.sql.files.maxPartitionBytes"
_CHAVE_BROADCAST = "spark.sql.autoBroadcastJoinThreshold"

_SEGURANCA_POR_CHAVE = {
    _CHAVE_SHUFFLE: "REVIEW",
    _CHAVE_OVERHEAD: "REVIEW",
    _CHAVE_MEMORIA: "REVIEW",
    _CHAVE_SPLIT: "REVIEW",
    _CHAVE_BROADCAST: "REVIEW",
}

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
    valor: int,
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
    ):
        if proposta is not None:
            propriedades.append(proposta)
        if recusa is not None:
            recusas.append(recusa)

    for chave, razao in sorted(_SEM_BASE_MEDIDA.items()):
        recusas.append({"reason": "no_measured_basis", "property": chave, "detail": razao})

    return {
        "runtime": {
            "glue_version": str(runtime.get("glue") or ""),
            "spark_version": spark_version,
            "aqe_default": aqe,
        },
        "properties": propriedades,
        "refused": recusas,
    }
