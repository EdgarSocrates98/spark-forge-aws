from __future__ import annotations

from pathlib import Path

from sparkforge_aws.codeintel.incremental import refresh


def test_refresh_reports_complete_then_changed_and_reused_files(tmp_path: Path) -> None:
    (tmp_path / "lib.py").write_text("def process(value):\n    return value\n", encoding="utf-8")
    (tmp_path / "job.py").write_text(
        "from lib import process\n\ndef run(value):\n    return process(value)\n",
        encoding="utf-8",
    )
    database = tmp_path / "index.sqlite3"

    first = refresh(tmp_path, database)
    assert first.complete is True
    assert first.scanned_files >= 2

    (tmp_path / "lib.py").write_text(
        "def process(value):\n    return value + 1\n", encoding="utf-8"
    )
    second = refresh(tmp_path, database)
    assert second.complete is False
    assert "lib.py" in second.changed_files
    assert second.reused_files >= 0
    assert second.tree_fingerprint
    assert second.freshness == "fresh"
