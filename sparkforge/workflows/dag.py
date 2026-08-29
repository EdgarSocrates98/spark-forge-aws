"""Execution DAG and Waves Engine for SparkForge Workflows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DAGNode:
    id: str
    node_type: str  # task, agent, tool, eval, gate, artifact
    payload: dict[str, Any] = field(default_factory=dict)


class ExecutionDAG:
    """Directed Acyclic Graph with Waves scheduling."""

    def __init__(self) -> None:
        self.nodes: dict[str, DAGNode] = {}
        self.dependencies: dict[str, set[str]] = defaultdict(
            set
        )  # node_id -> dependencies (must run before)
        self.dependents: dict[str, set[str]] = defaultdict(set)  # node_id -> dependent nodes

    def add_node(
        self, node_id: str, node_type: str = "task", payload: dict[str, Any] | None = None
    ) -> DAGNode:
        node = DAGNode(id=node_id, node_type=node_type, payload=payload or {})
        self.nodes[node_id] = node
        return node

    def add_dependency(self, target_id: str, depends_on_id: str) -> None:
        if target_id not in self.nodes:
            self.add_node(target_id)
        if depends_on_id not in self.nodes:
            self.add_node(depends_on_id)
        self.dependencies[target_id].add(depends_on_id)
        self.dependents[depends_on_id].add(target_id)

    def detect_cycles(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in self.dependents[node_id]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def compute_waves(self) -> list[list[DAGNode]]:
        """Groups independent nodes into waves for parallel/sequential scheduling."""
        if self.detect_cycles():
            raise ValueError("Cycle detected in Execution DAG; cannot compute waves.")

        in_degree = {nid: len(self.dependencies[nid]) for nid in self.nodes}
        current_wave_ids = [nid for nid, deg in in_degree.items() if deg == 0]

        waves: list[list[DAGNode]] = []

        while current_wave_ids:
            wave_nodes = [self.nodes[nid] for nid in current_wave_ids]
            waves.append(wave_nodes)

            next_wave_ids = []
            for nid in current_wave_ids:
                for dependent in self.dependents[nid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_wave_ids.append(dependent)

            current_wave_ids = next_wave_ids

        return waves
