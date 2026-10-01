"""Devin, Windsurf, Copilot and Generic Platform Exporters."""

from __future__ import annotations

from pathlib import Path

from sparkforge.adapters.platforms.base import GENERATED_HEADER, BasePlatformExporter
from sparkforge.registry.loader import CanonicalRegistry


class DevinExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "devin"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        devin_file = output_dir / "knowledge" / "devin" / "INSTRUCTIONS.md"
        devin_file.parent.mkdir(parents=True, exist_ok=True)
        content = (
            f"{GENERATED_HEADER}\n# Devin Instructions for SparkForge AWS\n\n"
            f"Operate deterministically "
            f"first.\n"
        )
        devin_file.write_text(content, encoding="utf-8")
        generated.append(devin_file)
        return generated


class WindsurfExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "windsurf"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        rules_file = output_dir / ".windsurfrules"
        content = (
            f"{GENERATED_HEADER}\n# Windsurf Rules — SparkForge AWS\n\n- Deterministic first\n"
            f"- Use PySpark native functions\n- Follow Token Economy tiers\n"
        )
        rules_file.write_text(content, encoding="utf-8")
        generated.append(rules_file)
        return generated


class CopilotExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "copilot"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        gh_dir = output_dir / ".github"
        gh_dir.mkdir(parents=True, exist_ok=True)
        copilot_file = gh_dir / "copilot-instructions.md"
        content = (
            f"{GENERATED_HEADER}\n# GitHub Copilot Instructions — SparkForge AWS\n\nApply strict "
            f"PySpark, AWS Glue, EMR, and Iceberg performance principles.\n"
        )
        copilot_file.write_text(content, encoding="utf-8")
        generated.append(copilot_file)
        return generated


class GenericExporter(BasePlatformExporter):
    @property
    def platform_name(self) -> str:
        return "generic"

    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        generated: list[Path] = []
        # We preserve existing root AGENTS.md or export generic summary
        summary_file = output_dir / "docs" / "vnext" / "GENERIC-AGENTS-SPEC.md"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        content = f"{GENERATED_HEADER}\n# Generic Open Agent Specification\n\n"
        for agent in registry.agents.values():
            content += (
                f"## {agent.name}\n- Role: {agent.role}\n- Description: {agent.description}\n\n"
            )
        summary_file.write_text(content, encoding="utf-8")
        generated.append(summary_file)
        return generated
