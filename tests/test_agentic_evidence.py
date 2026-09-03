"""Testes do Evidence Engine."""

from __future__ import annotations

from sparkforge.agentic.evidence import (
    aggregate_strength,
    classify_source,
    detect_conflicts,
    verify_evidence,
)
from sparkforge.agentic.models import Evidence, EvidenceAuthority


class TestClassifySource:
    def test_apache_spark_docs_is_t1(self):
        assert (
            classify_source("https://spark.apache.org/docs/latest/")
            == EvidenceAuthority.T1_OFFICIAL_DOCS
        )

    def test_aws_docs_is_t1(self):
        assert (
            classify_source("https://docs.aws.amazon.com/glue/")
            == EvidenceAuthority.T1_OFFICIAL_DOCS
        )

    def test_iceberg_docs_is_t1(self):
        assert (
            classify_source("https://iceberg.apache.org/docs/latest/")
            == EvidenceAuthority.T1_OFFICIAL_DOCS
        )

    def test_release_notes_is_t2(self):
        assert (
            classify_source("https://github.com/apache/spark/releases/tag/v3.5.0")
            == EvidenceAuthority.T2_SOURCE_CODE
        )

    def test_source_code_blob_is_t2(self):
        assert (
            classify_source(
                "https://github.com/apache/spark/blob/main/core/src/main/scala/SparkContext.scala"
            )
            == EvidenceAuthority.T2_SOURCE_CODE
        )

    def test_llm_output_is_t5(self):
        assert classify_source("gpt-4 says this is correct") == EvidenceAuthority.T5_LLM_KNOWLEDGE

    def test_conjecture_is_t6(self):
        assert classify_source("i think this is the issue") == EvidenceAuthority.T6_CONJECTURE

    def test_blog_defaults_t4(self):
        assert (
            classify_source("https://medium.com/@engineer/spark-tuning")
            == EvidenceAuthority.T4_RECOGNIZED_AUTHORITY
        )


class TestVerifyEvidence:
    def test_fresh_in_scope(self):
        e = Evidence(
            source="https://spark.apache.org/docs/3.5.0/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            version="3.5.0",
            scope="spark",
        )
        v = verify_evidence(e, target_runtime={"spark": "3.5.0"}, target_version="3.5.0")
        assert v.is_fresh
        assert v.in_scope
        assert v.is_usable
        assert v.weight == 1.0

    def test_version_mismatch_not_fresh(self):
        e = Evidence(
            source="https://spark.apache.org/docs/3.3.0/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            version="3.3.0",
            scope="spark",
        )
        v = verify_evidence(e, target_runtime={"spark": "3.5.0"}, target_version="3.5.0")
        assert not v.is_fresh
        assert "version mismatch" in v.issues[0]

    def test_scope_mismatch_not_in_scope(self):
        e = Evidence(
            source="https://iceberg.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="iceberg",
        )
        v = verify_evidence(e, target_runtime={"spark": "3.5.0"})
        assert not v.in_scope

    def test_no_version_assumes_fresh(self):
        e = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
        )
        v = verify_evidence(e, target_runtime={"spark": "3.5.0"}, target_version="3.5.0")
        assert v.is_fresh  # conservador: sem version, assume fresh


class TestAggregateStrength:
    def test_empty_evidence(self):
        s = aggregate_strength([])
        assert s.evidence_count == 0
        assert not s.sufficient_for_high_confidence

    def test_t1_alone_sufficient(self):
        e = Evidence(
            source="https://spark.apache.org/docs/3.5.0/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            version="3.5.0",
            scope="spark",
        )
        s = aggregate_strength([e], target_runtime={"spark": "3.5.0"})
        assert s.has_sufficient_authority
        assert s.has_fresh_in_scope
        assert s.sufficient_for_high_confidence

    def test_t5_alone_not_sufficient(self):
        e = Evidence(
            source="gpt-4 says so",
            authority=EvidenceAuthority.T5_LLM_KNOWLEDGE,
        )
        s = aggregate_strength([e])
        assert not s.has_sufficient_authority
        assert not s.sufficient_for_high_confidence

    def test_t6_alone_not_sufficient(self):
        e = Evidence(
            source="i think so",
            authority=EvidenceAuthority.T6_CONJECTURE,
        )
        s = aggregate_strength([e])
        assert not s.has_sufficient_authority
        assert not s.sufficient_for_high_confidence

    def test_conflict_detected(self):
        e1 = Evidence(
            source="doc1",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            supports=["claim_a"],
        )
        e2 = Evidence(
            source="doc2",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            contradicts=["claim_a"],
        )
        s = aggregate_strength([e1, e2])
        assert s.conflict_detected
        assert not s.sufficient_for_high_confidence

    def test_t1_plus_t5_still_sufficient(self):
        e1 = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
        )
        e2 = Evidence(
            source="gpt-4 confirms",
            authority=EvidenceAuthority.T5_LLM_KNOWLEDGE,
        )
        s = aggregate_strength([e1, e2], target_runtime={"spark": "3.5.0"})
        assert s.has_sufficient_authority
        assert s.sufficient_for_high_confidence


class TestDetectConflicts:
    def test_no_conflict(self):
        e1 = Evidence(source="a", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=["c1"])
        e2 = Evidence(source="b", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=["c2"])
        assert detect_conflicts([e1, e2]) == []

    def test_conflict_same_claim(self):
        e1 = Evidence(source="a", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, supports=["c1"])
        e2 = Evidence(source="b", authority=EvidenceAuthority.T1_OFFICIAL_DOCS, contradicts=["c1"])
        conflicts = detect_conflicts([e1, e2])
        assert len(conflicts) == 1
        # Par ordenado canonicamente
        assert conflicts[0] == tuple(sorted([e1.id, e2.id]))


class TestAutoridadeNaoEOMesmoQueFrescor:
    """Os dois campos eram a MESMA expressao ate 2026-09-03.

    `has_sufficient_authority` olha so o tier; `has_fresh_in_scope` exige tier
    E verificacao. Quando os dois eram identicos, a docstring prometia uma
    distincao que o codigo nao tinha, e uma T1 fora de versao reportava
    "sem autoridade" em vez de "autoridade sim, vigencia nao".
    """

    def test_t1_fora_de_scope_tem_autoridade_mas_nao_esta_em_scope(self):
        e = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
        )
        s = aggregate_strength([e], target_runtime={"iceberg": "1.5"})
        assert s.has_sufficient_authority
        assert not s.has_fresh_in_scope
        assert not s.sufficient_for_high_confidence

    def test_t1_em_scope_satisfaz_os_dois(self):
        e = Evidence(
            source="https://spark.apache.org/docs/",
            authority=EvidenceAuthority.T1_OFFICIAL_DOCS,
            scope="spark",
        )
        s = aggregate_strength([e], target_runtime={"spark": "3.5"})
        assert s.has_sufficient_authority
        assert s.has_fresh_in_scope

    def test_t5_sozinha_nao_satisfaz_nenhum_dos_dois(self):
        e = Evidence(source="claude-opus disse", authority=EvidenceAuthority.T5_LLM_KNOWLEDGE)
        s = aggregate_strength([e])
        assert not s.has_sufficient_authority
        assert not s.has_fresh_in_scope
