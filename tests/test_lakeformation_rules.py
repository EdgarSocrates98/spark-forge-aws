"""SF-LF -- controle de acesso fino do Lake Formation em job Glue.

As duas regras da area afirmam a mesma classe de coisa: o Terraform pede, no
MESMO `aws_glue_job`, duas coisas que a AWS declara incompativeis sob FGAC.
`SF-LF-001` e FGAC com `--extra-jars` (a AWS bloqueia o fornecimento de JAR
adicional para preservar o isolamento do system driver); `SF-LF-002` e FGAC num
job `gluestreaming` (Spark streaming esta na lista de nao suportados).

Este arquivo prova tres coisas, e a terceira e a que justifica o formato da
regra:

1.  cada regra dispara no caso positivo, no subject certo;
2.  nao dispara no par negativo -- FGAC sozinho nao e achado, e `--extra-jars`
    sozinho tambem nao;
3.  nao dispara juntando atributo de DOIS jobs diferentes do mesmo arquivo.

O terceiro e medido nos dois sentidos: alem de afirmar que a regra fica calada,
o teste REMOVE `same_subject` de uma copia do catalogo e mostra que ali ela
acusa. Sem essa segunda metade, uma regra que nunca casasse por qualquer outro
motivo passaria no teste de silencio sem provar nada.

A FORMA DO FACT E MEDIDA, NAO SUPOSTA. `TestTheShapeOfTheFactsTheRulesMatch`
fixa o `attrs.block`/`attrs.key`/`attrs.value` que o extrator produz de fato
para os tres atributos que as regras leem. O caso perigoso e `attrs.key: name`:
ele existe DUAS vezes por job -- `block: root` (o nome do job) e
`block: command` (o tipo de comando) -- e uma SF-LF-002 sem o filtro de bloco
acusaria um job chamado `gluestreaming` que roda `glueetl`.
"""
import copy

import pytest

from sparkforge.facts.terraform import extract_terraform, extract_terraform_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope
from tests.test_fixtures_golden_infra_code import FIXTURES, run_fixture

POSITIVO_JAR = FIXTURES / "fgac_com_jar_extra"
POSITIVO_STREAM = FIXTURES / "fgac_em_job_streaming"

RUNTIME_GLUE_50 = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}
RUNTIME_GLUE_40 = {"glue": "4.0", "spark": "3.3.0", "python": "3.10", "iceberg": "1.0.0"}


def _rule(rule_id: str) -> dict:
    return next(r for r in load_catalog() if r["id"] == rule_id)


def _facts(directory):
    input_dir = directory / "input"
    return list(extract_terraform_tree(input_dir, repo_root=input_dir))


# Terraform sintetico para os casos de borda que nao merecem fixture propria --
# uma fixture existe para provar o que a regra AFIRMA, e um valor vazio nao e
# uma configuracao que alguem escreve de proposito, e um acidente de template.
_TF_FGAC = """
resource "aws_glue_job" "unico" {
  glue_version = "5.0"
  command {
    name = "glueetl"
  }
  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--extra-jars"                               = "s3://artefatos/jars/x.jar"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}
"""


def _judge_source(src: str) -> set[str]:
    facts = list(extract_terraform(src, "main.tf"))
    return {f.rule_id for f in judge(facts, load_catalog(), RUNTIME_GLUE_50)}


def _sem_same_subject(rule_id: str) -> list[dict]:
    """Copia do catalogo com `same_subject` removido de UMA regra.

    E a contraprova do teste de silencio: mostra que o `when` casaria juntando
    jobs diferentes, e que e `same_subject` -- e nao a falta de facts -- que o
    impede.
    """
    catalogo = copy.deepcopy(load_catalog())
    for regra in catalogo:
        if regra["id"] == rule_id:
            regra["when"].pop("same_subject", None)
    return catalogo


