from pathlib import Path

from sparkforge.agents import AgentResult, AgentSpec, Budget, ConversationRoom, Supervisor, select_context

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
    result = Supervisor(room, [agent], {"a": handler}, Budget(max_rounds=3, max_tokens=1)).run("goal")
    assert result["status"] == "blocked"
    assert result["decision"] == "token_budget_exhausted"
    assert any(row["kind"] == "decision" for row in room.records())
