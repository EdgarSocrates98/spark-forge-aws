from sparkforge.facts import migration
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

SPARK_4 = {"glue": "6.0", "spark": "4.1.1", "python": "3.13"}
SPARK_35 = {"glue": "5.1", "spark": "3.5.6", "python": "3.11"}


def _facts(tmp_path, corpo: str):
    (tmp_path / "job.py").write_text(corpo, encoding="utf-8")
    return migration.extract_migration_tree(tmp_path, repo_root=tmp_path)


class TestConfigRenomeada:
    CORPO = 'spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")\n'

    def test_dispara_em_spark_4(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_4)
        assert "SF-SPARK4-001" in {f.rule_id for f in findings}

    def test_nao_dispara_em_spark_35(self, tmp_path):
        """A chave antiga e a CERTA em 3.5. Acusa-la ali seria mandar consertar
        o que nao esta quebrado."""
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_35)
        assert "SF-SPARK4-001" not in {f.rule_id for f in findings}


class TestApiRemovida:
    CORPO = "import pyspark.pandas as ps\nnovo = base.append(extra)\n"

    def test_dispara_em_spark_4(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_4)
        assert "SF-SPARK4-002" in {f.rule_id for f in findings}

    def test_nao_dispara_em_spark_35(self, tmp_path):
        findings = judge(_facts(tmp_path, self.CORPO), load_catalog(), SPARK_35)
        assert "SF-SPARK4-002" not in {f.rule_id for f in findings}