class TestTheShapeOfTheFactsTheRulesMatch:
    """Se o extrator mudar a forma, as regras ficam mudas -- e falso negativo
    mudo e o defeito mais caro deste repositorio. Este teste quebra primeiro."""

    def test_the_fgac_parameter_is_a_default_argument(self):
        facts = _facts(POSITIVO_JAR)
        fgac = [
            f
            for f in facts
            if f.kind == "tf.attribute"
            and f.attrs.get("key") == "--enable-lakeformation-fine-grained-access"
        ]
        assert len(fgac) == 2
        for fact in fgac:
            assert fact.attrs["block"] == "default_arguments"
            assert fact.attrs["value"] == "true"
            assert fact.subject["type"] == "tf_resource"

    def test_extra_jars_is_a_default_argument(self):
        facts = _facts(POSITIVO_JAR)
        jars = [
            f for f in facts if f.kind == "tf.attribute" and f.attrs.get("key") == "--extra-jars"
        ]
        assert [f.attrs["block"] for f in jars] == ["default_arguments"]
        assert [f.subject["symbol"] for f in jars] == ["aws_glue_job.etl_fgac_com_jar"]

    def test_the_command_type_lives_under_key_name_in_the_command_block(self):
        """A armadilha: `attrs.key == "name"` existe nos DOIS blocos. No `root`
        e o nome do job, no `command` e o tipo de comando. Uma regra que casasse
        so por `key`/`value` acusaria um job BATCH chamado `gluestreaming`."""
        facts = _facts(POSITIVO_JAR)
        nomes = [f for f in facts if f.kind == "tf.attribute" and f.attrs.get("key") == "name"]
        blocos = {f.attrs["block"] for f in nomes}
        assert blocos == {"root", "command"}

        comandos = {f.attrs["value"] for f in nomes if f.attrs["block"] == "command"}
        assert comandos == {"glueetl", "gluestreaming"}

        raiz = {f.attrs["value"] for f in nomes if f.attrs["block"] == "root"}
        assert "gluestreaming" not in raiz


class TestTheRulesAreDeclaredTheWayTheAreaClaims:
    @pytest.mark.parametrize("rule_id", ["SF-LF-001", "SF-LF-002"])
    def test_p0_because_aws_declares_the_combination_blocked(self, rule_id):
        assert _rule(rule_id)["severity_default"] == "P0"

    @pytest.mark.parametrize("rule_id", ["SF-LF-001", "SF-LF-002"])
    def test_same_subject_is_declared(self, rule_id):
        assert _rule(rule_id)["when"]["same_subject"] is True

    @pytest.mark.parametrize("rule_id", ["SF-LF-001", "SF-LF-002"])
    def test_guarded_by_glue_5_0(self, rule_id):
        rule = _rule(rule_id)
        assert rule["runtime_scope"] == {"glue": ">=5.0"}
        assert in_scope(rule["runtime_scope"], RUNTIME_GLUE_50)
        assert not in_scope(rule["runtime_scope"], RUNTIME_GLUE_40)


