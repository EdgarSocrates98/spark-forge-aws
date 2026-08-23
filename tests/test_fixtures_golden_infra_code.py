"""Golden test do corpus que cruza infraestrutura com codigo.

Duas regras do catalogo fazem uma pergunta que nenhum artefato responde
sozinho, e ate este corpus existir nenhuma fixture as exercitava disparando:

  SF-ENV-003  `--enable-observability-metrics` ligado no Terraform sem
              `GlueContext` no codigo -- o argumento fica ligado e o painel
              fica vazio.
  SF-GLUE-004 `max_retries > 0` com escrita `append` -- a retentativa
              reexecuta o job e `append` nao e idempotente.

Por isso `input/` carrega `*.tf` E `*.py` do mesmo job: e a unica forma de a
fixture representar o que a regra afirma.

AS DUAS FIXTURES DE `SF-LF` SAO TF-ONLY, e de proposito. As regras de FGAC
(`fgac_com_jar_extra`, `fgac_em_job_streaming`) correlacionam atributos do MESMO
`aws_glue_job`, entao o `.py` nao acrescentaria evidencia -- acrescentaria facts
de PySpark capazes de fazer outra regra disparar junto e contaminar o que a
fixture prova. Elas moram neste corpus, e nao em `fixtures/terraform/`, porque
este e o corpus cujo runner extrai Terraform DE ARVORE
(`extract_terraform_tree`); `fixtures/tfdiff/` extrai de um par
before/after, e um defeito de FGAC nao e uma mudanca -- e um estado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "infra_code"

REQUIRED_FIXTURES = {
    "fgac_com_jar_extra",
    "fgac_em_job_streaming",
    "observability_without_glue_context",
    "retries_with_append_write",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = list(extract_terraform_tree(input_dir, repo_root=input_dir))
    facts.extend(extract_tree(input_dir, repo_root=input_dir))
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


class TestAdversarial:
    def test_observability_argument_without_glue_context_fires(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "observability_without_glue_context")
        assert [f.rule_id for f in findings] == ["SF-ENV-003"]
        assert not [f for f in facts if f.kind == "pyspark.glue_context_init"]

    def test_the_same_argument_with_glue_context_does_not_fire(self):
        """A metade negativa, e ela mora na OUTRA fixture: `retries_with_append_write`
        inicializa `GlueContext`. Sem esse par, uma regra que ignorasse o codigo
        e disparasse so pelo argumento do Terraform passaria igual."""
        _, facts, findings, _ = run_fixture(FIXTURES / "retries_with_append_write")
        assert [f for f in facts if f.kind == "pyspark.glue_context_init"]
        assert "SF-ENV-003" not in {f.rule_id for f in findings}

    def test_retries_with_append_write_fires(self):
        """`max_retries` sozinho nao e achado, e `append` sozinho tambem nao.
        A combinacao e que duplica dado, em silencio, com o job marcado como
        sucesso na segunda tentativa."""
        _, facts, findings, _ = run_fixture(FIXTURES / "retries_with_append_write")
        assert [f.rule_id for f in findings] == ["SF-GLUE-004"]
        write = next(f for f in facts if f.kind == "pyspark.write")
        assert write.attrs["mode"] == "append"

    def test_zero_retries_does_not_fire(self):
        """A outra fixture tem `max_retries = 0` e escrita `overwrite`: nenhuma
        das duas metades de SF-GLUE-004 esta presente."""
        _, _, findings, _ = run_fixture(FIXTURES / "observability_without_glue_context")
        assert "SF-GLUE-004" not in {f.rule_id for f in findings}

    def test_each_fixture_fires_exactly_one_rule(self):
        """Corpus de correlacao e o mais facil de contaminar: um atributo a mais
        no Terraform e a fixture passa a provar duas coisas ao mesmo tempo, e
        nenhuma delas com clareza."""
        for directory in fixture_dirs():
            _, _, findings, _ = run_fixture(directory)
            assert len(findings) == 1, (directory.name, [f.rule_id for f in findings])
