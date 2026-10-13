from __future__ import annotations

import json
import shutil
from pathlib import Path

from sparkforge_aws.adapters.cli import build_parser, main

ROOT = Path(__file__).resolve().parents[1]


def test_parser_exposes_decision_commands() -> None:
    parsed = build_parser().parse_args(
        ["decision", "validate", "--contract", "routing.data_domain"]
    )

    assert (parsed.command, parsed.decision_action) == ("decision", "validate")
    evaluated = build_parser().parse_args(["decision", "evaluate", "--input", "state.json"])
    assert (evaluated.command, evaluated.decision_action) == ("decision", "evaluate")


def test_decision_validate_and_shadow_and_receipt_cli(tmp_path: Path, capsys) -> None:
    shadow_repo = tmp_path / "repo"
    shadow_repo.mkdir()
    shutil.copytree(ROOT / "config", shadow_repo / "config")
    request_path = shadow_repo / "input.json"
    request_path.write_text(
        json.dumps(
            {
                "task_id": "cli-task",
                "task_description": "diagnose",
                "current_route": "tier_3_cheap_local",
            }
        ),
        encoding="utf-8",
    )
    assert main(["decision", "validate", "--repo", str(ROOT)]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "decision",
                "shadow",
                "--repo",
                str(shadow_repo),
                "--contract",
                "routing.data_domain",
                "--input",
                str(request_path),
                "--now",
                "fixed",
                "--out",
                str(shadow_repo / "shadow.json"),
            ]
        )
        == 0
    )
    shadow = json.loads(capsys.readouterr().out)
    assert shadow["result"]["status"] == "accepted"
    receipt_path = (
        shadow_repo / ".sparkforge_aws" / "decision-receipts"
        / f"{shadow['result']['receipt_id']}.json"
    )
    assert (
        main(
            [
                "decision",
                "receipt",
                "--repo",
                str(shadow_repo),
                "--path",
                str(receipt_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["valid"] is True
    assert (
        main(
            [
                "decision",
                "compare",
                "--shadow",
                str(shadow_repo / "shadow.json"),
                "--current-route",
                "tier_3_cheap_local",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["state"] == "agreement"


def test_decision_benchmark_cli_passes_seed() -> None:
    assert (
        main(
            [
                "decision",
                "benchmark",
                "--repo",
                str(ROOT),
                "--fixture",
                "evals/token_efficient/fixtures/decision_plane_cases.yaml",
            ]
        )
        == 0
    )


def test_candidate_validate_cli_uses_explicit_repository(capsys) -> None:
    from sparkforge_aws.evals.cli import main as eval_main

    assert eval_main(["candidate", "validate", "--repo", str(ROOT)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidates"][0]["content_sha256"]
