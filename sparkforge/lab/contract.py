"""Version, fidelity and resource contracts for Forge Lab.

This module is deliberately offline. It validates declarations and never
resolves tags, pulls images, or contacts a cloud service.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class LabContractError(ValueError):
    """Invalid Forge Lab product contract."""


FIDELITY_TIERS = frozenset({"L0", "L1", "L2", "L3"})
FIDELITY_NAMES = {
    "L0": "deterministic_fixture",
    "L1": "real_local_engine",
    "L2": "service_contract",
    "L3": "cloud_validation",
}
LAB_MODES = frozenset({"lite", "standard", "deep"})
LAB_PROFILES = frozenset({"core", "spark", "kafka", "streaming", "flink", "lakehouse", "cdc", "polaris", "observability", "chaos", "full"})
RESULT_CLASSIFICATIONS = frozenset({"PASS", "FAIL", "UNRESOLVED", "INFRA_FAILURE", "INVALID_SCENARIO"})


@dataclass(frozen=True, slots=True)
class Fidelity:
    tier: str
    environment: str
    implementation: str
    proves: tuple[str, ...]
    does_not_prove: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "name": FIDELITY_NAMES[self.tier],
            "environment": self.environment,
            "implementation": self.implementation,
            "proves": list(self.proves),
            "does_not_prove": list(self.does_not_prove),
        }


@dataclass(frozen=True, slots=True)
class VersionRegistry:
    schema_version: int
    defaults: Mapping[str, Mapping[str, Any]]
    compatibility: object
    raw: Mapping[str, Any]

    def serialized_values(self) -> tuple[str, ...]:
        # Contract values are checked for forbidden mutable tags. Mapping keys
        # describe the schema and may legitimately contain words such as
        # ``forbid_latest``; they are not image/version values.
        return tuple(_walk_values(self.raw))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "defaults": {key: dict(value) for key, value in self.defaults.items()},
            "compatibility": _plain(self.compatibility),
        }

    def component(self, name: str) -> Mapping[str, Any]:
        try:
            return self.defaults[name]
        except KeyError as exc:
            raise LabContractError(f"version registry component not found: {name}") from exc


@dataclass(frozen=True, slots=True)
class LabResourceContract:
    profile: str
    mode: str
    required_memory_gb: float
    required_cpu: float
    runtime_class: str
    network: str
    ports: tuple[int, ...]
    destructive_behavior: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "mode": self.mode,
            "required_memory_gb": self.required_memory_gb,
            "required_cpu": self.required_cpu,
            "runtime_class": self.runtime_class,
            "network": self.network,
            "ports": list(self.ports),
            "destructive_behavior": self.destructive_behavior,
        }


def load_version_registry(path: str | Path) -> VersionRegistry:
    target = Path(path).expanduser().resolve()
    raw = _load_document(target, "version registry")
    version = raw.get("schema_version")
    if version != 1:
        raise LabContractError("version registry schema_version must be 1")
    defaults_raw = raw.get("defaults")
    if not isinstance(defaults_raw, Mapping) or not defaults_raw:
        raise LabContractError("version registry defaults must be a non-empty object")
    defaults: dict[str, Mapping[str, Any]] = {}
    for name, value in defaults_raw.items():
        if not isinstance(name, str) or not isinstance(value, Mapping):
            raise LabContractError("version registry defaults must map names to objects")
        tag = value.get("tag")
        image = value.get("image")
        if not isinstance(image, str) or not image.strip() or not isinstance(tag, str) or not tag.strip():
            raise LabContractError(f"registry component {name} requires image and tag")
        if "latest" in f"{image}:{tag}".lower():
            raise LabContractError(f"registry component {name} cannot use latest")
        digest = value.get("digest")
        if digest is not None and (not isinstance(digest, str) or not digest.startswith("sha256:")):
            raise LabContractError(f"registry component {name} digest must be sha256 or omitted")
        defaults[name] = dict(value)
    serialized = tuple(_walk_strings(raw))
    if any(value.lower() == "latest" or value.endswith(":latest") for value in serialized):
        raise LabContractError("version registry cannot contain latest")
    compatibility = raw.get("compatibility", {})
    if not isinstance(compatibility, (Mapping, list)):
        raise LabContractError("version registry compatibility must be an object or list")
    return VersionRegistry(1, defaults, _plain(compatibility), dict(raw))


def load_resource_contract(value: object) -> LabResourceContract:
    if not isinstance(value, Mapping):
        raise LabContractError("resource contract must be an object")
    profile = _required(value.get("profile", "core"), "resource.profile")
    mode = _required(value.get("mode", "lite"), "resource.mode")
    if profile not in LAB_PROFILES:
        raise LabContractError(f"unsupported lab profile: {profile}")
    if mode not in LAB_MODES:
        raise LabContractError(f"unsupported lab mode: {mode}")
    ports = value.get("ports", [])
    if not isinstance(ports, list) or not all(isinstance(port, int) and 1 <= port <= 65535 for port in ports):
        raise LabContractError("resource.ports must contain valid integers")
    required_memory = value.get("required_memory_gb", 0.5)
    required_cpu = value.get("required_cpu", 1)
    if not isinstance(required_memory, (int, float)) or required_memory <= 0:
        raise LabContractError("resource.required_memory_gb must be positive")
    if not isinstance(required_cpu, (int, float)) or required_cpu <= 0:
        raise LabContractError("resource.required_cpu must be positive")
    return LabResourceContract(
        profile=profile,
        mode=mode,
        required_memory_gb=float(required_memory),
        required_cpu=float(required_cpu),
        runtime_class=_required(value.get("runtime_class", "smoke"), "resource.runtime_class"),
        network=_required(value.get("network", "isolated"), "resource.network"),
        ports=tuple(sorted(set(ports))),
        destructive_behavior=bool(value.get("destructive_behavior", False)),
    )


def _load_document(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise LabContractError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise LabContractError(f"{label} unreadable: {path}") from exc
    if not isinstance(value, Mapping):
        raise LabContractError(f"{label} root must be an object")
    return value


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LabContractError(f"{field} must be a non-empty string")
    return value.strip()


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        result: list[str] = []
        for key, item in value.items():
            result.extend(_walk_strings(key))
            result.extend(_walk_strings(item))
        return result
    if isinstance(value, list | tuple):
        result = []
        for item in value:
            result.extend(_walk_strings(item))
        return result
    return []


def _walk_values(value: object) -> list[str]:
    """Return scalar strings from values, excluding mapping keys."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        result: list[str] = []
        for item in value.values():
            result.extend(_walk_values(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_walk_values(item))
        return result
    return []


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


__all__ = [
    "FIDELITY_NAMES",
    "FIDELITY_TIERS",
    "LAB_MODES",
    "LAB_PROFILES",
    "RESULT_CLASSIFICATIONS",
    "Fidelity",
    "LabContractError",
    "LabResourceContract",
    "VersionRegistry",
    "load_resource_contract",
    "load_version_registry",
]
