"""Compact content-addressed receipts for generic decisions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sparkforge.decision.fingerprint import digest
from sparkforge.decision.models import DecisionResult, LocalMeasurement

RECEIPT_VERSION = 1
RECEIPT_PREFIX = "dkr_"


class ReceiptValidationError(ValueError):
    """Receipt schema or integrity failure."""


def build_receipt(
    result: DecisionResult,
    *,
    state_fingerprint: str,
    measurement: LocalMeasurement,
    emitted_at: str | None = None,
    mode: str = "shadow",
    promoted: bool = False,
    fallback_route: str | None = None,
    rollback_reason: str | None = None,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    refusal = None
    if result.status.value != "accepted":
        refusal = {"kind": result.status.value, "reason": result.reason}
    body = {
        "schema_version": RECEIPT_VERSION,
        "contract": {
            "contract_id": result.contract_id,
            "contract_version": result.contract_version,
            "contract_sha256": result.contract_sha256,
        },
        "fingerprint": result.fingerprint,
        "state_fingerprint": state_fingerprint,
        "result": result.to_dict(),
        "method": result.method,
        "confidence": result.confidence,
        "evidence": list(result.evidence),
        "refusal": refusal,
        "cache": {"hit": result.cache_hit},
        "control": {
            "mode": mode,
            "promoted": promoted,
            "route": result.selected[0] if result.selected else None,
            "fallback_route": fallback_route,
            "rollback_reason": rollback_reason,
            "fallback_reason": fallback_reason,
        },
        "measurement": measurement.to_dict(),
    }
    receipt_id = RECEIPT_PREFIX + digest(body)
    document = dict(body)
    document["receipt_id"] = receipt_id
    document["emitted_at"] = emitted_at or datetime.now(timezone.utc).isoformat()
    return document


def verify_receipt(document: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "receipt_id",
        "contract",
        "fingerprint",
        "state_fingerprint",
        "result",
        "method",
        "confidence",
        "evidence",
        "refusal",
        "cache",
        "measurement",
    }
    missing = sorted(required - set(document))
    if missing:
        raise ReceiptValidationError(f"receipt_missing_fields: {', '.join(missing)}")
    body = {
        key: value for key, value in document.items() if key not in {"receipt_id", "emitted_at"}
    }
    expected = RECEIPT_PREFIX + digest(body)
    actual = document.get("receipt_id")
    return {
        "receipt_id": actual,
        "expected_receipt_id": expected,
        "valid": actual == expected,
        "status": "valid" if actual == expected else "integrity_failed",
    }


class KernelReceiptStore:
    """Persist generic receipts under the existing local decision directory."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.root = self.repo / ".sparkforge" / "decision-receipts"

    def emit(
        self,
        result: DecisionResult,
        *,
        state_fingerprint: str,
        measurement: LocalMeasurement,
        now: str | None = None,
        mode: str = "shadow",
        promoted: bool = False,
        fallback_route: str | None = None,
        rollback_reason: str | None = None,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        document = build_receipt(
            result,
            state_fingerprint=state_fingerprint,
            measurement=measurement,
            emitted_at=now,
            mode=mode,
            promoted=promoted,
            fallback_route=fallback_route,
            rollback_reason=rollback_reason,
            fallback_reason=fallback_reason,
        )
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{document['receipt_id']}.kernel.json"
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ReceiptValidationError(f"receipt_collision_unreadable: {path}") from exc
            if existing != document:
                raise ReceiptValidationError(f"receipt_collision: {document['receipt_id']}")
            return existing
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return document

    def verify(self, path: Path | str) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        if self.root not in target.parents:
            raise ReceiptValidationError("receipt_path_escape")
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReceiptValidationError(f"receipt_unreadable: {target}") from exc
        if not isinstance(document, dict):
            raise ReceiptValidationError("receipt_must_be_object")
        return verify_receipt(document)


__all__ = [
    "KernelReceiptStore",
    "RECEIPT_PREFIX",
    "RECEIPT_VERSION",
    "ReceiptValidationError",
    "build_receipt",
    "verify_receipt",
]
