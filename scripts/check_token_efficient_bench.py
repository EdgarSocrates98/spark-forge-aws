"""Validate the token-efficient benchmark registry without making claims."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "token_efficient" / "suite.yaml"
PROFILES = {"economy", "balanced", "deep"}


def main() -> int:
    raw = yaml.safe_load(SUITE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        print("invalid benchmark schema_version")
        return 1
    baseline = raw.get("baseline_id")
    cases = raw.get("cases")
    if not isinstance(baseline, str) or not baseline or not isinstance(cases, list) or not cases:
        print("benchmark requires baseline_id and non-empty cases")
        return 1
    profiles = raw.get("profiles")
    if set(profiles or ()) != PROFILES:
        print("benchmark profiles must be economy, balanced and deep")
        return 1
    fixture_name = raw.get("quality_fixture")
    fixture_path = SUITE.parent / str(fixture_name or "")
    if not fixture_path.is_file():
        print("benchmark quality fixture is missing")
        return 1
    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    fixture_cases = fixture.get("cases") if isinstance(fixture, dict) else None
    if not isinstance(fixture_cases, list):
        print("benchmark quality fixture requires cases")
        return 1
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or len(set(ids)) != len(ids):
        print("benchmark case ids must be unique")
        return 1
    fixture_ids = {case.get("id") for case in fixture_cases if isinstance(case, dict)}
    if set(ids) != fixture_ids:
        print("suite and quality fixture case ids must match")
        return 1
    for case in cases:
        if not isinstance(case, dict):
            print("benchmark cases must be objects")
            return 1
        if not isinstance(case.get("max_bytes"), int) or case["max_bytes"] <= 0:
            print(f"invalid max_bytes: {case.get('id')}")
            return 1
        for field in ("expected_evidence", "expected_unresolved"):
            if not isinstance(case.get(field), list):
                print(f"{field} must be a list: {case.get('id')}")
                return 1
    print(json.dumps({"suite": raw["id"], "baseline_id": baseline, "cases": len(cases)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
