"""Projection of effective candidate lifecycle from verified receipts."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from sparkforge_aws.decision.fingerprint import digest


class LifecycleProjectionError(ValueError):
    """Named failure while reconstructing effective lifecycle state."""


class LifecycleStatus(str, Enum):
    CANDIDATE = "candidate"
    EVALUATED = "evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


DEFAULT_TRANSITIONS: dict[str, frozenset[str]] = {
    "candidate": frozenset({"evaluated", "rejected"}),
    "evaluated": frozenset({"accepted", "rejected"}),
    "accepted": frozenset({"rolled_back"}),
    "rejected": frozenset(),
    "rolled_back": frozenset(),
}


@dataclass(frozen=True, slots=True)
class EffectiveCandidate:
    """Declared and receipt-projected state for one candidate."""

    candidate_id: str
    declared_status: Any
    effective_status: Any
    receipt_ids: tuple[str, ...]
    last_sequence: int


class LifecycleProjector:
    """Verify the global receipt chain and project one candidate's state."""

    def __init__(
        self,
        root: Path | str,
        *,
        receipt_reader: Callable[[Path], Mapping[str, Any]] | None = None,
        transitions: Mapping[Any, Any] | None = None,
        status_parser: Callable[[Any], Any] | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self._receipt_reader = receipt_reader or self._read_receipt
        self._transitions = transitions or DEFAULT_TRANSITIONS
        self._status_parser = status_parser or (lambda value: value)

    def project(self, candidate_id: str, declared_status: Any) -> EffectiveCandidate:
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise LifecycleProjectionError("candidate_id_required")
        documents = self._verified_documents()
        state = self._status_parser(getattr(declared_status, "value", declared_status))
        receipt_ids: list[str] = []
        last_sequence = 0
        for document in documents:
            if not self._belongs_to(document, candidate_id):
                continue
            target = self._target_status(document)
            if target is None:
                continue
            parsed_target = self._status_parser(target)
            if parsed_target == state and document.get("action") == "evaluation":
                receipt_ids.append(str(document["receipt_id"]))
                last_sequence = int(document["event_sequence"])
                continue
            allowed = self._transitions.get(state, ())
            if parsed_target not in allowed:
                raise LifecycleProjectionError(
                    f"receipt_transition_invalid:{getattr(state, 'value', state)}->"
                    f"{getattr(parsed_target, 'value', parsed_target)}"
                )
            state = parsed_target
            receipt_ids.append(str(document["receipt_id"]))
            last_sequence = int(document["event_sequence"])
        return EffectiveCandidate(
            candidate_id=candidate_id,
            declared_status=declared_status,
            effective_status=state,
            receipt_ids=tuple(receipt_ids),
            last_sequence=last_sequence,
        )

    def verified_documents(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._verified_documents())

    def receipt_status(self) -> dict[str, tuple[str, ...]]:
        """Report authoritative v2 receipts and readable legacy receipts."""
        if not self.root.is_dir():
            return {"authoritative": (), "legacy": ()}
        paths = tuple(
            sorted(
                path
                for path in self.root.iterdir()
                if path.is_file() and path.suffix == ".json"
            )
        )
        documents = tuple(self._receipt_reader(path) for path in paths)
        authoritative = tuple(
            str(document["receipt_id"])
            for document in self._verified_documents()
        )
        legacy = tuple(
            str(document["receipt_id"])
            for document in documents
            if document.get("receipt_schema_version") != 2
        )
        return {"authoritative": authoritative, "legacy": legacy}

    def _verified_documents(self) -> list[Mapping[str, Any]]:
        if not self.root.is_dir():
            return []
        paths = sorted(
            self.root / entry.name
            for entry in self.root.iterdir()
            if entry.is_file() and entry.suffix == ".json"
        )
        documents = [self._receipt_reader(path) for path in paths]
        versioned = [
            document
            for document in documents
            if document.get("receipt_schema_version") == 2
        ]
        ordered = sorted(versioned, key=lambda item: self._sequence(item))
        previous: str | None = None
        for expected, document in enumerate(ordered, start=1):
            sequence = document.get("event_sequence")
            if sequence != expected:
                raise LifecycleProjectionError("receipt_sequence_gap")
            if document.get("previous_receipt_id") != previous:
                raise LifecycleProjectionError("receipt_predecessor_mismatch")
            previous = str(document.get("receipt_id"))
        return ordered

    @staticmethod
    def _sequence(document: Mapping[str, Any]) -> int:
        value = document.get("event_sequence")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise LifecycleProjectionError("receipt_sequence_invalid")
        return value

    @staticmethod
    def _belongs_to(document: Mapping[str, Any], candidate_id: str) -> bool:
        if document.get("candidate_id") == candidate_id:
            return True
        candidate = document.get("candidate")
        if isinstance(candidate, Mapping) and candidate.get("candidate_id") == candidate_id:
            return True
        return False

    @staticmethod
    def _target_status(document: Mapping[str, Any]) -> Any | None:
        if document.get("action") == "evaluation":
            evaluation = document.get("evaluation")
            if isinstance(evaluation, Mapping) and isinstance(evaluation.get("status"), str):
                return evaluation["status"]
        candidate = document.get("candidate")
        if isinstance(candidate, Mapping) and isinstance(candidate.get("status"), str):
            return candidate["status"]
        evaluation = document.get("evaluation")
        if isinstance(evaluation, Mapping) and isinstance(evaluation.get("status"), str):
            return evaluation["status"]
        return None

    @staticmethod
    def _read_receipt(path: Path) -> Mapping[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", path.stem):
            raise LifecycleProjectionError(f"receipt_id_invalid:{path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LifecycleProjectionError(f"receipt_unreadable:{path}") from exc
        if not isinstance(document, Mapping):
            raise LifecycleProjectionError(f"receipt_invalid:{path}")
        receipt_id = document.get("receipt_id")
        if receipt_id != path.stem:
            raise LifecycleProjectionError(f"receipt_id_mismatch:{path}")
        body = {key: value for key, value in document.items() if key != "receipt_id"}
        if digest(body) != receipt_id:
            raise LifecycleProjectionError(f"receipt_digest_mismatch:{path}")
        return document


__all__ = [
    "DEFAULT_TRANSITIONS",
    "EffectiveCandidate",
    "LifecycleProjectionError",
    "LifecycleProjector",
    "LifecycleStatus",
]
