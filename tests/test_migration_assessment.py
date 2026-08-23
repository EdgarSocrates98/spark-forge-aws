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
    def test_sf_mig_003_fora_do_runtime_scope_nunca_produz_finding_no_caminho_3_0_a_5_1(
        self, tmp_path
    ):
        # O fact mig.ansi_risk existe (extrator ja o emite desde a Task 6), e
        # desde a Task 11 a regra que o julga (SF-MIG-003) tem
        # `runtime_scope: {glue: ">=6.0"}` real -- nao e mais `blocked_on`. O
        # caminho 3.0 -> 5.1 nunca cruza 6.0, entao nenhum degrau satisfaz o
        # escopo e a regra continua fora de `findings`, agora pela mesma
        # guarda de versao que `TestGuardaDeVersao` ja prova para SF-MIG-001/002
        # -- provar isso em CADA degrau do caminho, nao so num, e o que garante
        # que nenhuma mudanca futura em `runtime_scope` reintroduza o disparo
        # por acidente antes do degrau que a cruza (ver `TestParGenerico`
        # abaixo para o par que CRUZA a fronteira).
        facts = _facts_com_cast(tmp_path)
        resultado = assessment.assess(facts, source="3.0", target="5.1")
        assert resultado.steps, "caminho precisa ter ao menos um degrau"
        assert "SF-MIG-003" not in {f.rule_id for f in resultado.findings}
        assert "SF-MIG-003" not in {f.rule_id for f, _ in resultado.by_step}

    def test_sf_mig_003_dispara_no_degrau_que_cruza_glue_6_0(self, tmp_path):
        # O par positivo, no nivel do assessment multi-degrau: o caminho
        # 5.1 -> 6.0 tem um unico degrau, e o ALVO dele (6.0) satisfaz
        # `runtime_scope: {glue: ">=6.0"}`. Prova que a matriz confirmada na
        # Task 11 nao so existe -- ela alcanca o motor de migracao ponta a
        # ponta, nao so o `judge()` de runtime unico que o golden
        # `cast_sem_guarda_ansi_default` ja cobre.
        facts = _facts_com_cast(tmp_path)
        resultado = assessment.assess(facts, source="5.1", target="6.0")
        assert resultado.steps == [("5.1", "6.0")]
        rule_ids = {f.rule_id for f in resultado.findings}
        assert "SF-MIG-003" in rule_ids
        assert (("5.1", "6.0")) in {degrau for _, degrau in resultado.by_step}


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
        # Sem excecao: `glue/analyzer.py` foi apagado na fase H1, e com ele o
        # unico arquivo do pacote que carregava par de versao no codigo
        # (`source_runtime: str = "4.0"`, `target_runtime: str = "5.1"`). Se um
        # par voltar a aparecer aqui, e regressao -- versao mora no catalogo de
        # regras e no `runtime_scope`, nunca no motor.
        ofensores = [
            str(p.relative_to(raiz))
            for p in raiz.rglob("*.py")
            if proibido.search(p.read_text(encoding="utf-8"))
        ]
        assert ofensores == [], f"par de versao embutido no motor: {ofensores}"


