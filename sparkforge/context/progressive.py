"""Progressive Knowledge Disclosure Manager.

Enforces 3-tier progressive disclosure:
- Level A: Metadata (~20-50 tokens for routing)
- Level B: Skill Instructions (procedural markdown loaded on activation)
- Level C: In-depth References (deep technical docs loaded on explicit demand)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeLevelA:
    """Metadata only: for fast, low-token routing decisions."""
    id: str
    name: str
    description: str
    triggers: list[str]
    estimated_tokens: int = 35


@dataclass(frozen=True)
class KnowledgeLevelB:
    """Skill / Procedure instructions: loaded only when skill is chosen."""
    metadata: KnowledgeLevelA
    procedure_content: str
    required_tools: list[str]


@dataclass(frozen=True)
class KnowledgeLevelC:
    """In-depth reference documents: loaded on demand."""
    level_b: KnowledgeLevelB
    references: dict[str, str]  # title -> full content


class ProgressiveDisclosureManager:
    """Manages lazy-loading of knowledge layers."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    def get_level_a(self, skill_id: str, description: str, triggers: list[str]) -> KnowledgeLevelA:
        return KnowledgeLevelA(
            id=skill_id,
            name=skill_id,
            description=description[:150],
            triggers=triggers,
        )

    def load_level_b(self, level_a: KnowledgeLevelA, skill_dir: Path) -> KnowledgeLevelB:
        skill_file = skill_dir / "SKILL.md"
        content = ""
        if skill_file.is_file():
            content = skill_file.read_text(encoding="utf-8", errors="ignore")
        return KnowledgeLevelB(
            metadata=level_a,
            procedure_content=content,
            required_tools=[],
        )

    def load_level_c(self, level_b: KnowledgeLevelB, references_dir: Path) -> KnowledgeLevelC:
        refs = {}
        if references_dir.is_dir():
            for ref_file in references_dir.glob("*.md"):
                refs[ref_file.stem] = ref_file.read_text(encoding="utf-8", errors="ignore")
        return KnowledgeLevelC(
            level_b=level_b,
            references=refs,
        )
