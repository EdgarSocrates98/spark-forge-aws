from __future__ import annotations

from sparkforge.context.context_tree import build_context_tree
from sparkforge.context.host_usage import HostTokenState


def test_context_tree_keeps_payload_and_provider_tokens_separate() -> None:
    tree = build_context_tree(
        {"capabilities": [{"name": "search"}], "context": [{"fact_id": "f1"}]},
        host_tokens=HostTokenState.from_transcript({"input_tokens": 10}, "run.jsonl"),
    )

    assert tree["unit"] == "serialized_utf8_json_bytes"
    assert tree["payload_bytes"] > 0
    assert tree["tokens"]["provider_tokens"] == {"input_tokens": 10}
    assert tree["tokens"]["tokens_unresolved"] is False
