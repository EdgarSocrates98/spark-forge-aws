"""Canonical deterministic Context Gateway orchestration."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sparkforge.context.context_tree import build_context_tree
from sparkforge.context.gateway_budget import BudgetRefusal, pack_payload, serialized_bytes
from sparkforge.context.gateway_capabilities import discover_capabilities, load_profiles
from sparkforge.context.gateway_models import (
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
from sparkforge.context.planner import plan_execution
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
        try:
            capabilities, policy = discover_capabilities(
                request.intent,
                self.catalog,
                request.profile,
                self.policies,
                skills=skills,
                knowledge=knowledge,
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
        }
        token_state = HostTokenState.from_transcript(
            request.host_usage,
            "gateway_request.host_usage" if request.host_usage is not None else None,
        )
        base["tokens_unresolved"] = token_state.status != "resolved"
        base["token_state"] = token_state.to_dict()
        base["execution_plan"] = plan_execution(
            has_deterministic_answer=bool(capabilities),
            allow_agentic_escalation=policy.allow_agentic_escalation,
        ).to_dict()
        base["context_tree"] = build_context_tree(base, host_tokens=token_state)
        try:
            packed = pack_payload(base, request.max_bytes)
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
            )
            return refusal.to_dict()
        packed.payload["reductions"] = list(packed.reductions)
        packed.payload["budget"] = {
            "max_bytes": request.max_bytes,
            "payload_bytes": packed.payload_bytes,
            "status": "ok",
            "reductions": list(packed.reductions),
            "paginated": packed.paginated,
            "unit": "serialized_utf8_json_bytes",
        }
        packed.payload["context_tree"] = build_context_tree(packed.payload, host_tokens=token_state)
        if serialized_bytes(packed.payload) > request.max_bytes:
            packed = pack_payload(packed.payload, request.max_bytes)
            packed.payload["budget"] = {
                "max_bytes": request.max_bytes,
                "payload_bytes": packed.payload_bytes,
                "status": "ok",
                "reductions": list(packed.reductions),
                "paginated": packed.paginated,
                "unit": "serialized_utf8_json_bytes",
            }
            packed.payload["context_tree"] = build_context_tree(
                packed.payload, host_tokens=token_state
            )
        return packed.payload

    def expand(self, uri: str, *, max_bytes: int) -> dict[str, Any]:
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
        }
        expand_tokens = HostTokenState.unresolved("transcript_unavailable")
        result["tokens_unresolved"] = True
        result["token_state"] = expand_tokens.to_dict()
        result["execution_plan"] = plan_execution(
            has_deterministic_answer=False,
            allow_agentic_escalation=False,
        ).to_dict()
        try:
            packed = pack_payload(result, max_bytes)
        except BudgetRefusal as exc:
            raise GatewayError(
                f"expanded content exceeds max_bytes ({exc.required_bytes})"
            ) from exc
        packed.payload["budget"] = {
            "max_bytes": max_bytes,
            "payload_bytes": packed.payload_bytes,
            "status": "ok",
            "reductions": list(packed.reductions),
            "paginated": packed.paginated,
            "unit": "serialized_utf8_json_bytes",
        }
        packed.payload["context_tree"] = build_context_tree(
            packed.payload,
            host_tokens=expand_tokens,
        )
        packed.payload["reductions"] = list(packed.reductions)
        return packed.payload
