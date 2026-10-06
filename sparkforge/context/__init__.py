"""SparkForge Context Engineering Package."""
from __future__ import annotations

from sparkforge.context.context_tree import ContextTreeEntry, build_context_tree
from sparkforge.context.funnel import ContextChunk, ContextFunnel, MinimalContext
from sparkforge.context.gateway import ContextGateway, GatewayError
from sparkforge.context.gateway_models import GatewayProfile, GatewayRequest
from sparkforge.context.host_usage import HostTokenState
from sparkforge.context.knowledge_pack import KnowledgePack, KnowledgePackLoader
from sparkforge.context.planner import ExecutionPlan, plan_execution
from sparkforge.context.progressive import (
    KnowledgeLevelA,
    KnowledgeLevelB,
    KnowledgeLevelC,
    ProgressiveDisclosureManager,
)
from sparkforge.context.quality import (
    ContextObservation,
    ContextQualityReport,
    CounterfactualContextBenchmark,
    MinimumSufficientContextBenchmark,
)

__all__ = [
    "ContextChunk",
    "ContextFunnel",
    "MinimalContext",
    "KnowledgePack",
    "KnowledgePackLoader",
    "KnowledgeLevelA",
    "KnowledgeLevelB",
    "KnowledgeLevelC",
    "ProgressiveDisclosureManager",
    "ContextGateway",
    "GatewayError",
    "GatewayProfile",
    "GatewayRequest",
    "HostTokenState",
    "ExecutionPlan",
    "plan_execution",
    "ContextTreeEntry",
    "build_context_tree",
    "ContextObservation",
    "ContextQualityReport",
    "CounterfactualContextBenchmark",
    "MinimumSufficientContextBenchmark",
]
