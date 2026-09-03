"""Debate Engine — protocolo formal de debate entre agentes.

Protocolo:
```
Opening → Claim → Objection → Rebuttal → Revision → Final Position → Verdict
```

Debate não é automático para toda tarefa. Triggers:
- contradictory findings
- confidence below threshold
- high-risk action
- production-impacting change
- destructive action
- evidence conflict
- cross-domain conflict

Debate tem budget finito: max rounds, max tokens, stop condition.
Não aumenta rounds infinitamente. Se deadlock:
1. Summarize disagreement
2. Identify root disagreement
3. Identify missing evidence
4. Design an experiment
5. Escalate if needed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sparkforge.agentic.models import Claim, Objection, Rebuttal


class DebateStatus(str, Enum):
    OPEN = "open"
    CONSENSUS = "consensus"  # agreement reached
    RESOLVED = "resolved"  # resolved by arbitration or evidence
    DEADLOCKED = "deadlocked"  # no consensus, escalate
    ABANDONED = "abandoned"  # budget exhausted or cancelled


class DebateTrigger(str, Enum):
    CONTRADICTORY_FINDINGS = "contradictory_findings"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_RISK = "high_risk"
    PRODUCTION_IMPACT = "production_impact"
    DESTRUCTIVE_ACTION = "destructive_action"
    EVIDENCE_CONFLICT = "evidence_conflict"
    CROSS_DOMAIN_CONFLICT = "cross_domain_conflict"
    MANUAL = "manual"


@dataclass
class DebateBudget:
    """Budget finito para debate. Enforced — não aumenta infinitamente."""

    max_rounds: int = 3
    max_tokens_per_round: int = 2000
    max_total_tokens: int = 8000
    max_objections_per_round: int = 3
    max_rebuttals_per_objection: int = 1

    def __post_init__(self) -> None:
        if self.max_rounds < 1:
            raise ValueError("DebateBudget: max_rounds deve ser >= 1")
        if self.max_rounds > 10:
            raise ValueError("DebateBudget: max_rounds > 10 é irracional — debate não converge")


@dataclass
class DebateRound:
    """Uma rodada de debate."""

    round_number: int
    claims: list[Claim] = field(default_factory=list)
    objections: list[Objection] = field(default_factory=list)
    rebuttals: list[Rebuttal] = field(default_factory=list)
    tokens_used: int = 0


@dataclass
class Debate:
    """Debate formal entre agentes.

    Um debate tem:
    - topic: o que está sendo debatido
    - participants: agentes envolvidos
    - rounds: rodadas executadas
    - budget: limites enforced
    - status: open/consensus/resolved/deadlocked/abandoned
    - verdict: conclusão final (se houver)
    """

    topic: str
    participants: list[str]  # agent_ids
    trigger: DebateTrigger
    budget: DebateBudget = field(default_factory=DebateBudget)
    rounds: list[DebateRound] = field(default_factory=list)
    status: DebateStatus = DebateStatus.OPEN
    verdict: str = ""
    root_disagreement: str = ""
    missing_evidence: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("Debate: topic vazio.")
        if len(self.participants) < 2:
            raise ValueError(f"Debate: requer >= 2 participantes, tem {len(self.participants)}")
        if not isinstance(self.trigger, DebateTrigger):
            raise ValueError("Debate: trigger deve ser DebateTrigger")
        if not isinstance(self.status, DebateStatus):
            raise ValueError("Debate: status deve ser DebateStatus")

    @property
    def id(self) -> str:
        import hashlib
        import json

        payload = json.dumps(
            {"topic": self.topic, "participants": sorted(self.participants)},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        h = hashlib.sha1(payload, usedforsecurity=False).hexdigest()
        return f"debate_{h[:8]}"

    @property
    def current_round(self) -> int:
        return len(self.rounds)

    @property
    def budget_exhausted(self) -> bool:
        if self.current_round >= self.budget.max_rounds:
            return True
        total_tokens = sum(r.tokens_used for r in self.rounds)
        if total_tokens >= self.budget.max_total_tokens:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "participants": list(self.participants),
            "trigger": self.trigger.value,
            "status": self.status.value,
            "budget": {
                "max_rounds": self.budget.max_rounds,
                "max_total_tokens": self.budget.max_total_tokens,
            },
            "rounds": [
                {
                    "round_number": r.round_number,
                    "claims": [c.id for c in r.claims],
                    "objections": [o.id for o in r.objections],
                    "rebuttals": [rb.id for rb in r.rebuttals],
                    "tokens_used": r.tokens_used,
                }
                for r in self.rounds
            ],
            "verdict": self.verdict,
            "root_disagreement": self.root_disagreement,
            "missing_evidence": list(self.missing_evidence),
            "created_at": self.created_at,
        }


def should_trigger_debate(
    findings: list[dict[str, Any]],
    confidence: str = "high",
    is_high_risk: bool = False,
    is_destructive: bool = False,
    is_production_impact: bool = False,
    has_evidence_conflict: bool = False,
    has_cross_domain_conflict: bool = False,
) -> DebateTrigger | None:
    """Decide se debate deve ser triggered.

    Retorna o trigger ou None se debate não é necessário.
    Tarefas simples de baixo risco não trigger debate.
    """
    # Destructive action → sempre debate
    if is_destructive:
        return DebateTrigger.DESTRUCTIVE_ACTION

    # High risk → debate
    if is_high_risk:
        return DebateTrigger.HIGH_RISK

    # Production impact → debate
    if is_production_impact:
        return DebateTrigger.PRODUCTION_IMPACT

    # Evidence conflict → debate
    if has_evidence_conflict:
        return DebateTrigger.EVIDENCE_CONFLICT

    # Cross-domain conflict → debate
    if has_cross_domain_conflict:
        return DebateTrigger.CROSS_DOMAIN_CONFLICT

    # Contradictory findings → debate
    # Detecta: dois findings com mesmo subject mas severity/status diferente
    if len(findings) >= 2:
        subjects: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            subj = json.dumps(f.get("subject", {}), sort_keys=True)
            subjects.setdefault(subj, []).append(f)
        for _subj, group in subjects.items():
            if len(group) >= 2:
                severities = {g.get("severity") for g in group}
                if len(severities) > 1:
                    return DebateTrigger.CONTRADICTORY_FINDINGS

    # Low confidence → debate apenas se há recomendação
    if confidence == "low":
        has_recommendation = any(f.get("proposed_change") for f in findings)
        if has_recommendation:
            return DebateTrigger.LOW_CONFIDENCE

    return None


def deadlock_resolution(debate: Debate) -> dict[str, Any]:
    """Resolve deadlock: não aumenta rounds, produz plano de escalada.

    Retorna um plano com:
    - summary: resumo do desacordo
    - root_disagreement: ponto fundamental de divergência
    - missing_evidence: evidência que resolveria
    - next_step: experiment | arbitration | human_escalation
    """
    if debate.status != DebateStatus.DEADLOCKED:
        raise ValueError(
            f"deadlock_resolution: debate status={debate.status.value}, esperado=deadlocked"
        )

    # Coleta claims não contestadas (potential consensus)
    all_objection_targets: set[str] = set()
    for r in debate.rounds:
        for o in r.objections:
            all_objection_targets.add(o.target_claim)

    uncontested: list[str] = []
    for r in debate.rounds:
        for c in r.claims:
            if c.id not in all_objection_targets:
                uncontested.append(c.statement)

    return {
        "debate_id": debate.id,
        "summary": f"Debate on '{debate.topic}' deadlocked after {debate.current_round} rounds.",
        "uncontested_claims": uncontested,
        "root_disagreement": debate.root_disagreement or "Root disagreement not yet identified.",
        "missing_evidence": debate.missing_evidence,
        "next_step": "experiment" if debate.missing_evidence else "human_escalation",
        "participants": debate.participants,
    }


# Necessário para should_trigger_debate
import json  # noqa: E402
