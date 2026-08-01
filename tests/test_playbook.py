"""O espelho de orquestracao para plataforma sem despacho de subagente.

Devin, Codex e Copilot nao despacham subagente -- isso e capacidade de harness,
nao conteudo deste repositorio. O playbook emite a MESMA decomposicao em
sequencia. Perde o paralelismo; mantem o metodo, as fronteiras negativas e a
ordem.

O teste que importa e o de FIDELIDADE: se o playbook divergir dos executores
que o coordenador declara, ele vira prosa que envelhece -- exatamente o que a
decisao F4-D4 rejeitou ao escolher verbo em vez de documento.
"""
from pathlib import Path

import pytest
import yaml

from sparkforge.case.playbook import build_playbook

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"


def _coordinators() -> list[str]:
    return sorted(p.stem for p in AGENTS.glob("*.md"))


def _declared_executors(name: str) -> list[str]:
    block = (AGENTS / f"{name}.md").read_text(encoding="utf-8").split("---", 2)[1]
    return (yaml.safe_load(block) or {}).get("executors") or []


class TestFidelity:
    @pytest.mark.parametrize("name", _coordinators())
    def test_steps_match_the_declared_executors(self, name):
        """O invariante que impede o espelho de virar prosa."""
        playbook = build_playbook(name, case={})
        assert [s["executor"] for s in playbook["steps"]] == _declared_executors(name)

    @pytest.mark.parametrize("name", _coordinators())
    def test_every_step_carries_the_negative_boundary(self, name):
        """Sem a fronteira negativa, quem seguir o playbook vira coordenador
        disfarcado e a decomposicao perde o sentido."""
        for step in build_playbook(name, case={})["steps"]:
            assert step["does_not"], step["executor"]


class TestDeterminism:
    def test_same_input_twice_yields_identical_output(self):
        first = build_playbook("spark-performance-architect", case={"phase": "diagnosis"})
        second = build_playbook("spark-performance-architect", case={"phase": "diagnosis"})
        assert first == second


class TestErrors:
    def test_unknown_coordinator_is_an_actionable_error(self):
        with pytest.raises(ValueError) as excinfo:
            build_playbook("nao-existe", case={})
        message = str(excinfo.value)
        assert "nao-existe" in message
        assert "spark-performance-architect" in message, "erro deve listar os validos"
