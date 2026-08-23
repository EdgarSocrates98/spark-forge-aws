"""Bounded autonomy and policy-driven routing for SparkForge agents."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


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

    def route(
        self,
        *,
        goal: str,
        available_agents: Iterable[str],
        completed: set[str] | None = None,
        evidence_count: int = 0,
        risk: str = "low",
    ) -> RouteDecision:
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
        return RouteDecision(
            phase,
            selected,
            f"next unmet phase: {phase}",
            effort,
            self.focus_for_goal(goal),
        )

    def should_stop(
        self,
        *,
        iteration: int,
        tokens_used: int,
        progress: int,
        stagnant_iterations: int,
        terminal: bool = False,
    ) -> StopDecision:
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

    def authorize_tool(
        self,
        *,
        agent: str,
        tool: str,
        allowed_tools: Iterable[str],
        mutating: bool = False,
        approval: bool = False,
    ) -> tuple[bool, str]:
        if tool not in set(allowed_tools):
            return False, "tool not allowlisted for agent"
        if mutating and not approval:
            return False, "mutating action requires approval"
        return True, "authorized"


# --------------------------------------------------------------------------- #
# Classe de tool e cadeia de autorizacao (secoes 40 e 76 do prompt de harness)
# --------------------------------------------------------------------------- #


class ToolClass(str, Enum):
    """As cinco classes da secao 40, DERIVADAS das anotacoes MCP.

    Nao ha lista paralela: `sparkforge/adapters/tools.py` ja declara
    `readOnlyHint`, `openWorldHint` e `destructiveHint` em cada tool, e essas
    tres dimensoes definem a classe. Manter uma segunda tabela a mao seria a
    familia de defeito que a Fase 5c achou nos dois `EXTRACTORS` mantidos em
    paralelo: uma cresce, a outra nao, e o desacordo e mudo.

    Duas nascem VAZIAS -- nenhuma tool de hoje e `destructive`, e nenhuma e
    mutante E de nuvem. Isso e o resultado, nao lacuna: o valor da classificacao
    agora nao e bloquear o que existe, e impedir que uma tool futura entre sem
    classe.
    """

    READ_ONLY = "READ_ONLY"
    CLOUD_READ = "CLOUD_READ"
    LOCAL_MUTATION = "LOCAL_MUTATION"
    CLOUD_MUTATION = "CLOUD_MUTATION"
    DESTRUCTIVE = "DESTRUCTIVE"


# Classes que o perfil OFFLINE recusa, com aprovacao ou sem. O perfil e TETO,
# nao preferencia: se aprovacao furasse o teto, OFFLINE deixaria de significar
# "zero rede" na primeira aprovacao distraida.
_CLASSES_DE_REDE = frozenset({ToolClass.CLOUD_READ, ToolClass.CLOUD_MUTATION})

# Classes que exigem aprovacao explicita POR CLASSE. `READ_ONLY` fica de fora:
# leitura local e o default permitido da secao 40.
_EXIGEM_APROVACAO = frozenset(
    {
        ToolClass.LOCAL_MUTATION,
        ToolClass.CLOUD_READ,
        ToolClass.CLOUD_MUTATION,
        ToolClass.DESTRUCTIVE,
    }
)


def tool_class(tool: str) -> ToolClass:
    """A classe de uma tool, derivada da anotacao dela.

    `KeyError` para nome desconhecido, e isso e fail-closed deliberado: um
    default `READ_ONLY` para o que ninguem declarou e exatamente como uma tool
    nova entra sem classe -- e sem classe ela nao passa por aprovacao nenhuma.
    """
    from sparkforge.adapters.tools import TOOLS

    anotacoes = TOOLS[tool]["annotations"]
    if anotacoes.get("destructiveHint"):
        return ToolClass.DESTRUCTIVE
    de_nuvem = bool(anotacoes.get("openWorldHint"))
    somente_leitura = bool(anotacoes.get("readOnlyHint"))
    if somente_leitura:
        return ToolClass.CLOUD_READ if de_nuvem else ToolClass.READ_ONLY
    return ToolClass.CLOUD_MUTATION if de_nuvem else ToolClass.LOCAL_MUTATION


@dataclass(frozen=True)
class AuthorizationDecision:
    """A decisao, com a CADEIA que a sustentou.

    E isto que separa cadeia de checagem de um nivel: a decisao carrega o
    agente, o perfil e a aprovacao que a permitiu, entao um trace consegue
    responder "quem permitiu isso, e com base em que" sem reconstruir o estado
    do momento. `authorize_tool` respondia `(bool, str)` -- o `str` dizia o
    motivo da recusa, e nada dizia o motivo da PERMISSAO.
    """

    agent: str
    tool: str
    tool_class: ToolClass
    profile: str
    authorized: bool
    reason: str
    required_approval: ToolClass | None = None
    granted_by: ToolClass | None = None


def authorize(
    *,
    agent: str,
    tool: str,
    allowed_tools: Iterable[str],
    profile: str,
    approvals: Iterable[ToolClass] = (),
) -> AuthorizationDecision:
    """Autoriza uma chamada de tool, com a cadeia registrada na decisao.

    `approvals` e por CLASSE, e nao um booleano. O `approval=True` de
    `authorize_tool` aprovava mutacao local e escrita na nuvem de uma vez, e era
    essa a lacuna que a secao 76 nomeia: sem escopo, a aprovacao dada para uma
    coisa vale para outra.
    """
    classe = tool_class(tool)
    aprovadas = frozenset(approvals)

    if tool not in set(allowed_tools):
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=profile,
            authorized=False,
            reason="tool fora da allowlist do agente",
        )

    if profile == "OFFLINE" and classe in _CLASSES_DE_REDE:
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=profile,
            authorized=False,
            reason=(
                "perfil OFFLINE recusa tool de rede, com aprovacao ou sem: o "
                "perfil e teto, nao preferencia"
            ),
        )

    if classe in _EXIGEM_APROVACAO and classe not in aprovadas:
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=profile,
            authorized=False,
            reason=f"classe {classe.value} exige aprovacao explicita para esta classe",
            required_approval=classe,
        )

    return AuthorizationDecision(
        agent=agent,
        tool=tool,
        tool_class=classe,
        profile=profile,
        authorized=True,
        reason="autorizado",
        granted_by=classe if classe in _EXIGEM_APROVACAO else None,
    )
