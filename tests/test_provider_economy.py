from __future__ import annotations

import json
from pathlib import Path

from sparkforge.economy.provider_cost import provider_cost


def _transcript(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "model": "fixture-model",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "cache_read_input_tokens": 30,
                        "cache_creation_input_tokens": 4,
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _pricing(path: Path, *, cost_basis: str = "operator:test") -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "currency": "USD",
                "cost_basis": cost_basis,
                "source": "fixture-pricing",
                "rates": {
                    "input_tokens": {"per_million": 1.0},
                    "output_tokens": {"per_million": 2.0},
                    "cache_read_tokens": {"per_million": 0.1},
                    "cache_creation_tokens": {"per_million": 0.5},
                },
            }
        ),
        encoding="utf-8",
    )


def test_provider_cost_requires_cost_basis_and_keeps_token_units(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    pricing = tmp_path / "pricing.json"
    _transcript(transcript)
    _pricing(pricing)

    result = provider_cost(transcript, pricing)

    assert result["tokens"] == {
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_tokens": 30,
        "cache_creation_tokens": 4,
    }
    assert result["cost_basis"] == "operator:test"
    assert result["cost_usd"] > 0
    assert result["unresolved"] == []


def test_provider_cost_refuses_missing_basis_without_zeroing_usage(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    pricing = tmp_path / "pricing.json"
    _transcript(transcript)
    _pricing(pricing, cost_basis="")

    result = provider_cost(transcript, pricing)

    assert result["tokens"]["input_tokens"] == 100
    assert result["cost_usd"] is None
    assert any(item["reason"] == "pricing_field_missing" for item in result["unresolved"])
