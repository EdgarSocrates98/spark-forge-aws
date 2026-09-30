from __future__ import annotations

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
        "execution": {"mode": "live_external", "adapter": "authorized_command"},
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
    adapter = AuthorizedCommandAdapter(
        {"fixture": {"executable": sys.executable, "args": [str(script)]}},
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
    adapter = AuthorizedCommandAdapter(
        {"fail": {"executable": sys.executable, "args": [str(script)]}},
        repo=tmp_path,
    )
    with pytest.raises(EvidenceAdapterError, match="exit_3"):
        adapter.run("fail")


def test_imported_adapter_has_no_provider_sdk_dependency() -> None:
    source = Path("sparkforge/evals/evidence_adapters.py").read_text(encoding="utf-8")
    assert all(name not in source for name in ("anthropic", "openai", "bedrock", "litellm"))
