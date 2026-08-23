"""Bounded autonomy and policy-driven routing for SparkForge agents."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # So para a anotacao: em tempo de execucao o import continua LOCAL, dentro
    # das funcoes que precisam dele, para `import sparkforge.agents` nao passar
    # a arrastar o pacote `registry` inteiro por causa de um enum.
    from sparkforge.registry.models import ExecutionProfile


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

    `DESTRUCTIVE` nasce VAZIA -- nenhuma tool de hoje declara
    `destructiveHint`. Isso e o resultado, nao lacuna: o valor da
    classificacao agora nao e bloquear o que existe, e impedir que uma tool
    futura entre sem classe.

    NAO se mapeia para `sparkforge/registry/models.py:RiskLevel`, e a
    incompatibilidade e de EIXO, nao de granularidade: `RiskLevel`
    (`read_only/reversible/sensitive/destructive`) grada o quanto uma mutacao
    doi e nao tem dimensao de rede nenhuma; `ToolClass` cruza "muta?" com
    "sai da maquina?" e nao tem `reversible` nem `sensitive`. Nenhum dos dois
    e refinamento do outro, entao converter um no outro exige inventar o eixo
    que falta -- e inventa-lo sob prazo, no dia da ponte, e como uma
    classificacao de seguranca vira palpite. Hoje nao ha divergencia viva
    porque `CanonicalRegistry.load_from_configs()` nunca popula `self.tools`;
    se algum dia popular, esta nota e o aviso de que a unificacao e decisao de
    projeto, nao refactor mecanico.
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
    Quem precisa de DECISAO em vez de excecao chama `authorize()`, que traduz
    o `KeyError` numa recusa auditavel (ver la).

    O import de `TOOLS` e local, e nao no topo do modulo, por duas razoes que
    valem a linha: `import sparkforge.agents` passaria a arrastar o catalogo
    inteiro de tools (e, por tabela, `facts`, `collect` e `rules`) so para
    quem quisesse `AutonomyBudget`; e a leitura em tempo de chamada e o que
    deixa o teste substituir o catalogo por um sintetico para exercitar
    classe que hoje nao tem tool nenhuma. Nao ha ciclo de import aqui -- a
    razao nao e essa.
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


def _perfil_canonico(profile: object) -> ExecutionProfile | None:
    """O `ExecutionProfile` que `profile` nomeia, ou `None` se nao nomeia
    nenhum.

    Existe porque comparar o perfil com o literal `"OFFLINE"` falhava ABERTO,
    e o modo da falha era silencioso: `ExecutionProfile` e `str, Enum` com
    valor MINUSCULO (`OFFLINE = "offline"`), entao o valor canonico do
    repositorio atravessava uma anotacao `profile: str` sem erro de tipo
    nenhum e comparava `False` -- o teto de rede sumia e a decisao saia
    gravada como `"autorizado"`, indistinguivel de permissao legitima.

    `str(ExecutionProfile.OFFLINE)` devolve `"ExecutionProfile.OFFLINE"`, e
    nao `"offline"`; por isso o teste de tipo vem antes, e a normalizacao por
    texto so alcanca `str` de verdade.

    Normaliza caixa porque as duas grafias ja circulam neste repositorio e
    recusar a maiuscula converteria um defeito de teto num defeito de
    disponibilidade. O que ela NAO faz e adivinhar: texto que nao nomeia
    perfil nenhum devolve `None`, e quem chama recusa.
    """
    from sparkforge.registry.models import ExecutionProfile

    if isinstance(profile, ExecutionProfile):
        return profile
    if isinstance(profile, str):
        try:
            return ExecutionProfile(profile.strip().lower())
        except ValueError:
            return None
    return None


def _teto_recusa_rede(perfil: ExecutionProfile) -> bool:
    """`True` quando o TETO daquele perfil proibe tool de rede.

    Funcao, e nao comparacao solta com `ExecutionProfile.OFFLINE` no meio de
    `authorize()`, por dois motivos: o conceito ganha nome (o perfil tem um
    teto, a tool tem uma classe, e o teto e que manda), e o dia em que um
    segundo perfil precisar do mesmo teto a mudanca acontece aqui, num lugar
    so, em vez de num `or` acrescentado a pressa dentro do fluxo de decisao.
    """
    from sparkforge.registry.models import ExecutionProfile

    return perfil is ExecutionProfile.OFFLINE


@dataclass(frozen=True)
class AuthorizationDecision:
    """A decisao, com a CADEIA que a sustentou.

    E isto que separa cadeia de checagem de um nivel: a decisao carrega o
    agente, o perfil e a aprovacao que a permitiu, entao um trace consegue
    responder "quem permitiu isso, e com base em que" sem reconstruir o estado
    do momento. `authorize_tool` respondia `(bool, str)` -- o `str` dizia o
    motivo da recusa, e nada dizia o motivo da PERMISSAO.

    `tool_class` e `None` APENAS quando a tool nao esta no catalogo e por isso
    nao tem classe: ausencia declarada, nunca classe default. `profile` guarda
    o `ExecutionProfile` canonico quando o perfil foi reconhecido, e o valor
    cru recebido quando nao foi -- quem audita precisa ver o que chegou, nao o
    que gostariamos que tivesse chegado.
    """

    agent: str
    tool: str
    tool_class: ToolClass | None
    profile: object
    authorized: bool
    reason: str
    required_approval: ToolClass | None = None
    granted_by: ToolClass | None = None


def authorize(
    *,
    agent: str,
    tool: str,
    allowed_tools: Iterable[str],
    profile: object,
    approvals: Iterable[ToolClass] = (),
    denied_tools: Iterable[str] = (),
) -> AuthorizationDecision:
    """Autoriza uma chamada de tool, com a cadeia registrada na decisao.

    `approvals` e por CLASSE, e nao um booleano. O `approval=True` de
    `authorize_tool` aprovava mutacao local e escrita na nuvem de uma vez, e era
    essa a lacuna que a secao 76 nomeia: sem escopo, a aprovacao dada para uma
    coisa vale para outra.

    `denied_tools` existe porque `AgentManifest` declara a denylist ao lado da
    allowlist e as duas sao validadas por schema; uma denylist que a cadeia
    ignorasse em silencio seria pior que denylist nenhuma, porque quem a
    escreve acredita que ela morde. Deny vence allow: uma tool nos dois campos
    e recusada, que e a unica precedencia em que um engano na allowlist nao
    abre o que a denylist fechou de proposito.

    Ordem das checagens, e o porque dela: denylist e allowlist primeiro
    (nenhuma das duas precisa saber a classe, e sao o caso mais frequente),
    depois a classe, depois o perfil, depois o teto, depois a aprovacao. A
    classe vinha antes da allowlist e isso fazia `authorize()` ESTOURAR em vez
    de decidir no caso mais provavel de todos -- agente alucina nome de tool,
    ou um rename perde um call site --, justo na fronteira cujo argumento e
    "a decisao carrega a cadeia". Agora esse caso produz recusa auditavel.

    Perfil nao reconhecido tambem RECUSA, pela mesma disciplina de
    `tool_class()`: sem perfil nao ha teto, e "sem teto" nao pode ser o
    default de quem escreveu o nome errado.

    LIMITE, declarado porque tem consequencia: isto autoriza um NOME, nunca
    uma CHAMADA. A assinatura nao recebe os argumentos da tool, entao `path`,
    `bucket` e `report_path` estao fora da decisao por construcao -- ler
    `~/.aws/credentials` e READ_ONLY e passa sob qualquer perfil. Fechar isso
    e o hook `PreToolUse` da secao 41, que ve argumentos; esta funcao nao tem
    onde recebe-los. Ver `docs/harness/AUTHORIZATION-CHAIN.md`.
    """
    aprovadas = frozenset(approvals)

    def recusa(motivo: str, classe: ToolClass | None, perfil: object) -> AuthorizationDecision:
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=perfil,
            authorized=False,
            reason=motivo,
        )

    if tool in set(denied_tools):
        return recusa("tool na denylist do agente", None, profile)

    if tool not in set(allowed_tools):
        return recusa("tool fora da allowlist do agente", None, profile)

    try:
        classe = tool_class(tool)
    except KeyError:
        return recusa(
            "tool fora do catalogo, e sem classe nao ha o que autorizar", None, profile
        )

    perfil = _perfil_canonico(profile)
    if perfil is None:
        return recusa(
            f"perfil nao reconhecido ({profile!r}): sem perfil nao ha teto", classe, profile
        )

    if _teto_recusa_rede(perfil) and classe in _CLASSES_DE_REDE:
        return recusa(
            "perfil OFFLINE recusa tool de rede, com aprovacao ou sem: o "
            "perfil e teto, nao preferencia",
            classe,
            perfil,
        )

    if classe in _EXIGEM_APROVACAO and classe not in aprovadas:
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=perfil,
            authorized=False,
            reason=f"classe {classe.value} exige aprovacao explicita para esta classe",
            required_approval=classe,
        )

    return AuthorizationDecision(
        agent=agent,
        tool=tool,
        tool_class=classe,
        profile=perfil,
        authorized=True,
        reason="autorizado",
        granted_by=classe if classe in _EXIGEM_APROVACAO else None,
    )
