"""Bounded autonomy and policy-driven routing for SparkForge agents."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sparkforge.paths import resolve_within

if TYPE_CHECKING:
    # So para a anotacao: em tempo de execucao o import continua LOCAL, dentro
    # das funcoes que precisam dele, para `import sparkforge.agents` nao passar
    # a arrastar o pacote `registry` inteiro por causa de um enum.
    from sparkforge.registry.models import AgentManifest, ExecutionProfile


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

    DUAS classes ficam sem membro no catalogo de hoje, por razoes diferentes,
    e nenhuma das duas e lacuna:

    - `DESTRUCTIVE`, porque nenhuma tool declara `destructiveHint`.
    - `CLOUD_READ`, porque nao existe uma unica tool que toque a rede sem
      TAMBEM escrever em disco -- os sete coletores AWS gravam o artefato e o
      manifesto de integridade, entao caem em `CLOUD_MUTATION`.

    A segunda so ficou vazia quando a anotacao dos coletores parou de mentir
    (eles declaravam `readOnlyHint: True` e escrevem). Derivar a classe da
    anotacao foi o que expos isso -- e e esse o valor da derivacao, nao a
    classificacao em si. O valor de classificar agora nao e bloquear o que
    existe, e impedir que uma tool futura entre sem classe.

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


# Nomes de parametro que SAO caminho de sistema de arquivos, medidos sobre o
# `inputSchema` das 44 tools e nao imaginados: 43 delas declaram pelo menos um,
# e as sete grafias usadas hoje sao `path`, `repo`, `file`, `before`, `after`,
# `*_path` e `*_paths`. `_dir`, `_files` e `_root` entram por antecipacao de
# grafia, nao por medicao -- nenhuma tool de hoje usa.
#
# Isto E uma lista mantida a mao, e vale dizer por que aqui a derivacao nao
# serviu, ao contrario de `tool_class()`. La existe declaracao estruturada
# (`readOnlyHint` e as outras duas) da qual derivar; aqui nao existe campo
# nenhum no schema dizendo "isto e caminho" -- so o nome e a prosa da
# descricao. Derivar de prosa e heuristica, e heuristica que erra para o lado
# de "nao e caminho" falha ABERTO, que e o modo de falha que esta fase existe
# para fechar. A lista fica, e `TestOCatalogoContinuaCabendoNaVerificacao` e o
# gate que impede ela de envelhecer calada: se uma tool entrar com caminho
# batizado de outro jeito, a contagem de 43 muda e o teste cai.
_NOMES_DE_CAMINHO = frozenset({"path", "repo", "file", "before", "after"})
_SUFIXOS_DE_CAMINHO = ("_path", "_paths", "_file", "_files", "_dir", "_root")


def _e_chave_de_caminho(nome: str) -> bool:
    """`True` quando o nome do parametro nomeia um caminho de filesystem."""
    return nome in _NOMES_DE_CAMINHO or nome.endswith(_SUFIXOS_DE_CAMINHO)


def _caminhos_declarados(arguments: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Os pares (parametro, valor) que a decisao precisa confinar.

    Lista e percorrida item a item porque `facts_paths` de `sparkforge_fuse` e
    `sparkforge_funcval_plan` E uma lista -- verificar so `isinstance(valor,
    str)` deixaria o argumento principal daquelas duas passar sem checagem
    nenhuma.

    Valor que nao e texto (numero, booleano, `None`, mapa aninhado) e ignorado
    de proposito: nao ha caminho que este catalogo declare nessas formas, e
    inventar travessia de estrutura arbitraria seria superficie sem caso.
    """
    for chave, valor in arguments.items():
        if not _e_chave_de_caminho(chave):
            continue
        if isinstance(valor, str):
            yield chave, valor
        elif isinstance(valor, (list, tuple)):
            for item in valor:
                if isinstance(item, str):
                    yield chave, item


