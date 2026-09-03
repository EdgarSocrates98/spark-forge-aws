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

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BudgetStatus(str, Enum):
    WITHIN = "within"  # dentro do budget
    WARNING = "warning"  # perto do limite (80%+)
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
        """Status pelos QUATRO limites, não só tokens.

        `max_time_seconds` e `max_retries` eram rastreados e nunca lidos até
        2026-09-03: um agente com `time_elapsed_seconds=9999` sobre um teto de
        120 reportava `within`. Limite declarado e não verificado é pior que
        limite ausente — promete corte que não acontece.
        """
        if self.tokens_used >= self.max_tokens:
            return BudgetStatus.EXHAUSTED
        if self.tool_calls_used >= self.max_tool_calls:
            return BudgetStatus.EXHAUSTED
        if self.max_time_seconds > 0 and self.time_elapsed_seconds >= self.max_time_seconds:
            return BudgetStatus.EXHAUSTED
        if self.retries_used > self.max_retries:
            return BudgetStatus.EXHAUSTED
        ratios = [
            self.tokens_used / self.max_tokens if self.max_tokens > 0 else 0.0,
            self.tool_calls_used / self.max_tool_calls if self.max_tool_calls > 0 else 0.0,
            self.time_elapsed_seconds / self.max_time_seconds if self.max_time_seconds > 0 else 0.0,
        ]
        if max(ratios) >= 0.8:
            return BudgetStatus.WARNING
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

    def consume_time(self, seconds: int) -> None:
        """Acumula tempo decorrido. Estoura quando passa do teto declarado.

        O tempo é injetado por quem chama — este módulo nunca lê o relógio,
        pela mesma razão que `case.store` nunca gera timestamp.
        """
        self.time_elapsed_seconds += seconds
        if self.max_time_seconds > 0 and self.time_elapsed_seconds > self.max_time_seconds:
            raise BudgetExceededError(
                f"AgentBudget: time {self.time_elapsed_seconds}s > max {self.max_time_seconds}s"
            )

    def consume_retry(self) -> None:
        self.retries_used += 1
        if self.retries_used > self.max_retries:
            raise BudgetExceededError(
                f"AgentBudget: retries {self.retries_used} > max {self.max_retries}"
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
        """Status pelos limites declarados, incluindo tool calls e tempo.

        `max_total_tool_calls` e `max_total_time_seconds` eram declarados e
        nunca lidos até 2026-09-03 — mesmo defeito de `AgentBudget.status`.
        """
        if self.tokens_used >= self.max_total_tokens:
            return BudgetStatus.EXHAUSTED
        if self.agents_spawned >= self.max_agents:
            return BudgetStatus.EXHAUSTED
        if self.cost_incurred_usd >= self.max_cost_usd:
            return BudgetStatus.EXHAUSTED
        if self.tool_calls_used >= self.max_total_tool_calls:
            return BudgetStatus.EXHAUSTED
        if (
            self.max_total_time_seconds > 0
            and self.time_elapsed_seconds >= self.max_total_time_seconds
        ):
            return BudgetStatus.EXHAUSTED
        ratios = [
            self.tokens_used / self.max_total_tokens if self.max_total_tokens > 0 else 0.0,
            self.tool_calls_used / self.max_total_tool_calls
            if self.max_total_tool_calls > 0
            else 0.0,
            self.time_elapsed_seconds / self.max_total_time_seconds
            if self.max_total_time_seconds > 0
            else 0.0,
        ]
        if max(ratios) >= 0.8:
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

    def consume_tool_call(self, n: int = 1) -> None:
        self.tool_calls_used += n
        if self.tool_calls_used > self.max_total_tool_calls:
            raise BudgetExceededError(
                f"CaseBudget: tool_calls {self.tool_calls_used} > max {self.max_total_tool_calls}"
            )

    def consume_time(self, seconds: int) -> None:
        """Tempo injetado por quem chama — este módulo nunca lê o relógio."""
        self.time_elapsed_seconds += seconds
        if (
            self.max_total_time_seconds > 0
            and self.time_elapsed_seconds > self.max_total_time_seconds
        ):
            raise BudgetExceededError(
                f"CaseBudget: time {self.time_elapsed_seconds}s > "
                f"max {self.max_total_time_seconds}s"
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


# Chave opcional de `.sparkforge/case.yaml` que declara os tetos do case.
CASE_BUDGET_KEY = "budget"

_CASE_BUDGET_INT_FIELDS = (
    "max_total_tokens",
    "max_total_tool_calls",
    "max_total_time_seconds",
    "max_agents",
    "max_debates",
    "max_experiments",
)


def case_budget_from_case(case: Mapping[str, Any]) -> CaseBudget | None:
    """Constrói o `CaseBudget` declarado no case, ou `None` se não há bloco.

    `None` é a resposta honesta para "este case não declara budget": devolver
    o default do código no lugar seria apresentar valor de fábrica como estado
    medido do case — o defeito que `budget show` tinha até 2026-09-03.

    Só limites vêm daqui. Consumo (`tokens_used`, `cost_incurred_usd`) não é
    lido do case: consumo é medido no ledger de spans, não declarado à mão.
    """
    raw = case.get(CASE_BUDGET_KEY)
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError(
            f"case.yaml: `{CASE_BUDGET_KEY}` deve ser um mapa, recebido {type(raw).__name__}"
        )

    permitidas = set(_CASE_BUDGET_INT_FIELDS) | {"max_cost_usd"}
    desconhecidas = sorted(set(raw) - permitidas)
    if desconhecidas:
        raise ValueError(
            f"case.yaml: chaves desconhecidas em `{CASE_BUDGET_KEY}`: "
            f"{', '.join(desconhecidas)}. Esperado: {', '.join(sorted(permitidas))}"
        )

    kwargs: dict[str, Any] = {}
    for nome in _CASE_BUDGET_INT_FIELDS:
        if nome in raw:
            valor = raw[nome]
            if not isinstance(valor, int) or isinstance(valor, bool) or valor < 0:
                raise ValueError(
                    f"case.yaml: `{CASE_BUDGET_KEY}.{nome}` deve ser int >= 0, recebido {valor!r}"
                )
            kwargs[nome] = valor
    if "max_cost_usd" in raw:
        valor = raw["max_cost_usd"]
        if isinstance(valor, bool) or not isinstance(valor, int | float) or valor < 0:
            raise ValueError(
                f"case.yaml: `{CASE_BUDGET_KEY}.max_cost_usd` deve ser número >= 0, "
                f"recebido {valor!r}"
            )
        kwargs["max_cost_usd"] = float(valor)

    return CaseBudget(**kwargs)


@dataclass
class WasteReport:
    """Relatório de desperdício detectado."""

    duplicated_context: list[str] = field(default_factory=list)
    duplicate_tool_calls: list[str] = field(default_factory=list)
    duplicate_evidence: list[str] = field(default_factory=list)
    redundant_agents: list[str] = field(default_factory=list)
    # Preenchido por quem executa o debate — `detect_waste` não o mede
    # (decidir que um debate era desnecessário exige o resultado dele).
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
    agent_outputs: Mapping[str, str] | None,
    summaries: list[str],
    retrieved_docs: list[str],
    used_docs: list[str],
    context_chunks: list[str] | None = None,
) -> WasteReport:
    """Detecta desperdício em uma execução.

    Heurísticas simples, todas exatas (igualdade, não semelhança):
    - duplicate_tool_calls: mesma tool+args chamada >1 vez
    - duplicate_evidence: mesma evidence_id >1 vez
    - redundant_agents: agentes que não produziram output (`agent_outputs`
      mapeia agent_id -> output; vazio ou só espaço conta como redundante)
    - repeated_summaries: summaries idênticos
    - unused_retrieved_docs: retrieved mas não used
    - duplicated_context: mesmo trecho de contexto enviado >1 vez

    `unnecessary_debates` NÃO é medido aqui: decidir que um debate era
    desnecessário exige o resultado dele, que esta função não recebe. O campo
    existe em `WasteReport` para quem executa o debate preencher — vazio aqui
    significa "não medido", não "não houve".

    Até 2026-09-03 esta função recebia `agent_ids` e nunca o usava, e três dos
    campos do relatório saíam sempre vazios sem que nada dissesse por quê.
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

    # Agentes que não produziram output
    redundant = sorted(
        agent_id for agent_id, output in (agent_outputs or {}).items() if not output.strip()
    )

    # Mesmo trecho de contexto enviado mais de uma vez
    seen_chunks: set[str] = set()
    duplicated_context: list[str] = []
    for chunk in context_chunks or []:
        if chunk in seen_chunks:
            duplicated_context.append(chunk)
        seen_chunks.add(chunk)

    return WasteReport(
        duplicated_context=duplicated_context,
        duplicate_tool_calls=duplicate_calls,
        duplicate_evidence=duplicate_ev,
        redundant_agents=redundant,
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
