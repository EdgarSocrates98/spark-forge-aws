from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.codeintel.index import indexar
from sparkforge.workspace import build_graph, build_semantic_graph, load_manifest
from sparkforge.workspace.manifest import WorkspaceManifestError


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
