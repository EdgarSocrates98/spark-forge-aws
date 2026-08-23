from pathlib import Path

from sparkforge.agents import (
    AgentResult,
    AgentSpec,
    Budget,
    ConversationRoom,
    Supervisor,
    select_context,
)


def test_room_is_append_only_and_context_is_bounded(tmp_path: Path):
    room = ConversationRoom(tmp_path, "case-1", max_messages=5)
    first = room.append("a", "fact", "observe", {"fact": "spark"})
    room.append("b", "challenge", "debate", {"challenge": "verify"}, [first])
    assert len(room.records()) == 2
    assert len(room.context(limit=1)) == 1

def test_context_selection_deduplicates_and_preserves_decision():
    rows = [
        {"kind": "fact", "content": {"fact": "spark plan"}},
        {"kind": "fact", "content": {"fact": "spark plan"}},
        {"kind": "decision", "content": {"decision": "ready"}},
        {"kind": "noise", "content": {"text": "unrelated"}},
    ]
    selected = select_context(rows, "spark", 100)
    assert len(selected) == 3
    assert any(row["kind"] == "decision" for row in selected)
def test_supervisor_stops_on_budget_and_records_decision(tmp_path: Path):
    room = ConversationRoom(tmp_path, "case-2", max_messages=20)
    agent = AgentSpec("a", "tester")
    def handler(spec, state, context):
        return AgentResult("verified", {"fact": "ok"}, tokens=10)
    supervisor = Supervisor(room, [agent], {"a": handler}, Budget(max_rounds=3, max_tokens=1))
    result = supervisor.run("goal")
    assert result["status"] == "blocked"
    assert result["decision"] == "token_budget_exhausted"
    assert any(row["kind"] == "decision" for row in room.records())


def test_supervisor_completes_the_whole_pipeline_with_the_default_budget(tmp_path: Path):
    """O default de `Budget` tem que alcancar `decide`.

    Regressao: `max_rounds` cobra uma rodada por FASE e `PHASES` tem sete. Com
    o default anterior de 3, `run` voltava `blocked` / `budget_exhausted` na
    quarta fase para qualquer caso, sem nunca chamar `verify`, `synthesize` ou
    `decide` -- o consumidor lia falta de evidencia onde havia orcamento
    acabando cedo. Nenhum teste cobria o caminho completo, por isso o defeito
    era invisivel.
    """
    room = ConversationRoom(tmp_path, "case-3", max_messages=200)
    agent = AgentSpec("a", "tester")

    def handler(spec, state, context):
        return AgentResult("verified", {"fact": "ok"}, tokens=10)

    result = Supervisor(room, [agent], {"a": handler}).run("goal")
    assert result["status"] == "completed"
    assert result["decision"] == "ready"
    assert result["rounds"] == len(Supervisor.PHASES)
