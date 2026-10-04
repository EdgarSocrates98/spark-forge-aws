"""Extract deterministic facts from event-driven AWS configuration dumps.

The extractor accepts saved JSON for EventBridge rules/Pipes, SQS queues and
SNS topics/subscriptions. It never calls AWS and keeps missing redrive, retry,
or target evidence unresolved instead of treating absence as a safe default.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "event_driven@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "eventbridge.rule",
        "eventbridge.pipe",
        "sqs.queue",
        "sns.topic",
        "sns.subscription",
        "event_driven.unresolved",
        "event_driven.analyzed",
    }
)


def _subject(artifact: str, line: int, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": artifact,
        "line": line,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _fact(
    kind: str,
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    *,
    attrs: dict[str, Any] | None = None,
    measures: dict[str, Any] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, line, symbol),
        attrs=attrs or {},
        measures=measures or {},
        provenance=provenance,
    )


def _unresolved(
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    reason: str,
    **attrs: Any,
) -> Fact:
    return _fact(
        "event_driven.unresolved",
        artifact,
        line,
        provenance,
        attrs={"reason": reason, **attrs},
    )


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _section(data: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return None


def _rules(
    data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]
) -> list[Fact]:
    raw = _section(data, "eventbridge_rules", "eventbridge", "rules")
    if isinstance(raw, dict):
        raw = raw.get("rules", raw.get("Rules"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        return [_unresolved(artifact, line, provenance, "invalid_eventbridge_rules")]
    facts: list[Fact] = []
    for item in raw:
        if not isinstance(item, dict):
            facts.append(_unresolved(artifact, line, provenance, "invalid_eventbridge_rule"))
            continue
        name = _text(item.get("name", item.get("Name")))
        if not name:
            facts.append(_unresolved(artifact, line, provenance, "eventbridge_rule_name_missing"))
            continue
        targets = _list(item.get("targets", item.get("Targets")))
        target_types = sorted(
            str(target.get("type", target.get("Type", "unknown"))).lower()
            for target in targets
            if isinstance(target, dict)
        )
        retry_declared = any(
            isinstance(target, dict)
            and isinstance(target.get("retry_policy", target.get("RetryPolicy")), dict)
            for target in targets
        )
        dlq_declared = any(
            isinstance(target, dict)
            and isinstance(target.get("dead_letter_config", target.get("DeadLetterConfig")), dict)
            for target in targets
        )
        attrs: dict[str, Any] = {
            "name": name,
            "state": _text(item.get("state", item.get("State"))) or "unknown",
            "target_types": target_types,
            "event_pattern_declared": isinstance(
                item.get("event_pattern", item.get("EventPattern")), (dict, str)
            ),
            "retry_declared": retry_declared,
            "dead_letter_declared": dlq_declared,
        }
        facts.append(
            _fact(
                "eventbridge.rule",
                artifact,
                line,
                provenance,
                attrs=attrs,
                measures={"target_count": len(targets)},
                symbol=name,
            )
        )
    return facts


def _pipes(
    data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]
) -> list[Fact]:
    raw = _section(data, "eventbridge_pipes", "pipes")
    if isinstance(raw, dict):
        raw = raw.get("pipes", raw.get("Pipes"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        return [_unresolved(artifact, line, provenance, "invalid_eventbridge_pipes")]
    facts: list[Fact] = []
    for item in raw:
        if not isinstance(item, dict):
            facts.append(_unresolved(artifact, line, provenance, "invalid_eventbridge_pipe"))
            continue
        name = _text(item.get("name", item.get("Name")))
        if not name:
            facts.append(_unresolved(artifact, line, provenance, "eventbridge_pipe_name_missing"))
            continue
        source = item.get("source", item.get("Source"))
        target = item.get("target", item.get("Target"))
        attrs = {
            "name": name,
            "state": _text(item.get("state", item.get("State"))) or "unknown",
            "source_type": _text(source.get("type"))
            if isinstance(source, dict)
            else _text(source) or "unknown",
            "target_type": _text(target.get("type"))
            if isinstance(target, dict)
            else _text(target) or "unknown",
            "enrichment_declared": item.get("enrichment") is not None,
        }
        facts.append(
            _fact("eventbridge.pipe", artifact, line, provenance, attrs=attrs, symbol=name)
        )
    return facts


def _queues(
    data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]
) -> list[Fact]:
    raw = _section(data, "sqs_queues", "sqs", "queues")
    if isinstance(raw, dict):
        raw = raw.get("queues", raw.get("Queues"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        return [_unresolved(artifact, line, provenance, "invalid_sqs_queues")]
    facts: list[Fact] = []
    for item in raw:
        if not isinstance(item, dict):
            facts.append(_unresolved(artifact, line, provenance, "invalid_sqs_queue"))
            continue
        name = _text(item.get("name", item.get("QueueName")))
        if not name:
            facts.append(_unresolved(artifact, line, provenance, "sqs_queue_name_missing"))
            continue
        redrive = item.get("redrive_policy", item.get("RedrivePolicy"))
        if isinstance(redrive, str):
            try:
                redrive = json.loads(redrive)
            except json.JSONDecodeError:
                redrive = None
        redrive_declared = isinstance(redrive, dict) and bool(
            redrive.get("deadLetterTargetArn", redrive.get("dead_letter_target_arn"))
        )
        fifo = _bool(item.get("fifo", item.get("FifoQueue")))
        attrs: dict[str, Any] = {
            "name": name,
            "fifo": fifo if fifo is not None else "unresolved",
            "redrive_declared": redrive_declared,
        }
        measures = {}
        visibility = item.get("visibility_timeout", item.get("VisibilityTimeout"))
        if isinstance(visibility, (int, float)) and not isinstance(visibility, bool):
            measures["visibility_timeout_seconds"] = visibility
        facts.append(
            _fact(
                "sqs.queue", artifact, line, provenance, attrs=attrs, measures=measures, symbol=name
            )
        )
    return facts


def _sns(data: dict[str, Any], artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    topics = _section(data, "sns_topics", "topics")
    subscriptions = _section(data, "sns_subscriptions", "subscriptions")
    if isinstance(topics, dict):
        topics = topics.get("topics", topics.get("Topics"))
    if isinstance(subscriptions, dict):
        subscriptions = subscriptions.get("subscriptions", subscriptions.get("Subscriptions"))
    facts: list[Fact] = []
    if topics is not None and not isinstance(topics, list):
        facts.append(_unresolved(artifact, line, provenance, "invalid_sns_topics"))
        topics = []
    for item in _list(topics):
        if not isinstance(item, dict):
            facts.append(_unresolved(artifact, line, provenance, "invalid_sns_topic"))
            continue
        name = _text(item.get("name", item.get("TopicArn")))
        if name:
            facts.append(
                _fact("sns.topic", artifact, line, provenance, attrs={"name": name}, symbol=name)
            )
        else:
            facts.append(_unresolved(artifact, line, provenance, "sns_topic_name_missing"))
    if subscriptions is not None and not isinstance(subscriptions, list):
        facts.append(_unresolved(artifact, line, provenance, "invalid_sns_subscriptions"))
        subscriptions = []
    for item in _list(subscriptions):
        if not isinstance(item, dict):
            facts.append(_unresolved(artifact, line, provenance, "invalid_sns_subscription"))
            continue
        topic = _text(item.get("topic", item.get("TopicArn")))
        protocol = _text(item.get("protocol", item.get("Protocol")))
        endpoint = _text(item.get("endpoint", item.get("Endpoint")))
        if not topic or not protocol:
            facts.append(
                _unresolved(artifact, line, provenance, "sns_subscription_identity_missing")
            )
            continue
        redrive = item.get("redrive_policy", item.get("RedrivePolicy"))
        facts.append(
            _fact(
                "sns.subscription",
                artifact,
                line,
                provenance,
                attrs={
                    "topic": topic,
                    "protocol": protocol,
                    "endpoint_type": endpoint.split(":", 1)[0] if endpoint else "unresolved",
                    "redrive_declared": isinstance(redrive, (dict, str)),
                },
                symbol=topic,
            )
        )
    return facts


def _extract_text(text: str, artifact: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return [_unresolved(artifact, exc.lineno, provenance, "invalid_json")]
    if not isinstance(value, dict):
        return [_unresolved(artifact, 1, provenance, "root_must_be_object")]
    facts: list[Fact] = []
    facts.extend(_rules(value, artifact, 1, provenance))
    facts.extend(_pipes(value, artifact, 1, provenance))
    facts.extend(_queues(value, artifact, 1, provenance))
    facts.extend(_sns(value, artifact, 1, provenance))
    if not facts:
        facts.append(_unresolved(artifact, 1, provenance, "no_supported_event_driven_section"))
    facts.append(
        _fact(
            "event_driven.analyzed",
            artifact,
            1,
            provenance,
            attrs={
                "sections": sorted(
                    {
                        fact.kind.split(".", 1)[0]
                        for fact in facts
                        if not fact.kind.endswith("unresolved")
                    }
                )
            },
            measures={"fact_count": len(facts)},
        )
    )
    return sort_facts(facts)


def extract_event_driven_path(
    path: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    target = Path(path)
    rel = str(target.relative_to(repo_root)) if repo_root else str(target)
    return _extract_text(target.read_text(encoding="utf-8"), rel.replace("\\", "/"))


def extract_event_driven_tree(
    root: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    base = Path(root)
    facts: list[Fact] = []
    for path in iter_source_files(base, "*.json"):
        facts.extend(extract_event_driven_path(path, repo_root=repo_root))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_event_driven_path",
    "extract_event_driven_tree",
]