def _argumento_fora_da_raiz(arguments: dict[str, Any], root: Path | str) -> str | None:
    """O motivo da recusa, ou `None` quando todo caminho declarado cabe na raiz.

    `~` e recusado ANTES do confinamento, e nao por descuido: `resolve_within`
    nao expande `~` no alvo, entao `raiz / "~/.aws/credentials"` cai dentro da
    raiz e passaria. Nenhum adapter deste repositorio expande `~` num argumento
    de tool hoje (busca por `expanduser` em `sparkforge/`: tres ocorrencias, as
    tres sobre raiz de configuracao, nenhuma sobre argumento), entao a leitura
    falharia de todo jeito -- mas a recusa nao depende de isso continuar
    verdade.
    """
    for chave, valor in _caminhos_declarados(arguments):
        if valor.startswith("~"):
            return (
                f"argumento `{chave}` fora da raiz do case: `~` nomeia o home "
                f"do usuario e o confinamento nao o expande"
            )
        if resolve_within(root, valor) is None:
            return f"argumento `{chave}` aponta para fora da raiz do case: {valor!r}"
    return None


def _perfil_canonico(profile: object) -> ExecutionProfile | None:
    """O `ExecutionProfile` que `profile` nomeia, ou `None` se nao nomeia
    nenhum.

    Existe porque comparar o perfil com o literal `"OFFLINE"` falhava ABERTO,
    e o modo da falha era silencioso: `ExecutionProfile` e `str, Enum` com
    valor MINUSCULO (`OFFLINE = "offline"`), entao o valor canonico do
    repositorio atravessava uma anotacao `profile: str` sem erro de tipo
    nenhum e comparava `False` -- o teto de rede sumia e a decisao saia
    gravada como `"autorizado"`, indistinguivel de permissao legitima.

    O ramo `isinstance(profile, ExecutionProfile)` NAO e necessario hoje, e a
    honestidade sobre isso importa mais que a aparencia de rigor. Como
    `ExecutionProfile` e mixin de `str`, um membro ja responde
    `.strip().lower()` com o proprio valor (`"offline"`), entao o ramo de
    texto sozinho classificaria certo -- e nenhum teste consegue distinguir a
    presenca do ramo da ausencia dele. Ele fica por uma razao de futuro, nao
    de presente: no dia em que `ExecutionProfile` deixar de herdar de `str`
    (migrar para `StrEnum`, ou virar `Enum` puro), o ramo de texto passa a
    receber um objeto sem `.strip()` e a funcao devolveria `None` para o
    valor MAIS canonico que existe -- recusando tudo, em vez de autorizar
    tudo. O ramo torna esse dia inerte.

    Cuidado que ele tambem evita: `str(ExecutionProfile.OFFLINE)` devolve
    `"ExecutionProfile.OFFLINE"`, e nao `"offline"`. Esta funcao nunca chama
    `str(profile)` justamente por isso -- se alguem "simplificar" a
    normalizacao para `str(profile).lower()`, o teto volta a falhar aberto.

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

    `checked_arguments` nao e decoracao. Ele e `True` exatamente quando o
    confinamento dos argumentos RODOU -- e nao quando ele aprovou, nem quando
    argumentos foram passados. Sem esse campo, uma decisao tomada sem
    `arguments` seria indistinguivel de uma que examinou os caminhos e
    aprovou, e a combinacao que mais importa a quem audita e justamente
    `authorized=True` com `checked_arguments=False`: autorizado sem que
    ninguem tenha olhado para onde a chamada aponta.

    Ele fica `False` tambem nas recusas que acontecem ANTES do argumento
    (denylist, allowlist, classe, perfil, teto, aprovacao) e na recusa por
    `arguments` sem `root`. Nesses casos `authorized` ja e `False`, entao nao
    ha ambiguidade: a decisao diz "recusei, e nao cheguei a olhar o
    argumento", que e a verdade.
    """

    agent: str
    tool: str
    tool_class: ToolClass | None
    profile: object
    authorized: bool
    reason: str
    required_approval: ToolClass | None = None
    granted_by: ToolClass | None = None
    checked_arguments: bool = False


