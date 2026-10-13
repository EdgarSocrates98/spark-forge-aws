"""Deterministic context quality metrics.

Metrics distinguish serialized bytes, observed provider tokens and unresolved
token counts. No bytes-to-token conversion is performed here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContextObservation:
    """Item de contexto observado -- vocabulario de eixos (§58).

    `relevant` e `critical` nao se confundem: relevante diz que o item serve a
    tarefa; critical diz que a remocao dele muda a resposta. `used` registra
    que um executor consumiu o item; `cited` que o item virou citacao na
    resposta; `consumed` que os bytes entraram no prompt. `required` nao e
    flag do item -- e o alvo do recall (`required_evidence_refs`).
    """

    item_id: str
    kind: str
    payload_bytes: int
    relevant: bool = False
    critical: bool = False
    evidence_refs: tuple[str, ...] = ()
    stale: bool = False
    duplicate_of: str | None = None
    reused: bool = False
    cache_hit: bool = False
    used: bool = False
    cited: bool = False
    consumed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "kind": self.kind,
            "payload_bytes": self.payload_bytes,
            "relevant": self.relevant,
            "critical": self.critical,
            "evidence_refs": list(self.evidence_refs),
            "stale": self.stale,
            "duplicate_of": self.duplicate_of,
            "reused": self.reused,
            "cache_hit": self.cache_hit,
            "used": self.used,
            "cited": self.cited,
            "consumed": self.consumed,
        }


@dataclass(frozen=True, slots=True)
class ContextQualityReport:
    item_count: int
    relevant_count: int
    required_evidence_count: int
    recalled_evidence_count: int
    payload_bytes: int
    observed_provider_tokens: int | None
    duplicate_count: int
    stale_count: int
    reused_count: int
    cache_hit_count: int
    expansion_count: int
    selected_context_bytes: int
    critical_count: int = 0
    used_count: int = 0
    cited_count: int = 0
    consumed_count: int = 0
    metrics: dict[str, float | int | str] = field(default_factory=dict)

    @classmethod
    def from_items(
        cls,
        items: Iterable[ContextObservation],
        *,
        required_evidence_refs: Iterable[str] = (),
        observed_provider_tokens: int | None = None,
        expansion_count: int = 0,
        usefulness_basis: str = "caller_declared",
    ) -> ContextQualityReport:
        records = list(items)
        required = set(required_evidence_refs)
        recalled = {ref for item in records if item.relevant for ref in item.evidence_refs}
        relevant_count = sum(1 for item in records if item.relevant)
        useful_fact_count = sum(
            1 for item in records if item.relevant and item.kind == "fact"
        )
        payload_bytes = sum(max(0, item.payload_bytes) for item in records)
        duplicate_count = sum(1 for item in records if item.duplicate_of)
        stale_count = sum(1 for item in records if item.stale)
        reused_count = sum(1 for item in records if item.reused)
        cache_hit_count = sum(1 for item in records if item.cache_hit)
        critical_count = sum(1 for item in records if item.critical)
        used_count = sum(1 for item in records if item.used)
        cited_count = sum(1 for item in records if item.cited)
        consumed_count = sum(1 for item in records if item.consumed)
        item_count = len(records)
        precision = relevant_count / item_count if item_count else 0.0
        recall = len(recalled & required) / len(required) if required else None
        density = relevant_count / max(payload_bytes / 1000, 1)
        report = cls(
            item_count=item_count,
            relevant_count=relevant_count,
            required_evidence_count=len(required),
            recalled_evidence_count=len(recalled & required),
            payload_bytes=payload_bytes,
            observed_provider_tokens=observed_provider_tokens,
            duplicate_count=duplicate_count,
            stale_count=stale_count,
            reused_count=reused_count,
            cache_hit_count=cache_hit_count,
            expansion_count=expansion_count,
            selected_context_bytes=payload_bytes,
            critical_count=critical_count,
            used_count=used_count,
            cited_count=cited_count,
            consumed_count=consumed_count,
            metrics={
                "context_recall": recall if recall is not None else "unresolved",
                "context_precision": round(precision, 6),
                "context_density": round(density, 6),
                "duplicate_context_ratio": round(duplicate_count / max(item_count, 1), 6),
                "stale_context_ratio": round(stale_count / max(item_count, 1), 6),
                "reuse_rate": round(reused_count / max(item_count, 1), 6),
                "cache_hit_rate": round(cache_hit_count / max(item_count, 1), 6),
                "expansion_rate": expansion_count,
                "evidence_per_token": (
                    round(len(recalled & required) / observed_provider_tokens, 6)
                    if observed_provider_tokens
                    else "tokens_unresolved"
                ),
                # §59-60: `useful_items` conta todo kind; `useful_facts` so
                # kind=="fact" -- facts reais identificaveis, nao `relevant`
                # renomeado. A base do julgamento de utilidade e registrada.
                "useful_items_per_1k_tokens": (
                    round(relevant_count * 1000 / observed_provider_tokens, 6)
                    if observed_provider_tokens
                    else "tokens_unresolved"
                ),
                "useful_facts_per_1k_tokens": (
                    round(useful_fact_count * 1000 / observed_provider_tokens, 6)
                    if observed_provider_tokens
                    else "tokens_unresolved"
                ),
                "usefulness_basis": usefulness_basis,
            },
        )
        return report

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_count": self.item_count,
            "relevant_count": self.relevant_count,
            "required_evidence_count": self.required_evidence_count,
            "recalled_evidence_count": self.recalled_evidence_count,
            "payload_bytes": self.payload_bytes,
            "observed_provider_tokens": self.observed_provider_tokens
            if self.observed_provider_tokens is not None
            else "unresolved",
            "duplicate_count": self.duplicate_count,
            "stale_count": self.stale_count,
            "reused_count": self.reused_count,
            "cache_hit_count": self.cache_hit_count,
            "expansion_count": self.expansion_count,
            "selected_context_bytes": self.selected_context_bytes,
            "critical_count": self.critical_count,
            "used_count": self.used_count,
            "cited_count": self.cited_count,
            "consumed_count": self.consumed_count,
            "metrics": dict(self.metrics),
        }


@dataclass(frozen=True, slots=True)
class MinimumSufficientContextBenchmark:
    levels: tuple[ContextQualityReport, ...]
    target_recall: float = 1.0
    target_precision: float = 0.0

    def minimum_sufficient_level(self) -> int | None:
        for index, report in enumerate(self.levels):
            recall = report.metrics.get("context_recall")
            precision = report.metrics.get("context_precision", 0)
            if (
                isinstance(recall, (int, float))
                and recall >= self.target_recall
                and precision >= self.target_precision
            ):
                return index
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "levels": [report.to_dict() for report in self.levels],
            "target_recall": self.target_recall,
            "target_precision": self.target_precision,
            "minimum_sufficient_level": self.minimum_sufficient_level(),
        }


@dataclass(frozen=True, slots=True)
class CounterfactualContextBenchmark:
    """Ablacao empirica de contexto -- eval/Lab apenas (§63-64).

    `ablations` sao passos `(ids_removidos, report)` medidos de verdade em
    cenarios de eval; nada aqui roda em runtime normal. A pergunta respondida
    e "qual o maior conjunto removivel sem regressao de recall/precision" --
    o minimo suficiente empirico, nao o estatico.
    """

    full: ContextQualityReport
    ablations: tuple[tuple[tuple[str, ...], ContextQualityReport], ...]
    target_recall: float = 1.0
    target_precision: float = 0.0

    def minimum_sufficient_removed(self) -> tuple[str, ...] | None:
        """A maior remocao que ainda atende os alvos; None se nenhuma couber."""
        def _passa(report: ContextQualityReport) -> bool:
            recall = report.metrics.get("context_recall")
            precision = report.metrics.get("context_precision", 0)
            return (
                isinstance(recall, (int, float))
                and recall >= self.target_recall
                and isinstance(precision, (int, float))
                and precision >= self.target_precision
            )

        candidatas = [
            (set(removidos), report)
            for removidos, report in self.ablations
            if _passa(report)
        ]
        if not candidatas:
            return None
        melhor = max(candidatas, key=lambda par: len(par[0]))
        return tuple(sorted(melhor[0]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "full": self.full.to_dict(),
            "ablations": [
                {"removed": list(removidos), "report": report.to_dict()}
                for removidos, report in self.ablations
            ],
            "target_recall": self.target_recall,
            "target_precision": self.target_precision,
            "minimum_sufficient_removed": (
                list(minimo) if (minimo := self.minimum_sufficient_removed()) else None
            ),
        }


def context_item_from_mapping(item: Mapping[str, Any]) -> ContextObservation:
    """Adapt Gateway items without coupling quality metrics to Gateway classes."""
    payload = item.get("payload", item)
    if not isinstance(payload, Mapping):
        payload = {"value": payload}
    return ContextObservation(
        item_id=str(item.get("id", payload.get("id", "item"))),
        kind=str(item.get("kind", payload.get("kind", "unknown"))),
        payload_bytes=len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        relevant=bool(item.get("relevant", item.get("critical", False))),
        critical=bool(item.get("critical", False)),
        evidence_refs=tuple(str(value) for value in item.get("evidence_refs", ())),
        stale=bool(item.get("stale", False)),
        duplicate_of=item.get("duplicate_of"),
        reused=bool(item.get("reused", False)),
        cache_hit=bool(item.get("cache_hit", False)),
        used=bool(item.get("used", False)),
        cited=bool(item.get("cited", False)),
        consumed=bool(item.get("consumed", False)),
    )


__all__ = [
    "ContextObservation",
    "ContextQualityReport",
    "CounterfactualContextBenchmark",
    "MinimumSufficientContextBenchmark",
    "context_item_from_mapping",
]
