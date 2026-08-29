"""Token Budget and Cost Estimation Models for SparkForge Economy Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TierPricing:
    """Pricing in USD per 1M tokens."""

    input_price_per_m: float
    output_price_per_m: float
    cached_input_price_per_m: float = 0.0


# Standard price references per tier (USD / 1M tokens)
TIER_PRICING: dict[str, TierPricing] = {
    "tier_0_deterministic": TierPricing(0.0, 0.0, 0.0),
    "tier_1_cached": TierPricing(0.0, 0.0, 0.0),
    "tier_2_retrieval": TierPricing(0.0, 0.0, 0.0),
    "tier_3_cheap_local": TierPricing(0.10, 0.40, 0.025),
    "tier_4_specialist": TierPricing(0.80, 3.20, 0.20),
    "tier_5_premium": TierPricing(3.00, 15.00, 0.75),
    "tier_6_multi_agent": TierPricing(6.00, 30.00, 1.50),
}


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    tier: str = "tier_0_deterministic"
    tool_calls: int = 0
    agent_calls: int = 0
    retries: int = 0

    def estimate_cost_usd(self) -> float:
        pricing = TIER_PRICING.get(self.tier, TIER_PRICING["tier_3_cheap_local"])
        net_input = max(0, self.input_tokens - self.cached_tokens)
        cost_input = (net_input / 1_000_000.0) * pricing.input_price_per_m
        cost_cached = (self.cached_tokens / 1_000_000.0) * pricing.cached_input_price_per_m
        cost_output = (self.output_tokens / 1_000_000.0) * pricing.output_price_per_m
        return round(cost_input + cost_cached + cost_output, 6)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["estimated_cost_usd"] = self.estimate_cost_usd()
        return d


@dataclass
class TaskBudgetGuardrail:
    max_input_tokens: int = 8000
    max_output_tokens: int = 4000
    max_total_tokens: int = 16000
    max_cost_usd: float = 0.10
    max_agent_calls: int = 3
    max_tool_calls: int = 20
    max_retries: int = 2

    def check_exceeded(self, usage: TokenUsage) -> tuple[bool, str | None]:
        total_tokens = usage.input_tokens + usage.output_tokens
        if total_tokens > self.max_total_tokens:
            return True, f"Total token budget exceeded: {total_tokens} > {self.max_total_tokens}"
        if usage.input_tokens > self.max_input_tokens:
            return (
                True,
                f"Input token budget exceeded: {usage.input_tokens} > {self.max_input_tokens}",
            )
        if usage.output_tokens > self.max_output_tokens:
            return (
                True,
                f"Output token budget exceeded: {usage.output_tokens} > {self.max_output_tokens}",
            )
        if usage.estimate_cost_usd() > self.max_cost_usd:
            return (
                True,
                f"Cost budget exceeded: ${usage.estimate_cost_usd():.4f} > "
                f"${self.max_cost_usd:.4f}",
            )
        if usage.agent_calls > self.max_agent_calls:
            return True, f"Agent call limit exceeded: {usage.agent_calls} > {self.max_agent_calls}"
        if usage.tool_calls > self.max_tool_calls:
            return True, f"Tool call limit exceeded: {usage.tool_calls} > {self.max_tool_calls}"
        if usage.retries > self.max_retries:
            return True, f"Retry limit exceeded: {usage.retries} > {self.max_retries}"
        return False, None
