"""Offline Lab Doctor: host capability checks without starting Docker."""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import LabContractError, load_version_registry


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[dict[str, Any], ...]
    profiles: tuple[dict[str, Any], ...]
    unresolved: tuple[dict[str, Any], ...]

    @property
    def ready(self) -> bool:
        return not any(item.get("status") == "unavailable" for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": "Forge Lab",
            "ready": self.ready,
            "checks": [dict(item) for item in self.checks],
            "profiles": [dict(item) for item in self.profiles],
            "unresolved": [dict(item) for item in self.unresolved],
        }


PROFILE_REQUIREMENTS = {
    "core": {"memory_gb": 1, "components": ["minio", "iceberg_rest"]},
    "spark": {"memory_gb": 2, "components": ["spark"]},
    "kafka": {"memory_gb": 2, "components": ["kafka"]},
    "streaming": {"memory_gb": 4, "components": ["kafka", "spark"]},
    "flink": {"memory_gb": 4, "components": ["kafka", "flink"]},
    "lakehouse": {"memory_gb": 6, "components": ["spark", "flink", "iceberg_rest", "minio"]},
    "cdc": {"memory_gb": 4, "components": ["postgres", "debezium", "kafka"]},
    "polaris": {"memory_gb": 4, "components": ["polaris", "minio"]},
    "observability": {"memory_gb": 2, "components": ["prometheus", "otel_collector"]},
    "chaos": {"memory_gb": 1, "components": ["toxiproxy"]},
    "full": {"memory_gb": 10, "components": ["all"]},
}


def run_doctor(
    repo: str | Path = ".", *, registry_path: str | Path = "lab/versions.yaml"
) -> DoctorReport:
    root = Path(repo).expanduser().resolve()
    checks: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    docker = shutil.which("docker")
    checks.append(
        {"name": "docker", "status": "available" if docker else "unavailable", "path": docker or ""}
    )
    checks.append(
        {
            "name": "compose",
            "status": "available" if docker else "unresolved",
            "reason": "requires docker compose plugin",
        }
    )
    checks.append({"name": "architecture", "status": "available", "value": platform.machine()})
    checks.append({"name": "cpu", "status": "available", "value": os.cpu_count() or 1})
    disk = shutil.disk_usage(root)
    checks.append(
        {"name": "disk_gb", "status": "available", "value": round(disk.free / 1024**3, 2)}
    )
    try:
        registry = load_version_registry(root / registry_path)
    except LabContractError as exc:
        checks.append({"name": "version_registry", "status": "unavailable", "reason": str(exc)})
    else:
        missing_digest = sorted(
            name for name, value in registry.defaults.items() if not value.get("digest")
        )
        checks.append(
            {
                "name": "version_registry",
                "status": "available",
                "components": len(registry.defaults),
            }
        )
        if missing_digest:
            unresolved.append(
                {
                    "code": "image_digest_unresolved",
                    "components": missing_digest,
                    "reason": "registry declares tags; host must resolve digest before run",
                }
            )
    profiles = tuple(
        {"name": name, **value, "status": "unresolved_until_host_check"}
        for name, value in PROFILE_REQUIREMENTS.items()
    )
    return DoctorReport(tuple(checks), profiles, tuple(unresolved))


__all__ = ["DoctorReport", "PROFILE_REQUIREMENTS", "run_doctor"]
