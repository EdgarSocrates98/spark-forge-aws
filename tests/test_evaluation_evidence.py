from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.evals.evidence import EvaluationEvidenceBundle, EvidenceBundleError
from sparkforge.evals.evidence_adapters import BundleFileAdapter
from sparkforge.evals.policy import EvaluationPolicyError, PolicyResolver

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
