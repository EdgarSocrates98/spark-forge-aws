"""SDD_EVAL: a suite agentica sobre specs, com gabarito recomputado pelo gate.

Cada teste cobre um criterio de `docs/sdd/SDD_EVAL/define.md`. As fixtures de
`fixtures/sdd/` sao repositorios sinteticos com o hash do upstream gravado em
arquivo versionado; por isso o `.gitattributes` as deixa fora da conversao de
quebra de linha.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASOS = ("limpo", "cascata", "cobertura", "tdd", "operador")


def test_fixtures_sem_conversao_de_quebra():
    texto = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "fixtures/sdd/** -text" in texto.splitlines()
    for caso in CASOS:
        assert (ROOT / "fixtures" / "sdd" / caso / "docs" / "sdd").is_dir(), caso
