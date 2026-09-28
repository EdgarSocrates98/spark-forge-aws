"""Declared multi-repository workspace and deterministic semantic graph."""

from sparkforge.workspace.adapters import (
    FragmentAdapter,
    artifact_graph_fragment,
    semantic_graph_fragment,
    transcript_evidence_fragment,
)
from sparkforge.workspace.federated import (
    FederatedGraph,
    GraphAdapter,
    GraphFragment,
    compose,
    compose_federated_graph,
    compose_graph,
    compositor,
    fragment_from_graph,
)
from sparkforge.workspace.federation import compose_manifest_graph, compose_workspace_graph
from sparkforge.workspace.freshness import (
    FreshnessAssessment,
    FreshnessStatus,
    assess,
    assess_codeintel_freshness,
    assess_freshness,
    assess_index,
    read_codeintel_metadata,
    read_index_metadata,
)
from sparkforge.workspace.graph import WorkspaceGraph, build_graph
from sparkforge.workspace.impact import ImpactProjection, project_impact
from sparkforge.workspace.manifest import (
    CloudResource,
    GraphLink,
    Relationship,
    Repository,
    WorkspaceManifest,
    WorkspaceManifestError,
    fingerprint,
    load_manifest,
)
from sparkforge.workspace.semantic import (
    SemanticEdge,
    SemanticGraph,
    SemanticNode,
    build_semantic_graph,
)

__all__ = [
    "CloudResource",
    "GraphLink",
    "FragmentAdapter",
    "FederatedGraph",
    "FreshnessAssessment",
    "FreshnessStatus",
    "GraphAdapter",
    "GraphFragment",
    "ImpactProjection",
    "Repository",
    "Relationship",
    "WorkspaceGraph",
    "WorkspaceManifest",
    "WorkspaceManifestError",
    "SemanticEdge",
    "SemanticGraph",
    "SemanticNode",
    "build_semantic_graph",
    "build_graph",
    "compose",
    "compose_manifest_graph",
    "compose_federated_graph",
    "compose_graph",
    "compose_workspace_graph",
    "compositor",
    "fingerprint",
    "fragment_from_graph",
    "load_manifest",
    "artifact_graph_fragment",
    "project_impact",
    "semantic_graph_fragment",
    "transcript_evidence_fragment",
    "assess",
    "assess_codeintel_freshness",
    "assess_freshness",
    "assess_index",
    "read_codeintel_metadata",
    "read_index_metadata",
]
