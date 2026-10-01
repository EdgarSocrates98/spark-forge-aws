"""Claude Code Platform Exporter."""
from __future__ import annotations

from pathlib import Path

from sparkforge.adapters.platforms.base import GENERATED_HEADER, BasePlatformExporter
from sparkforge.registry.loader import CanonicalRegistry


class ClaudeExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "claude"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        claude_dir = output_dir / ".claude"
        agents_dir = claude_dir / "agents"
        skills_dir = claude_dir / "skills"

        agents_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Export Agents
        for agent_id, agent in registry.agents.items():
            agent_file = agents_dir / f"{agent_id}.md"
            content = f"{GENERATED_HEADER}\n# {agent.name}\n\n{agent.description}\n"
            agent_file.write_text(content, encoding="utf-8")
            generated.append(agent_file)

        return generated
