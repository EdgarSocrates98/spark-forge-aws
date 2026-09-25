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

from sparkforge.facts.lakeformation import build_lakeformation
from sparkforge.facts.lakeformation_missing_grant import build_missing_grant
from sparkforge.facts.terraform import extract_terraform, extract_terraform_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog
from sparkforge.rules.version_scope import in_scope
from tests.test_fixtures_golden_infra_code import FIXTURES, run_fixture
from tests.test_lakeformation_missing_grant import (
    cenario_fgac_escrita_negada,
    cenario_fgac_escrita_registrada,
    cenario_fta_append_sem_all,
    cenario_fta_leitura_sem_select,
    cenario_grant_que_cobre,
    cenario_sem_operacao,
)

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


# ---------------------------------------------------------------------------
# SF-LF-003 e SF-LF-004 entraram em 2026-09-09, junto com
# `sparkforge/facts/lakeformation.py`. As duas sao o PRIMEIRO caso desta area em
# que a regra nao le `tf.attribute` cru: o predicado que elas comparam por
# igualdade foi derivado num fact, porque o DSL de regra nao alcanca "o nome do
# catalogo esta dentro da chave".
# ---------------------------------------------------------------------------

RUNTIME_GLUE_51 = {"glue": "5.1", "spark": "3.5.6", "python": "3.11", "iceberg": "1.10.0"}


def _judge_source_em(src: str, runtime: dict) -> set[str]:
    facts = list(extract_terraform(src, "main.tf"))
    facts.extend(build_lakeformation(facts))
    return {f.rule_id for f in judge(facts, load_catalog(), runtime)}


# O VALOR da conf nao cabe em 100 colunas e nao pode ser quebrado: ele viaja
# inteiro para dentro do HCL, e o extrator le a linha como o Terraform a
# escreveria. Ele mora fora do template e entra por `.replace`, ANTES do
# `.format` -- assim `{catalogo}` e `{emrfs}` sobrevivem para serem
# preenchidos, e o texto produzido e byte a byte o mesmo de antes.
_CONF_CATALOGO = (
    "spark.sql.catalog.{catalogo}"
    "=org.apache.iceberg.spark.SparkSessionCatalog"
)
_CONF_RESOLVER = (
    "spark.hadoop.fs.s3.credentialsResolverClass="
    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver{emrfs}"
)

_TF_CATALOGO = """
resource "aws_glue_job" "unico" {{
  glue_version = "5.1"
  command {{
    name = "glueetl"
  }}
  default_arguments = {{
    "--enable-lakeformation-fine-grained-access" = "{fgac}"
    "--conf"                                     = "@CONF@"
  }}
}}
""".replace("@CONF@", _CONF_CATALOGO)

_TF_RESOLVER = """
resource "aws_glue_job" "unico" {{
  glue_version = "5.1"
  command {{
    name = "glueetl"
  }}
  default_arguments = {{
    "--conf" = "@CONF@"
  }}
}}
""".replace("@CONF@", _CONF_RESOLVER)

_EMRFS_RESTAURADO = " --conf spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem"


class TestSFLF003IcebergCatalogUnderFGAC:
    def test_o_catalogo_nomeado_com_fgac_acusa(self):
        achados = _judge_source_em(
            _TF_CATALOGO.format(fgac="true", catalogo="glue_catalog"), RUNTIME_GLUE_51
        )
        assert "SF-LF-003" in achados

    def test_o_session_catalog_com_fgac_NAO_acusa(self):
        """A metade que impede a regra de acusar todo job com FGAC.

        Sem este par, uma regra que ignorasse `is_session_catalog` e disparasse
        so pela presenca do argumento passaria igual -- e acusaria exatamente a
        configuracao que a AWS publica.
        """
        achados = _judge_source_em(
            _TF_CATALOGO.format(fgac="true", catalogo="spark_catalog"), RUNTIME_GLUE_51
        )
        assert "SF-LF-003" not in achados

    def test_o_catalogo_nomeado_SEM_fgac_NAO_acusa(self):
        """O par cruzado: `glue_catalog` fora de FGAC e configuracao correta, e
        a propria AWS a publica nos exemplos de Full Table Access."""
        achados = _judge_source_em(
            _TF_CATALOGO.format(fgac="false", catalogo="glue_catalog"), RUNTIME_GLUE_51
        )
        assert "SF-LF-003" not in achados

    def test_ela_exige_os_dois_facts_derivados(self):
        exigidos = set(_rule("SF-LF-003")["requires_facts"])
        assert exigidos == {"lakeformation.access_model", "lakeformation.iceberg_catalog"}

    def test_ela_NAO_declara_same_subject_e_o_risco_esta_escrito(self):
        """A ausencia e deliberada e medida: `tf.spark_conf` tem subject
        `<recurso>#<chave>` e o argumento de job tem `<recurso>`, entao os dois
        nunca cairiam no mesmo grupo. O falso positivo que isso abre tem de
        estar declarado em `risks`, senao a regra esconde o proprio limite."""
        regra = _rule("SF-LF-003")
        assert "same_subject" not in regra["when"]
        assert any("same_subject" in r for r in regra["risks"])


