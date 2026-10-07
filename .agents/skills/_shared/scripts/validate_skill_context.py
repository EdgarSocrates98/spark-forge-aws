#!/usr/bin/env python3
"""Validate a recommendation envelope before a SparkForge skill hands it off.

The validator is deliberately offline and provider-independent. It checks the
stable contract, not domain correctness; domain correctness still needs the
SparkForge verbs and their fact/rule evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED = (
    "title",
    "severity",
    "confidence",
    "evidence",
    "root_cause",
    "proposed_change",
    "expected_effect",
    "risks",
    "tradeoffs",
    "validation",
    "rollback",
)


def validate(payload: Any, *, skill: str = "") -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["recommendation must be a mapping"]
    recommendation = payload.get("recommendation", payload)
    if not isinstance(recommendation, dict):
        return ["recommendation must be a mapping"]
    for key in REQUIRED:
        if key not in recommendation:
            errors.append(f"missing recommendation.{key}")
    evidence = recommendation.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("recommendation.evidence must be a non-empty list")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"recommendation.evidence[{index}] must be fact_id text")
    for key in ("proposed_change", "risks", "tradeoffs", "validation", "rollback"):
        value = recommendation.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"recommendation.{key} must be a non-empty list")
    if "expected_gain" in recommendation:
        errors.append("expected_gain is forbidden; use measured expected_effect")
    if skill and recommendation.get("skill") not in (None, skill):
        errors.append(f"recommendation.skill must be {skill!r} when present")
    return errors


def main(*, default_skill: str = "") -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON envelope")
    parser.add_argument("--skill", default=default_skill)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    errors = validate(payload, skill=args.skill)
    print(json.dumps({"ok": not errors, "skill": args.skill, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
