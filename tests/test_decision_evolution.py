from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from sparkforge_aws.decision.fingerprint import digest
from sparkforge_aws.evals.decision_replay import (
    load_replay_suite,
    run_replay_benchmark,
    split_replay_benchmark,
)
from sparkforge_aws.evals.evidence import EvaluationEvidenceBundle
from sparkforge_aws.evals.evolution import (
    CandidateEvaluation,
    CandidateRegistry,
    CandidateSpec,
    CandidateStatus,
    EvolutionError,
    EvolutionService,
    _candidate_runner,
    transition,
)
from sparkforge_aws.evals.metric_compiler import compile_reports

ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_versioned_candidates_and_digest() -> None:
    candidates = CandidateRegistry(ROOT).load()
    baseline, variant = candidates
    assert baseline.status is CandidateStatus.ACCEPTED
    assert variant.parent_digest == baseline.candidate_digest
    assert variant.candidate_digest != variant.content_sha256
    assert len(variant.content_sha256) == 64
    assert len(variant.candidate_digest) == 64
    assert variant.to_dict()["content_sha256"] == variant.content_sha256
    assert variant.to_dict()["candidate_digest"] == variant.candidate_digest


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
authority:
  require_parent_digest_for_mutation: false
  require_content_digest: true
  require_contract_sha256: false
candidates:
  - id: bad
    version: '1'
    kind: prompt
    content: body
    candidate_digest: wrong
    contract_id: contract
    contract_version: '1'
    calibration_version: none
