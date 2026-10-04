"""Semantic checkpoints for long-running agent sessions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class SemanticCheckpoint:
    objective: str
    state: str
    facts: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    context_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    budget: Mapping[str, Any] = field(default_factory=dict)
    routing: Mapping[str, Any] = field(default_factory=dict)
    security_state: Mapping[str, Any] = field(default_factory=dict)
    next_actions: tuple[str, ...] = ()
    created_at: str = ""

    @property
    def id(self) -> str:
        payload = self.to_dict(include_id=False)
        return "checkpoint_" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:20]

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "objective": self.objective,
            "state": self.state,
            "facts": list(self.facts),
            "decisions": list(self.decisions),
            "hypotheses": list(self.hypotheses),
            "unknowns": list(self.unknowns),
            "memory_refs": list(self.memory_refs),
            "context_refs": list(self.context_refs),
            "artifact_refs": list(self.artifact_refs),
            "budget": dict(self.budget),
            "routing": dict(self.routing),
            "security_state": dict(self.security_state),
            "next_actions": list(self.next_actions),
            "created_at": self.created_at,
        }
        if include_id:
            result = {"id": self.id, **result}
        return result

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> SemanticCheckpoint:
        return cls(
            objective=str(raw.get("objective", "")),
            state=str(raw.get("state", "")),
            facts=tuple(str(v) for v in raw.get("facts", ())),
            decisions=tuple(str(v) for v in raw.get("decisions", ())),
            hypotheses=tuple(str(v) for v in raw.get("hypotheses", ())),
            unknowns=tuple(str(v) for v in raw.get("unknowns", ())),
            memory_refs=tuple(str(v) for v in raw.get("memory_refs", ())),
            context_refs=tuple(str(v) for v in raw.get("context_refs", ())),
            artifact_refs=tuple(str(v) for v in raw.get("artifact_refs", ())),
            budget=dict(raw.get("budget", {})),
            routing=dict(raw.get("routing", {})),
            security_state=dict(raw.get("security_state", {})),
            next_actions=tuple(str(v) for v in raw.get("next_actions", ())),
            created_at=str(raw.get("created_at", "")),
        )

    def save(self, path: Path | str) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return destination

    @classmethod
    def load(cls, path: Path | str) -> SemanticCheckpoint:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


__all__ = ["SemanticCheckpoint"]
