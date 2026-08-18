"""Bounded supervisor loop for SparkForge agents.

`Budget.max_rounds` limita QUANTAS FASES o loop executa, nao quantas passadas
completas ele faz sobre `PHASES` -- `run` faz exatamente uma passada e cobra uma
rodada por fase. O default acompanha `len(Supervisor.PHASES)` de proposito: com
um valor menor o loop nunca alcanca `decide` e todo caso volta `blocked` /
`budget_exhausted`, o que parece falta de evidencia e e so o orcamento acabando
antes do pipeline terminar. Quem quiser cortar o pipeline mais cedo baixa o
valor de proposito; quem nao mexer recebe a passada inteira.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .room import ConversationRoom

PHASES = ("observe", "plan", "dispatch", "debate", "verify", "synthesize", "decide")


@dataclass(frozen=True)
class Budget:
    max_rounds: int = len(PHASES)
    max_messages: int = 120
    max_tokens: int = 12000
    max_context_messages: int = 24


@dataclass
class AgentSpec:
    name: str
    role: str
    rule_areas: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    knowledge_refs: tuple[str, ...] = ()


@dataclass
class AgentResult:
    status: str
    content: dict[str, Any]
    tokens: int = 0
    refs: tuple[str, ...] = ()


Handler = Callable[[AgentSpec, dict[str, Any], list[dict[str, Any]]], AgentResult]


class Supervisor:
    PHASES = PHASES

    def __init__(
        self,
        room: ConversationRoom,
        agents: Iterable[AgentSpec],
        handlers: dict[str, Handler],
        budget: Budget | None = None,
    ):
        self.room = room
        self.agents = {agent.name: agent for agent in agents}
        self.handlers = handlers
        self.budget = budget or Budget()
        self.tokens_used = 0
        self.rounds = 0

    def _emit(
        self,
        author: str,
        kind: str,
        phase: str,
        content: dict[str, Any],
        refs: Iterable[str] = (),
    ) -> str:
        return self.room.append(author, kind, phase, content, refs)

    def run(self, goal: str, recommended_agents: list[str] | None = None) -> dict[str, Any]:
        selected = [
            self.agents[name]
            for name in (recommended_agents or list(self.agents))
            if name in self.agents
        ]
        if not selected:
            return {"status": "blocked", "reason": "no eligible agents"}
        self._emit(
            "supervisor",
            "task",
            "observe",
            {"goal": goal, "agents": [a.name for a in selected]},
        )
        state: dict[str, Any] = {"goal": goal, "results": [], "decision": None}
        for phase in self.PHASES:
            if (
                self.rounds >= self.budget.max_rounds
                or len(self.room.records()) >= self.budget.max_messages
            ):
                state["decision"] = "budget_exhausted"
                self._emit("supervisor", "decision", phase, state)
                return {"status": "blocked", **state}
            self.rounds += 1
            if phase == "dispatch":
                for agent in selected:
                    handler = self.handlers.get(agent.name)
                    if not handler:
                        continue
                    result = handler(
                        agent,
                        state,
                        self.room.context(
                            phase=phase,
                            limit=self.budget.max_context_messages,
                            query=goal,
                            token_budget=max(1, self.budget.max_tokens - self.tokens_used),
                        ),
                    )
                    self.tokens_used += result.tokens
                    if self.tokens_used > self.budget.max_tokens:
                        state["decision"] = "token_budget_exhausted"
                        self._emit("supervisor", "decision", phase, state)
                        return {"status": "blocked", **state}
                    state["results"].append(
                        {
                            "agent": agent.name,
                            "status": result.status,
                            "content": result.content,
                            "refs": list(result.refs),
                        }
                    )
                    self._emit(agent.name, "handoff", phase, result.content, result.refs)
            elif phase == "debate":
                self._emit(
                    "supervisor",
                    "challenge",
                    phase,
                    {
                        "instruction": "challenge unsupported claims and duplicate findings",
                        "result_count": len(state["results"]),
                    },
                )
            elif phase == "verify":
                verified = [
                    item for item in state["results"] if item["status"] in {"ok", "verified"}
                ]
                state["verified_count"] = len(verified)
                self._emit(
                    "verifier",
                    "fact",
                    phase,
                    {"verified_count": len(verified), "total": len(state["results"])},
                )
            elif phase == "synthesize":
                state["report"] = {
                    "goal": goal,
                    "evidence": state["results"],
                    "verified_count": state.get("verified_count", 0),
                }
                self._emit("synthesizer", "handoff", phase, state["report"])
            elif phase == "decide":
                state["decision"] = "ready" if state.get("verified_count", 0) else "needs_evidence"
                self._emit(
                    "supervisor",
                    "decision",
                    phase,
                    {"decision": state["decision"], "tokens_used": self.tokens_used},
                )
        return {
            "status": "completed",
            **state,
            "tokens_used": self.tokens_used,
            "rounds": self.rounds,
        }
