"""SparkForge Context Engineering Package."""
from __future__ import annotations

from sparkforge.context.funnel import ContextChunk, ContextFunnel, MinimalContext
from sparkforge.context.gateway import ContextGateway, GatewayError
from sparkforge.context.gateway_models import GatewayProfile, GatewayRequest
from sparkforge.context.knowledge_pack import KnowledgePack, KnowledgePackLoader
from sparkforge.context.progressive import (
    KnowledgeLevelA,
    KnowledgeLevelB,
    KnowledgeLevelC,
    ProgressiveDisclosureManager,
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
]
