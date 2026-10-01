"""Antigravity 2.0 Platform Exporter."""

from __future__ import annotations

from pathlib import Path

from sparkforge.adapters.platforms.base import GENERATED_HEADER, BasePlatformExporter
from sparkforge.registry.loader import CanonicalRegistry


class AntigravityExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "antigravity"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        agents_dir = output_dir / ".agents" / "agents"
        skills_dir = output_dir / ".agents" / "skills"
        rules_dir = output_dir / ".agents" / "rules"

        agents_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Export Agents
        for agent_id, agent in registry.agents.items():
            agent_file = agents_dir / f"{agent_id}.md"
            content = (
                f"{GENERATED_HEADER}\n# {agent.name}\n\n**Role**: {agent.role}\n"
                f"**Purpose**: {agent.purpose}\n"
                f"\n## Description\n{agent.description}\n\n## Allowed Tools\n"
            )
            for tool in agent.allowed_tools:
                content += f"- `{tool}`\n"
            agent_file.write_text(content, encoding="utf-8")
            generated.append(agent_file)

        # Export Skills
        for skill_id, skill in registry.skills.items():
            s_dir = skills_dir / skill_id
            s_dir.mkdir(parents=True, exist_ok=True)
            skill_file = s_dir / "SKILL.md"
            content = (
                f"{GENERATED_HEADER}\n---\nname: {skill.name}\ndescription: {skill.description}\n"
                f"---\n\n# {skill.name}\n\n## Triggers\n"
            )
            for tr in skill.triggers:
                content += f"- {tr}\n"
            content += f"\n## Procedure\nRefer to canonical skill definition for {skill.name}.\n"
            skill_file.write_text(content, encoding="utf-8")
            generated.append(skill_file)

        return generated
