#!/usr/bin/env python3
"""Regenera os golden outputs das fixtures.

Rode SOMENTE quando a mudanca de comportamento for intencional, e revise o diff:
o golden e a defesa contra falso positivo, e regenerar sem ler o diff a destroi.

Uso:
    python scripts/regen_fixtures.py            # todas
    python scripts/regen_fixtures.py coalesce_one
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.facts.pyspark_ast import extract_tree  # noqa: E402
from sparkforge.rules.engine import judge  # noqa: E402
from sparkforge.rules.loader import load_catalog  # noqa: E402

FIXTURES = ROOT / "fixtures" / "pyspark"


def regen(directory: Path) -> None:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])

    out = directory / "expected"
    out.mkdir(exist_ok=True)
    for name, payload in (
        ("facts.json", [f.to_dict() for f in facts]),
        ("findings.json", [f.to_dict() for f in findings]),
    ):
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        (out / name).write_text(text, encoding="utf-8")

    fired = ", ".join(sorted({f.rule_id for f in findings})) or "nenhum"
    print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings ({fired})")


def main() -> int:
    targets = sys.argv[1:]
    dirs = (
        [FIXTURES / name for name in targets]
        if targets
        else sorted(p for p in FIXTURES.iterdir() if p.is_dir())
    )
    for directory in dirs:
        regen(directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
