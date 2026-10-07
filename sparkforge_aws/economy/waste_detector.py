"""Token Waste Detector for SparkForge Economy Engine.

SEM NUMERO INVENTADO. A versao anterior estimava tokens desperdicados com
constantes fixas (500 por chamada repetida) e custo com tabelas de preco que
ninguem declarou ($0.80/Mtok, $15/Mtok) -- numeros fabricados que pareciam
medicao. O detector so afirma o que mediu: `observed_wasted_tokens` soma os
tokens que os proprios eventos registraram nas chamadas redundantes; custo
estimado so existe com uma fonte de preco nomeada, e aqui nenhuma existe --
`estimated_wasted_cost_usd` fica `None` com `measurement_status.cost =
"unresolved"`.

CLASSIFICACAO. `observed` quando o padrao e medido nos eventos (chamada
repetida com os mesmos argumentos); `hypothesis` quando a afirmacao de
desperdicio depende de uma alternativa que nao foi executada (um modelo mais
barato TALVEZ bastasse -- "talvez" nao e medida).

Cobertura equivalente existe em `observability/agentops._waste`, que le spans
persistidos em vez de eventos e usa os padroes `duplicate_tool_call` /
`premium_model_on_simple_task` / `empty_context_payload`. As duas superficies
classificam com o mesmo vocabulario `observed`/`hypothesis`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WasteFinding:
    pattern_id: str
    title: str
    severity: str  # P0, P1, P2, P3
    description: str
    recommendation: str
    classification: str = "observed"  # observed | hypothesis
    observed_wasted_tokens: int | None = None
    estimated_wasted_tokens: int | None = None
    estimated_wasted_cost_usd: float | None = None
    measurement_status: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "classification": self.classification,
            "observed_wasted_tokens": self.observed_wasted_tokens,
            "estimated_wasted_tokens": self.estimated_wasted_tokens,
            "estimated_wasted_cost_usd": self.estimated_wasted_cost_usd,
            "measurement_status": dict(self.measurement_status),
        }


class TokenWasteDetector:
    """Detects inefficiencies, redundant calls, and token leaks in execution traces."""

    def analyze_trace(self, trace_events: list[dict[str, Any]]) -> list[WasteFinding]:
        findings: list[WasteFinding] = []

        seen_tool_calls: dict[str, list[int | None]] = {}
        premium_calls_on_simple_tasks: list[int | None] = []

        for event in trace_events:
            event_type = event.get("type", "")
            tokens = event.get("tokens")
            tokens = int(tokens) if isinstance(tokens, (int, float)) else None

            if event_type == "tool_call":
                tool_name = event.get("name", "")
                tool_args = str(event.get("args", {}))
                key = f"{tool_name}:{tool_args}"
                seen_tool_calls.setdefault(key, []).append(tokens)

            if event_type == "model_call":
                tier = event.get("tier", "")
                task_complexity = event.get("task_complexity", "low")
                if tier == "tier_5_premium" and task_complexity in ("low", "deterministic"):
                    premium_calls_on_simple_tasks.append(tokens)

        # Check repeated identical tool calls
        for key, token_list in seen_tool_calls.items():
            if len(token_list) > 2:
                redundant = token_list[1:]
                observed = (
                    sum(t for t in redundant if t is not None)
                    if all(t is not None for t in redundant)
                    else None
                )
                findings.append(
                    WasteFinding(
                        pattern_id="WASTE-001",
                        title=f"Identical tool call repeated {len(token_list)} times",
                        severity="P1",
                        description=(
                            f"Tool call '{key[:60]}...' executed {len(token_list)} times "
                            f"with identical arguments."
                        ),
                        recommendation=(
                            "Enable Tier 1 ArtifactCache to avoid repeated identical "
                            "tool runs."
                        ),
                        classification="observed",
                        observed_wasted_tokens=observed,
                        measurement_status={
                            "tokens": "measured" if observed is not None else "unresolved",
                            "cost": "unresolved",
                        },
                    )
                )

        # Check premium model misuse
        if premium_calls_on_simple_tasks:
            findings.append(
                WasteFinding(
                    pattern_id="WASTE-002",
                    title="Expensive model used for simple/deterministic task",
                    severity="P1",
                    description=(
                        f"Detected {len(premium_calls_on_simple_tasks)} Tier 5 calls on "
                        f"low complexity tasks."
                    ),
                    recommendation=(
                        "Route to Tier 3 cheap model or Tier 0 deterministic tool."
                    ),
                    classification="hypothesis",
                    measurement_status={"tokens": "unresolved", "cost": "unresolved"},
                )
            )

        return findings


__all__ = ["TokenWasteDetector", "WasteFinding"]
