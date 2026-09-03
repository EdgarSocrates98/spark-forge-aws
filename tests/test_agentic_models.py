"""Testes das entidades agênticas de primeira classe.

Cobre:
- id determinístico (content-addressed)
- validação em __post_init__
- serialização to_dict
- invariantes do contrato (evidence obrigatória, rollback obrigatório, etc.)
"""
from __future__ import annotations

import pytest

from sparkforge.agentic.models import (
    Claim,
    ClaimType,
    Contradiction,
    Decision,
    Evidence,
    EvidenceAuthority,
    Experiment,
    ExperimentStatus,
    Hypothesis,
    HypothesisStatus,
    Objection,
    Rebuttal,
    Unknown,
    UnknownStatus,
)


class TestClaim:
    def test_id_deterministic(self):
        c1 = Claim(
            claimant="sf-iceberg-specialist",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files cause read amplification",
        )
        c2 = Claim(
            claimant="sf-iceberg-specialist",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files cause read amplification",
        )
        assert c1.id == c2.id
        assert c1.id.startswith("claim_")

    def test_id_differs_on_statement(self):
        c1 = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="A",
        )
        c2 = Claim(
            claimant="agent",
            claim_type=ClaimType.OBSERVATION,
            statement="B",
        )
        assert c1.id != c2.id

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement vazio"):
            Claim(
                claimant="agent",
                claim_type=ClaimType.OBSERVATION,
                statement="",
            )

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            Claim(
                claimant="agent",
                claim_type=ClaimType.OBSERVATION,
                statement="test",
                confidence="very_high",
            )

    def test_to_dict_roundtrip(self):
        c = Claim(
            claimant="sf-spark-specialist",
            claim_type=ClaimType.INFERENCE,
            statement="Shuffle is the bottleneck",
            evidence_refs=["f_abc123", "f_def456"],
            assumptions=["partition count is stable"],
            confidence="medium",
        )
        d = c.to_dict()
        assert d["claimant"] == "sf-spark-specialist"
        assert d["claim_type"] == "inference"
        assert d["confidence"] == "medium"
        assert d["evidence_refs"] == ["f_abc123", "f_def456"]
        assert d["id"] == c.id


class TestEvidence:
    def test_id_deterministic(self):
        e1 = Evidence(
            source="https://iceberg.apache.org/docs/latest/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
        )
        e2 = Evidence(
            source="https://iceberg.apache.org/docs/latest/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
        )
        assert e1.id == e2.id
        assert e1.id.startswith("ev_")

    def test_empty_source_raises(self):
        with pytest.raises(ValueError, match="source vazio"):
            Evidence(source="", authority=EvidenceAuthority.T1_OFFICIAL_DOCS)

    def test_t5_llm_not_sufficient_alone(self):
        e = Evidence(
            source="gpt-4 says so",
            authority=EvidenceAuthority.T5_LLM_KNOWLEDGE,
        )
        assert not e.is_sufficient_alone

    def test_t1_official_sufficient_alone(self):
        e = Evidence(
            source="apache/spark docs",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
        )
        assert e.is_sufficient_alone

    def test_t6_conjecture_not_sufficient(self):
        e = Evidence(
            source="i think so",
            authority=EvidenceAuthority.T6_CONJECTURE,
        )
        assert not e.is_sufficient_alone


class TestHypothesis:
    def test_id_deterministic(self):
        h1 = Hypothesis(statement="OOM caused by broadcast join", proposed_by="agent")
        h2 = Hypothesis(statement="OOM caused by broadcast join", proposed_by="agent")
        assert h1.id == h2.id
        assert h1.id.startswith("hyp_")

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement vazio"):
            Hypothesis(statement="")

    def test_default_status_open(self):
        h = Hypothesis(statement="test hypothesis")
        assert h.status == HypothesisStatus.OPEN

    def test_to_dict(self):
        h = Hypothesis(
            statement="Small files cause read amplification",
            supporting_evidence=["ev_abc1"],
            contradicting_evidence=["ev_def2"],
            expected_outcome="Compaction reduces read latency",
            failure_modes=["metadata cache masks the effect"],
            confidence="medium",
            falsification_method="Run compaction and measure read latency",
            proposed_by="sf-iceberg-specialist",
        )
        d = h.to_dict()
        assert d["status"] == "open"
        assert d["confidence"] == "medium"
        assert d["proposed_by"] == "sf-iceberg-specialist"


class TestExperiment:
    def test_id_deterministic(self):
        e1 = Experiment(
            hypothesis_id="hyp_abc1",
            variable="spark.sql.shuffle.partitions",
            baseline="200",
        )
        e2 = Experiment(
            hypothesis_id="hyp_abc1",
            variable="spark.sql.shuffle.partitions",
            baseline="200",
        )
        assert e1.id == e2.id
        assert e1.id.startswith("exp_")

    def test_empty_variable_raises(self):
        with pytest.raises(ValueError, match="variable vazio"):
            Experiment(hypothesis_id="hyp_1", variable="", baseline="x")

    def test_empty_hypothesis_id_raises(self):
        with pytest.raises(ValueError, match="hypothesis_id vazio"):
            Experiment(hypothesis_id="", variable="x", baseline="y")

    def test_default_status_proposed(self):
        e = Experiment(hypothesis_id="hyp_1", variable="x", baseline="y")
        assert e.status == ExperimentStatus.PROPOSED


