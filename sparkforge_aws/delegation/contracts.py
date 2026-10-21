"""Peer-delegation contracts (lf-0029): mirror of the-forge's lf-0027/28 shapes.

The cross-forge integrations spec (``prompt_evo_integrations.md``, audited in
``forge-cli/docs/integration/``) names three contracts:
``forge/SpecialistCapability/v1``, ``forge/SpecialistDelegation/v1`` and
``forge/EvidenceHandoff/v1``. Inside the-forge they live in the
``theforge/<Name>/v1`` namespace (``contracts/specialist_capability.py``,
``contracts/specialist_delegation.py``, ``contracts/evidence_handoff.py``).

sparkforge_aws cannot import theforge (hard invariant: the core never imports
a sibling forge), so this module re-implements the SAME contract shapes
natively — same schema ids, same field names, same invariants — so a document
produced here is interchangeable with the one the-forge produces over the
wire. Where semantics had to be re-expressed, the function docstring names
the canonical implementation it mirrors.

Data-only rule (spec §12): nothing here is an instruction. ``entrypoint`` is
a typed argv template resolved through ``governance.resolve_capability_argv``
— never a shell string; findings/handoffs are DATA the consumer stores.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, TypeVar, get_type_hints

# ---------------------------------------------------------------------------
# Vocabulary (closed sets — a value outside them is invalid by construction)
# ---------------------------------------------------------------------------

class DelegationError(ValueError):
    """Contract violation in a delegation document or call.

    Raised at construction/parse time — never a control-flow signal a caller
    may ignore. Mirrors ``theforge.contracts.base.ContractError``.
    """


SPECIALIST_CAPABILITY_SCHEMA = "theforge/SpecialistCapability/v1"
SPECIALIST_DELEGATION_SCHEMA = "theforge/SpecialistDelegation/v1"
EVIDENCE_HANDOFF_SCHEMA = "theforge/EvidenceHandoff/v1"
PEER_DISCOVERY_SCHEMA = "sparkforge_aws/PeerDiscoveryReport/v1"

# Bundled/checkout file names a specialist uses to ship capability/agentic
# manifests (mirror of theforge CAPABILITY_MANIFEST_NAMES + forge.agentic.json).
CAPABILITY_MANIFEST_NAMES: tuple[str, ...] = (
    "forge.capabilities.json",
    "forge.capability.json",
)
AGENTIC_MANIFEST_NAME = "forge.agentic.json"

# "not pinned by the author — resolved at install/runtime".
RUNTIME_DETECTED = "runtime-detected"

PROVIDER_ID = re.compile(r"^[a-z][a-z0-9-]*$")
CAPABILITY_ID = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$")
CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DELEGATION_SLUG = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)

DISCOVERY_STATES: tuple[str, ...] = (
    "NOT_INSTALLED",
    "DISCOVERED",
    "VERIFIED",
    "INCOMPATIBLE",
    "DEGRADED",
    "UNAVAILABLE",
    "UNTRUSTED",
)
DiscoveryState = Literal[
    "NOT_INSTALLED", "DISCOVERED", "VERIFIED", "INCOMPATIBLE",
    "DEGRADED", "UNAVAILABLE", "UNTRUSTED",
]

DISCOVERY_SOURCES: tuple[str, ...] = (
    "path",
    "package",
    "entry-point",
    "bundled-manifest",
    "checkout",
    "probe",
)
DiscoverySource = Literal[
    "path", "package", "entry-point", "bundled-manifest", "checkout", "probe",
]

# The 6-level risk vocabulary (theforge DelegationRisk). Orthogonal to the
# 5-level OperationClass — ``external_cost`` != "none" adds COST_BEARING.
DelegationRisk = Literal[
    "LOCAL_READ", "LOCAL_WRITE", "EXTERNAL_READ",
    "EXTERNAL_WRITE", "DESTRUCTIVE", "COST_BEARING",
]
DELEGATION_RISKS: tuple[DelegationRisk, ...] = (
    "LOCAL_READ", "LOCAL_WRITE", "EXTERNAL_READ",
    "EXTERNAL_WRITE", "DESTRUCTIVE", "COST_BEARING",
)

# The named refusal/failure taxonomy — a failure is always one of these,
# never an anonymous error and never laundered into a success.
DelegationFailure = Literal[
    "provider-absent",
    "version-incompatible",
    "capability-absent",
    "invalid-input",
    "permission-denied",
    "timeout",
    "runtime-error",
    "invalid-output",
    "insufficient-evidence",
    "policy-refusal",
    "cycle-detected",
    "budget-exhausted",
    "cancelled",
]
DELEGATION_FAILURES: tuple[DelegationFailure, ...] = (
    "provider-absent", "version-incompatible", "capability-absent",
    "invalid-input", "permission-denied", "timeout", "runtime-error",
    "invalid-output", "insufficient-evidence", "policy-refusal",
    "cycle-detected", "budget-exhausted", "cancelled",
)

# Confidence levels are what the source declared — normalize_confidence maps
# foreign vocabularies as a *rename*, never a promotion: nothing maps
# POSSIBLE to CONFIRMED, and no code path exists to raise a level.
HandoffConfidence = Literal["POSSIBLE", "LIKELY", "CONFIRMED", "UNKNOWN"]

EvidenceStatus = Literal["completed", "partial", "failed", "refused", "cancelled"]
EvidenceRefKind = Literal["path", "ref", "summary"]
Severity = Literal["info", "low", "medium", "high", "critical"]
OperationClass = Literal[
    "read_only", "local_mutation", "external_read", "external_mutation", "destructive"
]
ExternalCost = Literal["none", "possible", "metered", "unknown"]
CapabilityExecutionMode = Literal["local", "remote", "hybrid"]

DelegationDiscovery = Literal["runtime", "declared", "off"]
DelegationExecution = Literal["governed", "manual", "forbidden"]

MAX_VISITED_PROVIDERS = 32
MAX_HANDOFF_REFS = 64
MAX_HANDOFF_FINDINGS = 128
MAX_REF_VALUE = 240
MAX_SUMMARY_CHARS = 2_000
MAX_DETAIL_CHARS = 500
MAX_LIMITATIONS = 64
MAX_EVIDENCE_BYTES = 262_144  # canonical JSON of the whole envelope

_FOREIGN_CONFIDENCE: dict[str, HandoffConfidence] = {
    # canonical spellings
    "possible": "POSSIBLE",
    "likely": "LIKELY",
    "confirmed": "CONFIRMED",
    "unknown": "UNKNOWN",
    # data-sentinel FindingStatus: CONFIRMED/PROBABLE/POSSIBLE/UNKNOWN
    "probable": "LIKELY",
    # forge-doctor-data / audit G15: HIGH/MEDIUM/LOW/UNKNOWN
    "high": "CONFIRMED",
    "medium": "LIKELY",
    "moderate": "LIKELY",
    "low": "POSSIBLE",
    "unresolved": "UNKNOWN",
}

_FOREIGN_SEVERITY: dict[str, Severity] = {
    # canonical spellings (lowercase theforge Severity)
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
    # forge-doctor-data Severity: pass|info|warning|error — `error` maps to
    # `high`, never `critical` (a rename, never an inflation).
    "warning": "medium",
    "error": "high",
    "pass": "info",
}


def normalize_confidence(value: str) -> HandoffConfidence:
    """Map a declared confidence onto the closed vocabulary — a rename, never
    a promotion. Unknown spellings are a DelegationError, not a guess."""
    level = _FOREIGN_CONFIDENCE.get(value.strip().lower())
    if level is None:
        raise DelegationError(
            f"unmapped confidence {value!r}; add an explicit mapping rule, "
            "never a guess (spec: POSSIBLE must never become CONFIRMED)"
        )
    return level


def normalize_severity(value: str) -> Severity:
    """Map a foreign severity onto the closed vocabulary — a rename, never
    an inflation. Unknown spellings are a DelegationError."""
    level = _FOREIGN_SEVERITY.get(value.strip().lower())
    if level is None:
        raise DelegationError(f"unmapped severity {value!r}")
    return level


# ---------------------------------------------------------------------------
# Canonical JSON / hashing helpers (mirror of contracts/canonical.py)
# ---------------------------------------------------------------------------

def canonical_json(obj: Any) -> str:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of(obj: Any) -> str:
    return sha256_hex(canonical_json(obj).encode("utf-8"))


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _check_sha256(value: str, *, field: str) -> None:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise DelegationError(
            f"{field}: invalid sha256 {value!r}, expected 64 lowercase hex chars"
        )


def check_evidence_ref(value: str, *, field: str) -> None:
    """A finding's pointer to its backing evidence: bounded, no whitespace,
    no traversal, no backslashes. Opaque pointer — stored, never resolved."""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_REF_VALUE
        or any(ch.isspace() for ch in value)
        or "\\" in value
        or ".." in value.split("/")
    ):
        raise DelegationError(
            f"{field}: invalid evidence ref {value!r} — bounded opaque pointer expected"
        )


# ---------------------------------------------------------------------------
# Dict<->dataclass codec (minimal mirror of contracts/base.py from_dict)
# ---------------------------------------------------------------------------

T = TypeVar("T")


def to_dict(obj: Any) -> dict[str, Any]:
    return {k: v for k, v in asdict(obj).items()}


def from_dict(cls: type[T], data: Any, path: str = "$") -> T:
    """Rebuild a contract dataclass from a JSON-shaped dict.

    Only the shapes this module declares are handled: dataclass fields, list,
    str/int/bool/None scalars and Literal validation by construction (the
    dataclass ``__post_init__`` invariants do the checking).
    """
    from dataclasses import MISSING, fields

    if not isinstance(data, dict):
        raise DelegationError(f"{path}: expected object, got {type(data).__name__}")
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for f in fields(cls):  # type: ignore[arg-type]
        if f.name not in data:
            if f.default is MISSING and f.default_factory is MISSING:
                raise DelegationError(f"{path}.{f.name}: required field missing")
            continue
        kwargs[f.name] = _coerce(hints[f.name], data[f.name], f"{path}.{f.name}")
    try:
        return cls(**kwargs)
    except (DelegationError, ValueError, TypeError) as exc:
        raise DelegationError(f"{path}: {exc}") from exc


def _coerce(tp: Any, value: Any, path: str) -> Any:
    import types as _types
    from dataclasses import is_dataclass
    from typing import Union, get_args, get_origin

    if tp is Any:
        return value
    origin = get_origin(tp)
    args = get_args(tp)
    if origin in (Union, _types.UnionType):
        if value is None and type(None) in args:
            return None
        errors: list[str] = []
        for member in args:
            if member is type(None):
                continue
            try:
                return _coerce(member, value, path)
            except DelegationError as exc:
                errors.append(str(exc))
        raise DelegationError(f"{path}: no union member matched ({'; '.join(errors)})")
    if origin is Literal:
        if not any(type(value) is type(a) and value == a for a in args):
            raise DelegationError(f"{path}: expected one of {list(args)}, got {value!r}")
        return value
    if origin is list:
        if not isinstance(value, list):
            raise DelegationError(f"{path}: expected array, got {type(value).__name__}")
        return [_coerce(args[0], item, f"{path}[{i}]") for i, item in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise DelegationError(f"{path}: expected object, got {type(value).__name__}")
        return {str(k): _coerce(args[1], v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(tp, type) and is_dataclass(tp):
        return from_dict(tp, value, path)
    return _coerce_scalar(tp, value, path)


def _coerce_scalar(tp: Any, value: Any, path: str) -> Any:
    if tp is str:
        if not isinstance(value, str):
            raise DelegationError(f"{path}: expected str, got {type(value).__name__}")
        return value
    if tp is bool:
        if not isinstance(value, bool):
            raise DelegationError(f"{path}: expected bool, got {type(value).__name__}")
        return value
    if tp is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise DelegationError(f"{path}: expected int, got {type(value).__name__}")
        return value
    return value


def _parse_semver(value: str) -> bool:
    return bool(_SEMVER_RE.match(value))


# ---------------------------------------------------------------------------
# theforge/SpecialistCapability/v1 — the discovery advertisement
# ---------------------------------------------------------------------------

CapabilityDiscoveryMode = Literal["manifest", "package", "registry", "entry-point", "probe"]
CapabilityVerificationMode = Literal["self-declared", "handshake", "probe"]


@dataclass(frozen=True, kw_only=True)
class SpecialistIdentity:
    """Who publishes the manifest: provider id, version, domain."""

    id: str
    version: str = "unknown"
    domain: str = ""

    def __post_init__(self) -> None:
        if not PROVIDER_ID.match(self.id):
            raise DelegationError(f"invalid specialist id {self.id!r}")
        if (
            self.version not in (RUNTIME_DETECTED, "unknown")
            and not _parse_semver(self.version)
        ):
            raise DelegationError(
                f"specialist {self.id}: version {self.version!r} is not SemVer 2.0.0 "
                f"(or {RUNTIME_DETECTED!r})"
            )


@dataclass(frozen=True, kw_only=True)
class SurfaceSupport:
    """A governed surface the specialist declares (``health``/``handoff``)."""

    supported: bool = False
    detail: str = ""


@dataclass(frozen=True, kw_only=True)
class DeclaredCapability:
    """One invocable capability declared by a specialist.

    ``entrypoint`` is a typed argv template (``{cli}``, ``{python}``,
    ``{checkout}``, ``{target}`` and peer flags like ``{job}``/``{region}``),
    resolved through ``governance.resolve_capability_argv`` — never a shell
    string. ``intents`` is the consumer-side routing vocabulary declared by
    the delegating forge (dotted slugs).
    """

    id: str
    description: str = ""
    version: str = ""
    input_schema: str = ""
    output_schema: str = ""
    entrypoint: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    execution_mode: CapabilityExecutionMode = "local"
    risk: OperationClass = "read_only"
    requires: list[str] = field(default_factory=list)
    optional_deps: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    network: bool = False
    external_cost: ExternalCost = "unknown"
    timeout_s: int | None = None
    limitations: list[str] = field(default_factory=list)
    discovery_mode: CapabilityDiscoveryMode = "manifest"
    verification_mode: CapabilityVerificationMode = "self-declared"

    def __post_init__(self) -> None:
        if not CAPABILITY_ID.match(self.id):
            raise DelegationError(f"invalid capability id {self.id!r}")
        if self.version and not _parse_semver(self.version):
            raise DelegationError(
                f"capability {self.id}: version {self.version!r} is not SemVer 2.0.0"
            )
        if self.timeout_s is not None and self.timeout_s <= 0:
            raise DelegationError(
                f"capability {self.id}: timeout_s must be a positive integer"
            )
        if self.execution_mode == "local" and self.network:
            raise DelegationError(
                f"capability {self.id}: network=True requires execution_mode "
                "'remote' or 'hybrid', not 'local'"
            )
        for intent in self.intents:
            if not DELEGATION_SLUG.match(intent):
                raise DelegationError(f"capability {self.id}: invalid intent slug {intent!r}")


@dataclass(frozen=True, kw_only=True)
class SpecialistCapability:
    """``theforge/SpecialistCapability/v1`` — one specialist's advertisement."""

    schema: str = SPECIALIST_CAPABILITY_SCHEMA
    specialist: SpecialistIdentity
    capabilities: list[DeclaredCapability] = field(default_factory=list)
    health: SurfaceSupport = field(default_factory=SurfaceSupport)
    handoff: SurfaceSupport = field(default_factory=SurfaceSupport)

    def __post_init__(self) -> None:
        if self.schema != SPECIALIST_CAPABILITY_SCHEMA:
            raise DelegationError(
                f"unsupported schema {self.schema!r}, expected {SPECIALIST_CAPABILITY_SCHEMA!r}"
            )
        ids = [c.id for c in self.capabilities]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise DelegationError(f"duplicate capability ids {dups}")

    def capability(self, capability_id: str) -> DeclaredCapability | None:
        return next((c for c in self.capabilities if c.id == capability_id), None)


