"""Testes dos CLI commands agênticos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters.cli import main
from sparkforge.agentic.blackboard import append_decision, init_blackboard
from sparkforge.agentic.models import Decision
from sparkforge.case.store import new_case, save_case


class TestAgentsList:
    def test_list_agents(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "spark-performance-architect.md").write_text(
            "---\n"
            "name: spark-performance-architect\n"
            "description: Spark performance architect\n"
            "---\n",
            encoding="utf-8",
        )
        (agents_dir / "iceberg-performance-engineer.md").write_text(
            "---\nname: iceberg-performance-engineer\ndescription: Iceberg specialist\n---\n",
            encoding="utf-8",
        )

        exit_code = main(["agents", "list", "--repo", str(tmp_path)])
        assert exit_code == 0

    def test_list_empty(self, tmp_path: Path):
        exit_code = main(["agents", "list", "--repo", str(tmp_path)])
        assert exit_code == 0


class TestAgentsInspect:
    def test_inspect_existing(self, tmp_path: Path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "test-agent.md").write_text("# Test Agent", encoding="utf-8")

        exit_code = main(["agents", "inspect", "--repo", str(tmp_path), "--id", "test-agent"])
        assert exit_code == 0

    def test_inspect_nonexistent(self, tmp_path: Path):
        exit_code = main(["agents", "inspect", "--repo", str(tmp_path), "--id", "nonexistent"])
        assert exit_code == 1


class TestBlackboardSummary:
    def test_empty_blackboard(self, tmp_path: Path):
        init_blackboard(tmp_path)
        exit_code = main(["blackboard", "summary", "--repo", str(tmp_path)])
        assert exit_code == 0

    def test_with_data(self, tmp_path: Path):
        init_blackboard(tmp_path)
        d = Decision(
            problem="test",
            options=["a"],
            selected_option="a",
            rollback="revert a",
        )
        append_decision(d, tmp_path)

        exit_code = main(["blackboard", "summary", "--repo", str(tmp_path)])
        assert exit_code == 0


class TestBlackboardList:
    def test_list_decisions(self, tmp_path: Path):
        init_blackboard(tmp_path)
        d = Decision(
            problem="test problem",
            options=["a", "b"],
            selected_option="a",
            rollback="revert a",
        )
        append_decision(d, tmp_path)

        exit_code = main(["blackboard", "list", "--repo", str(tmp_path), "--type", "decisions"])
        assert exit_code == 0

    def test_list_claims_empty(self, tmp_path: Path):
        init_blackboard(tmp_path)
        exit_code = main(["blackboard", "list", "--repo", str(tmp_path), "--type", "claims"])
        assert exit_code == 0


class TestDecisionsList:
    def test_list_empty(self, tmp_path: Path):
        exit_code = main(["decisions", "list", "--repo", str(tmp_path)])
        assert exit_code == 0


class TestBudgetShow:
    """`budget show` le o case, e nunca devolve default do codigo como estado.

    Ate 2026-09-03 este verbo imprimia `CaseBudget()` -- `tokens_used: 0`,
    `status: within` -- sem case nenhum e sem nenhuma marca de que o numero
    era de fabrica. Estes testes fixam as tres saidas possiveis: sem case
    falha, case sem bloco `budget:` sai `unresolved`, case com bloco sai
    `declared` com os valores DELE.
    """

    @staticmethod
    def _abrir_case(root: Path, budget: dict | None = None) -> None:
        case = new_case(
            case_id="case_teste",
            created_at="2026-09-03T00:00:00+00:00",
            runtime={"glue": "5.0"},
            repo=str(root),
        )
        if budget is not None:
            case["budget"] = budget
        save_case(case, root)

    def test_sem_case_falha_em_vez_de_inventar(self, tmp_path: Path, capsys):
        exit_code = main(["budget", "show", "--repo", str(tmp_path)])
        assert exit_code == 1
        assert "case ausente" in capsys.readouterr().err

    def test_template_e_rotulado_como_template(self, capsys):
        exit_code = main(["budget", "show", "--template"])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "template"
        assert "NAO e o estado de nenhum case" in payload["note"]
        assert payload["limits"]["max_total_tokens"] == 50000

    def test_case_sem_bloco_budget_sai_unresolved(self, tmp_path: Path, capsys):
        self._abrir_case(tmp_path)
        exit_code = main(["budget", "show", "--repo", str(tmp_path)])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["limits"]["status"] == "unresolved"
        assert "budget" in payload["limits"]["reason"]
        # Nenhum default do codigo vaza como se fosse limite do case.
        assert "max_total_tokens" not in payload["limits"]

    def test_case_com_bloco_budget_sai_declarado(self, tmp_path: Path, capsys):
        self._abrir_case(tmp_path, budget={"max_total_tokens": 1234, "max_agents": 2})
        exit_code = main(["budget", "show", "--repo", str(tmp_path)])
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["limits"]["status"] == "declared"
        assert payload["limits"]["max_total_tokens"] == 1234
        assert payload["limits"]["max_agents"] == 2
        assert payload["case_id"] == "case_teste"

    def test_consumo_sai_unresolved_e_aponta_onde_e_medido(self, tmp_path: Path, capsys):
        self._abrir_case(tmp_path)
        main(["budget", "show", "--repo", str(tmp_path)])
        consumo = json.loads(capsys.readouterr().out)["consumption"]
        assert consumo["status"] == "unresolved"
        assert "economy report" in consumo["payload_bytes"]
        assert "tokens_unresolved" in consumo["tokens"]
        assert "cost_basis" in consumo["cost_usd"]

    def test_bloco_budget_invalido_falha_nomeando_a_chave(self, tmp_path: Path, capsys):
        self._abrir_case(tmp_path, budget={"max_tokens_totais": 10})
        exit_code = main(["budget", "show", "--repo", str(tmp_path)])
        assert exit_code == 1
        assert "max_tokens_totais" in capsys.readouterr().err


class TestAutonomyShow:
    @pytest.mark.parametrize("level", ["L0", "L1", "L2", "L3", "L4", "L5"])
    def test_show_each_level(self, level: str):
        exit_code = main(["autonomy", "show", "--level", level])
        assert exit_code == 0

# --------------------------------------------------------------------------
# arbitrate -- o executor agentico ganha superficie
# --------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parents[1]

# O par REAL do catalogo: `SF-GRAPH-005` manda declarar o jar de GraphFrames em
# `--extra-jars`, `SF-LF-001` manda remove-lo porque a AWS nao oferece modo de
# FGAC que aceite JAR adicional. Um job que usa GraphFrames e tem controle de
# acesso fino dispara as duas, e elas sao incompativeis por limitacao de
# plataforma DOCUMENTADA -- e o unico caso de contradicao direta que a secao
# 12.4 do spec mediu no catalogo inteiro.
FIXTURE_GRAPH = RAIZ / "fixtures" / "graph" / "import_sem_jar_no_iac"
FIXTURE_FGAC = RAIZ / "fixtures" / "infra_code" / "fgac_com_jar_extra"

# O runtime da secao 12.8, fixo pelo mesmo motivo: runtime diferente muda o
# escopo de versao, e com ele a confianca da claim.
RUNTIME = ["--glue", "5.0", "--spark", "3.5.4"]


def _json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _escreve(destino: Path, conteudo) -> Path:
    destino.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return destino


def _par_real(tmp_path: Path) -> tuple[Path, list[Path]]:
    """Findings e facts do par contraditorio real, tirados de duas fixtures.

    Duas fixtures e nao uma: o par existe entre AREAS, e nenhuma fixture do
    corpus dispara as duas regras sozinha. Unir os dois lados e o que constroi
    o case que a contradicao descreve -- um job que usa GraphFrames num
    ambiente com FGAC.
    """
    findings = _escreve(
        tmp_path / "findings.json",
        _json(FIXTURE_GRAPH / "expected" / "findings.json")
        + _json(FIXTURE_FGAC / "expected" / "findings.json"),
    )
    facts = [
        _escreve(tmp_path / "facts_graph.json", _json(FIXTURE_GRAPH / "expected" / "facts.json")),
        _escreve(tmp_path / "facts_fgac.json", _json(FIXTURE_FGAC / "expected" / "facts.json")),
    ]
    return findings, facts


def _par_que_fecha(tmp_path: Path) -> tuple[Path, Path]:
    """Um par cuja arbitragem FECHA, e por que ele e sintetico.

    Medido: o par real do catalogo sai `recommendation: experiment` -- as duas
    regras citam documentacao oficial da AWS e o que esta medido no case nao
    separa uma da outra. O desfecho e correto, mas com ele so nenhum teste
    sobre `Decision` -- nem sobre `decisions list`/`explain` lendo o que o
    verbo gravou -- exercitaria coisa alguma. Lastro desigual e o que abre o
    ramo.
    """
    findings = _escreve(
        tmp_path / "findings_fecha.json",
        [
            {
                "rule_id": "SF-GLUE-001",
                "title": "Capacidade insuficiente para o SLA declarado",
                "subject": {"type": "job", "symbol": "etl_pedidos"},
                "evidence": ["f_run001"],
                "runtime_scope": {},
                "sources": [
                    {
                        "url": "https://docs.aws.amazon.com/glue/latest/dg/add-job.html",
                        "retrieved": "2026-08-01",
                    },
                    {
                        "url": "https://spark.apache.org/docs/latest/tuning.html",
                        "retrieved": "2026-08-01",
                    },
                ],
                "action": {
                    "kind": "capacity.increase_workers",
                    "target": "glue.number_of_workers",
                    "direction": "increase",
                    "requires_absent": [],
                    "moves": [],
                    "depends_on": [],
                },
                "validation": ["contagem total antes e depois"],
                "risks": ["o custo por execucao sobe junto com o numero de workers"],
            },
            {
                "rule_id": "SF-WASTE-001",
                "title": "Capacidade ociosa medida",
                "subject": {"type": "job", "symbol": "etl_pedidos"},
                "evidence": ["f_ausente"],
                "runtime_scope": {},
                "sources": [],
                "action": {
                    "kind": "capacity.reduce_workers",
                    "target": "glue.number_of_workers",
                    "direction": "decrease",
                    "requires_absent": [],
                    "moves": [],
                    "depends_on": [],
                },
                "validation": [],
                "risks": [],
            },
        ],
    )
    facts = _escreve(
        tmp_path / "facts_fecha.json",
        [
            {
                "kind": "glue.job_run",
                "subject": {"type": "job_run", "symbol": "jr_0001"},
                "measures": {},
                "attrs": {},
                "provenance": {},
                "id": "f_run001",
            }
        ],
    )
    return findings, facts


class TestArbitrate:
    """`sparkforge arbitrate` -- a superficie do executor agentico.

    Ate esta entrega a camada agentica era biblioteca inerte: `blackboard
    summary` devolvia zero em tudo num repositorio de trabalho porque nenhum
    verbo escrevia `Claim`, `Evidence` ou `Decision`. Estes testes cobram o
    contrario -- que existe UM verbo que escreve, e que os verbos de leitura
    que ja existiam passam a ler o que ele gravou.
    """

    def test_o_verbo_grava_o_blackboard_que_antes_era_zero(self, tmp_path: Path, capsys):
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        assert main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)]) == 0
        pacote = json.loads(capsys.readouterr().out)

        assert pacote["kind"] == "executor.run"
        assert pacote["persisted"] is True
        assert pacote["claims"], "o par real parou de produzir claim"

        assert main(["blackboard", "summary", "--repo", str(repo)]) == 0
        resumo = json.loads(capsys.readouterr().out)
        assert resumo["claims"] == len(pacote["claims"])
        assert resumo["evidence"] == len(pacote["evidence"])
        assert resumo["contradictions"] == len(pacote["contradictions"])
        # O que este teste existe para provar: deixou de ser zero.
        assert resumo["claims"] > 0

    def test_a_contradicao_real_do_catalogo_sai_com_o_par_nomeado(
        self, tmp_path: Path, capsys
    ):
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        pacote = json.loads(capsys.readouterr().out)

        pares = [sorted(c["rules"]) for c in pacote["contradictions"]]
        assert ["SF-GRAPH-005", "SF-LF-001"] in pares
        assert all(c["target"] == "glue.default_arguments" for c in pacote["contradictions"])

    def test_a_arbitragem_que_nao_fecha_devolve_plano_com_debate_unresolved(
        self, tmp_path: Path, capsys
    ):
        """O contrato que a descricao da tool declara: ela NAO executa debate.

        Sem executor de debate, o desfecho honesto e o plano com a lacuna
        nomeada -- nunca uma resolucao inventada para o par.
        """
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        pacote = json.loads(capsys.readouterr().out)

        assert pacote["debate_plans"], "o par real parou de pedir debate"
        for plano in pacote["debate_plans"]:
            assert plano["plan"]["executed"] is False
            assert plano["plan"]["unresolved"]["reason"] == "debate.unresolved"

    def test_o_score_de_arbitragem_nao_sai_na_resposta(self, tmp_path: Path, capsys):
        """Os pesos de `assess_claim` sao convencao sem calibracao: o valor
        absoluto nao e confianca medida e nao pode ser publicado como tal."""
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        texto = capsys.readouterr().out

        assert "confidence_score" not in texto
        assert "evidence_quality" not in texto
        assert "independence_score" not in texto

    def test_decisions_list_e_explain_leem_o_que_o_arbitrate_gravou(
        self, tmp_path: Path, capsys
    ):
        """A prova de que a camada deixou de ser biblioteca inerte.

        `decisions list` e `decisions explain` existiam antes desta entrega e
        liam um blackboard que ninguem preenchia.
        """
        findings, facts = _par_que_fecha(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags([facts], repo)])
        pacote = json.loads(capsys.readouterr().out)
        assert pacote["decisions"], "o par que fecha parou de fechar"
        decisao_id = pacote["decisions"][0]["id"]

        assert main(["decisions", "list", "--repo", str(repo)]) == 0
        listadas = json.loads(capsys.readouterr().out)
        assert listadas["blackboard_count"] == len(pacote["decisions"])
        assert decisao_id in {d["id"] for d in listadas["blackboard_decisions"]}

        assert main(["decisions", "explain", "--repo", str(repo), "--id", decisao_id]) == 0
        explicada = json.loads(capsys.readouterr().out)
        assert explicada["id"] == decisao_id
        assert explicada["rollback"].strip()

    def test_o_adr_e_gravado_dentro_do_repo(self, tmp_path: Path, capsys):
        findings, facts = _par_que_fecha(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags([facts], repo)])
        pacote = json.loads(capsys.readouterr().out)

        for caminho in pacote["persistence"]["adrs"]:
            arquivo = Path(caminho)
            assert arquivo.parent == repo / ".sparkforge" / "blackboard" / "adr"
            assert "## Rollback" in arquivo.read_text(encoding="utf-8")

    def test_aceita_a_lista_nua_e_o_objeto_embrulhado(self, tmp_path: Path, capsys):
        """As duas formas que o repositorio produz, e a saida e a mesma.

        `judge --out` grava a lista nua; parte do corpus grava o objeto com a
        chave do dominio. Desembrulhar a mao antes de chamar o verbo e onde o
        operador erra o conjunto -- que e o defeito da secao 12.9.
        """
        findings, facts = _par_real(tmp_path)
        repo_lista = tmp_path / "lista"
        repo_lista.mkdir()
        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo_lista)])
        pela_lista = json.loads(capsys.readouterr().out)

        embrulhado = _escreve(
            tmp_path / "findings_obj.json", {"findings": _json(findings)}
        )
        facts_obj = [
            _escreve(tmp_path / f"{p.stem}_obj.json", {"facts": _json(p)}) for p in facts
        ]
        repo_objeto = tmp_path / "objeto"
        repo_objeto.mkdir()
        main(["arbitrate", "--findings", str(embrulhado), *_flags(facts_obj, repo_objeto)])
        pelo_objeto = json.loads(capsys.readouterr().out)

        for chave in ("claims", "evidence", "contradictions", "unknowns", "debate_plans"):
            assert pela_lista[chave] == pelo_objeto[chave], chave

    def test_o_id_do_fact_sem_id_e_computado_pelo_conteudo(self, tmp_path: Path, capsys):
        """O `input/facts.json` de uma fixture nao carrega `id`.

        Sem recomputar, a claim citaria um `fact_id` ausente do conjunto e o
        gate de lastro a reprovaria por ausencia de medida -- uma lacuna que a
        execucao real nao tem.
        """
        from sparkforge.findings.models import Fact

        findings, facts = _par_real(tmp_path)
        crus = [{k: v for k, v in f.items() if k != "id"} for f in _json(facts[0])]
        sem_id = _escreve(tmp_path / "facts_sem_id.json", crus)
        esperados = {
            Fact(
                kind=f["kind"],
                subject=f["subject"],
                measures=f.get("measures") or {},
                attrs=f.get("attrs") or {},
                provenance=f.get("provenance") or {},
            ).id
            for f in crus
        }
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags([sem_id, facts[1]], repo)])
        pacote = json.loads(capsys.readouterr().out)

        citados = {ref for c in pacote["claims"] for ref in c["evidence_refs"]}
        assert citados & esperados, "nenhuma claim ancorou nos facts sem id declarado"

    def test_a_uniao_e_a_flag_repetida_e_nao_um_arquivo_so(self, tmp_path: Path, capsys):
        """Um subconjunto fabrica lacuna que a execucao real nao tem.

        Com so o lado do FGAC, os achados de GraphFrames perdem a ancora e
        viram `Unknown`. E o contrafactual da secao 12.9, medido aqui.
        """
        findings, facts = _par_real(tmp_path)
        repo_uniao = tmp_path / "uniao"
        repo_uniao.mkdir()
        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo_uniao)])
        completo = json.loads(capsys.readouterr().out)

        repo_parcial = tmp_path / "parcial"
        repo_parcial.mkdir()
        main(["arbitrate", "--findings", str(findings), *_flags([facts[1]], repo_parcial)])
        parcial = json.loads(capsys.readouterr().out)

        assert not completo["unknowns"]
        assert parcial["unknowns"], "o subconjunto deveria abrir lacuna"

    def test_o_runtime_efetivamente_usado_volta_na_resposta(self, tmp_path: Path, capsys):
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        pacote = json.loads(capsys.readouterr().out)

        assert pacote["runtime"]["glue"] == "5.0"
        assert pacote["runtime"]["spark"] == "3.5.4"
        assert "divergences" in pacote["runtime"]

    def test_o_verbo_declara_L0_e_que_nao_aplicou_mudanca(self, tmp_path: Path, capsys):
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        pacote = json.loads(capsys.readouterr().out)

        assert pacote["autonomy"]["level"] == "L0"
        assert pacote["autonomy"]["applied_changes"] is False

    def test_rodar_duas_vezes_nao_duplica_o_blackboard(self, tmp_path: Path, capsys):
        findings, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        capsys.readouterr()
        main(["arbitrate", "--findings", str(findings), *_flags(facts, repo)])
        pacote = json.loads(capsys.readouterr().out)

        main(["blackboard", "summary", "--repo", str(repo)])
        resumo = json.loads(capsys.readouterr().out)
        assert resumo["claims"] == len(pacote["claims"])
        assert pacote["persistence"]["skipped"]["claims"] == len(pacote["claims"])

    def test_findings_ausente_falha_com_o_comando_que_resolve(self, tmp_path: Path, capsys):
        _, facts = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        codigo = main(
            ["arbitrate", "--findings", str(tmp_path / "nao-existe.json"), *_flags(facts, repo)]
        )
        assert codigo == 2
        erro = capsys.readouterr().err
        assert "sparkforge judge" in erro

    def test_facts_ausente_falha_com_o_comando_que_resolve(self, tmp_path: Path, capsys):
        findings, _ = _par_real(tmp_path)
        repo = tmp_path / "repo"
        repo.mkdir()

        codigo = main(
            [
                "arbitrate",
                "--findings",
                str(findings),
                "--facts",
                str(tmp_path / "nao-existe.json"),
                "--repo",
                str(repo),
                *RUNTIME,
            ]
        )
        assert codigo == 2
        assert "sparkforge analyze pyspark" in capsys.readouterr().err

    def test_o_budget_do_plano_vem_do_case_e_nunca_do_default_do_codigo(
        self, tmp_path: Path, capsys
    ):
        """Regra 11: valor de fabrica nao e estado do case.

        Sem `case.yaml`, `budget` do plano sai `unresolved` nomeando a lacuna.
        Com o bloco declarado, saem os valores DELE.
        """
        findings, facts = _par_real(tmp_path)
        sem_case = tmp_path / "sem_case"
        sem_case.mkdir()
        main(["arbitrate", "--findings", str(findings), *_flags(facts, sem_case)])
        pacote = json.loads(capsys.readouterr().out)
        assert pacote["debate_plans"][0]["plan"]["budget"]["status"] == "unresolved"

        com_case = tmp_path / "com_case"
        com_case.mkdir()
        case = new_case(
            case_id="case_arbitrate",
            created_at="2026-09-08T00:00:00+00:00",
            runtime={"glue": "5.0"},
            repo=str(com_case),
        )
        case["budget"] = {"max_total_tokens": 4321, "max_agents": 2}
        save_case(case, com_case)
        main(["arbitrate", "--findings", str(findings), *_flags(facts, com_case)])
        pacote = json.loads(capsys.readouterr().out)
        limites = pacote["debate_plans"][0]["plan"]["budget"]
        assert limites["status"] == "declared"
        assert limites["max_total_tokens"] == 4321


def _flags(facts: list[Path], repo: Path) -> list[str]:
    """As flags de `--facts` repetido mais `--repo` e o runtime fixo."""
    argumentos: list[str] = []
    for caminho in facts:
        argumentos += ["--facts", str(caminho)]
    return [*argumentos, "--repo", str(repo), *RUNTIME]
