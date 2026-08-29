"""Utilizacao de worker ao lado do skew, num fact so.

POR QUE AS DUAS JUNTAS. A seccao 37 do documento de origem pede que o
financeiro encontre desperdicio, e avisa no mesmo paragrafo que utilizacao
baixa com skew extremo NAO significa reduzir workers: noventa por cento dos
executores podem estar ociosos porque uma task ficou catorze minutos numa
particao torta, e tirar worker dali nao toca a causa.

As duas medidas moram em fontes diferentes -- utilizacao vem do CloudWatch
(`glue.metric`), skew vem do event log (`spark.stage.task_duration`) -- e a DSL
do catalogo casa um fact por clausula. Sem este resumo, a regra que separa
"superdimensionado" de "ocioso por skew" precisaria correlacionar dois kinds
dentro do `when`, e nao ha como.

FORMA. Isto e fact, e nao mecanismo: nao ha limiar e nao ha juizo, so leitura de
duas medidas que ja existem. O limiar e da regra, versionado no catalogo junto
do resto. Deriva de fact e nao de caminho, como `run_cost` e
`timeout_diagnosis`.

O QUE ESTE MODULO RECUSA: quantificar economia. "Voce poderia economizar X"
exige o custo do run que NAO aconteceu, e o subprojeto E ja recusou esse
contrafactual por escrito.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "utilization@0.1.0"

EMITTED_KINDS = frozenset({"glue.utilization.summary", "glue.utilization.unresolved"})

_METRICA_UTILIZACAO = "glue.driver.workerUtilization"

# Memoria e disco entram pelo p95 e nao pelo p50: o pico e o que decide se havia
# folga, e uma media baixa com pico alto nao e folga nenhuma.
_METRICAS_DE_FOLGA = (
    ("memory_used_pct_p95", "glue.ALL.memory.total.used.percentage", "p95"),
    ("disk_used_pct_p95", "glue.driver.disk.used.percentage", "p95"),
)

_COMO_COLETAR = (
    "sparkforge collect cloudwatch traz glue.driver.workerUtilization, e "
    "sparkforge analyze cloudwatch o transforma em glue.metric."
)


def _metrica(facts: Sequence[Fact], nome: str) -> Fact | None:
    for fact in facts:
        if fact.kind == "glue.metric" and str(fact.attrs.get("name") or "") == nome:
            return fact
    return None


def _skew(facts: Sequence[Fact]) -> float | None:
    """A razao do PIOR stage, e nao a media entre eles.

    A media dilui exatamente o stage que segura o job: um stage torto entre
    vinte saudaveis desaparece na media e e o unico que importa.
    """
    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in facts
        if f.kind == "spark.stage.task_duration" and f.measures.get("p50_ms")
    ]
    return round(max(razoes), 2) if razoes else None


def extract_utilization(facts: Sequence[Fact], path: str) -> list[Fact]:
    """Um resumo por run, ou uma lacuna nomeada quando falta a utilizacao."""
    if not facts:
        # Pool vazio nao e lacuna: nada foi lido, e nada foi lido nao e o
        # mesmo que lido e sem a metrica.
        return []

    utilizacao = _metrica(facts, _METRICA_UTILIZACAO)
    subject: dict[str, Any] = {"type": "job_run", "symbol": ""}
    if utilizacao is not None:
        subject = dict(utilizacao.subject)

    if utilizacao is None or utilizacao.measures.get("p50") is None:
        return [
            Fact(
                kind="glue.utilization.unresolved",
                subject=subject,
                attrs={
                    "reason": "utilization_not_observed",
                    "detail": (
                        f"Sem `{_METRICA_UTILIZACAO}` nao da para dizer se havia folga: "
                        f"utilizacao e o eixo da pergunta, e as outras medidas sozinhas "
                        f"nao a substituem. {_COMO_COLETAR}"
                    ),
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        ]

    medidas: dict[str, float] = {
        "worker_utilization_p50": float(utilizacao.measures["p50"]),
    }
    for chave, nome, estatistica in _METRICAS_DE_FOLGA:
        fato = _metrica(facts, nome)
        if fato is not None and fato.measures.get(estatistica) is not None:
            medidas[chave] = float(fato.measures[estatistica])

    razao = _skew(facts)
    if razao is not None:
        medidas["skew_p95_over_p50"] = razao

    return sort_facts(
        [
            Fact(
                kind="glue.utilization.summary",
                subject=subject,
                measures=medidas,
                attrs={"utilization_metric": _METRICA_UTILIZACAO},
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        ]
    )