# ---------------------------------------------------------------------------
# theforge/SpecialistDelegation/v1 — declaration + chain state
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class SpecialistRef:
    """One specialist the consumer may delegate to, scoped by intents.

    ``optional`` records the spec's semantics (``optional: true``): the
    consumer must degrade gracefully when the provider is absent — an absent
    optional specialist is a named refusal in the plan, never a failure of
    the consumer's own work.
    """

    provider: str
    optional: bool = True
    intents: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not PROVIDER_ID.match(self.provider):
            raise DelegationError(f"invalid specialist provider id {self.provider!r}")
        for intent in self.intents:
            if not DELEGATION_SLUG.match(intent):
                raise DelegationError(
                    f"specialist {self.provider}: invalid intent slug {intent!r}"
                )


@dataclass(frozen=True, kw_only=True)
class DelegationPolicy:
    """The policy block: discovery mode, execution mode, evidence, fallback.

    ``fallback`` names the consumer's own degrading path
    (``native-analysis`` in the spec example) — an opaque slug, never an
    instruction.
    """

    discovery: DelegationDiscovery = "runtime"
    execution: DelegationExecution = "governed"
    preserve_evidence: bool = True
    fallback: str = ""

    def __post_init__(self) -> None:
        if self.fallback and not DELEGATION_SLUG.match(self.fallback):
            raise DelegationError(f"invalid fallback slug {self.fallback!r}")


