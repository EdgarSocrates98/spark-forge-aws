"""`graph view`/`graph ui` model integrity: emitted edges never dangle.

lf-0021: the edge SQL used to take its node subset by ROWID order
(``SELECT id FROM nodes LIMIT ?``) while the node window used
``ORDER BY qualified_name LIMIT ?`` — two different subsets, so a truncated
view emitted edges whose endpoints were not in the emitted node set.
"""

from __future__ import annotations

from sparkforge_aws import graphview
from sparkforge_aws.codeintel.db import abrir, banco_para, criar_schema


def _index(root, nodes, edges):
    """Build a real codeintel sqlite under ``root``'s state dir."""
    db = banco_para(root)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = abrir(db)
    criar_schema(conn)
    conn.execute(
        "INSERT INTO files (id,path,language,content_sha256,size_bytes,"
        "modified_ns,indexed_at) VALUES ('f1','a.py','python','x',1,1,1)"
    )
    for nid, qname in nodes:
        conn.execute(
            "INSERT INTO nodes (id,file_id,kind,name,qualified_name,"
            "start_line,end_line) VALUES (?,'f1','function',?,?,1,2)",
            (nid, nid, qname),
        )
    for src, tgt in edges:
        conn.execute(
            "INSERT INTO edges (source_id,target_id,kind,line) "
            "VALUES (?,?,'calls',5)",
            (src, tgt),
        )
    conn.close()
    return db


def test_view_edges_never_dangle(tmp_path, monkeypatch):
    """Insertion (rowid) order must NOT decide the edge window.

    ``n_z`` is inserted first but sorts last by qualified_name, so with
    ``limit=3`` the node window keeps {n_a, n_b, n_c}; the edge n_b→n_z has
    its target outside the window and must not be emitted. Under the old
    rowid-order subquery the edge window kept {n_z, n_a, n_b} and n_b→n_z
    came out dangling.
    """
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)
    nodes = [
        ("n_z", "zzz.zeta"),
        ("n_a", "aaa.alpha"),
        ("n_b", "bbb.beta"),
        ("n_c", "ccc.gamma"),
    ]
    _index(tmp_path, nodes, [("n_a", "n_b"), ("n_b", "n_z")])

    view = graphview.build_view(tmp_path, limit=3)
    assert view is not None
    emitted = {n.id for n in view.nodes}
    assert emitted == {"n_a", "n_b", "n_c"}
    for e in view.edges:
        assert e.source in emitted and e.target in emitted
    assert [(e.source, e.target) for e in view.edges] == [("n_a", "n_b")]
    # contract + descriptor stay consistent with what was actually emitted
    doc = view.to_dict()
    assert doc["schema"] == "forge/ForgeGraphView/v1"
    assert doc["descriptor"]["edge_count"] == len(doc["edges"]) == 1
    assert doc["descriptor"]["node_count"] == len(doc["nodes"]) == 3
    assert "truncated" in doc["descriptor"]["limitations"][0]


def test_view_edges_all_survive_when_window_covers_them(tmp_path, monkeypatch):
    """Same fixture, full window: both edges land inside and are emitted."""
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)
    nodes = [
        ("n_z", "zzz.zeta"),
        ("n_a", "aaa.alpha"),
        ("n_b", "bbb.beta"),
        ("n_c", "ccc.gamma"),
    ]
    _index(tmp_path, nodes, [("n_a", "n_b"), ("n_b", "n_z")])
    view = graphview.build_view(tmp_path, limit=10)
    assert view is not None
    assert len(view.edges) == 2
    emitted = {n.id for n in view.nodes}
    for e in view.edges:
        assert e.source in emitted and e.target in emitted


def test_build_view_none_without_index(tmp_path, monkeypatch):
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)
    assert graphview.build_view(tmp_path) is None
