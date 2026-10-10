"""Spark Forge AWS → ForgeGraphView/v1 adapter.

Projects the real code-intelligence graph (`.sparkforge_aws/local/
codeintel/graph.sqlite3` — nodes/edges written by `code index`) onto
the view contract, read-only. The index stays authoritative; this only
projects it. ``unresolved_refs`` are never turned into edges — they are
honest holes in the graph, not inferred relations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sparkforge_aws._graphview import (
    ForgeGraphView,
    GraphEdgeView,
    GraphNodeView,
    new_descriptor,
)

PROVIDER = "spark-forge-aws"


def _db_path(root: Path) -> Path | None:
    from sparkforge_aws.codeintel.db import banco_para

    p = banco_para(root)
    return p if p.is_file() else None


def index_status(root: str | Path = ".") -> dict:
    """Honest graph availability — the federation/discovery answer."""
    db = _db_path(Path(root))
    if db is None:
        return {
            "provider": PROVIDER,
            "graph": "unavailable",
            "reason": "no code-intel index — run `sparkforge-aws code index` first",
        }
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        kinds = [r[0] for r in conn.execute("SELECT DISTINCT kind FROM edges")]
    finally:
        conn.close()
    return {
        "provider": PROVIDER,
        "graph": "available",
        "db": str(db),
        "nodes": nodes,
        "edges": edges,
        "edge_kinds": sorted(kinds),
    }


def build_view(root: str | Path = ".", *, limit: int = 5000) -> ForgeGraphView | None:
    """codeintel sqlite → view. None when no index exists."""
    db = _db_path(Path(root))
    if db is None:
        return None
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        rows = conn.execute(
            "SELECT nodes.id, nodes.kind, nodes.name, nodes.qualified_name,"
            "       files.path, nodes.start_line"
            "  FROM nodes JOIN files ON files.id = nodes.file_id"
            " ORDER BY nodes.qualified_name LIMIT ?",
            (limit,),
        ).fetchall()
        keep = {r[0] for r in rows}
        edges = conn.execute(
            "SELECT DISTINCT source_id, target_id, kind FROM edges"
            " WHERE source_id IN (SELECT id FROM nodes LIMIT ?)"
            "   AND target_id IN (SELECT id FROM nodes LIMIT ?)",
            (limit, limit),
        ).fetchall()
    finally:
        conn.close()

    limitations = []
    if total_nodes > len(rows):
        limitations.append(
            f"view truncated to {len(rows)} of {total_nodes} nodes (--limit)"
        )
    desc = new_descriptor(
        provider_id=PROVIDER,
        domain="code",
        graph_id="codeintel-graph",
        capabilities=(
            "node_inspect",
            "edge_inspect",
            "neighbors",
            "paths",
            "dependency_traversal",
            "impact_analysis",
            "search",
            "filter",
            "export",
        ),
        limitations=tuple(limitations),
    )
    object.__setattr__(desc, "node_count", len(rows))
    object.__setattr__(desc, "edge_count", len(edges))
    object.__setattr__(
        desc, "available_layers", tuple(sorted({r[1] for r in rows}))
    )
    nodes = tuple(
        GraphNodeView(
            id=r[0],
            kind=r[1],
            label=r[3] or r[2],
            domain="code",
            source_provider=PROVIDER,
            attributes={"file": r[4], "line": r[5]},
            epistemic_state="observed",
        )
        for r in rows
        if r[0] in keep
    )
    vedges = tuple(
        GraphEdgeView(
            id=f"{s}|{k}|{t}",
            source=s,
            target=t,
            kind=k,
            provenance="observed",
            epistemic_state="observed",
        )
        for s, t, k in edges
    )
    return ForgeGraphView(descriptor=desc, nodes=nodes, edges=vedges)
