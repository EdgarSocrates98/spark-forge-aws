"""Testes do Shared Blackboard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.agentic.blackboard import (
    append_claim,
    append_contradiction,
    append_decision,
    append_evidence,
    append_experiment,
    append_hypothesis,
    append_objection,
    append_rebuttal,
    append_unknown,
    blackboard_path,
    get_entity_by_id,
    init_blackboard,
    read_claims,
    read_decisions,
    read_evidence,
    read_hypotheses,
    read_unknowns,
    summarize,
)
from sparkforge.agentic.models import (
    Claim,
    ClaimType,
    Contradiction,
    Decision,
    Evidence,
    EvidenceAuthority,
    Experiment,
    Hypothesis,
    Objection,
    Rebuttal,
    Unknown,
    UnknownStatus,
)


@pytest.fixture
def bb_root(tmp_path: Path) -> Path:
    init_blackboard(tmp_path)
    return tmp_path


class TestInitBlackboard:
    def test_creates_directory(self, tmp_path: Path):
        p = init_blackboard(tmp_path)
        assert p.exists()
        assert p.is_dir()
        assert p.name == "blackboard"

    def test_idempotent(self, tmp_path: Path):
        init_blackboard(tmp_path)
        init_blackboard(tmp_path)  # não erro
        assert blackboard_path(tmp_path).exists()


class TestAppendClaim:
    def test_append_and_read(self, bb_root: Path):
        c = Claim(
            claimant="sf-iceberg-specialist",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files cause read amplification",
        )
        append_claim(c, bb_root)
        records = read_claims(bb_root)
        assert len(records) == 1
        assert records[0]["id"] == c.id
        assert records[0]["statement"] == "Small files cause read amplification"

    def test_duplicate_raises(self, bb_root: Path):
        c = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="test",
        )
        append_claim(c, bb_root)
        with pytest.raises(ValueError, match="já existe"):
            append_claim(c, bb_root)


class TestAppendEvidence:
    def test_append_and_read(self, bb_root: Path):
        e = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
        )
        append_evidence(e, bb_root)
        records = read_evidence(bb_root)
        assert len(records) == 1
        assert records[0]["authority"] == "T1"


class TestAppendHypothesis:
    def test_append_and_read(self, bb_root: Path):
        h = Hypothesis(statement="OOM caused by broadcast join")
        append_hypothesis(h, bb_root)
        records = read_hypotheses(bb_root)
        assert len(records) == 1
        assert records[0]["status"] == "open"


class TestAppendDecision:
    def test_append_and_read(self, bb_root: Path):
        d = Decision(
            problem="Reduce shuffle spill",
            options=["increase partitions", "broadcast join"],
            selected_option="broadcast join",
            rollback="revert to 200 partitions",
        )
        append_decision(d, bb_root)
        records = read_decisions(bb_root)
        assert len(records) == 1
        assert records[0]["selected_option"] == "broadcast join"


class TestAppendUnknown:
    def test_append_and_read(self, bb_root: Path):
        u = Unknown(question="What is the partition count?")
        append_unknown(u, bb_root)
        records = read_unknowns(bb_root)
        assert len(records) == 1
        assert records[0]["status"] == "open"


class TestAppendObjectionRebuttal:
    def test_objection_and_rebuttal(self, bb_root: Path):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.INFERENCE,
            statement="Shuffle is the bottleneck",
        )
        append_claim(c, bb_root)

        o = Objection(
            target_claim=c.id,
            objector="agent_b",
            statement="Evidence is from v3, we run v4",
        )
        append_objection(o, bb_root)

        r = Rebuttal(
            target_objection=o.id,
            rebuttal_by="agent_a",
            statement="v4 has the same behavior",
        )
        append_rebuttal(r, bb_root)


class TestAppendContradiction:
    def test_append_and_read(self, bb_root: Path):
        ctr = Contradiction(
            claim_a="claim_abc",
            claim_b="claim_def",
            description="One says OOM, other says CPU",
        )
        append_contradiction(ctr, bb_root)


class TestAppendExperiment:
    def test_append_and_read(self, bb_root: Path):
        exp = Experiment(
            hypothesis_id="hyp_1",
            variable="spark.sql.shuffle.partitions",
            baseline="200",
        )
        append_experiment(exp, bb_root)


class TestSummarize:
    def test_empty_blackboard(self, bb_root: Path):
        s = summarize(bb_root)
        assert s.claims == 0
        assert s.evidence == 0
        assert s.decisions == 0

    def test_with_data(self, bb_root: Path):
        c = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="test",
        )
        append_claim(c, bb_root)

        u = Unknown(question="unknown 1")
        append_unknown(u, bb_root)

        u2 = Unknown(question="unknown 2", status=UnknownStatus.OPEN)
        append_unknown(u2, bb_root)

        s = summarize(bb_root)
        assert s.claims == 1
        assert s.unknowns == 2
        assert s.open_unknowns == 2


class TestGetEntityById:
    def test_found(self, bb_root: Path):
        c = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="find me",
        )
        append_claim(c, bb_root)
        found = get_entity_by_id(c.id, bb_root)
        assert found is not None
        assert found["statement"] == "find me"

    def test_not_found(self, bb_root: Path):
        found = get_entity_by_id("nonexistent", bb_root)
        assert found is None


class TestJsonlFormat:
    def test_file_is_jsonl(self, bb_root: Path):
        c = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="test jsonl",
        )
        path = append_claim(c, bb_root)
        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["id"] == c.id
