"""Delegation orchestration (lf-0029): plan → discover → gate → exec → handoff.

The consumer-side flow of a governed delegation:

1. ``plan_delegation`` selects a declared specialist + capability for an
   intent — or answers a named refusal (never a guess).
2. ``discover_peer`` resolves the peer's state. Only ``VERIFIED`` executes;
   every other state is a named refusal (absent → ``provider-absent`` with
   the fallback slug, incompatible → ``version-incompatible``, untrusted →
   ``permission-denied``).
3. ``gate_capability`` applies the 6-level risk gate: ``LOCAL_READ`` runs
   under policy; every external/cost-bearing/mutating level needs an
   explicit ``--authorize`` grant.
4. ``run_governed`` executes the resolved argv — never a shell.
5. The peer's typed parser turns stdout into handoff findings; the envelope
   is bounded, redacted, sealed and persisted under the state dir.

An absent optional specialist is never a consumer failure: the refusal
carries the declared ``fallback`` slug (``native-analysis``) so the caller
degrades explicitly. Nothing here calls AWS — sentinel's cloud verbs are
the delegatee's own reads, gated by EXTERNAL_READ + COST_BEARING.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge_aws.delegation import governance
from sparkforge_aws.delegation.contracts import (
    DelegationFailure,
    DelegationRefusal,
    EvidenceRef,
    HandoffError,
    SpecialistDelegation,
    sha256_hex,
    to_dict,
)
from sparkforge_aws.delegation.discovery import (
    PeerSpec,
    discover_peer,
    discover_peers,
)
from sparkforge_aws.delegation.execute import run_governed
from sparkforge_aws.delegation.handoff import (
    HandoffParseError,
    build_handoff,
    parser_for,
    persist_handoff,
)
from sparkforge_aws.delegation.peers import (
    CONSUMER_PROVIDER,
    PEER_BY_PROVIDER,
    PEERS,
    consumer_delegation,
)
from sparkforge_aws.delegation.router import plan_delegation

__all__ = [
    "cmd_discover",
    "cmd_plan",
    "cmd_run",
    "cmd_handoffs",
    "delegate",
    "plan",
]

# discovery-state → refusal mapping mirrors router._STATE_FAILURE
_STATE_FAILURE: dict[str, DelegationFailure] = {
    "NOT_INSTALLED": "provider-absent",
    "DISCOVERED": "provider-absent",
    "UNAVAILABLE": "provider-absent",
    "DEGRADED": "provider-absent",
    "INCOMPATIBLE": "version-incompatible",
    "UNTRUSTED": "permission-denied",
}


def _cli_argv(spec: PeerSpec, cli_path: str | None) -> list[str]:
    return [cli_path or spec.cli]


def _state_refusal(provider: str, state: str, detail: str) -> DelegationRefusal:
    return DelegationRefusal(
        code=_STATE_FAILURE.get(state, "provider-absent"),
        detail=detail,
        provider=provider,
    )


def _refusal_payload(
    delegation: SpecialistDelegation,
    refusal: DelegationRefusal,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    """A named refusal payload — the honest answer a caller degrades on."""
    return {
        "status": "refused",
        "schema": "sparkforge_aws/DelegationResult/v1",
        "correlation_id": correlation_id,
        "consumer": delegation.consumer,
        "refusal": {
            "code": refusal.code,
            "detail": refusal.detail,
            "provider": refusal.provider,
        },
        "fallback": delegation.policy.fallback or None,
        "findings": [],
        "handoff": None,
    }


def discover(*, probe: bool = True, workspace: Path | None = None,
             provider: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Discovery pass over declared peers → report dict."""
    specs = [PEER_BY_PROVIDER[provider]] if provider else list(PEERS)
    if provider and provider not in PEER_BY_PROVIDER:
        return {
            "status": "refused",
            "error": {
                "code": "provider-absent",
                "detail": f"{provider!r} is not a declared specialist of "
                          f"{CONSUMER_PROVIDER}",
            },
        }
    report = discover_peers(
        specs,
        probe=probe,
        workspace_root=workspace,
        **kwargs,
    )
    return {
        "status": "ok",
        "schema": report.schema,
        "generated_at": report.generated_at,
        "probed": report.probed,
        "entries": [
            {
                "provider": e.provider,
                "state": e.state,
                "version": e.version,
                "checks": e.checks,
                "sources": [
                    {"source": s.source, "detail": s.detail, "path": s.path}
                    for s in e.sources
                ],
                "capabilities": [
                    c.id
                    for c in (e.capability_manifest.capabilities
                              if e.capability_manifest else [])
                ],
                "declared_capabilities": [
                    c.id for c in PEER_BY_PROVIDER[e.provider].capabilities
                ]
                if e.provider in PEER_BY_PROVIDER else [],
                "notes": e.notes,
                "limitations": e.limitations,
            }
            for e in report.entries
        ],
        "limitations": report.limitations,
    }


