"""Unidade do executor de debate (`sparkforge/agentic/executor/debate_run.py`).

Os goldens de `tests/test_fixtures_golden_debate.py` cobrem desfecho e recusa
por fixture. Aqui ficam as garantias que nao cabem num rastro: o plano congelado
e o mesmo caminho do `arbitrate`, o `start` e idempotente, o id do debate nao
vira caminho arbitrario, a retomada depois de processo morto nao duplica
entidade, e o teto de rodadas vem do CASE e nunca do default de `DebateBudget`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.agentic.blackboard import (
    append_claim,
    append_objection,
    init_blackboard,
    read_claims,
    read_decisions,
)
from sparkforge.agentic.budget import case_budget_from_case, debate_rounds_from_budget
from sparkforge.agentic.executor import debate_run as dr
from sparkforge.agentic.executor.plan import debate_plan
from sparkforge.agentic.executor.run import open_debate_plans, run_executor
from sparkforge.agentic.models import Claim, ClaimType, Objection
from sparkforge.case.store import SCHEMA_VERSION, save_case

RAIZ = Path(__file__).resolve().parents[1]
UNIAO = (
    RAIZ / "fixtures" / "graph" / "import_sem_jar_no_iac" / "expected",
    RAIZ / "fixtures" / "infra_code" / "fgac_com_jar_extra" / "expected",
)
REGRAS = ("SF-GRAPH-005", "SF-LF-001")
RUNTIME = {"glue": "5.0", "spark": "3.5.4"}
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


def _uniao() -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    facts: list[dict] = []
    for pasta in UNIAO:
        findings += json.loads((pasta / "findings.json").read_text(encoding="utf-8"))
        facts += json.loads((pasta / "facts.json").read_text(encoding="utf-8"))
    return findings, facts


def _case(raiz: Path, budget: dict | None = BUDGET) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    caso = {"schema_version": SCHEMA_VERSION, "case_id": "debate-unit"}
    if budget is not None:
        caso["budget"] = budget
    save_case(caso, raiz)
    return raiz


def _start(raiz: Path, regras=REGRAS, facts: list[dict] | None = None) -> dict:
    findings, uniao = _uniao()
    return dr.start(raiz, findings, uniao if facts is None else facts, RUNTIME, regras)


# --------------------------------------------------------------------------
# O plano congelado
# --------------------------------------------------------------------------


class TestOPlanoEOMesmoDoArbitrate:
    def test_open_debate_plans_devolve_os_planos_do_run_executor(self, tmp_path):
        """Mesmo caminho, e nao copia: o plano congelado e o que o `arbitrate` emite."""
        findings, facts = _uniao()
        calculado = open_debate_plans(findings, facts, RUNTIME, BUDGET)
        gravado = run_executor(findings, facts, tmp_path / "repo", runtime=RUNTIME, budget=BUDGET)
        assert calculado == gravado["debate_plans"]
        assert [p["rules"] for p in calculado] == [list(REGRAS)]

    def test_open_debate_plans_nao_grava_nada(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        findings, facts = _uniao()
        open_debate_plans(findings, facts, RUNTIME, BUDGET)
        assert list(tmp_path.iterdir()) == []

    def test_start_nao_grava_a_saida_do_arbitrate(self, tmp_path):
        """`start` recalcula; ele nao escreve claim, evidencia nem trace."""
        raiz = _case(tmp_path / "case")
        assert _start(raiz)["status"] == "started"
        assert not (raiz / ".sparkforge" / "blackboard").exists()


class TestStart:
    def test_at001_start_cria_o_estado_e_next_devolve_o_brief_do_lado_a(self, tmp_path):
        raiz = _case(tmp_path / "case")
        saida = _start(raiz)
        assert saida["status"] == "started" and saida["created"] is True
        plano = json.loads(
            (raiz / saida["state_dir"] / "plan.json").read_text(encoding="utf-8")
        )
        assert plano["debate_id"] == saida["debate_id"]
        assert plano["max_rounds"] == 3
        assert "f_55f5ac" in plano["union_fact_ids"]

        brief = dr.next_step(raiz, saida["debate_id"])["brief"]
        assert (brief["side"], brief["round"], brief["rounds_remaining"]) == ("A", 1, 3)
        assert brief["defends"]["rule_id"] == "SF-GRAPH-005"
        assert brief["opposes"]["rule_id"] == "SF-LF-001"
        assert brief["defends"]["anchor_fact_ids"] == ["f_32bc0d", "f_d9303b"]
        assert set(brief["submission_schema"]) >= {"side", "round", "claims", "objections"}

    def test_at002_sem_budget_recusa_e_nao_grava_nada(self, tmp_path):
        raiz = _case(tmp_path / "case", budget=None)
        saida = _start(raiz)
        assert saida["status"] == "refused" and saida["reason"] == dr.BUDGET_UNDECLARED
        assert not (raiz / ".sparkforge" / "debate").exists()

    def test_sem_case_yaml_tambem_e_budget_undeclared(self, tmp_path):
        saida = _start(tmp_path)
        assert saida["reason"] == dr.BUDGET_UNDECLARED

    def test_max_rounds_fora_da_faixa_nomeia_a_chave(self, tmp_path):
        raiz = _case(tmp_path / "case", budget={"max_debates": 1, "max_rounds": 11})
        saida = _start(raiz)
        assert saida["reason"] == dr.BUDGET_UNDECLARED
        assert "max_rounds" in saida["detail"]

    def test_start_e_idempotente_para_o_mesmo_plano(self, tmp_path):
        raiz = _case(tmp_path / "case")
        primeiro, segundo = _start(raiz), _start(raiz)
        assert primeiro["debate_id"] == segundo["debate_id"]
        assert (primeiro["created"], segundo["created"]) == (True, False)

    def test_outro_plano_para_o_mesmo_par_e_recusado(self, tmp_path):
        raiz = _case(tmp_path / "case")
        _start(raiz)
        _findings, facts = _uniao()
        menos_um = [f for f in facts if f["id"] != "f_7d812c"]
        saida = _start(raiz, facts=menos_um)
        assert saida["reason"] == dr.DEBATE_EXISTS_OTHER_PLAN

    def test_o_id_do_debate_e_o_hash_do_plano(self, tmp_path):
        raiz = _case(tmp_path / "case")
        saida = _start(raiz)
        plano = json.loads((raiz / saida["state_dir"] / "plan.json").read_text(encoding="utf-8"))
        del plano["debate_id"]
        assert saida["debate_id"] == "dbt_" + dr._sha1(dr._canonico(plano))[:8]


# --------------------------------------------------------------------------
# O id nao vira caminho, e a vez sai dos arquivos
# --------------------------------------------------------------------------


class TestIdDoDebate:
    @pytest.mark.parametrize("debate_id", ["../../etc", "dbt_ZZZZZZZZ", "", "dbt_1234567"])
    def test_id_malformado_e_debate_not_found(self, tmp_path, debate_id):
        raiz = _case(tmp_path / "case")
        assert dr.next_step(raiz, debate_id)["reason"] == dr.DEBATE_NOT_FOUND
        assert dr.submit(raiz, debate_id, {})["reason"] == dr.DEBATE_NOT_FOUND


class TestRetomada:
    def test_recusa_nao_move_o_brief(self, tmp_path):
        raiz = _case(tmp_path / "case")
        debate_id = _start(raiz)["debate_id"]
        antes = dr.next_step(raiz, debate_id)
        assert dr.submit(raiz, debate_id, {"side": "B", "round": 1})["status"] == "refused"
        assert dr.next_step(raiz, debate_id) == antes

    def test_submissoes_anteriores_sao_rotuladas_como_nao_confiaveis(self, tmp_path):
        raiz = _case(tmp_path / "case")
        debate_id = _start(raiz)["debate_id"]
        dr.submit(raiz, debate_id, {"side": "A", "round": 1, "claims": [A1]})
        brief = dr.next_step(raiz, debate_id)["brief"]
        assert brief["prior_submissions"]
        assert all(s["untrusted_content"] is True for s in brief["prior_submissions"])

    def test_processo_morto_antes_do_commit_nao_duplica_entidade(self, tmp_path):
        """A submissao e o commit: entidade gravada sem ela e pulada no reenvio."""
        raiz = _case(tmp_path / "case")
        debate_id = _start(raiz)["debate_id"]
        payload = {"side": "A", "round": 1, "claims": [A1]}
        assert dr.submit(raiz, debate_id, payload)["status"] == "accepted"

        arquivo = raiz / ".sparkforge" / "debate" / debate_id / "submissions.jsonl"
        arquivo.write_text("", encoding="utf-8")  # o processo morreu antes desta linha

        assert dr.submit(raiz, debate_id, payload)["status"] == "accepted"
        assert len(read_claims(raiz)) == 1


# --------------------------------------------------------------------------
# Fechamento
# --------------------------------------------------------------------------


def _debate_com_vencedor(raiz: Path) -> str:
    debate_id = _start(raiz)["debate_id"]
    a = dr.submit(raiz, debate_id, {"side": "A", "round": 1, "claims": [A1]})
    b = dr.submit(
        raiz,
        debate_id,
        {
            "side": "B",
            "round": 1,
            "claims": [B1],
            "objections": [
                {
                    "target_claim": a["entities"]["claims"][0],
                    "statement": "sob FGAC o JAR adicional e bloqueado",
                    "evidence_refs": ["f_55f5ac"],
                }
            ],
        },
    )
    dr.submit(
        raiz,
        debate_id,
        {
            "side": "A",
            "round": 2,
            "concede": True,
            "rebuttals": [
                {
                    "target_objection": b["entities"]["objections"][0],
                    "statement": "concedo: FGAC declarado no mesmo job",
                    "evidence_refs": ["f_55f5ac"],
                }
            ],
        },
    )
    dr.submit(raiz, debate_id, {"side": "B", "round": 2})
    return debate_id


class TestFechamento:
    def test_done_e_sempre_o_mesmo(self, tmp_path):
        raiz = _case(tmp_path / "case")
        debate_id = _debate_com_vencedor(raiz)
        primeiro = dr.next_step(raiz, debate_id)
        assert primeiro["status"] == "done" and primeiro["winner_rule"] == "SF-LF-001"
        assert dr.next_step(raiz, debate_id) == primeiro
        assert len(read_decisions(raiz)) == 1

    def test_vence_depois_do_arbitrate_no_mesmo_case(self, tmp_path):
        """As claims do executor (inference, com evidencia) nao impedem o vencedor."""
        raiz = _case(tmp_path / "case")
        findings, facts = _uniao()
        run_executor(findings, facts, raiz, runtime=RUNTIME, budget=BUDGET)
        debate_id = _debate_com_vencedor(raiz)
        done = dr.next_step(raiz, debate_id)
        assert (done["outcome"], done["referee"]["upheld"]) == ("winner", True)

    def test_objecao_viva_de_outra_fonte_no_case_impede_o_vencedor(self, tmp_path):
        """Consequencia declarada: o referee le o blackboard INTEIRO do case."""
        raiz = _case(tmp_path / "case")
        init_blackboard(raiz)
        alheia = Claim(
            claimant="outra-fonte",
            claim_type=ClaimType.INFERENCE,
            statement="afirmacao de fora do debate",
            evidence_refs=["f_32bc0d"],
        )
        append_claim(alheia, raiz)
        append_objection(
            Objection(target_claim=alheia.id, objector="outra", statement="nao respondida"),
            raiz,
        )
        debate_id = _debate_com_vencedor(raiz)
        done = dr.next_step(raiz, debate_id)
        assert done["candidate"]["winner_rule"] == "SF-LF-001"
        assert done["outcome"] == "unresolved"
        assert done["referee"]["upheld"] is False

    def test_decisao_nunca_sai_high_nem_aplica_mudanca(self, tmp_path):
        raiz = _case(tmp_path / "case")
        done = dr.next_step(raiz, _debate_com_vencedor(raiz))
        assert done["decision"]["confidence"] in {"medium", "low"}
        assert done["decision"]["rollback"].strip()
        assert done["autonomy"]["applied_changes"] is False


# --------------------------------------------------------------------------
# O teto de rodadas vem do case
# --------------------------------------------------------------------------


class TestTetoDeRodadas:
    def test_budget_aceita_max_rounds_e_valida_a_faixa(self):
        assert case_budget_from_case({"budget": {"max_rounds": 3}}) is not None
        for invalido in (0, 11, True, "3"):
            with pytest.raises(ValueError, match="max_rounds"):
                case_budget_from_case({"budget": {"max_rounds": invalido}})

    def test_sem_a_chave_nao_ha_teto_e_nao_ha_default(self):
        assert debate_rounds_from_budget({"max_debates": 1}) is None
        assert debate_rounds_from_budget(None) is None

    def test_plano_publica_o_teto_declarado_e_o_criterio_de_parada(self):
        plano = debate_plan(["SF-GLUE-001"], {}, {"max_debates": 1, "max_rounds": 2})
        assert plano["rounds"] == {"status": "declared", "max_rounds": 2}
        assert "max_rounds = 2" in plano["stop_criteria"]
