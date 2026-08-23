"""A composicao de artefatos que `assess()` deliberadamente nao faz.

`assess()` e puro sobre `list[Fact]`, e e isso que torna testavel julgar sem
tocar disco. `collect()` e a metade de I/O -- mesma separacao que faz
`extract_migration_tree` viver fora de `judge`.
"""
from pathlib import Path

from sparkforge.facts import migration as facts_migration
from sparkforge.migration import collect as collect_mod

JOB = (
    "import com.amazonaws.services.s3.AmazonS3\n"
    'spark.conf.set("fs.s3.consistent", "true")\n'
)

TF_FGAC = """
resource "aws_glue_job" "curated" {
  name = "curated"
  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--extra-jars"                               = "s3://bucket/conector.jar"
  }
}
"""

INVENTARIO = """
consumers:
  - table: glue_catalog.curated.pedidos
    service: athena
"""


def _job(tmp_path: Path) -> Path:
    (tmp_path / "job.py").write_text(JOB, encoding="utf-8")
    return tmp_path


class TestCodigoSempre:
    def test_diretorio_so_com_codigo_devolve_o_que_o_extrator_de_migracao_devolve(
        self, tmp_path
    ):
        raiz = _job(tmp_path)
        direto = facts_migration.extract_migration_tree(raiz, repo_root=raiz)
        assert [f.to_dict() for f in collect_mod.collect(raiz)] == [
            f.to_dict() for f in direto
        ]

    def test_arquivo_py_sozinho_tambem_e_aceito(self, tmp_path):
        raiz = _job(tmp_path)
        facts = collect_mod.collect(raiz / "job.py")
        assert {f.kind for f in facts} == {"mig.sdk_import", "mig.emrfs_config"}


class TestTerraformSoQuandoExiste:
    def test_sem_tf_nenhum_fact_de_terraform(self, tmp_path):
        facts = collect_mod.collect(_job(tmp_path))
        assert not [f for f in facts if f.kind.startswith("tf.")]

    def test_com_tf_os_facts_entram_na_uniao(self, tmp_path):
        raiz = _job(tmp_path)
        (raiz / "infra.tf").write_text(TF_FGAC, encoding="utf-8")
        facts = collect_mod.collect(raiz)
        kinds = {f.kind for f in facts}
        assert "tf.attribute" in kinds, "o `.tf` do job precisa virar fact"
        # A uniao, nao a substituicao: o codigo continua ali.
        assert "mig.sdk_import" in kinds


class TestInventarioDeConsumidoresPorConvencao:
    """O inventario e procurado onde o extrator o declara, nao adivinhado.

    `sparkforge/facts/consumers.py` nomeia `.sparkforge/consumers.yaml` como a
    convencao. Varrer todo `*.yaml` da arvore acharia o inventario, e junto com
    ele todo workflow de CI e todo arquivo de configuracao -- cada um virando um
    `env.consumers_analyzed` que afirma "inventario lido" sobre arquivo que nao
    e inventario.
    """

    def test_le_o_arquivo_da_convencao(self, tmp_path):
        raiz = _job(tmp_path)
        (raiz / ".sparkforge").mkdir()
        (raiz / ".sparkforge" / "consumers.yaml").write_text(INVENTARIO, encoding="utf-8")
        facts = collect_mod.collect(raiz)
        consumidores = [f for f in facts if f.kind == "env.consumer"]
        assert [f.attrs["service"] for f in consumidores] == ["athena"]

    def test_le_o_diretorio_da_convencao_dividido_por_dominio(self, tmp_path):
        raiz = _job(tmp_path)
        (raiz / ".sparkforge" / "consumers").mkdir(parents=True)
        (raiz / ".sparkforge" / "consumers" / "vendas.yaml").write_text(
            INVENTARIO, encoding="utf-8"
        )
        facts = collect_mod.collect(raiz)
        assert [f.kind for f in facts if f.kind == "env.consumer"] == ["env.consumer"]

    def test_yaml_fora_da_convencao_nao_vira_inventario(self, tmp_path):
        raiz = _job(tmp_path)
        (raiz / "config.yaml").write_text(INVENTARIO, encoding="utf-8")
        facts = collect_mod.collect(raiz)
        assert not [f for f in facts if f.kind.startswith("env.")], (
            "um `.yaml` qualquer da arvore nao e inventario declarado"
        )


class TestUniaoOrdenada:
    def test_ordem_e_deterministica(self, tmp_path):
        raiz = _job(tmp_path)
        (raiz / "infra.tf").write_text(TF_FGAC, encoding="utf-8")
        (raiz / ".sparkforge").mkdir()
        (raiz / ".sparkforge" / "consumers.yaml").write_text(INVENTARIO, encoding="utf-8")
        uma = [f.to_dict() for f in collect_mod.collect(raiz)]
        outra = [f.to_dict() for f in collect_mod.collect(raiz)]
        assert uma == outra

    def test_o_tf_da_convencao_de_consumidores_nao_e_varrido_duas_vezes(self, tmp_path):
        # `.sparkforge/` fica DENTRO da raiz, e `extract_terraform_tree` varre a
        # raiz inteira: um `.tf` ali dentro entraria uma vez so, nunca duas.
        raiz = _job(tmp_path)
        (raiz / ".sparkforge").mkdir()
        (raiz / ".sparkforge" / "extra.tf").write_text(TF_FGAC, encoding="utf-8")
        facts = collect_mod.collect(raiz)
        anchors = [f.provenance["artifact"] for f in facts if f.kind == "tf.resource"]
        assert len(anchors) == len(set(anchors))
