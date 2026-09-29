"""Provider-neutral replay protocol for bounded host decisions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from sparkforge.decision.contracts import ContractLoader, ContractValidationError
from sparkforge.decision.fingerprint import digest
from sparkforge.decision.models import DecisionStatus
from sparkforge.decision.runtime import BoundedDecisionKernel

HOST_SCHEMA_VERSION = 1
HOST_PROTOCOL_VERSION = "bounded-host-v1"
MAX_HOST_TURNS = 128
MAX_TURN_CONTENT = 65536
_ROLES = frozenset({"system", "user", "assistant", "tool"})


class HostProtocolError(ValueError):
    """Named, fail-closed host envelope error."""


@dataclass(frozen=True, slots=True)
class HostEnvelope:
    schema_version: int
    case_id: str
    contract_id: str
    contract_version: str
    request: dict[str, Any]
    transcript_hash: str
    turns: tuple[dict[str, Any], ...]
    usage: dict[str, Any] | None = None
    cost_basis: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> HostEnvelope:
        if not isinstance(raw, Mapping):
            raise HostProtocolError("host_envelope_invalid:root")
        schema_version = raw.get("schema_version")
        if schema_version != HOST_SCHEMA_VERSION:
            raise HostProtocolError("host_envelope_unsupported:schema_version")
        values: dict[str, str] = {}
        for field_name in ("case_id", "contract_id", "contract_version", "transcript_hash"):
            value = raw.get(field_name)
            if not isinstance(value, (str, int)) or not str(value).strip():
                raise HostProtocolError(f"host_envelope_invalid:{field_name}")
            values[field_name] = str(value).strip()
        request = raw.get("request")
        if not isinstance(request, Mapping):
            raise HostProtocolError("host_envelope_invalid:request")
        state = request.get("state")
        if not isinstance(state, Mapping):
            raise HostProtocolError("host_envelope_invalid:request.state")
        turns_raw = raw.get("turns")
        if not isinstance(turns_raw, list) or not turns_raw:
            raise HostProtocolError("host_envelope_invalid:turns")
        if len(turns_raw) > MAX_HOST_TURNS:
            raise HostProtocolError("host_envelope_invalid:turns_bounded")
        turns: list[dict[str, Any]] = []
        for index, turn in enumerate(turns_raw):
            if not isinstance(turn, Mapping):
                raise HostProtocolError(f"host_envelope_invalid:turns[{index}]")
            role = turn.get("role")
            content = turn.get("content")
            if role not in _ROLES:
                raise HostProtocolError(f"host_envelope_invalid:turns[{index}].role")
            if not isinstance(content, str):
                raise HostProtocolError(f"host_envelope_invalid:turns[{index}].content")
            if len(content) > MAX_TURN_CONTENT:
                raise HostProtocolError(f"host_envelope_invalid:turns[{index}].content_bounded")
            turns.append({"role": str(role), "content": content})
        usage = raw.get("usage")
        cost_basis = raw.get("cost_basis")
        if usage is not None and not isinstance(usage, Mapping):
            raise HostProtocolError("host_envelope_invalid:usage")
        if cost_basis is not None and not isinstance(cost_basis, Mapping):
            raise HostProtocolError("host_envelope_invalid:cost_basis")
        return cls(
            schema_version=HOST_SCHEMA_VERSION,
            case_id=values["case_id"],
            contract_id=values["contract_id"],
            contract_version=values["contract_version"],
            request=dict(request),
            transcript_hash=values["transcript_hash"],
            turns=tuple(turns),
            usage=dict(usage) if usage is not None else None,
            cost_basis=dict(cost_basis) if cost_basis is not None else None,
        )

    def canonical(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "request": self.request,
            "transcript_hash": self.transcript_hash,
            "turns": list(self.turns),
            "usage": self.usage,
            "cost_basis": self.cost_basis,
        }

    @property
    def envelope_hash(self) -> str:
        return digest(self.canonical())

    def transcript_payload(self) -> dict[str, Any]:
        """Canonical content used to bind usage to one recorded transcript."""
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "request": self.request,
            "turns": list(self.turns),
        }

    @property
    def transcript_sha256(self) -> str:
        return digest(self.transcript_payload())

    def transcript_integrity(self) -> tuple[str, ...]:
        expected = self.transcript_sha256
        unresolved: list[str] = []
        if self.transcript_hash != expected:
            unresolved.append("transcript_hash_mismatch")
        if self.usage is not None and self.usage.get("transcript_sha256") != expected:
            unresolved.append("usage_transcript_hash_mismatch")
        return tuple(unresolved)

    def usage_state(self) -> dict[str, Any]:
        return _usage_state(self.usage)


@dataclass(frozen=True, slots=True)
class HostReplayResult:
    case_id: str
    status: str
    semantic_result: dict[str, Any] | None
    receipt_identity: dict[str, Any] | None
    provider_tokens: dict[str, int] | None
    tokens_unresolved: bool
    cost_basis: dict[str, Any] | None
    transcript_sha256: str | None = None
    unresolved: tuple[str, ...] = ()
    refusal_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": HOST_SCHEMA_VERSION,
            "protocol_version": HOST_PROTOCOL_VERSION,
            "case_id": self.case_id,
            "status": self.status,
            "semantic_result": self.semantic_result,
            "receipt_identity": self.receipt_identity,
            "provider_tokens": self.provider_tokens,
            "tokens_unresolved": self.tokens_unresolved,
            "cost_basis": self.cost_basis,
            "transcript_sha256": self.transcript_sha256,
            "unresolved": list(self.unresolved),
            "refusal_reason": self.refusal_reason,
        }


@runtime_checkable
class BoundedHostProvider(Protocol):
    """Host boundary implemented by replay-only adapters in the core."""

    protocol_version: str

    def replay(self, envelope: HostEnvelope) -> HostReplayResult:
        """Replay recorded input through local deterministic code only."""
        ...


class ReplayHostAdapter:
    """Replay structured host envelopes without provider or network access."""

    protocol_version = HOST_PROTOCOL_VERSION

    def __init__(
        self,
        repo: str = ".",
        *,
        loader: ContractLoader | None = None,
        kernel: BoundedDecisionKernel | None = None,
    ) -> None:
        self.loader = loader or ContractLoader(repo)
        self.kernel = kernel or BoundedDecisionKernel()

    def replay_mapping(self, raw: Mapping[str, Any]) -> HostReplayResult:
        return replay_host_mapping(raw, self)

    def replay(self, envelope: HostEnvelope) -> HostReplayResult:
        integrity = envelope.transcript_integrity()
        usage_state = _usage_state(envelope.usage, expected_hash=envelope.transcript_sha256)
        try:
            contract = self.loader.load(envelope.contract_id, envelope.contract_version)
            state = envelope.request["state"]
            evaluation = self.kernel.evaluate(contract, state, now="1970-01-01T00:00:00+00:00")
        except (ContractValidationError, KeyError, TypeError, ValueError) as exc:
            reason = f"host_replay_refused:{type(exc).__name__}"
            return HostReplayResult(
                case_id=envelope.case_id,
                status=DecisionStatus.REFUSED.value,
                semantic_result=None,
                receipt_identity=None,
                provider_tokens=usage_state.get("provider_tokens"),
                tokens_unresolved=bool(usage_state.get("tokens_unresolved", True)),
                cost_basis=envelope.cost_basis,
                transcript_sha256=envelope.transcript_sha256,
                unresolved=(reason,),
                refusal_reason=reason,
            )
        receipt = evaluation.receipt
        semantic = evaluation.result.to_dict()
        identity = {
            "contract": receipt["contract"],
            "fingerprint": receipt["fingerprint"],
            "state_fingerprint": receipt["state_fingerprint"],
        }
        return HostReplayResult(
            case_id=envelope.case_id,
            status=evaluation.result.status.value,
            semantic_result=semantic,
            receipt_identity=identity,
            provider_tokens=usage_state.get("provider_tokens"),
            tokens_unresolved=bool(usage_state.get("tokens_unresolved", True)),
            cost_basis=envelope.cost_basis,
            transcript_sha256=envelope.transcript_sha256,
            unresolved=tuple(
                dict.fromkeys(tuple(integrity) + tuple(usage_state.get("unresolved", ())))
            ),
        )


__all__ = [
    "BoundedHostProvider",
    "HOST_PROTOCOL_VERSION",
    "HOST_SCHEMA_VERSION",
    "HostEnvelope",
    "HostProtocolError",
    "HostReplayResult",
    "ReplayHostAdapter",
    "replay_host_mapping",
]


def replay_host_mapping(
    raw: Mapping[str, Any], adapter: BoundedHostProvider
) -> HostReplayResult:
    """Validate a host mapping before passing it to a bounded adapter."""
    try:
        envelope = HostEnvelope.from_mapping(raw)
    except HostProtocolError as exc:
        return HostReplayResult(
            case_id=(
                str(raw.get("case_id", "unknown"))
                if isinstance(raw, Mapping)
                else "unknown"
            ),
            status=DecisionStatus.REFUSED.value,
            semantic_result=None,
            receipt_identity=None,
            provider_tokens=None,
            tokens_unresolved=True,
            cost_basis=None,
            transcript_sha256=None,
            unresolved=(str(exc),),
            refusal_reason=str(exc),
        )
    return adapter.replay(envelope)


def _usage_state(
    raw: Mapping[str, Any] | None, *, expected_hash: str | None = None
) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("provider_tokens") is None:
        return {
            "provider_tokens": None,
            "tokens_unresolved": True,
            "unresolved_reason": "host_transcript_absent",
        }
    tokens = raw.get("provider_tokens")
    transcript_hash = raw.get("transcript_sha256")
    if (
        not isinstance(tokens, Mapping)
        or not isinstance(transcript_hash, str)
        or not transcript_hash.strip()
    ):
        return {
            "provider_tokens": None,
            "tokens_unresolved": True,
            "unresolved_reason": "provider_tokens_invalid",
        }
    try:
        input_tokens = int(tokens["input_tokens"])
        output_tokens = int(tokens["output_tokens"])
    except (KeyError, TypeError, ValueError):
        return {
            "provider_tokens": None,
            "tokens_unresolved": True,
            "unresolved_reason": "provider_tokens_invalid",
        }
    if input_tokens < 0 or output_tokens < 0:
        return {
            "provider_tokens": None,
            "tokens_unresolved": True,
            "unresolved_reason": "provider_tokens_invalid",
        }
    if expected_hash is not None and transcript_hash.strip() != expected_hash:
        return {
            "provider_tokens": None,
            "tokens_unresolved": True,
            "unresolved_reason": "usage_transcript_hash_mismatch",
            "unresolved": ("usage_transcript_hash_mismatch",),
        }
    return {
        "provider_tokens": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
        "tokens_unresolved": False,
        "source": "host_transcript",
        "transcript_sha256": transcript_hash.strip(),
        "unresolved": (),
    }
