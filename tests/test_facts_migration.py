from sparkforge.facts import migration

JOB_COM_SDK_V1 = '''
from awsglue.context import GlueContext
import com.amazonaws.services.s3.AmazonS3ClientBuilder as Builder

def main():
    pass
'''

JOB_LIMPO = '''
from awsglue.context import GlueContext

def main():
    pass
'''


class TestSdkImport:
    def test_reconhece_import_do_sdk_v1(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        sdk = [f for f in facts if f.kind == "mig.sdk_import"]
        assert len(sdk) == 1
        assert sdk[0].attrs["package"] == "com.amazonaws"
        assert sdk[0].attrs["generation"] == "v1"

    def test_job_sem_sdk_nao_emite_o_kind(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_LIMPO, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert [f for f in facts if f.kind == "mig.sdk_import"] == []

    def test_o_fact_nao_carrega_juizo(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        for fact in facts:
            texto = str(fact.attrs) + str(fact.measures)
            for palavra in ("severidade", "risco", "deve", "incompativel"):
                assert palavra not in texto.lower(), f"{fact.kind} julga: {texto}"

    def test_kinds_emitidos_sao_vocabulario_fechado(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert {f.kind for f in facts} <= migration.EMITTED_KINDS

    def test_extracao_e_deterministica(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        primeira = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        segunda = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert [f.id for f in primeira] == [f.id for f in segunda]


JOB_COM_EMRFS = '''
spark.conf.set("fs.s3.consistent", "true")
spark.conf.set("fs.s3.consistent.retryCount", "5")
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
sql_context = SQLContext(sc)
'''

JOB_SEM_CHAVES_RELEVANTES = '''
spark.conf.set("fs.s3a.endpoint", "s3.amazonaws.com")
spark.conf.set("spark.sql.adaptive.enabled", "true")
'''

# Decisao pinada por este teste: o extrator faz o MESMO tipo de varredura
# ingenua por linha que `_sdk_imports` ja faz para `com.amazonaws` (regex sobre
# o texto cru, sem checar se a linha e uma chamada real a `spark.conf.set`).
# Por isso uma chave de EMRFS entre aspas dentro de um comentario tambem gera
# fact. Escolha deliberada: sobre-capturar custa a quem escreve a regra
# explicar um falso positivo; sub-capturar esconde uma configuracao morta para
# sempre -- e essa e a categoria de erro que este extrator existe para evitar.
JOB_CHAVE_EM_COMENTARIO = '''
# TODO: revisar depois -- "fs.s3.consistent" nao faz mais nada no S3A do Glue 5+
'''


class TestConfiguracaoLegada:
    def _facts(self, tmp_path, texto=JOB_COM_EMRFS):
        (tmp_path / "job.py").write_text(texto, encoding="utf-8")
        return migration.extract_migration_tree(tmp_path, repo_root=tmp_path)

    def test_reconhece_configuracao_de_emrfs(self, tmp_path):
        chaves = sorted(
            f.attrs["key"] for f in self._facts(tmp_path) if f.kind == "mig.emrfs_config"
        )
        assert chaves == ["fs.s3.consistent", "fs.s3.consistent.retryCount"]

    def test_reconhece_configuracao_legada_do_spark(self, tmp_path):
        legadas = [f for f in self._facts(tmp_path) if f.kind == "mig.legacy_conf"]
        assert [f.attrs["key"] for f in legadas] == ["spark.sql.legacy.timeParserPolicy"]

    def test_reconhece_api_depreciada(self, tmp_path):
        apis = [f for f in self._facts(tmp_path) if f.kind == "mig.deprecated_api"]
        assert [f.attrs["symbol"] for f in apis] == ["SQLContext"]

    def test_registra_a_linha_de_origem(self, tmp_path):
        # Task 4 ancora a linha em `fact.subject["line"]` (`_source_subject`);
        # `provenance` carrega artefato/sha/extrator, nunca a linha. Teste
        # preciso em vez de aceitar as duas formas -- ver instrucoes da Task 5.
        for fact in self._facts(tmp_path):
            assert fact.subject["line"] > 0

    def test_chave_irrelevante_nao_emite_fact(self, tmp_path):
        facts = self._facts(tmp_path, JOB_SEM_CHAVES_RELEVANTES)
        relevantes = [f for f in facts if f.kind in ("mig.emrfs_config", "mig.legacy_conf")]
        assert relevantes == []

    def test_reconhece_chave_de_emrfs_dentro_de_comentario_por_design(self, tmp_path):
        chaves = [
            f.attrs["key"]
            for f in self._facts(tmp_path, JOB_CHAVE_EM_COMENTARIO)
            if f.kind == "mig.emrfs_config"
        ]
        assert chaves == ["fs.s3.consistent"]
