"""Testes do Debate Engine."""

from __future__ import annotations

import pytest

from sparkforge.agentic.debate import (
    Debate,
    DebateBudget,
    DebateRound,
    DebateStatus,
    DebateTrigger,
    deadlock_resolution,
    should_trigger_debate,
)


class TestDebateBudget:
    def test_default_budget(self):
        b = DebateBudget()
        assert b.max_rounds == 3
        assert b.max_total_tokens == 8000

    def test_zero_rounds_raises(self):
        with pytest.raises(ValueError, match="max_rounds"):
            DebateBudget(max_rounds=0)

    def test_too_many_rounds_raises(self):
        with pytest.raises(ValueError, match="irracional"):
            DebateBudget(max_rounds=11)


class TestDebate:
    def test_id_deterministic(self):
        d1 = Debate(
            topic="Is broadcast join safe?",
            participants=["agent_a", "agent_b"],
            trigger=DebateTrigger.EVIDENCE_CONFLICT,
        )
        d2 = Debate(
            topic="Is broadcast join safe?",
            participants=["agent_a", "agent_b"],
            trigger=DebateTrigger.EVIDENCE_CONFLICT,
        )
        assert d1.id == d2.id
        assert d1.id.startswith("debate_")

    def test_single_participant_raises(self):
        with pytest.raises(ValueError, match="2 participantes"):
            Debate(
                topic="test",
                participants=["solo"],
                trigger=DebateTrigger.MANUAL,
            )

    def test_empty_topic_raises(self):
        with pytest.raises(ValueError, match="topic vazio"):
            Debate(
                topic="",
                participants=["a", "b"],
                trigger=DebateTrigger.MANUAL,
            )

    def test_budget_exhausted_by_rounds(self):
        d = Debate(
            topic="test",
            participants=["a", "b"],
            trigger=DebateTrigger.MANUAL,
            budget=DebateBudget(max_rounds=2),
        )
        d.rounds.append(DebateRound(round_number=1, tokens_used=100))
        d.rounds.append(DebateRound(round_number=2, tokens_used=100))
        assert d.budget_exhausted

    def test_budget_exhausted_by_tokens(self):
        d = Debate(
            topic="test",
            participants=["a", "b"],
            trigger=DebateTrigger.MANUAL,
            budget=DebateBudget(max_rounds=10, max_total_tokens=100),
        )
        d.rounds.append(DebateRound(round_number=1, tokens_used=60))
        d.rounds.append(DebateRound(round_number=2, tokens_used=50))
        assert d.budget_exhausted

    def test_to_dict(self):
        d = Debate(
            topic="test debate",
            participants=["a", "b"],
            trigger=DebateTrigger.LOW_CONFIDENCE,
        )
        d_dict = d.to_dict()
        assert d_dict["topic"] == "test debate"
        assert d_dict["trigger"] == "low_confidence"
        assert d_dict["status"] == "open"


class TestShouldTriggerDebate:
    def test_destructive_triggers(self):
        trigger = should_trigger_debate([], is_destructive=True)
        assert trigger == DebateTrigger.DESTRUCTIVE_ACTION

    def test_high_risk_triggers(self):
        trigger = should_trigger_debate([], is_high_risk=True)
        assert trigger == DebateTrigger.HIGH_RISK

    def test_production_impact_triggers(self):
        trigger = should_trigger_debate([], is_production_impact=True)
        assert trigger == DebateTrigger.PRODUCTION_IMPACT

    def test_evidence_conflict_triggers(self):
        trigger = should_trigger_debate([], has_evidence_conflict=True)
        assert trigger == DebateTrigger.EVIDENCE_CONFLICT

    def test_simple_task_no_trigger(self):
        trigger = should_trigger_debate(
            [],
            confidence="high",
            is_high_risk=False,
            is_destructive=False,
        )
        assert trigger is None

    def test_low_confidence_with_recommendation_triggers(self):
        findings = [{"proposed_change": ["change X"], "subject": {"a": 1}, "severity": "P2"}]
        trigger = should_trigger_debate(findings, confidence="low")
        assert trigger == DebateTrigger.LOW_CONFIDENCE

    def test_low_confidence_no_recommendation_no_trigger(self):
        findings = [{"proposed_change": [], "subject": {"a": 1}, "severity": "P2"}]
        trigger = should_trigger_debate(findings, confidence="low")
        assert trigger is None

    def test_contradictory_findings_trigger(self):
        findings = [
            {"subject": {"job": "x"}, "severity": "P1", "proposed_change": []},
            {"subject": {"job": "x"}, "severity": "P3", "proposed_change": []},
        ]
        trigger = should_trigger_debate(findings)
        assert trigger == DebateTrigger.CONTRADICTORY_FINDINGS


class TestDeadlockResolution:
    def test_deadlock_resolution(self):
        d = Debate(
            topic="test",
            participants=["a", "b"],
            trigger=DebateTrigger.MANUAL,
            budget=DebateBudget(max_rounds=1),
        )
        d.status = DebateStatus.DEADLOCKED
        d.root_disagreement = "Whether broadcast threshold is exceeded"
        d.missing_evidence = ["Measure table size"]

        result = deadlock_resolution(d)
        assert result["debate_id"] == d.id
        assert result["next_step"] == "experiment"
        assert "Measure table size" in result["missing_evidence"]

    def test_deadlock_no_evidence_escalates(self):
        d = Debate(
            topic="test",
            participants=["a", "b"],
            trigger=DebateTrigger.MANUAL,
        )
        d.status = DebateStatus.DEADLOCKED
        result = deadlock_resolution(d)
        assert result["next_step"] == "human_escalation"

    def test_non_deadlock_raises(self):
        d = Debate(
            topic="test",
            participants=["a", "b"],
            trigger=DebateTrigger.MANUAL,
        )
        with pytest.raises(ValueError, match="esperado=deadlocked"):
            deadlock_resolution(d)
