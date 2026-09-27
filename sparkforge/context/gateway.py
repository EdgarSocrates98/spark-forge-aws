"""Canonical deterministic Context Gateway orchestration."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sparkforge.codeintel.query_expansion import expand_query
from sparkforge.context.context_tree import build_context_tree
from sparkforge.context.gateway_budget import (
    BudgetRefusal,
    materialize_bounded,
    serialized_bytes,
)
from sparkforge.context.gateway_capabilities import discover_capabilities, load_profiles
from sparkforge.context.gateway_models import (
    AnswerState,
    BudgetReport,
    ContextItem,
    GatewayPhase,
    GatewayProfile,
    GatewayRequest,
    GatewayResponse,
    Unresolved,
)
from sparkforge.context.gateway_refs import ContextRefError, ContextRefStore
from sparkforge.context.host_usage import HostTokenState
from sparkforge.context.planner import derive_triggers, normalize_triggers, plan_execution
from sparkforge.economy.cache import ArtifactCache


class GatewayError(ValueError):
    """Named boundary error for invalid Gateway operations."""


def _request_id(request: GatewayRequest) -> str:
    raw = {
        "intent": request.intent,
        "profile": request.profile.value,
        "max_bytes": request.max_bytes,
        "case_id": request.case_id,
        "items": list(request.items),
    }
    return hashlib.sha256(str(sorted(raw.items())).encode("utf-8")).hexdigest()[:16]


def _item_id(item: Mapping[str, Any], ordinal: int) -> str:
    for key in ("id", "fact_id", "finding_id", "rule_id"):
        value = item.get(key)
        if value:
            return str(value)
    return f"context:{ordinal:04d}"


def _item_kind(item: Mapping[str, Any]) -> str:
    raw = item.get("kind", item.get("type", "context"))
    return str(raw).split(".", 1)[0].lower()


def _is_critical(item: Mapping[str, Any], kind: str) -> bool:
    critical_kinds = {"fact", "finding", "rule", "error", "risk", "unresolved"}
    critical_keys = ("fact_id", "rule_id", "evidence_refs", "risks", "unresolved")
    return bool(item.get("critical")) or kind in critical_kinds or any(
        key in item for key in critical_keys
    )


class ContextGateway:
    """Coordinates discovery, selection, reduction, materialization and expand."""

    def __init__(
        self,
        catalog: Mapping[str, Mapping[str, Any]],
        *,
        cache: ArtifactCache | None = None,
        profiles_path: Path | None = None,
        authorized_root: Path | None = None,
    ) -> None:
        self.catalog = catalog
        self.policies = load_profiles(profiles_path)
        self.refs = ContextRefStore(cache=cache, authorized_root=authorized_root)

    def start(
        self,
        request: GatewayRequest,
        *,
        skills: list[Mapping[str, Any]] | None = None,
        knowledge: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        request_id = _request_id(request)
        unresolved: list[Unresolved] = []
        policy = self.policies[request.profile]
        expansion = expand_query(request.intent, max_terms=policy.max_query_terms)
        active_triggers = normalize_triggers(
            (*request.triggers, *derive_triggers(request.items))
        )
        answer_status = request.answer_status or (
            "partial" if request.items else "unavailable"
        )
        answer_state = AnswerState(
            answer_status,
            request.answer_reasons or ("answer_state_not_declared",),
            active_triggers,
        )
        try:
            capabilities, policy = discover_capabilities(
                request.intent,
                self.catalog,
                request.profile,
                self.policies,
                skills=skills,
                knowledge=knowledge,
                expansion=expansion,
            )
        except (KeyError, ValueError) as exc:
            raise GatewayError(f"capability discovery failed: {exc}") from exc

        context: list[ContextItem] = []
        refs = []
        ordered_items = sorted(
            enumerate(request.items),
            key=lambda pair: (-int(pair[1].get("relevance", 50)), _item_id(pair[1], pair[0])),
        )
        for ordinal, raw in ordered_items:
            kind = _item_kind(raw)
            item_id = _item_id(raw, ordinal)
            critical = _is_critical(raw, kind)
            relevance = int(raw.get("relevance", 100 if critical else 50))
            payload = dict(raw)
            payload.pop("id", None)
            payload.pop("critical", None)
            payload.pop("relevance", None)
            ref = None
            if kind in {"knowledge", "code", "artifact"} or serialized_bytes(payload) > 512:
                ref = self.refs.put(kind, payload, provenance=raw.get("provenance"))
                refs.append(ref)
            context.append(
                ContextItem(
                    id=item_id,
                    kind=kind,
                    relevance=relevance,
                    critical=critical,
                    payload=payload,
                    ref=ref,
                )
            )

        base = {
            "schema_version": 1,
            "status": "ok",
            "phase": GatewayPhase.MATERIALIZED.value,
            "request_id": request_id,
            "profile": request.profile.value,
            "capabilities": [item.to_dict() for item in capabilities],
            "context": [item.to_dict() for item in context],
            "refs": [item.to_dict() for item in refs],
            "budget": {
                "max_bytes": request.max_bytes,
                "payload_bytes": 0,
                "status": "pending",
                "reductions": [],
                "paginated": False,
                "unit": "serialized_utf8_json_bytes",
            },
            "reductions": [],
            "unresolved": [item.to_dict() for item in unresolved],
            "provider_tokens": dict(request.host_usage) if request.host_usage is not None else None,
            "answer_state": answer_state.to_dict(),
            "query_expansion": expansion.to_dict(),
            "discovery": {
                "candidate_count": len(capabilities),
                "limits": {
                    "capabilities": policy.max_capabilities,
                    "skills": policy.max_skills,
                    "knowledge": policy.max_knowledge_chunks,
                },
            },
        }
        token_state = HostTokenState.from_transcript(
            request.host_usage,
            "gateway_request.host_usage" if request.host_usage is not None else None,
        )
        base["tokens_unresolved"] = token_state.status != "resolved"
        base["token_state"] = token_state.to_dict()
        base["execution_plan"] = plan_execution(
            has_deterministic_answer=answer_state.status == "resolved",
            answer_status=answer_state.status,
            triggers=answer_state.triggers,
            allow_agentic_escalation=policy.allow_agentic_escalation,
        ).to_dict()

        def rebuild_derived(payload: dict[str, Any]) -> None:
            for _ in range(3):
                budget = dict(payload.get("budget", {}))
                budget.update(
                    {
                        "max_bytes": request.max_bytes,
                        "payload_bytes": serialized_bytes(payload),
                        "status": "ok",
                        "reductions": list(payload.get("reductions", [])),
                        "paginated": "pagination" in payload,
                        "unit": "serialized_utf8_json_bytes",
                    }
                )
                payload["budget"] = budget
                payload["context_tree"] = build_context_tree(
                    payload,
                    host_tokens=token_state,
                )

        try:
            materialized = materialize_bounded(base, request.max_bytes, rebuild_derived)
        except BudgetRefusal as exc:
            refusal = GatewayResponse(
                status="refused",
                phase=GatewayPhase.REDUCED,
                request_id=request_id,
                profile=request.profile,
                capabilities=(),
                context=(),
                refs=(),
                budget=BudgetReport(
                    request.max_bytes,
                    exc.required_bytes,
                    "refused",
                    ("critical_overflow",),
                    True,
                ),
                unresolved=(Unresolved("budget_unresolved", str(exc), "increase max_bytes"),),
                host_usage=request.host_usage,
                error="critical gateway content exceeds max_bytes",
                answer_state=answer_state,
                query_expansion=expansion.to_dict(),
            )
            return refusal.to_dict()
        return materialized

    def expand(self, uri: str, *, max_bytes: int | None = None) -> dict[str, Any]:
        if max_bytes is None:
            max_bytes = self.policies[GatewayProfile.ECONOMY].default_max_bytes
        if max_bytes <= 0:
            raise GatewayError("max_bytes must be positive")
        try:
            value = self.refs.resolve(uri)
        except ContextRefError as exc:
            raise GatewayError(str(exc)) from exc
        result = {
            "schema_version": 1,
            "status": "ok",
            "phase": GatewayPhase.EXPANDED.value,
            "request_id": uri.rsplit("/", 1)[-1][:16],
            "profile": GatewayProfile.ECONOMY.value,
            "capabilities": [],
            "context": [
                {
                    "id": uri.rsplit("/", 1)[-1],
                    "kind": value["ref"]["kind"],
                    "relevance": 100,
                    "critical": True,
                    "payload": value["payload"],
                }
            ],
            "refs": [value["ref"]],
            "budget": {
                "max_bytes": max_bytes,
                "payload_bytes": 0,
                "status": "pending",
                "reductions": [],
                "paginated": False,
                "unit": "serialized_utf8_json_bytes",
            },
            "reductions": [],
            "unresolved": [],
            "provider_tokens": None,
            "answer_state": AnswerState(
                "unavailable",
                ("reference_expansion_is_context_only",),
                (),
            ).to_dict(),
            "query_expansion": expand_query("").to_dict(),
        }
        expand_tokens = HostTokenState.unresolved("transcript_unavailable")
        result["tokens_unresolved"] = True
        result["token_state"] = expand_tokens.to_dict()
        result["execution_plan"] = plan_execution(
            has_deterministic_answer=False,
            answer_status="unavailable",
            allow_agentic_escalation=False,
        ).to_dict()

        def rebuild_derived(payload: dict[str, Any]) -> None:
            for _ in range(3):
                budget = dict(payload.get("budget", {}))
                budget.update(
                    {
                        "max_bytes": max_bytes,
                        "payload_bytes": serialized_bytes(payload),
                        "status": "ok",
                        "reductions": list(payload.get("reductions", [])),
                        "paginated": "pagination" in payload,
                        "unit": "serialized_utf8_json_bytes",
                    }
                )
                payload["budget"] = budget
                payload["context_tree"] = build_context_tree(
                    payload,
                    host_tokens=expand_tokens,
                )
        try:
            materialized = materialize_bounded(result, max_bytes, rebuild_derived)
        except BudgetRefusal as exc:
            raise GatewayError(
                f"expanded content exceeds max_bytes ({exc.required_bytes})"
            ) from exc
        return materialized
