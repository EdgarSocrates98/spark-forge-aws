"""Regenerate streaming-ops facts/findings goldens from their JSON contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.streaming_ops import extract_streaming_ops_path
from sparkforge.findings.models import sort_facts
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_ops"


def main() -> None:
    catalog = load_catalog()
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = sort_facts(
            extract_streaming_ops_path(directory / meta["artifact"], repo_root=directory / "input")
        )
        findings = judge(facts, catalog, {})
        expected = directory / "expected"
        expected.mkdir(exist_ok=True)
        (expected / "facts.json").write_text(
            json.dumps([fact.to_dict() for fact in facts], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (expected / "findings.json").write_text(
            json.dumps([finding.to_dict() for finding in findings], indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(directory.name, len(facts), len(findings))


if __name__ == "__main__":
    main()
