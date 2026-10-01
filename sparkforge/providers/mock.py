"""Deterministic Mock LLM Provider for Testing and CI."""
from __future__ import annotations

from typing import Any

from sparkforge.agents.budget import estimate_tokens


class MockModelProvider:
    """Zero-cost, offline deterministic model provider."""

    def __init__(self, default_response: str = "Deterministic analysis completed.") -> None:
        self.default_response = default_response
        self.call_history: list[dict[str, Any]] = []

    def generate(self, prompt: str, tier: str = "tier_3_cheap_local") -> dict[str, Any]:
        self.call_history.append({"prompt": prompt, "tier": tier})
        return {
            "content": self.default_response,
            "input_tokens": estimate_tokens(prompt),
            "output_tokens": estimate_tokens(self.default_response),
            "cached_tokens": 0,
            "cost_usd": 0.0,
        }
