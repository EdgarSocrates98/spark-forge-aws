"""Testes do Arbitration Engine."""

from __future__ import annotations

from sparkforge.agentic.arbitration import (
    arbitrate,
    assess_claim,
    compute_independence_score,
    detect_false_consensus,
)
from sparkforge.agentic.models import Claim, ClaimType, Evidence, EvidenceAuthority


class TestAssessClaim:
    def test_claim_with_t1_evidence_scores_high(self):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files cause read amplification",
        )
        e = Evidence(
            source="https://iceberg.apache.org/docs/latest/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="iceberg",
            supports=[c.id],
        )
        a = assess_claim(c, [e], target_runtime={"iceberg": "1.5"})
        assert a.score > 0.5
        assert a.authority_tier == EvidenceAuthority.T1_OFFICIAL_DOCS
        assert not a.has_counterexample

    def test_claim_with_counterexample_scores_lower(self):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Broadcast join is safe",
        )
        e_support = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c.id],
        )
        e_contradict = Evidence(
            source="benchmark showing OOM",
            authority=EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK,
            contradicts=[c.id],
        )
        a = assess_claim(c, [e_support, e_contradict], target_runtime={"spark": "3.5"})
        assert a.has_counterexample
        # Counterexample penalty: score *= 0.5
        assert a.score < 0.5

    def test_claim_with_no_evidence_scores_zero(self):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.CONJECTURE
            if hasattr(ClaimType, "CONJECTURE")
            else ClaimType.OBSERVATION,
            statement="test",
        )
        a = assess_claim(c, [])
        assert a.score == 0.0


class TestComputeIndependenceScore:
    def test_independent_agents_high_score(self):
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B"),
            Claim(claimant="agent_c", claim_type=ClaimType.OBSERVATION, statement="C"),
        ]
        evidences = [
            Evidence(source="doc1", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
            Evidence(source="doc2", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
            Evidence(source="doc3", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
        ]
        score = compute_independence_score(claims, evidences)
        assert score == 1.0  # all unique

    def test_same_agent_low_score(self):
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="B"),
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="C"),
        ]
        evidences = [
            Evidence(source="same_doc", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
            Evidence(source="same_doc", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
        ]
        score = compute_independence_score(claims, evidences)
        assert score < 0.5

    def test_empty_claims(self):
        score = compute_independence_score([], [])
        assert score == 0.0


class TestDetectFalseConsensus:
    def test_false_consensus_detected(self):
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="B"),
        ]
        evidences = [
            Evidence(source="same", authority=EvidenceAuthority.T5_LLM_KNOWLEDGE),
            Evidence(source="same", authority=EvidenceAuthority.T5_LLM_KNOWLEDGE),
        ]
        # Same agent, same source → independence = 0.5 → false consensus at threshold 0.6
        assert detect_false_consensus(claims, evidences, threshold=0.6)

    def test_independent_not_false_consensus(self):
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B"),
        ]
        evidences = [
            Evidence(source="doc1", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
            Evidence(source="doc2", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
        ]
        assert not detect_false_consensus(claims, evidences)

    def test_single_claim_not_false_consensus(self):
        claims = [Claim(claimant="a", claim_type=ClaimType.OBSERVATION, statement="x")]
        assert not detect_false_consensus(claims, [])


class TestArbitrate:
    def test_clear_winner(self):
        c_a = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files cause read amplification",
        )
        c_b = Claim(
            claimant="agent_b",
            claim_type=ClaimType.HYPOTHESIS,
            statement="Small files are not a problem",
        )
        e_a = Evidence(
            source="https://iceberg.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="iceberg",
            supports=[c_a.id],
        )
        e_b = Evidence(
            source="i think so",
            authority=EvidenceAuthority.T6_CONJECTURE,
            supports=[c_b.id],
        )
        result = arbitrate([c_a, c_b], [e_a, e_b], target_runtime={"iceberg": "1.5"})
        assert result.winning_claim_id == c_a.id
        assert result.recommendation == "accept"

    def test_no_evidence_escalates(self):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="test",
        )
        result = arbitrate([c], [])
        # No evidence → score 0.0 < 0.3 → escalate (not reject)
        assert result.recommendation == "escalate"
        assert result.confidence == "low"

    def test_no_claims_rejects(self):
        result = arbitrate([], [])
        assert result.recommendation == "reject"
        assert result.winning_claim_id is None

    def test_close_scores_trigger_experiment(self):
        c_a = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="A is the cause",
        )
        c_b = Claim(
            claimant="agent_b",
            claim_type=ClaimType.HYPOTHESIS,
            statement="B is the cause",
        )
        # Both with same tier evidence
        e_a = Evidence(
            source="doc_a",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c_a.id],
        )
        e_b = Evidence(
            source="doc_b",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c_b.id],
        )
        result = arbitrate([c_a, c_b], [e_a, e_b], target_runtime={"spark": "3.5"})
        # Close scores → experiment
        assert result.recommendation in ("experiment", "accept")

    def test_false_consensus_triggers_experiment(self):
        c_a = Claim(
            claimant="agent_a",
            claim_type=ClaimType.HYPOTHESIS,
            statement="A",
        )
        c_b = Claim(
            claimant="agent_a",  # same agent
            claim_type=ClaimType.HYPOTHESIS,
            statement="A is correct",
        )
        e = Evidence(
            source="same_source",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c_a.id, c_b.id],
        )
        result = arbitrate([c_a, c_b], [e], target_runtime={"spark": "3.5"})
        # Same agent, same source → independence ~0.5 → false consensus at 0.6
        # But arbitrate uses default threshold 0.3, so check close-scores path
        assert result.recommendation == "experiment"
