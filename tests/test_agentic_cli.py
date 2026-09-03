"""Testes dos CLI commands agênticos."""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.adapters.cli import main
from sparkforge.agentic.blackboard import append_decision, init_blackboard
from sparkforge.agentic.models import Decision


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
            "---\n"
            "name: iceberg-performance-engineer\n"
            "description: Iceberg specialist\n"
            "---\n",
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
    def test_show_default_budget(self):
        exit_code = main(["budget", "show"])
        assert exit_code == 0


class TestAutonomyShow:
    @pytest.mark.parametrize("level", ["L0", "L1", "L2", "L3", "L4", "L5"])
    def test_show_each_level(self, level: str):
        exit_code = main(["autonomy", "show", "--level", level])
        assert exit_code == 0
