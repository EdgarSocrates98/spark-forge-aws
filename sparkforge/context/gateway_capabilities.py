"""Provider-independent deterministic capability discovery."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.context.gateway_models import Capability, GatewayProfile


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    max_capabilities: int
    max_skills: int
    max_knowledge_chunks: int
    allow_agentic_escalation: bool


def load_profiles(path: Path | None = None) -> dict[GatewayProfile, ProfilePolicy]:
    source = path or Path(__file__).with_name("gateway_profiles.yaml")
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    profiles = raw.get("profiles", {}) if isinstance(raw, Mapping) else {}
    result: dict[GatewayProfile, ProfilePolicy] = {}
    for name, values in profiles.items():
        result[GatewayProfile(str(name))] = ProfilePolicy(
            max_capabilities=int(values["max_capabilities"]),
            max_skills=int(values["max_skills"]),
            max_knowledge_chunks=int(values["max_knowledge_chunks"]),
            allow_agentic_escalation=bool(values.get("allow_agentic_escalation", False)),
        )
    return result


def _terms(intent: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", intent.lower()))))


def discover_capabilities(
    intent: str,
    catalog: Mapping[str, Mapping[str, Any]],
    profile: GatewayProfile,
    policies: Mapping[GatewayProfile, ProfilePolicy],
    skills: list[Mapping[str, Any]] | None = None,
    knowledge: list[Mapping[str, Any]] | None = None,
) -> tuple[tuple[Capability, ...], ProfilePolicy]:
    policy = policies[profile]
    query_terms = set(_terms(intent))
    candidates: list[Capability] = []
    for name, spec in catalog.items():
        description = str(spec.get("description", ""))
        haystack = f"{name} {description}".lower()
        score = sum(3 if term in name.lower() else 1 for term in query_terms if term in haystack)
        if score:
            candidates.append(
                Capability(name=name, kind="tool", score=score, description=description)
            )
    for item in skills or []:
        name = str(item.get("name", item.get("id", "")))
        if not name:
            continue
        text = f"{name} {item.get('description', '')}".lower()
        score = sum(2 for term in query_terms if term in text)
        if score:
            candidates.append(
                Capability(
                    name=name,
                    kind="skill",
                    score=score,
                    description=str(item.get("description", "")),
                )
            )
    for item in knowledge or []:
        name = str(item.get("name", item.get("id", "")))
        if not name:
            continue
        text = f"{name} {item.get('description', '')}".lower()
        score = sum(2 for term in query_terms if term in text)
        if score:
            candidates.append(
                Capability(
                    name=name,
                    kind="knowledge",
                    score=score,
                    description=str(item.get("description", "")),
                )
            )
    candidates.sort(key=lambda item: (-item.score, item.kind, item.name))
    return tuple(candidates[: policy.max_capabilities]), policy
