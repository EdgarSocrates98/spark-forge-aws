"""Resumo do `sparkforge scan`: o que rodou, o que saiu e o que foi recusado."""
from __future__ import annotations

from collections import Counter
from typing import Any

from sparkforge.scan.plan import Plano

SEVERIDADES = ("P0", "P1", "P2", "P3", "P4")


def gate(findings: list[dict[str, Any]], fail_on: str | None) -> dict[str, Any]:
    """`--fail-on P1` dispara com P0 ou P1, como no `report github`."""
    if fail_on is None:
        return {"fail_on": None, "tripped": False}
    alcance = set(SEVERIDADES[: SEVERIDADES.index(fail_on) + 1])
    return {"fail_on": fail_on, "tripped": any(f.get("severity") in alcance for f in findings)}


def resumo(
    plano: Plano,
    por_analyze: dict[str, dict[str, int]],
    falhas: list[dict[str, str]],
    facts_extraidos: int,
    facts_fundidos: int,
    findings: list[dict[str, Any]],
    runtime: dict[str, Any] | None,
    saidas: list[str],
    fail_on: str | None,
) -> dict[str, Any]:
    recusas = sorted(
        [*(r.to_dict() for r in plano.recusas), *falhas],
        key=lambda r: (r["reason"], r["path"]),
    )
    return {
        "dry_run": False,
        "plan": plano.to_dict(),
        "analyzes": {nome: dict(por_analyze[nome]) for nome in sorted(por_analyze)},
        "facts": {"extracted": facts_extraidos, "after_fuse": facts_fundidos},
        "findings": {
            "total": len(findings),
            "by_severity": dict(sorted(Counter(str(f.get("severity")) for f in findings).items())),
            "rule_ids": sorted({str(f.get("rule_id")) for f in findings}),
        },
        "refused": recusas,
        "refused_by_reason": dict(sorted(Counter(r["reason"] for r in recusas).items())),
        "runtime": runtime,
        "outputs": list(saidas),
        "gate": gate(findings, fail_on),
    }
