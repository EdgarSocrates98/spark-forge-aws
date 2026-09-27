from __future__ import annotations

from sparkforge.context.host_usage import HostTokenState


def test_host_usage_resolves_only_from_valid_transcript_values() -> None:
    state = HostTokenState.from_transcript(
        {"input_tokens": 12, "output_tokens": 8, "invalid": -1},
        "session.jsonl",
    )

    assert state.status == "resolved"
    assert state.usage == {"input_tokens": 12, "output_tokens": 8}
    assert state.to_dict()["tokens_unresolved"] is False


def test_host_usage_is_explicitly_unresolved_without_transcript() -> None:
    state = HostTokenState.from_transcript(None, None)

    assert state.status == "unresolved"
    assert state.to_dict() == {
        "status": "unresolved",
        "tokens_unresolved": True,
        "reason": "transcript_unavailable",
    }
