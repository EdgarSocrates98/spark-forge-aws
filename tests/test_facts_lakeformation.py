"""`lakeformation.*` deriva o modelo de acesso que a configuracao DECLARA.

O que estes testes prendem nao e o parse -- e a fronteira entre observar e
julgar. `is_session_catalog: false` precisa sair sem acusacao junto, porque a
restricao de session catalog e de FGAC e a AWS publica exemplo de FTA com
catalogo de nome arbitrario. Quem transforma o booleano em achado e a regra.

O motivo de este modulo existir esta medido no proprio docstring dele: o DSL de
regra compara igualdade, e "este catalogo e o session catalog" nao e pergunta de
igualdade sobre nenhuma chave que os extratores emitem hoje.
"""

from __future__ import annotations

from sparkforge.facts.lakeformation import (
    EMITTED_KINDS,
    FGAC_ARGUMENT,
    build_lakeformation,
)
from sparkforge.findings.models import Fact

PROV = {"extractor": "teste@0.0.0", "artifact": "memoria"}


def _tf_attr(key: str, value: str, *, block: str = "default_arguments") -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"type": "tf_resource", "file": "main.tf", "line": 3, "symbol": "aws_glue_job.etl"},
        measures={},
        attrs={"key": key, "value": value, "block": block},
        provenance=PROV,
    )


def _tf_conf(key: str, value: str) -> Fact:
    return Fact(
        kind="tf.spark_conf",
        subject={
            "type": "tf_resource",
            "file": "main.tf",
            "line": 9,
            "symbol": f"aws_glue_job.etl#{key}",
        },
        measures={},
        attrs={
            "key": key,
            "value": value,
            "source_argument": "--conf",
            "block": "default_arguments",
        },
        provenance=PROV,
    )


def _efetiva(key: str, value: str, **extra: object) -> Fact:
    return Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": key},
        measures={},
        attrs={"key": key, "value": value, "app_id": "app-1", **extra},
        provenance=PROV,
    )


def _codigo(key: str, value: str) -> Fact:
    return Fact(
        kind="pyspark.conf_set",
        subject={"type": "source_location", "file": "job.py", "line": 12},
        measures={},
        attrs={"key": key, "value": value},
        provenance=PROV,
    )


def _de(facts: list[Fact], kind: str) -> list[Fact]:
    return [f for f in facts if f.kind == kind]


class TestModeloDeAcesso:
    def test_a_flag_ligada_vira_fgac(self):
        saida = build_lakeformation([_tf_attr(FGAC_ARGUMENT, "true")])
        modelo = _de(saida, "lakeformation.access_model")
        assert len(modelo) == 1
        assert modelo[0].attrs["model"] == "fgac"
        assert modelo[0].attrs["fgac_enabled"] is True
        assert modelo[0].attrs["source"] == "terraform"

    def test_a_flag_DESLIGADA_nao_e_a_flag_ausente(self):
        """`"false"` declarado e decisao escrita; ausencia e silencio.

        O molde e `SF-ERR-002`, que separa os dois pelo mesmo motivo: uma regra
        que trate `false` e ausente como a mesma coisa perde a capacidade de
        dizer que alguem desligou de proposito.
        """
        saida = build_lakeformation([_tf_attr(FGAC_ARGUMENT, "false")])
        modelo = _de(saida, "lakeformation.access_model")
        assert len(modelo) == 1
        assert modelo[0].attrs["model"] == "none"
        assert modelo[0].attrs["declared_value"] == "false"

        assert not _de(build_lakeformation([]), "lakeformation.access_model")

    def test_a_flag_fora_de_default_arguments_nao_conta(self):
        saida = build_lakeformation([_tf_attr(FGAC_ARGUMENT, "true", block="command")])
        assert not _de(saida, "lakeformation.access_model")


