from __future__ import annotations

import pytest

from sparkforge.workspace import GraphFragment, compose_federated_graph, project_impact


def _impact_graph():
    return compose_federated_graph(
        [
            GraphFragment(
                source="fixture",
                nodes=(
                    {"id": "job:daily", "kind": "job"},
                    {"id": "dataset:orders", "kind": "dataset"},
                    {"id": "test:orders", "kind": "test"},
                    {"id": "cloud:orders", "kind": "cloud_resource"},
                    {"id": "other:orders", "kind": "other"},
                ),
                edges=(
                    {"source": "job:daily", "relation": "writes", "target": "dataset:orders"},
                    {
                        "source": "dataset:orders",
                        "relation": "covered_by",
                        "target": "test:orders",
                    },
                    {
                        "source": "dataset:orders",
                        "relation": "corresponds_to",
                        "target": "cloud:orders",
                    },
                    {
                        "source": "cloud:orders",
                        "relation": "related_to",
                        "target": "other:orders",
                    },
                ),
            )
        ]
    )


def test_project_impact_returns_sorted_categories_from_explicit_edges() -> None:
    projection = project_impact(_impact_graph(), "job:daily", max_depth=3)

    assert projection.affected_jobs == ()
    assert projection.affected_datasets == ("dataset:orders",)
    assert projection.affected_tests == ("test:orders",)
    assert projection.affected_cloud_resources == ("cloud:orders",)
    assert projection.unresolved == ({"code": "impact_kind_unresolved", "node_id": "other:orders"},)


def test_project_impact_respects_depth_and_item_bounds() -> None:
    graph = _impact_graph()

    shallow = project_impact(graph, "job:daily", max_depth=1)
    bounded = project_impact(graph, "job:daily", max_depth=3, max_items=1)

    assert shallow.affected_datasets == ("dataset:orders",)
    assert shallow.affected_tests == ()
    assert shallow.affected_cloud_resources == ()
    assert bounded.affected_datasets == ("dataset:orders",)
    assert bounded.affected_tests == ("test:orders",)
    assert bounded.affected_cloud_resources == ("cloud:orders",)


def test_project_impact_preserves_graph_unresolved_and_rejects_invalid_bounds() -> None:
    graph = compose_federated_graph(
        [
            GraphFragment(
                source="fixture",
                nodes=({"id": "job:daily", "kind": "job"},),
                edges=(
                    {
                        "source": "job:daily",
                        "relation": "writes",
                        "target": "dataset:missing",
                    },
                ),
            )
        ]
    )

    projection = project_impact(graph, "job:daily")

    assert {item["code"] for item in projection.unresolved} == {"graph_edge_unresolved"}
    with pytest.raises(ValueError, match="invalid impact bounds"):
        project_impact(graph, "job:daily", max_depth=-1)
    with pytest.raises(ValueError, match="invalid impact bounds"):
        project_impact(graph, "job:daily", max_items=0)
