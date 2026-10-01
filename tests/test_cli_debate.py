"""`sparkforge debate start|next|submit` e as tres tools MCP, ponta a ponta.

A maquina de estados ja tem unidade (`test_agentic_debate_run.py`) e goldens
(`test_fixtures_golden_debate.py`). O que fica aqui e a CASCA: que a CLI e o MCP
chegam ao mesmo modulo pelos mesmos insumos do `arbitrate` -- findings e a
UNIAO dos facts lidos de arquivo, com o `id` recomputado pelo conteudo --, que a
recusa nomeada atravessa as duas superficies sem traducao, e que so erro de
FRONTEIRA (arquivo ausente, JSON invalido) vira exit != 0.

O caso e o da regra 29: `fixtures/graph/import_sem_jar_no_iac` unida a
`fixtures/infra_code/fgac_com_jar_extra`, o unico par do catalogo que
`direct_conflicts` produz (`SF-GRAPH-005` x `SF-LF-001`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import _DEBATE_REFUSAL_REASONS, TOOLS, call_tool
from sparkforge.agentic.blackboard import read_decisions
from sparkforge.agentic.executor import debate_evidence, debate_run
from sparkforge.case.store import SCHEMA_VERSION, save_case

RAIZ = Path(__file__).resolve().parents[1]
UNIAO = (
    RAIZ / "fixtures" / "graph" / "import_sem_jar_no_iac" / "expected",
    RAIZ / "fixtures" / "infra_code" / "fgac_com_jar_extra" / "expected",
)
REGRAS = "SF-GRAPH-005,SF-LF-001"
TRES = ("sparkforge_debate_start", "sparkforge_debate_next", "sparkforge_debate_submit")
BUDGET = {"max_debates": 1, "max_rounds": 3}

A1 = {
    "claim_type": "inference",
    "statement": "o job importa GraphFrames e o IaC nao entrega o JAR",
    "evidence_refs": ["f_32bc0d", "f_d9303b"],
    "confidence": "high",
}
B1 = {
    "claim_type": "inference",
    "statement": "o job declara FGAC e JAR adicional no mesmo aws_glue_job",
    "evidence_refs": ["f_55f5ac", "f_6ab9b2"],
    "confidence": "medium",
}


def _run(argv: list[str], capsys) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, (json.loads(out) if out.strip() else {})


@pytest.fixture()
def caso(tmp_path: Path) -> dict:
    """Um case com `budget:` declarado e os insumos do `arbitrate` em arquivo."""
    repo = tmp_path / "case"
    repo.mkdir()
    save_case(
        {"schema_version": SCHEMA_VERSION, "case_id": "debate-cli", "budget": BUDGET}, repo
    )
    findings: list[dict] = []
    for pasta in UNIAO:
        findings += json.loads((pasta / "findings.json").read_text(encoding="utf-8"))
    findings_path = tmp_path / "findings.json"
    findings_path.write_text(json.dumps(findings), encoding="utf-8")
    return {
        "repo": repo,
        "tmp": tmp_path,
        "findings": findings_path,
        "facts": [pasta / "facts.json" for pasta in UNIAO],
    }


def _start_argv(caso: dict) -> list[str]:
    argv = ["debate", "start", "--repo", str(caso["repo"]), "--rules", REGRAS]
    argv += ["--findings", str(caso["findings"]), "--glue", "5.0"]
    for facts in caso["facts"]:
        argv += ["--facts", str(facts)]
    return argv


def _submit(caso: dict, debate_id: str, payload: dict, capsys, nome: str) -> tuple[int, dict]:
    arquivo = caso["tmp"] / f"{nome}.json"
    arquivo.write_text(json.dumps(payload), encoding="utf-8")
    return _run(
        [
            "debate",
            "submit",
            "--repo",
            str(caso["repo"]),
            "--debate",
            debate_id,
            "--file",
            str(arquivo),
        ],
        capsys,
    )


def _next(caso: dict, debate_id: str, capsys) -> tuple[int, dict]:
    return _run(
        ["debate", "next", "--repo", str(caso["repo"]), "--debate", debate_id], capsys
    )


# --------------------------------------------------------------------------
# Ponta a ponta pela CLI
# --------------------------------------------------------------------------


class TestDebatePelaCli:
    def test_start_congela_o_plano_e_e_idempotente(self, caso, capsys):
        code, primeiro = _run(_start_argv(caso), capsys)
        assert code == 0
        assert primeiro["status"] == "started" and primeiro["created"] is True
        assert primeiro["rules"] == ["SF-GRAPH-005", "SF-LF-001"]
        assert primeiro["max_rounds"] == 3
        assert (caso["repo"] / primeiro["state_dir"] / "plan.json").is_file()

        code, segundo = _run(_start_argv(caso), capsys)
        assert code == 0
        assert segundo["debate_id"] == primeiro["debate_id"]
        assert segundo["created"] is False

    def test_facts_de_arquivo_sao_a_uniao_com_o_id_recomputado(self, caso, capsys):
        """A claim cita `f_55f5ac`, que so existe na SEGUNDA fixture: com um
        `--facts` so, a mesma submissao seria `dangling_evidence_ref`."""
        _, started = _run(_start_argv(caso), capsys)
        plano = json.loads(
            (caso["repo"] / started["state_dir"] / "plan.json").read_text(encoding="utf-8")
        )
        assert {"f_32bc0d", "f_d9303b", "f_55f5ac", "f_6ab9b2"} <= set(plano["union_fact_ids"])

    def test_debate_inteiro_fecha_com_vencedor_pelo_referee(self, caso, capsys):
        _, started = _run(_start_argv(caso), capsys)
        debate_id = started["debate_id"]

        code, passo = _next(caso, debate_id, capsys)
        assert code == 0 and passo["status"] == "brief"
        assert (passo["brief"]["side"], passo["brief"]["round"]) == ("A", 1)
        assert passo["brief"]["defends"]["rule_id"] == "SF-GRAPH-005"

        _, a = _submit(caso, debate_id, {"side": "A", "round": 1, "claims": [A1]}, capsys, "a1")
        assert a["status"] == "accepted"
        assert a["next"]["brief"]["side"] == "B"

        objecao = {
            "target_claim": a["entities"]["claims"][0],
            "statement": "sob FGAC o JAR adicional e bloqueado",
            "evidence_refs": ["f_55f5ac"],
        }
        _, b = _submit(
            caso,
            debate_id,
            {"side": "B", "round": 1, "claims": [B1], "objections": [objecao]},
            capsys,
            "b1",
        )
        assert b["status"] == "accepted"
        assert b["next"]["brief"]["open_objections_against_you"] == b["entities"]["objections"]

        replica = {
            "target_objection": b["entities"]["objections"][0],
            "statement": "concedo: FGAC declarado no mesmo job",
            "evidence_refs": ["f_55f5ac"],
        }
        _, a2 = _submit(
            caso,
            debate_id,
            {"side": "A", "round": 2, "concede": True, "rebuttals": [replica]},
            capsys,
            "a2",
        )
        assert a2["status"] == "accepted"

        _, b2 = _submit(caso, debate_id, {"side": "B", "round": 2}, capsys, "b2")
        assert b2["status"] == "accepted"
        done = b2["next"]
        assert done["status"] == "done"
        assert (done["outcome"], done["winner_rule"]) == ("winner", "SF-LF-001")
        assert done["closed_by"] == "consensus"
        assert done["referee"]["upheld"] is True
        assert done["autonomy"] == {"level": "L0", "applied_changes": False}

        # `next` depois do fechamento devolve sempre o mesmo `done`, e o
        # blackboard tem UMA decisao -- que o `referee` rodado depois aceita.
        _, de_novo = _next(caso, debate_id, capsys)
        assert de_novo == done
        assert len(read_decisions(caso["repo"])) == 1
        _, veredito = _run(["debate", "referee", "--repo", str(caso["repo"])], capsys)
        assert veredito["upheld"] is True

        _, fechado = _submit(caso, debate_id, {"side": "A", "round": 3}, capsys, "tarde")
        assert fechado["reason"] == debate_run.DEBATE_CLOSED


# --------------------------------------------------------------------------
# Recusa nomeada e erro de fronteira
# --------------------------------------------------------------------------


class TestRecusaEFronteira:
    def test_recusa_sai_nomeada_com_exit_zero_e_nao_move_o_estado(self, caso, capsys):
        """Fora da vez: `out_of_turn`, exit 0, e o brief seguinte e o mesmo."""
        _, started = _run(_start_argv(caso), capsys)
        debate_id = started["debate_id"]
        _, antes = _next(caso, debate_id, capsys)

        code, recusa = _submit(
            caso, debate_id, {"side": "B", "round": 1, "claims": [B1]}, capsys, "fora"
        )
        assert code == 0
        assert recusa == {
            "status": "refused",
            "reason": debate_run.OUT_OF_TURN,
            "detail": recusa["detail"],
        }
        _, depois = _next(caso, debate_id, capsys)
        assert depois == antes

    def test_fact_citado_fora_da_uniao_e_recusado(self, caso, capsys):
        _, started = _run(_start_argv(caso), capsys)
        claim = {**A1, "evidence_refs": ["f_000000"]}
        _, recusa = _submit(
            caso, started["debate_id"], {"side": "A", "round": 1, "claims": [claim]}, capsys, "x"
        )
        assert recusa["reason"] == debate_run.DANGLING_EVIDENCE_REF

    def test_sem_budget_no_case_recusa_budget_undeclared(self, caso, capsys):
        save_case({"schema_version": SCHEMA_VERSION, "case_id": "sem-budget"}, caso["repo"])
        code, recusa = _run(_start_argv(caso), capsys)
        assert code == 0
        assert recusa["reason"] == debate_run.BUDGET_UNDECLARED
        assert not (caso["repo"] / ".sparkforge" / "debate").exists()

    def test_debate_inexistente_e_debate_not_found(self, caso, capsys):
        code, recusa = _next(caso, "../../etc", capsys)
        assert code == 0 and recusa["reason"] == debate_run.DEBATE_NOT_FOUND

    def test_arquivo_de_submissao_ausente_e_erro_de_fronteira(self, caso, capsys):
        _, started = _run(_start_argv(caso), capsys)
        argv = ["debate", "submit", "--repo", str(caso["repo"])]
        argv += ["--debate", started["debate_id"], "--file", str(caso["tmp"] / "nada.json")]
        assert main(argv) == 2
        assert "sparkforge debate next" in capsys.readouterr().err

    def test_json_invalido_e_erro_de_fronteira(self, caso, capsys):
        _, started = _run(_start_argv(caso), capsys)
        arquivo = caso["tmp"] / "quebrado.json"
        arquivo.write_text("{nao e json", encoding="utf-8")
        argv = ["debate", "submit", "--repo", str(caso["repo"])]
        argv += ["--debate", started["debate_id"], "--file", str(arquivo)]
        assert main(argv) == 2

    def test_json_que_nao_e_objeto_e_recusa_do_protocolo(self, caso, capsys):
        """Forma e do executor: `[]` chega a ele e sai `invalid_schema`."""
        _, started = _run(_start_argv(caso), capsys)
        arquivo = caso["tmp"] / "lista.json"
        arquivo.write_text("[]", encoding="utf-8")
        argv = ["debate", "submit", "--repo", str(caso["repo"])]
        argv += ["--debate", started["debate_id"], "--file", str(arquivo)]
        code, recusa = _run(argv, capsys)
        assert code == 0 and recusa["reason"] == debate_run.INVALID_SCHEMA

    def test_findings_ausente_e_erro_de_fronteira(self, caso, capsys):
        caso = {**caso, "findings": caso["tmp"] / "nao-existe.json"}
        assert main(_start_argv(caso)) == 2


# --------------------------------------------------------------------------
# A superficie MCP e a mesma
# --------------------------------------------------------------------------


class TestMcpEACli:
    def test_mcp_chega_ao_mesmo_debate_e_ao_mesmo_brief(self, caso, capsys):
        _, pela_cli = _run(_start_argv(caso), capsys)
        pelo_mcp = call_tool(
            "sparkforge_debate_start",
            {
                "repo": str(caso["repo"]),
                "rules": ["SF-GRAPH-005", "SF-LF-001"],
                "findings_path": str(caso["findings"]),
                "facts_path": [str(p) for p in caso["facts"]],
                "glue": "5.0",
            },
        )
        assert pelo_mcp["debate_id"] == pela_cli["debate_id"]
        assert pelo_mcp["created"] is False

        debate_id = pela_cli["debate_id"]
        _, brief_cli = _next(caso, debate_id, capsys)
        brief_mcp = call_tool(
            "sparkforge_debate_next", {"repo": str(caso["repo"]), "debate_id": debate_id}
        )
        assert brief_mcp == brief_cli

    def test_submit_inline_pelo_mcp_passa_a_recusa_sem_traducao(self, caso, capsys):
        _, started = _run(_start_argv(caso), capsys)
        recusa = call_tool(
            "sparkforge_debate_submit",
            {
                "repo": str(caso["repo"]),
                "debate_id": started["debate_id"],
                "submission": {"side": "A", "round": 1, "claims": [{**A1, "evidence_refs": []}]},
            },
        )
        assert recusa["status"] == "refused"
        assert recusa["reason"] == debate_run.CLAIM_WITHOUT_EVIDENCE

    def test_as_tres_tools_sao_local_mutation(self):
        from sparkforge.agents.autonomy import ToolClass, tool_class

        for nome in TRES:
            assert tool_class(nome) is ToolClass.LOCAL_MUTATION, nome

    def test_as_descricoes_dizem_que_nada_aqui_gera_argumento(self):
        for nome in TRES:
            descricao = TOOLS[nome]["description"].lower()
            assert "provider" in descricao, nome
            assert "host" in descricao, nome

    def test_o_enum_de_recusas_e_o_conjunto_das_constantes(self):
        """A lista literal de `tools.py` e as constantes dos dois modulos sao o
        MESMO conjunto: recusa nova sem entrada no schema derruba este teste, e
        nao o cliente que valida a resposta.

        Recusa e reconhecida pela FORMA do valor (`snake_case` com ao menos um
        `_`): nome de arquivo, diretorio, agente e a opcao `unresolved` nao tem
        essa forma, e nenhuma lista de exclusao precisa crescer junto.
        """
        import re

        forma = re.compile(r"^[a-z]+(?:_[a-z]+)+$")
        constantes = {
            valor
            for modulo in (debate_run, debate_evidence)
            for nome, valor in vars(modulo).items()
            if nome.isupper() and isinstance(valor, str) and forma.match(valor)
        }
        assert constantes == set(_DEBATE_REFUSAL_REASONS)
