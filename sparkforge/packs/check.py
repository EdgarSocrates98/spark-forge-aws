"""`pack check`: cada regra do pack precisa disparar no fixture que a declara.

E o contrato dos goldens do core (toda regra tem golden que dispara) aplicado
ao pack. Este modulo so le os casos e compara; quem julga e o adapter, que ja
sabe carregar facts e detectar runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.packs.load import Pack
from sparkforge.packs.manifest import PackRefused
from sparkforge.paths import resolve_within


@dataclass(frozen=True)
class Case:
    name: str
    facts_path: Path
    expected: frozenset[str]


def cases(pack: Pack) -> list[Case]:
    base = pack.root / "fixtures"
    if not base.is_dir():
        return []
    saida = []
    for entrada in sorted(p for p in base.iterdir() if p.is_dir()):
        caso = resolve_within(base, entrada.name)
        fatos = resolve_within(caso, "facts.json") if caso else None
        expect = resolve_within(caso, "expect.yaml") if caso else None
        if caso is None or fatos is None or expect is None or not fatos.is_file():
            detalhe = f"fixtures/{entrada.name} sem facts.json"
            raise PackRefused("regra_invalida", detalhe, pack.id)
        documento = {}
        if expect.is_file():
            documento = yaml.safe_load(expect.read_text(encoding="utf-8-sig"))
        fires = (documento or {}).get("fires") or []
        saida.append(Case(entrada.name, fatos, frozenset(str(r) for r in fires)))
    return saida


def evaluate(
    pack: Pack, fired_by_case: dict[str, set[str]], all_cases: list[Case]
) -> dict[str, Any]:
    """Compara o que disparou (so as regras do pack) com o que cada caso declara."""
    resultados = []
    provadas: set[str] = set()
    prefixo = f"{pack.prefix}-"
    for caso in all_cases:
        disparou = {r for r in fired_by_case.get(caso.name, set()) if r.startswith(prefixo)}
        provadas |= disparou & caso.expected
        resultados.append(
            {
                "case": caso.name,
                "expected": sorted(caso.expected),
                "fired": sorted(disparou),
                "ok": disparou == set(caso.expected),
            }
        )
    sem_fixture = sorted(str(r["id"]) for r in pack.rules if str(r["id"]) not in provadas)
    return {
        "pack": {"id": pack.id, "version": pack.manifest.version, "prefix": pack.prefix},
        "cases": resultados,
        "rules_without_fixture": sem_fixture,
        "ok": all(r["ok"] for r in resultados) and not sem_fixture,
    }
