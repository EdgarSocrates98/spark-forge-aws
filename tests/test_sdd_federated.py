"""Federated SDD adapter tests — Onda 5D (sparkforge_aws)."""

from __future__ import annotations

import json

from sparkforge_aws.sdd import federated


def test_phase_map_identity():
    for phase in ("explore", "define", "design", "plan", "build_report",
                  "ship"):
        assert federated.map_phase(phase) == phase


def test_gate_from_evaluate_shape():
    native = {
        "ok": False,
        "refused": [{"code": "upstream_hash_stale", "feature": "F1",
                     "path": "design.md", "field": "upstream.sha256",
                     "unlock": "sparkforge-aws sdd stamp"}],
        "unresolved": [{"code": "criterion_unverified", "feature": "F1",
                        "path": "define.md",
                        "unlock": "run the criterion"}],
    }
    gate = federated.to_gate("F1", "plan", native)
    assert gate["schema"] == "forge/SDDGate/v1"
    assert gate["phase"] == "plan"
    assert gate["ok"] is False
    assert gate["refused"][0]["unlock"] == "sparkforge-aws sdd stamp"


def test_decision_tree_passthrough():
    doc = {"schema": "forge/DecisionTree/v1", "feature": "F1",
           "decisions": [{"id": "D-1", "question": "?", "type": "human",
                          "status": "open"}],
           "recorded_at": "2026-04-05T10:00:00Z",
           "recorded_by": {"agent": "t"}}
    out = federated.to_decision_tree("F1", doc)
    assert out["schema"] == "forge/DecisionTree/v1"
    assert out["decisions"][0]["status"] == "open"


def test_convergence_wraps_native_report():
    rep = {"ok": False, "compared": ["requirements", "tasks"],
           "divergences": [{"class": "missing", "path": "plan.md",
                            "detail": "REQ-2 uncovered"}]}
    out = federated.to_convergence("F1", rep)
    assert out["schema"] == "forge/Convergence/v1"
    assert out["ok"] is False
    assert out["divergences"][0]["class"] == "missing"


def test_federated_view_decisions(tmp_path):
    (tmp_path / "decisions.json").write_text(json.dumps({
        "decisions": [{"id": "D-1", "question": "q", "type": "human",
                       "status": "decided", "answer": "A"}]}))
    view = federated.federated_view(tmp_path, feature="F1")
    assert "forge/DecisionTree/v1" in view
    assert view["forge/DecisionTree/v1"][0]["decisions"][0]["answer"] == "A"


def test_federated_view_empty(tmp_path):
    assert federated.federated_view(tmp_path, feature="F1") == {}
