"""Safety contract for the future L3 AWS validation tier."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .contract import LabContractError


def validate_aws_request(
    value: dict[str, Any], *, execute: bool = False, confirm: bool = False
) -> dict[str, Any]:
    required = ("region", "owner", "run_id", "ttl", "budget", "resource_prefix")
    missing = [field for field in required if not value.get(field)]
    if missing:
        return {
            "allowed": False,
            "classification": "INVALID_SCENARIO",
            "unresolved": [{"code": "aws_guard_missing", "fields": missing}],
        }
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,30}", str(value["resource_prefix"])):
        raise LabContractError("resource_prefix must be lowercase and bounded")
    if not execute:
        return {
            "allowed": False,
            "classification": "UNRESOLVED",
            "reason": "AWS execution requires explicit opt-in",
        }
    if not confirm:
        raise LabContractError("AWS validation requires --confirm")
    return {
        "allowed": True,
        "classification": "UNRESOLVED",
        "reason": "execution adapter not part of offline core",
    }


def required_tags(
    *, run_id: str, owner: str, ttl: str, created_at: str | None = None
) -> dict[str, str]:
    if not run_id or not owner or not ttl:
        raise LabContractError("run_id, owner and ttl are required for AWS tags")
    timestamp = created_at or datetime.now().astimezone().isoformat()
    return {
        "sparkforge_lab": "true",
        "run_id": run_id,
        "ttl": ttl,
        "owner": owner,
        "created_at": timestamp,
    }


__all__ = ["required_tags", "validate_aws_request"]
