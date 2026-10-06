from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge_aws.codeintel.index import indexar
from sparkforge_aws.workspace import (
    FreshnessAssessment,
    build_graph,
    build_semantic_graph,
    load_manifest,
)
from sparkforge_aws.workspace.manifest import WorkspaceManifestError


def test_workspace_manifest_and_graph_keep_declared_relationships(tmp_path: Path) -> None:
    (tmp_path / "pipelines").mkdir()
    (tmp_path / "shared").mkdir()
    (tmp_path / "pipelines" / "job.py").write_text("# job\n", encoding="utf-8")
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: customer-data
repositories:
  - name: pipelines
    path: pipelines
  - name: shared
    path: shared
relationships:
  pipelines:
    uses: [shared]
""",
        encoding="utf-8",
    )

    graph = build_graph(load_manifest(manifest_path))
    assert graph.edges[0].resolved is True
    assert graph.neighbors("pipelines") == ("shared",)
    assert graph.to_dict()["schema_version"] == 1


def test_workspace_manifest_rejects_path_escape(tmp_path: Path) -> None:
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: unsafe\nrepositories:\n  - name: outside\n    path: ../outside\n""",
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceManifestError, match="escapes"):
        load_manifest(manifest_path)


def test_semantic_graph_composes_symbols_and_data_flow(tmp_path: Path) -> None:
    pipelines = tmp_path / "pipelines"
    pipelines.mkdir()
    (pipelines / "job.py").write_text(
        'def run(spark):\n'
        '    df = spark.table("raw.events")\n'
        '    df.writeTo("gold.events").append()\n',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: customer-data
repositories:
  - name: pipelines
    path: pipelines
relationships: {}
""",
        encoding="utf-8",
    )
    database = pipelines / "pipeline.sqlite3"
    indexar(pipelines, database)

    graph = build_semantic_graph(
        load_manifest(manifest_path), databases={"pipelines": database}
    )

    kinds = {node.kind for node in graph.nodes}
    relations = {edge.relation for edge in graph.edges}
    assert {"repository", "file", "symbol", "dataset"} <= kinds
    assert {"READ", "WRITE"} <= relations
    assert graph.impact("repo:pipelines", direction="outbound")


def test_semantic_graph_serializes_explicit_freshness_states(tmp_path: Path) -> None:
    (tmp_path / "repo").mkdir()
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: customer-data
repositories:
  - name: repo
    path: repo
relationships: {}
""",
        encoding="utf-8",
    )
    manifest = load_manifest(manifest_path)

    unknown = build_semantic_graph(manifest).to_dict()
    fresh = build_semantic_graph(
        manifest,
        freshness=FreshnessAssessment("fresh", "same", "same", "fingerprint_match"),
    ).to_dict()
    stale = build_semantic_graph(
        manifest,
        freshness=FreshnessAssessment("stale", "current", "indexed", "fingerprint_mismatch"),
    ).to_dict()

    assert unknown["freshness"] == "unknown"
    assert fresh["freshness"] == "fresh"
    assert stale["freshness"] == "stale"


def test_manifest_carrega_recursos_cloud_declarados(tmp_path: Path) -> None:
    (tmp_path / "pipelines").mkdir()
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: customer-data
repositories:
  - name: pipelines
    path: pipelines
relationships: {}
cloud_resources:
  - id: events
    kind: dataset
    services: [glue, lakeformation, s3]
    account_id: '111111111111'
    catalog_id: '111111111111'
    region: us-east-1
    database: raw
    table: events
    bucket: customer-data
    prefix: raw/events/
""",
        encoding="utf-8",
    )

    manifest = load_manifest(manifest_path)

    assert [item.id for item in manifest.cloud_resources] == ["events"]
    assert manifest.cloud_resources[0].services == ("glue", "lakeformation", "s3")


def test_manifest_rejeita_traversal_em_recurso_cloud(tmp_path: Path) -> None:
    (tmp_path / "repo").mkdir()
    manifest_path = tmp_path / "workspace.yaml"
    manifest_path.write_text(
        """workspace: unsafe
repositories:
  - name: repo
    path: repo
relationships: {}
cloud_resources:
  - id: events
    kind: dataset
    services: [s3]
    bucket: customer-data
    prefix: raw/../other/
""",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceManifestError, match="traversal"):
        load_manifest(manifest_path)