class TestDecision:
    def test_id_deterministic(self):
        d1 = Decision(
            problem="Reduce shuffle spill",
            options=["increase partitions", "broadcast join"],
            selected_option="broadcast join",
            rollback="revert to 200 partitions",
            decided_by="sf-spark-specialist",
        )
        d2 = Decision(
            problem="Reduce shuffle spill",
            options=["increase partitions", "broadcast join"],
            selected_option="broadcast join",
            rollback="revert to 200 partitions",
            decided_by="sf-spark-specialist",
        )
        assert d1.id == d2.id
        assert d1.id.startswith("dec_")

    def test_empty_options_raises(self):
        with pytest.raises(ValueError, match="options vazio"):
            Decision(
                problem="x",
                options=[],
                selected_option="y",
                rollback="z",
            )

    def test_selected_not_in_options_raises(self):
        with pytest.raises(ValueError, match="selected_option"):
            Decision(
                problem="x",
                options=["a", "b"],
                selected_option="c",
                rollback="z",
            )

    def test_empty_rollback_raises(self):
        with pytest.raises(ValueError, match="rollback"):
            Decision(
                problem="x",
                options=["a"],
                selected_option="a",
                rollback="",
            )

    def test_irreversible_rollback_allowed(self):
        """Decisões irreversíveis declara 'irreversible: <motivo>'."""
        d = Decision(
            problem="Drop legacy table",
            options=["drop", "keep"],
            selected_option="drop",
            rollback="irreversible: data loss after drop",
        )
        assert d.rollback.startswith("irreversible:")

    def test_to_dict(self):
        d = Decision(
            problem="Reduce shuffle spill",
            options=["increase partitions", "broadcast join"],
            selected_option="broadcast join",
            rejected_options=["increase partitions"],
            evidence_refs=["f_abc", "ev_def"],
            risks=["OOM if broadcast threshold exceeded"],
            assumptions=["table fits in broadcast threshold"],
            confidence="medium",
            validation="Run funcval compare before and after",
            rollback="revert to 200 partitions",
            falsification_condition="If spill does not decrease, revert",
            decided_by="sf-spark-specialist",
        )
        d_dict = d.to_dict()
        assert d_dict["selected_option"] == "broadcast join"
        assert d_dict["rejected_options"] == ["increase partitions"]
        assert "irreversible" not in d_dict["rollback"]


class TestUnknown:
    def test_id_deterministic(self):
        u1 = Unknown(question="What is the exact partition count?")
        u2 = Unknown(question="What is the exact partition count?")
        assert u1.id == u2.id
        assert u1.id.startswith("unk_")

    def test_empty_question_raises(self):
        with pytest.raises(ValueError, match="question vazio"):
            Unknown(question="")

    def test_default_status_open(self):
        u = Unknown(question="test")
        assert u.status == UnknownStatus.OPEN

    def test_blocking_unknown(self):
        u = Unknown(
            question="Is Iceberg v2 in use?",
            impact="Compaction strategy depends on format version",
            blocking=True,
            evidence_needed=["analyze iceberg metadata"],
        )
        assert u.blocking
        assert u.evidence_needed == ["analyze iceberg metadata"]


class TestContradiction:
    def test_id_deterministic(self):
        c1 = Contradiction(
            claim_a="claim_abc",
            claim_b="claim_def",
            description="One says OOM, other says CPU bound",
        )
        c2 = Contradiction(
            claim_a="claim_def",
            claim_b="claim_abc",
            description="One says OOM, other says CPU bound",
        )
        # Ordem canônica: id independente da ordem de entrada
        assert c1.id == c2.id
        assert c1.id.startswith("ctr_")

    def test_same_claim_raises(self):
        with pytest.raises(ValueError, match="claim_a == claim_b"):
            Contradiction(
                claim_a="claim_x",
                claim_b="claim_x",
                description="self-contradiction",
            )

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description vazio"):
            Contradiction(claim_a="a", claim_b="b", description="")


class TestObjection:
    def test_id_deterministic(self):
        o1 = Objection(
            target_claim="claim_abc",
            objector="sf-iceberg-specialist",
            statement="Evidence is from v3, we run v4",
        )
        o2 = Objection(
            target_claim="claim_abc",
            objector="sf-iceberg-specialist",
            statement="Evidence is from v3, we run v4",
        )
        assert o1.id == o2.id
        assert o1.id.startswith("obj_")

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement vazio"):
            Objection(
                target_claim="claim_x",
                objector="agent",
                statement="",
            )


class TestRebuttal:
    def test_id_deterministic(self):
        r1 = Rebuttal(
            target_objection="obj_abc",
            rebuttal_by="sf-spark-specialist",
            statement="v4 has the same behavior, confirmed by release notes",
        )
        r2 = Rebuttal(
            target_objection="obj_abc",
            rebuttal_by="sf-spark-specialist",
            statement="v4 has the same behavior, confirmed by release notes",
        )
        assert r1.id == r2.id
        assert r1.id.startswith("reb_")

    def test_empty_statement_raises(self):
        with pytest.raises(ValueError, match="statement vazio"):
            Rebuttal(
                target_objection="obj_x",
                rebuttal_by="agent",
                statement="",
            )
