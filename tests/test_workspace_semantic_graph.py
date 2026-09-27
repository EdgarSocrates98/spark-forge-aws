from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.workspace import build_graph, load_manifest
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
