#!/usr/bin/env python3
"""Regenera goldens offline de CDC, Debezium/Kafka Connect e AWS DMS."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.cdc import extract_cdc_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "cdc"


def main() -> None:
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = extract_cdc_tree(directory / "input", artifact=meta["artifact"])
        findings = judge(facts, load_catalog(), {})
        expected = directory / "expected"
        expected.mkdir(exist_ok=True)
        (expected / "facts.json").write_text(
            json.dumps([fact.to_dict() for fact in facts], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (expected / "findings.json").write_text(
            json.dumps([finding.to_dict() for finding in findings], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings")


if __name__ == "__main__":
    main()
