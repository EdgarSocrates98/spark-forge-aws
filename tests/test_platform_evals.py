"""Shape guards for Platform Intelligence evals."""

from __future__ import annotations

from pathlib import Path

from scripts.check_platform_eval_contract import validate


SUITE = Path(__file__).parents[1] / "evals" / "platform_intelligence" / "suite.yaml"


def test_platform_eval_contract_has_quality_and_economy_axes() -> None:
    result = validate(SUITE)

    assert result["valid"] is True
    assert result["case_count"] >= 8


def test_platform_eval_knowledge_separates_tokens_and_bytes() -> None:
    document = Path(__file__).parents[1] / "docs" / "knowledge" / "platform-intelligence-evals.md"
    text = document.read_text(encoding="utf-8")

    assert "tokens" in text.lower()
    assert "bytes" in text.lower()
