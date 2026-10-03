"""Regenerate streaming pipeline facts/findings goldens from fixture inputs."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.streaming_pipeline import build_streaming_pipeline
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_pipeline"


def regenerate(directory: Path) -> None:
    payloads = json.loads((directory / "input/facts.json").read_text(encoding="utf-8"))
    facts = [Fact(**payload) for payload in payloads]
    contract = json.loads((directory / "input/contract.json").read_text(encoding="utf-8"))
    derived = sort_facts(build_streaming_pipeline(facts, contract))
    findings = judge(derived, load_catalog(), {})
    (directory / "expected/facts.json").write_text(
        json.dumps([fact.to_dict() for fact in derived], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (directory / "expected/findings.json").write_text(
        json.dumps([finding.to_dict() for finding in findings], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    for fixture in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        regenerate(fixture)
        print(f"regenerated {fixture.name}")
