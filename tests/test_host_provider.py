from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.decision import DecisionStatus, ReplayHostAdapter, replay_host_mapping

ROOT = Path(__file__).resolve().parents[1]


def _cases() -> dict:
    return yaml.safe_load(
        (ROOT / "evals/token_efficient/fixtures/host_replay.yaml").read_text(
            encoding="utf-8"
        )
    )


def test_valid_host_replay_is_semantically_and_identity_deterministic() -> None:
    raw = _cases()["cases"][0]
    adapter = ReplayHostAdapter(ROOT)
    first = adapter.replay_mapping(raw)
    second = adapter.replay_mapping(raw)
    assert first.status == DecisionStatus.ACCEPTED.value
    assert first.semantic_result == second.semantic_result
    assert first.receipt_identity == second.receipt_identity
    assert first.provider_tokens == {"input_tokens": 23, "output_tokens": 11, "total_tokens": 34}
    assert first.tokens_unresolved is False


def test_invalid_host_envelope_is_named_refusal() -> None:
    raw = _cases()["cases"][1]
    result = ReplayHostAdapter(ROOT).replay_mapping(raw)
    assert result.status == DecisionStatus.REFUSED.value
    assert result.refusal_reason == "host_envelope_invalid:request.state"
    assert result.tokens_unresolved is True


def test_missing_usage_remains_unresolved_without_invalidating_result() -> None:
    raw = _cases()["cases"][2]
    result = ReplayHostAdapter(ROOT).replay_mapping(raw)
    assert result.status == DecisionStatus.ACCEPTED.value
    assert result.provider_tokens is None
    assert result.tokens_unresolved is True


def test_usage_transcript_hash_mismatch_never_attributes_provider_tokens() -> None:
    raw = dict(_cases()["cases"][0])
    raw["usage"] = dict(raw["usage"])
    raw["usage"]["transcript_sha256"] = "mismatched-transcript"
    result = ReplayHostAdapter(ROOT).replay_mapping(raw)
    assert result.status == DecisionStatus.ACCEPTED.value
    assert result.provider_tokens is None
    assert result.tokens_unresolved is True
    assert "usage_transcript_hash_mismatch" in result.unresolved


def test_decision_core_has_no_provider_or_mcp_sdk_imports() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "sparkforge/decision").glob("*.py")
    ).lower()
    for forbidden in ("anthropic", "openai", "bedrock", "litellm", "mcp"):
        assert forbidden not in source


def test_evaluation_core_has_no_provider_or_mcp_sdk_imports() -> None:
    import ast

    modules = []
    for path in (ROOT / "sparkforge/evals").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules.extend(
            node.module or node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.names
        )
        modules.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
    source = "\n".join(modules).lower()
    for forbidden in ("anthropic", "openai", "bedrock", "litellm", "mcp"):
        assert forbidden not in source


def test_replay_host_mapping_keeps_validation_at_adapter_boundary() -> None:
    raw = _cases()["cases"][1]
    result = replay_host_mapping(raw, ReplayHostAdapter(ROOT))

    assert result.status == DecisionStatus.REFUSED.value
    assert result.refusal_reason == "host_envelope_invalid:request.state"
