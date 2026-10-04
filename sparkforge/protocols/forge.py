"""Minimal public Forge/A2A contracts.

These envelopes intentionally expose evidence and unresolved state, not
internal blackboards, provider SDK objects or execution implementation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


def _id(prefix: str, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


class ForgeTaskStatus(str, Enum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ForgeCapability:
    name: str
    version: str = "1"
    domains: tuple[str, ...] = ()
    operations: tuple[str, ...] = ()
    trust_floor: str = "VERIFIED_FACT"

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "domains": list(self.domains), "operations": list(self.operations), "trust_floor": self.trust_floor}


@dataclass(frozen=True, slots=True)
class ForgeTask:
    task_type: str
    objective: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    budget: Mapping[str, Any] = field(default_factory=dict)
    requested_by: str = ""
    risk: str = "read_only"

    @property
    def id(self) -> str:
        return _id("forge_task", self.to_dict(include_id=False))

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        result = {"task_type": self.task_type, "objective": self.objective, "inputs": dict(self.inputs), "budget": dict(self.budget), "requested_by": self.requested_by, "risk": self.risk}
        return {"id": self.id, **result} if include_id else result


@dataclass(frozen=True, slots=True)
class ForgeEvidenceBundle:
    facts: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"facts": list(self.facts), "findings": list(self.findings), "evidence_refs": list(self.evidence_refs), "unresolved": list(self.unresolved)}


@dataclass(frozen=True, slots=True)
class ForgeHandoff:
    task_id: str
    source: str
    target: str
    evidence: ForgeEvidenceBundle = field(default_factory=ForgeEvidenceBundle)
    requested_action: str = ""
    authority: str = "DATA_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "source": self.source, "target": self.target, "evidence": self.evidence.to_dict(), "requested_action": self.requested_action, "authority": "DATA_ONLY"}


@dataclass(frozen=True, slots=True)
class ForgeResult:
    task_id: str
    status: ForgeTaskStatus
    summary: str
    evidence: ForgeEvidenceBundle = field(default_factory=ForgeEvidenceBundle)
    metrics: Mapping[str, Any] = field(default_factory=dict)
    rollback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "status": self.status.value, "summary": self.summary, "evidence": self.evidence.to_dict(), "metrics": dict(self.metrics), "rollback": self.rollback}


@dataclass(frozen=True, slots=True)
class ForgeHealth:
    status: str
    version: str
    capabilities: tuple[ForgeCapability, ...] = ()
    checks: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "version": self.version, "capabilities": [item.to_dict() for item in self.capabilities], "checks": dict(self.checks)}


__all__ = [
    "ForgeCapability",
    "ForgeEvidenceBundle",
    "ForgeHandoff",
    "ForgeHealth",
    "ForgeResult",
    "ForgeTask",
    "ForgeTaskStatus",
]
