"""Regenera goldens da composição Glue efetivo→Terraform."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.fusion import fuse
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_glue_cross_artifact"


def _facts(directory: Path) -> list[Fact]:
    items = [
        item
        for path in sorted((directory / "input").glob("*.json"))
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]
    return [
        Fact(
            kind=item["kind"],
            subject=item["subject"],
            measures=item.get("measures") or {},
            attrs=item.get("attrs") or {},
            provenance=item.get("provenance") or {},
            schema_version=item.get("schema_version", 1),
        )
        for item in items
    ]


def main() -> int:
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        facts = sort_facts(fuse(_facts(directory)))
        findings = judge(facts, load_catalog(), {})
        expected = directory / "expected"
        expected.mkdir(exist_ok=True)
        (expected / "facts.json").write_text(
            json.dumps([fact.to_dict() for fact in facts], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (expected / "findings.json").write_text(
            json.dumps([finding.to_dict() for finding in findings], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
