"""Main Platform Compiler and Synchronization Engine."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sparkforge.adapters.platforms.antigravity import AntigravityExporter
from sparkforge.adapters.platforms.base import BasePlatformExporter
from sparkforge.adapters.platforms.claude import ClaudeExporter
from sparkforge.adapters.platforms.cursor import CursorExporter
from sparkforge.adapters.platforms.targets import (
    CopilotExporter,
    DevinExporter,
    GenericExporter,
    WindsurfExporter,
)
from sparkforge.registry.loader import CanonicalRegistry, get_default_registry


class PlatformCompiler:
    """Orchestrates multi-platform export from the Canonical Registry."""

    def __init__(self, registry: Optional[CanonicalRegistry] = None, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.registry = registry or get_default_registry(root_dir=self.root_dir)
        self.exporters: dict[str, BasePlatformExporter] = {
            "antigravity": AntigravityExporter(),
            "cursor": CursorExporter(),
            "claude": ClaudeExporter(),
            "devin": DevinExporter(),
            "windsurf": WindsurfExporter(),
            "copilot": CopilotExporter(),
            "generic": GenericExporter(),
        }

    def export_target(self, target_name: str, output_dir: Optional[Path] = None) -> list[Path]:
        out = output_dir or self.root_dir
        exporter = self.exporters.get(target_name.lower())
        if not exporter:
            valid = ", ".join(self.exporters.keys())
            raise ValueError(f"Unknown platform target '{target_name}'. Available: {valid}")
        return exporter.export(self.registry, out)

    def export_all(self, output_dir: Optional[Path] = None) -> dict[str, list[Path]]:
        results = {}
        for name in self.exporters:
            results[name] = self.export_target(name, output_dir)
        return results
