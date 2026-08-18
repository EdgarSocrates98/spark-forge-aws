"""Bounded autonomy and policy-driven routing for SparkForge agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

@dataclass(frozen=True)
class AutonomyBudget:
    max_iterations: int = 6
    max_agents: int = 4
    max_tokens: int = 12000
    stagnation_limit: int = 2

@dataclass(frozen=True)
class StopDecision:
    stop: bool
    reason: str

@dataclass(frozen=True)
class RouteDecision:
    phase: str
    agents: tuple[str, ...]
    reason: str
    effort: str
    focus: str = "improvement"

class AutonomyController:
    PHASE_ORDER = ("inventory", "collect", "analyze", "judge", "verify", "synthesize")
    def __init__(self, budget: AutonomyBudget | None = None):
        self.budget = budget or AutonomyBudget()

    def estimate_effort(self, goal: str, *, risk: str = "low", evidence_count: int = 0) -> str:
        words = len(goal.split())
        if risk in {"high", "critical"} or words > 60 or evidence_count > 20:
            return "deep"
        if words > 20 or evidence_count > 5:
            return "standard"
        return "focused"

    def focus_for_goal(self, goal: str) -> str:
        text = goal.lower()
        if any(word in text for word in ("build", "create", "implement", "construct")):
            return "construction"
        if any(word in text for word in ("document", "guide", "readme", "explain")):
            return "documentation"
        if any(word in text for word in ("validate", "test", "verify", "audit")):
            return "validation"
        return "improvement"

    def route(self, *, goal: str, available_agents: Iterable[str], completed: set[str] | None = None, evidence_count: int = 0, risk: str = "low") -> RouteDecision:
        done = completed or set()
        effort = self.estimate_effort(goal, risk=risk, evidence_count=evidence_count)
        phase = next((item for item in self.PHASE_ORDER if item not in done), "synthesize")
        preferred = {
            "inventory": ("sf-inventory",),
            "collect": ("sf-extractor",),
            "analyze": ("sf-judge", "sf-data-quality"),
            "judge": ("sf-judge",),
            "verify": ("sf-verifier",),
            "synthesize": ("sf-synthesizer",),
        }[phase]
        allowed = set(available_agents)
        selected = tuple(name for name in preferred if name in allowed)[: self.budget.max_agents]
        if not selected:
            selected = tuple(sorted(allowed))[: self.budget.max_agents]
        return RouteDecision(phase, selected, f"next unmet phase: {phase}", effort, self.focus_for_goal(goal))

    def should_stop(self, *, iteration: int, tokens_used: int, progress: int, stagnant_iterations: int, terminal: bool = False) -> StopDecision:
        if terminal:
            return StopDecision(True, "terminal decision reached")
        if iteration >= self.budget.max_iterations:
            return StopDecision(True, "iteration budget exhausted")
        if tokens_used >= self.budget.max_tokens:
            return StopDecision(True, "token budget exhausted")
        if stagnant_iterations >= self.budget.stagnation_limit:
            return StopDecision(True, "no measurable progress")
        if progress < 0:
            return StopDecision(True, "quality regression detected")
        return StopDecision(False, "continue")

    def authorize_tool(self, *, agent: str, tool: str, allowed_tools: Iterable[str], mutating: bool = False, approval: bool = False) -> tuple[bool, str]:
        if tool not in set(allowed_tools):
            return False, "tool not allowlisted for agent"
        if mutating and not approval:
            return False, "mutating action requires approval"
        return True, "authorized"
