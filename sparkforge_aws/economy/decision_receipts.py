"""Content-addressed receipts for shadow routing observations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sparkforge_aws.case.store import state_path
from sparkforge_aws.economy.decision_models import (
    DecisionComparison,
    DecisionInput,
    DecisionResult,
)
from sparkforge_aws.receipt._hash import digest_of

RECEIPT_VERSION = 1
RECEIPT_PREFIX = "drec_"


class DecisionReceiptError(ValueError):
    """Named receipt persistence or integrity error."""


class DecisionReceipt:
    def __init__(self, receipt_id: str, path: Path, document: dict[str, Any]) -> None:
        self.receipt_id = receipt_id
        self.path = path
        self.document = document

    def to_dict(self) -> dict[str, Any]:
        return dict(self.document)


class DecisionReceiptStore:
    """Persist receipts under a repository-confined local directory."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.root = state_path(self.repo, "decision-receipts")

    def emit(
        self,
        request: DecisionInput,
        current: Any,
        result: DecisionResult,
        comparison: DecisionComparison,
        *,
        now: str | None = None,
        trace_ref: str | None = None,
        mode: str = "shadow",
        promoted: bool = False,
        fallback_route: str | None = None,
        rollback_reason: str | None = None,
        fallback_reason: str | None = None,
        authority: str | None = None,
        vetoed: bool | None = None,
        activation_evidence: dict[str, Any] | None = None,
        authority_decision: dict[str, Any] | None = None,
        candidate: dict[str, Any] | None = None,
    ) -> DecisionReceipt:
        body = {
            "receipt_version": RECEIPT_VERSION,
            "contract": {
                "contract_id": result.contract_id,
                "contract_version": result.contract_version,
                "contract_sha256": result.contract_sha256,
            },
            "input": request.canonical(),
            "input_sha256": digest_of(request.canonical()),
            "current": _current_dict(current),
            "shadow": result.to_dict(include_receipt=False),
            "kernel": {
                "fingerprint": result.fingerprint,
                "cache_hit": result.cache_hit,
                "evidence": list(result.evidence),
            },
            "comparison": comparison.to_dict(),
            "control": {
                "mode": mode,
                "promoted": promoted,
                "route": result.selected[0] if result.selected else None,
                "fallback_route": fallback_route,
                "rollback_reason": rollback_reason,
                "fallback_reason": fallback_reason,
            },
            "token_state": request.provider_usage.to_dict(),
            "trace_ref": trace_ref,
            "candidate": dict(candidate) if candidate is not None else None,
        }
        if authority is not None:
            body["authority"] = authority
        if vetoed is not None:
            body["legacy_vetoed"] = vetoed
        if activation_evidence is not None:
            body["activation_evidence"] = dict(activation_evidence)
        if authority_decision is not None:
            body["authority_decision"] = dict(authority_decision)
            body["policy_version"] = authority_decision.get("policy_version")
            body["calibration_version"] = authority_decision.get("calibration_version")
        receipt_id = RECEIPT_PREFIX + digest_of(body)
        document = dict(body)
        document["receipt_id"] = receipt_id
        document["emitted_at"] = now or datetime.now(timezone.utc).isoformat()
        document["shadow"] = result.with_receipt(receipt_id).to_dict()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{receipt_id}.json"
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise DecisionReceiptError(f"receipt_collision_unreadable: {path}") from exc
            if not isinstance(existing, dict) or _semantic_body(existing) != body:
                raise DecisionReceiptError(f"receipt_collision: {receipt_id}")
            return DecisionReceipt(receipt_id, path, existing)
        temporary = path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            raise DecisionReceiptError(f"receipt_write_failed: {path}") from exc
        return DecisionReceipt(receipt_id, path, document)

    def verify(self, receipt_path: Path | str) -> dict[str, Any]:
        path = Path(receipt_path).expanduser().resolve()
        if self.root not in path.parents:
            raise DecisionReceiptError("receipt_path_escape")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DecisionReceiptError(f"receipt_unreadable: {path}") from exc
        if not isinstance(document, dict):
            raise DecisionReceiptError("receipt_must_be_object")
        expected = RECEIPT_PREFIX + digest_of(_semantic_body(document))
        actual = document.get("receipt_id")
        return {
            "receipt_id": actual,
            "valid": actual == expected,
            "expected_receipt_id": expected,
            "status": "valid" if actual == expected else "integrity_failed",
        }

    def emit_recovery(
        self,
        request: DecisionInput,
        *,
        base_receipt_id: str,
        recovery: dict[str, Any],
        now: str | None = None,
    ) -> DecisionReceipt:
        body = {
            "receipt_version": RECEIPT_VERSION,
            "kind": "recovery",
            "base_receipt_id": base_receipt_id,
            "input_sha256": digest_of(request.canonical()),
            "recovery": recovery,
        }
        receipt_id = RECEIPT_PREFIX + digest_of(body)
        document = dict(body)
        document["receipt_id"] = receipt_id
        document["emitted_at"] = now or datetime.now(timezone.utc).isoformat()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{receipt_id}.recovery.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            return DecisionReceipt(receipt_id, path, existing)
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return DecisionReceipt(receipt_id, path, document)


def _semantic_body(document: dict[str, Any]) -> dict[str, Any]:
    body = {
        key: value for key, value in document.items() if key not in {"receipt_id", "emitted_at"}
    }
    shadow = body.get("shadow")
    if isinstance(shadow, dict):
        body["shadow"] = {key: value for key, value in shadow.items() if key != "receipt_id"}
    return body


def _current_dict(current: Any) -> dict[str, Any] | None:
    if current is None:
        return None
    if isinstance(current, str):
        return {"route": current}
    if isinstance(current, dict):
        return dict(current)
    to_dict = getattr(current, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value
    tier = getattr(current, "tier", None)
    profile = getattr(current, "profile", None)
    return {
        "route": str(getattr(tier, "value", tier)) if tier is not None else None,
        "profile": str(getattr(profile, "value", profile)) if profile is not None else None,
    }


__all__ = [
    "DecisionReceipt",
    "DecisionReceiptError",
    "DecisionReceiptStore",
]