@dataclass(frozen=True, kw_only=True)
class DelegationChain:
    """Chain-control state travelling with an in-flight delegation.

    Invariants (mirrored from theforge DelegationChain):

    - ``visited_providers`` holds unique provider ids; when non-empty its
      first element is the consumer that minted the chain. Re-entering the
      origin is an admission-time ``cycle-detected``, never a loop.
    - ``delegation_depth`` counts hops already taken; ``max_hops`` caps them.
      ``depth > max_hops`` cannot be constructed.
    - ``timeout_budget_s`` is the *remaining* chain-wide budget in seconds.
    - ``cancelled=True`` means any further hop is refused ``cancelled``.
    """

    correlation_id: str = ""
    delegation_depth: int = 0
    visited_providers: list[str] = field(default_factory=list)
    max_hops: int = 4
    timeout_budget_s: int = 600
    cancellation_token: str = ""
    cancelled: bool = False

    def __post_init__(self) -> None:
        if self.correlation_id and not CORRELATION_ID.match(self.correlation_id):
            raise DelegationError(f"invalid correlation_id {self.correlation_id!r}")
        if self.cancellation_token and not CORRELATION_ID.match(self.cancellation_token):
            raise DelegationError(f"invalid cancellation_token {self.cancellation_token!r}")
        if self.delegation_depth < 0:
            raise DelegationError("delegation_depth must be >= 0")
        if self.max_hops < 1:
            raise DelegationError("max_hops must be >= 1")
        if self.delegation_depth > self.max_hops:
            raise DelegationError(
                f"delegation_depth {self.delegation_depth} exceeds max_hops {self.max_hops}"
            )
        if self.timeout_budget_s <= 0:
            raise DelegationError("timeout_budget_s must be a positive integer")
        if len(self.visited_providers) > MAX_VISITED_PROVIDERS:
            raise DelegationError("visited_providers exceed bound")
        for provider in self.visited_providers:
            if not PROVIDER_ID.match(provider):
                raise DelegationError(f"invalid visited provider id {provider!r}")
        if len(set(self.visited_providers)) != len(self.visited_providers):
            raise DelegationError(
                "visited_providers must be unique — a revisit is a cycle, "
                "refuse it at admission instead of encoding it"
            )
        if self.visited_providers:
            if len(self.visited_providers) != self.delegation_depth + 1:
                raise DelegationError(
                    f"visited_providers ({len(self.visited_providers)}) must be "
                    f"delegation_depth + 1 ({self.delegation_depth + 1})"
                )
        elif self.delegation_depth > 0:
            raise DelegationError(
                "delegation_depth > 0 requires visited_providers — the chain "
                "must record where it has been"
            )
        if self.cancelled and not self.cancellation_token:
            raise DelegationError("cancelled=True requires a cancellation_token")


