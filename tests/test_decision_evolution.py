from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sparkforge.evals.evolution import (
    CandidateEvaluation,
    CandidateRegistry,
    CandidateSpec,
    CandidateStatus,
    EvolutionError,
    EvolutionService,
    transition,
)

ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_versioned_candidates_and_digest() -> None:
    candidates = CandidateRegistry(ROOT).load()
    baseline, variant = candidates
    assert baseline.status is CandidateStatus.ACCEPTED
    assert variant.parent_digest == baseline.content_sha256
    assert len(variant.content_sha256) == 64
    assert variant.to_dict()["content_sha256"] == variant.content_sha256


def test_lifecycle_has_explicit_edges() -> None:
    assert (
        transition(CandidateStatus.CANDIDATE, CandidateStatus.EVALUATED)
        is CandidateStatus.EVALUATED
    )
    candidate = CandidateSpec(
        "candidate",
        "1",
        "prompt",
        "body",
        "contract",
        "1",
        "none",
    )
    evaluated = transition(candidate, CandidateStatus.EVALUATED)
    assert evaluated.status is CandidateStatus.EVALUATED
    with pytest.raises(EvolutionError, match="invalid_candidate_transition"):
        transition(candidate, CandidateStatus.ACCEPTED)


def test_registry_rejects_content_digest_mismatch(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """
schema_version: 1
registry_id: test
benchmark_suite: fixture.yaml
require_domain_holdout: true
authority: {require_parent_digest_for_mutation: false, require_content_digest: true}
candidates:
  - id: bad
    version: '1'
    kind: prompt
    content: body
    content_sha256: wrong
    contract_id: contract
    contract_version: '1'
    calibration_version: none
""",
        encoding="utf-8",
    )
    with pytest.raises(EvolutionError, match="content_digest_mismatch"):
        CandidateRegistry(tmp_path, registry).load()


def test_evaluation_receipt_and_rollback_are_local(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_sha256=candidate.content_sha256,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
        rollback_target="restore-baseline",
        comparison={"cells": []},
    )
    path = service._write(
        "evaluation", {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()}
    )
    assert json.loads(path.read_text(encoding="utf-8"))["receipt_id"] == path.stem
    with pytest.raises(EvolutionError, match="active_disabled_by_policy"):
        service.promote(candidate, evaluation, caller_authorized=True)
