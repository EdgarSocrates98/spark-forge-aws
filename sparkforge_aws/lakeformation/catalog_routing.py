"""Catalog and account routing without semantic ID aliases."""

from __future__ import annotations

from typing import Any

_DIMENSIONS = (
    "job_account_id",
    "local_account_id",
    "source_account_id",
    "target_account_id",
    "source_catalog_owner_account_id",
    "target_catalog_owner_account_id",
)


def _catalog_view(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _comparison(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    if actual in (None, "") or expected in (None, ""):
        status = "unresolved"
    else:
        status = "pass" if str(actual) == str(expected) else "fail"
    return {
        "name": name,
        "actual": actual,
        "expected": expected,
        "status": status,
    }


def route_catalogs(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve catalog ownership while preserving every account dimension."""
    required: list[str] = []
    source = _catalog_view(payload.get("source_catalog"))
    target = _catalog_view(payload.get("target_catalog"))
    dimensions = {name: payload.get(name) for name in _DIMENSIONS}
    dimensions["source_catalog_owner_account_id"] = source.get("owner_account_id")
    dimensions["target_catalog_owner_account_id"] = target.get("owner_account_id")
    comparisons: list[dict[str, Any]] = []
    for name, value in dimensions.items():
        if not value:
            required.append(name)

    catalogs: dict[str, dict[str, Any]] = {}
    for role in ("source", "target"):
        catalog = _catalog_view(payload.get(f"{role}_catalog"))
        catalogs[role] = catalog
        for key in ("name", "owner_account_id", "glue_id", "glue_account_id"):
            if not catalog.get(key):
                required.append(f"{role}_catalog.{key}")
        ownership = _comparison(
            f"{role}.glue_id_vs_owner",
            catalog.get("glue_id"),
            catalog.get("owner_account_id"),
        )
        comparisons.append(ownership)
        if ownership["status"] == "fail":
            required.append(f"{role}_catalog.owner_vs_glue_id")
        expected_context = catalog.get("expected_glue_account_id")
        context = _comparison(
            f"{role}.glue_account_id_vs_expected_context",
            catalog.get("glue_account_id"),
            expected_context,
        )
        comparisons.append(context)
        if context["status"] == "fail":
            required.append(f"{role}_catalog.glue_account_context")
        if (
            catalog.get("glue_id")
            and catalog.get("glue_account_id")
            and str(catalog["glue_id"]) != str(catalog["glue_account_id"])
            and context["status"] != "pass"
        ):
            required.append("glue_id_account_id_diverge")

    return {
        "status": "unresolved" if required else "ok",
        "dimensions": dimensions,
        "catalogs": catalogs,
        "semantic_comparisons": comparisons,
        "required_verification": sorted(set(required)),
        "observed": [
            "catalog ownership is explicit",
            "glue.id and glue.account-id are independent properties",
        ],
    }


__all__ = ["route_catalogs"]
