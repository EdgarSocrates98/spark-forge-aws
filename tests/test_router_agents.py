# tests/test_router_agents.py
"""Escolher coordenador e consulta, nao julgamento.

Manter os 3 agentes antigos e acrescentar 3 novos cria dois vocabularios --
risco levantado e aceito ao decidir F4-D2. A tabela e o que o neutraliza:
a mesma coisa que `next_step` fez com a escolha de skill.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "rules" / "catalog" / "routing.yaml"
AGENTS = ROOT / "agents"


def _routing() -> dict:
    return yaml.safe_load(ROUTING.read_text(encoding="utf-8"))


def _agent_routes() -> list[dict]:
    return [r for r in _routing()["rules"] if r.get("recommended_agent")]


class TestAgentRoutes:
    def test_there_is_at_least_one_route_per_coordinator(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        routed = {r["recommended_agent"] for r in _agent_routes()}
        missing = sorted(coordinators - routed)
        assert not missing, f"coordenadores sem rota: {missing}"

    def test_every_routed_agent_exists(self):
        coordinators = {p.stem for p in AGENTS.glob("*.md")}
        for route in _agent_routes():
            assert route["recommended_agent"] in coordinators, route["id"]

    def test_agent_routes_have_id_and_reason(self):
        for route in _agent_routes():
            assert route["id"].startswith("AGENT-"), route
            assert route.get("reason"), route["id"]

    def test_agent_route_ids_are_unique(self):
        ids = [r["id"] for r in _agent_routes()]
        assert len(ids) == len(set(ids))
