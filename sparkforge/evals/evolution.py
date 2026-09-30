"""Offline prompt and agent candidate lifecycle.

Candidate content is immutable and content-addressed. This module coordinates
local registry validation, replay evidence, lifecycle transitions and receipts;
it never calls a model or an external service.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, overload

import yaml

from sparkforge.decision.authority import AuthorityPolicy, PromotionEvidence
from sparkforge.decision.fingerprint import digest
from sparkforge.evals.decision_replay import (
    Runner,
    compare_replay_benchmark,
    load_replay_suite,
    run_replay_benchmark,
    split_replay_benchmark,
)
from sparkforge.evals.evidence import EvaluationEvidenceBundle, EvidenceBundleError
from sparkforge.evals.evidence_resolver import EvidenceResolutionError, EvidenceResolver
from sparkforge.evals.lifecycle import (
    EffectiveCandidate,
    LifecycleProjectionError,
    LifecycleProjector,
)
from sparkforge.evals.policy import EvaluationPolicy, EvaluationPolicyError, PolicyResolver

SCHEMA_VERSION = 1
REGISTRY_PATH = Path("config/evolution/prompt_agents.yaml")
DEFAULT_SUITE_PATH = Path("evals/token_efficient/fixtures/decision_control_plane_cases.yaml")


class EvolutionError(ValueError):
    """Named candidate registry, evaluation or lifecycle failure."""


class CandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    EVALUATED = "evaluated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


ALLOWED_TRANSITIONS: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.CANDIDATE: frozenset(
        {CandidateStatus.EVALUATED, CandidateStatus.REJECTED}
    ),
    CandidateStatus.EVALUATED: frozenset({CandidateStatus.ACCEPTED, CandidateStatus.REJECTED}),
    CandidateStatus.ACCEPTED: frozenset({CandidateStatus.ROLLED_BACK}),
    CandidateStatus.REJECTED: frozenset(),
    CandidateStatus.ROLLED_BACK: frozenset(),
}

_CANDIDATE_FIELDS = frozenset(
    {
        "id",
        "version",
        "kind",
        "content",
        "content_path",
        "content_sha256",
        "candidate_digest",
        "candidate_type",
        "contract_id",
        "contract_version",
        "contract_sha256",
        "calibration_version",
        "parent_digest",
        "status",
        "family",
    }
)
_REGISTRY_FIELDS = frozenset(
    {
        "schema_version",
        "registry_id",
        "candidate_root",
        "benchmark_suite",
        "require_domain_holdout",
        "authority",
        "evaluation_policy",
        "policy_version",
        "policies",
        "external_commands",
        "receipt_lock",
        "candidates",
    }
)
_AUTHORITY_FIELDS = frozenset(
    {
        "require_content_digest",
        "require_parent_digest_for_mutation",
        "require_evaluation_receipt",
        "require_rollback_target",
        "require_contract_sha256",
    }
)


@dataclass(frozen=True, slots=True)
class EvolutionAuthorityPolicy:
    require_content_digest: bool = True
    require_parent_digest_for_mutation: bool = True
    require_evaluation_receipt: bool = True
    require_rollback_target: bool = True
    require_contract_sha256: bool = True


@dataclass(frozen=True, slots=True)
class EvaluationGatePolicy:
    min_status_accuracy: float = 1.0
    min_evidence_recall: float = 1.0
    max_false_positive_rate: float = 0.0
    max_quality_regression: float = 0.0
    min_route_accuracy: float | None = None
    max_route_regression: float = 0.0
    require_route_metric: bool = False
    max_payload_regression: float = 0.0
    max_token_regression: float = 0.0
    max_cost_regression: float = 0.0
    require_tokens: bool = False
    require_cost: bool = False


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_id: str
    version: str
    kind: str
    content: str
    contract_id: str
    contract_version: str
    calibration_version: str
    parent_digest: str | None = None
    status: CandidateStatus = CandidateStatus.CANDIDATE
    contract_sha256: str | None = None
    candidate_type: str = "root"
    family: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_id",
            "version",
            "kind",
            "contract_id",
            "contract_version",
            "calibration_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise EvolutionError(f"candidate_{field_name}_required")
        if not isinstance(self.content, str):
            raise EvolutionError("candidate_content_must_be_text")
        if self.parent_digest is not None and not isinstance(self.parent_digest, str):
            raise EvolutionError("candidate_parent_digest_must_be_text")
        if self.contract_sha256 is not None and (
            not isinstance(self.contract_sha256, str) or not self.contract_sha256.strip()
        ):
            raise EvolutionError("candidate_contract_sha256_invalid")
        if not isinstance(self.candidate_type, str):
            raise EvolutionError("candidate_type_must_be_text")
        if not isinstance(self.family, str):
            raise EvolutionError("candidate_family_must_be_text")
        if not self.family.strip():
            object.__setattr__(self, "family", self.kind)
        if self.candidate_type not in {"root", "mutation"}:
            raise EvolutionError("candidate_type_invalid")
        if self.candidate_type == "mutation" and self.parent_digest is None:
            raise EvolutionError("candidate_parent_digest_required_for_mutation")
        if self.candidate_type == "root" and self.parent_digest is not None:
            raise EvolutionError("root_candidate_cannot_have_parent")
        if self.parent_digest is not None and not self.parent_digest.strip():
            raise EvolutionError("candidate_parent_digest_empty")

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def candidate_digest(self) -> str:
        return digest(self.identity_dict())

    def identity_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "version": self.version,
            "kind": self.kind,
            "content": self.content,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "calibration_version": self.calibration_version,
            "parent_digest": self.parent_digest,
            "candidate_type": self.candidate_type,
        }

    def to_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        value = {
            "candidate_id": self.candidate_id,
            "version": self.version,
            "kind": self.kind,
            "candidate_digest": self.candidate_digest,
            "content_sha256": self.content_sha256,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "calibration_version": self.calibration_version,
            "parent_digest": self.parent_digest,
            "candidate_type": self.candidate_type,
            "family": self.family,
            "status": self.status.value,
        }
        if include_content:
            value["content"] = self.content
        return value


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate_digest: str
    suite_sha256: str
    labeled_tasks: int
    quality_gate: bool
    economy_gate: bool
    ci_verified: bool
    evidence_refs: tuple[str, ...]
    rollback_target: str
    comparison: dict[str, Any]
    status: CandidateStatus = CandidateStatus.EVALUATED
    parent_digest: str | None = None
    quality_metrics: dict[str, Any] = field(default_factory=dict)
    economy_metrics: dict[str, Any] = field(default_factory=dict)
    gate_reasons: tuple[str, ...] = ()
    rollback_required: bool = True
    metrics_derived: bool = False
    corpus_gate: bool = True
    policy_id: str = "legacy"
    policy_version: str = "legacy"
    policy_sha256: str = ""
    bundle_id: str = ""
    execution_mode: str = "surrogate"
    input_manifest_sha256: str = ""
    evidence_ref_kinds: tuple[str, ...] = ()
    verified_evidence_refs: tuple[str, ...] = ()
    verified_evidence_kinds: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    evidence_verified: bool = False
    producer_identity_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_digest, str) or not self.candidate_digest.strip():
            raise EvolutionError("evaluation_candidate_digest_required")
        if not isinstance(self.suite_sha256, str) or not self.suite_sha256.strip():
            raise EvolutionError("evaluation_suite_sha256_required")
        if self.parent_digest is not None and not isinstance(self.parent_digest, str):
            raise EvolutionError("evaluation_parent_digest_must_be_text")
        if not isinstance(self.labeled_tasks, int) or isinstance(self.labeled_tasks, bool):
            raise EvolutionError("evaluation_labeled_tasks_must_be_integer")
        if self.labeled_tasks < 0:
            raise EvolutionError("evaluation_labeled_tasks_negative")
        if not isinstance(self.quality_gate, bool):
            raise EvolutionError("evaluation_quality_gate_must_be_boolean")
        if not isinstance(self.economy_gate, bool):
            raise EvolutionError("evaluation_economy_gate_must_be_boolean")
        if not isinstance(self.ci_verified, bool):
            raise EvolutionError("evaluation_ci_verified_must_be_boolean")
        if not isinstance(self.rollback_required, bool):
            raise EvolutionError("evaluation_rollback_required_must_be_boolean")
        if not isinstance(self.metrics_derived, bool):
            raise EvolutionError("evaluation_metrics_derived_must_be_boolean")
        if not isinstance(self.corpus_gate, bool):
            raise EvolutionError("evaluation_corpus_gate_must_be_boolean")
        if not isinstance(self.comparison, Mapping):
            raise EvolutionError("evaluation_comparison_must_be_mapping")
        if not isinstance(self.rollback_target, str):
            raise EvolutionError("evaluation_rollback_target_must_be_text")
        if self.rollback_required and not self.rollback_target.strip():
            raise EvolutionError("evaluation_rollback_target_required")
        evidence_refs = _strict_refs(self.evidence_refs, "evaluation.evidence_refs")
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted({ref.strip() for ref in evidence_refs if ref.strip()})),
        )
        if not isinstance(self.quality_metrics, Mapping):
            raise EvolutionError("evaluation_quality_metrics_must_be_mapping")
        if not isinstance(self.economy_metrics, Mapping):
            raise EvolutionError("evaluation_economy_metrics_must_be_mapping")
        object.__setattr__(
            self,
            "gate_reasons",
            _strict_refs(self.gate_reasons, "evaluation.gate_reasons"),
        )
        object.__setattr__(
            self,
            "evidence_ref_kinds",
            tuple(
                sorted(
                    set(
                        _strict_refs(
                            self.evidence_ref_kinds, "evaluation.evidence_ref_kinds"
                        )
                    )
                )
            ),
        )
        object.__setattr__(
            self,
            "verified_evidence_refs",
            tuple(
                sorted(
                    set(
                        _strict_refs(
                            self.verified_evidence_refs,
                            "evaluation.verified_evidence_refs",
                        )
                    )
                )
            ),
        )
        object.__setattr__(
            self,
            "verified_evidence_kinds",
            tuple(
                sorted(
                    set(
                        _strict_refs(
                            self.verified_evidence_kinds,
                            "evaluation.verified_evidence_kinds",
                        )
                    )
                )
            ),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(sorted(set(_strict_refs(self.unresolved, "evaluation.unresolved")))),
        )
        if not isinstance(self.evidence_verified, bool):
            raise EvolutionError("evaluation_evidence_verified_must_be_boolean")
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise EvolutionError("evaluation_policy_id_invalid")
        if self.producer_identity_sha256 is not None and (
            not isinstance(self.producer_identity_sha256, str)
            or not self.producer_identity_sha256.strip()
        ):
            raise EvolutionError("evaluation_producer_identity_invalid")

    @property
    def candidate_sha256(self) -> str:
        """Backward-compatible alias for the candidate identity digest."""
        return self.candidate_digest

    @property
    def gates_pass(self) -> bool:
        return (
            self.corpus_gate
            and self.metrics_derived
            and self.quality_gate
            and self.economy_gate
            and self.ci_verified
            and bool(self.evidence_refs)
            and self.evidence_verified
            and (not self.rollback_required or bool(self.rollback_target.strip()))
            and self.comparison.get("refused") is None
            and not self.gate_reasons
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_digest": self.candidate_digest,
            "parent_digest": self.parent_digest,
            "suite_sha256": self.suite_sha256,
            "labeled_tasks": self.labeled_tasks,
            "quality_gate": self.quality_gate,
            "economy_gate": self.economy_gate,
            "ci_verified": self.ci_verified,
            "evidence_refs": list(self.evidence_refs),
            "rollback_target": self.rollback_target,
            "rollback_required": self.rollback_required,
            "gates_pass": self.gates_pass,
            "comparison": self.comparison,
            "quality_metrics": dict(self.quality_metrics),
            "economy_metrics": dict(self.economy_metrics),
            "gate_reasons": list(self.gate_reasons),
            "metrics_derived": self.metrics_derived,
            "corpus_gate": self.corpus_gate,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_sha256": self.policy_sha256,
            "bundle_id": self.bundle_id,
            "execution_mode": self.execution_mode,
            "input_manifest_sha256": self.input_manifest_sha256,
            "evidence_ref_kinds": list(self.evidence_ref_kinds),
            "verified_evidence_refs": list(self.verified_evidence_refs),
            "verified_evidence_kinds": list(self.verified_evidence_kinds),
            "unresolved": list(self.unresolved),
            "evidence_verified": self.evidence_verified,
            "producer_identity_sha256": self.producer_identity_sha256,
            "status": self.status.value,
        }


@overload
def transition(candidate: CandidateSpec, target: CandidateStatus) -> CandidateSpec: ...


@overload
def transition(candidate: CandidateStatus, target: CandidateStatus) -> CandidateStatus: ...


def transition(
    candidate: CandidateSpec | CandidateStatus, target: CandidateStatus
) -> CandidateSpec | CandidateStatus:
    """Apply one legal lifecycle edge and return a new immutable candidate."""
    target = CandidateStatus(target)
    if isinstance(candidate, CandidateStatus):
        if target not in ALLOWED_TRANSITIONS[candidate]:
            raise EvolutionError(f"invalid_candidate_transition:{candidate.value}->{target.value}")
        return target
    if target not in ALLOWED_TRANSITIONS[candidate.status]:
        raise EvolutionError(
            f"invalid_candidate_transition:{candidate.status.value}->{target.value}"
        )
    return replace(candidate, status=target)


class CandidateRegistry:
    """Load and validate candidates from an explicit repository root."""

    def __init__(self, repo: Path | str = ".", path: Path | str | None = None) -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.path = (self.repo / (path or REGISTRY_PATH)).resolve()
        if self.repo not in self.path.parents:
            raise EvolutionError("registry_path_escape")
        self._authority_policy = EvolutionAuthorityPolicy()
        self._evaluation_policy = EvaluationGatePolicy()
        self._policy_resolver = PolicyResolver((), policy_version="legacy")
        self._external_commands: dict[str, Any] = {}
        self._receipt_lock: dict[str, Any] = {
            "stale_after_seconds": 300,
            "recovery": "pid_absent_after_threshold",
        }

    @property
    def authority_policy(self) -> EvolutionAuthorityPolicy:
        return self._authority_policy

    @property
    def evaluation_policy(self) -> EvaluationGatePolicy:
        return self._evaluation_policy

    @property
    def policy_resolver(self) -> PolicyResolver:
        return self._policy_resolver

    @property
    def external_commands(self) -> dict[str, Any]:
        return dict(self._external_commands)

    @property
    def receipt_lock(self) -> dict[str, Any]:
        return dict(self._receipt_lock)

    def load(self) -> tuple[CandidateSpec, ...]:
        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise EvolutionError(f"candidate_registry_unreadable:{self.path}") from exc
        if not isinstance(raw, Mapping) or raw.get("schema_version") != SCHEMA_VERSION:
            raise EvolutionError("candidate_registry_invalid:schema_version")
        unknown = sorted(set(raw) - _REGISTRY_FIELDS)
        if unknown:
            raise EvolutionError(f"candidate_registry_unknown_fields:{','.join(unknown)}")
        _text(raw.get("registry_id"), "registry_id")
        _text(raw.get("benchmark_suite"), "benchmark_suite")
        _strict_bool(raw.get("require_domain_holdout", True), "require_domain_holdout")
        self._authority_policy = _parse_authority_policy(raw.get("authority"))
        self._evaluation_policy = _parse_evaluation_policy(raw.get("evaluation_policy"))
        external_commands = raw.get("external_commands", {})
        if isinstance(external_commands, list) and not external_commands:
            external_commands = {}
        if not isinstance(external_commands, Mapping):
            raise EvolutionError("candidate_registry_invalid:external_commands")
        self._external_commands = dict(external_commands)
        receipt_lock = raw.get("receipt_lock", {})
        if not isinstance(receipt_lock, Mapping):
            raise EvolutionError("candidate_registry_invalid:receipt_lock")
        stale_after = receipt_lock.get("stale_after_seconds", 300)
        if (
            isinstance(stale_after, bool)
            or not isinstance(stale_after, (int, float))
            or stale_after <= 0
        ):
            raise EvolutionError("candidate_registry_invalid:receipt_lock.stale_after_seconds")
        recovery = receipt_lock.get("recovery", "pid_absent_after_threshold")
        if recovery != "pid_absent_after_threshold":
            raise EvolutionError("candidate_registry_invalid:receipt_lock.recovery")
        self._receipt_lock = {
            "stale_after_seconds": float(stale_after),
            "recovery": recovery,
        }
        try:
            self._policy_resolver = PolicyResolver.from_mapping(raw)
        except EvaluationPolicyError as exc:
            raise EvolutionError(str(exc)) from exc
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            raise EvolutionError("candidate_registry_invalid:candidates")
        candidate_root = raw.get("candidate_root", ".")
        if not isinstance(candidate_root, str):
            raise EvolutionError("candidate_root_must_be_text")
        loaded = tuple(
            self._candidate(item, candidate_root)
            for item in candidates
        )
        ids = [(candidate.candidate_id, candidate.version) for candidate in loaded]
        if len(set(ids)) != len(ids):
            raise EvolutionError("candidate_registry_duplicate_identity")
        digests = {candidate.candidate_digest for candidate in loaded}
        if any(
            candidate.parent_digest is not None and candidate.parent_digest not in digests
            for candidate in loaded
        ):
            raise EvolutionError("candidate_parent_digest_unknown")
        return loaded

    def get(self, candidate_id: str, version: str | None = None) -> CandidateSpec:
        matches = [candidate for candidate in self.load() if candidate.candidate_id == candidate_id]
        if version is not None:
            matches = [candidate for candidate in matches if candidate.version == str(version)]
        if len(matches) != 1:
            raise EvolutionError(f"candidate_not_unique:{candidate_id}")
        return matches[0]

    def policy_for(self, candidate: CandidateSpec) -> EvaluationPolicy:
        self.load()
        try:
            return self._policy_resolver.resolve(candidate)
        except EvaluationPolicyError as exc:
            raise EvolutionError(str(exc)) from exc

    def _candidate(
        self,
        value: Any,
        candidate_root: str,
    ) -> CandidateSpec:
        if not isinstance(value, Mapping):
            raise EvolutionError("candidate_registry_invalid:candidate_mapping")
        unknown = sorted(set(value) - _CANDIDATE_FIELDS)
        if unknown:
            raise EvolutionError(f"candidate_unknown_fields:{','.join(unknown)}")
        content = value.get("content")
        content_path = value.get("content_path")
        if content is not None and content_path is not None:
            raise EvolutionError("candidate_content_sources_conflict")
        if content is None and content_path is None:
            raise EvolutionError("candidate_content_required")
        if content_path is not None:
            if not isinstance(content_path, str):
                raise EvolutionError("candidate_content_path_must_be_text")
            content = self._read_content(content_path, candidate_root)
        if not isinstance(content, str):
            raise EvolutionError("candidate_content_must_be_text")
        status = _status(value.get("status", CandidateStatus.CANDIDATE.value))
        candidate_type = _text(value.get("candidate_type", "root"), "candidate.candidate_type")
        family = _text(value.get("family", value.get("kind")), "candidate.family")
        parent = value.get("parent_digest")
        if parent is not None and not isinstance(parent, str):
            raise EvolutionError("candidate_parent_digest_must_be_text")
        if (
            self.authority_policy.require_parent_digest_for_mutation
            and candidate_type == "mutation"
            and parent is None
        ):
            raise EvolutionError("candidate_parent_digest_required_for_mutation")
        if candidate_type == "root" and parent is not None:
            raise EvolutionError("root_candidate_cannot_have_parent")
        contract_sha256 = value.get("contract_sha256")
        if self.authority_policy.require_contract_sha256 and contract_sha256 is None:
            raise EvolutionError("candidate_contract_digest_required")
        candidate = CandidateSpec(
            candidate_id=_text(value.get("id"), "candidate.id"),
            version=_text(value.get("version"), "candidate.version"),
            kind=_text(value.get("kind"), "candidate.kind"),
            content=content,
            contract_id=_text(value.get("contract_id"), "candidate.contract_id"),
            contract_version=_text(value.get("contract_version"), "candidate.contract_version"),
            calibration_version=_text(
                value.get("calibration_version"), "candidate.calibration_version"
            ),
            parent_digest=parent,
            status=status,
            contract_sha256=(
                _text(contract_sha256, "candidate.contract_sha256")
                if contract_sha256 is not None
                else None
            ),
            candidate_type=candidate_type,
            family=family,
        )
        if self.authority_policy.require_contract_sha256:
            self._validate_contract_sha256(candidate)
        declared_digest = value.get("candidate_digest")
        if declared_digest is None and value.get("content_sha256") is not None:
            declared_digest = value.get("content_sha256")
        if self.authority_policy.require_content_digest and declared_digest is None:
            raise EvolutionError("candidate_digest_required")
        if declared_digest is not None and not isinstance(declared_digest, str):
            raise EvolutionError("candidate_digest_must_be_text")
        if declared_digest is not None and declared_digest != candidate.candidate_digest:
            raise EvolutionError("candidate_digest_mismatch")
        if (
            value.get("content_sha256") is not None
            and not isinstance(value["content_sha256"], str)
        ):
            raise EvolutionError("candidate_content_sha256_must_be_text")
        if (
            value.get("content_sha256") is not None
            and value["content_sha256"] != candidate.content_sha256
        ):
            raise EvolutionError("candidate_content_sha256_mismatch")
        return candidate

    def _validate_contract_sha256(self, candidate: CandidateSpec) -> None:
        try:
            from sparkforge.economy.decision_contracts import ContractRegistry

            contract = ContractRegistry(self.repo).load(
                candidate.contract_id, candidate.contract_version
            )
        except (OSError, ValueError, KeyError) as exc:
            raise EvolutionError(
                f"candidate_contract_unreadable:{candidate.contract_id}:{candidate.contract_version}"
            ) from exc
        if candidate.contract_sha256 != contract.sha256:
            raise EvolutionError("candidate_contract_sha256_mismatch")

    def _read_content(self, value: str, candidate_root: Any) -> str:
        if not value or Path(value).is_absolute():
            raise EvolutionError("candidate_content_path_invalid")
        root_value = candidate_root or "."
        base = (self.repo / str(root_value)).resolve()
        target_value = Path(value)
        base_relative = base.relative_to(self.repo)
        has_root_prefix = (
            base_relative.parts
            and target_value.parts[: len(base_relative.parts)] == base_relative.parts
        )
        if has_root_prefix:
            target = (self.repo / target_value).resolve()
        else:
            target = (base / target_value).resolve()
        if base != target and base not in target.parents:
            raise EvolutionError("candidate_content_path_escape")
        try:
            return target.read_text(encoding="utf-8")
        except OSError as exc:
            raise EvolutionError(f"candidate_content_unreadable:{target}") from exc


def load_candidate_registry(repo: Path | str = ".") -> tuple[CandidateSpec, ...]:
    return CandidateRegistry(repo).load()


EvolutionRegistry = CandidateRegistry


class EvolutionService:
    """Coordinate candidate replay and append-only local lifecycle receipts."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.registry = CandidateRegistry(self.repo)
        self.root = self.repo / ".sparkforge" / "evolution"
        self.evidence_resolver = EvidenceResolver(self.repo)
        self._last_receipt_lock_state = "uninitialized"
        self.lifecycle = LifecycleProjector(
            self.root,
            receipt_reader=self._read_verified_receipt,
            transitions=ALLOWED_TRANSITIONS,
            status_parser=_status,
        )

    def effective_candidate(
        self, candidate: CandidateSpec | str, version: str | None = None
    ) -> EffectiveCandidate:
        value = self.registry.get(candidate, version) if isinstance(candidate, str) else candidate
        try:
            return self.lifecycle.project(value.candidate_id, value.status)
        except LifecycleProjectionError as exc:
            raise EvolutionError(str(exc)) from exc

    def validate(self, candidate_id: str | None = None) -> dict[str, Any]:
        candidates = self.registry.load()
        if candidate_id is not None:
            candidates = tuple(
                candidate for candidate in candidates if candidate.candidate_id == candidate_id
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "registry": self.registry.path.as_posix(),
            "candidates": [candidate.to_dict() for candidate in candidates],
        }

    def evaluate(
        self,
        candidate: CandidateSpec,
        *,
        bundle: EvaluationEvidenceBundle | None = None,
        suite: Mapping[str, Any] | None = None,
        suite_path: Path | str | None = None,
        old_runner: Runner | None = None,
        new_runner: Runner | None = None,
        ci_verified: bool = False,
        evidence_refs: tuple[str, ...] = (),
        rollback_target: str | None = None,
    ) -> CandidateEvaluation:
        if not isinstance(ci_verified, bool):
            raise EvolutionError("ci_verified_must_be_boolean")
        if isinstance(bundle, Mapping):
            try:
                bundle = EvaluationEvidenceBundle.from_mapping(bundle)
            except (EvidenceBundleError, TypeError) as exc:
                raise EvolutionError(str(exc)) from exc
        if bundle is not None and not isinstance(bundle, EvaluationEvidenceBundle):
            raise EvolutionError("evidence_bundle_invalid:type")
        if (old_runner is None) != (new_runner is None):
            raise EvolutionError("baseline_and_candidate_runners_required_together")
        policy = self.registry.policy_for(candidate)
        baseline: CandidateSpec | None = None
        execution_mode = "surrogate"
        bundle_id = ""
        input_manifest_sha256 = ""
        bundle_evidence_kinds: tuple[str, ...] = ()
        verified_evidence_refs: tuple[str, ...] = ()
        verified_evidence_kinds: tuple[str, ...] = ()
        unresolved: tuple[str, ...] = ()
        evidence_verified = True
        producer_identity_sha256: str | None = None
        if bundle is not None:
            self._validate_bundle_for_candidate(bundle, candidate, policy)
            try:
                resolved = self.evidence_resolver.resolve(
                    bundle,
                    policy,
                    authorized_commands=self.registry.external_commands,
                )
            except EvidenceResolutionError as exc:
                raise EvolutionError(str(exc)) from exc
            execution_mode = bundle.execution_mode
            bundle_id = bundle.bundle_id
            input_manifest_sha256 = str(bundle.suite["input_manifest_sha256"])
            bundle_evidence_kinds = bundle.evidence_kinds
            verified_evidence_refs = resolved.verified_refs
            verified_evidence_kinds = resolved.verified_ref_kinds
            unresolved = resolved.unresolved
            evidence_verified = not resolved.blocking_unresolved
            producer_identity_sha256 = resolved.producer_identity_sha256
            comparison = resolved.derived_metrics["comparison"]
            labeled_tasks = _strict_int(
                bundle.suite.get("labeled_tasks", policy.minimum_labeled_tasks),
                "bundle.suite.labeled_tasks",
            )
            (
                quality_gate,
                economy_gate,
                quality_metrics,
                economy_metrics,
                gate_reasons,
            ) = _derive_gates(comparison, policy)
            gate_reasons = tuple(
                sorted({*gate_reasons, *resolved.blocking_unresolved})
            )
            evidence_refs = tuple(ref.ref for ref in bundle.evidence_refs)
            rollback_target = rollback_target or bundle.rollback_target
            ci_verified = ci_verified or "ci" in verified_evidence_kinds
        else:
            if suite is None:
                suite = load_replay_suite(
                    self.repo / (suite_path or DEFAULT_SUITE_PATH),
                    minimum_labeled_tasks=policy.minimum_labeled_tasks,
                )
            baseline = self._baseline_for(candidate)
            if old_runner is None or new_runner is None:
                old_runner = _candidate_runner(baseline)
                new_runner = _candidate_runner(candidate)
            baseline_identity = {
                "candidate_id": baseline.candidate_id,
                "version": baseline.version,
                "candidate_digest": baseline.candidate_digest,
            }
            candidate_identity = {
                "candidate_id": candidate.candidate_id,
                "version": candidate.version,
                "candidate_digest": candidate.candidate_digest,
                "parent_digest": candidate.parent_digest,
            }
            paired_report = run_replay_benchmark(
                suite,
                old_runner=old_runner,
                new_runner=new_runner,
                baseline_identity=baseline_identity,
                candidate_identity=candidate_identity,
            )
            baseline_report, candidate_report = split_replay_benchmark(paired_report)
            comparison = compare_replay_benchmark(baseline_report, candidate_report)
            quality_gate, economy_gate, quality_metrics, economy_metrics, gate_reasons = (
                _derive_gates(comparison, policy)
            )
            labeled_tasks = _strict_int(suite.get("labeled_tasks", 0), "suite.labeled_tasks")
            input_manifest_sha256 = digest(
                [dict(case.get("input_manifest", {})) for case in suite.get("cases", ())]
            )
            if labeled_tasks < policy.minimum_labeled_tasks:
                gate_reasons = tuple(
                    sorted({*gate_reasons, "labeled_tasks_below_policy_minimum"})
                )
        evaluation = CandidateEvaluation(
            candidate_digest=candidate.candidate_digest,
            parent_digest=candidate.parent_digest,
            suite_sha256=(bundle.suite_sha256 if bundle is not None else str(suite["sha256"])),
            labeled_tasks=labeled_tasks,
            quality_gate=quality_gate,
            economy_gate=economy_gate,
            ci_verified=ci_verified,
            evidence_refs=evidence_refs,
            rollback_target=(
                rollback_target
                or (candidate.parent_digest or "restore-previous-accepted")
                if self.registry.authority_policy.require_rollback_target
                else (rollback_target or "")
            ),
            comparison=comparison,
            quality_metrics=quality_metrics,
            economy_metrics=economy_metrics,
            gate_reasons=gate_reasons,
            rollback_required=self.registry.authority_policy.require_rollback_target,
            metrics_derived=True,
            corpus_gate=labeled_tasks >= policy.minimum_labeled_tasks,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_sha256=policy.policy_sha256,
            bundle_id=bundle_id,
            execution_mode=execution_mode,
            input_manifest_sha256=input_manifest_sha256,
            evidence_ref_kinds=bundle_evidence_kinds,
            verified_evidence_refs=verified_evidence_refs,
            verified_evidence_kinds=verified_evidence_kinds,
            unresolved=unresolved,
            evidence_verified=evidence_verified,
            producer_identity_sha256=producer_identity_sha256,
        )
        self._write(
            "evaluation",
            {
                "candidate": candidate.to_dict(),
                "evaluation": evaluation.to_dict(),
                "candidate_digest": candidate.candidate_digest,
                "policy_version": policy.policy_version,
                "policy_sha256": policy.policy_sha256,
                "bundle_id": bundle_id,
                "rollback_target": evaluation.rollback_target,
            },
        )
        return evaluation

    def promote(
        self,
        candidate: CandidateSpec,
        evaluation: CandidateEvaluation,
        *,
        caller_authorized: bool,
        contract_sha256: str | None = None,
    ) -> CandidateSpec:
        if self.registry.authority_policy.require_evaluation_receipt and not self._has_evaluation(
            candidate, evaluation
        ):
            raise EvolutionError("candidate_evaluation_receipt_missing_or_mismatched")
        effective = self.effective_candidate(candidate)
        if (
            effective.effective_status is CandidateStatus.CANDIDATE
            and not self.registry.authority_policy.require_evaluation_receipt
        ):
            effective_status = CandidateStatus.EVALUATED
        else:
            effective_status = effective.effective_status
        if effective_status is not CandidateStatus.EVALUATED:
            raise EvolutionError("candidate_promotion_requires_evaluated")
        if evaluation.candidate_digest != candidate.candidate_digest:
            raise EvolutionError("candidate_evaluation_digest_mismatch")
        if not evaluation.gates_pass:
            raise EvolutionError("candidate_promotion_gates_incomplete")
        policy = self.registry.policy_for(candidate)
        if evaluation.policy_sha256 and evaluation.policy_sha256 != policy.policy_sha256:
            raise EvolutionError("candidate_promotion_policy_digest_mismatch")
        if evaluation.bundle_id:
            if not evaluation.evidence_verified:
                raise EvolutionError("candidate_promotion_evidence_unverified")
            required_kinds = set(policy.required_verified_evidence_kinds)
            missing = sorted(required_kinds - set(evaluation.verified_evidence_kinds))
            if missing:
                raise EvolutionError(
                    f"candidate_promotion_evidence_missing:{','.join(missing)}"
                )
        if self.registry.authority_policy.require_rollback_target:
            self._validate_rollback_target(candidate, evaluation.rollback_target)
        policy = AuthorityPolicy.from_repo(self.repo)
        contract = _ContractIdentity(
            candidate.contract_id,
            candidate.contract_version,
            contract_sha256 or candidate.contract_sha256,
            candidate.calibration_version,
        )
        authority = policy.authorize_promotion(
            mode="active",
            contract=contract,
            evidence=PromotionEvidence(
                promotion_id=f"candidate:{candidate.candidate_id}:{candidate.version}",
                contract_id=candidate.contract_id,
                contract_version=candidate.contract_version,
                contract_sha256=contract.sha256,
                labeled_tasks=evaluation.labeled_tasks,
                quality_gate=evaluation.quality_gate,
                economy_gate=evaluation.economy_gate,
                ci_verified=evaluation.ci_verified,
                rollback=evaluation.rollback_target,
                evidence_refs=(
                    evaluation.verified_evidence_refs
                    or evaluation.evidence_refs
                ),
                calibration_version=candidate.calibration_version,
            ),
            caller_authorized=caller_authorized,
        )
        if not authority.allowed:
            raise EvolutionError(f"candidate_promotion_refused:{authority.reason}")
        accepted = transition(
            replace(candidate, status=CandidateStatus.EVALUATED), CandidateStatus.ACCEPTED
        )
        self._write(
            "promotion",
            {
                "candidate": accepted.to_dict(),
                "evaluation": evaluation.to_dict(),
                "authority": authority.to_dict(),
                "rollback_target": evaluation.rollback_target,
                "candidate_digest": candidate.candidate_digest,
                "policy_version": evaluation.policy_version,
                "policy_sha256": evaluation.policy_sha256,
                "bundle_id": evaluation.bundle_id,
                "provenance": {
                    "candidate_digest": candidate.candidate_digest,
                    "parent_digest": candidate.parent_digest,
                    "contract_id": candidate.contract_id,
                    "contract_version": candidate.contract_version,
                    "contract_sha256": candidate.contract_sha256,
                    "calibration_version": candidate.calibration_version,
                    "policy_id": evaluation.policy_id,
                    "policy_version": evaluation.policy_version,
                    "policy_sha256": evaluation.policy_sha256,
                    "evaluation_receipt_id": self._evaluation_receipt_id(
                        candidate, evaluation
                    ),
                    "producer_identity_sha256": evaluation.producer_identity_sha256,
                    "verified_evidence_refs": list(evaluation.verified_evidence_refs),
                    "verified_evidence_kinds": list(evaluation.verified_evidence_kinds),
                    "quality_metrics": dict(evaluation.quality_metrics),
                    "economy_metrics": dict(evaluation.economy_metrics),
                    "execution_mode": evaluation.execution_mode,
                    "rollback_target": evaluation.rollback_target,
                },
            },
        )
        return accepted

    def latest_evaluation(self, candidate: CandidateSpec) -> CandidateEvaluation:
        target = candidate.candidate_digest
        if not self.root.is_dir():
            raise EvolutionError("candidate_evaluation_missing")
        matches: list[tuple[int, CandidateEvaluation]] = []
        legacy_matches: list[CandidateEvaluation] = []
        versioned: list[Mapping[str, Any]] = []
        with os.scandir(self.root) as entries:
            paths = sorted(
                self.root / entry.name
                for entry in entries
                if entry.is_file() and entry.name.endswith(".json")
            )
        for path in paths:
            document = self._read_verified_receipt(path)
            if document.get("receipt_schema_version") == 2:
                versioned.append(document)
            if document.get("action") != "evaluation":
                continue
            value = document.get("evaluation")
            if isinstance(value, Mapping) and value.get("candidate_digest") == target:
                evaluation = _evaluation_from_dict(value)
                if document.get("receipt_schema_version") == 2:
                    sequence = document.get("event_sequence")
                    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
                        raise EvolutionError("evolution_receipt_sequence_invalid:missing")
                    matches.append((sequence, evaluation))
                else:
                    legacy_matches.append(evaluation)
        self._verify_receipt_chain(versioned)
        if matches:
            sequences = [sequence for sequence, _ in matches]
            if len(sequences) != len(set(sequences)):
                raise EvolutionError("evolution_receipt_sequence_invalid:duplicate")
            return max(matches, key=lambda item: item[0])[1]
        if legacy_matches:
            raise EvolutionError("candidate_evaluation_legacy_not_authoritative")
        if not matches and not legacy_matches:
            raise EvolutionError("candidate_evaluation_missing")
        raise EvolutionError("candidate_evaluation_missing")

    def rollback(self, candidate: CandidateSpec, previous: CandidateSpec) -> CandidateSpec:
        effective = self.effective_candidate(candidate)
        previous_effective = self.effective_candidate(previous)
        if effective.effective_status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("candidate_rollback_requires_accepted")
        if previous_effective.effective_status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("rollback_target_must_be_accepted")
        if candidate.parent_digest != previous.candidate_digest:
            raise EvolutionError("rollback_target_incompatible")
        rolled_back = transition(
            replace(candidate, status=CandidateStatus.ACCEPTED), CandidateStatus.ROLLED_BACK
        )
        self._write(
            "rollback",
            {
                "candidate": rolled_back.to_dict(),
                "restored": previous.to_dict(),
                "rollback_target": previous.candidate_digest,
            },
        )
        return rolled_back

    def _validate_rollback_target(self, candidate: CandidateSpec, target: str) -> None:
        if not target:
            raise EvolutionError("rollback_target_unresolved")
        if candidate.parent_digest != target:
            raise EvolutionError("rollback_target_incompatible")
        try:
            parent = next(
                item
                for item in self.registry.load()
                if item.candidate_digest == target
            )
        except StopIteration as exc:
            raise EvolutionError("rollback_target_unresolved") from exc
        effective = self.effective_candidate(parent)
        if effective.effective_status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("rollback_target_must_be_accepted")
        if (
            parent.family != candidate.family
            or parent.kind != candidate.kind
            or parent.contract_id != candidate.contract_id
            or parent.contract_version != candidate.contract_version
        ):
            raise EvolutionError("rollback_target_incompatible")

    def _evaluation_receipt_id(
        self, candidate: CandidateSpec, evaluation: CandidateEvaluation
    ) -> str | None:
        target = candidate.candidate_digest
        matches: list[Mapping[str, Any]] = []
        for path in self._receipt_paths():
            document = self._read_verified_receipt(path)
            if document.get("receipt_schema_version") != 2:
                continue
            if document.get("action") != "evaluation":
                continue
            value = document.get("evaluation")
            if not isinstance(value, Mapping) or value.get("candidate_digest") != target:
                continue
            if _evaluation_from_dict(value).to_dict() == evaluation.to_dict():
                matches.append(document)
        if not matches:
            return None
        return str(max(matches, key=lambda item: int(item["event_sequence"]))["receipt_id"])

    def _write(self, action: str, value: Mapping[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".receipt.lock"
        descriptor = self._acquire_receipt_lock(lock)
        try:
            previous_id, sequence = self._next_receipt_link()
            payload = dict(value)
            candidate = payload.get("candidate")
            if isinstance(candidate, Mapping) and candidate.get("candidate_id"):
                payload.setdefault("candidate_id", candidate["candidate_id"])
            body = {
                "schema_version": SCHEMA_VERSION,
                "receipt_schema_version": 2,
                "event_sequence": sequence,
                "previous_receipt_id": previous_id,
                "action": action,
                **payload,
            }
            receipt_id = digest(body)
            path = self.root / f"{receipt_id}.json"
            document = {**body, "receipt_id": receipt_id}
            if path.exists():
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise EvolutionError(f"evolution_receipt_unreadable:{path}") from exc
                if existing != document:
                    raise EvolutionError(f"evolution_receipt_collision:{receipt_id}")
                return path
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
            return path
        finally:
            try:
                os.close(descriptor)
            finally:
                try:
                    lock.unlink()
                except OSError:
                    pass

    def _acquire_receipt_lock(self, lock: Path) -> int:
        recovered = False
        for attempt in range(2):
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as exc:
                state = self._inspect_receipt_lock(lock)
                if state == "stale_detected" and attempt == 0:
                    recovered = True
                    continue
                self._last_receipt_lock_state = state
                raise EvolutionError(f"evolution_receipt_lock_{state}") from exc
            except OSError as exc:
                self._last_receipt_lock_state = "unverifiable"
                raise EvolutionError("evolution_receipt_lock_unverifiable") from exc
            metadata = {
                "pid": os.getpid(),
                "created_at": time.time(),
                "hostname": socket.gethostname(),
                "process_start_fingerprint": _process_start_fingerprint(os.getpid()),
            }
            try:
                os.write(
                    descriptor,
                    json.dumps(metadata, sort_keys=True).encode("utf-8"),
                )
            except OSError:
                try:
                    lock.unlink()
                except OSError:
                    pass
                raise
            self._last_receipt_lock_state = "lock_recovered" if recovered else "acquired"
            return descriptor
        self._last_receipt_lock_state = "busy"
        raise EvolutionError("evolution_receipt_lock_busy")

    def _inspect_receipt_lock(self, lock: Path) -> str:
        try:
            metadata = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "unverifiable"
        if not isinstance(metadata, Mapping):
            return "unverifiable"
        created_at = metadata.get("created_at")
        pid = metadata.get("pid")
        hostname = metadata.get("hostname")
        if (
            isinstance(created_at, bool)
            or not isinstance(created_at, (int, float))
            or not isinstance(pid, int)
            or isinstance(pid, bool)
            or not isinstance(hostname, str)
            or hostname != socket.gethostname()
        ):
            return "unverifiable"
        if time.time() - float(created_at) < float(
            self.registry.receipt_lock.get("stale_after_seconds", 300)
        ):
            return "busy"
        process_state = _process_state(pid, metadata.get("process_start_fingerprint"))
        if process_state is not False:
            return "unverifiable" if process_state is None else "busy"
        try:
            lock.unlink()
        except OSError:
            return "unverifiable"
        return "stale_detected"

    def _next_receipt_link(self) -> tuple[str | None, int]:
        documents: list[Mapping[str, Any]] = []
        for path in self._receipt_paths():
            document = self._read_verified_receipt(path)
            if document.get("receipt_schema_version") == 2:
                documents.append(document)
        if not documents:
            return None, 1
        latest = max(documents, key=lambda item: int(item.get("event_sequence", 0)))
        return str(latest["receipt_id"]), int(latest["event_sequence"]) + 1

    def _receipt_paths(self) -> tuple[Path, ...]:
        with os.scandir(self.root) as entries:
            return tuple(
                sorted(
                    self.root / entry.name
                    for entry in entries
                    if entry.is_file() and entry.name.endswith(".json")
                )
            )

    def _verify_receipt_chain(self, documents: list[Mapping[str, Any]]) -> None:
        if not documents:
            return
        ordered = sorted(documents, key=lambda item: int(item.get("event_sequence", 0)))
        previous: str | None = None
        for expected_sequence, document in enumerate(ordered, start=1):
            sequence = document.get("event_sequence")
            if sequence != expected_sequence:
                raise EvolutionError("evolution_receipt_sequence_invalid:gap")
            if document.get("previous_receipt_id") != previous:
                raise EvolutionError("evolution_receipt_sequence_invalid:predecessor")
            previous = str(document.get("receipt_id"))

    def _has_evaluation(
        self, candidate: CandidateSpec, evaluation: CandidateEvaluation
    ) -> bool:
        if not evaluation.candidate_digest or not evaluation.suite_sha256:
            return False
        if evaluation.status is not CandidateStatus.EVALUATED:
            return False
        if evaluation.candidate_digest != candidate.candidate_digest:
            return False
        try:
            persisted = self.latest_evaluation(candidate)
        except EvolutionError:
            return False
        return persisted.to_dict() == evaluation.to_dict()

    def _baseline_for(self, candidate: CandidateSpec) -> CandidateSpec:
        if candidate.parent_digest is None:
            raise EvolutionError("candidate_baseline_required")
        candidates = self.registry.load()
        matches = [item for item in candidates if item.candidate_digest == candidate.parent_digest]
        if len(matches) != 1:
            raise EvolutionError("candidate_baseline_digest_missing")
        baseline = matches[0]
        if self.effective_candidate(baseline).effective_status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("candidate_baseline_must_be_accepted")
        return baseline

    def _validate_bundle_for_candidate(
        self,
        bundle: EvaluationEvidenceBundle,
        candidate: CandidateSpec,
        policy: Any,
    ) -> None:
        if bundle.candidate_digest != candidate.candidate_digest:
            raise EvolutionError("evidence_bundle_candidate_digest_mismatch")
        if bundle.parent_digest != candidate.parent_digest:
            raise EvolutionError("evidence_bundle_parent_digest_mismatch")
        if bundle.policy_sha256 != policy.policy_sha256:
            raise EvolutionError("evidence_bundle_policy_digest_mismatch")
        if bundle.policy.get("policy_version") != policy.policy_version:
            raise EvolutionError("evidence_bundle_policy_version_mismatch")
        if bundle.candidate.get("contract_id") != candidate.contract_id:
            raise EvolutionError("evidence_bundle_contract_id_mismatch")
        if bundle.candidate.get("contract_version") != candidate.contract_version:
            raise EvolutionError("evidence_bundle_contract_version_mismatch")
        if bundle.candidate.get("contract_sha256") != candidate.contract_sha256:
            raise EvolutionError("evidence_bundle_contract_digest_mismatch")

    def _read_verified_receipt(self, path: Path) -> Mapping[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", path.stem):
            raise EvolutionError(f"evolution_receipt_id_invalid:{path}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvolutionError(f"evolution_receipt_unreadable:{path}") from exc
        if not isinstance(document, Mapping):
            raise EvolutionError(f"evolution_receipt_invalid:{path}")
        receipt_id = document.get("receipt_id")
        if receipt_id != path.stem:
            raise EvolutionError(f"evolution_receipt_id_mismatch:{path}")
        body = {key: value for key, value in document.items() if key != "receipt_id"}
        if digest(body) != receipt_id:
            raise EvolutionError(f"evolution_receipt_digest_mismatch:{path}")
        return document


@dataclass(frozen=True, slots=True)
class _ContractIdentity:
    contract_id: str
    contract_version: str
    sha256: str | None
    calibration_version: str


def _status(value: Any) -> CandidateStatus:
    if not isinstance(value, str):
        raise EvolutionError("candidate_status_must_be_text")
    try:
        return CandidateStatus(value)
    except ValueError as exc:
        raise EvolutionError(f"candidate_status_invalid:{value}") from exc


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionError(f"{field}_required")
    return value.strip()


def _strict_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise EvolutionError(f"{field}_must_be_text")
    if not allow_empty and not value.strip():
        raise EvolutionError(f"{field}_required")
    return value.strip()


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise EvolutionError(f"{field}_must_be_boolean")
    return value


def _strict_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise EvolutionError(f"{field}_must_be_integer")
    return value


def _strict_refs(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise EvolutionError(f"{field}_must_be_sequence_of_strings")
    if any(not isinstance(item, str) for item in value):
        raise EvolutionError(f"{field}_must_be_sequence_of_strings")
    return tuple(value)


def _strict_number(value: Any, field: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvolutionError(f"{field}_must_be_number")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise EvolutionError(f"{field}_must_be_between_zero_and_one")
    return number


def _parse_authority_policy(value: Any) -> EvolutionAuthorityPolicy:
    if not isinstance(value, Mapping):
        raise EvolutionError("candidate_registry_invalid:authority")
    unknown = sorted(set(value) - _AUTHORITY_FIELDS)
    if unknown:
        raise EvolutionError(f"candidate_authority_unknown_fields:{','.join(unknown)}")
    return EvolutionAuthorityPolicy(
        require_content_digest=_strict_bool(
            value.get("require_content_digest", True), "authority.require_content_digest"
        ),
        require_parent_digest_for_mutation=_strict_bool(
            value.get("require_parent_digest_for_mutation", True),
            "authority.require_parent_digest_for_mutation",
        ),
        require_evaluation_receipt=_strict_bool(
            value.get("require_evaluation_receipt", True),
            "authority.require_evaluation_receipt",
        ),
        require_rollback_target=_strict_bool(
            value.get("require_rollback_target", True),
            "authority.require_rollback_target",
        ),
        require_contract_sha256=_strict_bool(
            value.get("require_contract_sha256", True),
            "authority.require_contract_sha256",
        ),
    )


def _parse_evaluation_policy(value: Any) -> EvaluationGatePolicy:
    if value is None:
        return EvaluationGatePolicy()
    if not isinstance(value, Mapping):
        raise EvolutionError("candidate_registry_invalid:evaluation_policy")
    quality = value.get("quality", {})
    economy = value.get("economy", {})
    if not isinstance(quality, Mapping) or not isinstance(economy, Mapping):
        raise EvolutionError("evaluation_policy_quality_and_economy_must_be_mappings")
    known_quality = {
        "min_status_accuracy",
        "min_evidence_recall",
        "max_false_positive_rate",
        "max_quality_regression",
        "min_route_accuracy",
        "max_route_regression",
        "require_route_metric",
    }
    known_economy = {
        "max_payload_regression",
        "max_token_regression",
        "max_cost_regression",
        "require_tokens",
        "require_cost",
    }
    unknown_quality = sorted(set(quality) - known_quality)
    unknown_economy = sorted(set(economy) - known_economy)
    if unknown_quality or unknown_economy:
        fields = [f"quality.{item}" for item in unknown_quality]
        fields.extend(f"economy.{item}" for item in unknown_economy)
        raise EvolutionError(f"evaluation_policy_unknown_fields:{','.join(fields)}")
    return EvaluationGatePolicy(
        min_status_accuracy=_strict_number(
            quality.get("min_status_accuracy", 1.0), "quality.min_status_accuracy"
        ),
        min_evidence_recall=_strict_number(
            quality.get("min_evidence_recall", 1.0), "quality.min_evidence_recall"
        ),
        max_false_positive_rate=_strict_number(
            quality.get("max_false_positive_rate", 0.0), "quality.max_false_positive_rate"
        ),
        max_quality_regression=_strict_number(
            quality.get("max_quality_regression", 0.0), "quality.max_quality_regression"
        ),
        min_route_accuracy=_strict_number(
            quality.get("min_route_accuracy"), "quality.min_route_accuracy", allow_none=True
        ),
        max_route_regression=_strict_number(
            quality.get("max_route_regression", 0.0), "quality.max_route_regression"
        ),
        require_route_metric=_strict_bool(
            quality.get("require_route_metric", False), "quality.require_route_metric"
        ),
        max_payload_regression=_strict_number(
            economy.get("max_payload_regression", 0.0), "economy.max_payload_regression"
        ),
        max_token_regression=_strict_number(
            economy.get("max_token_regression", 0.0), "economy.max_token_regression"
        ),
        max_cost_regression=_strict_number(
            economy.get("max_cost_regression", 0.0), "economy.max_cost_regression"
        ),
        require_tokens=_strict_bool(
            economy.get("require_tokens", False), "economy.require_tokens"
        ),
        require_cost=_strict_bool(economy.get("require_cost", False), "economy.require_cost"),
    )


def _derive_gates(
    comparison: Mapping[str, Any], policy: EvaluationGatePolicy
) -> tuple[bool, bool, dict[str, Any], dict[str, Any], tuple[str, ...]]:
    if comparison.get("refused") is not None:
        return False, False, {}, {}, ("comparison_refused",)
    metrics = comparison.get("metrics")
    if not isinstance(metrics, Mapping):
        return False, False, {}, {}, ("comparison_metrics_missing",)
    baseline = metrics.get("baseline")
    candidate = metrics.get("candidate")
    if not isinstance(baseline, Mapping) or not isinstance(candidate, Mapping):
        return False, False, {}, {}, ("comparison_metrics_invalid",)
    reasons: list[str] = []
    quality = {
        "status_accuracy": candidate.get("status_accuracy"),
        "baseline_status_accuracy": baseline.get("status_accuracy"),
        "evidence_recall": candidate.get("evidence_recall"),
        "baseline_evidence_recall": baseline.get("evidence_recall"),
        "false_positive_rate": candidate.get("false_positive_rate"),
        "route_accuracy": candidate.get("route_accuracy"),
        "baseline_route_accuracy": baseline.get("route_accuracy"),
    }
    _require_minimum(
        quality["status_accuracy"], policy.min_status_accuracy, "status_accuracy", reasons
    )
    _require_minimum(
        quality["evidence_recall"], policy.min_evidence_recall, "evidence_recall", reasons
    )
    _require_maximum(
        quality["false_positive_rate"],
        policy.max_false_positive_rate,
        "false_positive_rate",
        reasons,
    )
    _require_regression(
        quality["baseline_status_accuracy"],
        quality["status_accuracy"],
        policy.max_quality_regression,
        "status_accuracy", reasons
    )
    _require_regression(
        quality["baseline_evidence_recall"],
        quality["evidence_recall"],
        policy.max_quality_regression,
        "evidence_recall", reasons
    )
    if policy.require_route_metric or policy.min_route_accuracy is not None:
        _require_minimum(
            quality["route_accuracy"], policy.min_route_accuracy or 0.0, "route_accuracy", reasons
        )
        _require_regression(
            quality["baseline_route_accuracy"],
            quality["route_accuracy"],
            policy.max_route_regression,
            "route_accuracy", reasons
        )
    economy = {
        "payload_bytes_mean": candidate.get("payload_bytes_mean"),
        "baseline_payload_bytes_mean": baseline.get("payload_bytes_mean"),
        "provider_tokens_mean": candidate.get("provider_tokens_mean"),
        "baseline_provider_tokens_mean": baseline.get("provider_tokens_mean"),
        "cost_mean": candidate.get("cost_mean"),
        "baseline_cost_mean": baseline.get("cost_mean"),
    }
    _require_regression(
        economy["baseline_payload_bytes_mean"], economy["payload_bytes_mean"],
        policy.max_payload_regression, "payload_bytes", reasons
    )
    if policy.require_tokens:
        if economy["provider_tokens_mean"] is None:
            reasons.append("provider_tokens_unresolved")
        else:
            _require_regression(
                economy["baseline_provider_tokens_mean"], economy["provider_tokens_mean"],
                policy.max_token_regression, "provider_tokens", reasons
            )
    if policy.require_cost:
        if economy["cost_mean"] is None:
            reasons.append("cost_unresolved")
        else:
            _require_regression(
                economy["baseline_cost_mean"], economy["cost_mean"],
                policy.max_cost_regression, "cost", reasons
            )
    quality_failed = any(
        reason.startswith(
            ("status_accuracy", "evidence_recall", "false_positive_rate", "route_accuracy")
        )
        for reason in reasons
    )
    economy_failed = any(
        reason.startswith(("payload_bytes", "provider_tokens", "cost")) for reason in reasons
    )
    return not quality_failed, not economy_failed, quality, economy, tuple(sorted(set(reasons)))


def _require_minimum(value: Any, minimum: float, name: str, reasons: list[str]) -> None:
    if not isinstance(value, (int, float)) or float(value) < minimum:
        reasons.append(f"{name}_below_threshold")


def _require_maximum(value: Any, maximum: float, name: str, reasons: list[str]) -> None:
    if not isinstance(value, (int, float)) or float(value) > maximum:
        reasons.append(f"{name}_above_threshold")


def _require_regression(
    baseline: Any, candidate: Any, maximum: float, name: str, reasons: list[str]
) -> None:
    if baseline is None or candidate is None:
        reasons.append(f"{name}_regression_unresolved")
        return
    denominator = max(abs(float(baseline)), 1.0)
    regression = (float(candidate) - float(baseline)) / denominator
    if regression > maximum:
        reasons.append(f"{name}_regression_above_threshold")


def _candidate_runner(candidate: CandidateSpec) -> Runner:
    """Build a deterministic local runner whose behavior depends on content.

    The fixture is intentionally provider-free. Candidate text may contain
    simple directives such as ``unknown_status=accepted`` or
    ``evidence=none``; ordinary prompt text uses safe defaults. This makes a
    content mutation observable without pretending that a provider was called.
    """
    directives = _content_directives(candidate.content)
    content_bytes = len(candidate.content.encode("utf-8"))

    def runner(case: Mapping[str, Any], profile: str) -> Mapping[str, Any]:
        signal = str(case.get("signal", ""))
        if signal == "unknown":
            status = directives.get("unknown_status", "unresolved")
        else:
            status = directives.get("known_status", "accepted")
        evidence = (
            tuple(case.get("expected_evidence", ()))
            if directives.get("evidence", "expected") == "expected"
            else ()
        )
        findings = (
            tuple(case.get("expected_findings", ()))
            if directives.get("findings", "expected") == "expected"
            else ()
        )
        input_manifest = case.get("input_manifest", {})
        input_bytes = input_manifest.get("bytes") if isinstance(input_manifest, Mapping) else None
        payload_bytes = (
            input_bytes + content_bytes if isinstance(input_bytes, (int, float)) else None
        )
        return {
            "status": status,
            "actual_route": directives.get("route") or case.get("expected_route"),
            "observed_evidence": evidence,
            "observed_findings": findings,
            "unresolved": ("candidate_prompt_unknown_status",)
            if status == "unresolved" and signal == "unknown"
            else (),
            "payload_bytes": payload_bytes,
            "tokens_unresolved": True,
            "tokens_unresolved_reason": "provider_transcript_absent",
            "profile": profile,
            "candidate_digest": candidate.candidate_digest,
        }

    return runner


def _content_directives(content: str) -> dict[str, str]:
    directives: dict[str, str] = {}
    for line in content.splitlines():
        if "=" not in line:
            continue
        key, value = (part.strip().lower() for part in line.split("=", 1))
        if key in {"unknown_status", "known_status", "evidence", "findings", "route"}:
            directives[key] = value
    return directives


def _evaluation_from_dict(value: Mapping[str, Any]) -> CandidateEvaluation:
    try:
        candidate_digest = value.get("candidate_digest", value.get("candidate_sha256"))
        candidate_digest = _strict_text(candidate_digest, "evaluation.candidate_digest")
        evidence_refs = _strict_refs(value.get("evidence_refs", ()), "evaluation.evidence_refs")
        comparison = value.get("comparison", {})
        quality_metrics = value.get("quality_metrics", {})
        economy_metrics = value.get("economy_metrics", {})
        if not isinstance(comparison, Mapping):
            raise EvolutionError("evaluation_comparison_must_be_mapping")
        if not isinstance(quality_metrics, Mapping):
            raise EvolutionError("evaluation_quality_metrics_must_be_mapping")
        if not isinstance(economy_metrics, Mapping):
            raise EvolutionError("evaluation_economy_metrics_must_be_mapping")
        return CandidateEvaluation(
            candidate_digest=candidate_digest,
            parent_digest=(
                _strict_text(value["parent_digest"], "evaluation.parent_digest")
                if value.get("parent_digest") is not None
                else None
            ),
            suite_sha256=_strict_text(value["suite_sha256"], "evaluation.suite_sha256"),
            labeled_tasks=_strict_int(value["labeled_tasks"], "evaluation.labeled_tasks"),
            quality_gate=_strict_bool(value["quality_gate"], "evaluation.quality_gate"),
            economy_gate=_strict_bool(value["economy_gate"], "evaluation.economy_gate"),
            ci_verified=_strict_bool(value["ci_verified"], "evaluation.ci_verified"),
            evidence_refs=evidence_refs,
            rollback_target=_strict_text(
                value["rollback_target"], "evaluation.rollback_target", allow_empty=True
            ),
            comparison=dict(comparison),
            status=_status(
                _strict_text(
                    value.get("status", CandidateStatus.EVALUATED.value),
                    "evaluation.status",
                )
            ),
            quality_metrics=dict(quality_metrics),
            economy_metrics=dict(economy_metrics),
            gate_reasons=tuple(
                _strict_refs(value.get("gate_reasons", ()), "evaluation.gate_reasons")
            ),
            rollback_required=_strict_bool(
                value.get("rollback_required", True), "evaluation.rollback_required"
            ),
            metrics_derived=_strict_bool(
                value.get("metrics_derived", False), "evaluation.metrics_derived"
            ),
            corpus_gate=_strict_bool(
                value.get("corpus_gate", False),
                "evaluation.corpus_gate",
            ),
            policy_version=_strict_text(
                value.get("policy_version", "legacy"), "evaluation.policy_version"
            ),
            policy_id=_strict_text(
                value.get("policy_id", "legacy"), "evaluation.policy_id"
            ),
            policy_sha256=_strict_text(
                value.get("policy_sha256", ""), "evaluation.policy_sha256", allow_empty=True
            ),
            bundle_id=_strict_text(
                value.get("bundle_id", ""), "evaluation.bundle_id", allow_empty=True
            ),
            execution_mode=_strict_text(
                value.get("execution_mode", "surrogate"), "evaluation.execution_mode"
            ),
            input_manifest_sha256=_strict_text(
                value.get("input_manifest_sha256", ""),
                "evaluation.input_manifest_sha256",
                allow_empty=True,
            ),
            evidence_ref_kinds=tuple(
                _strict_refs(value.get("evidence_ref_kinds", ()), "evaluation.evidence_ref_kinds")
            ),
            verified_evidence_refs=tuple(
                _strict_refs(
                    value.get("verified_evidence_refs", ()),
                    "evaluation.verified_evidence_refs",
                )
            ),
            verified_evidence_kinds=tuple(
                _strict_refs(
                    value.get("verified_evidence_kinds", ()),
                    "evaluation.verified_evidence_kinds",
                )
            ),
            unresolved=tuple(
                _strict_refs(value.get("unresolved", ()), "evaluation.unresolved")
            ),
            evidence_verified=_strict_bool(
                value.get("evidence_verified", False), "evaluation.evidence_verified"
            ),
            producer_identity_sha256=(
                _strict_text(
                    value["producer_identity_sha256"],
                    "evaluation.producer_identity_sha256",
                )
                if value.get("producer_identity_sha256") is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError, EvolutionError) as exc:
        raise EvolutionError("candidate_evaluation_invalid") from exc


def _process_start_fingerprint(pid: int) -> str | None:
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        return hashlib.sha256(stat_path.read_bytes()).hexdigest()
    except OSError:
        return None


def _process_state(pid: int, fingerprint: Any) -> bool | None:
    if pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError as exc:
        if getattr(exc, "winerror", None) == 87:
            return False
        return None
    current = _process_start_fingerprint(pid)
    if fingerprint and current is not None and str(fingerprint) != current:
        return False
    return True


__all__ = [
    "ALLOWED_TRANSITIONS",
    "CandidateEvaluation",
    "CandidateRegistry",
    "CandidateSpec",
    "CandidateStatus",
    "EvaluationGatePolicy",
    "EvolutionAuthorityPolicy",
    "EvolutionError",
    "EvolutionRegistry",
    "EvolutionService",
    "load_candidate_registry",
    "transition",
]