class TestSFLF004FTASemEMRFS:
    def test_resolver_sem_emrfs_no_51_acusa(self):
        achados = _judge_source_em(_TF_RESOLVER.format(emrfs=""), RUNTIME_GLUE_51)
        assert "SF-LF-004" in achados

    def test_resolver_COM_emrfs_restaurado_NAO_acusa(self):
        achados = _judge_source_em(
            _TF_RESOLVER.format(emrfs=_EMRFS_RESTAURADO), RUNTIME_GLUE_51
        )
        assert "SF-LF-004" not in achados

    def test_no_glue_50_a_MESMA_configuracao_esta_CORRETA(self):
        """A fronteira e de VERSAO, e este teste e o que prova que ela e real.

        Ate o Glue 5.0 o conector S3 default e o EMRFS, e
        `fs.s3.credentialsResolverClass` vale sem que ninguem restaure nada.
        Acusar aqui seria acusar configuracao correta -- e e por isso que o
        `runtime_scope` desta regra e `>=5.1` e nao `>=5.0` como o das irmas.
        """
        achados = _judge_source_em(_TF_RESOLVER.format(emrfs=""), RUNTIME_GLUE_50)
        assert "SF-LF-004" not in achados

    def test_guardada_por_glue_5_1(self):
        regra = _rule("SF-LF-004")
        assert regra["runtime_scope"] == {"glue": ">=5.1"}
        assert in_scope(regra["runtime_scope"], RUNTIME_GLUE_51)
        assert not in_scope(regra["runtime_scope"], RUNTIME_GLUE_50)

    def test_outro_resolver_nao_e_o_do_lake_formation(self):
        """A regra fala do resolver do Lake Formation, nao de qualquer resolver
        customizado -- um `credentialsResolverClass` proprio nao pede credencial
        ao Lake Formation e nao tem a pre-condicao de EMRFS."""
        src = _TF_RESOLVER.format(emrfs="").replace(
            "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
            "com.exemplo.MeuResolver",
        )
        assert "SF-LF-004" not in _judge_source_em(src, RUNTIME_GLUE_51)


# ---------------------------------------------------------------------------
# SF-LF-011 -- a falha observada (ERR-LF-001) cruzada com a permissao medida.
# Os cenarios sao os do extrator: tres acusam (AC1, AC2, AC4) e tres nao (AC3,
# AC5, AC8). `runtime_scope: {}` -- o runtime do judge nao decide nada aqui.


def _sf_lf_011_dispara(pool) -> bool:
    facts = list(pool) + build_missing_grant(pool)
    return "SF-LF-011" in {f.rule_id for f in judge(facts, load_catalog(), RUNTIME_GLUE_50)}


def test_sf_lf_011_dispara_so_com_permissao_nomeada():
    disparam = (
        cenario_fta_append_sem_all,
        cenario_fta_leitura_sem_select,
        cenario_fgac_escrita_negada,
    )
    for cenario in disparam:
        assert _sf_lf_011_dispara(cenario()), cenario.__name__
    calam = (cenario_grant_que_cobre, cenario_fgac_escrita_registrada, cenario_sem_operacao)
    for cenario in calam:
        assert not _sf_lf_011_dispara(cenario()), cenario.__name__
