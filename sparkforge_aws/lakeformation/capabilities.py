"""Version-aware Lake Formation capability data for the architecture analyzer."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from sparkforge_aws.knowledge_ref import knowledge_dir, safe_knowledge_file

_RELATIVE = "lakeformation/capability-matrix.yaml"
_VALID_STATUSES = frozenset(
    {"supported", "limited", "read_only", "version_dependent", "not_supported", "unknown"}
)


def _path():
    return safe_knowledge_file(knowledge_dir(), _RELATIVE)


def _release_key(value: str) -> str:
    parts = str(value).strip().split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else str(value).strip()


@lru_cache(maxsize=1)
def load_matrix() -> dict[str, Any]:
    with _path().open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    engines = set(document.get("engines") or [])
    sources = document.get("sources") or {}
    statuses = set(document.get("statuses") or [])
    if not engines or statuses != _VALID_STATUSES:
        raise ValueError("capability matrix must declare closed engines and statuses")
    rows = document.get("capabilities") or []
    errors: list[str] = []
    for index, row in enumerate(rows):
        prefix = f"capabilities[{index}]"
        if row.get("engine") not in engines:
            errors.append(f"{prefix}.engine desconhecido")
        if row.get("status") not in _VALID_STATUSES:
            errors.append(f"{prefix}.status invalido")
        if row.get("status") != "unknown":
            if not row.get("source") or row["source"] not in sources:
                errors.append(f"{prefix}.source ausente ou desconhecido")
            if not row.get("last_verified") or not row.get("limitations"):
                errors.append(f"{prefix}.last_verified/limitations ausente")
    if errors:
        raise ValueError("capability matrix invalida: " + "; ".join(errors))
    return document


def capability(
    engine: str,
    runtime: str,
    access_model: str,
    table_format: str,
    operation: str,
    api: str | None = None,
) -> dict[str, Any]:
    """Return one exact capability row, or an explicit unresolved result."""
    runtime_key = _release_key(runtime)
    candidates = [
        row
        for row in load_matrix()["capabilities"]
        if row.get("engine") == engine
        and _release_key(row.get("runtime", "")) == runtime_key
        and row.get("access_model") == access_model
        and row.get("format") == table_format
        and row.get("operation") == operation
        and (api is None or row.get("api") == api)
    ]
    if len(candidates) == 1:
        return dict(candidates[0])
    if len(candidates) > 1:
        return {
            "status": "unknown",
            "reason": "capability_ambiguous",
            "required_verification": "declare API exactly to select one capability cell",
        }
    return {
        "status": "unknown",
        "reason": "capability_not_declared",
        "required_verification": (
            f"official source for {engine} {runtime} {access_model} "
            f"{table_format} {operation}"
        ),
    }


def clear_cache() -> None:
    load_matrix.cache_clear()


__all__ = ["capability", "clear_cache", "load_matrix"]
