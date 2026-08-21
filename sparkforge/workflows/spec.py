"""Task Spec Engine for SparkForge Workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from sparkforge.registry.models import RiskLevel, TokenBudget


@dataclass
class TaskSpec:
    objective: str
    context: str = ""
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    requires_approval: bool = False
    budget: TokenBudget = field(default_factory=TokenBudget)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["budget"] = self.budget.to_dict()
        return d

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), sort_keys=False, default_flow_style=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskSpec:
        risk_str = data.get("risk_level", "read_only")
        risk = RiskLevel(risk_str) if isinstance(risk_str, str) else RiskLevel.READ_ONLY
        budget_data = data.get("budget", {})
        budget = TokenBudget(**budget_data) if isinstance(budget_data, dict) else TokenBudget()

        return cls(
            objective=data.get("objective", ""),
            context=data.get("context", ""),
            constraints=data.get("constraints", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            affected_files=data.get("affected_files", []),
            interfaces=data.get("interfaces", []),
            validation_commands=data.get("validation_commands", []),
            dependencies=data.get("dependencies", []),
            risk_level=risk,
            requires_approval=data.get("requires_approval", False),
            budget=budget,
        )
