"""Agent Execution Graph — grafo tipado de execução agêntica.

Nós: agent, skill, tool, debate, experiment, gate, artifact,
     human_approval, decision, verification

Edges: depends_on, produces, consumes, contradicts, validates,
       invalidates, supersedes, requires, blocks

O grafo permite explicar:
```
CASE → hypotheses → agents → evidence → debate → experiments → decision
```

Não substitui o ExecutionDAG existente (workflows/dag.py) — o estende
com tipos de nó/edge agênticos.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"
    DEBATE = "debate"
    EXPERIMENT = "experiment"
    GATE = "gate"
    ARTIFACT = "artifact"
    HUMAN_APPROVAL = "human_approval"
    DECISION = "decision"
    VERIFICATION = "verification"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    CLAIM = "claim"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    CONTRADICTS = "contradicts"
    VALIDATES = "validates"
    INVALIDATES = "invalidates"
    SUPERSEDES = "supersedes"
    REQUIRES = "requires"
    BLOCKS = "blocks"


@dataclass(frozen=True)
class GraphNode:
    """Nó do grafo de execução agêntica."""

    node_type: NodeType
    ref_id: str  # id da entidade referenciada (agent_id, claim_id, etc.)
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        payload = json.dumps(
            {"type": self.node_type.value, "ref": self.ref_id},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        h = hashlib.sha1(payload, usedforsecurity=False).hexdigest()
        return f"node_{h[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "ref_id": self.ref_id,
            "label": self.label,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class GraphEdge:
    """Edge do grafo de execução agêntica."""

    source: str  # node_id
    target: str  # node_id
    edge_type: EdgeType
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        payload = json.dumps(
            {"s": self.source, "t": self.target, "e": self.edge_type.value},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        h = hashlib.sha1(payload, usedforsecurity=False).hexdigest()
        return f"edge_{h[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class ExecutionGraph:
    """Grafo de execução agêntica.

    Permite explicar o caminho:
    CASE → hypotheses → agents → evidence → debate → experiments → decision
    """

    case_id: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> GraphNode:
        """Adiciona um nó. Dedup por id."""
        existing = {n.id for n in self.nodes}
        if node.id not in existing:
            self.nodes.append(node)
        return node

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """Adiciona uma edge. Dedup por id."""
        existing = {e.id for e in self.edges}
        if edge.id not in existing:
            self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> GraphNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes if n.node_type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> list[GraphEdge]:
        return [e for e in self.edges if e.edge_type == edge_type]

    def get_neighbors(self, node_id: str, edge_type: EdgeType | None = None) -> list[GraphNode]:
        """Retorna nós vizinhos (outgoing edges)."""
        neighbor_ids: list[str] = []
        for e in self.edges:
            if e.source == node_id:
                if edge_type is None or e.edge_type == edge_type:
                    neighbor_ids.append(e.target)
        return [n for n in self.nodes if n.id in neighbor_ids]

    def get_dependencies(self, node_id: str) -> list[GraphNode]:
        """Retorna nós dos quais este nó depende (incoming depends_on edges)."""
        dep_ids: list[str] = []
        for e in self.edges:
            if e.target == node_id and e.edge_type == EdgeType.DEPENDS_ON:
                dep_ids.append(e.source)
        return [n for n in self.nodes if n.id in dep_ids]

    def get_contradictions(self, node_id: str) -> list[GraphNode]:
        """Retorna nós que contradizem este nó."""
        contra_ids: list[str] = []
        for e in self.edges:
            if e.source == node_id and e.edge_type == EdgeType.CONTRADICTS:
                contra_ids.append(e.target)
            if e.target == node_id and e.edge_type == EdgeType.CONTRADICTS:
                contra_ids.append(e.source)
        return [n for n in self.nodes if n.id in contra_ids]

    def explain_path(self, start_node_id: str, end_node_id: str) -> list[str]:
        """Explica o caminho de start a end (BFS)."""
        if start_node_id == end_node_id:
            return [start_node_id]

        visited: set[str] = set()
        queue: list[list[str]] = [[start_node_id]]

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if current in visited:
                continue
            visited.add(current)

            for e in self.edges:
                if e.source == current and e.edge_type in (
                    EdgeType.DEPENDS_ON,
                    EdgeType.PRODUCES,
                    EdgeType.CONSUMES,
                    EdgeType.VALIDATES,
                ):
                    neighbor = e.target
                    if neighbor == end_node_id:
                        return path + [neighbor]
                    if neighbor not in visited:
                        queue.append(path + [neighbor])

        return []  # no path found

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    @property
    def summary(self) -> dict[str, int]:
        """Contagem por tipo de nó."""
        counts: dict[str, int] = {}
        for n in self.nodes:
            key = n.node_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts


def build_graph_from_case(
    case_id: str,
    claims: list[dict[str, Any]] | None = None,
    hypotheses: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    agents: list[str] | None = None,
) -> ExecutionGraph:
    """Constrói um ExecutionGraph a partir das entidades de um case.

    Cria nós para cada entidade e edges de dependência/contradição.
    """
    graph = ExecutionGraph(case_id=case_id)

    claims = claims or []
    hypotheses = hypotheses or []
    evidence = evidence or []
    decisions = decisions or []
    agents = agents or []

    # Add agent nodes
    for agent_id in agents:
        graph.add_node(
            GraphNode(
                node_type=NodeType.AGENT,
                ref_id=agent_id,
                label=agent_id,
            )
        )

    # Add claim nodes
    for c in claims:
        graph.add_node(
            GraphNode(
                node_type=NodeType.CLAIM,
                ref_id=c.get("id", ""),
                label=c.get("statement", "")[:80],
                metadata={"claimant": c.get("claimant", ""), "claim_type": c.get("claim_type", "")},
            )
        )
        # Edge: agent produces claim
        claimant = c.get("claimant", "")
        if claimant:
            agent_node = graph.get_nodes_by_type(NodeType.AGENT)
            for an in agent_node:
                if an.ref_id == claimant:
                    graph.add_edge(
                        GraphEdge(
                            source=an.id,
                            target=graph.get_nodes_by_type(NodeType.CLAIM)[-1].id,
                            edge_type=EdgeType.PRODUCES,
                        )
                    )

    # Add evidence nodes
    for e in evidence:
        graph.add_node(
            GraphNode(
                node_type=NodeType.EVIDENCE,
                ref_id=e.get("id", ""),
                label=e.get("source", "")[:80],
                metadata={"authority": e.get("authority", "")},
            )
        )

    # Add hypothesis nodes
    for h in hypotheses:
        graph.add_node(
            GraphNode(
                node_type=NodeType.HYPOTHESIS,
                ref_id=h.get("id", ""),
                label=h.get("statement", "")[:80],
                metadata={"status": h.get("status", ""), "confidence": h.get("confidence", "")},
            )
        )

    # Add decision nodes
    for d in decisions:
        graph.add_node(
            GraphNode(
                node_type=NodeType.DECISION,
                ref_id=d.get("id", ""),
                label=d.get("problem", "")[:80],
                metadata={
                    "selected": d.get("selected_option", ""),
                    "confidence": d.get("confidence", ""),
                },
            )
        )

    # Build edges: evidence supports/contradicts claims
    ev_nodes = graph.get_nodes_by_type(NodeType.EVIDENCE)
    claim_nodes = graph.get_nodes_by_type(NodeType.CLAIM)
    for ev_node in ev_nodes:
        ev_data = next((e for e in evidence if e.get("id") == ev_node.ref_id), None)
        if not ev_data:
            continue
        for claim_id in ev_data.get("supports", []):
            for cn in claim_nodes:
                if cn.ref_id == claim_id:
                    graph.add_edge(
                        GraphEdge(
                            source=ev_node.id,
                            target=cn.id,
                            edge_type=EdgeType.VALIDATES,
                        )
                    )
        for claim_id in ev_data.get("contradicts", []):
            for cn in claim_nodes:
                if cn.ref_id == claim_id:
                    graph.add_edge(
                        GraphEdge(
                            source=ev_node.id,
                            target=cn.id,
                            edge_type=EdgeType.CONTRADICTS,
                        )
                    )

    return graph
