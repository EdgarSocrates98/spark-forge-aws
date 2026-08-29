"""O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta.

NAO e extrator, e nada aqui vira Fact. O fact de custo e
`sparkforge/facts/run_cost.py`; este modulo COMPOE -- e composicao e leitura,
nao medicao.

A FRONTEIRA E O NUCLEO. DPU-segundos nao e invariante na troca entre mais
recurso e mais tempo: dobrar workers raramente divide o tempo por dois, e as
vezes divide por mais. Duas capacidades medidas lado a lado respondem o que
nenhum modelo responderia sem inventar um fator de eficiencia que fonte
nenhuma publica.

O QUE ESTE MODULO RECUSA:
  - Atribuir custo a causa. "Voce desperdicou X com spill" exige o custo do run
    que NAO aconteceu.
  - Interpolar entre capacidades observadas. A curva seria bonita e mentiria
    exatamente entre os pontos, que e onde alguem olharia.
  - Ordenar achado por economia estimada. Cada numero desses e um
    contrafactual disfarcado de prioridade.
  - Limiar de "caro". Fonte nenhuma diz que 2,32 USD por run e muito.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


def _capacidade(run: Fact) -> tuple[str, str, int, bool]:
    return (
        str(run.attrs.get("glue_version") or ""),
        str(run.attrs.get("worker_type") or ""),
        int(run.measures.get("number_of_workers") or 0),
        bool(run.attrs.get("autoscaling")),
    )


def _frontier(
    runs: Sequence[Fact], custo_por_run: dict[str, float]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grupos: dict[tuple[str, str, int, bool], list[Fact]] = {}
    for run in runs:
        grupos.setdefault(_capacidade(run), []).append(run)

    linhas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        custos = sorted(
            custo_por_run[str(m.subject.get("job_run_id"))]
            for m in membros
            if str(m.subject.get("job_run_id")) in custo_por_run
        )
        if not custos:
            recusas.append(
                {
                    "reason": "cost_unobservable",
                    "capacity": f"{worker_type} x{workers}",
                    "runs": len(membros),
                    "detail": (
                        "Nenhum run desta capacidade tem custo: sem `dpu_seconds` nao ha "
                        "o que converter. Sob Auto Scaling sem DPUSeconds o coletor "
                        "recusou derivar, e a recusa se propaga ate aqui."
                    ),
                }
            )
            continue
        duracoes = sorted(
            float(m.measures["execution_time_s"])
            for m in membros
            if m.measures.get("execution_time_s") is not None
        )
        linhas.append(
            {
                "glue_version": glue_version,
                "worker_type": worker_type,
                "number_of_workers": workers,
                "autoscaling": autoscaling,
                "runs": len(membros),
                "runtime_p50_s": _nearest_rank(duracoes, 50) if duracoes else None,
                "runtime_p95_s": _nearest_rank(duracoes, 95) if duracoes else None,
                "cost_per_run_p95": _nearest_rank(custos, 95),
            }
        )

    linhas.sort(key=lambda linha: linha["cost_per_run_p95"])
    if linhas:
        barato = linhas[0]["cost_per_run_p95"]
        for linha in linhas:
            linha["cost_relative"] = (
                linha["cost_per_run_p95"] / barato if barato else None
            )
    return linhas, recusas


def build_finops_report(
    facts: Sequence[Fact],
    *,
    job_name: str,
    findings: Sequence[Any] = (),
) -> dict[str, Any]:
    """Compoe o relatorio financeiro a partir de facts ja extraidos."""
    runs = [
        f
        for f in facts
        if f.kind == "glue.job_run" and f.subject.get("job_name") == job_name
    ]
    custos = extract_run_cost(runs, "<facts>")
    custo_por_run = {
        str(c.subject.get("job_run_id")): float(c.measures["cost"])
        for c in custos
        if c.kind == "glue.run_cost"
    }

    frontier, recusas = _frontier(runs, custo_por_run)
    return {
        "job_name": job_name,
        "currency": next(
            (c.attrs["currency"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "region": next(
            (c.attrs["region"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "runtime_version": next(
            (c.attrs["runtime_version"] for c in custos if c.kind == "glue.run_cost"),
            "",
        ),
        "frontier": frontier,
        "refused": recusas,
    }
