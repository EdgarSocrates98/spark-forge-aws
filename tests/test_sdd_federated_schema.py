"""Federated contract conformance — adapter output vs canonical schemas.

The canonical JSON Schemas live in the-forge workspace sibling. In a
full FORJAS workspace this test validates adapter output against them;
outside the workspace it skips (schema absence is reported, not faked).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

_SCHEMA_CANDIDATES = [
    os.environ.get("FORGE_SDD_SCHEMA_DIR", ""),
    str(Path(__file__).resolve().parents[2] / "the-forge" / "docs"
        / "portable-installation" / "schemas"),
]


def _schema_dir() -> Path:
    for cand in _SCHEMA_CANDIDATES:
        p = Path(cand) if cand else Path("/nonexistent")
        if p.is_dir() and (p / "ForgeSDDGate.schema.json").is_file():
            return p
    pytest.skip("canonical schema dir not available in this workspace")
    raise AssertionError


def _load(name: str) -> dict:
    return json.loads((_schema_dir() / name).read_text(encoding="utf-8"))


def test_gate_conforms():
    from sparkforge_aws.sdd import federated
    gate = federated.to_gate("F1", "plan", {
        "ok": False,
        "refused": [{"code": "c", "feature": "F1", "path": "plan.md",
                     "field": "x", "unlock": "u"}],
        "unresolved": [{"code": "g", "feature": "F1", "path": "define.md",
                        "unlock": "u"}]})
    jsonschema.validate(gate, _load("ForgeSDDGate.schema.json"))


def test_receipt_conforms():
    from sparkforge_aws.sdd import federated
    r = federated.to_receipt("F1", "ship", "release", "owner",
                             "2026-04-05T10:00:00Z", verdict="pass",
                             outputs=["a.txt"])
    jsonschema.validate(r, _load("ForgeSDDReceipt.schema.json"))


def test_evidence_conforms(tmp_path):
    from sparkforge_aws.sdd import federated
    f = tmp_path / "e.bin"
    f.write_bytes(b"x")
    ev = federated.to_evidence(f, kind="test-run", agent="t",
                               command=["pytest"], covers=["REQ-1"])
    jsonschema.validate(ev, _load("ForgeEvidence.schema.json"))


def test_decision_tree_conforms():
    from sparkforge_aws.sdd import federated
    doc = {"decisions": [{"id": "D-1", "question": "q", "type": "human",
                          "status": "decided", "answer": "A",
                          "depends_on": [], "alternatives": [
                              {"id": "a1", "label": "A",
                               "recommendation": True,
                               "rationale": "r"}],
                          "evidence": [], "actor": "owner",
                          "impact": "medium", "reopen_condition": "c"}],
           "recorded_at": "2026-04-05T10:00:00Z",
           "recorded_by": {"agent": "t"}}
    out = federated.to_decision_tree("F1", doc)
    jsonschema.validate(out, _load("ForgeDecisionTree.schema.json"))


def test_convergence_conforms():
    from sparkforge_aws.sdd import federated
    out = federated.to_convergence("F1", {
        "ok": False, "compared": ["requirements", "tasks"],
        "divergences": [{"class": "missing", "path": "plan.md",
                         "detail": "REQ-2 uncovered"}]})
    jsonschema.validate(out, _load("ForgeConvergence.schema.json"))
