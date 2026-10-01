"""Opt-in translators for recorded Claude, Codex and Devin host envelopes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sparkforge.decision.fingerprint import digest
from sparkforge.decision.host import HostReplayResult, ReplayHostAdapter


class RecordedHostAdapter(ReplayHostAdapter):
    """Normalize one recorded host format before local deterministic replay."""

    provider_name = "recorded"
    message_keys = ("turns", "messages", "transcript")

    def replay_provider_mapping(self, raw: Mapping[str, Any]) -> HostReplayResult:
        return self.replay_mapping(self.normalize_mapping(raw))

    def normalize_mapping(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        turns = _first_value(raw, self.message_keys)
        normalized_turns = _turns(turns)
        request = raw.get("request")
        if not isinstance(request, Mapping):
            request = _request(raw)
        case_id = str(raw.get("case_id", f"{self.provider_name}-recorded"))
        contract_id = str(raw.get("contract_id", ""))
        contract_version = str(raw.get("contract_version", ""))
        canonical = {
            "schema_version": 1,
            "case_id": case_id,
            "contract_id": contract_id,
            "contract_version": contract_version,
            "request": dict(request),
            "turns": normalized_turns,
        }
        transcript_hash = str(raw.get("transcript_hash", "")).strip() or digest(canonical)
        usage = _usage(raw.get("usage"), raw, transcript_hash)
        return {
            "schema_version": 1,
            "case_id": case_id,
            "contract_id": contract_id,
            "contract_version": contract_version,
            "request": dict(request),
            "transcript_hash": transcript_hash,
            "turns": normalized_turns,
            "usage": usage,
            "cost_basis": (
                dict(raw["cost_basis"])
                if isinstance(raw.get("cost_basis"), Mapping)
                else None
            ),
        }


class ClaudeHostAdapter(RecordedHostAdapter):
    provider_name = "claude"
    message_keys = ("turns", "messages", "content", "transcript")


class CodexHostAdapter(RecordedHostAdapter):
    provider_name = "codex"
    message_keys = ("turns", "messages", "response", "transcript")


class DevinHostAdapter(RecordedHostAdapter):
    provider_name = "devin"
    message_keys = ("turns", "messages", "transcript", "events")


def _first_value(raw: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return value
    return []


def _request(raw: Mapping[str, Any]) -> dict[str, Any]:
    candidate = raw.get("input") or raw.get("request_body") or raw.get("state")
    if isinstance(candidate, Mapping) and isinstance(candidate.get("state"), Mapping):
        return dict(candidate)
    if isinstance(candidate, Mapping):
        return {"state": dict(candidate)}
    return {}


def _turns(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    turns: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        role = item.get("role", item.get("speaker", "assistant"))
        content = item.get("content", item.get("text", item.get("message", "")))
        if isinstance(content, list):
            content = "".join(
                str(block.get("text", ""))
                for block in content
                if isinstance(block, Mapping)
            )
        if isinstance(content, Mapping):
            content = content.get("text", content.get("value", ""))
        turns.append({"role": str(role), "content": str(content)})
    return turns


def _usage(raw_usage: Any, raw: Mapping[str, Any], transcript_hash: str) -> dict[str, Any] | None:
    usage = raw_usage
    if not isinstance(usage, Mapping):
        response = raw.get("response")
        usage = response.get("usage") if isinstance(response, Mapping) else None
    if not isinstance(usage, Mapping):
        return None
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    if input_tokens is None or output_tokens is None:
        return None
    return {
        "provider_tokens": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "transcript_sha256": str(usage.get("transcript_sha256", transcript_hash)),
    }


__all__ = [
    "ClaudeHostAdapter",
    "CodexHostAdapter",
    "DevinHostAdapter",
    "RecordedHostAdapter",
]
