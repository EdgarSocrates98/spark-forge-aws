"""Tests for SparkForge Canonical Registry (Phase 2)."""
import pytest

from sparkforge.registry import (
    AgentManifest,
    CanonicalRegistry,
    ExecutionProfile,
    ModelPolicy,
    ModelTier,
    RiskLevel,
    SkillManifest,
    ToolManifest,
    ValidationError,
    get_default_registry,
    validate_agent_dict,
    validate_skill_dict,
    validate_tool_dict,
)


def test_agent_manifest_creation_and_dict():
    agent = AgentManifest(
        id="sf-pyspark-specialist",
        name="sf-pyspark-specialist",
        version="1.0.0",
        description="Specialist in PySpark performance and execution plans",
        purpose="PySpark tuning and diagnosis",
        role="specialist",
        domains=["pyspark", "aws-glue"],
        allowed_tools=["sparkforge_analyze_pyspark", "sparkforge_analyze_plan"],
        risk_level=RiskLevel.READ_ONLY,
        model_policy=ModelPolicy(tier=ModelTier.TIER_4_SPECIALIST),
    )
    d = agent.to_dict()
    assert d["id"] == "sf-pyspark-specialist"
    assert d["risk_level"] == "read_only"
    assert d["model_policy"]["tier"] == "tier_4_specialist"
    validate_agent_dict(d)


def test_skill_manifest_validation():
    skill = SkillManifest(
        id="optimize-pyspark-code",
        name="optimize-pyspark-code",
        version="1.0.0",
        description="Optimize PySpark AST transformations and avoid bad patterns",
        triggers=["high cpu", "python udf", "collect()"],
        anti_triggers=["bash script", "terraform only"],
    )
    d = skill.to_dict()
    assert d["id"] == "optimize-pyspark-code"
    validate_skill_dict(d)


def test_tool_manifest_validation():
    tool = ToolManifest(
        id="sparkforge_analyze_pyspark",
        name="sparkforge_analyze_pyspark",
        namespace="sparkforge.facts",
        description="Extract deterministic AST facts from PySpark code",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        output_schema={"type": "array"},
        mutation_class=RiskLevel.READ_ONLY,
        deterministic=True,
        cacheable=True,
    )
    d = tool.to_dict()
    assert d["deterministic"] is True
    validate_tool_dict(d)


def test_registry_loading():
    registry = get_default_registry()
    assert len(registry.agents) > 0
    assert len(registry.skills) > 0
    assert registry.get_agent("sf-pyspark-specialist") is not None
    assert registry.get_skill("optimize-pyspark-code") is not None


def test_invalid_agent_validation_raises():
    invalid_data = {
        "id": "invalid name with spaces",
        "name": "test",
        # missing required fields
    }
    with pytest.raises(ValidationError):
        validate_agent_dict(invalid_data)
