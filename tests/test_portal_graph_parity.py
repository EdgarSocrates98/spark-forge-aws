"""lf-0023 parity — the portal ``/graphs`` endpoint serves the identical
``forge/ForgeGraphView/v1`` document the CLI ``graph view``/``graph ui``
produces.

The Forge Portal's Graph Explorer renders the served document verbatim;
the Python Graph Studio (``graph ui``) renders the same document. Both
paths must see the same vertex/edge set — this test pins the contract at
the producer boundary (``graphview.build_view`` is the single source).
"""

from __future__ import annotations

import json

from sparkforge_aws import graphview, portal_adapter
from sparkforge_aws.adapters.cli import main as cli_main
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
    for nid, qname, kind in nodes:
        conn.execute(
            "INSERT INTO nodes (id,file_id,kind,name,qualified_name,"
            "start_line,end_line) VALUES (?,'f1',?,?,?,1,2)",
            (nid, kind, nid, qname),
        )
    for src, tgt, kind in edges:
        conn.execute(
            "INSERT INTO edges (source_id,target_id,kind,line) "
            "VALUES (?,?,?,5)",
            (src, tgt, kind),
        )
    conn.close()
    return db


def _fixture(tmp_path):
    nodes = [
        ("n_a", "aaa.alpha", "function"),
        ("n_b", "bbb.beta", "function"),
        ("n_c", "ccc.gamma", "module"),
        ("n_d", "ddd.delta", "class"),  # isolated vertex — no edges
    ]
    edges = [("n_a", "n_b", "calls"), ("n_a", "n_c", "imports")]
    _index(tmp_path, nodes, edges)


def test_portal_graphs_serves_identical_view_as_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)
    _fixture(tmp_path)

    # CLI side — `sparkforge-aws graph view --root <repo>` (the document
    # `graph ui` hands to the Graph Studio, verbatim).
    code = cli_main(["graph", "view", "--root", str(tmp_path)])
    cli_doc = json.loads(capsys.readouterr().out)
    assert code == 0
    assert cli_doc["schema"] == "forge/ForgeGraphView/v1"

    # Portal side — the adapter's GET /api/v1/graphs response. The wire
    # payload is the JSON serialization, so compare at the JSON level
    # (to_dict() keeps tuples; the served bytes are lists).
    bundle = portal_adapter.SparkForgePortal(tmp_path)._graphs()
    assert bundle["availability"]["state"] == "available"
    assert len(bundle["views"]) == 1
    portal_doc = json.loads(json.dumps(bundle["views"][0], default=str))

    # Identical projection document — same vertex/edge set, same
    # descriptor, same provenance. Byte-for-byte at the JSON level.
    assert portal_doc == cli_doc
    assert portal_doc["schema"] == cli_doc["schema"]
    assert {n["id"] for n in portal_doc["nodes"]} == {
        n["id"] for n in cli_doc["nodes"]
    }
    assert {e["id"] for e in portal_doc["edges"]} == {
        e["id"] for e in cli_doc["edges"]
    }
    # the isolated vertex is present on both sides (not silently dropped)
    assert "n_d" in {n["id"] for n in portal_doc["nodes"]}


def test_portal_graphs_matches_build_view_directly(tmp_path, monkeypatch):
    """The adapter never remaps: ``views[0]`` is ``build_view().to_dict()``
    unchanged — no bespoke data path bypassing the contract."""
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)
    _fixture(tmp_path)

    view = graphview.build_view(tmp_path)
    assert view is not None
    doc = portal_adapter.SparkForgePortal(tmp_path)._graphs()
    assert doc["views"][0] == view.to_dict()


def test_portal_graphs_no_graph_state_matches_cli_refusal(
    tmp_path, monkeypatch, capsys
):
    """Both surfaces name the same honest absence, not a divergent state."""
    monkeypatch.delenv("SPARKFORGE_AWS_HOME", raising=False)

    code = cli_main(["graph", "view", "--root", str(tmp_path)])
    refusal = json.loads(capsys.readouterr().out)
    assert code == 2
    assert refusal["refusal"] == "SF-GRAPH-NO-INDEX"

    bundle = portal_adapter.SparkForgePortal(tmp_path)._graphs()
    assert bundle["availability"]["state"] == "no_graph"
    assert bundle["views"] == []
