"""Freshness assessment for local Code Intelligence indexes.

Freshness is evidence, not a default.  The assessor only returns ``fresh``
when both fingerprints are available and equal, and only returns ``stale``
when both are available and differ.  Every other case is ``unknown``.

The module reads only the local SQLite metadata written by Code Intelligence;
it does not index, execute repository code, call a provider, or use MCP.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

FreshnessStatus = Literal["fresh", "stale", "unknown"]

_FINGERPRINT_KEYS = (
    "fingerprint",
    "tree_fingerprint",
    "content_fingerprint",
    "root_fingerprint",
)


@dataclass(frozen=True, slots=True)
class FreshnessAssessment:
    """Comparison result for a current and an indexed fingerprint."""

    status: FreshnessStatus
    current_fingerprint: str | None = None
    indexed_fingerprint: str | None = None
    reason: str = "fingerprint_unresolved"

    @classmethod
    def unknown(
        cls,
        reason: str = "fingerprint_unresolved",
        *,
        current_fingerprint: str | None = None,
        indexed_fingerprint: str | None = None,
    ) -> FreshnessAssessment:
        return cls(
            "unknown",
            _normalise_fingerprint(current_fingerprint),
            _normalise_fingerprint(indexed_fingerprint),
            reason,
        )

    @property
    def freshness(self) -> FreshnessStatus:
        """Compatibility spelling used by serialized graph envelopes."""

        return self.status

    @property
    def is_fresh(self) -> bool:
        return self.status == "fresh"

    def to_dict(self) -> dict[str, Any]:
        return {
            "freshness": self.status,
            "current_fingerprint": self.current_fingerprint,
            "indexed_fingerprint": self.indexed_fingerprint,
            "reason": self.reason,
        }


def assess_freshness(
    current_fingerprint: object | None,
    indexed_fingerprint: object | Mapping[str, object] | None = None,
    *,
    metadata: Mapping[str, object] | None = None,
) -> FreshnessAssessment:
    """Compare current and indexed fingerprints fail-closed.

    ``indexed_fingerprint`` may be a metadata mapping as a convenience for
    callers that already loaded the Code Intelligence metadata table.  A
    missing, empty, or non-string fingerprint is unresolved; it is never
    treated as a match.
    """

    if isinstance(indexed_fingerprint, Mapping):
        metadata = indexed_fingerprint
        indexed_fingerprint = None
    indexed = _normalise_fingerprint(indexed_fingerprint)
    if indexed is None and metadata is not None:
        indexed = _metadata_fingerprint(metadata)
    current = _normalise_fingerprint(current_fingerprint)

    if current is not None and indexed is not None:
        if current == indexed:
            return FreshnessAssessment("fresh", current, indexed, "fingerprint_match")
        return FreshnessAssessment("stale", current, indexed, "fingerprint_mismatch")
    if current is None and indexed is None:
        reason = "current_and_indexed_fingerprint_unresolved"
    elif current is None:
        reason = "current_fingerprint_unresolved"
    else:
        reason = "indexed_fingerprint_unresolved"
    return FreshnessAssessment.unknown(
        reason,
        current_fingerprint=current,
        indexed_fingerprint=indexed,
    )


def read_codeintel_metadata(database: str | Path) -> dict[str, str]:
    """Read Code Intelligence ``metadata`` without changing the database.

    A missing or malformed local index is evidence for ``unknown`` and is
    represented by an empty mapping.  The function intentionally does not
    infer freshness from the presence of a database file.
    """

    path = Path(database).expanduser()
    if not path.is_file():
        return {}
    try:
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            table = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'metadata'"
            ).fetchone()
            if table is None:
                return {}
            rows = connection.execute("SELECT key, value FROM metadata ORDER BY key").fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return {}
    return {str(key): str(value) for key, value in rows if key is not None and value is not None}


def assess_codeintel_freshness(
    current_fingerprint: object | None,
    database: str | Path | None = None,
    *,
    metadata: Mapping[str, object] | None = None,
) -> FreshnessAssessment:
    """Assess freshness using metadata from a local Code Intelligence index."""

    values = metadata
    if values is None and database is not None:
        values = read_codeintel_metadata(database)
    return assess_freshness(current_fingerprint, metadata=values)


# Short aliases keep the boundary easy to discover without introducing a
# second implementation or a second set of semantics.
assess = assess_freshness
assess_index = assess_codeintel_freshness
read_index_metadata = read_codeintel_metadata


def _metadata_fingerprint(metadata: Mapping[str, object]) -> str | None:
    for key in _FINGERPRINT_KEYS:
        value = _normalise_fingerprint(metadata.get(key))
        if value is not None:
            return value
    return None


def _normalise_fingerprint(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


__all__ = [
    "FreshnessAssessment",
    "FreshnessStatus",
    "assess",
    "assess_codeintel_freshness",
    "assess_freshness",
    "assess_index",
    "read_codeintel_metadata",
    "read_index_metadata",
]
