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
