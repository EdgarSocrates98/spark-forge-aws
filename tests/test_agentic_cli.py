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
