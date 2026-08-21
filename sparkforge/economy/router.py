"""Capability-Based Model Router for SparkForge Economy Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from sparkforge.registry.models import ExecutionProfile, ModelTier, RiskLevel


@dataclass(frozen=True)
class RoutingDecision:
    tier: ModelTier
    profile: ExecutionProfile
    selected_skills: list[str] = field(default_factory=list)
    max_tokens: int = 4000
    estimated_cost_usd: float = 0.001
    reason: str = ""
    multi_agent_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        d["profile"] = self.profile.value
        return d


class CapabilityModelRouter:
    """Selects the most cost-effective tier and model capabilities based on task parameters."""

    def route_task(
        self,
        task_description: str,
        profile: ExecutionProfile = ExecutionProfile.ECO,
        risk_level: RiskLevel = RiskLevel.READ_ONLY,
        is_deterministic_available: bool = False,
        is_cached: bool = False,
    ) -> RoutingDecision:
        task_lower = task_description.lower()

        # Tier 0: Deterministic First
        if is_deterministic_available:
            return RoutingDecision(
                tier=ModelTier.TIER_0_DETERMINISTIC,
                profile=profile,
                max_tokens=0,
                estimated_cost_usd=0.0,
                reason="Task can be solved deterministically via sparkforge.facts or rules.",
                multi_agent_allowed=False,
            )

        # Tier 1: Cached result
        if is_cached:
            return RoutingDecision(
                tier=ModelTier.TIER_1_CACHED,
                profile=profile,
                max_tokens=0,
                estimated_cost_usd=0.0,
                reason="Cached valid artifact found.",
                multi_agent_allowed=False,
            )

        # Profile: OFFLINE
        if profile == ExecutionProfile.OFFLINE:
            return RoutingDecision(
                tier=ModelTier.TIER_3_CHEAP_LOCAL,
                profile=ExecutionProfile.OFFLINE,
                max_tokens=2000,
                estimated_cost_usd=0.0,
                reason="Offline profile selected: local deterministic/local model execution.",
                multi_agent_allowed=False,
            )

        # Profile: STRICT / QUALITY with high risk or complex multi-aspect tasks
        if profile in (ExecutionProfile.QUALITY, ExecutionProfile.STRICT) and (
            risk_level in (RiskLevel.SENSITIVE, RiskLevel.DESTRUCTIVE)
            or any(kw in task_lower for kw in ["incident", "outage", "security breach", "data loss"])
        ):
            return RoutingDecision(
                tier=ModelTier.TIER_5_PREMIUM,
                profile=profile,
                max_tokens=8000,
                estimated_cost_usd=0.05,
                reason="High-risk / high-criticality task in strict/quality profile warrants Tier 5 reasoning.",
                multi_agent_allowed=(profile == ExecutionProfile.STRICT),
            )

        # Tier 4: Specialist tasks with dedicated domain skills
        specialist_keywords = {
            "pyspark": "optimize-pyspark-code",
            "iceberg": "optimize-iceberg-table",
            "athena": "optimize-athena-queries",
            "emr": "review-emr-cluster",
            "glue": "tune-glue-job",
            "data quality": "review-data-validation",
            "skew": "diagnose-data-skew",
            "parquet": "optimize-parquet-layout",
            "terraform": "review-terraform-data-platform",
            "dynamodb": "design-dynamodb-model",
            "step functions": "design-step-functions-orchestration",
            "kinesis": "streaming-reliability",
        }

        matched_skills: list[str] = []
        for kw, skill in specialist_keywords.items():
            if kw in task_lower:
                matched_skills.append(skill)

        if matched_skills:
            return RoutingDecision(
                tier=ModelTier.TIER_4_SPECIALIST,
                profile=profile,
                selected_skills=matched_skills,
                max_tokens=4000,
                estimated_cost_usd=0.005,
                reason=f"Specialist domain detected with matched skills: {', '.join(matched_skills)}",
                multi_agent_allowed=False,
            )

        # Default: Tier 3 (Cheap Local / Eco Single Agent)
        return RoutingDecision(
            tier=ModelTier.TIER_3_CHEAP_LOCAL,
            profile=profile,
            max_tokens=2000,
            estimated_cost_usd=0.001,
            reason="Standard query routed to Tier 3 cheap/fast model under ECO profile.",
            multi_agent_allowed=False,
        )
