"""Local-First AgentOps and Structured Tracing Engine."""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# Vocabulario fechado do status de medicao de tokens de um span. `""` no campo
# significa "nao declarado" e e resolvido por derivacao -- ver
# `tokens_status_of`.
TOKEN_STATUS_VALUES = ("measured", "unresolved", "not_applicable")


def tokens_status_of(
    component_type: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    declared: str = "",
) -> str:
    """O status de medicao real de tokens de um span.

    `measured`: usage veio do provider/host (qualquer token != 0, ou o chamador
    declarou -- um provider que reporta 0 e medicao, e so ele sabe disso).
    `unresolved`: span de `model` sem usage -- o provider nao reportou e zero
    aqui NAO e medicao. `not_applicable`: span que nao carrega token de
    provider (tool, task, routing...), onde zero e ausencia estrutural.
    """
    if declared:
        if declared not in TOKEN_STATUS_VALUES:
            raise ValueError(
                f"tokens_status '{declared}' fora do vocabulario {TOKEN_STATUS_VALUES}"
            )
        return declared
    if input_tokens or output_tokens or cached_tokens:
        return "measured"
    if component_type == "model":
        return "unresolved"
    return "not_applicable"


@dataclass
class TraceSpan:
    span_id: str
    run_id: str
    parent_span_id: str | None
    name: str
    component_type: str  # task, routing, context, agent, model, tool, eval, gate
    start_time: float
    end_time: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "ok"  # ok, error
    metadata: dict[str, Any] = field(default_factory=dict)
    # Bytes que ESTE span poe na janela de contexto, e a formula que os produziu.
    # Nao e "o que o modelo viu": o host reserializa com espacamento proprio, e
    # afirmar que sao o mesmo numero seria a mentira confortavel desta fase.
    payload_bytes: int = 0
    payload_basis: str = ""
    # O que a chamada PEDIU. Vazio quando a tool nao aceita o parametro -- vazio
    # aqui significa "nao se aplica", e nao "pediu full".
    detail_level: str = ""
    # `None` e nao `0`: zero item e uma resposta vazia de verdade, e ausencia e a
    # tool que nao declara `returned_count`.
    item_count: int | None = None
    # Dado fino de tool. `status` (linha acima) e o resumo binario que a Task 2
    # deriva dele: "ok" se `outcome == "ok"`, senao "error".
    outcome: str = "ok"  # ok, unauthorized, error
    # Custo so pode existir com a fonte do preco nomeada. Ver `end_span`.
    cost_basis: str = ""
    # Status de medicao dos campos de token. `""` = nao declarado; o valor
    # efetivo sai por `resolved_tokens_status()`/`tokens_status_of`, nunca cru.
    tokens_status: str = ""

    def duration_seconds(self) -> float:
        if self.end_time:
            return max(0.0, self.end_time - self.start_time)
        return 0.0

    def resolved_tokens_status(self) -> str:
        return tokens_status_of(
            self.component_type,
            self.input_tokens,
            self.output_tokens,
            self.cached_tokens,
            self.tokens_status,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duration_seconds"] = self.duration_seconds()
        d["tokens_status"] = self.resolved_tokens_status()
        return d


@dataclass
class ExecutionTrace:
    run_id: str
    task_description: str
    start_time: float
    end_time: float | None = None
    profile: str = "eco"
    status: str = "running"
    spans: list[TraceSpan] = field(default_factory=list)

    def total_tokens(self) -> int:
        return sum(s.input_tokens + s.output_tokens for s in self.spans)

    def total_cost_usd(self) -> float:
        return round(sum(s.estimated_cost_usd for s in self.spans), 6)

    def measured_total_tokens(self) -> int | None:
        """Soma so os spans `measured`. `None` quando nenhum span foi medido --
        `None` e nao 0, porque 0 no banco afirmaria um usage que nao existiu."""
        measured = [s for s in self.spans if s.resolved_tokens_status() == "measured"]
        if not measured:
            return None
        return sum(s.input_tokens + s.output_tokens for s in measured)

    def measured_total_cost_usd(self) -> float | None:
        """Soma so os spans com `cost_basis`. Sem fonte de preco em nenhum
        span, o total e `None` -- nunca 0.0, que seria "custo medido: zero"."""
        priced = [s for s in self.spans if s.cost_basis]
        if not priced:
            return None
        return round(sum(s.estimated_cost_usd for s in priced), 6)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_tokens"] = self.measured_total_tokens()
        d["total_cost_usd"] = self.measured_total_cost_usd()
        return d


class AgentOpsTracker:
    """Manages active traces and local spans."""

    def start_trace(self, task_description: str, profile: str = "eco") -> ExecutionTrace:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        trace = ExecutionTrace(
            run_id=run_id,
            task_description=task_description,
            start_time=time.time(),
            profile=profile,
        )
        return trace

    def start_span(
        self,
        trace: ExecutionTrace,
        name: str,
        component_type: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TraceSpan:
        span = TraceSpan(
            span_id=f"span_{uuid.uuid4().hex[:8]}",
            run_id=trace.run_id,
            parent_span_id=parent_span_id,
            name=name,
            component_type=component_type,
            start_time=time.time(),
            metadata=metadata or {},
        )
        trace.spans.append(span)
        return span

    def end_span(
        self,
        span: TraceSpan,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        status: str = "ok",
        cost_basis: str = "",
        tokens_status: str = "",
    ) -> None:
        """Fecha o span. Custo diferente de zero EXIGE `cost_basis`.

        Preco sem fonte e o numero inventado que o subprojeto E recusou por
        escrito, e um span de tool nao tem preco nenhum: chamada local nao tem
        tabela publicada. Zero nao afirma preco, entao dispensa a fonte.

        `tokens_status` declara a medicao de usage: `"measured"` quando o
        provider/host reportou usage (inclusive 0), `"unresolved"` quando nao
        reportou, `"not_applicable"` para spans que nao carregam token. Vazio
        deriva por `tokens_status_of` -- e um span de `model` que nao declara
        usage vira `unresolved`, nunca "0 medido".
        """
        if estimated_cost_usd and not cost_basis:
            raise ValueError(
                f"custo {estimated_cost_usd} sem `cost_basis`: preco sem fonte e "
                f"numero inventado. Nomeie de onde o preco veio (ex.: a tabela "
                f"publicada do provider, com a data da leitura) ou deixe o custo em zero."
            )
        if tokens_status and tokens_status not in TOKEN_STATUS_VALUES:
            raise ValueError(
                f"tokens_status '{tokens_status}' fora do vocabulario {TOKEN_STATUS_VALUES}"
            )
        span.end_time = time.time()
        span.input_tokens = input_tokens
        span.output_tokens = output_tokens
        span.cached_tokens = cached_tokens
        span.estimated_cost_usd = estimated_cost_usd
        span.cost_basis = cost_basis
        span.tokens_status = tokens_status
        span.status = status

    def finish_trace(self, trace: ExecutionTrace, status: str = "completed") -> None:
        trace.end_time = time.time()
        trace.status = status
