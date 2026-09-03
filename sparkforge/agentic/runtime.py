"""Runtime abstraction — protocolo runtime-independente.

O SparkForge é runtime-independente: Claude Code, Devin CLI, Devin Desktop,
Copilot CI e Codex executam o mesmo protocolo. Este módulo define a
abstração que cada runtime adapta.

Princípio: o protocolo é o contrato, o runtime é a implementação.
Um runtime que não suporta `spawn_agent` usa `playbook` como floor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class RuntimeName(str, Enum):
    CLAUDE_CODE = "claude_code"
    DEVIN_CLI = "devin_cli"
    DEVIN_DESKTOP = "devin_desktop"
    COPILOT_CI = "copilot_ci"
    CODEX = "codex"
    GENERIC = "generic"


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Capacidades declaradas por um runtime.

    Usado em capability negotiation: o orquestrador pergunta o que o runtime
    suporta antes de escolher o padrão de execução (subagent vs playbook,
    paralelo vs sequencial, etc.).
    """

    spawn_agent: bool = False
    parallel_agents: bool = False
    nested_agents: bool = False  # subagent dentro de subagent
    structured_output: bool = False
    tool_calling: bool = False
    streaming: bool = False
    checkpointing: bool = False
    max_concurrent_agents: int = 1
    max_nesting_depth: int = 0


# Capacidades medidas por runtime (parity.yaml é a fonte canônica).
# Atualizado quando parity.yaml muda — não copiar para outros arquivos.
_MEASURED_CAPABILITIES: dict[RuntimeName, RuntimeCapabilities] = {
    RuntimeName.CLAUDE_CODE: RuntimeCapabilities(
        spawn_agent=True,
        parallel_agents=True,
        nested_agents=False,  # subagents cannot spawn subagents
        structured_output=True,
        tool_calling=True,
        streaming=True,
        checkpointing=False,
        max_concurrent_agents=10,
        max_nesting_depth=1,
    ),
    RuntimeName.DEVIN_CLI: RuntimeCapabilities(
        spawn_agent=True,
        parallel_agents=True,
        nested_agents=False,
        structured_output=True,
        tool_calling=True,
        streaming=True,
        checkpointing=True,
        max_concurrent_agents=10,
        max_nesting_depth=1,
    ),
    RuntimeName.DEVIN_DESKTOP: RuntimeCapabilities(
        spawn_agent=True,
        parallel_agents=True,
        nested_agents=False,
        structured_output=True,
        tool_calling=True,
        streaming=True,
        checkpointing=True,
        max_concurrent_agents=10,
        max_nesting_depth=1,
    ),
    RuntimeName.COPILOT_CI: RuntimeCapabilities(
        spawn_agent=False,
        parallel_agents=False,
        nested_agents=False,
        structured_output=False,
        tool_calling=False,
        streaming=False,
        checkpointing=False,
        max_concurrent_agents=1,
        max_nesting_depth=0,
    ),
    RuntimeName.CODEX: RuntimeCapabilities(
        spawn_agent=False,
        parallel_agents=False,
        nested_agents=False,
        structured_output=False,
        tool_calling=False,
        streaming=False,
        checkpointing=False,
        max_concurrent_agents=1,
        max_nesting_depth=0,
    ),
    RuntimeName.GENERIC: RuntimeCapabilities(
        spawn_agent=False,
        parallel_agents=False,
        nested_agents=False,
        structured_output=False,
        tool_calling=False,
        streaming=False,
        checkpointing=False,
        max_concurrent_agents=1,
        max_nesting_depth=0,
    ),
}


def get_capabilities(runtime: RuntimeName) -> RuntimeCapabilities:
    """Retorna capacidades medidas para um runtime.

    Não guess: se não medimos, retorna GENERIC (tudo False).
    """
    return _MEASURED_CAPABILITIES.get(runtime, _MEASURED_CAPABILITIES[RuntimeName.GENERIC])


@dataclass
class AgentSpawnRequest:
    """Pedido de spawn de um agente.

    `task` é a instrução em linguagem natural — o runtime decide se
    executa inline, como subagent, ou via playbook.
    """

    agent_id: str
    task: str
    context_refs: list[str] = field(default_factory=list)  # blackboard refs
    budget_tokens: int | None = None
    timeout_seconds: int | None = None


@dataclass
class AgentSpawnResult:
    """Resultado de um spawn de agente."""

    agent_id: str
    spawn_id: str  # runtime-specific id
    status: str  # "inline" | "subagent" | "playbook"
    output: str = ""
    error: str | None = None


class AgentRuntime(Protocol):
    """Protocolo que cada runtime implementa.

    Não é instanciado diretamente — cada runtime adapta para sua API.
    O orquestrador usa este protocolo para despachar agentes
    independentemente de qual runtime está executando.
    """

    @property
    def name(self) -> RuntimeName: ...

    @property
    def capabilities(self) -> RuntimeCapabilities: ...

    def spawn_agent(self, request: AgentSpawnRequest) -> AgentSpawnResult:
        """Spawna um agente. Retorna imediatamente se inline/playbook,
        ou um spawn_id para polling se subagent assíncrono."""
        ...

    def collect_result(self, spawn_id: str) -> AgentSpawnResult | None:
        """Coleta resultado de um spawn assíncrono. None se ainda running."""
        ...

    def tool_call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Executa uma tool MCP/CLI. Retorna o output estruturado."""
        ...


def can_spawn_parallel(runtime: RuntimeName, n_agents: int) -> bool:
    """Verifica se o runtime suporta N agentes em paralelo."""
    caps = get_capabilities(runtime)
    return caps.parallel_agents and caps.max_concurrent_agents >= n_agents


def can_debate(runtime: RuntimeName) -> bool:
    """Debate requer spawn de agentes independentes.

    Sem spawn, debate degenera para análise sequencial inline.
    """
    caps = get_capabilities(runtime)
    return caps.spawn_agent and caps.max_concurrent_agents >= 2


def execution_strategy(runtime: RuntimeName, n_agents: int) -> str:
    """Decide estratégia de execução baseada em capacidades.

    Retorna:
    - "parallel" — spawn paralelo de agentes
    - "sequential" — spawn sequencial (um por vez)
    - "inline" — executa inline, sem spawn
    - "playbook" — usa playbook como floor
    """
    caps = get_capabilities(runtime)
    if not caps.spawn_agent:
        return "playbook"
    if caps.parallel_agents and caps.max_concurrent_agents >= n_agents:
        return "parallel"
    if caps.spawn_agent:
        return "sequential"
    return "inline"
