from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.paths import WorkspaceScanPolicy, scan_repository
from sparkforge.workspace.manifest import fingerprint


def test_workspace_scanner_names_denied_and_oversized_files(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (tmp_path / "large.bin").write_bytes(b"x" * 16)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("x = 1\n", encoding="utf-8")

    report = scan_repository(tmp_path, WorkspaceScanPolicy(max_file_bytes=8))

    assert report.files == ()
    reasons = {(item["path"], item["reason"]) for item in report.skipped}
    assert (".env", "denylisted_file") in reasons
    assert ("large.bin", "file_too_large") in reasons
    assert ("build", "denylisted_name") in reasons


def test_workspace_scanner_rejects_symlink_candidates(tmp_path: Path) -> None:
    target = tmp_path / "target.py"
    target.write_text("value = 1\n", encoding="utf-8")
    link = tmp_path / "link.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    report = scan_repository(tmp_path)

    assert target in report.files
    assert {item["reason"] for item in report.skipped} == {"symlink"}


def test_fingerprint_records_scanner_policy_and_excludes_secret_content(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=first\n", encoding="utf-8")
    first = fingerprint(tmp_path)
    (tmp_path / ".env").write_text("TOKEN=second\n", encoding="utf-8")

    assert fingerprint(tmp_path) == first
