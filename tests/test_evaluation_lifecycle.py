from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sparkforge.evals.evolution import (
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
