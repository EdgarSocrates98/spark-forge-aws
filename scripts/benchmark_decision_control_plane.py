"""Run the approved offline decision control-plane replay matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sparkforge.decision.fingerprint import digest
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
        "transcript_hash": case.get("transcript_hash"),
        "cost": case.get("cost"),
        "cost_basis": case.get("cost_basis"),
    }


def _control_plane_observation(
    case: dict[str, Any], profile: str, adapter: ReplayHostAdapter
) -> dict[str, Any]:
    turns = [{"role": "user", "content": str(case["id"])}]
    request = {"state": {"signal": str(case.get("signal", "safe"))}}
    transcript_payload = {
        "schema_version": 1,
        "case_id": str(case["id"]),
        "contract_id": "kernel.synthetic",
        "contract_version": "1",
        "request": request,
        "turns": turns,
    }
    transcript_hash = digest(transcript_payload)
    usage = None
    if case.get("provider_tokens") is not None:
        usage = {
            "provider_tokens": case["provider_tokens"],
            "transcript_sha256": transcript_hash,
        }
    envelope = {
        "schema_version": 1,
        "case_id": str(case["id"]),
        "contract_id": "kernel.synthetic",
        "contract_version": "1",
        "request": request,
        "transcript_hash": transcript_hash,
        "turns": turns,
        "usage": usage,
        "cost_basis": case.get("cost_basis"),
    }
    result = adapter.replay_mapping(envelope)
    return {
        "status": result.status,
        "observed_evidence": [],
        "observed_findings": [],
        "actual_route": _selected_route(result.semantic_result),
        "unresolved": list(result.unresolved),
        "execution_plan": "deterministic_replay",
        "payload_bytes": len(json.dumps(envelope, sort_keys=True).encode("utf-8")) + len(profile),
        "provider_tokens": result.provider_tokens,
        "tokens_unresolved": result.tokens_unresolved,
        "transcript_hash": result.transcript_sha256,
        "cost": case.get("cost"),
        "cost_basis": result.cost_basis,
    }


def _selected_route(semantic_result: dict[str, Any] | None) -> str | None:
    if not isinstance(semantic_result, dict):
        return None
    selected = semantic_result.get("selected")
    if isinstance(selected, (list, tuple)) and selected:
        return str(selected[0])
    return None


if __name__ == "__main__":
    raise SystemExit(main())
