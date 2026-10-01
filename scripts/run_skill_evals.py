#!/usr/bin/env python3
"""Run deterministic, provider-free checks for the skill eval catalog."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_skills import audit
from scripts.check_skill_evals import check_one

SKILLS = ROOT / "skills"


def run() -> dict:
    skill_dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    audit_errors = [f"{item.skill}: {item.message}" for item in audit()]
    eval_errors = [error for path in skill_dirs for error in check_one(path)]
    cases = []
    for path in skill_dirs:
        payload = json.loads((path / "evals" / "evals.json").read_text(encoding="utf-8"))
        for case in payload["evals"]:
            cases.append({"skill": path.name, "id": case["id"], "passed": not audit_errors and not eval_errors})
    passed = sum(case["passed"] for case in cases)
    return {
        "mode": "offline_contract",
        "provider_calls": 0,
        "aws_calls": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills": len(skill_dirs),
        "cases": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "audit_errors": audit_errors,
        "eval_errors": eval_errors,
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="required explicit mode; no provider is contacted")
    parser.add_argument("--out", type=Path, help="write JSON report")
    args = parser.parse_args()
    if not args.offline:
        parser.error("only --offline is supported by the repository runner")
    report = run()
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized, encoding="utf-8")
    print(f"{report['passed']}/{report['cases']} cases passed; provider_calls=0; aws_calls=0")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
