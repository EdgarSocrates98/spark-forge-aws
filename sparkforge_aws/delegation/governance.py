"""Delegation governance (lf-0029): risk gates, chain control, retry policy,
argv/refs hygiene, evidence-handoff hygiene.

Native re-implementation of ``theforge/delegation_governance.py`` semantics —
sparkforge_aws cannot import theforge, so the same pure, deterministic
functions live here: no wall-clock (callers pass measured seconds), no I/O,
no provider execution. This module decides *whether* and *how* a delegation
may proceed; ``execute.py`` is the single subprocess substrate.

Data-only rule: fields extracted from a provider document —
``DeclaredCapability``, ``EvidenceHandoff``, finding summaries — are DATA.
They select among *declared* options or annotate a refusal; they never
become commands, capability grants or trust elevation.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from sparkforge_aws.delegation.contracts import (
    MAX_DETAIL_CHARS,
    MAX_EVIDENCE_BYTES,
    MAX_HANDOFF_FINDINGS,
    MAX_HANDOFF_REFS,
    MAX_LIMITATIONS,
    MAX_REF_VALUE,
    MAX_SUMMARY_CHARS,
    DeclaredCapability,
    DelegationChain,
    DelegationError,
    DelegationFailure,
    DelegationRefusal,
    DelegationRisk,
    EvidenceHandoff,
    ExecutionBudget,
    GateDecision,
    SpecialistDelegation,
    canonical_json,
    from_dict,
    handoff_integrity,
    sha256_hex,
    sha256_of,
)

__all__ = [
    "RISK_RANK",
    "RETRYABLE_FAILURES",
    "POLICY_ALLOWED",
    "ExecutionBudget",
    "DelegationRefusal",
    "GateDecision",
    "admit_hop",
    "argv_problems",
    "bound_handoff",
    "capability_risks",
    "gate_capability",
    "idempotency_key",
    "may_retry",
    "redact_handoff",
    "resolve_capability_argv",
    "seal_handoff",
    "start_chain",
    "verify_integrity",
]

RISK_RANK: dict[DelegationRisk, int] = {
    "LOCAL_READ": 0,
    "LOCAL_WRITE": 1,
    "EXTERNAL_READ": 2,
    "COST_BEARING": 3,
    "EXTERNAL_WRITE": 4,
    "DESTRUCTIVE": 5,
}

# Failures worth a controlled retry (attempt limit still applies); every
# other code is terminal.
RETRYABLE_FAILURES: frozenset[DelegationFailure] = frozenset(
    {"timeout", "runtime-error"}
)

# Levels allowed by declared policy alone. Everything else — including
# LOCAL_WRITE — requires the caller to name the level in ``authorized``
# (CLI: ``--authorize EXTERNAL_READ`` / ``--authorize COST_BEARING``).
POLICY_ALLOWED: frozenset[DelegationRisk] = frozenset({"LOCAL_READ"})

# Template placeholders. {cli}/{python}/{checkout}/{target} mirror the
# theforge convention; the peer-flag set ({job},{run_id},{profile},{region},
# {platform},{check}) covers the real sentinel/doctor verb surfaces. Every
# substituted value is always exactly one argv element — there is no shell,
# so metacharacters can never become commands.
_REQUIRED_PLACEHOLDERS = ("{cli}", "{python}", "{checkout}", "{target}")
_OPTIONAL_PLACEHOLDERS = ("{job}", "{run_id}", "{profile}", "{region}",
                          "{platform}", "{check}")
_PLACEHOLDERS = _REQUIRED_PLACEHOLDERS + _OPTIONAL_PLACEHOLDERS
# Placeholders whose substituted value is a filesystem path — traversal
# segments are refused. Peer flags (--job, --region…) are bounded scalars:
# control bytes are still refused, but '..' in a job name is not traversal.
_PATH_PLACEHOLDERS = frozenset({"{checkout}", "{target}"})
_MAX_ARGV_LEN = 256
_MAX_ARGV_CHARS = 8_192


# --- risk mapping ------------------------------------------------------------


def capability_risks(capability: DeclaredCapability) -> frozenset[DelegationRisk]:
    """Map a declared capability onto the 6-level risk vocabulary.

    ``risk`` (the 5-level OperationClass) maps positionally;
    ``external_cost`` adds ``COST_BEARING`` on every value except an explicit
    ``"none"`` — undeclared cost (``unknown``) is treated as possibly
    bearing, because "no external cost" is a positive claim a silent
    manifest never made.
    """
    op_map: dict[str, DelegationRisk] = {
        "read_only": "LOCAL_READ",
        "local_mutation": "LOCAL_WRITE",
        "external_read": "EXTERNAL_READ",
        "external_mutation": "EXTERNAL_WRITE",
        "destructive": "DESTRUCTIVE",
    }
    levels: set[DelegationRisk] = {op_map[capability.risk]}
    if capability.external_cost != "none":
        levels.add("COST_BEARING")
    return frozenset(levels)


def gate_capability(
    risks: frozenset[DelegationRisk] | set[DelegationRisk],
    *,
    authorized: frozenset[DelegationRisk] | set[DelegationRisk] = frozenset(),
    policy_allows_local_read: bool = True,
) -> GateDecision:
    """The policy gate over one capability's risk levels.

    ``LOCAL_READ`` is allowed by policy (unless the caller disables even
    that). Every other level — local writes, anything external, destructive,
    cost-bearing — requires the caller to have explicitly authorized the
    level. Deny-by-default: an undeclared level can never allow.
    """
    ordered = tuple(sorted(risks, key=lambda r: RISK_RANK[r]))
    allowed_levels = set(authorized)
    if policy_allows_local_read:
        allowed_levels.add("LOCAL_READ")
    missing = tuple(r for r in ordered if r not in allowed_levels)
    if not missing:
        return GateDecision(
            decision="allow",
            rule="policy-gate",
            reason="all declared risk levels allowed by policy or authorization",
            risks=ordered,
        )
    return GateDecision(
        decision="deny",
        rule="policy-gate",
        reason=("risk levels require explicit authorization: " + ", ".join(missing)),
        risks=ordered,
        missing=missing,
    )


def may_retry(
    code: DelegationFailure,
    risks: frozenset[DelegationRisk] | set[DelegationRisk],
    *,
    attempt: int,
    max_retries: int = 1,
) -> bool:
    """Controlled retries for safe operations only.

    A retry is admitted only when every declared risk of the operation is
    ``LOCAL_READ``, the failure is transient (``timeout``/``runtime-error``)
    and the attempt budget is not spent. Refusals, cycles, invalid data and
    any side-effecting operation are terminal.
    """
    if attempt >= max_retries:
        return False
    if code not in RETRYABLE_FAILURES:
        return False
    return set(risks) <= {"LOCAL_READ"}


# --- chain control -----------------------------------------------------------


def start_chain(
    delegation: SpecialistDelegation,
    *,
    correlation_id: str,
    timeout_budget_s: int = 600,
    max_hops: int = 4,
    cancellation_token: str = "",
) -> SpecialistDelegation:
    """Mint chain-control state for a fresh delegation: the consumer is hop 0
    of ``visited_providers``, so re-entering it later is a refused revisit."""
    chain = DelegationChain(
        correlation_id=correlation_id,
        delegation_depth=0,
        visited_providers=[delegation.consumer],
        max_hops=max_hops,
        timeout_budget_s=timeout_budget_s,
        cancellation_token=cancellation_token,
    )
    return replace(delegation, chain=chain)


def admit_hop(
    delegation: SpecialistDelegation,
    provider: str,
    *,
    elapsed_s: int = 0,
) -> SpecialistDelegation | DelegationRefusal:
    """Extend the delegation chain to ``provider``, or refuse with a named code.

    Checked in order: cancelled chain, exhausted hop/timeout budget, revisit
    of an already-visited provider (the origin consumer is visited by
    construction), and a provider the consumer never declared.
    """
    chain = delegation.chain
    if chain is None:
        return DelegationRefusal(
            code="invalid-input",
            detail="no delegation chain — mint one with start_chain first",
        )
    if chain.cancelled:
        return DelegationRefusal(
            code="cancelled",
            detail=f"chain {chain.correlation_id} was cancelled",
            provider=provider,
        )
    if chain.delegation_depth + 1 > chain.max_hops:
        return DelegationRefusal(
            code="budget-exhausted",
            detail=(
                f"hop budget exhausted: depth {chain.delegation_depth} "
                f"already at max_hops {chain.max_hops}"
            ),
            provider=provider,
        )
    remaining = chain.timeout_budget_s - max(0, elapsed_s)
    if remaining <= 0:
        return DelegationRefusal(
            code="budget-exhausted",
            detail=(
                f"timeout budget exhausted: {elapsed_s}s spent of "
                f"{chain.timeout_budget_s}s"
            ),
            provider=provider,
        )
    visited = set(chain.visited_providers) | {delegation.consumer}
    if provider in visited:
        return DelegationRefusal(
            code="cycle-detected",
            detail=(
                f"{provider!r} already visited in chain {chain.correlation_id} "
                f"({', '.join(chain.visited_providers)}) — delegation cycle refused"
            ),
            provider=provider,
        )
    if delegation.specialist(provider) is None:
        return DelegationRefusal(
            code="provider-absent",
            detail=f"{provider!r} is not declared by consumer {delegation.consumer!r}",
            provider=provider,
        )
    return replace(
        delegation,
        chain=DelegationChain(
            correlation_id=chain.correlation_id,
            delegation_depth=chain.delegation_depth + 1,
            visited_providers=[*chain.visited_providers, provider],
            max_hops=chain.max_hops,
            timeout_budget_s=remaining,
            cancellation_token=chain.cancellation_token,
        ),
    )


# --- argv and ref hygiene ----------------------------------------------------


def argv_problems(argv: list[str]) -> list[str]:
    """Problems in a resolved argv — deterministic checks, no execution."""
    problems: list[str] = []
    if not argv:
        problems.append("empty argv")
        return problems
    if len(argv) > _MAX_ARGV_LEN:
        problems.append(f"argv longer than {_MAX_ARGV_LEN} elements")
    if sum(len(a) for a in argv) > _MAX_ARGV_CHARS:
        problems.append(f"argv longer than {_MAX_ARGV_CHARS} chars")
    for i, arg in enumerate(argv):
        if not arg:
            problems.append(f"argv[{i}] is empty")
            continue
        if any(ord(ch) < 0x20 for ch in arg):
            problems.append(f"argv[{i}] contains control characters")
    return problems


def _check_substitution(value: str, *, name: str, path_like: bool) -> str | None:
    """Refuse control bytes in every substitution; refuse traversal in
    path-bearing ones (``{checkout}``, ``{target}``)."""
    if not value or any(ord(ch) < 0x20 for ch in value):
        return f"{name} substitution is empty or contains control characters"
    if path_like and ".." in value.replace("\\", "/").split("/"):
        return f"{name} substitution {value!r} must not contain '..' segments"
    return None


def resolve_capability_argv(
    template: list[str],
    *,
    cli_argv: list[str] | None = None,
    python: str | None = None,
    checkout: str | None = None,
    values: dict[str, str | None] | None = None,
) -> list[str] | DelegationRefusal:
    """Resolve a declared ``entrypoint`` template to a runnable argv.

    ``values`` maps *bare* placeholder names (``target``, ``job``,
    ``run_id``, ``profile``, ``region``, ``platform``, ``check``) to one argv
    element each. An optional placeholder bound to ``None``/empty is dropped
    together with the ``--flag`` token immediately before it, so
    ``--run-id {run_id}`` collapses cleanly when no run id is supplied. A
    required placeholder without a value, an unknown placeholder and a
    traversal-bearing substitution are named refusals, never crashes.
    """
    values = values or {}
    supplied = {
        "cli": None,  # handled via cli_argv
        "python": python,
        "checkout": checkout,
        **{k: v for k, v in values.items()},
    }
    resolved: list[str] = []
    for token in template:
        if token.startswith("{") and token.endswith("}"):
            name = token[1:-1]
            if token not in _PLACEHOLDERS:
                return DelegationRefusal(
                    code="invalid-input",
                    detail=f"unknown entrypoint placeholder {token!r}",
                )
            if token == "{cli}":  # noqa: S105 — a template placeholder, not a secret
                if not cli_argv:
                    return DelegationRefusal(
                        code="invalid-input",
                        detail="entrypoint needs {cli} but no cli argv was resolved",
                    )
                resolved.extend(cli_argv)
                continue
            value = supplied.get(name)
            if value is None or value == "":
                if token in _OPTIONAL_PLACEHOLDERS:
                    # Drop the flag token that precedes this placeholder
                    # (e.g. "--run-id"), so the pair vanishes cleanly.
                    if resolved and resolved[-1].startswith("--"):
                        resolved.pop()
                    continue
                return DelegationRefusal(
                    code="invalid-input",
                    detail=f"entrypoint needs {token} but no value was supplied",
                )
            if err := _check_substitution(
                value, name=token, path_like=token in _PATH_PLACEHOLDERS
            ):
                return DelegationRefusal(code="invalid-input", detail=err)
            resolved.append(value)
        else:
            resolved.append(token)
    if problems := argv_problems(resolved):
        return DelegationRefusal(
            code="invalid-input",
            detail="resolved argv invalid: " + "; ".join(problems),
        )
    return resolved


# --- evidence handoff hygiene -------------------------------------------------


def idempotency_key(
    source_provider: str,
    capability: str,
    run_id: str,
    input_fingerprint: str,
) -> str:
    """Deterministic idempotency key: same producer + capability + run +
    input fingerprint → same key, so a replayed delegation is detectable."""
    digest = sha256_of(
        {
            "capability": capability,
            "inputs": input_fingerprint,
            "run": run_id,
            "source": source_provider,
        }
    )
    return f"idem-{digest[:24]}"


def seal_handoff(handoff: EvidenceHandoff) -> EvidenceHandoff:
    """Return the envelope with its ``integrity`` hash bound to the content."""
    return replace(handoff, integrity=handoff_integrity(handoff))


def verify_integrity(handoff: EvidenceHandoff) -> bool:
    """True iff ``integrity`` equals the canonical hash of the rest. An
    unsealed envelope (``integrity=None``) is unverifiable, not valid."""
    return handoff.integrity is not None and handoff.integrity == handoff_integrity(handoff)


_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def bound_handoff(doc: dict[str, Any]) -> EvidenceHandoff:
    """Build an ``EvidenceHandoff`` from a provider-emitted document,
    truncating oversized collections instead of refusing the whole envelope.

    Free-text fields (finding ``summary``, ref ``detail``/summary ``value``,
    error ``detail``, ``limitations`` entries) are clipped to their caps —
    flagged by ``truncated=True``. Refs keep declaration order (first-N),
    findings keep the most severe first (ties by id), and items are dropped
    until the canonical size fits. ``status``/``error`` are preserved
    untouched; ``integrity`` is cleared (re-seal after bounding).

    Bounding shrinks collections and clips text — a *structural* violation
    (a malformed ref, an unknown enum value, a failed status without an
    error) is still a ``DelegationError``: bounding never repairs invalid
    data into a valid-looking envelope.
    """

    def clip(value: Any, cap: int) -> Any:
        return value[:cap] if isinstance(value, str) and len(value) > cap else value

    fields = dict(doc)
    clipped = False
    for refs_name in ("input_refs", "result_refs"):
        refs = fields.get(refs_name)
        if isinstance(refs, list):
            for item in refs:
                if not isinstance(item, dict):
                    continue
                cap = MAX_SUMMARY_CHARS if item.get("kind") == "summary" else MAX_REF_VALUE
                for key, limit in (("value", cap), ("detail", MAX_DETAIL_CHARS)):
                    if key in item and item[key] != clip(item[key], limit):
                        item[key] = clip(item[key], limit)
                        clipped = True
    findings_raw = fields.get("findings")
    if isinstance(findings_raw, list):
        for item in findings_raw:
            if isinstance(item, dict) and item.get("summary") != clip(
                item.get("summary", ""), MAX_SUMMARY_CHARS
            ):
                item["summary"] = clip(item.get("summary", ""), MAX_SUMMARY_CHARS)
                clipped = True
    error_raw = fields.get("error")
    if isinstance(error_raw, dict) and error_raw.get("detail") != clip(
        error_raw.get("detail", ""), MAX_DETAIL_CHARS
    ):
        error_raw["detail"] = clip(error_raw.get("detail", ""), MAX_DETAIL_CHARS)
        clipped = True
    limitations_raw = fields.get("limitations")
    if isinstance(limitations_raw, list):
        fields["limitations"] = [
            (clip(item, MAX_DETAIL_CHARS) if isinstance(item, str) else item)
            for item in limitations_raw
        ]
        clipped = clipped or fields["limitations"] != limitations_raw
    dropped = 0
    for name, cap in (
        ("input_refs", MAX_HANDOFF_REFS),
        ("result_refs", MAX_HANDOFF_REFS),
        ("findings", MAX_HANDOFF_FINDINGS),
        ("limitations", MAX_LIMITATIONS),
    ):
        items = fields.get(name)
        if isinstance(items, list) and len(items) > cap:
            dropped += len(items) - cap
            fields[name] = items[:cap]
    findings = fields.get("findings")
    if isinstance(findings, list):
        fields["findings"] = sorted(
            findings,
            key=lambda f: (_SEVERITY_RANK.get(f.get("severity"), 9), f.get("id", "")),
        )
    if dropped or clipped:
        fields["truncated"] = True
        fields["dropped"] = int(fields.get("dropped") or 0) + dropped
    fields["integrity"] = None  # truncated content invalidates any prior seal
    while _doc_bytes(fields) > MAX_EVIDENCE_BYTES:
        for name in ("findings", "result_refs", "input_refs", "limitations"):
            items = fields.get(name)
            if isinstance(items, list) and items:
                fields[name] = items[:-1]
                fields["truncated"] = True
                fields["dropped"] = int(fields.get("dropped") or 0) + 1
                break
        else:
            raise DelegationError(
                f"evidence handoff exceeds {MAX_EVIDENCE_BYTES} canonical bytes "
                "with no droppable collection left"
            )
    return from_dict(EvidenceHandoff, fields)


def _doc_bytes(fields: dict[str, Any]) -> int:
    return len(canonical_json(fields).encode("utf-8"))


# --- handoff redaction --------------------------------------------------------
#
# A small local scrub for provider-emitted free text before persistence.
# (sparkforge_aws cannot import theforge's security.redact.) Covers the
# credential shapes a log excerpt most often leaks: AWS access keys, bearer
# tokens and ``key=value`` secrets. Anything already-redacted (`***`) is
# stable — the scrub is idempotent.

_SECRET_VALUE_RE = re.compile(
    r"AKIA[0-9A-Z]{16}"                          # AWS access key id
    r"|ASIA[0-9A-Z]{16}"                         # AWS temporary key id
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|[A-Za-z0-9_=-]{20,}\.[A-Za-z0-9_=-]{10,}\.[A-Za-z0-9_=-]{10,}",  # JWT-ish
)
_KEY_VALUE_SECRET_RE = re.compile(
    r"(aws_secret_access_key|secret|token|password|api_?key)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


def _scrub(text: str, cap: int) -> str:
    text = _SECRET_VALUE_RE.sub("<redacted>", text)
    return _KEY_VALUE_SECRET_RE.sub("<redacted>", text)[:cap]


def redact_handoff(handoff: EvidenceHandoff) -> EvidenceHandoff:
    """Scrub every free-text field before persistence.

    Ids, refs, codes and hashes are structure, not secrets; ``summary``,
    ``detail`` and ``limitations`` entries are provider text and may carry
    credentials. Redacted text is clipped back to its field cap — a
    redaction can never make a field oversized. Invalidates ``integrity`` —
    re-seal after redaction.
    """
    return replace(
        handoff,
        input_refs=[
            replace(
                r,
                value=_scrub(r.value, MAX_SUMMARY_CHARS) if r.kind == "summary" else r.value,
                detail=_scrub(r.detail, MAX_DETAIL_CHARS),
            )
            for r in handoff.input_refs
        ],
        result_refs=[
            replace(
                r,
                value=_scrub(r.value, MAX_SUMMARY_CHARS) if r.kind == "summary" else r.value,
                detail=_scrub(r.detail, MAX_DETAIL_CHARS),
            )
            for r in handoff.result_refs
        ],
        findings=[
            replace(
                f,
                summary=_scrub(f.summary, MAX_SUMMARY_CHARS),
                evidence_refs=[_scrub(r, MAX_REF_VALUE) for r in f.evidence_refs],
            )
            for f in handoff.findings
        ],
        limitations=[_scrub(item, MAX_DETAIL_CHARS) for item in handoff.limitations],
        error=(
            replace(handoff.error, detail=_scrub(handoff.error.detail, MAX_DETAIL_CHARS))
            if handoff.error is not None
            else None
        ),
        redacted=True,
        integrity=None,
    )


def new_correlation_id() -> str:
    """A fresh chain id: ``dl-<sha256[:16]>`` over random bytes — bounded
    shape accepted by ``CORRELATION_ID`` (never a URL, no whitespace)."""
    import secrets

    return f"dl-{sha256_hex(secrets.token_bytes(16))[:16]}"
