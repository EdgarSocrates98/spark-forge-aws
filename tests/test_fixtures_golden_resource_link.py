"""Golden do corpus de TOPOLOGIA de catalogo -- resource link.

O que este corpus mede: que a afirmacao da §1 de
`knowledge/glue/lakeformation-fgac.md` -- *"o resource link precisa ter o mesmo
nome do recurso na conta de origem"* -- virou FACT medido, e que a comparacao de
nome nao e a mesma nos dois tipos de link.

As quatro fixtures formam um par mais dois eixos proprios:

    link_de_tabela_com_nome_divergente   nome PROPRIO, origem resolve  -> SF-XACC-002
    link_de_tabela_intacto               nome IDENTICO, origem resolve -> nenhum achado
    link_de_banco_com_origem_que_nao_resolve
                                         nome identico (por `DatabaseName`),
                                         origem responde EntityNotFound -> SF-XACC-003
    link_que_o_coletor_nao_pode_ler      AccessDenied no link            -> nenhum achado

O par de tabela isola UM eixo -- o nome --, e e ele que prova que a regra
distingue em vez de sempre disparar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.glue_resource_link import (
    EMITTED_KINDS,
    extract_glue_resource_link_tree,
)
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "resource_link"

REQUIRED_FIXTURES = {
    "link_de_banco_com_origem_que_nao_resolve",
    "link_de_tabela_com_nome_divergente",
    "link_de_tabela_intacto",
    "link_que_o_coletor_nao_pode_ler",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    entrada = directory / "input"
    return extract_glue_resource_link_tree(entrada, repo_root=entrada)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        assert [f.to_dict() for f in _extract(directory)] == [
            f.to_dict() for f in _extract(directory)
        ]

    def test_no_kind_outside_the_declared_namespace(self, directory):
        _, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} <= EMITTED_KINDS


class TestOParQueIsolaONome:
    """Duas fixtures de tabela, um eixo de diferenca. E o ponto do corpus."""

    def _link(self, nome: str):
        _, facts, _, _ = run_fixture(FIXTURES / nome)
        return next(f for f in facts if f.kind == "glue.resource_link")

    def test_o_nome_divergente_e_medido_e_nao_inferido(self):
        link = self._link("link_de_tabela_com_nome_divergente")
        assert link.attrs["link_name"] == "dim_cliente_prod"
        assert link.attrs["source_resource_name"] == "dim_cliente"
        assert link.attrs["name_matches_source"] is False

    def test_o_nome_identico_nao_produz_achado(self):
        link = self._link("link_de_tabela_intacto")
        assert link.attrs["name_matches_source"] is True
        _, _, findings, _ = run_fixture(FIXTURES / "link_de_tabela_intacto")
        assert findings == []

    def test_os_dois_tem_a_MESMA_topologia_fora_do_nome(self):
        """Sem isto o par nao isola eixo nenhum: se as duas fixtures diferissem
        tambem no alvo, o achado poderia vir do alvo e ninguem notaria."""
        divergente = self._link("link_de_tabela_com_nome_divergente")
        intacto = self._link("link_de_tabela_intacto")
        for campo in ("is_resource_link", "target_catalog_id", "target_database",
                      "target_region", "cross_account", "link_catalog_id"):
            assert divergente.attrs[campo] == intacto.attrs[campo], campo


class TestOLinkDeBancoNaoUsaOCampoDeTabela:
    """`TargetDatabase` nao tem `Name`. Comparar contra `target_name` daria nome
    divergente em TODO link de banco correto -- e o corpus prende isso."""

    def _facts(self):
        _, facts, _, _ = run_fixture(FIXTURES / "link_de_banco_com_origem_que_nao_resolve")
        return {f.kind: f for f in facts}

    def test_o_alvo_de_banco_nao_tem_nome_e_o_nome_bate_mesmo_assim(self):
        link = self._facts()["glue.resource_link"]
        assert link.attrs["target_type"] == "database"
        assert link.attrs["target_name"] == ""
        assert link.attrs["source_resource_name"] == "curated"
        assert link.attrs["name_matches_source"] is True

    def test_a_ausencia_do_alvo_sai_AMBIGUA_e_nao_resolvida(self):
        alvo = self._facts()["glue.resource_link.target"]
        assert alvo.attrs["resolved"] is False
        assert alvo.attrs["aws_error_code"] == "EntityNotFoundException"
        # A distincao entre "nao existe" e "nao posso ver" NAO foi medida, e o
        # fact diz isso em vez de escolher um dos dois sentidos.
        assert alvo.attrs["target_absence_is_ambiguous"] is True

    def test_o_achado_nao_afirma_que_o_link_esta_pendurado(self):
        _, _, findings, _ = run_fixture(
            FIXTURES / "link_de_banco_com_origem_que_nao_resolve"
        )
        assert [f.rule_id for f in findings] == ["SF-XACC-003"]


class TestNaoConseguiNaoEnaoHa:
    """A quarta fixture, e a razao dela: um link que o coletor nao pode LER nao
    pode virar `is_resource_link: false` -- essa leitura e indistinguivel de
    "e uma tabela comum", e as duas exigem consertos opostos."""

    def _facts(self):
        _, facts, _, _ = run_fixture(FIXTURES / "link_que_o_coletor_nao_pode_ler")
        return facts

    def test_nenhuma_topologia_e_emitida(self):
        assert "glue.resource_link" not in {f.kind for f in self._facts()}

    def test_os_dois_blocos_recusam_por_razoes_diferentes(self):
        recusas = {
            f.attrs["block"]: f
            for f in self._facts()
            if f.kind == "glue.resource_link.unresolved"
        }
        assert set(recusas) == {"link", "target"}
        assert recusas["link"].attrs["reason"] == "sem_permissao"
        assert recusas["target"].attrs["reason"] == "sem_alvo_medido_no_link"
        for recusa in recusas.values():
            assert recusa.attrs["unblocked_by"]

    def test_nenhuma_regra_dispara_sem_medida(self):
        _, _, findings, _ = run_fixture(FIXTURES / "link_que_o_coletor_nao_pode_ler")
        assert findings == []
