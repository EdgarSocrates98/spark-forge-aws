from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from sparkforge_aws.workspace import (
    GraphFragment,
    assess_freshness,
    compose_federated_graph,
    project_impact,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "evals" / "token_efficient"
GRAPH_FIXTURE = FIXTURE_ROOT / "fixtures" / "federated_graph_cases.yaml"
TRANSCRIPT_FIXTURE = FIXTURE_ROOT / "fixtures" / "provider_transcripts.yaml"
QUALITY_FIXTURE = FIXTURE_ROOT / "fixtures" / "quality_cases.yaml"
SUITE = FIXTURE_ROOT / "suite.yaml"


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    assert value.get("schema_version") == 1, path
    cases = value.get("cases")
    assert isinstance(cases, list) and cases, path
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    assert len(ids) == len(cases)
    assert all(isinstance(case_id, str) and case_id for case_id in ids)
    assert len(set(ids)) == len(ids)
    return value


def _fragment(raw: dict[str, Any]) -> GraphFragment:
    return GraphFragment(
        source=str(raw["source_id"]),
        nodes=tuple(raw.get("nodes", ())),
        edges=tuple(raw.get("edges", ())),
        provenance=tuple(raw.get("provenance", ())),
        unresolved=tuple(raw.get("unresolved", ())),
        freshness=assess_freshness(
            raw.get("current_fingerprint"), raw.get("indexed_fingerprint")
        ),
    )


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return str(edge["source"]), str(edge["relation"]), str(edge["target"])


def test_offline_fixture_corpus_has_six_required_classes() -> None:
    graph_cases = _load(GRAPH_FIXTURE)["cases"]
    transcript_cases = _load(TRANSCRIPT_FIXTURE)["cases"]
    classes = {str(case["class"]) for case in (*graph_cases, *transcript_cases)}

    assert {
        "success",
        "conflict",
        "endpoint_absent",
        "truncation",
        "freshness",
        "transcript_absent",
    } <= classes
    assert {case["expected_freshness"] for case in graph_cases} >= {"stale", "unknown"}


def test_quality_fixture_uses_case_ids_and_suite_declares_offline_inputs() -> None:
    quality = _load(QUALITY_FIXTURE)
    suite = yaml.safe_load(SUITE.read_text(encoding="utf-8"))

    assert len(quality["cases"]) == 15
    assert suite["federated_graph_fixture"] == "fixtures/federated_graph_cases.yaml"
    assert suite["provider_transcript_fixture"] == "fixtures/provider_transcripts.yaml"
    assert suite["quality_fixture"] == "fixtures/quality_cases.yaml"


@pytest.mark.parametrize("case_id", ["graph-success", "graph-conflict", "graph-endpoint-absent"])
def test_graph_fixture_contract_preserves_explicit_nodes_edges_provenance_and_expected_impact(
    case_id: str,
) -> None:
    cases = {case["case_id"]: case for case in _load(GRAPH_FIXTURE)["cases"]}
    case = cases[case_id]

    assert case["fragments"]
    assert all(fragment.get("source_id") for fragment in case["fragments"])
    assert all("nodes" in fragment and "edges" in fragment for fragment in case["fragments"])
    assert all("provenance" in fragment for fragment in case["fragments"])
    assert set(case["expected_impact"]) == {
        "affected_jobs",
        "affected_datasets",
        "affected_tests",
        "affected_cloud_resources",
    }

    graph = compose_federated_graph(
        [_fragment(fragment) for fragment in case["fragments"]],
        **case["bounds"],
    )
    assert graph.freshness.status == case["expected_freshness"]
    assert sorted(node["id"] for node in graph.nodes) == sorted(case["expected_nodes"])
    assert sorted(_edge_key(edge) for edge in graph.edges) == sorted(
        tuple(edge) for edge in case["expected_edges"]
    )
    assert set(item["code"] for item in graph.unresolved) >= set(case["expected_unresolved"])
    impact = project_impact(graph, case["root_node"], max_depth=3)
    assert impact.to_dict() == {
        **case["expected_impact"],
        "unresolved": [dict(item) for item in impact.unresolved],
    }


def test_graph_fixture_contract_covers_bounds_and_freshness_without_default_fresh() -> None:
    cases = {case["case_id"]: case for case in _load(GRAPH_FIXTURE)["cases"]}
    for case_id in ("graph-truncation", "graph-freshness-stale", "graph-freshness-unknown"):
        case = cases[case_id]
        graph = compose_federated_graph(
            [_fragment(fragment) for fragment in case["fragments"]],
            **case["bounds"],
        )
        assert graph.freshness.status == case["expected_freshness"]
        assert graph.freshness.status != "fresh" or case["expected_freshness"] == "fresh"
        if case.get("expected_truncated"):
            assert graph.truncated is True
            assert len(graph.nodes) <= case["bounds"]["max_nodes"]
            assert len(graph.edges) <= case["bounds"]["max_edges"]
            assert len(graph.provenance) <= case["bounds"]["max_provenance"]


def test_provider_transcript_contract_keeps_tokens_separate_and_explicit() -> None:
    cases = {case["case_id"]: case for case in _load(TRANSCRIPT_FIXTURE)["cases"]}
    present = cases["transcript-synthetic"]
    absent = cases["transcript-absent"]

    assert present["transcript"]["usage"] == present["provider_tokens"]
    assert present["tokens_unresolved"] is False
    assert absent["transcript"] is None
    assert absent["provider_tokens"] is None
    assert absent["tokens_unresolved"] is True
    assert absent["unresolved"] == [{"code": "tokens_unresolved", "reason": "transcript_absent"}]


def test_offline_fixtures_do_not_import_aws_or_mutate_fixture_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockedAws(ModuleType):
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"AWS access attempted: {name}")

    monkeypatch.setitem(sys.modules, "boto3", BlockedAws("boto3"))
    paths = (GRAPH_FIXTURE, TRANSCRIPT_FIXTURE, QUALITY_FIXTURE, SUITE)
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}

    cases = _load(GRAPH_FIXTURE)["cases"]
    for case in cases:
        compose_federated_graph(
            [_fragment(fragment) for fragment in case["fragments"]],
            **case["bounds"],
        )
    _load(TRANSCRIPT_FIXTURE)
    _load(QUALITY_FIXTURE)
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}

    assert after == before
