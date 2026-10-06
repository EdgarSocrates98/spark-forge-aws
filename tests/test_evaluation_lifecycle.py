from __future__ import annotations

import json
import shutil
import socket
import time
from pathlib import Path

import pytest

from sparkforge_aws.decision.fingerprint import digest
from sparkforge_aws.evals.evolution import (
    CandidateEvaluation,
    CandidateStatus,
    EvolutionError,
    EvolutionService,
)

ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path: Path) -> EvolutionService:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    return EvolutionService(repo)


def test_effective_lifecycle_survives_service_restart(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:fixture",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
    )
    service._write(
        "evaluation",
        {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()},
    )
    accepted = {**candidate.to_dict(), "status": CandidateStatus.ACCEPTED.value}
    service._write("promotion", {"candidate": accepted, "evaluation": evaluation.to_dict()})

    restarted = EvolutionService(service.repo)
    state = restarted.effective_candidate("routing-variant")

    assert state.effective_status is CandidateStatus.ACCEPTED
    assert state.last_sequence == 2


def test_effective_lifecycle_refuses_missing_sequence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:fixture",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
    )
    first = service._write(
        "evaluation",
        {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()},
    )
    accepted = {**candidate.to_dict(), "status": CandidateStatus.ACCEPTED.value}
    second = service._write(
        "promotion", {"candidate": accepted, "evaluation": evaluation.to_dict()}
    )
    first.unlink()

    with pytest.raises(EvolutionError, match="receipt_sequence_gap"):
        service.effective_candidate(candidate)

    assert not first.exists()
    assert json.loads(second.read_text(encoding="utf-8"))["event_sequence"] == 2


def test_stale_receipt_lock_is_recovered_only_when_pid_is_absent(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.registry._receipt_lock = {
        "stale_after_seconds": 1,
        "recovery": "pid_absent_after_threshold",
    }
    service.root.mkdir(parents=True, exist_ok=True)
    lock = service.root / ".receipt.lock"
    lock.write_text(
        json.dumps(
            {
                "pid": 999999,
                "created_at": time.time() - 10,
                "hostname": socket.gethostname(),
                "process_start_fingerprint": None,
            }
        ),
        encoding="utf-8",
    )
    service._write("diagnostic", {"candidate_id": "routing-variant"})
    assert service._last_receipt_lock_state == "lock_recovered"
    assert not lock.exists()


def test_unverifiable_receipt_lock_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.root.mkdir(parents=True, exist_ok=True)
    lock = service.root / ".receipt.lock"
    lock.write_text("{}", encoding="utf-8")
    with pytest.raises(EvolutionError, match="lock_unverifiable"):
        service._write("diagnostic", {"candidate_id": "routing-variant"})
    assert lock.exists()


def test_legacy_evaluation_receipt_is_audit_only(tmp_path: Path) -> None:
    service = _service(tmp_path)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:fixture",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
        evidence_verified=True,
    )
    body = {
        "schema_version": 1,
        "action": "evaluation",
        "candidate_id": candidate.candidate_id,
        "candidate": candidate.to_dict(),
        "evaluation": evaluation.to_dict(),
    }
    receipt_id = digest(body)
    (service.root / f"{receipt_id}.json").parent.mkdir(parents=True, exist_ok=True)
    (service.root / f"{receipt_id}.json").write_text(
        json.dumps({**body, "receipt_id": receipt_id}), encoding="utf-8"
    )
    assert service.lifecycle.receipt_status() == {
        "authoritative": (),
        "legacy": (receipt_id,),
    }
    with pytest.raises(EvolutionError, match="legacy_not_authoritative"):
        service.latest_evaluation(candidate)
