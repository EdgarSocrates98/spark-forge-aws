"""Amazon Neptune Graph Database Specialization and Query Tuning Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NeptuneQueryReport:
    query_language: str  # opencypher, gremlin, sparql
    has_full_graph_scan: bool
    unindexed_edge_traversals: list[str] = field(default_factory=list)
    estimated_cost_class: str = "low"  # low, medium, high
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NeptuneSpecialist:
    """Analyzes Amazon Neptune queries, explain outputs, and data models."""

    def analyze_query_text(self, query_text: str) -> NeptuneQueryReport:
        q_lower = query_text.lower()
        is_cypher = "match" in q_lower or "return" in q_lower
        is_gremlin = "g.v(" in q_lower or "g.e(" in q_lower

        qlang = "openCypher" if is_cypher else ("Gremlin" if is_gremlin else "SPARQL")
        recs = []
        full_scan = False

        # OpenCypher full node scan without label filter
        if is_cypher:
            if "match (n)" in q_lower or "match (a)-[" in q_lower:
                full_scan = True
                recs.append(
                    "Unlabeled node pattern (`MATCH (n)`) triggers a full graph vertex scan. "
                    "Add specific node labels (`MATCH (n:Person)`)."
                )
            if "where" not in q_lower and "limit" not in q_lower:
                recs.append(
                    "Query lacks WHERE filter and LIMIT clause, risking memory exhaustion on "
                    "large graphs."
                )

        # Gremlin full scan
        if is_gremlin:
            if "g.v()" in q_lower:
                full_scan = True
                recs.append("`g.V()` without has() step scans all vertices in Neptune index.")

        return NeptuneQueryReport(
            query_language=qlang,
            has_full_graph_scan=full_scan,
            estimated_cost_class="high" if full_scan else "low",
            recommendations=recs,
        )
