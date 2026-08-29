"""Canonical Factory Registry Models.

Single source of truth (SSOT) data models for the Agent Factory.
Designed to be serializable to/from JSON and YAML with strict schema validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    SENSITIVE = "sensitive"
    DESTRUCTIVE = "destructive"


class ExecutionProfile(str, Enum):
    ECO = "eco"
    BALANCED = "balanced"
    QUALITY = "quality"
    OFFLINE = "offline"
    STRICT = "strict"


class ModelTier(str, Enum):
    TIER_0_DETERMINISTIC = "tier_0_deterministic"
    TIER_1_CACHED = "tier_1_cached"
    TIER_2_RETRIEVAL = "tier_2_retrieval"
    TIER_3_CHEAP_LOCAL = "tier_3_cheap_local"
    TIER_4_SPECIALIST = "tier_4_specialist"
    TIER_5_PREMIUM = "tier_5_premium"
    TIER_6_MULTI_AGENT = "tier_6_multi_agent"


class PlatformTarget(str, Enum):
    ANTIGRAVITY = "antigravity"
    CURSOR = "cursor"
    CLAUDE = "claude"
    DEVIN = "devin"
    WINDSURF = "windsurf"
    COPILOT = "copilot"
    GENERIC = "generic"


@dataclass(frozen=True)
class TokenBudget:
    max_input_tokens: int = 4000
    max_output_tokens: int = 2000
    max_total_tokens: int = 8000
    max_agent_calls: int = 2
    max_tool_calls: int = 10
    max_rounds: int = 3
    max_retries: int = 2
    max_cost_usd: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelPolicy:
    tier: ModelTier = ModelTier.TIER_3_CHEAP_LOCAL
    temperature: float = 0.0
    structured_output: bool = True
    streaming: bool = False
    fallback_tier: ModelTier | None = ModelTier.TIER_0_DETERMINISTIC

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        if self.fallback_tier:
            d["fallback_tier"] = self.fallback_tier.value
        return d


@dataclass(frozen=True)
class AgentManifest:
    id: str
    name: str
    version: str
    description: str
    purpose: str
    role: str
    domains: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    optional_skills: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    knowledge_refs: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)
    token_budget: TokenBudget = field(default_factory=TokenBudget)
    supported_targets: list[PlatformTarget] = field(
        default_factory=lambda: [
            PlatformTarget.ANTIGRAVITY,
            PlatformTarget.CURSOR,
            PlatformTarget.CLAUDE,
            PlatformTarget.DEVIN,
            PlatformTarget.WINDSURF,
            PlatformTarget.COPILOT,
            PlatformTarget.GENERIC,
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        d["model_policy"] = self.model_policy.to_dict()
        d["token_budget"] = self.token_budget.to_dict()
        d["supported_targets"] = [t.value for t in self.supported_targets]
        return d


@dataclass(frozen=True)
class SkillManifest:
    id: str
    name: str
    version: str
    description: str  # Level A (~20-50 tokens)
    triggers: list[str] = field(default_factory=list)
    anti_triggers: list[str] = field(default_factory=list)
    procedure_path: str = ""  # Level B
    references: list[str] = field(default_factory=list)  # Level C
    required_tools: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.READ_ONLY

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


@dataclass(frozen=True)
class ToolManifest:
    id: str
    name: str
    namespace: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    mutation_class: RiskLevel = RiskLevel.READ_ONLY
    deterministic: bool = True
    cacheable: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mutation_class"] = self.mutation_class.value
        return d


@dataclass(frozen=True)
class TeamManifest:
    id: str
    name: str
    coordinator: str
    members: list[str]
    handoffs: list[str]
    max_rounds: int = 3
    escalation_policy: str = "stop_on_gate_failure"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowManifest:
    id: str
    name: str
    description: str
    waves: list[dict[str, Any]] = field(default_factory=list)
    required_gates: list[str] = field(default_factory=list)
    timeout_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyManifest:
    id: str
    name: str
    network_default: str = "deny"
    mutation_policy: str = "approval_required"
    secrets_logging: str = "deny"
    offline_fallback: str = "unresolved"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeManifest:
    id: str
    domain: str
    title: str
    concise_path: str
    patterns_path: str | None = None
    anti_patterns_path: str | None = None
    references_path: str | None = None
    last_verified: str = ""
    source_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalManifest:
    id: str
    name: str
    category: str  # unit, contract, golden, bdd, holdout, security, economy
    dataset_path: str
    metrics: list[str]
    min_pass_rate: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ======================================================================
# Specialized Domain Manifests
# ======================================================================

@dataclass(frozen=True)
class GlueMigrationManifest:
    id: str
    source_runtime: str  # e.g. "4.0"
    target_runtime: str  # e.g. "5.1"
    breaking_change_checks: list[str]
    dependency_upgrades: list[dict[str, str]]
    s3_filesystem_audit: bool = True
    lakeformation_audit: bool = True
    iceberg_audit: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LakeFormationManifest:
    id: str
    mode: str  # fta, fgac, hybrid
    cross_account: bool = False
    resource_links: list[str] = field(default_factory=list)
    ram_shares: list[str] = field(default_factory=list)
    kms_key_arns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IcebergDoctorManifest:
    id: str
    table_name: str
    format_version: int = 2
    max_small_file_mb: int = 64
    max_delete_file_ratio: float = 0.05
    maintenance_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerraformPlanManifest:
    id: str
    plan_path: str
    blocked_actions: list[str] = field(default_factory=lambda: ["delete", "replace"])
    iam_wildcard_strict: bool = True
    s3_public_block_check: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
