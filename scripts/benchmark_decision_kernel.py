#!/usr/bin/env python3
"""Run the offline bounded-decision synthetic baseline.

The report records local latency and payload bytes only. Provider token counts
and financial cost stay explicitly unresolved unless a separate host transcript
is supplied by a future, out-of-band measurement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sparkforge.decision import (  # noqa: E402
    BoundedDecisionKernel,
    ContractLoader,
    DecisionCache,
)


def run_fixture(repo: Path, fixture: Path) -> dict[str, Any]:
    raw = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("decision kernel fixture must use schema_version 1")
    cases = raw.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("decision kernel fixture must contain cases")
    rows: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("fixture case must be an object")
        contract = ContractLoader(repo).parse(case["contract"])
        cache = DecisionCache(contract.cache_max_entries)
        kernel = BoundedDecisionKernel(cache=cache)
        repeats = int(case.get("repeat", 1))
        if repeats < 1:
            raise ValueError(f"invalid repeat for {case.get('id')}")
        evaluations = []
        for _ in range(repeats):
            started = perf_counter_ns()
            evaluation = kernel.evaluate(
                contract, case.get("state", {}), now="2026-09-28T00:00:00Z"
            )
            elapsed = perf_counter_ns() - started
            evaluations.append((evaluation, elapsed))
        evaluation, elapsed = evaluations[-1]
        result = evaluation.result
        expected_status = str(case["expected_status"])
        expected_selected = tuple(str(item) for item in case.get("expected_selected", []))
        passed = result.status.value == expected_status
        if expected_selected:
            passed = passed and result.selected == expected_selected
        if case.get("expected_reason") is not None:
            passed = passed and result.reason == str(case["expected_reason"])
        rows.append(
            {
                "id": str(case["id"]),
                "status": result.status.value,
                "selected": list(result.selected),
                "reason": result.reason,
                "fingerprint": result.fingerprint,
                "cache_hit": result.cache_hit,
                "latency_ns": elapsed,
                "payload_bytes": evaluation.measurement.payload_bytes,
                "provider_tokens": None,
                "tokens_unresolved": True,
                "cost_basis": None,
                "passed": passed,
            }
        )
    passed = sum(1 for row in rows if row["passed"])
    return {
        "schema_version": 1,
        "suite_id": str(raw.get("suite_id", "decision-kernel")),
        "total_cases": len(rows),
        "passed_cases": passed,
        "failed_cases": len(rows) - passed,
        "provider_tokens": None,
        "tokens_unresolved": True,
        "cost_basis": None,
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--fixture", default="evals/token_efficient/fixtures/decision_kernel_cases.yaml"
    )
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    report = run_fixture(Path(args.repo).resolve(), Path(args.fixture).resolve())
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