class TestRelatorioDeduplica:
    """A outra metade de `TestDuplicataEntreDegraus`.

    As duas visoes convivem de proposito. `findings`/`by_step` respondem "isto
    ainda vale depois do proximo salto?", e por isso guardam a cardinalidade por
    degrau -- e a DECISAO 1 do modulo, e ela nao mudou. `report()` responde a
    pergunta de quem LE o relatorio: "quantos problemas eu tenho?". Mostrar o
    mesmo problema tres vezes porque o caminho tem tres degraus faz um
    assessment de 4.0 para 6.0 parecer tres vezes pior que o mesmo job de 5.1
    para 6.0, sem que nada de fato seja pior.
    """

    def test_o_mesmo_problema_aparece_uma_vez_so(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        no_relatorio = [r for r in resultado.report() if r.finding.rule_id == "SF-MIG-001"]
        assert len(no_relatorio) == 1

    def test_a_cardinalidade_por_degrau_continua_intacta(self, tmp_path):
        """Deduplicar no relatorio nao pode custar a informacao que `by_step`
        carrega -- se custasse, seria a DECISAO 1 revogada pela porta dos fundos."""
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert len([f for f in resultado.findings if f.rule_id == "SF-MIG-001"]) == 2

    def test_o_relatorio_diz_em_que_degraus_o_problema_vale(self, tmp_path):
        """Deduplicar sem dizer onde vale trocaria ruido por perda: quem le
        precisa saber que o breaking change sobrevive ao proximo salto."""
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        entrada = next(r for r in resultado.report() if r.finding.rule_id == "SF-MIG-001")
        assert entrada.steps == [("4.0", "5.0"), ("5.0", "5.1")]

    def test_dois_imports_no_mesmo_arquivo_ja_sao_um_achado_so_antes_daqui(self, tmp_path):
        """Medido, nao suposto: o motor ja emite UM `SF-MIG-001` para dois
        imports de SDK v1 no mesmo arquivo, citando os dois facts como
        evidencia. A deduplicacao do relatorio nao tem nada a fazer aqui -- e
        importa saber disso, porque a alternativa (achar que o relatorio e quem
        colapsa) mandaria alguem procurar o bug no lugar errado no dia em que a
        contagem parecesse baixa demais."""
        (tmp_path / "job.py").write_text(
            "import com.amazonaws.services.s3.AmazonS3\n"
            "import com.amazonaws.services.dynamodbv2.AmazonDynamoDB\n",
            encoding="utf-8",
        )
        facts = facts_migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        resultado = assessment.assess(facts, source="4.0", target="5.1")
        por_degrau = [f for f in resultado.findings if f.rule_id == "SF-MIG-001"]
        assert len(por_degrau) == 2, "um por degrau, nao um por import"
        assert len(por_degrau[0].evidence) == 2, "os dois imports na mesma evidencia"

    def test_problemas_com_evidencia_distinta_nao_colapsam(self):
        """A chave de deduplicacao NAO e `rule_id`. Dois achados da mesma regra
        sustentados por facts DIFERENTES sao dois problemas, e colapsa-los
        esconderia um -- o oposto exato do que a deduplicacao existe para fazer.

        Montado direto, pelo mesmo motivo do teste de severidade abaixo: o que
        se fixa aqui e a chave, e amarra-la a uma regra especifica faria o teste
        morrer quando aquela regra mudasse de forma.
        """
        from sparkforge.findings.models import Finding

        def _finding(linha: int, fact_id: str) -> Finding:
            return Finding(
                rule_id="SF-MIG-001",
                title="import de SDK v1",
                severity="P1",
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "job.py", "line": linha},
                evidence=[fact_id],
            )

        primeiro, segundo = _finding(1, "f_aaa111"), _finding(9, "f_bbb222")
        resultado = assessment.MigrationAssessment(
            source="4.0",
            target="5.1",
            steps=[("4.0", "5.0"), ("5.0", "5.1")],
            findings=[primeiro, segundo, primeiro, segundo],
            by_step=[
                (primeiro, ("4.0", "5.0")),
                (segundo, ("4.0", "5.0")),
                (primeiro, ("5.0", "5.1")),
                (segundo, ("5.0", "5.1")),
            ],
        )
        relatorio = resultado.report()
        assert len(relatorio) == 2
        assert {r.finding.subject["line"] for r in relatorio} == {1, 9}
        assert all(r.steps == [("4.0", "5.0"), ("5.0", "5.1")] for r in relatorio)

    def test_a_ordem_do_relatorio_segue_a_de_findings(self, tmp_path):
        """`findings` ja passou por `sort_findings` -- por severidade, de forma
        determinista. O relatorio herda essa ordem em vez de inventar outra."""
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        vistos: list[str] = []
        for finding in resultado.findings:
            if finding.rule_id not in vistos:
                vistos.append(finding.rule_id)
        assert [r.finding.rule_id for r in resultado.report()] == vistos

    def test_to_dict_traz_as_tres_visoes(self, tmp_path):
        d = assessment.assess(_facts(tmp_path), source="4.0", target="5.1").to_dict()
        assert {"findings", "by_step", "report"} <= set(d)
        assert len(d["report"]) < len(d["findings"])
        assert d["report"][0]["steps"] == [["4.0", "5.0"], ["5.0", "5.1"]]


