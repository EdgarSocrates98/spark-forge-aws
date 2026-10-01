from __future__ import annotations

from sparkforge.context.gateway_capabilities import discover_capabilities, load_profiles
from sparkforge.context.gateway_models import GatewayProfile


def test_profile_applies_independent_skill_and_knowledge_limits() -> None:
    skills = [{"name": f"glue-skill-{index}", "description": "glue"} for index in range(10)]
    knowledge = [
        {"name": f"glue-knowledge-{index}", "description": "glue"} for index in range(10)
    ]

    capabilities, policy = discover_capabilities(
        "glue",
        {},
        GatewayProfile.ECONOMY,
        load_profiles(),
        skills=skills,
        knowledge=knowledge,
    )

    assert len(capabilities) <= policy.max_capabilities
    assert sum(item.kind == "skill" for item in capabilities) <= policy.max_skills
    assert sum(item.kind == "knowledge" for item in capabilities) <= policy.max_knowledge_chunks


def test_profile_selection_is_stable_for_equal_scores() -> None:
    skills = [
        {"name": "glue-skill-b", "description": "glue"},
        {"name": "glue-skill-a", "description": "glue"},
    ]

    first, _ = discover_capabilities(
        "glue", {}, GatewayProfile.DEEP, load_profiles(), skills=skills
    )
    second, _ = discover_capabilities(
        "glue", {}, GatewayProfile.DEEP, load_profiles(), skills=list(reversed(skills))
    )

    assert [item.name for item in first] == [item.name for item in second]


def test_profile_default_budget_is_declared_in_yaml() -> None:
    policies = load_profiles()

    assert policies[GatewayProfile.ECONOMY].default_max_bytes == 6000
    assert policies[GatewayProfile.BALANCED].default_max_bytes == 16000
    assert policies[GatewayProfile.DEEP].default_max_bytes == 30000
