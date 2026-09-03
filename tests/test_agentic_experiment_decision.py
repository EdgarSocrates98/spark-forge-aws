"""Testes do Experiment Engine e Decision Engine."""

from __future__ import annotations

import pytest

from sparkforge.agentic.decision import (
    DecisionContext,
    generate_adr,
    is_significant_decision,
    make_decision,
)
from sparkforge.agentic.experiment import (
    ExperimentPlan,
    design_experiment,
    design_experiment_for_unknown,
    design_experiment_from_deadlock,
    evaluate_experiment_result,
)
from sparkforge.agentic.models import (
    Experiment,
    ExperimentStatus,
    Hypothesis,
)


class TestDesignExperiment:
    def test_design_from_hypothesis(self):
        h = Hypothesis(
            statement="Small files cause read amplification",
            expected_outcome="Compaction reduces read latency by 30%",
            failure_modes=["Metadata cache masks the effect"],
            proposed_by="sf-iceberg-specialist",
        )
        exp = design_experiment(
            h,
            variable="compaction_enabled",
            baseline="no compaction",
            proposed_by="sf-iceberg-specialist",
        )
        assert exp.hypothesis_id == h.id
        assert exp.variable == "compaction_enabled"
        assert exp.baseline == "no compaction"
        assert exp.status == ExperimentStatus.PROPOSED
        assert "Compaction reduces" in exp.success_criteria

    def test_hypothesis_without_expected_outcome_raises(self):
        h = Hypothesis(statement="test")
        with pytest.raises(ValueError, match="expected_outcome"):
            design_experiment(h, variable="x", baseline="y")


class TestDesignFromDeadlock:
    def test_generates_two_experiments(self):
        h_a = Hypothesis(
            statement="OOM from broadcast",
            expected_outcome="Disabling broadcast eliminates OOM",
        )
        h_b = Hypothesis(
            statement="OOM from shuffle",
            expected_outcome="Increasing partitions eliminates OOM",
        )
        plan = design_experiment_from_deadlock(
            h_a,
            h_b,
            variable="broadcast_enabled",
            baseline="broadcast on",
        )
        assert isinstance(plan, ExperimentPlan)
        assert len(plan.experiments) == 2
        assert plan.risk_level == "low"


class TestDesignForUnknown:
    def test_generates_experiment(self):
        exp = design_experiment_for_unknown(
            unknown_question="What is the partition count?",
            variable="partition_count",
            baseline="200",
        )
        assert exp.variable == "partition_count"
        assert exp.status == ExperimentStatus.PROPOSED


class TestEvaluateResult:
    def test_success(self):
        exp = Experiment(
            hypothesis_id="hyp_1",
            variable="x",
            baseline="y",
            status=ExperimentStatus.RUNNING,
        )
        status, reasoning = evaluate_experiment_result(
            exp, observed_result="improved", success_criteria_met=True
        )
        assert status == ExperimentStatus.SUCCEEDED
        assert "Success" in reasoning

    def test_failure(self):
        exp = Experiment(
            hypothesis_id="hyp_1",
            variable="x",
            baseline="y",
            status=ExperimentStatus.RUNNING,
        )
        status, reasoning = evaluate_experiment_result(
            exp, observed_result="no change", success_criteria_met=False
        )
        assert status == ExperimentStatus.FAILED
        assert "NOT met" in reasoning

    def test_not_running_raises(self):
        exp = Experiment(
            hypothesis_id="hyp_1",
            variable="x",
            baseline="y",
            status=ExperimentStatus.PROPOSED,
        )
        with pytest.raises(ValueError, match="esperado=running"):
            evaluate_experiment_result(exp, "result", True)


class TestMakeDecision:
    def test_creates_decision(self):
        ctx = DecisionContext(
            problem="Reduce shuffle spill",
            options=["increase partitions", "broadcast join"],
            evidence_by_option={"broadcast join": ["f_abc", "ev_def"]},
            risks=["OOM if threshold exceeded"],
            assumptions=["table fits in broadcast threshold"],
            decided_by="sf-spark-specialist",
        )
        d = make_decision(
            ctx,
            selected_option="broadcast join",
            validation="Run funcval compare",
            rollback="revert to 200 partitions",
        )
        assert d.selected_option == "broadcast join"
        assert d.rejected_options == ["increase partitions"]
        assert d.evidence_refs == ["f_abc", "ev_def"]

    def test_selected_not_in_options_raises(self):
        ctx = DecisionContext(
            problem="test",
            options=["a", "b"],
        )
        with pytest.raises(ValueError, match="não está em options"):
            make_decision(ctx, selected_option="c", rollback="r")

    def test_empty_rollback_raises(self):
        ctx = DecisionContext(problem="test", options=["a"])
        with pytest.raises(ValueError, match="rollback"):
            make_decision(ctx, selected_option="a", rollback="")


class TestGenerateADR:
    def test_generates_markdown(self):
        ctx = DecisionContext(
            problem="Use broadcast join for dimension table",
            options=["broadcast join", "sort-merge join"],
            risks=["OOM if table grows"],
            assumptions=["table < 10GB"],
            decided_by="sf-spark-specialist",
            created_at="2026-09-03T10:00:00Z",
        )
        d = make_decision(
            ctx,
            selected_option="broadcast join",
            confidence="medium",
            validation="Run funcval compare",
            rollback="revert to sort-merge join",
            falsification_condition="If OOM occurs, revert",
        )
        adr = generate_adr(d)
        assert "# ADR-" in adr
        assert "broadcast join" in adr
        assert "sort-merge join" in adr
        assert "Rollback" in adr
        assert "Falsification" in adr

    def test_irreversible_decision(self):
        ctx = DecisionContext(
            problem="Drop legacy table",
            options=["drop", "keep"],
            decided_by="human",
        )
        d = make_decision(
            ctx,
            selected_option="drop",
            rollback="irreversible: data loss after drop",
        )
        adr = generate_adr(d)
        assert "irreversible" in adr


class TestIsSignificant:
    def test_high_confidence_simple_not_significant(self):
        ctx = DecisionContext(
            problem="trivial change",
            options=["a", "b"],
        )
        d = make_decision(ctx, selected_option="a", confidence="high", rollback="revert a")
        assert not is_significant_decision(d)

    def test_low_confidence_is_significant(self):
        ctx = DecisionContext(
            problem="uncertain change",
            options=["a", "b"],
        )
        d = make_decision(ctx, selected_option="a", confidence="low", rollback="revert a")
        assert is_significant_decision(d)

    def test_with_risks_is_significant(self):
        ctx = DecisionContext(
            problem="risky change",
            options=["a", "b"],
            risks=["OOM possible"],
        )
        d = make_decision(ctx, selected_option="a", confidence="high", rollback="revert a")
        assert is_significant_decision(d)

    def test_irreversible_is_significant(self):
        ctx = DecisionContext(
            problem="drop table",
            options=["drop", "keep"],
        )
        d = make_decision(
            ctx,
            selected_option="drop",
            confidence="high",
            rollback="irreversible: data loss",
        )
        assert is_significant_decision(d)
