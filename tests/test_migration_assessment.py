import pytest

from sparkforge.facts import migration as facts_migration
from sparkforge.migration import assessment

JOB = (
    "import com.amazonaws.services.s3.AmazonS3\n"
    'spark.conf.set("fs.s3.consistent", "true")\n'
)

# SF-MIG-003 exige `mig.ansi_risk` com `attrs.form == "cast"`, e esta regra e
# `blocked_on`: precisa disparar em NENHUM degrau, mesmo com o fact presente.
JOB_COM_CAST_SEM_GUARDA = 'x = df.withColumn("v", col("texto").cast("int"))\n'


def _facts(tmp_path):
    (tmp_path / "job.py").write_text(JOB, encoding="utf-8")
    return facts_migration.extract_migration_tree(tmp_path, repo_root=tmp_path)


def _facts_com_cast(tmp_path):
    (tmp_path / "job.py").write_text(JOB_COM_CAST_SEM_GUARDA, encoding="utf-8")
    return facts_migration.extract_migration_tree(tmp_path, repo_root=tmp_path)


class TestAvaliacaoPorDegrau:
    def test_cada_finding_registra_em_que_degrau_nasceu(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.findings, "esperava finding de SF-MIG"
        for _, degrau in resultado.by_step:
            assert degrau in (("4.0", "5.0"), ("5.0", "5.1"))

    def test_par_sem_degrau_nao_produz_finding(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="5.1", target="5.1")
        assert resultado.findings == []

    def test_gate_sem_evidencia_e_blocked_nunca_pass(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        for nome in ("dados", "performance", "custo", "canary"):
            assert resultado.gates[nome] == "BLOCKED", nome
            assert resultado.missing_evidence[nome], f"{nome} sem evidencia nomeada"

    def test_recomendacao_nao_e_go_com_gate_bloqueado(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.recommendation in ("CONDITIONAL_GO", "NO_GO")

    def test_serializa_para_dict(self, tmp_path):
        d = assessment.assess(_facts(tmp_path), source="4.0", target="5.1").to_dict()
        assert d["source_runtime"] == "4.0"
        assert d["target_runtime"] == "5.1"
        assert d["gates"]["dados"] == "BLOCKED"


class TestRegraBloqueadaNuncaAparece:
    def test_sf_mig_003_bloqueada_por_blocked_on_nunca_produz_finding(self, tmp_path):
        # O fact mig.ansi_risk existe (extrator ja o emite desde a Task 6), mas
        # a regra que o julgaria (SF-MIG-003) esta `blocked_on` porque nenhuma
        # fonte confirma a versao do Glue em que ANSI vira default (Task 11
        # ainda nao rodou). `judge` reporta isso como skipped, nunca como
        # finding -- provar isso em CADA degrau do caminho, nao so num, e o
        # que garante que nenhum runtime_scope futuro reintroduza o disparo
        # por acidente antes de a matriz ganhar a fronteira.
        facts = _facts_com_cast(tmp_path)
        resultado = assessment.assess(facts, source="3.0", target="5.1")
        assert resultado.steps, "caminho precisa ter ao menos um degrau"
        assert "SF-MIG-003" not in {f.rule_id for f in resultado.findings}
        assert "SF-MIG-003" not in {f.rule_id for f, _ in resultado.by_step}


class TestGuardaDeVersao:
    def test_degrau_fora_do_runtime_scope_nao_dispara_a_regra(self, tmp_path):
        # SF-MIG-001 e SF-MIG-002 exigem `glue: ">=5.0"`. Um caminho que fica
        # inteiro abaixo de 5.0 (3.0 -> 4.0) nao cruza a fronteira em nenhum
        # degrau, entao nenhuma das duas pode aparecer -- mesmo com os facts
        # (import SDK v1, config EMRFS) presentes no job.
        facts = _facts(tmp_path)
        resultado = assessment.assess(facts, source="3.0", target="4.0")
        rule_ids = {f.rule_id for f in resultado.findings}
        assert "SF-MIG-001" not in rule_ids
        assert "SF-MIG-002" not in rule_ids


class TestPropagaErroDoCaminho:
    def test_versao_desconhecida_propaga_o_erro_nomeado(self, tmp_path):
        # `assess` nao engole o erro de `version_path.steps`: um assessment
        # vazio para um par invalido pareceria "nenhum breaking change", nao
        # "o par nao pode nem ser avaliado".
        with pytest.raises(ValueError, match="fora da matriz"):
            assessment.assess(_facts(tmp_path), source="4.0", target="9.9")

    def test_alvo_anterior_a_origem_propaga_o_erro_nomeado(self, tmp_path):
        with pytest.raises(ValueError, match="alvo anterior"):
            assessment.assess(_facts(tmp_path), source="5.1", target="4.0")


class TestDuplicataEntreDegraus:
    def test_finding_cuja_faixa_cobre_dois_degraus_nasce_nos_dois(self, tmp_path):
        # DECISAO 1 (docstring de sparkforge/migration/assessment.py): duplicata
        # entre degraus e o comportamento pretendido, nao um bug a esconder.
        # SF-MIG-001 tem `runtime_scope: {glue: ">=5.0"}`, e o caminho 4.0->5.1
        # cruza dois degraus cujo ALVO satisfaz esse escopo (5.0 e 5.1): a
        # mesma evidencia (mesmo `mig.sdk_import`) produz um SF-MIG-001 em cada
        # um, e `findings` carrega os dois -- nao deduplicado.
        facts = _facts(tmp_path)
        resultado = assessment.assess(facts, source="4.0", target="5.1")
        ocorrencias = [f for f in resultado.findings if f.rule_id == "SF-MIG-001"]
        assert len(ocorrencias) == 2, ocorrencias

        degraus_do_achado = sorted(
            degrau for finding, degrau in resultado.by_step if finding.rule_id == "SF-MIG-001"
        )
        assert degraus_do_achado == [("4.0", "5.0"), ("5.0", "5.1")]


class TestParGenerico:
    def test_pares_diferentes_selecionam_regras_diferentes(self, tmp_path):
        facts = _facts(tmp_path)
        curto = assessment.assess(facts, source="5.0", target="5.1")
        longo = assessment.assess(facts, source="4.0", target="5.1")
        assert len(longo.steps) > len(curto.steps)
        assert len(longo.by_step) >= len(curto.by_step)

    def test_par_que_nao_cruza_a_faixa_nao_dispara_a_regra(self, tmp_path):
        # SF-MIG-001 declara `glue: ">=5.0"`. Um caminho que termina em 4.0 nao
        # cruza a faixa, entao a regra nao deve aparecer.
        facts = _facts(tmp_path)
        resultado = assessment.assess(facts, source="3.0", target="4.0")
        assert "SF-MIG-001" not in {f.rule_id for f in resultado.findings}

    def test_nenhum_par_de_versao_aparece_no_codigo_do_motor(self):
        import re
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "sparkforge" / "migration"
        proibido = re.compile(r'"[3-9]\.\d+"')
        # Excecao conhecida e restrita: `glue/analyzer.py` e o analisador antigo
        # que esta fase substitui (`source_runtime: str = "4.0"`,
        # `target_runtime: str = "5.1"`). O Task 11 decide o destino dele --
        # ele tem consumidor declarado (`sparkforge/migration/__init__.py`
        # reexporta `GlueMigrationAnalyzer`), entao nao e removido aqui. Este
        # teste cobre so os modulos que esta fase construiu: `version_path.py`,
        # `assessment.py` e qualquer irmao novo -- nao o pacote `migration`
        # inteiro, para nao esconder uma regressao futura atras de uma
        # excecao larga demais.
        excecoes = {Path("glue") / "analyzer.py"}
        ofensores = [
            str(p.relative_to(raiz))
            for p in raiz.rglob("*.py")
            if p.relative_to(raiz) not in excecoes
            and proibido.search(p.read_text(encoding="utf-8"))
        ]
        assert ofensores == [], f"par de versao embutido no motor: {ofensores}"
