"""Provider-agnostic model selection for Devin/Claude coordinators."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    provider: str = "unknown"
    input_price: float | None = None
    output_price: float | None = None
    context_tokens: int | None = None
    quality: int = 3
    reasoning: bool = False
    tools: bool = False
    vision: bool = False
    available: bool = True

@dataclass(frozen=True)
class ModelDemand:
    task: str
    risk: str = "low"
    complexity: str = "focused"
    needs_tools: bool = False
    needs_vision: bool = False
    min_quality: int = 1
    max_input_price: float | None = None
    max_output_price: float | None = None

@dataclass(frozen=True)
class ModelChoice:
    model: ModelInfo | None
    reason: str
    fallback: bool = False

class ModelSelector:
    def choose(self, models: Iterable[ModelInfo], demand: ModelDemand) -> ModelChoice:
        candidates = [m for m in models if m.available and m.quality >= demand.min_quality]
        if demand.needs_tools:
            candidates = [m for m in candidates if m.tools]
        if demand.needs_vision:
            candidates = [m for m in candidates if m.vision]
        if demand.max_input_price is not None:
            candidates = [m for m in candidates if m.input_price is None or m.input_price <= demand.max_input_price]
        if demand.max_output_price is not None:
            candidates = [m for m in candidates if m.output_price is None or m.output_price <= demand.max_output_price]
        if not candidates:
            return ModelChoice(None, "no available model satisfies the demand")
        hard = demand.risk in {"high", "critical"} or demand.complexity == "deep"
        def score(model: ModelInfo) -> tuple[int, int, float]:
            capability = model.quality + (2 if model.reasoning and hard else 0) + (1 if model.tools and demand.needs_tools else 0)
            price = (model.input_price or 0.0) + (model.output_price or 0.0)
            return (capability, model.context_tokens or 0, -price)
        chosen = max(candidates, key=score)
        return ModelChoice(chosen, "selected from the coordinator account inventory")
