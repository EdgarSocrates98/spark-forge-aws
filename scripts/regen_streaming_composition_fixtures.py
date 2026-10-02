#!/usr/bin/env python3
"""Regenera goldens da composição streaming/transport/Iceberg offline."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_path
from sparkforge.facts.streaming import extract_streaming_progress_path
from sparkforge.facts.streaming_composition import build_streaming_composition
from sparkforge.facts.transport import extract_transport_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_composition"


def _facts(directory: Path):
    facts = []
    for path in sorted((directory / "input").iterdir()):
        if path.name == "progress.jsonl":
            facts.extend(extract_streaming_progress_path(path))
        elif path.name == "iceberg.json":
            facts.extend(extract_iceberg_metadata_path(path))
        elif path.name == "kafka.json":
            facts.extend(extract_transport_path(path, artifact_type="kafka"))
        elif path.name == "kinesis.json":
            facts.extend(extract_transport_path(path, artifact_type="kinesis"))
    return facts


def main() -> None:
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = build_streaming_composition(
            _facts(directory),
            mode=meta["mode"],
            table=meta.get("table", ""),
            query_name=meta.get("query_name", ""),
            transport_key=meta.get("transport_key", ""),
        )
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
