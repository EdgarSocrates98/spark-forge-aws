from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from sparkforge.evals.evidence import EvaluationEvidenceBundle
from sparkforge.evals.evidence_adapters import (
    AuthorizedCommandAdapter,
    BundleFileAdapter,
    EvidenceAdapterError,
)

HASH = "0" * 64


def _bundle() -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate": {
            "id": "candidate",
            "version": "1",
            "candidate_digest": HASH,
            "parent_digest": HASH,
            "family": "prompt",
            "kind": "prompt",
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
        "execution": {
            "mode": "live_external",
            "adapter": "authorized_command",
            "command_id": "fixture",
            "producer_identity": "fixture-producer-v1",
        },
        "transcripts": {"baseline": None, "candidate": None},
        "reports": {"baseline": {}, "candidate": {}},
        "metrics": {"comparison": {}, "quality": {}, "economy": {}},
        "policy": {"policy_id": "p", "policy_version": "v1", "policy_sha256": HASH},
        "evidence_refs": [],
        "rollback_target": HASH,
        "unresolved": [],
    }


def test_authorized_command_returns_same_canonical_bundle(tmp_path: Path) -> None:
    script = tmp_path / "emit_bundle.py"
    script.write_text(
        "import json\n"
        "print(json.dumps(" + repr(_bundle()).replace("'", '"') + "))\n",
        encoding="utf-8",
    )
    executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    artifact_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    adapter = AuthorizedCommandAdapter(
        {
            "fixture": {
                "executable": sys.executable,
                "executable_sha256": executable_sha256,
                "artifact": str(script),
                "artifact_sha256": artifact_sha256,
                "args": [str(script)],
            }
        },
        repo=tmp_path,
    )
    result = adapter.run("fixture")
    assert isinstance(result, EvaluationEvidenceBundle)
    assert result.execution_mode == "live_external"
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    assert result.to_dict() == BundleFileAdapter(tmp_path).load(bundle_path).to_dict()


def test_authorized_command_refuses_unknown_and_failed_commands(tmp_path: Path) -> None:
    adapter = AuthorizedCommandAdapter({}, repo=tmp_path)
    with pytest.raises(EvidenceAdapterError, match="not_authorized"):
        adapter.run("missing")

    script = tmp_path / "fail.py"
    script.write_text("raise SystemExit(3)\n", encoding="utf-8")
    executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    artifact_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    adapter = AuthorizedCommandAdapter(
        {
            "fail": {
                "executable": sys.executable,
                "executable_sha256": executable_sha256,
                "artifact": str(script),
                "artifact_sha256": artifact_sha256,
                "args": [str(script)],
            }
        },
        repo=tmp_path,
    )
    with pytest.raises(EvidenceAdapterError, match="exit_3"):
        adapter.run("fail")


def test_authorized_command_bounds_output_before_json_load(tmp_path: Path) -> None:
    script = tmp_path / "large.py"
    script.write_text("print('x' * 100)\n", encoding="utf-8")
    executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    artifact_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    adapter = AuthorizedCommandAdapter(
        {
            "large": {
                "executable": sys.executable,
                "executable_sha256": executable_sha256,
                "artifact": str(script),
                "artifact_sha256": artifact_sha256,
                "args": [str(script)],
                "max_output_bytes": 32,
            }
        },
        repo=tmp_path,
    )

    with pytest.raises(EvidenceAdapterError, match="output_too_large"):
        adapter.run("large")


def test_authorized_command_pins_artifact_and_rejects_runtime_args(tmp_path: Path) -> None:
    script = tmp_path / "identity.py"
    script.write_text("print('{}')\n", encoding="utf-8")
    executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    adapter = AuthorizedCommandAdapter(
        {
            "identity": {
                "executable": sys.executable,
                "executable_sha256": executable_sha256,
                "artifact": str(script),
                "artifact_sha256": "0" * 64,
                "args": [str(script)],
            }
        },
        repo=tmp_path,
    )

    with pytest.raises(EvidenceAdapterError, match="artifact_digest_mismatch"):
        adapter.run("identity")

    valid_artifact_sha256 = hashlib.sha256(script.read_bytes()).hexdigest()
    adapter.commands["identity"]["artifact_sha256"] = valid_artifact_sha256
    with pytest.raises(EvidenceAdapterError, match="identity_mismatch:runtime_args"):
        adapter.run("identity", argv=("mutable",))


def test_imported_adapter_has_no_provider_sdk_dependency() -> None:
    source = Path("sparkforge/evals/evidence_adapters.py").read_text(encoding="utf-8")
    assert all(name not in source for name in ("anthropic", "openai", "bedrock", "litellm"))
