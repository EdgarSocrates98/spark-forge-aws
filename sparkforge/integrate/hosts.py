"""Onde cada host le agents, skills e MCP de USUARIO (D4).

Tabela declarativa, com a fonte oficial de cada caminho (lida em 2026-09-25, T1).
Nenhum caminho sai de variavel de ambiente espalhada: `home`, `windows` e `appdata`
entram por parametro, e o teste aponta os tres para `tmp_path`.

`~/.agents/skills` e lido por Devin, Codex e Copilot CLI; os tres gravam a mesma
renderizacao, a da plataforma `devin` -- a mesma que o espelho `.agents/skills` do
repositorio recebe. Os campos `subagent:`/`agent:` que ela acrescenta sao do Devin,
e os outros dois hosts nao os leem.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

HOSTS = ("claude", "devin", "codex", "copilot")

MARKETPLACE = "sparkforge-local"
PLUGIN = "sparkforge-aws"

FONTES = {
    "claude": "https://code.claude.com/docs/en/plugins",
    "devin": "https://docs.devin.ai/cli/subagents",
    "codex": "https://learn.chatgpt.com/docs/agent-configuration/subagents",
    "copilot": "https://docs.github.com/en/copilot/how-tos/copilot-cli",
}


@dataclass(frozen=True)
class Host:
    name: str
    agents_dir: Path
    agent_pattern: str
    agent_platform: str
    executors: bool
    skills_dir: Path
    skill_platform: str
    mcp_config: Path | None
    mcp_format: str | None
    fonte: str


def claude_marketplace_dir(home: Path) -> Path:
    return Path(home) / ".sparkforge" / "claude"


def claude_plugin_dir(home: Path) -> Path:
    return claude_marketplace_dir(home) / "plugins" / PLUGIN


def devin_config_dir(home: Path, *, windows: bool, appdata: Path | None) -> Path:
    """`~/.config/devin`, ou `%APPDATA%\\devin` no Windows."""
    if not windows:
        return Path(home) / ".config" / "devin"
    base = Path(appdata) if appdata else Path(home) / "AppData" / "Roaming"
    return base / "devin"


def host(
    nome: str,
    *,
    home: Path,
    windows: bool | None = None,
    appdata: Path | None = None,
) -> Host:
    """O `Host` de `nome` sob `home`. `windows=None` e `os.name == "nt"`, e
    `appdata=None` le `APPDATA` -- so o CLI deixa os dois no default."""
    if nome not in HOSTS:
        raise ValueError(f"host desconhecido: {nome!r}; conhecidos: {list(HOSTS)}")
    home = Path(home)
    if windows is None:
        windows = os.name == "nt"
    if appdata is None and os.environ.get("APPDATA"):
        appdata = Path(os.environ["APPDATA"])
    compartilhadas = home / ".agents" / "skills"
    if nome == "claude":
        plugin = claude_plugin_dir(home)
        return Host(
            name="claude",
            agents_dir=plugin / "agents",
            agent_pattern="{stem}.md",
            agent_platform="claude",
            executors=True,
            skills_dir=plugin / "skills",
            skill_platform="claude",
            mcp_config=None,
            mcp_format=None,
            fonte=FONTES["claude"],
        )
    if nome == "devin":
        config = devin_config_dir(home, windows=windows, appdata=appdata)
        return Host(
            name="devin",
            agents_dir=config / "agents",
            agent_pattern="{stem}.md",
            agent_platform="devin",
            executors=True,
            skills_dir=compartilhadas,
            skill_platform="devin",
            mcp_config=config / "mcp_config.json",
            mcp_format="json",
            fonte=FONTES["devin"],
        )
    if nome == "codex":
        # Executores ficam de fora: nao tem `description`, e o TOML do Codex exige.
        return Host(
            name="codex",
            agents_dir=home / ".codex" / "agents",
            agent_pattern="{stem}.toml",
            agent_platform="codex",
            executors=False,
            skills_dir=compartilhadas,
            skill_platform="devin",
            mcp_config=home / ".codex" / "config.toml",
            mcp_format="toml",
            fonte=FONTES["codex"],
        )
    return Host(
        name="copilot",
        agents_dir=home / ".copilot" / "agents",
        agent_pattern="{stem}.agent.md",
        agent_platform="github",
        executors=True,
        skills_dir=compartilhadas,
        skill_platform="devin",
        mcp_config=home / ".copilot" / "mcp-config.json",
        mcp_format="json",
        fonte=FONTES["copilot"],
    )


def mcp_command(python: str | None = None) -> tuple[str, list[str]]:
    """O servidor MCP pelo Python que TEM o sparkforge instalado, sem PYTHONPATH."""
    return (python or sys.executable, ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"])


def mcp_entry(nome: str, python: str | None = None) -> dict:
    """A entrada `mcpServers.sparkforge` de um host de config JSON."""
    comando, args = mcp_command(python)
    entrada: dict = {"command": comando, "args": args}
    if nome == "copilot":
        entrada = {"type": "local", **entrada, "tools": ["*"]}
    return entrada


__all__ = [
    "FONTES",
    "HOSTS",
    "MARKETPLACE",
    "PLUGIN",
    "Host",
    "claude_marketplace_dir",
    "claude_plugin_dir",
    "devin_config_dir",
    "host",
    "mcp_command",
    "mcp_entry",
]
