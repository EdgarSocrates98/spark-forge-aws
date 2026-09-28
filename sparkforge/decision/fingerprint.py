"""Stable identity for contract and compiled decision state."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sparkforge.decision.contracts import DecisionContract
from sparkforge.decision.models import CompiledState


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def decision_fingerprint(contract: DecisionContract, state: CompiledState) -> str:
    return digest(
        {
            "schema_version": contract.schema_version,
            "contract_id": contract.contract_id,
            "contract_version": contract.contract_version,
            "contract_sha256": contract.sha256,
            "primitive": contract.primitive.value,
            "spec": contract.spec,
            "state": dict(state.values),
        }
    )


def state_fingerprint(state: CompiledState) -> str:
    return digest({"state": dict(state.values), "unresolved": state.unresolved})


__all__ = ["canonical_json", "decision_fingerprint", "digest", "state_fingerprint"]
