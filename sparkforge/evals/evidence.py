"""Canonical, provider-neutral evaluation evidence bundles."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

EVIDENCE_SCHEMA_VERSION = 1
EXECUTION_MODES = frozenset({"surrogate", "recorded_host", "live_external"})
ADAPTERS = frozenset({"fixture", "bundle_file", "authorized_command"})
_HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


class EvidenceBundleError(ValueError):
    """Named validation failure at the evidence boundary."""


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceBundleError(f"evidence_bundle_invalid:{field}")
    return value.strip()


def _hash(value: Any, field: str) -> str:
    result = _text(value, field)
    if not _HASH_RE.fullmatch(result):
        raise EvidenceBundleError(f"evidence_bundle_invalid:{field}_sha256")
    return result.removeprefix("sha256:")


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceBundleError(f"evidence_bundle_invalid:{field}")
    return dict(value)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """A typed, content-addressed reference used by a promotion gate."""

    kind: str
    ref: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], index: int) -> EvidenceRef:
        return cls(
            kind=_text(value.get("kind"), f"evidence_refs[{index}].kind"),
            ref=_text(value.get("ref"), f"evidence_refs[{index}].ref"),
            sha256=_hash(value.get("sha256"), f"evidence_refs[{index}].sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "ref": self.ref, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class EvaluationEvidenceBundle:
    """Validated evidence shared by file and authorized-command adapters."""

    schema_version: int
    candidate: dict[str, Any]
    suite: dict[str, Any]
    execution: dict[str, Any]
    transcripts: dict[str, Any]
    reports: dict[str, Any]
    metrics: dict[str, Any]
    policy: dict[str, Any]
    evidence_refs: tuple[EvidenceRef, ...]
    rollback_target: str
    unresolved: tuple[str, ...]
    bundle_id: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> EvaluationEvidenceBundle:
        if not isinstance(raw, Mapping):
            raise EvidenceBundleError("evidence_bundle_invalid:root")
        if raw.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
            raise EvidenceBundleError("evidence_bundle_unsupported:schema_version")
        candidate = _mapping(raw.get("candidate"), "candidate")
        suite = _mapping(raw.get("suite"), "suite")
        execution = _mapping(raw.get("execution"), "execution")
        transcripts = _mapping(raw.get("transcripts", {}), "transcripts")
        reports = _mapping(raw.get("reports"), "reports")
        metrics = _mapping(raw.get("metrics"), "metrics")
        policy = _mapping(raw.get("policy"), "policy")

        for field in (
            "id",
            "version",
            "candidate_digest",
            "contract_id",
            "contract_version",
            "kind",
        ):
            _text(candidate.get(field), f"candidate.{field}")
        _hash(candidate.get("candidate_digest"), "candidate.candidate_digest")
        if candidate.get("parent_digest") is not None:
            _hash(candidate.get("parent_digest"), "candidate.parent_digest")
        _text(candidate.get("family", candidate.get("kind")), "candidate.family")
        _hash(candidate.get("contract_sha256"), "candidate.contract_sha256")

        _text(suite.get("suite_id"), "suite.suite_id")
        _hash(suite.get("suite_sha256"), "suite.suite_sha256")
        _hash(suite.get("input_manifest_sha256"), "suite.input_manifest_sha256")

        mode = _text(execution.get("mode"), "execution.mode")
        if mode not in EXECUTION_MODES:
            raise EvidenceBundleError(f"evidence_bundle_invalid:execution.mode:{mode}")
        adapter = _text(execution.get("adapter"), "execution.adapter")
        if adapter not in ADAPTERS:
            raise EvidenceBundleError(f"evidence_bundle_invalid:execution.adapter:{adapter}")
        if mode == "live_external" and adapter != "authorized_command":
            raise EvidenceBundleError("evidence_bundle_invalid:execution.adapter_for_live_external")
        if mode == "live_external":
            _text(execution.get("command_id"), "execution.command_id")
            producer_identity = execution.get("producer_identity")
            if not isinstance(producer_identity, (str, Mapping)) or not producer_identity:
                raise EvidenceBundleError("evidence_bundle_invalid:execution.producer_identity")
            command_identity = execution.get("command_identity_sha256")
            if command_identity is not None:
                _hash(command_identity, "execution.command_identity_sha256")
            if isinstance(producer_identity, Mapping):
                producer_command_identity = producer_identity.get("command_identity_sha256")
                if producer_command_identity is not None:
                    _hash(
                        producer_command_identity,
                        "execution.producer_identity.command_identity_sha256",
                    )
        sequence = execution.get("sequence", 1)
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise EvidenceBundleError("evidence_bundle_invalid:execution.sequence")

        for side in ("baseline", "candidate"):
            if side in transcripts and transcripts[side] is not None:
                transcript = _mapping(transcripts[side], f"transcripts.{side}")
                _hash(transcript.get("sha256"), f"transcripts.{side}.sha256")
                _text(transcript.get("source_ref"), f"transcripts.{side}.source_ref")
        for side in ("baseline", "candidate"):
            if not isinstance(reports.get(side), Mapping):
                raise EvidenceBundleError(f"evidence_bundle_invalid:reports.{side}")
        for field in ("comparison", "quality", "economy"):
            if not isinstance(metrics.get(field), Mapping):
                raise EvidenceBundleError(f"evidence_bundle_invalid:metrics.{field}")

        for field in ("policy_id", "policy_version"):
            _text(policy.get(field), f"policy.{field}")
        _hash(policy.get("policy_sha256"), "policy.policy_sha256")

        refs_raw = raw.get("evidence_refs", ())
        if isinstance(refs_raw, (str, bytes)) or not isinstance(refs_raw, Sequence):
            raise EvidenceBundleError("evidence_bundle_invalid:evidence_refs")
        refs = tuple(
            sorted(
                (
                    EvidenceRef.from_mapping(ref, index)
                    for index, ref in enumerate(refs_raw)
                    if isinstance(ref, Mapping)
                ),
                key=lambda item: (item.kind, item.ref, item.sha256),
            )
        )
        if len(refs) != len(refs_raw):
            raise EvidenceBundleError("evidence_bundle_invalid:evidence_refs.item")
        rollback_target = _hash(raw.get("rollback_target"), "rollback_target")
        unresolved_raw = raw.get("unresolved", ())
        if isinstance(unresolved_raw, (str, bytes)) or not isinstance(unresolved_raw, Sequence):
            raise EvidenceBundleError("evidence_bundle_invalid:unresolved")
        unresolved = tuple(sorted({_text(item, "unresolved.item") for item in unresolved_raw}))

        normalized = cls(
            schema_version=EVIDENCE_SCHEMA_VERSION,
            candidate=candidate,
            suite=suite,
            execution=execution,
            transcripts=transcripts,
            reports=reports,
            metrics=metrics,
            policy=policy,
            evidence_refs=refs,
            rollback_target=rollback_target,
            unresolved=unresolved,
            bundle_id="",
        )
        expected = canonical_digest(normalized._body())
        declared = raw.get("bundle_id")
        if declared is not None and _hash(declared, "bundle_id") != expected:
            raise EvidenceBundleError("evidence_bundle_digest_mismatch")
        return replace(normalized, bundle_id=expected)

    def _body(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate": self.candidate,
            "suite": self.suite,
            "execution": self.execution,
            "transcripts": self.transcripts,
            "reports": self.reports,
            "metrics": self.metrics,
            "policy": self.policy,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "rollback_target": self.rollback_target,
            "unresolved": list(self.unresolved),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._body(), "bundle_id": self.bundle_id}

    @property
    def candidate_digest(self) -> str:
        return str(self.candidate["candidate_digest"]).removeprefix("sha256:")

    @property
    def parent_digest(self) -> str | None:
        value = self.candidate.get("parent_digest")
        return str(value).removeprefix("sha256:") if value is not None else None

    @property
    def suite_sha256(self) -> str:
        return str(self.suite["suite_sha256"]).removeprefix("sha256:")

    @property
    def policy_sha256(self) -> str:
        return str(self.policy["policy_sha256"]).removeprefix("sha256:")

    @property
    def execution_mode(self) -> str:
        return str(self.execution["mode"])

    @property
    def evidence_kinds(self) -> tuple[str, ...]:
        return tuple(sorted({ref.kind for ref in self.evidence_refs}))


__all__ = [
    "ADAPTERS",
    "EVIDENCE_SCHEMA_VERSION",
    "EXECUTION_MODES",
    "EvidenceBundleError",
    "EvidenceRef",
    "EvaluationEvidenceBundle",
    "canonical_digest",
]
