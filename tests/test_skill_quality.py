"""Deterministic gates for the 52-skill quality contract and eval catalog."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_skills import audit
from scripts.check_skill_evals import errors
from scripts.run_skill_evals import run

ROOT = Path(__file__).resolve().parents[1]


def test_all_source_skills_follow_contract() -> None:
    assert audit() == []


def test_all_source_skills_have_skill_creator_evals() -> None:
    assert errors() == []


def test_offline_eval_runner_is_complete_and_has_no_provider_side_effect() -> None:
    report = run()
    assert report["skills"] == 52
    assert report["cases"] == 104
    assert report["passed"] == 104
    assert report["failed"] == 0
    assert report["provider_calls"] == 0
    assert report["aws_calls"] == 0


def test_shared_validator_rejects_unanchored_recommendation() -> None:
    from skills._shared.scripts.validate_skill_context import validate

    errors = validate({"recommendation": {"title": "x"}})
    assert "recommendation.evidence must be a non-empty list" in errors