def plan(intent: str, *, authorized_risks: set[str] | frozenset[str] = frozenset(),
         workspace: Path | None = None, probe: bool = True,
         delegation: SpecialistDelegation | None = None,
         **kwargs: Any) -> dict[str, Any]:
    """Deterministic delegation plan → plan dict."""
    delegation = delegation or consumer_delegation()
    specs = list(PEERS)
    report = discover_peers(specs, probe=probe, workspace_root=workspace, **kwargs)
    catalogs = {p.provider: p.capabilities for p in specs}
    result = plan_delegation(
        intent,
        delegation,
        report.entries,
        authorized_risks=frozenset(authorized_risks),  # type: ignore[arg-type]
        catalogs=catalogs,
    )
    return {
        "status": result.status,
        "schema": "sparkforge_aws/DelegationPlan/v1",
        "intent": intent,
        "picks": [
            {
                "provider": p.provider,
                "capability": p.capability,
                "capability_version": p.capability_version,
                "risks": list(p.risks),
                "entrypoint": p.entrypoint,
                "justification": p.justification,
            }
            for p in result.picks
        ],
        "refusals": [
            {"code": r.code, "detail": r.detail, "provider": r.provider}
            for r in result.refusals
        ],
        "limitations": result.limitations,
        "unknowns": result.unknowns,
        "fallback": delegation.policy.fallback or None,
    }


