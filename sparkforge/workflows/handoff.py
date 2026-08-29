"""Structured Handoff Contracts for SparkForge Workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StructuredHandoff:
    """Structured handoff between agents or workflow stages to avoid transcript dumping."""
    sender_role: str
    recipient_role: str
    finding_summary: str
    evidence_fact_ids: list[str] = field(default_factory=list)
    confidence: str = "high"  # high, medium, low, unresolved
    changed_files: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    recommendation: str = ""
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_compact_markdown(self) -> str:
        lines = [
            f"### Handoff: `{self.sender_role}` ➔ `{self.recipient_role}`",
            f"- **Confidence**: {self.confidence.upper()}",
            f"- **Summary**: {self.finding_summary}",
        ]
        if self.evidence_fact_ids:
            lines.append(f"- **Evidence**: {', '.join(self.evidence_fact_ids)}")
        if self.changed_files:
            lines.append(f"- **Changed Files**: {', '.join(self.changed_files)}")
        if self.unresolved_questions:
            lines.append(f"- **Unresolved**: {'; '.join(self.unresolved_questions)}")
        if self.recommendation:
            lines.append(f"- **Recommendation**: {self.recommendation}")
        if self.next_action:
            lines.append(f"- **Next Action**: {self.next_action}")
        return "\n".join(lines)
