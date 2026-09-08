"""Testes de `claims_from_findings` -- finding julgado vira Claim, fact vira Evidence.

Duas perguntas separadas, e a separacao e o ponto desta camada:

- o `authority` da evidencia gradua a FONTE que sustenta o limiar da regra;
- o `measurement_ref` nomeia a MEDIDA que casou com o `when` daquela regra.

Nao ha tier para medida do artefato do cliente e nao vamos inventar um, entao
os dois campos saem lado a lado e nunca fundidos.

O `confidence` NAO vem do score de `assess_claim`: o `CLAUDE.md` declara que os
pesos daquele score (40/30/20/10) sao convencao e que nenhum experimento os
calibrou. Ele vem de tabela conferivel campo a campo, e e ela que estes testes
cobrem ramo a ramo.

Entrada preferida e fixture REAL -- `fixtures/waste/folga_medida_sem_skew/` ja
tem `facts.json` e `findings.json` ancorados, com `action` e `sources`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sparkforge.agentic.executor.authority import load_authority_map
from sparkforge.agentic.executor.claims import claims_from_findings, confidence_for
from sparkforge.agentic.models import ClaimType, EvidenceAuthority

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "waste" / "folga_medida_sem_skew" / "expected"

T1 = EvidenceAuthority.T1_OFFICIAL_DOCS
T2 = EvidenceAuthority.T2_SOURCE_CODE
T3 = EvidenceAuthority.T3_REPRODUCIBLE_BENCHMARK
T4 = EvidenceAuthority.T4_RECOGNIZED_AUTHORITY
T6 = EvidenceAuthority.T6_CONJECTURE


def _carrega(nome: str) -> list[dict[str, Any]]:
    documento = json.loads((FIXTURE / nome).read_text(encoding="utf-8"))
    if isinstance(documento, list):
        return documento
    return documento.get(nome.replace(".json", ""), [])


@pytest.fixture(scope="module")
def mapa() -> dict[str, object]:
    return load_authority_map()


@pytest.fixture(scope="module")
def facts_reais() -> list[dict[str, Any]]:
    return _carrega("facts.json")


@pytest.fixture(scope="module")
def findings_reais() -> list[dict[str, Any]]:
    return _carrega("findings.json")


class TestConfidenceFor:
    """A tabela, ramo a ramo. Cada nome diz a condicao que ele fixa."""

    def test_t1_vigente_no_escopo_com_medidas_presentes_e_high(self):
        assert confidence_for(T1, dentro_do_escopo=True, medidas_presentes=True) == "high"

    def test_t2_vigente_no_escopo_com_medidas_presentes_e_high(self):
        assert confidence_for(T2, dentro_do_escopo=True, medidas_presentes=True) == "high"

    def test_fonte_com_autoridade_fora_do_escopo_de_versao_e_medium(self):
        """Uma T1 fora da versao alvo tem autoridade e nao sustenta a claim."""
        assert confidence_for(T1, dentro_do_escopo=False, medidas_presentes=True) == "medium"

    def test_fonte_t4_e_low_mesmo_no_escopo_e_com_medidas(self):
        assert confidence_for(T4, dentro_do_escopo=True, medidas_presentes=True) == "low"

    def test_medida_exigida_ausente_e_low_mesmo_com_t1_no_escopo(self):
        assert confidence_for(T1, dentro_do_escopo=True, medidas_presentes=False) == "low"

    def test_t6_conjectura_e_low(self):
        assert confidence_for(T6, dentro_do_escopo=True, medidas_presentes=True) == "low"

    def test_t3_benchmark_e_medium_por_nao_cair_em_nenhum_dos_dois_lados(self):
        """T3 nao e "T1/T2 vigente" e nao e "T4 ou pior" -- a tabela nao o nomeia.

        Ele fica no unico degrau que sobra, e a escolha esta declarada em vez de
        cair por acidente num `else` sem razao escrita.
        """
        assert confidence_for(T3, dentro_do_escopo=True, medidas_presentes=True) == "medium"


class TestClaimsDaFixtureReal:
    def test_um_finding_vira_uma_claim_com_claimant_do_rule_id(
        self, findings_reais, facts_reais, mapa
    ):
        claims, _ = claims_from_findings(
            findings_reais, facts_reais, mapa, {"glue": "5.0", "spark": "3.5.4"}
        )
        assert len(claims) == len(findings_reais) == 1
        assert claims[0].claimant == "SF-WASTE-001"
        assert claims[0].claim_type is ClaimType.INFERENCE

    def test_claim_ancora_nos_fact_ids_do_finding_sem_repetir(
        self, findings_reais, facts_reais, mapa
    ):
        """O finding real cita `f_681614` quatro vezes -- uma por medida."""
        claims, _ = claims_from_findings(findings_reais, facts_reais, mapa, {})
        assert claims[0].evidence_refs == ["f_681614"]

    def test_evidence_liga_fonte_e_medida(self, findings_reais, facts_reais, mapa):
        """Host -> tier, fact -> `measurement_ref`, claim <- `supports`."""
        claims, evidences = claims_from_findings(findings_reais, facts_reais, mapa, {})
        # Duas entradas em `sources`, e so uma tem `url`.
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev.source.startswith("https://docs.aws.amazon.com/")
        assert ev.authority is T1
        assert ev.measurement_ref == "f_681614"
        assert ev.supports == [claims[0].id]

    def test_source_sem_url_nao_vira_evidence(self, findings_reais, facts_reais, mapa):
        """A entrada `origin: field-heuristic` nao tem host para graduar.

        Fabricar uma evidencia com o `default` do mapa promoveria heuristica de
        campo a autoridade reconhecida sem que ninguem tivesse declarado isso.
        """
        _, evidences = claims_from_findings(findings_reais, facts_reais, mapa, {})
        assert all(e.source for e in evidences)
        assert len(evidences) == 1

    def test_fixture_real_com_t1_e_fact_presente_sai_high(self, findings_reais, facts_reais, mapa):
        claims, _ = claims_from_findings(findings_reais, facts_reais, mapa, {"glue": "5.0"})
        assert claims[0].confidence == "high"


def _finding(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "rule_id": "SF-TESTE-001",
        "title": "Titulo do achado",
        "subject": {"type": "job_run", "symbol": "etl_teste"},
        "evidence": ["f_aaa"],
        "runtime_scope": {},
        "sources": [{"url": "https://docs.aws.amazon.com/glue/latest/dg/x.html"}],
    }
    base.update(over)
    return base


FACTS_PADRAO = [{"id": "f_aaa"}, {"id": "f_bbb"}]


class TestRamosDeConfidenceNoPacote:
    def test_fonte_fora_do_escopo_de_versao_do_case_sai_medium(self, mapa):
        claims, _ = claims_from_findings(
            [_finding(runtime_scope={"glue": ["3.0"]})],
            FACTS_PADRAO,
            mapa,
            {"glue": "5.0"},
        )
        assert claims[0].confidence == "medium"

    def test_fonte_t4_sai_low(self, mapa):
        """`aws.amazon.com` NAO e `docs.aws.amazon.com`: blog, nao referencia."""
        claims, evidences = claims_from_findings(
            [_finding(sources=[{"url": "https://aws.amazon.com/blogs/big-data/x/"}])],
            FACTS_PADRAO,
            mapa,
            {},
        )
        assert evidences[0].authority is T4
        assert claims[0].confidence == "low"

    def test_finding_que_cita_fact_ausente_do_case_sai_low(self, mapa):
        """A claim nao esta ancorada: o finding cita medida que nao veio."""
        claims, _ = claims_from_findings(
            [_finding(evidence=["f_aaa", "f_que_nao_veio"])],
            FACTS_PADRAO,
            mapa,
            {},
        )
        assert claims[0].confidence == "low"

    def test_finding_sem_sources_usa_t6_e_sai_low(self, mapa):
        claims, evidences = claims_from_findings([_finding(sources=[])], FACTS_PADRAO, mapa, {})
        assert evidences == []
        assert claims[0].confidence == "low"

    def test_melhor_tier_entre_sources_manda(self, mapa):
        """Menor numeral vence: T1 ao lado de T4 gradua o finding como T1."""
        claims, _ = claims_from_findings(
            [
                _finding(
                    sources=[
                        {"url": "https://aws.amazon.com/blogs/big-data/x/"},
                        {"url": "https://spark.apache.org/docs/latest/tuning.html"},
                    ]
                )
            ],
            FACTS_PADRAO,
            mapa,
            {},
        )
        assert claims[0].confidence == "high"


class TestIdentidadeDaClaim:
    def test_mesmo_rule_id_com_evidencias_diferentes_gera_ids_diferentes(self, mapa):
        """`Claim.id` cobre `evidence_refs` desde a auditoria de 2026-09-03.

        Antes disso a mesma afirmacao ancorada noutra medida colidia com a
        anterior e o blackboard a recusava como duplicata -- nao havia como
        registrar revisao nenhuma.
        """
        claims, _ = claims_from_findings(
            [_finding(evidence=["f_aaa"]), _finding(evidence=["f_bbb"])],
            FACTS_PADRAO,
            mapa,
            {},
        )
        assert len(claims) == 2
        assert claims[0].claimant == claims[1].claimant == "SF-TESTE-001"
        assert claims[0].id != claims[1].id

    def test_mesma_fonte_com_medidas_diferentes_gera_evidencias_diferentes(self, mapa):
        _, evidences = claims_from_findings(
            [_finding(evidence=["f_aaa"]), _finding(evidence=["f_bbb"])],
            FACTS_PADRAO,
            mapa,
            {},
        )
        assert len(evidences) == 2
        assert evidences[0].source == evidences[1].source
        assert evidences[0].authority is evidences[1].authority
        assert evidences[0].measurement_ref != evidences[1].measurement_ref
        assert evidences[0].id != evidences[1].id

    def test_created_at_e_injetado_pelo_caller(self, mapa):
        claims, _ = claims_from_findings(
            [_finding()], FACTS_PADRAO, mapa, {}, created_at="2026-09-08T00:00:00Z"
        )
        assert claims[0].created_at == "2026-09-08T00:00:00Z"


class TestBordas:
    def test_lista_vazia_devolve_dois_vazios(self, mapa):
        assert claims_from_findings([], FACTS_PADRAO, mapa, {}) == ([], [])

    def test_finding_sem_evidence_nao_tem_measurement_ref_e_sai_low(self, mapa):
        """Regra que nao declarou fact ancora nao vira claim de alta confianca."""
        claims, evidences = claims_from_findings([_finding(evidence=[])], FACTS_PADRAO, mapa, {})
        assert claims[0].evidence_refs == []
        assert claims[0].confidence == "low"
        assert evidences[0].measurement_ref == ""

    def test_finding_sem_title_usa_o_rule_id_como_statement(self, mapa):
        """`Claim` recusa statement vazio -- e a recusa nao pode derrubar o pacote."""
        claims, _ = claims_from_findings([_finding(title="")], FACTS_PADRAO, mapa, {})
        assert "SF-TESTE-001" in claims[0].statement
