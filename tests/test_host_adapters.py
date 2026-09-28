from __future__ import annotations

from pathlib import Path

from sparkforge.decision import ClaudeHostAdapter, CodexHostAdapter, DevinHostAdapter

ROOT = Path(__file__).resolve().parents[1]


def _raw(provider: str) -> dict:
    return {
        "case_id": f"{provider}-case",
        "contract_id": "kernel.synthetic",
        "contract_version": "1",
        "input": {"state": {"signal": "safe"}},
        "messages": [
            {"role": "user", "content": "route this"},
            {"role": "assistant", "content": "local"},
        ],
        "usage": {
            "input_tokens": 7,
            "output_tokens": 3,
        },
    }


def test_recorded_provider_adapters_replay_without_provider_calls():
    for adapter_type, provider in (
        (ClaudeHostAdapter, "claude"),
        (CodexHostAdapter, "codex"),
        (DevinHostAdapter, "devin"),
    ):
        result = adapter_type(ROOT).replay_provider_mapping(_raw(provider))
        assert result.case_id == f"{provider}-case"
        assert result.status == "accepted"
        assert result.provider_tokens == {
            "input_tokens": 7,
            "output_tokens": 3,
            "total_tokens": 10,
        }
        assert result.tokens_unresolved is False


def test_adapter_keeps_tokens_unresolved_without_recorded_usage():
    raw = _raw("claude")
    raw.pop("usage")
    result = ClaudeHostAdapter(ROOT).replay_provider_mapping(raw)
    assert result.status == "accepted"
    assert result.provider_tokens is None
    assert result.tokens_unresolved is True
