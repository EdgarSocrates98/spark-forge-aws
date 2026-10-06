from __future__ import annotations

import sqlite3
from pathlib import Path

from sparkforge_aws.workspace.freshness import (
    assess_codeintel_freshness,
    assess_freshness,
    read_codeintel_metadata,
)


def test_freshness_requires_two_matching_fingerprints() -> None:
    assert assess_freshness("abc", "abc").status == "fresh"
    assert assess_freshness("abc", "def").status == "stale"
    assert assess_freshness("abc", None).status == "unknown"
    assert assess_freshness(None, "abc").status == "unknown"


def test_freshness_reads_indexed_fingerprint_from_codeintel_metadata(tmp_path: Path) -> None:
    database = tmp_path / "graph.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            ("content_fingerprint", "same"),
        )
        connection.commit()
    finally:
        connection.close()

    assert read_codeintel_metadata(database)["content_fingerprint"] == "same"
    assert assess_codeintel_freshness("same", database).status == "fresh"
    assert assess_codeintel_freshness("changed", database).status == "stale"


def test_freshness_never_uses_metadata_verdict_without_comparison(tmp_path: Path) -> None:
    database = tmp_path / "graph.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            ("freshness_verdict", "fresh"),
        )
        connection.commit()
    finally:
        connection.close()

    assert assess_codeintel_freshness(None, database).status == "unknown"
