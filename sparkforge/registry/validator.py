"""Canonical Registry Validator.

Validates manifests using JSON Schema and model constraints.
"""
from __future__ import annotations

from typing import Any, Optional

import jsonschema

from sparkforge.registry.models import (
    AgentManifest,
    EvalManifest,
    KnowledgeManifest,
    PolicyManifest,
    SkillManifest,
    TeamManifest,
    ToolManifest,
    WorkflowManifest,
)

AGENT_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "version", "description", "purpose", "role"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "name": {"type": "string"},
        "version": {"type": "string"},
        "description": {"type": "string"},
        "purpose": {"type": "string"},
        "role": {"type": "string"},
        "domains": {"type": "array", "items": {"type": "string"}},
        "capabilities": {"type": "array", "items": {"type": "string"}},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "optional_skills": {"type": "array", "items": {"type": "string"}},
        "allowed_tools": {"type": "array", "items": {"type": "string"}},
        "denied_tools": {"type": "array", "items": {"type": "string"}},
        "knowledge_refs": {"type": "array", "items": {"type": "string"}},
        "risk_level": {"type": "string", "enum": ["read_only", "reversible", "sensitive", "destructive"]},
    },
}

SKILL_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "version", "description"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "name": {"type": "string"},
        "version": {"type": "string"},
        "description": {"type": "string"},
        "triggers": {"type": "array", "items": {"type": "string"}},
        "anti_triggers": {"type": "array", "items": {"type": "string"}},
        "procedure_path": {"type": "string"},
        "references": {"type": "array", "items": {"type": "string"}},
        "required_tools": {"type": "array", "items": {"type": "string"}},
        "risk_level": {"type": "string", "enum": ["read_only", "reversible", "sensitive", "destructive"]},
    },
}

TOOL_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "namespace", "description", "input_schema", "output_schema"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "name": {"type": "string"},
        "namespace": {"type": "string"},
        "description": {"type": "string"},
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "mutation_class": {"type": "string", "enum": ["read_only", "reversible", "sensitive", "destructive"]},
        "deterministic": {"type": "boolean"},
        "cacheable": {"type": "boolean"},
    },
}


class ValidationError(Exception):
    """Raised when a manifest fails validation."""


def validate_agent_dict(data: dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=data, schema=AGENT_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Agent validation error for '{data.get('id', 'unknown')}': {e.message}") from e


def validate_skill_dict(data: dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=data, schema=SKILL_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Skill validation error for '{data.get('id', 'unknown')}': {e.message}") from e


def validate_tool_dict(data: dict[str, Any]) -> None:
    try:
        jsonschema.validate(instance=data, schema=TOOL_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Tool validation error for '{data.get('id', 'unknown')}': {e.message}") from e
