from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sparkforge_aws.evals.evidence import EvaluationEvidenceBundle, EvidenceBundleError
from sparkforge_aws.evals.evidence_adapters import BundleFileAdapter
from sparkforge_aws.evals.evidence_resolver import EvidenceResolutionError, EvidenceResolver
from sparkforge_aws.evals.policy import EvaluationPolicyError, PolicyResolver

HASH = "0" * 64


def _raw_bundle() -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate": {
            "id": "candidate",
            "version": "1",
            "family": "prompt",
            "kind": "prompt",
            "candidate_digest": HASH,
            "parent_digest": HASH,
            "contract_id": "contract",
            "contract_version": "1",
            "contract_sha256": HASH,
        },
        "suite": {
            "suite_id": "suite",
            "suite_sha256": HASH,
            "input_manifest_sha256": HASH,
            "labeled_tasks": 50,
        },
        "execution": {"mode": "surrogate", "adapter": "fixture", "sequence": 1},
        "transcripts": {"baseline": None, "candidate": None},
        "reports": {"baseline": {}, "candidate": {}},
        "metrics": {"comparison": {}, "quality": {}, "economy": {}},
        "policy": {
            "policy_id": "policy",
            "policy_version": "v1",
            "policy_sha256": HASH,
        },
        "evidence_refs": [],
        "rollback_target": HASH,
        "unresolved": [],
    }


def test_bundle_canonicalizes_and_rejects_tampering() -> None:
    bundle = EvaluationEvidenceBundle.from_mapping(_raw_bundle())
    assert len(bundle.bundle_id) == 64
    assert bundle.to_dict()["bundle_id"] == bundle.bundle_id

    tampered = bundle.to_dict()
    tampered["candidate"] = {**bundle.candidate, "version": "2"}
    with pytest.raises(EvidenceBundleError, match="evidence_bundle_digest_mismatch"):
        EvaluationEvidenceBundle.from_mapping(tampered)


def test_bundle_rejects_invalid_transcript_and_live_adapter_shape() -> None:
    raw = _raw_bundle()
    raw["transcripts"] = {"candidate": {"sha256": "invalid", "source_ref": "host:x"}}
    with pytest.raises(EvidenceBundleError, match="transcripts.candidate.sha256"):
        EvaluationEvidenceBundle.from_mapping(raw)

    raw = _raw_bundle()
    raw["execution"] = {"mode": "live_external", "adapter": "bundle_file"}
    with pytest.raises(EvidenceBundleError, match="adapter_for_live_external"):
        EvaluationEvidenceBundle.from_mapping(raw)


def test_bundle_file_adapter_reads_json_and_rejects_escape(tmp_path: Path) -> None:
    raw = _raw_bundle()
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    bundle = BundleFileAdapter(tmp_path).load(path)
    assert bundle.candidate_digest == HASH
    with pytest.raises(EvidenceBundleError, match="path_escape"):
        BundleFileAdapter(tmp_path).load(tmp_path.parent / "outside.json")


def test_policy_resolver_requires_exact_key_and_no_default() -> None:
    resolver = PolicyResolver.from_mapping(
        {
            "policy_version": "v1",
            "policies": [
                {
                    "policy_id": "p",
                    "family": "prompt",
                    "kind": "prompt",
                    "contract_id": "contract",
                    "contract_version": "1",
                    "minimum_labeled_tasks": 2,
                }
            ],
        }
    )
    policy = resolver.resolve(
        type(
            "Candidate",
            (),
            {
                "family": "prompt",
                "kind": "prompt",
                "contract_id": "contract",
                "contract_version": "1",
            },
        )()
    )
    assert policy.minimum_labeled_tasks == 2
    with pytest.raises(EvaluationPolicyError, match="evaluation_policy_missing"):
        resolver.resolve(
            type(
                "Candidate",
                (),
                {
                    "family": "unknown",
                    "kind": "prompt",
                    "contract_id": "contract",
                    "contract_version": "1",
                },
            )()
        )


def test_recorded_host_requires_two_resolvable_transcripts(tmp_path: Path) -> None:
    raw = _raw_bundle()
    raw["execution"] = {"mode": "recorded_host", "adapter": "bundle_file"}
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=(),
        required_verified_evidence_kinds=(),
        evidence_roots=(),
    )

    with pytest.raises(EvidenceResolutionError, match="recorded_host_transcript_required"):
        EvidenceResolver(tmp_path).resolve(bundle, policy)


