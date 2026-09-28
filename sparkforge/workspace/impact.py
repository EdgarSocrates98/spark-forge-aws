"""Bounded impact projection over explicit federated graph edges."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sparkforge.workspace.federated import FederatedGraph


@dataclass(frozen=True, slots=True)
class ImpactProjection:
    affected_jobs: tuple[str, ...] = ()
    affected_datasets: tuple[str, ...] = ()
    affected_tests: tuple[str, ...] = ()
    affected_cloud_resources: tuple[str, ...] = ()
    unresolved: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "affected_jobs": list(self.affected_jobs),
            "affected_datasets": list(self.affected_datasets),
            "affected_tests": list(self.affected_tests),
            "affected_cloud_resources": list(self.affected_cloud_resources),
            "unresolved": [dict(item) for item in self.unresolved],
        }


def project_impact(
    graph: FederatedGraph,
    node_id: str,
    *,
    max_depth: int = 2,
    max_items: int = 100,
) -> ImpactProjection:
    if max_depth < 0 or max_items <= 0:
        raise ValueError("invalid impact bounds")

    nodes = {str(item.get("id")): item for item in graph.nodes if item.get("id")}
    unresolved = [dict(item) for item in graph.unresolved]
    if node_id not in nodes:
        unresolved.append({"code": "impact_node_unresolved", "node_id": node_id})

    groups: dict[str, list[str]] = {
        "affected_jobs": [],
        "affected_datasets": [],
        "affected_tests": [],
        "affected_cloud_resources": [],
    }
    for candidate in graph.neighbors(node_id, max_depth=max_depth):
        item = nodes.get(candidate)
        if item is None:
            unresolved.append({"code": "impact_node_unresolved", "node_id": candidate})
            continue
        category = _category(item, candidate)
        if category is None:
            unresolved.append({"code": "impact_kind_unresolved", "node_id": candidate})
            continue
        groups[category].append(candidate)

    return ImpactProjection(
        affected_jobs=_bounded_ids(groups["affected_jobs"], max_items),
        affected_datasets=_bounded_ids(groups["affected_datasets"], max_items),
        affected_tests=_bounded_ids(groups["affected_tests"], max_items),
        affected_cloud_resources=_bounded_ids(groups["affected_cloud_resources"], max_items),
        unresolved=_bounded_unresolved(unresolved, max_items),
    )


def _category(item: dict[str, Any], node_id: str) -> str | None:
    kind = str(item.get("kind") or "").strip()
    by_kind = {
        "job": "affected_jobs",
        "dataset": "affected_datasets",
        "test": "affected_tests",
        "cloud_resource": "affected_cloud_resources",
    }
    if kind:
        return by_kind.get(kind)
    for prefix, category in (
        ("job:", "affected_jobs"),
        ("dataset:", "affected_datasets"),
        ("test:", "affected_tests"),
        ("cloud:", "affected_cloud_resources"),
    ):
        if node_id.startswith(prefix):
            return category
    return None


def _bounded_ids(values: list[str], limit: int) -> tuple[str, ...]:
    return tuple(sorted(set(values))[:limit])


def _bounded_unresolved(values: list[dict[str, Any]], limit: int) -> tuple[dict[str, Any], ...]:
    unique = {json.dumps(item, sort_keys=True, default=str): item for item in values}
    ordered = [unique[key] for key in sorted(unique)]
    if len(ordered) <= limit:
        return tuple(ordered)
    summary = {"code": "impact_unresolved_truncated", "omitted": len(ordered) - limit}
    if limit == 1:
        return (summary,)
    return tuple(ordered[: limit - 1] + [summary])


__all__ = ["ImpactProjection", "project_impact"]
