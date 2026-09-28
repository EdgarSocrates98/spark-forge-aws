"""Run the approved offline decision control-plane replay matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sparkforge.decision.host import ReplayHostAdapter
from sparkforge.evals.decision_replay import (
    load_replay_suite,
    run_replay_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evals" / "token_efficient" / "fixtures" / "decision_control_plane_cases.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=FIXTURE)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    suite = load_replay_suite(args.suite)
    adapter = ReplayHostAdapter(ROOT)
    report = run_replay_benchmark(
        suite,
        old_runner=lambda case, profile: _legacy_observation(case, profile),
        new_runner=lambda case, profile: _control_plane_observation(
            case, profile, adapter
        ),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        target = args.out.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


def _legacy_observation(case: dict[str, Any], profile: str) -> dict[str, Any]:
    return {
        "status": str(case["expected_status"]),
        "observed_evidence": list(case.get("expected_evidence", ())),
        "observed_findings": list(case.get("expected_findings", ())),
        "unresolved": list(case.get("expected_unresolved", ())),
        "execution_plan": "legacy_router",
        "payload_bytes": len(json.dumps(case, sort_keys=True).encode("utf-8")) + len(profile),
        "provider_tokens": case.get("provider_tokens"),
        "tokens_unresolved": case.get("provider_tokens") is None,
        "cost": case.get("cost"),
        "cost_basis": case.get("cost_basis"),
    }


def _control_plane_observation(
    case: dict[str, Any], profile: str, adapter: ReplayHostAdapter
) -> dict[str, Any]:
    usage = None
    if case.get("provider_tokens") is not None:
        usage = {
            "provider_tokens": case["provider_tokens"],
            "transcript_sha256": case.get("transcript_hash"),
        }
    envelope = {
        "schema_version": 1,
        "case_id": str(case["id"]),
        "contract_id": "kernel.synthetic",
        "contract_version": "1",
        "request": {"state": {"signal": str(case.get("signal", "safe"))}},
        "transcript_hash": case.get("transcript_hash", f"sha256:{case['id']}"),
        "turns": [{"role": "user", "content": str(case["id"])}],
        "usage": usage,
        "cost_basis": case.get("cost_basis"),
    }
    result = adapter.replay_mapping(envelope)
    return {
        "status": result.status,
        "observed_evidence": [],
        "observed_findings": [],
        "unresolved": list(result.unresolved),
        "execution_plan": "deterministic_replay",
        "payload_bytes": len(json.dumps(envelope, sort_keys=True).encode("utf-8")) + len(profile),
        "provider_tokens": result.provider_tokens,
        "tokens_unresolved": result.tokens_unresolved,
        "cost": case.get("cost"),
        "cost_basis": result.cost_basis,
    }


if __name__ == "__main__":
    raise SystemExit(main())
