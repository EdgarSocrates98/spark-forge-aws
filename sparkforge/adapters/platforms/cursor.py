"""Cursor IDE Platform Exporter."""
from __future__ import annotations

from pathlib import Path

from sparkforge.adapters.platforms.base import GENERATED_HEADER, BasePlatformExporter
from sparkforge.registry.loader import CanonicalRegistry


class CursorExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "cursor"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        rules_dir = output_dir / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Export MDC Rules
        for skill_id, skill in registry.skills.items():
            rule_file = rules_dir / f"{skill_id}.mdc"
            content = f"""---
description: {skill.description}
globs: "*.py,*.sql,*.tf"
alwaysApply: false
---
{GENERATED_HEADER}
# {skill.name}

## When to Apply
"""
            for tr in skill.triggers:
                content += f"- {tr}\n"
            content += f"\n## Guidance\n{skill.description}\n"
            rule_file.write_text(content, encoding="utf-8")
            generated.append(rule_file)

        return generated
