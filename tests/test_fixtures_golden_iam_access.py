"""Golden do corpus de DECISAO de IAM.

O que este corpus mede: as QUATRO respostas de `EvalDecision` num artefato so, e
que a CAMADA que decidiu sobrevive ate o fact. Colapsa-las num booleano
`autorizado` faria "adicione a permissao" virar o conselho unico -- e ele e
errado em tres dos quatro casos.

Desde 2026-09-09 o corpus tambem prende o JULGAMENTO: `SF-IAM-001` a
`SF-IAM-003` consomem `iam.access_decision`, uma por camada, e a fixture dispara
as TRES ao mesmo tempo -- de proposito, porque o ponto dela e que um role so
pode ser negado por tres motivos que exigem consertos diferentes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.iam_access import EMITTED_KINDS, extract_iam_access_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "iam_access"

REQUIRED_FIXTURES = {"escrita_negada_pelo_boundary"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    entrada = directory / "input"
    return extract_iam_access_tree(entrada, repo_root=entrada)


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


class TestTresConsertosNoMesmoRole:
    """O ponto do corpus: tres negacoes, tres camadas, tres consertos."""

    def _decisoes(self):
        _, facts, _, _ = run_fixture(FIXTURES / "escrita_negada_pelo_boundary")
        return {f.attrs["action"]: f for f in facts if f.kind == "iam.access_decision"}

    def test_a_leitura_atravessa(self):
        d = self._decisoes()
        assert d["glue:GetTable"].attrs["allowed"] is True
        assert d["lakeformation:GetDataAccess"].attrs["allowed"] is True

    def test_a_escrita_no_s3_e_negada_pelo_BOUNDARY(self):
        """Alargar a policy do role nao muda nada -- o boundary recorta o que
        ela concede, e ele nao aparece no documento dela."""
        d = self._decisoes()["s3:PutObject"]
        assert d.attrs["allowed"] is False
        assert d.attrs["decision"] == "implicitDeny"
        assert d.attrs["denied_by"] == "permissions_boundary"

    def test_o_kms_e_negado_pela_SCP(self):
        """A negacao decide acima do role inteiro."""
        d = self._decisoes()["kms:GenerateDataKey"]
        assert d.attrs["decision"] == "explicitDeny"
        assert d.attrs["denied_by"] == "service_control_policy"

    def test_o_par_leitura_escrita_reproduz_a_classe_de_sintoma(self):
        """O job LE a tabela e falha ao ESCREVER, e a resposta nao esta na
        policy que todo mundo abre primeiro."""
        d = self._decisoes()
        lidos = [a for a, f in d.items() if f.attrs["allowed"]]
        negados = [a for a, f in d.items() if not f.attrs["allowed"]]
        assert set(lidos) == {"glue:GetTable", "lakeformation:GetDataAccess"}
        assert set(negados) == {
            "s3:PutObject",
            "s3:DeleteObject",
            "kms:GenerateDataKey",
        }
        # E as TRES negacoes vem de camadas DIFERENTES -- e o ponto do corpus:
        # boundary, service control policy e `Deny` explicito, num role so.
        assert {d[a].attrs["denied_by"] for a in negados} == {
            "permissions_boundary",
            "service_control_policy",
            "explicit_deny",
        }

    def test_o_limite_de_policy_de_recurso_sai_mesmo_com_status_ok(self):
        _, facts, _, _ = run_fixture(FIXTURES / "escrita_negada_pelo_boundary")
        razoes = {f.attrs["reason"] for f in facts if f.kind == "iam.access.unresolved"}
        assert razoes == {"policy_de_recurso_nao_avaliada"}

    def test_o_deny_explicito_e_a_terceira_camada(self):
        """`explicitDeny` SEM boundary e SEM SCP: a negacao esta numa policy
        anexada ao proprio role, e acrescentar `Allow` nao vence."""
        d = self._decisoes()["s3:DeleteObject"]
        assert d.attrs["decision"] == "explicitDeny"
        assert d.attrs["denied_by"] == "explicit_deny"
        assert d.measures["matched_statements"] == 1
