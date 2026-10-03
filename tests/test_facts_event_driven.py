from __future__ import annotations

from pathlib import Path

from sparkforge.facts.event_driven import extract_event_driven_path


ROOT = Path(__file__).resolve().parents[1]


def test_event_driven_extractor_preserves_dlq_and_targets():
    facts = extract_event_driven_path(
        ROOT / "fixtures/event_driven/rule_with_target/input/architecture.json"
    )
    queue = next(f for f in facts if f.kind == "sqs.queue")
    rule = next(f for f in facts if f.kind == "eventbridge.rule")
    assert queue.attrs["redrive_declared"] is True
    assert rule.measures["target_count"] == 1
    assert rule.attrs["dead_letter_declared"] is True


def test_event_driven_extractor_names_invalid_section():
    facts = extract_event_driven_path(
        ROOT / "fixtures/event_driven/invalid_artifact/input/architecture.json"
    )
    unresolved = [f for f in facts if f.kind == "event_driven.unresolved"]
    assert unresolved and unresolved[0].attrs["reason"] == "invalid_eventbridge_rules"
