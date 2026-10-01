"""Tests for SparkForge Token Economy Engine (Phase 3)."""

from sparkforge.economy import (
    ArtifactCache,
    CapabilityModelRouter,
    ExecutionProfile,
    ModelTier,
    TokenWasteDetector,
)


def test_artifact_cache_set_get(tmp_path):
    cache = ArtifactCache(cache_dir=tmp_path / "cache")
    inputs = {"path": "s3://bucket/data", "kind": "pyspark"}
    value = {"status": "optimized", "gain": "35%"}

    key = cache.set(namespace="pyspark_analysis", inputs=inputs, value=value)
    assert key is not None

    retrieved = cache.get(namespace="pyspark_analysis", inputs=inputs)
    assert retrieved == value

    # Different inputs should return None
    assert cache.get(namespace="pyspark_analysis", inputs={"other": 1}) is None


def test_capability_router_deterministic_first():
    router = CapabilityModelRouter()
    decision = router.route_task(
        task_description="Extract AST facts from Glue job",
        is_deterministic_available=True,
    )
    assert decision.tier == ModelTier.TIER_0_DETERMINISTIC
    assert decision.max_tokens == 0
    assert decision.estimated_cost_usd == 0.0


def test_capability_router_specialist_skill():
    router = CapabilityModelRouter()
    decision = router.route_task(
        task_description="Tuning PySpark job with high memory skew",
        profile=ExecutionProfile.ECO,
    )
    assert decision.tier == ModelTier.TIER_4_SPECIALIST
    assert "optimize-pyspark-code" in decision.selected_skills
    assert "diagnose-data-skew" in decision.selected_skills


def test_token_waste_detector():
    detector = TokenWasteDetector()
    events = [
        {
            "type": "tool_call",
            "name": "sparkforge_analyze_pyspark",
            "args": {"path": "job.py"},
            "tokens": 500,
        },
        {
            "type": "tool_call",
            "name": "sparkforge_analyze_pyspark",
            "args": {"path": "job.py"},
            "tokens": 500,
        },
        {
            "type": "tool_call",
            "name": "sparkforge_analyze_pyspark",
            "args": {"path": "job.py"},
            "tokens": 500,
        },
        {"type": "model_call", "tier": "tier_5_premium", "task_complexity": "low", "tokens": 2000},
    ]
    findings = detector.analyze_trace(events)
    assert len(findings) >= 2
    pattern_ids = [f.pattern_id for f in findings]
    assert "WASTE-001" in pattern_ids  # Repeated identical tool calls
    assert "WASTE-002" in pattern_ids  # Expensive model on simple task