@dataclass(frozen=True, kw_only=True)
class SpecialistDelegation:
    """``theforge/SpecialistDelegation/v1`` — declaration + chain state."""

    schema: str = SPECIALIST_DELEGATION_SCHEMA
    consumer: str
    specialists: list[SpecialistRef] = field(default_factory=list)
    policy: DelegationPolicy = field(default_factory=DelegationPolicy)
    chain: DelegationChain | None = None

    def __post_init__(self) -> None:
        if self.schema != SPECIALIST_DELEGATION_SCHEMA:
            raise DelegationError(
                f"unsupported schema {self.schema!r}, "
                f"expected {SPECIALIST_DELEGATION_SCHEMA!r}"
            )
        if not PROVIDER_ID.match(self.consumer):
            raise DelegationError(f"invalid consumer id {self.consumer!r}")
        ids = [s.provider for s in self.specialists]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise DelegationError(f"duplicate specialist refs {dups}")

    def specialist(self, provider: str) -> SpecialistRef | None:
        return next((s for s in self.specialists if s.provider == provider), None)


# ---------------------------------------------------------------------------
# theforge/EvidenceHandoff/v1 — the specialist→consumer envelope
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class EvidenceRef:
    """One pointer to an input or result: path, provider-native ref or summary."""

    kind: EvidenceRefKind
    value: str
    sha256: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.value:
            raise DelegationError(f"{self.kind} ref: value must be non-empty")
        if self.kind == "ref":
            if (
                len(self.value) > MAX_REF_VALUE
                or any(ch.isspace() for ch in self.value)
                or "\\" in self.value
                or ".." in self.value.split("/")
            ):
                raise DelegationError(
                    f"evidence ref {self.value!r} must be a bounded opaque '<scheme>:<id>'"
                )
        elif self.kind == "path":
            if (
                len(self.value) > MAX_REF_VALUE
                or self.value.startswith(("/", "~"))
                or "\\" in self.value
                or ":" in self.value
                or ".." in self.value.split("/")
            ):
                raise DelegationError(
                    f"path ref {self.value!r} must be a workspace-relative "
                    "POSIX path (no absolute, '~', drive or '..' segments)"
                )
        else:  # summary — the only ref that may hold spaces
            if len(self.value) > MAX_SUMMARY_CHARS:
                raise DelegationError(
                    f"summary ref exceeds {MAX_SUMMARY_CHARS} chars ({len(self.value)})"
                )
        if self.sha256 is not None:
            _check_sha256(self.sha256, field="evidence ref sha256")
        if len(self.detail) > MAX_DETAIL_CHARS:
            raise DelegationError("evidence ref detail exceeds bound")


