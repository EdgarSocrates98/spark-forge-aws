"""Autonomy Levels — L0 a L5.

Cada nível declara:
- allowed_actions
- budget
- risk
- approval_policy
- required_validation

L5 (autonomous engineering) não é permitido automaticamente para high-risk
actions sem guardrails.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum


class AutonomyLevel(str, Enum):
    L0_DETERMINISTIC = "L0"
    L1_SPECIALIST = "L1"
    L2_COOPERATIVE = "L2"
    L3_DEBATE = "L3"
    L4_EXPERIMENTAL = "L4"
    L5_AUTONOMOUS = "L5"


@dataclass
class AutonomyProfile:
    """Perfil de um nível de autonomia.

    Define o que um agente neste nível pode fazer.
    """

    level: AutonomyLevel
    name: str
    description: str
    allowed_actions: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    max_budget_tokens: int = 4000
    max_agents: int = 1
    max_debates: int = 0
    max_experiments: int = 0
    approval_policy: str = "none"  # none | post_hoc | pre_approval
    required_validation: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low | medium | high | critical


# Perfis por nível
_PROFILES: dict[AutonomyLevel, AutonomyProfile] = {
    AutonomyLevel.L0_DETERMINISTIC: AutonomyProfile(
        level=AutonomyLevel.L0_DETERMINISTIC,
        name="Deterministic",
        description="Extração e julgamento determinístico. Sem LLM.",
        allowed_actions=["extract_facts", "judge_rules", "validate_output"],
        forbidden_actions=["spawn_agent", "debate", "experiment", "modify_code"],
        max_budget_tokens=0,  # no LLM tokens
        max_agents=1,
        approval_policy="none",
        required_validation=["schema_validation", "evidence_validation"],
        risk_level="low",
    ),
    AutonomyLevel.L1_SPECIALIST: AutonomyProfile(
        level=AutonomyLevel.L1_SPECIALIST,
        name="Specialist",
        description="Análise de domínio único. Um agente, sem debate.",
        allowed_actions=["analyze", "extract_facts", "judge_rules", "recommend"],
        forbidden_actions=["spawn_agent", "debate", "experiment", "deploy"],
        max_budget_tokens=4000,
        max_agents=1,
        approval_policy="none",
        required_validation=["schema_validation", "evidence_validation", "output_validation"],
        risk_level="low",
    ),
    AutonomyLevel.L2_COOPERATIVE: AutonomyProfile(
        level=AutonomyLevel.L2_COOPERATIVE,
        name="Cooperative",
        description="Análise cross-domain. Múltiplos agentes, sem debate.",
        allowed_actions=["analyze", "extract_facts", "judge_rules", "recommend", "spawn_agent"],
        forbidden_actions=["debate", "experiment", "deploy"],
        max_budget_tokens=16000,
        max_agents=3,
        approval_policy="none",
        required_validation=[
            "schema_validation",
            "evidence_validation",
            "output_validation",
            "scope_validation",
        ],
        risk_level="medium",
    ),
    AutonomyLevel.L3_DEBATE: AutonomyProfile(
        level=AutonomyLevel.L3_DEBATE,
        name="Debate",
        description="Debate multi-agente. Revisão adversarial.",
        allowed_actions=[
            "analyze",
            "extract_facts",
            "judge_rules",
            "recommend",
            "spawn_agent",
            "debate",
        ],
        forbidden_actions=["experiment", "deploy", "destructive_action"],
        max_budget_tokens=32000,
        max_agents=5,
        max_debates=2,
        approval_policy="post_hoc",
        required_validation=[
            "schema_validation",
            "evidence_validation",
            "output_validation",
            "scope_validation",
            "debate_validation",
        ],
        risk_level="medium",
    ),
    AutonomyLevel.L4_EXPERIMENTAL: AutonomyProfile(
        level=AutonomyLevel.L4_EXPERIMENTAL,
        name="Experimental",
        description="Executa experimentos para resolver desacordo.",
        allowed_actions=[
            "analyze",
            "extract_facts",
            "judge_rules",
            "recommend",
            "spawn_agent",
            "debate",
            "experiment",
        ],
        forbidden_actions=["deploy", "destructive_action", "production_change"],
        max_budget_tokens=64000,
        max_agents=5,
        max_debates=3,
        max_experiments=3,
        approval_policy="pre_approval",
        required_validation=[
            "schema_validation",
            "evidence_validation",
            "output_validation",
            "scope_validation",
            "debate_validation",
            "experiment_validation",
        ],
        risk_level="high",
    ),
    AutonomyLevel.L5_AUTONOMOUS: AutonomyProfile(
        level=AutonomyLevel.L5_AUTONOMOUS,
        name="Autonomous Engineering",
        description="Auto-modifica agentes/código. Máxima autonomia com guardrails.",
        allowed_actions=[
            "analyze",
            "extract_facts",
            "judge_rules",
            "recommend",
            "spawn_agent",
            "debate",
            "experiment",
            "modify_code",
        ],
        forbidden_actions=["deploy_without_approval", "destructive_action_without_approval"],
        max_budget_tokens=128000,
        max_agents=10,
        max_debates=5,
        max_experiments=10,
        approval_policy="pre_approval",
        required_validation=[
            "schema_validation",
            "evidence_validation",
            "output_validation",
            "scope_validation",
            "debate_validation",
            "experiment_validation",
            "security_validation",
            "human_approval",
        ],
        risk_level="critical",
    ),
}


def get_profile(level: AutonomyLevel) -> AutonomyProfile:
    """Retorna o perfil de um nível de autonomia."""
    return _PROFILES.get(level, _PROFILES[AutonomyLevel.L0_DETERMINISTIC])


def can_perform_action(level: AutonomyLevel, action: str) -> bool:
    """Verifica se um nível de autonomia permite uma ação."""
    profile = get_profile(level)
    return action in profile.allowed_actions


def requires_approval_for_action(level: AutonomyLevel, action: str) -> bool:
    """Verifica se uma ação requer aprovação no nível dado."""
    profile = get_profile(level)
    if profile.approval_policy == "none":
        return False
    if profile.approval_policy == "pre_approval":
        return action in ("experiment", "modify_code", "deploy", "destructive_action")
    if profile.approval_policy == "post_hoc":
        return action in ("deploy", "destructive_action")
    return False


def validate_autonomy_boundary(
    level: AutonomyLevel,
    action: str,
    is_high_risk: bool = False,
    guardrails_satisfied: Iterable[str] | None = None,
) -> tuple[bool, str]:
    """Valida que uma ação está dentro do boundary de autonomia.

    `guardrails_satisfied` é o que o CHAMADOR comprova ter executado —
    aprovação humana obtida, validação de schema rodada, etc. A ação de alto
    risco só passa quando cobre o `required_validation` do perfil.

    Até 2026-09-03 a checagem de alto risco era `if "human_approval" not in
    profile.required_validation`, lida do perfil ESTÁTICO do próprio L5, que
    sempre contém `human_approval` — o ramo nunca podia disparar, e
    `validate_autonomy_boundary(L5, "modify_code", is_high_risk=True)`
    devolvia `(True, "")` sem que nada tivesse sido aprovado. Guardrail que
    valida a si mesmo não é guardrail.

    Retorna (allowed, reason).
    """
    profile = get_profile(level)

    if action in profile.forbidden_actions:
        return False, f"Ação {action!r} é proibida no nível {level.value}."

    if action not in profile.allowed_actions:
        return False, f"Ação {action!r} não está permitida no nível {level.value}."

    if is_high_risk:
        satisfeitos = set(guardrails_satisfied or ())
        faltando = [g for g in profile.required_validation if g not in satisfeitos]
        if faltando:
            return False, (
                f"Ação {action!r} de alto risco no nível {level.value} exige "
                f"guardrails não comprovados pelo chamador: {', '.join(faltando)}."
            )

    if requires_approval_for_action(level, action):
        satisfeitos = set(guardrails_satisfied or ())
        if "human_approval" not in satisfeitos:
            return False, (
                f"Ação {action!r} no nível {level.value} tem approval_policy "
                f"{profile.approval_policy!r} e exige `human_approval` comprovado."
            )

    return True, ""