def test_metrics_are_compared_with_report_derived_values(tmp_path: Path) -> None:
    comparison = {
        "cells": [],
        "metrics": {
            "baseline": {"route_accuracy": 1.0},
            "candidate": {"route_accuracy": 1.0},
        },
    }
    raw = _raw_bundle()
    raw["reports"] = {
        "baseline": {"metrics": comparison["metrics"]["baseline"]},
        "candidate": {"metrics": comparison["metrics"]["candidate"]},
        "comparison": comparison,
    }
    raw["metrics"] = {"comparison": comparison, "quality": {}, "economy": {}}
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=(),
        required_verified_evidence_kinds=(),
        evidence_roots=(),
    )
    assert EvidenceResolver(tmp_path).resolve(bundle, policy).state == "verified"

    tampered = bundle.to_dict()
    tampered["metrics"] = {
        "comparison": {
            **comparison,
            "metrics": {
                **comparison["metrics"],
                "candidate": {"route_accuracy": 0.0},
            },
        },
        "quality": {},
        "economy": {},
    }
    tampered.pop("bundle_id")
    changed = EvaluationEvidenceBundle.from_mapping(tampered)
    with pytest.raises(EvidenceResolutionError, match="metrics_mismatch:comparison"):
        EvidenceResolver(tmp_path).resolve(changed, policy)


def test_unreported_metrics_are_not_authoritative(tmp_path: Path) -> None:
    raw = _raw_bundle()
    raw["reports"] = {
        "baseline": {"metrics": {"route_accuracy": 1.0}},
        "candidate": {"metrics": {"route_accuracy": 1.0}},
    }
    raw["metrics"] = {
        "comparison": {
            "metrics": {
                "baseline": {"route_accuracy": 1.0},
                "candidate": {"route_accuracy": 1.0},
            },
            "cells": [],
        },
        "quality": {"quality_score": 1.0},
        "economy": {},
    }
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=(),
        required_verified_evidence_kinds=(),
        evidence_roots=(),
    )
    with pytest.raises(EvidenceResolutionError, match="metrics_mismatch:quality"):
        EvidenceResolver(tmp_path).resolve(bundle, policy)


def test_evidence_refs_are_confined_to_kind_roots(tmp_path: Path) -> None:
    root = tmp_path / "evidence" / "ci"
    root.mkdir(parents=True)
    artifact = root / "ci.json"
    artifact.write_text("ci", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("outside", encoding="utf-8")
    raw = _raw_bundle()
    raw["evidence_refs"] = [
        {
            "kind": "ci",
            "ref": "file:ci.json",
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        }
    ]
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=(),
        required_verified_evidence_kinds=(),
        evidence_kind_roots=(("ci", ("evidence/ci",)),),
    )
    resolved = EvidenceResolver(tmp_path).resolve(bundle, policy)
    assert resolved.verified_refs == ("file:ci.json",)

    escaped = bundle.to_dict()
    escaped["evidence_refs"][0]["ref"] = "file:../../outside.json"
    escaped.pop("bundle_id")
    with pytest.raises(EvidenceResolutionError, match="path_escape"):
        EvidenceResolver(tmp_path).resolve(
            EvaluationEvidenceBundle.from_mapping(escaped), policy
        )


def test_evidence_kind_aliasing_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    artifact = root / "shared.json"
    artifact.write_text("shared", encoding="utf-8")
    raw = _raw_bundle()
    sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    raw["evidence_refs"] = [
        {"kind": "ci", "ref": "file:shared.json", "sha256": sha256},
        {"kind": "review", "ref": "file:shared.json", "sha256": sha256},
    ]
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=(),
        required_verified_evidence_kinds=(),
        evidence_kind_roots=(("ci", ("evidence",)), ("review", ("evidence",))),
    )
    with pytest.raises(EvidenceResolutionError, match="kind_aliasing"):
        EvidenceResolver(tmp_path).resolve(bundle, policy)


def test_unresolved_state_is_exposed_and_denied_by_policy(tmp_path: Path) -> None:
    raw = _raw_bundle()
    raw["unresolved"] = ["transcript_missing"]
    bundle = EvaluationEvidenceBundle.from_mapping(raw)
    policy = SimpleNamespace(
        unresolved_allow=(),
        unresolved_deny=("transcript_missing",),
        required_verified_evidence_kinds=(),
        evidence_roots=(),
    )
    resolved = EvidenceResolver(tmp_path).resolve(bundle, policy)
    assert resolved.state == "invalid"
    assert "transcript_missing" in resolved.blocking_unresolved
