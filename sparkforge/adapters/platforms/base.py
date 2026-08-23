"""Base interface for Platform Exporters in SparkForge."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from sparkforge.registry.loader import CanonicalRegistry

GENERATED_HEADER = """<!--
  GENERATED FROM CANONICAL SOURCE — DO NOT EDIT DIRECTLY.
  SPARKFORGE AWS AGENT FACTORY vNext
-->
"""


class BasePlatformExporter(ABC):
    """Abstract platform exporter class."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Target platform name (e.g. 'antigravity', 'cursor', 'claude')."""

    @abstractmethod
    def export(self, registry: CanonicalRegistry, output_dir: Path) -> list[Path]:
        """Exports canonical registry entities to target platform artifacts.

        Returns list of generated file paths.
        """
