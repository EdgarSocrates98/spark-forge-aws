"""Hosts no escopo `project`/`workspace`: os diretorios que cada host le DENTRO
do repositorio (espelho de `integrate/hosts.py`, que cobre o HOME).

MCP no projeto: o arquivo unico `.mcp.json` na raiz, lido por Claude Code,
Devin e Codex -- o `mcp_config` de todo host aponta para ele e
`apply_json_config` mescla `mcpServers.sparkforge-aws` sem tocar nos demais.
"""
from __future__ import annotations

from pathlib import Path

from sparkforge_aws.integrate.hosts import FONTES, Host

HOSTS = ("claude", "devin", "codex", "copilot")


def project_host(name: str, root: Path) -> Host:
    """O `Host` de `name` com os diretorios relativos a `root` (o projeto)."""
    if name not in HOSTS:
        raise ValueError(f"host desconhecido: {name!r}; conhecidos: {list(HOSTS)}")
    root = Path(root)
    mcp = root / ".mcp.json"
    if name == "claude":
        return Host(
            name="claude",
            agents_dir=root / ".claude" / "agents",
            agent_pattern="{stem}.md",
            agent_platform="claude",
            executors=True,
            skills_dir=root / ".claude" / "skills",
            skill_platform="claude",
            mcp_config=mcp,
            mcp_format="json",
            fonte=FONTES["claude"],
        )
    if name == "devin":
        # Devin le `.devin/` e `.agents/` nativamente no repositorio.
        return Host(
            name="devin",
            agents_dir=root / ".devin" / "agents",
            agent_pattern="{stem}.md",
            agent_platform="devin",
            executors=True,
            skills_dir=root / ".devin" / "skills",
            skill_platform="devin",
            mcp_config=mcp,
            mcp_format="json",
            fonte=FONTES["devin"],
        )
    if name == "codex":
        # `.agents/skills` e a superficie de skills do Codex; os agents dele
        # sao TOML em `.codex/agents` (executores fora: sem `description`).
        return Host(
            name="codex",
            agents_dir=root / ".codex" / "agents",
            agent_pattern="{stem}.toml",
            agent_platform="codex",
            executors=False,
            skills_dir=root / ".agents" / "skills",
            skill_platform="devin",
            mcp_config=mcp,
            mcp_format="json",
            fonte=FONTES["codex"],
        )
    return Host(
        name="copilot",
        agents_dir=root / ".github" / "agents",
        agent_pattern="{stem}.agent.md",
        agent_platform="github",
        executors=True,
        skills_dir=root / ".github" / "skills",
        skill_platform="devin",
        mcp_config=mcp,
        mcp_format="json",
        fonte=FONTES["copilot"],
    )


# `.agents/` e a superficie compartilhada que Devin le nativamente (e Codex,
# nas skills): o espelho `devin` do repositorio, o mesmo que `.agents/` leva.
SHARED_AGENT_HOSTS = {
    "devin": (".agents/agents", ".agents/skills"),
}


def project_plan(
    h: Host, content_root: Path, target_root: Path
) -> list[tuple[Path, bytes]]:
    """`plan_files` do host + a copia `.agents/` compartilhada, quando houver."""
    from sparkforge_aws.integrate import writer

    plano = writer.plan_files(h, content_root)
    extra = SHARED_AGENT_HOSTS.get(h.name)
    if extra:
        agents_dir, skills_dir = extra
        shared = Host(
            name=h.name,
            agents_dir=Path(target_root) / agents_dir,
            agent_pattern=h.agent_pattern,
            agent_platform=h.agent_platform,
            executors=h.executors,
            skills_dir=Path(target_root) / skills_dir,
            skill_platform=h.skill_platform,
            mcp_config=None,
            mcp_format=None,
            fonte=h.fonte,
        )
        plano += writer.plan_files(shared, content_root)
    return plano


__all__ = ["HOSTS", "SHARED_AGENT_HOSTS", "project_host", "project_plan"]
