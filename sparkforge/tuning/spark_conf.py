"""O valor que a medida sustenta, e a procedencia de cada propriedade.

O documento de origem poe em letras grandes: `spark.sql.shuffle.partitions`
passa a ser DERIVED, e nao HARDCODED. Aqui esta a derivacao, e ela e a UNICA --
as outras trinta propriedades do 11 entram como recusa NOMEADA, cada uma com a
medida que a destravaria. Listar a recusa e a diferenca entre "nao sei" e "nao
perguntei".

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
    "spark.sql.autoBroadcastJoinThreshold": (
        "Exigiria o tamanho SERIALIZADO do lado pequeno do join, que nem "
        "`plan.join` nem `spark.sql.join_input` medem hoje -- os dois dao "
        "tamanho de entrada, e broadcast falha pelo tamanho em memoria do "
        "executor."
    ),
    "spark.executor.memoryOverhead": (
        "Exigiria o pico de memoria fora do heap por executor. "
        "`spark.executor.memory_usage` traz o pico de heap, e overhead e a "
        "outra metade -- propor sobre a metade errada e propor sobre nada."
    ),
    "spark.speculation": (
        "O documento de origem recusa explicitamente a inferencia "
        "`skew detectado -> speculation=true`: speculation duplica trabalho e "
        "aumenta I/O e custo. A decisao exige saber se a lentidao e do NO ou "
        "da PARTICAO, e nenhuma fonte de hoje separa os dois."
    ),
    "spark.sql.files.maxPartitionBytes": (
        "Exigiria distribuicao de tamanho de arquivo por fonte lida. "
        "`spark.sql.scan` traz bytes e arquivos lidos no total, e um valor "
        "derivado da media esconderia exatamente o caso que importa, que e a "
        "fonte com arquivo grande demais."
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
_SEGURANCA_POR_CHAVE = {_CHAVE_SHUFFLE: "REVIEW"}


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


def build_conf_advice(
    facts: Sequence[Fact],
    *,
    runtime: dict[str, Any],
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
