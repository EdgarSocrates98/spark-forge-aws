"""Token Waste Detector for SparkForge Economy Engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WasteFinding:
    pattern_id: str
    title: str
    severity: str  # P0, P1, P2, P3
    estimated_wasted_tokens: int
    estimated_wasted_cost_usd: float
    description: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "title": self.title,
            "severity": self.severity,
            "estimated_wasted_tokens": self.estimated_wasted_tokens,
            "estimated_wasted_cost_usd": self.estimated_wasted_cost_usd,
            "description": self.description,
            "recommendation": self.recommendation,
        }


class TokenWasteDetector:
    """Detects inefficiencies, redundant calls, and token leaks in execution traces."""

    def analyze_trace(self, trace_events: list[dict[str, Any]]) -> list[WasteFinding]:
        findings: list[WasteFinding] = []

        seen_tool_calls: dict[str, int] = {}
        total_prompt_tokens = 0
        premium_calls_on_simple_tasks = 0

        for event in trace_events:
            event_type = event.get("type", "")
            tokens = event.get("tokens", 0)
            total_prompt_tokens += tokens

            if event_type == "tool_call":
                tool_name = event.get("name", "")
                tool_args = str(event.get("args", {}))
                key = f"{tool_name}:{tool_args}"
                seen_tool_calls[key] = seen_tool_calls.get(key, 0) + 1

            if event_type == "model_call":
                tier = event.get("tier", "")
                task_complexity = event.get("task_complexity", "low")
                if tier == "tier_5_premium" and task_complexity in ("low", "deterministic"):
                    premium_calls_on_simple_tasks += 1

        # Check repeated identical tool calls
        for key, count in seen_tool_calls.items():
            if count > 2:
                wasted = (count - 1) * 500
                findings.append(
                    WasteFinding(
                        pattern_id="WASTE-001",
                        title=f"Identical tool call repeated {count} times",
                        severity="P1",
                        estimated_wasted_tokens=wasted,
                        estimated_wasted_cost_usd=round((wasted / 1_000_000.0) * 0.80, 4),
                        description=(
                            f"Tool call '{key[:60]}...' executed {count} times with identical "
                            f"arguments."
                        ),
                        recommendation=(
                            "Enable Tier 1 ArtifactCache to avoid repeated identical "
                            "tool runs."
                        ),
                    )
                )

        # Check premium model misuse
        if premium_calls_on_simple_tasks > 0:
            wasted = premium_calls_on_simple_tasks * 2000
            findings.append(
                WasteFinding(
                    pattern_id="WASTE-002",
                    title="Expensive model used for simple/deterministic task",
                    severity="P1",
                    estimated_wasted_tokens=wasted,
                    estimated_wasted_cost_usd=round((wasted / 1_000_000.0) * 15.0, 4),
                    description=(
                        f"Detected {premium_calls_on_simple_tasks} Tier 5 calls on low complexity "
                        f"tasks."
                    ),
                    recommendation="Route to Tier 3 cheap model or Tier 0 deterministic tool.",
                )
            )

        return findings
