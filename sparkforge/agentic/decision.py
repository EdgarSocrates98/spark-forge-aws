"""Decision Engine — decisão auditável com ADR automático.

Toda decisão registra:
- options consideradas (não apenas a selecionada)
- evidence que sustenta a escolha
- debate que contestou (se houve)
- experiments que validaram (se houve)
- risks, assumptions, unknowns
- validation e rollback
- falsification_condition: sob que condição esta decisão seria revertida

ADR (Architecture Decision Record) é gerado automaticamente para decisões
significativas. Decisões triviais não geram ADR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.agentic.models import Decision


@dataclass
class DecisionContext:
    """Contexto para tomar uma decisão.

    Reúne tudo que o decision engine precisa:
    - problem: o que decidir
    - options: alternativas consideradas
    - evidence_refs: evidência suportando cada option
    - debate_id: debate que contestou (se houve)
    - experiment_ids: experimentos que validaram (se houve)
    - risks, assumptions, unknowns
    - runtime: RuntimeContext snapshot
    """

    problem: str
    options: list[str]
    evidence_by_option: dict[str, list[str]] = field(default_factory=dict)
    debate_id: str | None = None
    experiment_ids: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    runtime: dict[str, Any] = field(default_factory=dict)
    decided_by: str = ""
    created_at: str = ""


def make_decision(
    ctx: DecisionContext,
    selected_option: str,
    confidence: str = "medium",
    validation: str = "",
    rollback: str = "",
    falsification_condition: str = "",
) -> Decision:
    """Cria uma Decision auditável.

    Validações:
    - selected_option deve estar em options
    - rollback é obrigatório (ou "irreversible: <motivo>")
    - rejected_options são todos os outros options

    Args:
        ctx: DecisionContext com problem, options, evidence, etc.
        selected_option: opção escolhida (deve estar em ctx.options)
        confidence: high/medium/low
        validation: como validar a decisão
        rollback: como reverter (ou "irreversible: <motivo>")
        falsification_condition: sob que condição reverter

    Returns:
        Decision dataclass
    """
    if selected_option not in ctx.options:
        raise ValueError(
            f"make_decision: selected_option {selected_option!r} não está em options"
        )

    if not rollback.strip():
        raise ValueError(
            "make_decision: rollback é obrigatório. "
            "Use 'irreversible: <motivo>' se a decisão é irreversível."
        )

    rejected = [o for o in ctx.options if o != selected_option]
    evidence_refs = ctx.evidence_by_option.get(selected_option, [])

    return Decision(
        problem=ctx.problem,
        options=ctx.options,
        selected_option=selected_option,
        rejected_options=rejected,
        evidence_refs=evidence_refs,
        debate_id=ctx.debate_id,
        experiment_ids=ctx.experiment_ids,
        risks=ctx.risks,
        assumptions=ctx.assumptions,
        unknowns=ctx.unknowns,
        confidence=confidence,
        runtime=ctx.runtime,
        validation=validation,
        rollback=rollback,
        falsification_condition=falsification_condition,
        decided_by=ctx.decided_by,
        created_at=ctx.created_at,
    )


def generate_adr(decision: Decision, adr_id: str = "") -> str:
    """Gera um Architecture Decision Record em Markdown.

    Formato ADR padrão (Michael Nygard):
    - Title
    - Status
    - Context
    - Decision
    - Consequences
    - Alternatives
    - Evidence
    - Validation
    - Rollback
    - Falsification
    """
    if not adr_id:
        adr_id = decision.id

    lines: list[str] = []
    lines.append(f"# ADR-{adr_id}: {decision.problem}")
    lines.append("")
    lines.append("## Status")
    lines.append(f"{'Accepted' if decision.confidence != 'low' else 'Proposed'}")
    lines.append("")
    lines.append("## Context")
    lines.append(f"{decision.problem}")
    lines.append("")
    if decision.runtime:
        lines.append("### Runtime")
        for k, v in sorted(decision.runtime.items()):
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.append("## Decision")
    lines.append(f"**Selected:** {decision.selected_option}")
    lines.append("")
    lines.append("## Alternatives Considered")
    for opt in decision.rejected_options:
        lines.append(f"- {opt}")
    lines.append("")

    if decision.evidence_refs:
        lines.append("## Evidence")
        for ref in decision.evidence_refs:
            lines.append(f"- {ref}")
        lines.append("")

    if decision.risks:
        lines.append("## Risks")
        for risk in decision.risks:
            lines.append(f"- {risk}")
        lines.append("")

    if decision.assumptions:
        lines.append("## Assumptions")
        for a in decision.assumptions:
            lines.append(f"- {a}")
        lines.append("")

    if decision.unknowns:
        lines.append("## Unknowns")
        for u in decision.unknowns:
            lines.append(f"- {u}")
        lines.append("")

    lines.append("## Validation")
    lines.append(decision.validation or "_Not specified_")
    lines.append("")
    lines.append("## Rollback")
    lines.append(decision.rollback)
    lines.append("")
    if decision.falsification_condition:
        lines.append("## Falsification Condition")
        lines.append(decision.falsification_condition)
        lines.append("")

    if decision.debate_id:
        lines.append("## Debate")
        lines.append(f"Debate ID: {decision.debate_id}")
        lines.append("")

    if decision.experiment_ids:
        lines.append("## Experiments")
        for exp_id in decision.experiment_ids:
            lines.append(f"- {exp_id}")
        lines.append("")

    lines.append("---")
    lines.append(f"Decided by: {decision.decided_by or 'unknown'}")
    lines.append(f"Created at: {decision.created_at or 'unknown'}")
    lines.append(f"Confidence: {decision.confidence}")

    return "\n".join(lines)


def is_significant_decision(decision: Decision) -> bool:
    """Determina se uma decisão é significativa o suficiente para gerar ADR.

    Critérios:
    - confidence != high (incerta)
    - tem risks
    - tem debate
    - tem experiments
    - é production-impacting (rollback não trivial)
    - é destructive (rollback começa com "irreversible")
    """
    if decision.confidence != "high":
        return True
    if decision.risks:
        return True
    if decision.debate_id:
        return True
    if decision.experiment_ids:
        return True
    if decision.rollback.startswith("irreversible"):
        return True
    if len(decision.options) > 2:
        return True
    return False
