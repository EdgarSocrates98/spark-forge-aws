"""Regenerate event-driven golden facts/findings from committed inputs."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.facts.event_driven import extract_event_driven_path
from sparkforge.findings.models import sort_facts
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for directory in sorted((ROOT / "fixtures/event_driven").iterdir()):
        if not directory.is_dir():
            continue
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        facts = sort_facts(
            extract_event_driven_path(directory / meta["artifact"], repo_root=directory / "input")
        )
        findings = judge(facts, load_catalog(), {})
        (directory / "expected").mkdir(exist_ok=True)
        (directory / "expected/facts.json").write_text(
            json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        (directory / "expected/findings.json").write_text(
            json.dumps([f.to_dict() for f in findings], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(directory.name, len(facts), len(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