def authorize(
    *,
    agent: str,
    tool: str,
    allowed_tools: Iterable[str],
    profile: object,
    approvals: Iterable[ToolClass] = (),
    denied_tools: Iterable[str] = (),
    arguments: dict[str, Any] | None = None,
    root: Path | str | None = None,
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

    `arguments` e `root` fecham metade do limite que esta funcao declarava:
    ela autorizava um NOME, nunca uma CHAMADA. Um revisor de seguranca leu um
    segredo de fora do repositorio com uma tool `READ_ONLY` sob perfil
    `OFFLINE`, com a cadeia funcionando exatamente como especificada, porque
    o `path` nao entrava na decisao. Medido no catalogo de hoje: 43 das 44
    tools declaram parametro de caminho, entao isso e a forma normal da
    chamada e nao um caso de borda. Com `arguments` e `root`, todo caminho
    declarado tem de cair dentro da raiz do case.

    A verificacao do argumento e a ULTIMA da ordem, depois da aprovacao, e a
    razao e o que a decisao passa a significar: as checagens anteriores
    respondem "esta tool, para este agente, sob este perfil"; a do argumento
    responde "esta chamada". Perguntar se o caminho e legitimo antes de saber
    se a tool sequer e legitima trocaria a razao da recusa pela menos
    fundamental das duas. O preco disso e que uma recusa anterior sai com
    `checked_arguments=False` mesmo tendo recebido argumentos -- e isso e
    verdade, nao perda: a verificacao nao rodou.

    `arguments` sem `root` RECUSA, pela terceira aplicacao da mesma
    disciplina: sem raiz nao ha confinamento, e "sem confinamento" nao pode
    ser o default de quem passou o argumento e esqueceu a raiz. O par
    completo tambem nao promove nada -- caminho perfeito nao fura classe,
    teto nem aprovacao, porque a verificacao so RECUSA, nunca concede.

    LIMITE que CONTINUA de pe, e e o maior dos dois: ver o argumento nao
    IMPOE nada. Nenhum dos quatro caminhos de execucao (`adapters/mcp.py`,
    `adapters/tools.py`, `adapters/cli.py`, `agents/supervisor.py`) chama
    `authorize()`, entao uma tool continua recebendo o caminho que quiserem
    passar para ela. Esse e o gap do hook `PreToolUse` da secao 41, e ele nao
    fecha aqui. Ver `docs/harness/AUTHORIZATION-CHAIN.md`.
    """
    aprovadas = frozenset(approvals)

    def recusa(
        motivo: str,
        classe: ToolClass | None,
        perfil: object,
        *,
        checou_argumentos: bool = False,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            agent=agent,
            tool=tool,
            tool_class=classe,
            profile=perfil,
            authorized=False,
            reason=motivo,
            checked_arguments=checou_argumentos,
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

    if arguments is not None:
        if root is None:
            return recusa(
                "argumentos recebidos sem raiz do case: sem raiz nao ha "
                "confinamento, e sem confinamento nao ha o que verificar",
                classe,
                perfil,
            )
        motivo = _argumento_fora_da_raiz(arguments, root)
        if motivo is not None:
            return recusa(motivo, classe, perfil, checou_argumentos=True)

    return AuthorizationDecision(
        agent=agent,
        tool=tool,
        tool_class=classe,
        profile=perfil,
        authorized=True,
        reason="autorizado",
        granted_by=classe if classe in _EXIGEM_APROVACAO else None,
        checked_arguments=arguments is not None and root is not None,
    )


@dataclass(frozen=True)
class CallPolicy:
    """A politica declarada que UMA fronteira de execucao impoe a cada chamada.

    Nao e fonte de politica nova, e a distincao importa: os campos sao
    exatamente os que `authorize()` ja exigia, e `from_manifest()` os tira de
    `AgentManifest`, que e onde a allowlist e a denylist ja vivem declaradas e
    validadas por schema. Uma segunda lista mantida ao lado daquela seria a
    familia de defeito que a derivacao de `ToolClass` existe para nao repetir.

    O que ela acrescenta e poder ATRAVESSAR uma fronteira. `call_tool` recebe
    um objeto e nao seis argumentos soltos, entao a politica e montada uma vez
    por sessao, no lugar que sabe qual agente esta rodando, em vez de remontada
    a cada despacho por quem so sabe o nome da tool.

    Ela e OPCIONAL em `call_tool` de proposito, e e isso que preserva a
    semantica: sem politica declarada nao ha o que impor, e inventar um default
    faria o catalogo inteiro passar a recusar hoje o que ele autoriza. Uma
    imposicao que quebra tudo nao e imposicao, e regressao.

    O nome nao e `ToolPolicy` porque esse ja esta ocupado: e o rotulo com que
    `docs/harness/CURRENT-HARNESS-GAP.md` chama a classificacao da secao 40, que
    e outra coisa -- aquilo classifica a TOOL, isto autoriza a CHAMADA. Duas
    coisas com o mesmo nome numa fronteira de seguranca e como um revisor le a
    linha errada e conclui que a checagem existe.
    """

    agent: str
    allowed_tools: tuple[str, ...]
    profile: object
    root: Path | str
    approvals: tuple[ToolClass, ...] = ()
    denied_tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Congela as listas em tuplas.

        Nao e purismo de imutabilidade: uma politica vive MAIS que uma chamada
        -- um agente a carrega pela sessao inteira --, e `authorize()` consome
        `allowed_tools` com `set()` a cada chamada. Guardar o iteravel cru
        deixaria um gerador autorizar a primeira chamada e recusar todas as
        seguintes, que e a forma de defeito de autorizacao mais dificil de
        enxergar: intermitente, e do lado que fecha.

        `object.__setattr__` porque o dataclass e frozen -- e o frozen fica
        para que ninguem edite a allowlist de uma politica ja em uso.
        """
        object.__setattr__(self, "allowed_tools", tuple(self.allowed_tools))
        object.__setattr__(self, "denied_tools", tuple(self.denied_tools))
        object.__setattr__(self, "approvals", tuple(self.approvals))

    @classmethod
    def from_manifest(
        cls,
        manifest: AgentManifest,
        *,
        profile: object,
        root: Path | str,
        approvals: Iterable[ToolClass] = (),
    ) -> CallPolicy:
        """A politica de um agente, tirada do manifesto dele.

        `profile`, `root` e `approvals` NAO saem do manifesto porque nao estao
        la: o manifesto declara o que o agente pode usar, e nao sob que perfil,
        em que case nem com que aprovacao do operador. Inventar um default para
        os tres aqui seria decidir em nome de quem opera, no lugar mais escondido
        possivel.
        """
        return cls(
            agent=manifest.id,
            allowed_tools=tuple(manifest.allowed_tools),
            profile=profile,
            root=root,
            approvals=tuple(approvals),
            denied_tools=tuple(manifest.denied_tools),
        )

    def decide(self, tool: str, arguments: dict[str, Any]) -> AuthorizationDecision:
        """A decisao da cadeia para esta chamada.

        Existe para que a fronteira nao precise saber a ordem dos oito
        parametros de `authorize()`: um segundo ponto de imposicao que montasse
        a chamada do proprio jeito poderia esquecer `denied_tools` e a denylist
        sumiria em silencio naquela fronteira so.
        """
        return authorize(
            agent=self.agent,
            tool=tool,
            allowed_tools=self.allowed_tools,
            profile=self.profile,
            approvals=self.approvals,
            denied_tools=self.denied_tools,
            arguments=arguments,
            root=self.root,
        )