@dataclass(frozen=True, kw_only=True)
class HandoffFinding:
    """One finding handed between specialists — a declaration echoed verbatim."""

    id: str
    severity: Severity
    confidence: HandoffConfidence
    summary: str = ""
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            raise DelegationError("finding id must be non-empty")
        if len(self.summary) > MAX_SUMMARY_CHARS:
            raise DelegationError(
                f"finding {self.id!r}: summary exceeds {MAX_SUMMARY_CHARS} chars"
            )
        for ref in self.evidence_refs:
            check_evidence_ref(ref, field=f"finding {self.id!r} evidence_refs")


@dataclass(frozen=True, kw_only=True)
class HandoffError:
    """The named failure of a delegated run — never an anonymous error."""

    code: DelegationFailure
    detail: str = ""
    retryable: bool = False

    def __post_init__(self) -> None:
        if self.retryable and self.code not in ("timeout", "runtime-error"):
            raise DelegationError(
                f"error {self.code!r} is not retryable — only transient "
                "execution failures (timeout, runtime-error) may be"
            )


@dataclass(frozen=True, kw_only=True)
class ResourceUsage:
    """Measured consumption; ``None`` = not measured (unknown is never zero)."""

    elapsed_ms: int | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    provider_tokens: int | None = None


@dataclass(frozen=True, kw_only=True)
class EvidenceHandoff:
    """``theforge/EvidenceHandoff/v1`` — the specialist→consumer envelope."""

    schema: str = EVIDENCE_HANDOFF_SCHEMA
    run_id: str
    correlation_id: str
    idempotency_key: str
    source_provider: str
    source_version: str = "unknown"
    consumer_provider: str = ""
    capability: str
    capability_version: str = ""
    status: EvidenceStatus = "completed"
    input_refs: list[EvidenceRef] = field(default_factory=list)
    result_refs: list[EvidenceRef] = field(default_factory=list)
    findings: list[HandoffFinding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    error: HandoffError | None = None
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    resources: ResourceUsage | None = None
    # sha256 of the canonical document with integrity=None — see
    # governance.seal_handoff / verify_integrity.
    integrity: str | None = None
    redacted: bool = False
    truncated: bool = False
    dropped: int = 0

    def __post_init__(self) -> None:
        if self.schema != EVIDENCE_HANDOFF_SCHEMA:
            raise DelegationError(
                f"unsupported schema {self.schema!r}, expected {EVIDENCE_HANDOFF_SCHEMA!r}"
            )
        for name in ("run_id", "correlation_id", "idempotency_key"):
            value = getattr(self, name)
            if not value or not CORRELATION_ID.match(value):
                raise DelegationError(f"invalid {name} {value!r}")
        if not PROVIDER_ID.match(self.source_provider):
            raise DelegationError(f"invalid source_provider {self.source_provider!r}")
        if not PROVIDER_ID.match(self.consumer_provider):
            raise DelegationError(f"invalid consumer_provider {self.consumer_provider!r}")
        if not CAPABILITY_ID.match(self.capability):
            raise DelegationError(f"invalid capability {self.capability!r}")
        if self.status in ("failed", "refused", "cancelled") and self.error is None:
            raise DelegationError(f"status {self.status!r} requires an error object")
        if self.status in ("completed", "partial") and self.error is not None:
            raise DelegationError(f"status {self.status!r} must not carry an error object")
        for name, refs in (("input_refs", self.input_refs), ("result_refs", self.result_refs)):
            if len(refs) > MAX_HANDOFF_REFS:
                raise DelegationError(f"{name} exceed bound {MAX_HANDOFF_REFS}")
        if len(self.findings) > MAX_HANDOFF_FINDINGS:
            raise DelegationError(f"findings exceed bound {MAX_HANDOFF_FINDINGS}")
        ids = [f.id for f in self.findings]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise DelegationError(f"duplicate finding ids {dups}")
        if len(self.limitations) > MAX_LIMITATIONS:
            raise DelegationError(f"limitations exceed bound {MAX_LIMITATIONS}")
        if self.integrity is not None:
            _check_sha256(self.integrity, field="integrity")
        if self.dropped < 0 or (self.dropped > 0 and not self.truncated):
            raise DelegationError("dropped > 0 requires truncated")
        if not self.created_at:
            raise DelegationError("created_at is required")
        self._check_size()

    def _check_size(self) -> None:
        """The canonical document is bounded — a whole log cannot fit."""
        size = len(canonical_json(to_dict(self)).encode("utf-8"))
        if size > MAX_EVIDENCE_BYTES:
            raise DelegationError(
                f"evidence handoff exceeds {MAX_EVIDENCE_BYTES} canonical bytes "
                f"({size}); pass refs and bounded summaries, never payloads — "
                "use governance.bound_handoff to truncate first"
            )


def handoff_integrity(handoff: EvidenceHandoff) -> str:
    """sha256 over the canonical envelope with ``integrity`` removed."""
    doc = to_dict(handoff)
    doc["integrity"] = None
    return sha256_of(doc)


# ---------------------------------------------------------------------------
# Peer discovery result (local shape — theforge SpecialistDiscovery mirror)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class DiscoveryEvidence:
    """One observed signal: where the specialist was seen + provenance."""

    source: DiscoverySource
    detail: str
    path: str | None = None
    sha256: str | None = None


@dataclass(frozen=True, kw_only=True)
class PeerDiscovery:
    """The resolved view of one specialist peer on this machine."""

    provider: str
    state: DiscoveryState = "NOT_INSTALLED"
    version: str = "unknown"
    cli_resolved: str = ""
    sources: list[DiscoveryEvidence] = field(default_factory=list)
    capability_manifest: SpecialistCapability | None = None
    # handshake | manifest | health -> PASS | FAIL | SKIP (+ detail in notes)
    checks: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class PeerDiscoveryReport:
    """A full peer-discovery pass for one consumer's declared specialists."""

    schema: str = PEER_DISCOVERY_SCHEMA
    generated_at: str = ""
    probed: bool = False
    entries: list[PeerDiscovery] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.schema != PEER_DISCOVERY_SCHEMA:
            raise DelegationError(
                f"unsupported schema {self.schema!r}, expected {PEER_DISCOVERY_SCHEMA!r}"
            )

    def entry(self, provider: str) -> PeerDiscovery | None:
        return next((e for e in self.entries if e.provider == provider), None)


# ---------------------------------------------------------------------------
# Governance + routing value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class DelegationRefusal:
    """A named refusal — the failure taxonomy applied, never silent."""

    code: DelegationFailure
    detail: str
    provider: str = ""


@dataclass(frozen=True, kw_only=True)
class GateDecision:
    """The outcome of gating one capability against policy + authorization."""

    decision: Literal["allow", "deny"]
    rule: str
    reason: str
    risks: tuple[DelegationRisk, ...] = ()
    missing: tuple[DelegationRisk, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ExecutionBudget:
    """A chain-wide execution budget: hops, seconds, providers, output bytes."""

    max_hops: int = 4
    timeout_budget_s: int = 600
    max_providers: int = 4
    max_output_bytes: int = MAX_EVIDENCE_BYTES


@dataclass(frozen=True, kw_only=True)
class DelegationPick:
    """One selected specialist capability, with the evidence that chose it."""

    provider: str
    capability: str
    capability_version: str = ""
    risks: tuple[DelegationRisk, ...] = ()
    entrypoint: list[str] = field(default_factory=list)
    justification: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class DelegationPlan:
    """The router's answer: picks, refusals and an honest status.

    ``ambiguous`` carries the competing providers/capabilities in
    ``unknowns``; ``refused``/``unavailable`` name their codes in
    ``refusals``. A plan never contains an anonymous failure.
    """

    status: Literal["planned", "ambiguous", "unavailable", "refused"]
    picks: list[DelegationPick] = field(default_factory=list)
    refusals: list[DelegationRefusal] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ExecResult:
    """A completed governed subprocess run — the raw material for parsing.

    ``returncode`` is data, not a verdict: the caller's output parser decides
    whether a non-zero code is a failure (``runtime-error``) or semantics
    (forge-doctor-data exits 1 when findings exist at or above the gate
    threshold — that is a *result*, not a crash).
    """

    argv: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_truncated: bool = False
    stderr_truncated: bool = False
