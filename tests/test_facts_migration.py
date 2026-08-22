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


REQUIREMENTS = "pandas==2.0.3\npyarrow==14.0.1\nrequests==2.31.0\n"

JOB_COM_CAST = '''
df = df.withColumn("valor", col("texto").cast("int"))
tabela = spark.sql("SELECT CAST(x AS DECIMAL(10,2)) FROM t")
seguro = df.withColumn("v", try_cast(col("texto"), "int"))
'''


class TestDependenciaEFormato:
    def test_reconhece_jar_com_scala_no_nome(self, tmp_path):
        (tmp_path / "conector_2.12-1.4.0.jar").write_bytes(b"")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        jars = [f for f in facts if f.kind == "mig.jar_binary"]
        assert len(jars) == 1
        assert jars[0].attrs["scala"] == "2.12"

    def test_jar_sem_scala_no_nome_ainda_e_observado(self, tmp_path):
        (tmp_path / "opaco.jar").write_bytes(b"")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        jars = [f for f in facts if f.kind == "mig.jar_binary"]
        assert len(jars) == 1
        assert jars[0].attrs["scala"] == ""

    def test_reconhece_dependencia_python_declarada(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        deps = {
            f.attrs["package"]: f.attrs["version"]
            for f in facts
            if f.kind == "mig.python_dep"
        }
        assert deps == {"pandas": "2.0.3", "pyarrow": "14.0.1", "requests": "2.31.0"}

    def test_reconhece_cast_sem_guarda_e_ignora_try_cast(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_CAST, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        riscos = [f for f in facts if f.kind == "mig.ansi_risk"]
        assert len(riscos) == 2, [f.subject["line"] for f in riscos]
        assert all(f.attrs["form"] == "cast" for f in riscos)


JOB_COM_FORMAT_VERSION = '''
spark.sql("ALTER TABLE t SET TBLPROPERTIES ('format-version'='2')")
'''


class TestFormatoDeTabela:
    # Decisao pinada por este teste: o atributo se chama `format_version`, nao
    # `version` puro, para deixar explicito que e a versao do FORMATO da
    # tabela (spec Iceberg/Hudi/Delta) -- nao a versao da BIBLIOTECA que le ou
    # escreve. Confundir as duas e o erro citado em `prompt_migrations_glue.md`
    # Sec 8.8; um atributo generico `version` reintroduziria a mesma ambiguidade
    # que o kind existe para evitar.
    def test_reconhece_format_version_da_tabela(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_FORMAT_VERSION, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        formatos = [f for f in facts if f.kind == "mig.table_format"]
        assert len(formatos) == 1
        assert formatos[0].attrs["format_version"] == "2"


# Decisao pinada por este teste: comentario, linha em branco e pacote sem pin
# (`pandas` sem `==`) NAO emitem `mig.python_dep`. Nenhum dos tres fixa uma
# versao -- e fixar versao e exatamente o que este kind observa. Sub-capturar
# aqui nao esconde um binario ou uma config morta (a categoria de erro que
# este modulo evita por design); so evita afirmar uma versao que o arquivo
# nao afirma.
REQUIREMENTS_COM_CASOS_NEGATIVOS = (
    "# pandas==2.0.3\n"
    "\n"
    "pandas\n"
    "requests==2.31.0\n"
)


class TestNegativoDependenciaPython:
    def test_ignora_comentario_branco_e_pacote_sem_pin(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            REQUIREMENTS_COM_CASOS_NEGATIVOS, encoding="utf-8"
        )
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        deps = {
            f.attrs["package"]: f.attrs["version"]
            for f in facts
            if f.kind == "mig.python_dep"
        }
        assert deps == {"requests": "2.31.0"}


class TestConfigRenomeadaNoSpark4:
    def test_reconhece_a_chave_de_rebase_com_prefixo_legacy(self, tmp_path):
        (tmp_path / "job.py").write_text(
            'spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")\n',
            encoding="utf-8",
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        renomeadas = [f for f in facts if f.kind == "mig.renamed_conf"]
        assert len(renomeadas) == 1
        assert renomeadas[0].attrs["key"] == "spark.sql.legacy.parquet.int96RebaseModeInWrite"
        assert renomeadas[0].attrs["renamed_to"] == "spark.sql.parquet.int96RebaseModeInWrite"

    def test_codec_lz4raw_e_observado_pelo_mesmo_kind(self, tmp_path):
        (tmp_path / "job.py").write_text(
            'df.write.option("compression", "lz4raw").parquet(destino)\n', encoding="utf-8"
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        renomeadas = [f for f in facts if f.kind == "mig.renamed_conf"]
        assert [f.attrs["renamed_to"] for f in renomeadas] == ["lz4_raw"]

    def test_chave_legacy_que_nao_foi_renomeada_nao_vira_este_kind(self, tmp_path):
        """`spark.sql.legacy.timeParserPolicy` continua existindo com esse nome
        em Spark 4. Tratar toda chave `legacy.` como renomeada acusaria config
        correta -- e `mig.legacy_conf` ja observa a familia inteira."""
        (tmp_path / "job.py").write_text(
            'spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")\n', encoding="utf-8"
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        assert [f for f in facts if f.kind == "mig.renamed_conf"] == []

    def test_numera_a_linha_igual_ao_detector_de_config_legada(self, tmp_path):
        """Form feed (`\f`) e separador de pagina legal em fonte Python. Sob
        `splitlines()` ele contaria como quebra de linha e sob `split("\n")`
        nao, entao os dois detectores dariam numeros diferentes para a MESMA
        linha -- e quem lesse os dois subjects procuraria a config em dois
        lugares, um dos quais nao existe.
        """
        (tmp_path / "job.py").write_text(
            'import os\n\f\nspark.conf.set('
            '"spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")\n',
            encoding="utf-8",
            newline="",
        )
        facts = migration.extract_migration_path(tmp_path / "job.py", repo_root=tmp_path)
        linhas = {f.kind: f.subject["line"] for f in facts}
        assert linhas["mig.renamed_conf"] == linhas["mig.legacy_conf"]