def _input_refs(provider: str, capability: str,
                values: dict[str, str | None]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    target = values.get("target")
    if isinstance(target, str) and target:
        # input refs are pointers, never payloads — the consumer resolves
        # the path inside its own roots.
        refs.append(
            EvidenceRef(kind="ref", value=f"argv:target:{sha256_hex(target.encode())[:24]}",
                        detail="target argument fingerprint")
        )
    job = values.get("job")
    if isinstance(job, str) and job:
        # the job name is argv data — a fingerprint is the durable ref,
        # never a raw identifier that could break the ref shape
        refs.append(EvidenceRef(kind="ref",
                                value=f"glue:job:{sha256_hex(job.encode())[:24]}",
                                detail="glue job name fingerprint"))
    return refs


def delegate(
    provider: str,
    capability_id: str,
    *,
    values: dict[str, str | None] | None = None,
    authorized_risks: set[str] | frozenset[str] = frozenset(),
    timeout_s: float | None = None,
    workspace: Path | None = None,
    correlation_id: str | None = None,
    delegation: SpecialistDelegation | None = None,
    persist: bool = True,
    popen_run: Any = None,  # test seam — forwarded to run_governed
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute one governed delegation → result dict.

    Named refusals come back as ``status: refused`` / ``status:
    unavailable`` payloads — never raised for domain failures
    (``DelegationError`` still signals malformed local input).
    """
    values = values or {}
    delegation = delegation or consumer_delegation()
    correlation_id = correlation_id or governance.new_correlation_id()
    workspace = Path(workspace) if workspace else Path.cwd()

    spec = PEER_BY_PROVIDER.get(provider)
    if spec is None:
        return _refusal_payload(
            delegation,
            DelegationRefusal(
                code="provider-absent",
                detail=f"{provider!r} is not a declared specialist of "
                       f"{CONSUMER_PROVIDER}",
                provider=provider,
            ),
            correlation_id=correlation_id,
        )
    capability = next((c for c in spec.capabilities if c.id == capability_id), None)
    if capability is None:
        return _refusal_payload(
            delegation,
            DelegationRefusal(
                code="capability-absent",
                detail=(
                    f"{provider}: capability {capability_id!r} is not declared; "
                    f"declared: {[c.id for c in spec.capabilities]}"
                ),
                provider=provider,
            ),
            correlation_id=correlation_id,
        )

    # chain control: mint or extend — cycle/budget refusals are named here.
    chained = delegation if delegation.chain else governance.start_chain(
        delegation, correlation_id=correlation_id
    )
    admitted = governance.admit_hop(chained, provider)
    if isinstance(admitted, DelegationRefusal):
        return _refusal_payload(delegation, admitted, correlation_id=correlation_id)
    chained = admitted

    # risk gate: LOCAL_READ under policy; everything else needs a grant.
    risks = governance.capability_risks(capability)
    gate = governance.gate_capability(risks, authorized=frozenset(authorized_risks))  # type: ignore[arg-type]
    if gate.decision == "deny":
        return _refusal_payload(
            delegation,
            DelegationRefusal(
                code="policy-refusal",
                detail=f"{provider}/{capability.id}: {gate.reason} "
                       f"(grant with --authorize)",
                provider=provider,
            ),
            correlation_id=correlation_id,
        )

    # discovery: VERIFIED executes; anything else is a named refusal.
    entry = discover_peer(
        spec, probe=True, workspace_root=workspace,
        **{k: v for k, v in kwargs.items() if k in ("dist_loader", "which", "runner")},
    )
    if entry.state != "VERIFIED":
        return _refusal_payload(
            delegation,
            _state_refusal(
                provider,
                entry.state,
                f"{provider}: discovery state {entry.state} is not VERIFIED"
                + (f" ({'; '.join(entry.notes)})" if entry.notes else ""),
            ),
            correlation_id=correlation_id,
        )
    version = entry.version

    # argv resolution → governed execution → typed parse → sealed handoff.
    argv = governance.resolve_capability_argv(
        list(capability.entrypoint),
        cli_argv=_cli_argv(spec, entry.cli_resolved or None),
        values=values,
    )
    if isinstance(argv, DelegationRefusal):
        return _refusal_payload(delegation, argv, correlation_id=correlation_id)

    result = run_governed(
        argv,
        timeout_s=timeout_s or capability.timeout_s or 300,
        _popen_run=popen_run,
    )
    parser = parser_for(provider)
    parsed: dict[str, Any] | None = None
    refusal: HandoffError | None = None
    if isinstance(result, DelegationRefusal):
        refusal = HandoffError(code=result.code, detail=result.detail,
                               retryable=result.code in governance.RETRYABLE_FAILURES)
        result = None
    elif parser is None:
        refusal = HandoffError(
            code="capability-absent",
            detail=f"{provider}: no output parser declared — contract gap",
        )
    elif result.returncode not in (0, 1):
        # rc≥2 is never findings — a real failure (usage, domain, internal).
        refusal = HandoffError(
            code="runtime-error",
            detail=(f"{provider}/{capability.id}: exit {result.returncode}: "
                    + (result.stderr or "")[-300:]),
            retryable=True,
        )
    else:
        # rc 0 = clean; rc 1 = findings at/above the peer's exit gate —
        # both are results, the typed parser decides validity.
        try:
            parsed = parser(result.stdout)
        except HandoffParseError as exc:
            refusal = HandoffError(code="invalid-output", detail=str(exc)[:500])
        except Exception as exc:
            refusal = HandoffError(code="invalid-output",
                                   detail=f"output parse failed: {exc}"[:500])

    handoff = build_handoff(
        run_id=correlation_id,
        correlation_id=correlation_id,
        source_provider=provider,
        source_version=version,
        consumer_provider=delegation.consumer,
        capability=capability.id,
        capability_version=capability.version or version,
        exec_result=result,
        input_refs=_input_refs(provider, capability.id, values),
        parsed=parsed,
        refusal=refusal,
    )
    path = persist_handoff(handoff, workspace) if persist else None

    status = handoff.status
    return {
        "status": status,
        "schema": "sparkforge_aws/DelegationResult/v1",
        "correlation_id": correlation_id,
        "consumer": delegation.consumer,
        "provider": provider,
        "provider_version": version,
        "capability": capability.id,
        "risks": list(gate.risks),
        "argv": argv,
        "findings": [to_dict(f) for f in handoff.findings],
        "limitations": handoff.limitations,
        "truncated": handoff.truncated,
        "dropped": handoff.dropped,
        "handoff": to_dict(handoff),
        "handoff_path": str(path) if path else None,
        "refusal": (
            {"code": refusal.code, "detail": refusal.detail}
            if refusal else None
        ),
        "fallback": delegation.policy.fallback or None,
        "elapsed_ms": result.elapsed_ms if result else None,
        "returncode": result.returncode if result else None,
    }


def handoffs(*, workspace: Path | None = None) -> dict[str, Any]:
    """List persisted handoffs — bounded, schema-checked reads only."""
    from sparkforge_aws.delegation.handoff import load_handoffs

    ws = Path(workspace) if workspace else Path.cwd()
    items = load_handoffs(ws)
    return {
        "status": "ok",
        "count": len(items),
        "handoffs": items,
    }


# ---------------------------------------------------------------------------
# CLI-facing wrappers (called by adapters/cli.py handlers)
# ---------------------------------------------------------------------------

def cmd_discover(args: Any) -> tuple[int, dict[str, Any]]:
    payload = discover(
        probe=not getattr(args, "no_probe", False),
        workspace=Path(getattr(args, "repo", None) or Path.cwd()),
        provider=getattr(args, "provider", None),
    )
    return (0 if payload["status"] == "ok" else 2), payload


def cmd_plan(args: Any) -> tuple[int, dict[str, Any]]:
    authorized = set(getattr(args, "authorize", None) or [])
    payload = plan(
        args.intent,
        authorized_risks=authorized,
        workspace=Path(getattr(args, "repo", None) or Path.cwd()),
        probe=not getattr(args, "no_probe", False),
    )
    return (0 if payload["status"] == "planned" else 1), payload


def cmd_run(args: Any) -> tuple[int, dict[str, Any]]:
    authorized = set(getattr(args, "authorize", None) or [])
    values: dict[str, str | None] = {
        "target": getattr(args, "target", None),
        "job": getattr(args, "job", None),
        "run_id": getattr(args, "run_id", None),
        "profile": getattr(args, "profile", None),
        "region": getattr(args, "region", None),
        "platform": getattr(args, "platform", None),
        "check": getattr(args, "check", None),
    }
    payload = delegate(
        args.provider,
        args.capability,
        values=values,
        authorized_risks=authorized,
        timeout_s=getattr(args, "timeout", None),
        workspace=Path(getattr(args, "repo", None) or Path.cwd()),
        persist=not getattr(args, "no_persist", False),
    )
    return (0 if payload["status"] in ("completed", "partial") else 1), payload


def cmd_handoffs(args: Any) -> tuple[int, dict[str, Any]]:
    payload = handoffs(
        workspace=Path(getattr(args, "repo", None) or Path.cwd()),
    )
    return 0, payload