""",
        encoding="utf-8",
    )
    with pytest.raises(EvolutionError, match="candidate_digest_mismatch"):
        CandidateRegistry(tmp_path, registry).load()


def test_registry_pins_candidate_contract_to_loaded_contract(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "config", tmp_path / "config")
    registry = tmp_path / "config" / "evolution" / "prompt_agents.yaml"
    value = registry.read_text(encoding="utf-8").replace("6ab2bdd8", "0ab2bdd8")
    registry.write_text(value, encoding="utf-8")

    with pytest.raises(EvolutionError, match="candidate_contract_sha256_mismatch"):
        CandidateRegistry(tmp_path).load()


def test_candidate_type_requires_consistent_parent_identity() -> None:
    with pytest.raises(EvolutionError, match="candidate_parent_digest_required_for_mutation"):
        CandidateSpec(
            "mutation",
            "1",
            "prompt",
            "body",
            "contract",
            "1",
            "none",
            candidate_type="mutation",
        )
    with pytest.raises(EvolutionError, match="root_candidate_cannot_have_parent"):
        CandidateSpec(
            "root",
            "1",
            "prompt",
            "body",
            "contract",
            "1",
            "none",
            parent_digest="parent",
        )


def test_evaluation_receipt_and_rollback_are_local(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
        evidence_verified=True,
    )
    path = service._write(
        "evaluation", {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()}
    )
    assert json.loads(path.read_text(encoding="utf-8"))["receipt_id"] == path.stem
    with pytest.raises(EvolutionError, match="active_disabled_by_policy"):
        service.promote(candidate, evaluation, caller_authorized=True)


def test_evaluate_compares_accepted_parent_with_candidate_and_derives_gates(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")

    evaluation = service.evaluate(
        candidate,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
    )

    assert evaluation.gates_pass
    assert evaluation.gate_reasons == ()
    assert evaluation.comparison["candidates"]["baseline"]["candidate_digest"] == (
        candidate.parent_digest
    )
    assert evaluation.comparison["candidates"]["candidate"]["candidate_digest"] == (
        candidate.candidate_digest
    )
    assert (
        evaluation.economy_metrics["payload_bytes_mean"]
        != evaluation.economy_metrics["baseline_payload_bytes_mean"]
    )


def test_active_promotion_refuses_surrogate_evaluation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = service.evaluate(
        candidate,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
    )
    authority_path = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    authority_path.write_text(
        authority_path.read_text(encoding="utf-8").replace(
            "    enabled: false", "    enabled: true", 1
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvolutionError, match="surrogate_active_forbidden"):
        service.promote(candidate, evaluation, caller_authorized=True)


def test_active_promotion_checks_unverified_evidence_without_bundle_id(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
        execution_mode="recorded_host",
        bundle_id="declared-but-unverified",
        evidence_verified=False,
    )
    service._write(
        "evaluation", {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()}
    )
    authority_path = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    authority_path.write_text(
        authority_path.read_text(encoding="utf-8").replace(
            "    enabled: false", "    enabled: true", 1
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvolutionError, match="evidence_unverified"):
        service.promote(candidate, evaluation, caller_authorized=True)


def test_active_promotion_requires_all_policy_evidence_kinds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = CandidateEvaluation(
        candidate_digest=candidate.candidate_digest,
        suite_sha256="suite-sha",
        labeled_tasks=50,
        quality_gate=True,
        economy_gate=True,
        ci_verified=True,
        evidence_refs=("ci:holdout",),
        rollback_target=candidate.parent_digest or "",
        comparison={"cells": [], "metrics": {}},
        metrics_derived=True,
        execution_mode="recorded_host",
        verified_evidence_refs=("ci:holdout",),
        verified_evidence_kinds=("ci",),
        evidence_verified=True,
    )
    service._write(
        "evaluation", {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()}
    )
    authority_path = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    authority_path.write_text(
        authority_path.read_text(encoding="utf-8").replace(
            "    enabled: false", "    enabled: true", 1
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvolutionError, match="evidence_missing:benchmark,review"):
        service.promote(candidate, evaluation, caller_authorized=True)


def test_evaluate_derives_quality_failure_from_candidate_behavior(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    baseline = service.registry.get("routing-baseline")
    candidate = CandidateSpec(
        "routing-degraded",
        "1",
        "prompt",
        "evidence=none",
        baseline.contract_id,
        baseline.contract_version,
        baseline.calibration_version,
        parent_digest=baseline.candidate_digest,
        contract_sha256=baseline.contract_sha256,
        candidate_type="mutation",
    )

    evaluation = service.evaluate(
        candidate,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
    )

    assert evaluation.quality_gate is False
    assert "evidence_recall_below_threshold" in evaluation.gate_reasons
    assert evaluation.metrics_derived is True


def test_latest_evaluation_rejects_tampered_receipt(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    service.evaluate(candidate)
    receipt = next(path for path in service.root.iterdir() if path.suffix == ".json")
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["evaluation"]["quality_gate"] = False
    receipt.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(EvolutionError, match="evolution_receipt_digest_mismatch"):
        service.latest_evaluation(candidate)


def test_latest_evaluation_rejects_coercion_after_receipt_rehash(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    service.evaluate(candidate)
    receipt = next(path for path in service.root.iterdir() if path.suffix == ".json")
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["evaluation"]["quality_gate"] = "false"
    body = {key: value for key, value in document.items() if key != "receipt_id"}
    replacement = service.root / f"{digest(body)}.json"
    document["receipt_id"] = replacement.stem
    replacement.write_text(json.dumps(document), encoding="utf-8")
    receipt.unlink()

    with pytest.raises(EvolutionError, match="candidate_evaluation_invalid"):
        service.latest_evaluation(candidate)


def test_registry_policies_control_receipt_and_rollback_requirements(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    registry_path = repo / "config" / "evolution" / "prompt_agents.yaml"
    registry_path.write_text(
        registry_path.read_text(encoding="utf-8")
        .replace("  require_evaluation_receipt: true", "  require_evaluation_receipt: false")
        .replace("  require_rollback_target: true", "  require_rollback_target: false"),
        encoding="utf-8",
    )
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    evaluation = service.evaluate(
        candidate,
        ci_verified=True,
        evidence_refs=("benchmark:holdout",),
    )

    assert evaluation.rollback_required is False
    assert evaluation.rollback_target == ""
    assert evaluation.gates_pass

    shutil.rmtree(service.root)
    with pytest.raises(EvolutionError, match="active_disabled_by_policy"):
        service.promote(candidate, evaluation, caller_authorized=True)


def test_new_evaluation_binds_policy_bundle_and_sequence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copytree(ROOT / "evals", repo / "evals")
    service = EvolutionService(repo)
    candidate = service.registry.get("routing-variant")
    policy = service.registry.policy_for(candidate)
    suite = load_replay_suite(
        repo / "evals/token_efficient/fixtures/decision_control_plane_cases.yaml",
        minimum_labeled_tasks=policy.minimum_labeled_tasks,
    )
    service.evaluate(candidate, ci_verified=True, evidence_refs=("benchmark:fixture",))
    baseline = service.registry.get("routing-baseline")
    paired = run_replay_benchmark(
        suite,
        old_runner=_candidate_runner(baseline),
        new_runner=_candidate_runner(candidate),
        baseline_identity={
            "candidate_id": baseline.candidate_id,
            "version": baseline.version,
            "candidate_digest": baseline.candidate_digest,
        },
        candidate_identity={
            "candidate_id": candidate.candidate_id,
            "version": candidate.version,
            "candidate_digest": candidate.candidate_digest,
        },
    )
    baseline_report, candidate_report = split_replay_benchmark(paired)
    metrics = compile_reports(
        {"baseline": baseline_report, "candidate": candidate_report}, require_raw=True
    )
    input_manifest_sha256 = digest(
        [dict(case["input_manifest"]) for case in suite["cases"]]
    )
    raw = {
        "schema_version": 1,
        "candidate": {
            **candidate.to_dict(),
            "id": candidate.candidate_id,
            "version": candidate.version,
            "family": candidate.family,
            "candidate_digest": candidate.candidate_digest,
            "parent_digest": candidate.parent_digest,
            "contract_id": candidate.contract_id,
            "contract_version": candidate.contract_version,
            "contract_sha256": candidate.contract_sha256,
        },
        "suite": {
            "suite_id": suite["suite_id"],
            "suite_sha256": suite["sha256"],
            "input_manifest_sha256": input_manifest_sha256,
            "labeled_tasks": suite["labeled_tasks"],
        },
        "execution": {"mode": "recorded_host", "adapter": "fixture", "sequence": 1},
        "transcripts": {"baseline": None, "candidate": None},
        "reports": {
            "baseline": baseline_report,
            "candidate": candidate_report,
        },
        "metrics": metrics,
        "policy": {
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
            "policy_sha256": policy.policy_sha256,
        },
        "evidence_refs": [],
        "rollback_target": candidate.parent_digest,
        "unresolved": [],
    }
    transcript_root = repo / ".sparkforge" / "evidence" / "ci"
    transcript_root.mkdir(parents=True, exist_ok=True)
    for side in ("baseline", "candidate"):
        transcript = transcript_root / f"{side}-transcript.json"
        transcript.write_text(side, encoding="utf-8")
        raw["transcripts"][side] = {
            "source_ref": f"file:{transcript.name}",
            "sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        }
    for kind in ("ci", "benchmark", "review"):
        root = (
            repo / ".sparkforge" / "evidence" / ("reviews" if kind == "review" else kind)
            if kind != "benchmark"
            else repo / "evals" / "token_efficient" / "fixtures"
        )
        root.mkdir(parents=True, exist_ok=True)
        artifact = root / f"{kind}-evidence.json"
        artifact.write_text(kind, encoding="utf-8")
        raw["evidence_refs"].append(
            {
                "kind": kind,
                "ref": f"file:{kind}-evidence.json",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        )
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    second = service.evaluate(bundle=bundle, candidate=candidate, ci_verified=True)
    assert second.bundle_id == bundle.bundle_id
    assert second.policy_sha256 == policy.policy_sha256
    assert set(second.evidence_ref_kinds) == {"ci", "benchmark", "review"}
    authority_path = repo / "config" / "decisions" / "agentic_control_plane.yaml"
    authority_path.write_text(
        authority_path.read_text(encoding="utf-8").replace(
            "    enabled: false", "    enabled: true", 1
        ),
        encoding="utf-8",
    )
    accepted = service.promote(candidate, second, caller_authorized=True)
    assert accepted.status is CandidateStatus.ACCEPTED
    receipts = [path for path in service.root.glob("*.json")]
    assert len(receipts) == 3
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    assert sorted(document["event_sequence"] for document in documents) == [1, 2, 3]
    assert all(document["policy_sha256"] for document in documents)
    promotion = next(document for document in documents if document["action"] == "promotion")
    assert promotion["provenance"]["policy_id"] == policy.policy_id
    assert promotion["provenance"]["evaluation_receipt_id"]