class TestApiRemovidaNaoAcusaCodigoPythonComum:
    def test_append_de_lista_python_nao_dispara(self, tmp_path):
        """`acc.append(1)` numa lista e Python comum, nao a API removida do
        pandas-on-Spark. Acusar isso destruiria a confianca no relatorio
        inteiro -- e o mesmo estrago que `same_subject` existe para evitar em
        SF-GLUE-002."""
        corpo = "acc = []\nacc.append(1)\n"
        findings = judge(_facts(tmp_path, corpo), load_catalog(), SPARK_4)
        assert "SF-SPARK4-002" not in {f.rule_id for f in findings}

    def test_o_fact_continua_sendo_emitido(self, tmp_path):
        """A observacao nao some: o extrator viu um `.append(` e diz isso. Quem
        decide que aquilo nao e o problema e a regra, nao o extrator -- tirar o
        fact criaria falso negativo silencioso."""
        from sparkforge.facts import migration

        (tmp_path / "job.py").write_text("acc = []\nacc.append(1)\n", encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert [f.kind for f in facts if f.kind == "mig.removed_api"] == ["mig.removed_api"]

    def test_modulo_que_usa_pandas_on_spark_continua_sendo_acusado(self, tmp_path):
        """A outra metade do conserto: o filtro nao pode virar falso negativo.
        O MESMO `.append` num modulo que importa `pyspark.pandas` segue
        disparando em P1 -- ali a API removida e de fato a que esta sendo
        chamada."""
        corpo = "import pyspark.pandas as ps\nacc = ps.read_parquet(origem)\nacc.append(1)\n"
        findings = judge(_facts(tmp_path, corpo), load_catalog(), SPARK_4)
        acusadas = {f.rule_id: f for f in findings}
        assert "SF-SPARK4-002" in acusadas
        assert acusadas["SF-SPARK4-002"].severity == "P1"


class TestPisoDeDependencia:
    def test_pyarrow_abaixo_do_piso_dispara(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pyarrow==11.0.0\n", encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        findings = judge(facts, load_catalog(), SPARK_4)
        assert "SF-SPARK4-003" in {f.rule_id for f in findings}

    def test_pyarrow_no_piso_nao_dispara(self, tmp_path):
        """O piso do Spark 4.1 e 15.0.0. Acusar exatamente 15.0.0 tornaria a
        regra ruido em todo job que ja migrou."""
        (tmp_path / "requirements.txt").write_text("pyarrow==15.0.0\n", encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        findings = judge(facts, load_catalog(), SPARK_4)
        assert "SF-SPARK4-003" not in {f.rule_id for f in findings}


class TestFronteiraBinariaDoScala:
    """SF-SPARK4-004. O guarda e por SPARK e nao por Glue porque quem subiu o
    Scala para 2.13 foi o Spark 4, nao o empacotamento da AWS -- a afirmacao
    vale igual num EMR com Spark 4. Mesma razao das outras tres da area."""

    def _jars(self, tmp_path, nome: str):
        (tmp_path / nome).write_bytes(b"")
        return migration.extract_migration_tree(tmp_path, repo_root=tmp_path)

    def test_jar_de_scala_212_dispara_em_spark_4(self, tmp_path):
        findings = judge(self._jars(tmp_path, "conector_2.12-1.4.0.jar"), load_catalog(), SPARK_4)
        acusadas = {f.rule_id: f for f in findings}
        assert "SF-SPARK4-004" in acusadas
        assert acusadas["SF-SPARK4-004"].severity == "P0"

    def test_jar_de_scala_212_nao_dispara_em_spark_35(self, tmp_path):
        """Scala 2.12 e o CERTO em Spark 3.5. Acusa-lo ali seria mandar
        recompilar um artefato que esta correto para o runtime em que roda."""
        findings = judge(self._jars(tmp_path, "conector_2.12-1.4.0.jar"), load_catalog(), SPARK_35)
        assert "SF-SPARK4-004" not in {f.rule_id for f in findings}

    def test_jar_de_scala_213_nao_dispara_em_spark_4(self, tmp_path):
        """O jar ja recompilado e exatamente o estado desejado -- acusa-lo
        tornaria a regra ruido em todo job que ja migrou."""
        findings = judge(self._jars(tmp_path, "conector_2.13-1.4.0.jar"), load_catalog(), SPARK_4)
        assert "SF-SPARK4-004" not in {f.rule_id for f in findings}

    def test_jar_de_scala_213_nao_dispara_em_spark_35(self, tmp_path):
        findings = judge(self._jars(tmp_path, "conector_2.13-1.4.0.jar"), load_catalog(), SPARK_35)
        assert "SF-SPARK4-004" not in {f.rule_id for f in findings}

    def test_jar_sem_sufixo_de_scala_nao_dispara(self, tmp_path):
        """Sem `attrs.scala_minor` o caminho fica ausente no avaliador
        (`ExprError`, logo `False`). Um jar que nao declara Scala no nome pode
        ser Java puro: acusa-lo seria acusar artefato correto."""
        findings = judge(self._jars(tmp_path, "opaco.jar"), load_catalog(), SPARK_4)
        assert "SF-SPARK4-004" not in {f.rule_id for f in findings}

    def test_jar_com_versao_que_nao_e_de_scala_no_nome_nao_dispara(self, tmp_path):
        """`minhalib_1.0-SNAPSHOT.jar` casa o regex do sufixo por acidente --
        `_1.0-` tem a mesma forma de `_2.12-`. Sem a guarda de major no
        extrator, esse jar receberia `scala_minor` 0 e levaria um P0 mandando
        recompilar contra Scala 2.13 um artefato que nunca teve Scala."""
        findings = judge(self._jars(tmp_path, "minhalib_1.0-SNAPSHOT.jar"), load_catalog(), SPARK_4)
        assert "SF-SPARK4-004" not in {f.rule_id for f in findings}

    def test_o_fact_continua_sendo_emitido_para_o_jar_opaco(self, tmp_path):
        """A observacao nao some: o extrator viu um jar e diz isso. Quem decide
        que nao da para afirmar nada sobre ele e a regra."""
        facts = self._jars(tmp_path, "opaco.jar")
        assert [f.kind for f in facts] == ["mig.jar_binary"]