class TestCatalogoIceberg:
    def test_o_session_catalog_e_reconhecido_pelo_nome(self):
        saida = build_lakeformation(
            [
                _tf_conf(
                    "spark.sql.catalog.spark_catalog",
                    "org.apache.iceberg.spark.SparkSessionCatalog",
                )
            ]
        )
        catalogos = _de(saida, "lakeformation.iceberg_catalog")
        assert len(catalogos) == 1
        assert catalogos[0].attrs["catalog_name"] == "spark_catalog"
        assert catalogos[0].attrs["is_session_catalog"] is True
        assert catalogos[0].attrs["catalog_impl"] == (
            "org.apache.iceberg.spark.SparkSessionCatalog"
        )

    def test_catalogo_de_nome_arbitrario_sai_como_OBSERVACAO_e_nao_acusacao(self):
        """O fact diz `false` e para. Nenhum `reason`, nenhum `severity`.

        Sob FTA a AWS publica exemplo com `glue_catalog`, entao um extrator que
        acusasse aqui acusaria configuracao suportada. A restricao e de FGAC, e
        cruzar as duas coisas e trabalho da regra.
        """
        saida = build_lakeformation(
            [
                _tf_conf(
                    "spark.sql.catalog.glue_catalog",
                    "org.apache.iceberg.spark.SparkCatalog",
                )
            ]
        )
        catalogo = _de(saida, "lakeformation.iceberg_catalog")[0]
        assert catalogo.attrs["is_session_catalog"] is False
        assert "reason" not in catalogo.attrs
        assert catalogo.measures == {}

    def test_propriedade_do_catalogo_nao_declara_catalogo_novo(self):
        """`spark.sql.catalog.foo.warehouse` e propriedade de `foo`.

        Sem este corte, cada propriedade viraria um catalogo de nome
        `foo.warehouse`, e a contagem de catalogos do case seria ficcao.
        """
        saida = build_lakeformation(
            [
                _tf_conf("spark.sql.catalog.spark_catalog", "org.x.Catalog"),
                _tf_conf("spark.sql.catalog.spark_catalog.warehouse", "s3://w/"),
                _tf_conf("spark.sql.catalog.dropDirectoryBeforeTable.enabled", "true"),
            ]
        )
        nomes = sorted(f.attrs["catalog_name"] for f in _de(saida, "lakeformation.iceberg_catalog"))
        assert nomes == ["spark_catalog"]

    def test_o_marcador_de_credencial_do_lake_formation_agrega_no_mesmo_catalogo(self):
        saida = build_lakeformation(
            [
                _tf_conf("spark.sql.catalog.glue_catalog", "org.x.Catalog"),
                _tf_conf("spark.sql.catalog.glue_catalog.glue.lakeformation-enabled", "true"),
            ]
        )
        catalogos = _de(saida, "lakeformation.iceberg_catalog")
        assert len(catalogos) == 1
        assert catalogos[0].attrs["lakeformation_enabled"] is True

    def test_a_MESMA_chave_em_duas_superficies_produz_dois_facts(self):
        """Pedido e medida nao se fundem, e o campo que os separa e `source`.

        `tf.spark_conf` e o que o Terraform PEDIU; `spark.conf_effective` e o
        que o run TEVE. Fundir os dois num fact so escolheria precedencia em
        silencio, e precedencia e julgamento.
        """
        saida = build_lakeformation(
            [
                _tf_conf("spark.sql.catalog.spark_catalog", "org.x.Catalog"),
                _efetiva("spark.sql.catalog.spark_catalog", "org.y.Outro"),
            ]
        )
        catalogos = _de(saida, "lakeformation.iceberg_catalog")
        assert sorted(f.attrs["source"] for f in catalogos) == ["event_log", "terraform"]
        assert len({f.id for f in catalogos}) == 2

    def test_conf_do_CODIGO_tambem_entra(self):
        saida = build_lakeformation([_codigo("spark.sql.catalog.spark_catalog", "org.x.C")])
        assert [f.attrs["source"] for f in _de(saida, "lakeformation.iceberg_catalog")] == ["code"]


class TestFilesystem:
    def test_resolver_pedido_sem_emrfs_restaurado(self):
        """A configuracao que nao produz erro e nao produz efeito.

        `fs.s3.credentialsResolverClass` e chave de EMRFS. Sob S3A -- default do
        Glue 5.1 -- ela e ignorada em silencio, e o fact registra os dois lados
        para que a regra possa dizer isso sem adivinhar.
        """
        saida = build_lakeformation(
            [
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass",
                    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
                )
            ]
        )
        fs = _de(saida, "lakeformation.filesystem")
        assert len(fs) == 1
        assert fs[0].attrs["lf_credentials_resolver_declared"] is True
        assert fs[0].attrs["emrfs_restored"] is False

    def test_emrfs_restaurado_e_reconhecido_pela_classe(self):
        saida = build_lakeformation(
            [
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass",
                    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
                ),
                _tf_conf("spark.hadoop.fs.s3.impl", "com.amazon.ws.emr.hadoop.fs.EmrFileSystem"),
            ]
        )
        fs = _de(saida, "lakeformation.filesystem")
        assert len(fs) == 1
        assert fs[0].attrs["emrfs_restored"] is True

    def test_outro_resolver_nao_e_o_do_lake_formation(self):
        saida = build_lakeformation(
            [_tf_conf("spark.hadoop.fs.s3.credentialsResolverClass", "com.exemplo.MeuResolver")]
        )
        assert _de(saida, "lakeformation.filesystem")[0].attrs[
            "lf_credentials_resolver_declared"
        ] is False


