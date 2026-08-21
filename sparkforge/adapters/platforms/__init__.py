"""SparkForge Multi-Platform Adapters and Compilers."""
from __future__ import annotations

from sparkforge.adapters.platforms.antigravity import AntigravityExporter
from sparkforge.adapters.platforms.base import GENERATED_HEADER, BasePlatformExporter
from sparkforge.adapters.platforms.claude import ClaudeExporter
from sparkforge.adapters.platforms.compiler import PlatformCompiler
from sparkforge.adapters.platforms.cursor import CursorExporter
from sparkforge.adapters.platforms.targets import (
    CopilotExporter,
    DevinExporter,
    GenericExporter,
    WindsurfExporter,
)

__all__ = [
    "GENERATED_HEADER",
    "BasePlatformExporter",
    "PlatformCompiler",
    "AntigravityExporter",
    "CursorExporter",
    "ClaudeExporter",
    "DevinExporter",
    "WindsurfExporter",
    "CopilotExporter",
    "GenericExporter",
]