class TestRelatorioMantemAPiorSeveridade:
    def test_a_instancia_mais_severa_ganha(self):
        """Uma regra com `severity_by` condicionado ao runtime pode nascer P2
        num degrau e P1 no seguinte. Reportar a primeira subestimaria o risco
        pelo unico motivo de a ordem do caminho ser essa.

        Monta o `MigrationAssessment` direto em vez de procurar no catalogo uma
        regra com esse formato: o comportamento a fixar e o da deduplicacao, e
        amarra-lo a uma regra especifica faria o teste morrer no dia em que
        aquela regra mudasse de forma, sem que nada aqui tivesse quebrado.
        """
        from sparkforge.findings.models import Finding

        def _finding(severidade: str) -> Finding:
            return Finding(
                rule_id="SF-MIG-001",
                title="mesmo problema",
                severity=severidade,
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "job.py", "line": 1},
                evidence=["f_abc123"],
            )

        leve, grave = _finding("P2"), _finding("P1")
        resultado = assessment.MigrationAssessment(
            source="4.0",
            target="5.1",
            steps=[("4.0", "5.0"), ("5.0", "5.1")],
            findings=[grave, leve],
            by_step=[(leve, ("4.0", "5.0")), (grave, ("5.0", "5.1"))],
        )
        (entrada,) = resultado.report()
        assert entrada.finding.severity == "P1"
        assert entrada.steps == [("4.0", "5.0"), ("5.0", "5.1")]


class TestEixosNomeados:
    """A secao 32 do prompt nomeia etapas que o contrato nao tinha.

    A regra que governou quais entraram: gate sem produtor e gate que ninguem
    preenche, e um gate que nunca muda de valor e decoracao. `lakeformation`
    tem produtor (`SF-LF` sobre `tf.attribute`) e `consumidor` tem produtor
    (`SF-ENV` sobre `env.consumer`). `iam_kms`, `rede` e `cross_account` nao tem
    nenhum -- entram BLOCKED com a evidencia que os preencheria, que e diferente
    de fingir que passaram.
    """

    def test_eixo_sem_produtor_nasce_blocked_com_evidencia_nomeada(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        for nome in ("iam_kms", "rede", "cross_account"):
            assert resultado.gates[nome] == "BLOCKED", nome
            assert resultado.missing_evidence[nome], f"{nome} sem evidencia nomeada"

    def test_lakeformation_sem_terraform_e_blocked_nunca_pass(self, tmp_path):
        # So codigo Python nos facts: a topologia de FGAC e declarada no
        # Terraform, entao o eixo nao foi avaliado -- nao passou.
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.gates["lakeformation"] == "BLOCKED"
        assert resultado.missing_evidence["lakeformation"]

    def test_consumidor_sem_inventario_e_blocked_nunca_pass(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.gates["consumidor"] == "BLOCKED"
        assert resultado.missing_evidence["consumidor"]

    def test_toda_evidencia_faltante_corresponde_a_um_gate_blocked(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        for nome in resultado.missing_evidence:
            assert resultado.gates[nome] == "BLOCKED", (
                f"{nome} declara evidencia faltante mas nao esta bloqueado"
            )


class TestEixoNomeadoNaoSomaDuasVezes:
    """Um finding conta em UM eixo, nunca em dois.

    Sem isto, `compatibilidade` absorveria tudo e o eixo nomeado seria
    decorativo para o veredito -- o mesmo achado moveria os dois.
    """

    @staticmethod
    def _facts_com_fgac_e_jar(tmp_path):
        from sparkforge.migration import collect as collect_mod

        (tmp_path / "job.py").write_text(JOB, encoding="utf-8")
        (tmp_path / "infra.tf").write_text(
            'resource "aws_glue_job" "curated" {\n'
            "  default_arguments = {\n"
            '    "--enable-lakeformation-fine-grained-access" = "true"\n'
            '    "--extra-jars"                               = "s3://b/c.jar"\n'
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        return collect_mod.collect(tmp_path)

    def test_finding_de_lake_formation_move_o_eixo_dele(self, tmp_path):
        resultado = assessment.assess(
            self._facts_com_fgac_e_jar(tmp_path), source="5.1", target="6.0"
        )
        assert "SF-LF-001" in {f.rule_id for f in resultado.findings}
        assert resultado.gates["lakeformation"] == "FAIL"
        assert resultado.recommendation == "NO_GO"

    def test_o_mesmo_finding_nao_move_compatibilidade(self, tmp_path):
        # O caminho 5.1->6.0 nao cruza a faixa de SF-MIG-001 (`>=5.0` ja valia
        # em 5.1, e o fact de import de SDK v1 continua ali) -- entao o que
        # sobra em `compatibilidade` e o que NAO e de eixo nomeado.
        resultado = assessment.assess(
            self._facts_com_fgac_e_jar(tmp_path), source="5.1", target="6.0"
        )
        de_lf = [f for f in resultado.findings if f.rule_id.startswith("SF-LF-")]
        assert de_lf, "o cenario precisa ter finding de SF-LF para medir isto"
        outros = [f for f in resultado.findings if not f.rule_id.startswith("SF-LF-")]
        esperado = assessment._compatibility_gate(outros)
        assert resultado.gates["compatibilidade"] == esperado