class TestRecusaNomeada:
    def test_com_modelo_declarado_a_lacuna_de_permissao_e_nomeada(self):
        saida = build_lakeformation([_tf_attr(FGAC_ARGUMENT, "true")])
        recusa = _de(saida, "lakeformation.unresolved")
        assert len(recusa) == 1
        assert recusa[0].attrs["reason"] == "permissoes_nao_coletadas"
        assert "lake_formation_grants" in recusa[0].attrs["missing"]

    def test_case_sem_lake_formation_nao_ganha_recusa(self):
        """Recusa que aparece em todo case nao informa nada."""
        saida = build_lakeformation([_tf_conf("spark.sql.shuffle.partitions", "200")])
        assert not _de(saida, "lakeformation.unresolved")
        assert saida == []


class TestContratoDoModulo:
    def test_todo_kind_emitido_esta_declarado(self):
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf("spark.sql.catalog.spark_catalog", "org.x.C"),
                _tf_conf("spark.hadoop.fs.s3.impl", "com.amazon.ws.emr.hadoop.fs.EmrFileSystem"),
            ]
        )
        assert {f.kind for f in saida} <= EMITTED_KINDS
        assert {f.kind for f in saida} == EMITTED_KINDS

    def test_valor_redigido_nao_sustenta_afirmacao(self):
        """Redacao vem antes do parse, e o parse nao a desfaz.

        Sem este corte, `<redigido>` compararia diferente de `_EMRFS_IMPL` e o
        fact diria `emrfs_restored: false` por um motivo que nao e o verdadeiro.
        """
        saida = build_lakeformation(
            [_efetiva("spark.hadoop.fs.s3.impl", "<redigido>", redacted=True)]
        )
        assert not _de(saida, "lakeformation.filesystem")

    def test_nada_dentro_nada_fora(self):
        assert build_lakeformation([]) == []

    def test_nenhum_fact_carrega_juizo(self):
        """Nem `severity`, nem `confidence`, nem `fix`. Fact observa."""
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf("spark.sql.catalog.glue_catalog", "org.x.C"),
            ]
        )
        proibidos = {"severity", "confidence", "fixes", "likely_causes", "recommendation"}
        for fact in saida:
            assert not proibidos & set(fact.attrs), fact.kind


class TestOEstadoBOTH:
    """FGAC e Full Table Access declarados juntos -- a AWS proibe os dois."""

    def test_fgac_com_resolver_de_fta_sai_both(self):
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass",
                    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
                ),
            ]
        )
        modelo = _de(saida, "lakeformation.access_model")[0]
        assert modelo.attrs["model"] == "both"
        assert modelo.attrs["fta_markers"] == ["spark.hadoop.fs.s3.credentialsResolverClass"]

    def test_fgac_com_lakeformation_enabled_no_catalogo_tambem_sai_both(self):
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf("spark.sql.catalog.glue_catalog.glue.lakeformation-enabled", "true"),
            ]
        )
        modelo = _de(saida, "lakeformation.access_model")[0]
        assert modelo.attrs["model"] == "both"

    def test_fgac_sozinho_continua_fgac(self):
        """A metade que impede `both` de virar o default silencioso."""
        saida = build_lakeformation([_tf_attr(FGAC_ARGUMENT, "true")])
        modelo = _de(saida, "lakeformation.access_model")[0]
        assert modelo.attrs["model"] == "fgac"
        assert modelo.attrs["fta_markers"] == []

    def test_marcador_de_fta_DESLIGADO_nao_conta(self):
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf("spark.sql.catalog.glue_catalog.glue.lakeformation-enabled", "false"),
            ]
        )
        assert _de(saida, "lakeformation.access_model")[0].attrs["model"] == "fgac"

    def test_resolver_de_OUTRO_fornecedor_nao_conta(self):
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "true"),
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass", "com.exemplo.MeuResolver"
                ),
            ]
        )
        assert _de(saida, "lakeformation.access_model")[0].attrs["model"] == "fgac"

    def test_flag_desligada_com_marcador_de_fta_NAO_e_both(self):
        """`false` mais FTA e um job de FTA, nao uma contradicao."""
        saida = build_lakeformation(
            [
                _tf_attr(FGAC_ARGUMENT, "false"),
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass",
                    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
                ),
            ]
        )
        modelo = _de(saida, "lakeformation.access_model")[0]
        assert modelo.attrs["model"] == "none"
        assert modelo.attrs["fta_markers"] == []

    def test_job_SO_de_fta_nao_produz_access_model(self):
        """O limite declarado no docstring: FTA nao tem argumento que o ligue.

        A superficie dele e `lakeformation.filesystem`, e inventar um
        `model: "fta"` ancorado numa chave de conf qualquer daria ao FTA uma
        declaracao que ele nao tem.
        """
        saida = build_lakeformation(
            [
                _tf_conf(
                    "spark.hadoop.fs.s3.credentialsResolverClass",
                    "com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver",
                )
            ]
        )
        assert not _de(saida, "lakeformation.access_model")
        assert _de(saida, "lakeformation.filesystem")