class TestSFLF001ExtraJarsUnderFGAC:
    def test_fires_on_the_job_that_declares_both(self):
        _, _, findings, _ = run_fixture(POSITIVO_JAR)
        acusados = [f for f in findings if f.rule_id == "SF-LF-001"]
        assert [f.subject["symbol"] for f in acusados] == ["aws_glue_job.etl_fgac_com_jar"]

    def test_fgac_without_extra_jars_does_not_fire(self):
        """O par negativo. `etl_fgac_sem_jar` tem FGAC e nao tem JAR extra --
        e configuracao CORRETA, e acusa-la destruiria a confianca no resto do
        relatorio."""
        _, _, findings, _ = run_fixture(POSITIVO_JAR)
        acusados = {f.subject["symbol"] for f in findings if f.rule_id == "SF-LF-001"}
        assert "aws_glue_job.etl_fgac_sem_jar" not in acusados

    def test_extra_jars_without_fgac_does_not_fire(self):
        """A outra metade do par: `--extra-jars` sozinho e o normal do mundo."""
        _, _, findings, _ = run_fixture(POSITIVO_STREAM)
        assert "SF-LF-001" not in {f.rule_id for f in findings}

    def test_fgac_in_one_job_and_extra_jars_in_another_does_not_fire(self):
        """O teste de `same_subject`. Em `fgac_em_job_streaming` o primeiro job
        tem FGAC e o segundo tem `--extra-jars`: as duas condicoes do `when`
        existem no arquivo, em jobs DIFERENTES, e cada job esta correto."""
        _, _, findings, _ = run_fixture(POSITIVO_STREAM)
        assert "SF-LF-001" not in {f.rule_id for f in findings}

    def test_without_same_subject_it_would_accuse_two_correct_jobs(self):
        """A contraprova. Sem `same_subject` a regra casa cruzando os dois jobs
        -- e por isso o silencio acima e efeito do campo, nao acaso."""
        facts = _facts(POSITIVO_STREAM)
        findings = judge(facts, _sem_same_subject("SF-LF-001"), RUNTIME_GLUE_50)
        assert "SF-LF-001" in {f.rule_id for f in findings}

    def test_an_empty_extra_jars_value_does_not_fire(self):
        """`"--extra-jars" = ""` e HCL valido, produz `tf.attribute` com
        `value: ""` -- argumento declarado que nao fornece JAR nenhum. E o que
        o `expr: attrs.value != ""` da regra existe para calar; sem ele a regra
        acusaria em P0 um job que nao pede nada. O par positivo ao lado prova
        que o filtro nao cala o caso real."""
        vazio = _judge_source(_TF_FGAC.replace("s3://artefatos/jars/x.jar", ""))
        cheio = _judge_source(_TF_FGAC)
        assert "SF-LF-001" not in vazio
        assert "SF-LF-001" in cheio


class TestSFLF002FGACOnAStreamingJob:
    def test_fires_on_the_streaming_job_with_fgac(self):
        _, _, findings, _ = run_fixture(POSITIVO_STREAM)
        acusados = [f for f in findings if f.rule_id == "SF-LF-002"]
        assert [f.subject["symbol"] for f in acusados] == ["aws_glue_job.stream_fgac"]

    def test_a_streaming_job_without_fgac_does_not_fire(self):
        _, _, findings, _ = run_fixture(POSITIVO_JAR)
        assert "SF-LF-002" not in {f.rule_id for f in findings}

    def test_a_batch_job_with_fgac_does_not_fire(self):
        """`etl_fgac_com_jar` e `etl_fgac_sem_jar` tem FGAC e sao `glueetl`.
        FGAC em job batch e o uso PREVISTO da funcionalidade."""
        _, _, findings, _ = run_fixture(POSITIVO_JAR)
        acusados = {f.subject["symbol"] for f in findings if f.rule_id == "SF-LF-002"}
        assert acusados == set()

    def test_fgac_in_one_job_and_streaming_in_another_does_not_fire(self):
        """O teste de `same_subject` desta regra: em `fgac_com_jar_extra` os
        dois primeiros jobs tem FGAC e o terceiro e `gluestreaming`."""
        _, _, findings, _ = run_fixture(POSITIVO_JAR)
        assert "SF-LF-002" not in {f.rule_id for f in findings}

    def test_without_same_subject_it_would_accuse_two_correct_jobs(self):
        facts = _facts(POSITIVO_JAR)
        findings = judge(facts, _sem_same_subject("SF-LF-002"), RUNTIME_GLUE_50)
        assert "SF-LF-002" in {f.rule_id for f in findings}


class TestTheAreaIsSkippedBelowGlue5:
    @pytest.mark.parametrize("rule_id", ["SF-LF-001", "SF-LF-002"])
    def test_skipped_with_reason_on_glue_4_0(self, rule_id):
        facts = _facts(POSITIVO_JAR)
        findings, skipped = judge(facts, load_catalog(), RUNTIME_GLUE_40, return_skipped=True)
        assert rule_id not in {f.rule_id for f in findings}
        bloqueio = next(s for s in skipped if s["rule_id"] == rule_id)
        assert bloqueio["reason"] == "runtime_scope"
