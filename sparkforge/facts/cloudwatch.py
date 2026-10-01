"""Extrator do artefato de metricas do CloudWatch em Facts.

POR QUE ESTE MODULO NASCEU DEPOIS DO COLETOR. `collect_cloudwatch` existia,
gravava o artefato e o registrava no manifesto, e nenhum consumidor o lia --
`glue.driver.*` aparecia no catalogo de regras apenas em texto de
`validation:`, nunca como `kind` casado por um `when:`. Artefato coletado sem
extrator e custo de coleta sem retorno.

Um `kind` so, `glue.metric`, discriminado por `attrs.name`, no molde de
`tf.attribute` -- e nao dezessete kinds, um por metrica. Como nenhuma regra
consumia CloudWatch, a forma estava livre; a escolhida e a que o motor de
regras ja sabe casar.

Puro e deterministico como os extratores irmaos: nunca aplica limiar, nunca
atribui severidade, nunca toca a rede.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import CLOUDWATCH_METRICS
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "cloudwatch@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.metric",
        "glue.metric.unresolved",
        "glue.metric.analyzed",
    }
)

# Estatistica exigida por metrica, de `CLOUDWATCH_METRICS`. Vai para dentro do
# fact porque `glue.error.ALL` e contador documentado como Sum: um leitor que
# nao souber a estatistica nao consegue interpretar o numero.
_STAT_BY_METRIC: dict[str, str] = dict(CLOUDWATCH_METRICS)


def _nearest_rank(sorted_values: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e `iceberg_metadata._nearest_rank`,
    reescrita aqui em vez de importada pela razao ja registrada por escrito em
    `iceberg_metadata.py:128`: os extratores sao modulos independentes por
    desenho. O que garante que as tres continuam iguais e teste, nao import.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


def _provenance(path: str, label: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": path, "metric": label}


def extract_cloudwatch(payload: dict[str, Any], path: str) -> list[Fact]:
    """Extrai Facts do conteudo ja carregado de um artefato CloudWatch."""
    job_name = payload.get("job_name") or ""
    job_run_id = payload.get("job_run_id") or ""
    period = payload.get("period_seconds")
    # `type: "job_run"` pelo mesmo precedente de `spark.job.spill_summary`
    # (`sparkforge/facts/event_log.py:646`): o enum fechado de `subject.type`
    # nao tem um tipo "metrica de run" proprio, e o job_run_id e a entidade
    # ancorada mais proxima. `symbol` = job_run_id: unico por run, e os tres
    # kinds deste modulo (`glue.metric`, `.unresolved`, `.analyzed`) sao todos
    # por-run, sem agregacao entre runs -- ao contrario de
    # `glue.job_run.distribution`/`.outcome` em `glue_job_run.py`.
    subject = {
        "job_name": job_name,
        "job_run_id": job_run_id,
        "type": "job_run",
        "symbol": job_run_id,
    }

    facts: list[Fact] = []
    with_data = 0
    empty = 0

    for result in payload.get("metric_data_results") or []:
        label = result.get("Label") or ""
        values = [float(v) for v in (result.get("Values") or [])]
        if not values:
            empty += 1
            facts.append(
                Fact(
                    kind="glue.metric.unresolved",
                    subject=dict(subject),
                    attrs={
                        "name": label,
                        "reason": "empty_series",
                        "detail": (
                            "CloudWatch devolveu a serie sem pontos. Duas causas possiveis e "
                            "distintas: observabilidade nao habilitada no job "
                            "(--enable-observability-metrics=true), ou a janela consultada nao "
                            "tem dado. Expiracao por retencao e recusada na coleta, nao aqui."
                        ),
                    },
                    provenance=_provenance(path, label),
                )
            )
            continue

        with_data += 1
        values.sort()
        facts.append(
            Fact(
                kind="glue.metric",
                subject=dict(subject),
                attrs={
                    "name": label,
                    "stat": _STAT_BY_METRIC.get(label, ""),
                    "period_s": period,
                },
                measures={
                    "min": values[0],
                    "p50": _nearest_rank(values, 50),
                    "p95": _nearest_rank(values, 95),
                    "max": values[-1],
                    "datapoints": len(values),
                },
                provenance=_provenance(path, label),
            )
        )

    facts.append(
        Fact(
            kind="glue.metric.analyzed",
            subject=dict(subject),
            measures={"metrics_with_data": with_data, "metrics_empty": empty},
            provenance={"extractor": EXTRACTOR_ID, "artifact": path},
        )
    )
    return sort_facts(facts)


def extract_cloudwatch_path(path: Path) -> list[Fact]:
    """Le o artefato do disco e delega para `extract_cloudwatch`."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return extract_cloudwatch(payload, str(path))
