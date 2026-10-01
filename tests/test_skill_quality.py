"""Deterministic gates for the 52-skill quality contract and eval catalog."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.audit_skills import _frontmatter, audit
from scripts.check_skill_evals import errors
from scripts.run_skill_evals import run

ROOT = Path(__file__).resolve().parents[1]


def test_all_source_skills_follow_contract() -> None:
    assert audit() == []


def test_all_source_skills_have_skill_creator_evals() -> None:
    assert errors() == []


def test_all_frontmatter_is_skill_creator_compatible() -> None:
    skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if (path / "SKILL.md").is_file())
    assert len(skill_dirs) == 52
    for skill_dir in skill_dirs:
        parsed = _frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        assert parsed is not None
        front, _ = parsed
        document = yaml.safe_load(front)
        assert set(document) <= {"name", "description", "metadata"}
        assert document["name"] == skill_dir.name
        assert document["description"].startswith("Use quando")
        assert len(document["description"]) <= 1024
        assert "<" not in document["description"]
        assert ">" not in document["description"]


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
