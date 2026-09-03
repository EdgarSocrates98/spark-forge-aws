"""Unified Token Economics — AgentBudget, CaseBudget, DebateBudget.

Unifica as 3 classes de budget existentes (TaskBudgetGuardrail, AutonomyBudget,
Budget) em uma hierarquia coerente. Não substitui as existentes — fornece
uma camada unificada que as referencia.

Princípios:
- Budget é finito e enforced.
- Estimativa antes da execução, comparação depois.
- Detecta: duplicated context, duplicate tool calls, duplicate evidence,
  redundant agents, unnecessary debates, repeated summaries, oversized outputs.
- Minimum sufficient context, agents, rounds, tool calls, model capability.
- Mas correctness, safety, evidence, auditability > token savings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BudgetStatus(str, Enum):
    WITHIN = "within"  # dentro do budget
    WARNING = "warning"  # 接近 do limite (80%+)
    EXCEEDED = "exceeded"  # excedeu
    EXHAUSTED = "exhausted"  # totalmente consumido


@dataclass
class AgentBudget:
    """Budget para um único agente.

    Enforced: o agente para quando atinge qualquer limite.
    """

    max_tokens: int = 4000
    max_tool_calls: int = 10
    max_time_seconds: int = 120
    max_retries: int = 2

    # Tracking (mutable)
    tokens_used: int = 0
    tool_calls_used: int = 0
    time_elapsed_seconds: int = 0
    retries_used: int = 0

    @property
    def status(self) -> BudgetStatus:
        token_ratio = self.tokens_used / self.max_tokens if self.max_tokens > 0 else 0
        if self.tokens_used >= self.max_tokens:
            return BudgetStatus.EXHAUSTED
        if self.tool_calls_used >= self.max_tool_calls:
            return BudgetStatus.EXHAUSTED
        if token_ratio >= 0.8:
            return BudgetStatus.WARNING
        if self.tokens_used > 0 or self.tool_calls_used > 0:
            return BudgetStatus.WITHIN
        return BudgetStatus.WITHIN

    @property
    def is_exhausted(self) -> bool:
        return self.status == BudgetStatus.EXHAUSTED

    def consume_tokens(self, n: int) -> None:
        self.tokens_used += n
        if self.tokens_used > self.max_tokens:
            raise BudgetExceededError(
                f"AgentBudget: tokens {self.tokens_used} > max {self.max_tokens}"
            )

    def consume_tool_call(self) -> None:
        self.tool_calls_used += 1
        if self.tool_calls_used > self.max_tool_calls:
            raise BudgetExceededError(
                f"AgentBudget: tool_calls {self.tool_calls_used} > max {self.max_tool_calls}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "max_tool_calls": self.max_tool_calls,
            "max_time_seconds": self.max_time_seconds,
            "max_retries": self.max_retries,
            "tokens_used": self.tokens_used,
            "tool_calls_used": self.tool_calls_used,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "retries_used": self.retries_used,
            "status": self.status.value,
        }


@dataclass
class CaseBudget:
    """Budget para um case inteiro.

    Agrega budgets de todos os agentes envolvidos.
    """

    max_total_tokens: int = 50000
    max_total_tool_calls: int = 200
    max_total_time_seconds: int = 1800  # 30 min
    max_agents: int = 5
    max_debates: int = 2
    max_experiments: int = 3
    max_cost_usd: float = 1.0

    # Tracking
    tokens_used: int = 0
    tool_calls_used: int = 0
    time_elapsed_seconds: int = 0
    agents_spawned: int = 0
    debates_held: int = 0
    experiments_run: int = 0
    cost_incurred_usd: float = 0.0

    @property
    def status(self) -> BudgetStatus:
        if self.tokens_used >= self.max_total_tokens:
            return BudgetStatus.EXHAUSTED
        if self.agents_spawned >= self.max_agents:
            return BudgetStatus.EXHAUSTED
        if self.cost_incurred_usd >= self.max_cost_usd:
            return BudgetStatus.EXHAUSTED
        token_ratio = self.tokens_used / self.max_total_tokens if self.max_total_tokens > 0 else 0
        if token_ratio >= 0.8:
            return BudgetStatus.WARNING
        return BudgetStatus.WITHIN

    @property
    def is_exhausted(self) -> bool:
        return self.status == BudgetStatus.EXHAUSTED

    def can_spawn_agent(self) -> bool:
        return self.agents_spawned < self.max_agents and not self.is_exhausted

    def can_start_debate(self) -> bool:
        return self.debates_held < self.max_debates and not self.is_exhausted

    def can_run_experiment(self) -> bool:
        return self.experiments_run < self.max_experiments and not self.is_exhausted

    def consume_agent(self, tokens: int = 0) -> None:
        if not self.can_spawn_agent():
            raise BudgetExceededError(f"CaseBudget: max_agents {self.max_agents} reached")
        self.agents_spawned += 1
        if tokens:
            self.consume_tokens(tokens)

    def consume_debate(self, tokens: int = 0) -> None:
        if not self.can_start_debate():
            raise BudgetExceededError(f"CaseBudget: max_debates {self.max_debates} reached")
        self.debates_held += 1
        if tokens:
            self.consume_tokens(tokens)

    def consume_experiment(self, cost_usd: float = 0.0) -> None:
        if not self.can_run_experiment():
            raise BudgetExceededError(f"CaseBudget: max_experiments {self.max_experiments} reached")
        self.experiments_run += 1
        self.cost_incurred_usd += cost_usd

    def consume_tokens(self, n: int) -> None:
        self.tokens_used += n
        if self.tokens_used > self.max_total_tokens:
            raise BudgetExceededError(
                f"CaseBudget: tokens {self.tokens_used} > max {self.max_total_tokens}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_total_tokens": self.max_total_tokens,
            "max_total_tool_calls": self.max_total_tool_calls,
            "max_total_time_seconds": self.max_total_time_seconds,
            "max_agents": self.max_agents,
            "max_debates": self.max_debates,
            "max_experiments": self.max_experiments,
            "max_cost_usd": self.max_cost_usd,
            "tokens_used": self.tokens_used,
            "tool_calls_used": self.tool_calls_used,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "agents_spawned": self.agents_spawned,
            "debates_held": self.debates_held,
            "experiments_run": self.experiments_run,
            "cost_incurred_usd": self.cost_incurred_usd,
            "status": self.status.value,
        }


@dataclass
class WasteReport:
    """Relatório de desperdício detectado."""

    duplicated_context: list[str] = field(default_factory=list)
    duplicate_tool_calls: list[str] = field(default_factory=list)
    duplicate_evidence: list[str] = field(default_factory=list)
    redundant_agents: list[str] = field(default_factory=list)
    unnecessary_debates: list[str] = field(default_factory=list)
    repeated_summaries: list[str] = field(default_factory=list)
    oversized_outputs: list[str] = field(default_factory=list)
    failed_retries: int = 0
    unused_retrieved_docs: int = 0

    @property
    def total_waste_count(self) -> int:
        return (
            len(self.duplicated_context)
            + len(self.duplicate_tool_calls)
            + len(self.duplicate_evidence)
            + len(self.redundant_agents)
            + len(self.unnecessary_debates)
            + len(self.repeated_summaries)
            + len(self.oversized_outputs)
            + self.failed_retries
            + self.unused_retrieved_docs
        )

    @property
    def has_waste(self) -> bool:
        return self.total_waste_count > 0


class BudgetExceededError(Exception):
    """Budget foi excedido. Enforced — não aumenta infinitamente."""


def detect_waste(
    tool_calls: list[dict[str, Any]],
    evidence_ids: list[str],
    agent_ids: list[str],
    summaries: list[str],
    retrieved_docs: list[str],
    used_docs: list[str],
) -> WasteReport:
    """Detecta desperdício em uma execução.

    Heurísticas simples:
    - duplicate_tool_calls: mesma tool+args chamada >1 vez
    - duplicate_evidence: mesma evidence_id >1 vez
    - redundant_agents: agentes que não produziram output
    - repeated_summaries: summaries idênticos
    - unused_retrieved_docs: retrieved mas não used
    """
    # Duplicate tool calls
    seen_calls: set[str] = set()
    duplicate_calls: list[str] = []
    for tc in tool_calls:
        key = f"{tc.get('tool', '')}:{str(tc.get('args', ''))}"
        if key in seen_calls:
            duplicate_calls.append(key)
        seen_calls.add(key)

    # Duplicate evidence
    seen_ev: set[str] = set()
    duplicate_ev: list[str] = []
    for eid in evidence_ids:
        if eid in seen_ev:
            duplicate_ev.append(eid)
        seen_ev.add(eid)

    # Repeated summaries
    seen_summaries: set[str] = set()
    repeated: list[str] = []
    for s in summaries:
        if s in seen_summaries:
            repeated.append(s)
        seen_summaries.add(s)

    # Unused retrieved docs
    retrieved_set = set(retrieved_docs)
    used_set = set(used_docs)
    unused = len(retrieved_set - used_set)

    return WasteReport(
        duplicate_tool_calls=duplicate_calls,
        duplicate_evidence=duplicate_ev,
        repeated_summaries=repeated,
        unused_retrieved_docs=unused,
    )


@dataclass
class BudgetEstimate:
    """Estimativa de budget antes da execução."""

    estimated_agents: int
    estimated_calls: int
    estimated_tokens: int
    estimated_latency_seconds: int
    estimated_cost_usd: float


@dataclass
class BudgetActual:
    """Budget real após execução, para comparação com estimativa."""

    actual_agents: int
    actual_calls: int
    actual_tokens: int
    actual_latency_seconds: int
    actual_cost_usd: float


def compare_budget(estimate: BudgetEstimate, actual: BudgetActual) -> dict[str, Any]:
    """Compara estimativa vs real e calcula utilization."""
    return {
        "agents": {
            "estimated": estimate.estimated_agents,
            "actual": actual.actual_agents,
            "utilization": actual.actual_agents / estimate.estimated_agents
            if estimate.estimated_agents > 0
            else 0,
        },
        "calls": {
            "estimated": estimate.estimated_calls,
            "actual": actual.actual_calls,
            "utilization": actual.actual_calls / estimate.estimated_calls
            if estimate.estimated_calls > 0
            else 0,
        },
        "tokens": {
            "estimated": estimate.estimated_tokens,
            "actual": actual.actual_tokens,
            "utilization": actual.actual_tokens / estimate.estimated_tokens
            if estimate.estimated_tokens > 0
            else 0,
            "waste": max(0, actual.actual_tokens - estimate.estimated_tokens),
        },
        "latency_seconds": {
            "estimated": estimate.estimated_latency_seconds,
            "actual": actual.actual_latency_seconds,
            "utilization": actual.actual_latency_seconds / estimate.estimated_latency_seconds
            if estimate.estimated_latency_seconds > 0
            else 0,
        },
        "cost_usd": {
            "estimated": estimate.estimated_cost_usd,
            "actual": actual.actual_cost_usd,
            "utilization": actual.actual_cost_usd / estimate.estimated_cost_usd
            if estimate.estimated_cost_usd > 0
            else 0,
        },
    }
