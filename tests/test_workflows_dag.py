"""Tests for SparkForge Workflow Engine and DAG Waves (Phase 7)."""
import pytest

from sparkforge.registry.models import RiskLevel
from sparkforge.workflows import ExecutionDAG, StructuredHandoff, TaskSpec


def test_task_spec_serialization():
    spec = TaskSpec(
        objective="Optimize Glue PySpark Memory Skew",
        context="Job runs 4 hours with intermittent OOM.",
        constraints=["Do not scale workers beyond 10 G.2X", "Zero data loss"],
        acceptance_criteria=["Job completes under 45 mins", "Functional validation passes"],
        risk_level=RiskLevel.REVERSIBLE,
    )
    d = spec.to_dict()
    assert d["objective"] == "Optimize Glue PySpark Memory Skew"
    assert d["risk_level"] == "reversible"
    yaml_str = spec.to_yaml()
    assert "Do not scale workers" in yaml_str

    restored = TaskSpec.from_dict(d)
    assert restored.objective == spec.objective


def test_execution_dag_waves():
    dag = ExecutionDAG()
    dag.add_node("discovery", node_type="task")
    dag.add_node("pyspark_ast", node_type="tool")
    dag.add_node("spark_plan", node_type="tool")
    dag.add_node("judge_bottleneck", node_type="task")
    dag.add_node("verify_report", node_type="task")

    # Dependencies:
    # Wave 0: discovery
    # Wave 1: pyspark_ast, spark_plan (both depend on discovery)
    # Wave 2: judge_bottleneck (depends on ast & plan)
    # Wave 3: verify_report (depends on judge)
    dag.add_dependency("pyspark_ast", "discovery")
    dag.add_dependency("spark_plan", "discovery")
    dag.add_dependency("judge_bottleneck", "pyspark_ast")
    dag.add_dependency("judge_bottleneck", "spark_plan")
    dag.add_dependency("verify_report", "judge_bottleneck")

    waves = dag.compute_waves()
    assert len(waves) == 4
    assert [n.id for n in waves[0]] == ["discovery"]
    assert set(n.id for n in waves[1]) == {"pyspark_ast", "spark_plan"}
    assert [n.id for n in waves[2]] == ["judge_bottleneck"]
    assert [n.id for n in waves[3]] == ["verify_report"]


def test_execution_dag_cycle_detection():
    dag = ExecutionDAG()
    dag.add_node("a")
    dag.add_node("b")
    dag.add_dependency("a", "b")
    dag.add_dependency("b", "a")  # Cycle

    assert dag.detect_cycles() is True
    with pytest.raises(ValueError, match="Cycle detected"):
        dag.compute_waves()


def test_structured_handoff():
    handoff = StructuredHandoff(
        sender_role="pyspark-specialist",
        recipient_role="evidence-verifier",
        finding_summary="Identified cartesian join without broadcast in line 42.",
        evidence_fact_ids=["pyspark.ast.001", "spark.plan.002"],
        confidence="high",
        recommendation="Replace with broadcast join.",
        next_action="Run functional validation plan.",
    )
    md = handoff.to_compact_markdown()
    assert "pyspark-specialist" in md
    assert "pyspark.ast.001" in md
