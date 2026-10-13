#!/usr/bin/env python3
"""Regenera somente goldens da primeira onda de Structured Streaming.

Use depois de uma mudança intencional no extrator ou no catálogo; revise o
diff dos arquivos gerados antes de commitar.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge_aws.facts.pyspark_ast import extract_tree
from sparkforge_aws.facts.runtime_detect import detect_runtime
from sparkforge_aws.facts.streaming import extract_streaming_progress_tree
from sparkforge_aws.findings.models import sort_facts
from sparkforge_aws.rules.engine import judge
from sparkforge_aws.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming"


def _run(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    if meta["artifact"] == "source":
        facts = extract_tree(input_dir, repo_root=input_dir)
        runtime_file = directory / "runtime.json"
        if runtime_file.exists():
            context, runtime_facts = detect_runtime(
                json.loads(runtime_file.read_text(encoding="utf-8"))
            )
            facts.extend(runtime_facts)
            runtime = context.to_dict()
        else:
            runtime = meta["runtime"]
    else:
        facts = extract_streaming_progress_tree(input_dir, repo_root=input_dir)
        runtime_file = directory / "runtime.json"
        if runtime_file.exists():
            context, runtime_facts = detect_runtime(
                json.loads(runtime_file.read_text(encoding="utf-8"))
            )
            facts.extend(runtime_facts)
            runtime = context.to_dict()
        else:
            runtime = meta["runtime"]
    facts = sort_facts(facts)
    findings = judge(facts, load_catalog(), runtime)
    return facts, findings


def main() -> None:
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        facts, findings = _run(directory)
        expected = directory / "expected"
        expected.mkdir(exist_ok=True)
        (expected / "facts.json").write_text(
            json.dumps([fact.to_dict() for fact in facts], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (expected / "findings.json").write_text(
            json.dumps(
                [finding.to_dict() for finding in findings], indent=2, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings")


if __name__ == "__main__":
    main()
