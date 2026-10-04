from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from sparkforge.architecture.streaming import analyze_streaming_architecture

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "realtime_architecture"


def test_candidate_matrix_refuses_underdetermined_winner():
    payload = analyze_streaming_architecture(
        FIXTURES / "ambiguous/input/requirements.json"
    )
    assert payload["decision"]["status"] == "unresolved"
    assert payload["decision"]["selected"] is None
    assert len(payload["decision"]["viable_candidates"]) > 1
    assert payload["workload_profile"]["assumptions"]


def test_hard_constraints_can_leave_one_candidate_without_soft_ranking():
    payload = analyze_streaming_architecture(
        FIXTURES / "unique_managed_spark/input/requirements.json"
    )
    assert payload["decision"] == json.loads(
        (FIXTURES / "unique_managed_spark/expected/result.json").read_text(
            encoding="utf-8"
        )
    )["decision"]
    assert payload["decision"]["selected"] == "glue_streaming"
    assert payload["candidate_matrix"][2]["status"] == "unsupported"


def test_fixture_results_are_stable_and_requirements_stay_separate():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        payload = analyze_streaming_architecture(directory / meta["artifact"])
        expected = json.loads(
            (directory / "expected/result.json").read_text(encoding="utf-8")
        )
        assert payload == expected
        assert "requirements" in payload["workload_profile"]
        assert "assumptions" in payload["workload_profile"]
        assert payload["decision"]["status"] == meta["expected_status"]
        assert payload["decision"]["selected"] == meta["expected_selected"]


def test_cli_emits_adr_and_matrix(tmp_path: Path):
    output = tmp_path / "architecture.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sparkforge.adapters.cli",
            "architecture",
            "streaming",
            "--path",
            str(FIXTURES / "ambiguous/input/requirements.json"),
            "--out",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    actual = json.loads(completed.stdout)
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert actual == persisted
    assert actual["adr"]["chosen_architecture"] is None
