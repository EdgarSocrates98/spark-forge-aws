"""Golden do corpus de PERMISSAO do Lake Formation.

Arquivo dedicado, mesma razao dos demais `test_fixtures_golden_*.py`: o golden
guarda os facts de `sparkforge/facts/lakeformation_grants.py`, que le o artefato
de `sparkforge collect lakeformation`.

## O que este corpus mede, e o que ele NAO mede

Ele mede que a permissao vira fact **sem virar juizo** -- e desde 2026-09-09
mede tambem o juizo que ela destrava: `SF-LF-007` (a conta recusa o que o job
pede) e `SF-LF-008` (`IAM_ALLOWED_PRINCIPALS` com `ALL`, a tabela registrada que
o Lake Formation nao governa). Cada fixture dispara UMA, e o Terraform ao lado
entra sob guarda de existencia -- `SF-LF-007` correlaciona o PEDIDO do job com a
RESPOSTA da conta, e nenhum artefato sozinho tem os dois.

As tres propriedades que ele prende, e cada uma nasceu de um modo de falha real:

  * `IAM_ALLOWED_PRINCIPALS` NAO e um role. Uma regra que leia "existe `ALL`
    sobre a tabela" sem olhar o principal concluiria que a escrita esta
    autorizada para o job -- e `IAM_ALLOWED_PRINCIPALS` e justamente a ausencia
    de governanca fina.
  * As TRES chamadas do coletor falham por motivos independentes. Aqui o bloco
    de data lake settings sai `sem_permissao` e os outros dois respondem, e o
    `status` de topo continua `ok`: o corpus mede que o topo nao esconde o bloco
    que falhou.
  * `registered: true` e afirmacao com fonte. O terceiro valor do ternario --
    ninguem mediu -- e coberto por `tests/test_facts_lakeformation_grants.py`,
    que exercita os blocos um a um sem precisar de artefato em disco.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.lakeformation import build_lakeformation
from sparkforge.facts.lakeformation_grants import (
    EMITTED_KINDS,
    extract_lakeformation_tree,
)
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "lakeformation"

REQUIRED_FIXTURES = {
    "grant_de_leitura_em_local_registrado",
    # O par NEGATIVO, e ele inverte os tres eixos: grant `ALL` em vez de
    # `SELECT`, localizacao NAO registrada, e o bloco de data lake settings
    # respondendo `ok` com o passo de conta DESLIGADO.
    "conta_sem_full_table_access",
    # O par do conflito declarado (§6): FGAC ligado E localizacao registrada.
    # A fixture irma `grant_de_leitura_em_local_registrado` tem a localizacao
    # registrada e NAO tem modelo de acesso declarado -- e por isso ela
    # dispara `SF-LF-010` e esta dispara `SF-LF-009`.
    "fgac_escrevendo_em_local_registrado",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    entrada = directory / "input"
    facts = extract_lakeformation_tree(entrada, repo_root=entrada)
    # O companheiro entra sob guarda de EXISTENCIA, no molde de
    # `test_fixtures_golden_cloudwatch_logs.py`: a regra que correlaciona o
    # PEDIDO do job (as confs de Full Table Access no Terraform) com a RESPOSTA
    # da conta (o data lake settings) precisa dos dois lados, e nenhum artefato
    # sozinho os tem.
    if any(entrada.rglob("*.tf")):
        facts.extend(extract_terraform_tree(entrada, repo_root=entrada))
        facts.extend(build_lakeformation(facts))
    return facts


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
        """Os kinds do EXTRATOR desta area, e os do COMPANHEIRO quando ha um.

        A fixture que traz Terraform ao lado carrega tambem os kinds de
        `terraform.py` e de `lakeformation.py` (a derivacao), e cobra-los contra
        `EMITTED_KINDS` de `lakeformation_grants` sozinho reprovaria por um
        companheiro que a propria regra exige.
        """
        _, facts, _, _ = run_fixture(directory)
        proprios = {f.kind for f in facts if f.kind.startswith("lakeformation.grant")}
        assert proprios <= EMITTED_KINDS
        assert proprios, "a fixture precisa exercitar o extrator desta area"


class TestAsTresPropriedades:
    def test_IAM_ALLOWED_PRINCIPALS_nao_se_confunde_com_o_role(self):
        _, facts, _, _ = run_fixture(FIXTURES / "grant_de_leitura_em_local_registrado")
        grants = [f for f in facts if f.kind == "lakeformation.grant"]
        assert len(grants) == 2
        aberto = [g for g in grants if g.attrs["is_iam_allowed_principals"]]
        do_role = [g for g in grants if not g.attrs["is_iam_allowed_principals"]]
        assert len(aberto) == 1 and len(do_role) == 1
        # O `ALL` existe sobre a tabela E NAO e do role do job. Ler so a lista
        # de permissoes, sem olhar o principal, concluiria o contrario.
        assert aberto[0].attrs["has_all"] is True
        assert do_role[0].attrs["has_all"] is False
        assert do_role[0].attrs["has_select"] is True

    def test_um_bloco_que_falha_nao_apaga_os_outros_dois(self):
        _, facts, _, _ = run_fixture(FIXTURES / "grant_de_leitura_em_local_registrado")
        recusas = [f for f in facts if f.kind == "lakeformation.grants.unresolved"]
        assert [r.attrs["block"] for r in recusas] == ["data_lake_settings"]
        assert [f for f in facts if f.kind == "lakeformation.grant"]
        assert [f for f in facts if f.kind == "lakeformation.registered_location"]
        assert not [f for f in facts if f.kind == "lakeformation.data_lake_settings"]

    def test_a_sentinela_carrega_o_status_de_topo(self):
        """O topo continua `ok` porque dois dos tres blocos responderam, e a
        recusa do terceiro esta ao lado. O corpus mede que o topo nao esconde
        o bloco que falhou."""
        _, facts, _, _ = run_fixture(FIXTURES / "grant_de_leitura_em_local_registrado")
        sentinela = [f for f in facts if f.kind == "lakeformation.grants.analyzed"]
        assert len(sentinela) == 1
        assert sentinela[0].attrs["status"] == "ok"

class TestOParNegativo:
    """`conta_sem_full_table_access` inverte os tres eixos, e por isso e par."""

    def test_grant_ALL_com_grant_option_e_o_passo_de_conta_DESLIGADO(self):
        """O achado que nenhum artefato do JOB revela.

        A permissao esta completa -- `ALL` com grant option --, e a escrita sob
        Full Table Access nao acontece assim mesmo, porque
        `allow_full_table_external_data_access` esta desligado na conta. E o
        passo 1 do procedimento da AWS, e ele precede qualquer concessao.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "conta_sem_full_table_access")
        grant = next(f for f in facts if f.kind == "lakeformation.grant")
        assert grant.attrs["has_all"] is True
        assert grant.attrs["permissions_with_grant_option"] == ["ALL"]

        settings = next(f for f in facts if f.kind == "lakeformation.data_lake_settings")
        assert settings.attrs["allow_full_table_external_data_access"] is False

    def test_localizacao_NAO_registrada_e_afirmacao_com_fonte(self):
        """`False` aqui e `True` na fixture irma, e nas duas a AWS RESPONDEU.

        O terceiro valor -- ninguem mediu -- nao aparece em golden nenhum de
        proposito: ele e ausencia de fact, e `tests/test_facts_lakeformation_grants.py`
        o exercita bloco a bloco.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "conta_sem_full_table_access")
        loc = next(f for f in facts if f.kind == "lakeformation.registered_location")
        assert loc.attrs["registered"] is False
        assert loc.attrs["role_arn"] == ""

    def test_os_dois_caminhos_de_catalogo_coexistem(self):
        """Catalogo de outra conta e catalogo local nao colidem no manifesto."""
        com_catalogo, _, _, _ = run_fixture(
            FIXTURES / "grant_de_leitura_em_local_registrado"
        )
        _, facts_local, _, _ = run_fixture(FIXTURES / "conta_sem_full_table_access")
        _, facts_xacc, _, _ = run_fixture(
            FIXTURES / "grant_de_leitura_em_local_registrado"
        )
        # So os facts DESTE extrator carregam `catalog_id` no subject -- os do
        # companheiro Terraform tem a forma de `tf_resource`.
        def _catalogos(facts):
            return {
                f.subject["catalog_id"]
                for f in facts
                if f.kind.startswith("lakeformation.grant")
                or f.kind in {"lakeformation.registered_location", "lakeformation.data_lake_settings"}
            }

        assert _catalogos(facts_local) == {""}
        assert _catalogos(facts_xacc) == {"222222222222"}
        assert not {f.id for f in facts_local} & {f.id for f in facts_xacc}
