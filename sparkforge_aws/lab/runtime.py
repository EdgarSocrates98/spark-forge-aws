"""Guarded runtime plans shared by Compose and Testcontainers backends."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .contract import LabContractError
from .scenario import ScenarioAction, ScenarioSpec

COMPOSE_PROFILES = {
    "core": "lakehouse",
    "spark": "batch",
    "kafka": "streaming",
    "streaming": "streaming",
    "flink": "streaming",
    "lakehouse": "lakehouse",
    "cdc": "cdc",
    "polaris": "lakehouse",
    "observability": "observability",
    "chaos": "chaos",
    "full": "full",
}


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    scenario_id: str
    backend: str
    profile: str
    mode: str
    project_name: str
    actions: tuple[ScenarioAction, ...]
    command: tuple[str, ...]
    requires_confirmation: bool
    execute: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario_id,
            "backend": self.backend,
            "profile": self.profile,
            "mode": self.mode,
            "project_name": self.project_name,
            "actions": [action.to_dict() for action in self.actions],
            "command": list(self.command),
            "requires_confirmation": self.requires_confirmation,
            "execute": self.execute,
            "mutated": False,
        }


def build_runtime_plan(
    scenario: ScenarioSpec,
    *,
    backend: str = "compose",
    execute: bool = False,
    confirm: bool = False,
) -> RuntimePlan:
    if backend not in {"compose", "testcontainers"}:
        raise LabContractError(f"unsupported lab runtime backend: {backend}")
    if execute and not confirm:
        raise LabContractError("runtime execution requires --execute and --confirm")
    project_name = _project_name(scenario.slug)
    profile = COMPOSE_PROFILES[scenario.resource.profile]
    if backend == "compose":
        command = (
            "docker",
            "compose",
            "--project-name",
            project_name,
            "--profile",
            profile,
            "-f",
            "labs/forge-lab/compose.yaml",
            "up",
            "--detach",
        )
    else:
        command = (
            "python",
            "-m",
            "sparkforge_aws.lab.testcontainers_backend",
            "--scenario",
            scenario.scenario_id,
            "--profile",
            scenario.resource.profile,
        )
    return RuntimePlan(
        scenario_id=scenario.scenario_id,
        backend=backend,
        profile=profile,
        mode=scenario.resource.mode,
        project_name=project_name,
        actions=scenario.compile_actions(),
        command=command,
        requires_confirmation=True,
        execute=execute,
    )


def build_lifecycle_command(
    action: str, *, project_name: str, profile: str = "", service: str = ""
) -> tuple[str, ...]:
    if action not in {"up", "down", "status", "shell", "gc"}:
        raise LabContractError(f"unsupported lab lifecycle action: {action}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", project_name):
        raise LabContractError("invalid lab project name")
    base = [
        "docker",
        "compose",
        "--project-name",
        project_name,
        "-f",
        "labs/forge-lab/compose.yaml",
    ]
    if action == "up":
        if not profile:
            raise LabContractError("lab up requires a profile")
        return tuple(base + ["--profile", profile, "up", "--detach"])
    if action == "down":
        return tuple(base + ["down", "--remove-orphans"])
    if action == "status":
        return tuple(base + ["ps"])
    if action == "shell":
        if not service:
            raise LabContractError("lab shell requires a service")
        return tuple(base + ["exec", service, "sh"])
    return tuple(base + ["config", "--services"])


def guard_mutation(*, execute: bool, confirm: bool, target: str = "local") -> None:
    if target not in {"local", "aws"}:
        raise LabContractError(f"unsupported lab target: {target}")
    if execute and not confirm:
        raise LabContractError("mutating Lab action refused: --confirm is required")
    if target == "aws" and execute:
        raise LabContractError("AWS Lab execution is a separate explicit validation tier")


def _project_name(slug: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return f"forge-lab-{value[:48]}"


__all__ = [
    "COMPOSE_PROFILES",
    "RuntimePlan",
    "build_lifecycle_command",
    "build_runtime_plan",
    "guard_mutation",
]
