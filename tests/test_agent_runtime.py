from pathlib import Path

from sparkforge.agents import (
    ConversationRoom,
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
