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
        """Tres agentes, tres fontes, e cada evidencia LIGADA a sua claim.

        A ligacao (`supports`) e o que faz a fonte contar: evidencia solta na
        lista nao sustenta claim nenhuma, e ate 2026-09-03 ela contava mesmo
        assim -- era so `len({e.source}) / max(len(claims), len(evidences))`.
        """
        c_a = Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A")
        c_b = Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B")
        c_c = Claim(claimant="agent_c", claim_type=ClaimType.OBSERVATION, statement="C")
        evidences = [
            Evidence(
                source="doc1", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=[c_a.id]
            ),
            Evidence(
                source="doc2", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=[c_b.id]
            ),
            Evidence(
                source="doc3", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=[c_c.id]
            ),
        ]
        score = compute_independence_score([c_a, c_b, c_c], evidences)
        assert score == 1.0  # all unique

    def test_evidencia_nao_ligada_nao_confere_independencia(self):
        """Evidencia na lista sem `supports` nao sustenta claim nenhuma."""
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B"),
        ]
        soltas = [
            Evidence(source="doc1", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
            Evidence(source="doc2", authority=EvidenceAuthority.T1_OFFICIAL_DOCS),
        ]
        assert compute_independence_score(claims, soltas) == 0.0

    def test_mesma_fonte_para_dois_agentes_nao_e_independente(self):
        """O caso que a media escondia: 1.0 de agente com 0.5 de fonte dava 0.75."""
        c_a = Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A")
        c_b = Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B")
        unica = [
            Evidence(
                source="https://docs.aws.amazon.com/glue/x",
                authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
                supports=[c_a.id, c_b.id],
            )
        ]
        score = compute_independence_score([c_a, c_b], unica)
        assert score == 0.5  # min(claimant=1.0, fonte=1/2)

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
        c_a = Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A")
        c_b = Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B")
        evidences = [
            Evidence(
                source="doc1", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=[c_a.id]
            ),
            Evidence(
                source="doc2", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=[c_b.id]
            ),
        ]
        assert not detect_false_consensus([c_a, c_b], evidences)

    def test_dois_agentes_com_a_mesma_fonte_e_falso_consenso(self):
        """Linhagem identica dispara mesmo com agentes distintos.

        Ate 2026-09-03 este caso pontuava 0.75 e passava por independente
        sobre o limiar de 0.3 -- exatamente o "same source, same hypothesis
        lineage" que a docstring prometia detectar e nao detectava.
        """
        c_a = Claim(claimant="agent_a", claim_type=ClaimType.INFERENCE, statement="shuffle domina")
        c_b = Claim(
            claimant="agent_b", claim_type=ClaimType.INFERENCE, statement="shuffle e o gargalo"
        )
        unica = [
            Evidence(
                source="https://spark.apache.org/docs/latest/tuning.html",
                authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
                supports=[c_a.id, c_b.id],
            )
        ]
        assert detect_false_consensus([c_a, c_b], unica)

    def test_claims_sem_evidencia_nao_sao_conluio_por_ausencia(self):
        """Ausencia de fonte nao e fonte compartilhada.

        O sinal de linhagem ignora claim sem evidencia; quem pega esse caso e
        o score, e o `arbitrate` ja escala por score baixo.
        """
        claims = [
            Claim(claimant="agent_a", claim_type=ClaimType.OBSERVATION, statement="A"),
            Claim(claimant="agent_b", claim_type=ClaimType.OBSERVATION, statement="B"),
        ]
        # Dispara pelo score (0.0), nao pela linhagem -- e a distincao importa
        # porque o remedio de cada um e diferente: falta evidencia, nao ha conluio.
        assert detect_false_consensus(claims, [])
        assert compute_independence_score(claims, []) == 0.0

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


class TestArbitragemSemDisputa:
    """Uma claim so nao e arbitragem, e o relatorio nao pode fingir que foi."""

    def _claim_forte(self):
        c = Claim(
            claimant="agent_a",
            claim_type=ClaimType.INFERENCE,
            statement="Shuffle domina o tempo do stage",
        )
        e = Evidence(
            source="https://spark.apache.org/docs/latest/tuning.html",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c.id],
        )
        return c, e

    def test_claim_unica_forte_nao_pede_experimento_contra_si_mesma(self):
        c, e = self._claim_forte()
        r = arbitrate([c], [e], target_runtime={"spark": "3.5"})
        # Ate 2026-09-03: `loser` era a propria vencedora, a diferenca dava 0,
        # e o ramo de "scores proximos" recomendava experimento para
        # diferenciar uma claim dela mesma.
        assert r.recommendation == "accept"
        assert "loser" not in r.reasoning
        assert "sem claim rival" in r.reasoning

    def test_claim_unica_marca_disputed_false_e_loser_zero(self):
        c, e = self._claim_forte()
        r = arbitrate([c], [e], target_runtime={"spark": "3.5"})
        assert r.disputed is False
        assert r.evidence_quality_loser == 0.0

    def test_duas_claims_continuam_marcadas_como_disputa(self):
        c_a, e_a = self._claim_forte()
        c_b = Claim(
            claimant="agent_b",
            claim_type=ClaimType.INFERENCE,
            statement="CPU domina o tempo do stage",
        )
        r = arbitrate([c_a, c_b], [e_a], target_runtime={"spark": "3.5"})
        assert r.disputed is True


class TestPesoDeEvidenciaPorClaim:
    """`evidence_weight` agrega so o que suporta a claim avaliada."""

    def test_claim_sem_evidencia_nao_herda_o_peso_da_rival(self):
        c_com = Claim(
            claimant="agent_a",
            claim_type=ClaimType.INFERENCE,
            statement="Small files causam read amplification",
        )
        c_sem = Claim(
            claimant="agent_b",
            claim_type=ClaimType.INFERENCE,
            statement="Small files nao sao problema",
        )
        e = Evidence(
            source="https://iceberg.apache.org/docs/latest/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="iceberg",
            supports=[c_com.id],
        )
        a_com = assess_claim(c_com, [e], target_runtime={"iceberg": "1.5"})
        a_sem = assess_claim(c_sem, [e], target_runtime={"iceberg": "1.5"})
        # Ate 2026-09-03 as duas reportavam o mesmo `evidence_weight`, porque
        # a agregacao rodava sobre a lista inteira de evidencias.
        assert a_com.evidence_weight > 0
        assert a_sem.evidence_weight == 0.0

    def test_relatorio_distingue_evidencia_de_vencedor_e_perdedor(self):
        c_a = Claim(claimant="a", claim_type=ClaimType.INFERENCE, statement="A")
        c_b = Claim(claimant="b", claim_type=ClaimType.INFERENCE, statement="B")
        e = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
            supports=[c_a.id],
        )
        r = arbitrate([c_a, c_b], [e], target_runtime={"spark": "3.5"})
        assert r.evidence_quality_winner > r.evidence_quality_loser
