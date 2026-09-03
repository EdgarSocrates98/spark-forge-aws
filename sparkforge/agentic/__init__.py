"""Agentic Engineering Runtime — camada agêntica do SparkForge.

Esta camada adiciona entidades de primeira classe para o ciclo agêntico:
Claim, Evidence, Hypothesis, Experiment, Decision, Unknown, Contradiction,
Objection, Rebuttal. Ela não substitui a camada determinística (Fact, Finding,
Rule) — a estende com juízo estruturado, debate, experimentação e decisão
auditável.

Princípios:
- Nenhum agente é confiável apenas por ser especialista.
- Uma conclusão só é confiável quando sobrevive à evidência, revisão cruzada,
  contestação adversarial e validação.
- Unknown nunca vira fact por conveniência.
- Toda decisão é auditável e reversível (ou declara irreversível).
- Budget é finito e enforced.
- Runtime-independente: Claude, Devin, Copilot, Codex executam o mesmo protocolo.

Módulos:
- models: Claim, Evidence, Hypothesis, Experiment, Decision, Unknown, etc.
- runtime: AgentRuntime protocol, capability negotiation
- evidence: Source Authority Engine (TIER 1-6)
- blackboard: Shared Blackboard (directory-based case state)
- debate: Debate Engine (Opening→Claim→Objection→Rebuttal→Verdict)
- arbitration: Arbitration + false consensus detection
- experiment: Experiment Designer
- decision: Decision Engine + ADR automático
- memory: Decision Memory (working/case/institutional)
- budget: Unified token economics (AgentBudget, CaseBudget, DebateBudget)
- security: Threat model + guardrails
- autonomy: L0-L5 autonomy levels
- graph: Agent Execution Graph (typed nodes/edges)
"""

from __future__ import annotations

from sparkforge.agentic.models import (
    Claim,
    ClaimType,
    Contradiction,
    Decision,
    Evidence,
    EvidenceAuthority,
    Experiment,
    ExperimentStatus,
    Hypothesis,
    HypothesisStatus,
    Objection,
    Rebuttal,
    Unknown,
    UnknownStatus,
)

__all__ = [
    "Claim",
    "ClaimType",
    "Contradiction",
    "Decision",
    "Evidence",
    "EvidenceAuthority",
    "Experiment",
    "ExperimentStatus",
    "Hypothesis",
    "HypothesisStatus",
    "Objection",
    "Rebuttal",
    "Unknown",
    "UnknownStatus",
]
