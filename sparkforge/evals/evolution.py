"""Offline prompt and agent candidate lifecycle.

Candidate content is immutable and content-addressed. This module coordinates
local registry validation, replay evidence, lifecycle transitions and receipts;
it never calls a model or an external service.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
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
)

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
        "contract_id",
        "contract_version",
        "contract_sha256",
        "calibration_version",
        "parent_digest",
        "status",
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
        "candidates",
    }
)


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
        if self.parent_digest is not None and not self.parent_digest.strip():
            raise EvolutionError("candidate_parent_digest_empty")

    @property
    def content_sha256(self) -> str:
        return digest(self.identity_dict())

    def identity_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "version": self.version,
            "kind": self.kind,
            "content": self.content,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "calibration_version": self.calibration_version,
            "parent_digest": self.parent_digest,
        }

    def to_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        value = {
            "candidate_id": self.candidate_id,
            "version": self.version,
            "kind": self.kind,
            "content_sha256": self.content_sha256,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "calibration_version": self.calibration_version,
            "parent_digest": self.parent_digest,
            "status": self.status.value,
        }
        if include_content:
            value["content"] = self.content
        return value


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate_sha256: str
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

    def __post_init__(self) -> None:
        if self.labeled_tasks < 0:
            raise EvolutionError("evaluation_labeled_tasks_negative")
        if not self.rollback_target.strip():
            raise EvolutionError("evaluation_rollback_target_required")
        if any(not isinstance(ref, str) for ref in self.evidence_refs):
            raise EvolutionError("evaluation_evidence_refs_must_be_text")
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted({ref.strip() for ref in self.evidence_refs if ref.strip()})),
        )

    @property
    def gates_pass(self) -> bool:
        return (
            self.labeled_tasks >= 50
            and self.quality_gate
            and self.economy_gate
            and self.ci_verified
            and bool(self.evidence_refs)
            and bool(self.rollback_target.strip())
            and self.comparison.get("refused") is None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_sha256": self.candidate_sha256,
            "parent_digest": self.parent_digest,
            "suite_sha256": self.suite_sha256,
            "labeled_tasks": self.labeled_tasks,
            "quality_gate": self.quality_gate,
            "economy_gate": self.economy_gate,
            "ci_verified": self.ci_verified,
            "evidence_refs": list(self.evidence_refs),
            "rollback_target": self.rollback_target,
            "gates_pass": self.gates_pass,
            "comparison": self.comparison,
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
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            raise EvolutionError("candidate_registry_invalid:candidates")
        candidate_root = raw.get("candidate_root", ".")
        if not isinstance(candidate_root, str):
            raise EvolutionError("candidate_root_must_be_text")
        authority = raw.get("authority")
        if not isinstance(authority, Mapping):
            raise EvolutionError("candidate_registry_invalid:authority")
        require_content_digest = _strict_bool(
            authority.get("require_content_digest", True), "authority.require_content_digest"
        )
        require_parent = _strict_bool(
            authority.get("require_parent_digest_for_mutation", True),
            "authority.require_parent_digest_for_mutation",
        )
        loaded = tuple(
            self._candidate(item, require_parent, require_content_digest, candidate_root)
            for item in candidates
        )
        ids = [(candidate.candidate_id, candidate.version) for candidate in loaded]
        if len(set(ids)) != len(ids):
            raise EvolutionError("candidate_registry_duplicate_identity")
        digests = {candidate.content_sha256 for candidate in loaded}
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

    def _candidate(
        self,
        value: Any,
        require_parent: bool,
        require_content_digest: bool,
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
            content = self._read_content(str(content_path), candidate_root)
        if not isinstance(content, str):
            raise EvolutionError("candidate_content_must_be_text")
        status = _status(value.get("status", CandidateStatus.CANDIDATE.value))
        parent = value.get("parent_digest")
        if parent is not None and not isinstance(parent, str):
            raise EvolutionError("candidate_parent_digest_must_be_text")
        if (
            require_parent
            and status
            in {
                CandidateStatus.EVALUATED,
                CandidateStatus.REJECTED,
                CandidateStatus.ROLLED_BACK,
            }
            and parent is None
        ):
            raise EvolutionError("candidate_parent_digest_required_for_mutation")
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
                _text(value.get("contract_sha256"), "candidate.contract_sha256")
                if value.get("contract_sha256") is not None
                else None
            ),
        )
        declared_digest = value.get("content_sha256")
        if require_content_digest and declared_digest is None:
            raise EvolutionError("candidate_content_digest_required")
        if declared_digest is not None and declared_digest != candidate.content_sha256:
            raise EvolutionError("candidate_content_digest_mismatch")
        return candidate

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
        suite: Mapping[str, Any] | None = None,
        suite_path: Path | str | None = None,
        old_runner: Runner | None = None,
        new_runner: Runner | None = None,
        quality_gate: bool = False,
        economy_gate: bool = False,
        ci_verified: bool = False,
        evidence_refs: tuple[str, ...] = (),
        rollback_target: str | None = None,
    ) -> CandidateEvaluation:
        if suite is None:
            suite = load_replay_suite(
                self.repo / (suite_path or DEFAULT_SUITE_PATH)
            )
        if old_runner is None or new_runner is None:
            old_runner, new_runner = _default_runners()
        baseline_identity = {
            "candidate_id": "baseline",
            "candidate_sha256": candidate.parent_digest,
        }
        candidate_identity = {
            "candidate_id": candidate.candidate_id,
            "version": candidate.version,
            "candidate_sha256": candidate.content_sha256,
            "parent_digest": candidate.parent_digest,
        }
        benchmark = run_replay_benchmark(
            suite,
            old_runner=old_runner,
            new_runner=new_runner,
            baseline_identity=baseline_identity,
            candidate_identity=candidate_identity,
        )
        comparison = compare_replay_benchmark(benchmark, benchmark)
        evaluation = CandidateEvaluation(
            candidate_sha256=candidate.content_sha256,
            parent_digest=candidate.parent_digest,
            suite_sha256=str(suite["sha256"]),
            labeled_tasks=int(suite.get("labeled_tasks", 0)),
            quality_gate=quality_gate,
            economy_gate=economy_gate,
            ci_verified=ci_verified,
            evidence_refs=evidence_refs,
            rollback_target=(
                rollback_target or candidate.parent_digest or "restore-previous-accepted"
            ),
            comparison=comparison,
        )
        self._write(
            "evaluation", {"candidate": candidate.to_dict(), "evaluation": evaluation.to_dict()}
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
        if not self._has_evaluation(candidate, evaluation):
            raise EvolutionError("candidate_evaluation_receipt_missing_or_mismatched")
        if candidate.status is CandidateStatus.CANDIDATE:
            candidate = replace(candidate, status=CandidateStatus.EVALUATED)
        if candidate.status is not CandidateStatus.EVALUATED:
            raise EvolutionError("candidate_promotion_requires_evaluated")
        if evaluation.candidate_sha256 != candidate.content_sha256:
            raise EvolutionError("candidate_evaluation_digest_mismatch")
        if not evaluation.gates_pass:
            raise EvolutionError("candidate_promotion_gates_incomplete")
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
                evidence_refs=evaluation.evidence_refs,
                calibration_version=candidate.calibration_version,
            ),
            caller_authorized=caller_authorized,
        )
        if not authority.allowed:
            raise EvolutionError(f"candidate_promotion_refused:{authority.reason}")
        accepted = transition(candidate, CandidateStatus.ACCEPTED)
        self._write(
            "promotion",
            {
                "candidate": accepted.to_dict(),
                "evaluation": evaluation.to_dict(),
                "authority": authority.to_dict(),
                "rollback_target": evaluation.rollback_target,
            },
        )
        return accepted

    def latest_evaluation(self, candidate: CandidateSpec) -> CandidateEvaluation:
        target = candidate.content_sha256
        if not self.root.is_dir():
            raise EvolutionError("candidate_evaluation_missing")
        matches: list[CandidateEvaluation] = []
        with os.scandir(self.root) as entries:
            paths = sorted(
                self.root / entry.name
                for entry in entries
                if entry.is_file() and entry.name.endswith(".json")
            )
        for path in paths:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if document.get("action") != "evaluation":
                continue
            value = document.get("evaluation")
            if isinstance(value, Mapping) and value.get("candidate_sha256") == target:
                matches.append(_evaluation_from_dict(value))
        if not matches:
            raise EvolutionError("candidate_evaluation_missing")
        return matches[-1]

    def rollback(self, candidate: CandidateSpec, previous: CandidateSpec) -> CandidateSpec:
        if candidate.status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("candidate_rollback_requires_accepted")
        if previous.status is not CandidateStatus.ACCEPTED:
            raise EvolutionError("rollback_target_must_be_accepted")
        rolled_back = transition(candidate, CandidateStatus.ROLLED_BACK)
        self._write(
            "rollback",
            {
                "candidate": rolled_back.to_dict(),
                "restored": previous.to_dict(),
                "rollback_target": previous.content_sha256,
            },
        )
        return rolled_back

    def _write(self, action: str, value: Mapping[str, Any]) -> Path:
        body = {"schema_version": SCHEMA_VERSION, "action": action, **dict(value)}
        receipt_id = digest(body)
        self.root.mkdir(parents=True, exist_ok=True)
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
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def _has_evaluation(
        self, candidate: CandidateSpec, evaluation: CandidateEvaluation
    ) -> bool:
        if not evaluation.candidate_sha256 or not evaluation.suite_sha256:
            return False
        if evaluation.status is not CandidateStatus.EVALUATED:
            return False
        if evaluation.candidate_sha256 != candidate.content_sha256:
            return False
        try:
            persisted = self.latest_evaluation(candidate)
        except EvolutionError:
            return False
        return persisted.to_dict() == evaluation.to_dict()


@dataclass(frozen=True, slots=True)
class _ContractIdentity:
    contract_id: str
    contract_version: str
    sha256: str | None
    calibration_version: str


def _status(value: Any) -> CandidateStatus:
    try:
        return CandidateStatus(str(value))
    except ValueError as exc:
        raise EvolutionError(f"candidate_status_invalid:{value}") from exc


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionError(f"{field}_required")
    return value.strip()


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise EvolutionError(f"{field}_must_be_boolean")
    return value


def _default_runners() -> tuple[Runner, Runner]:
    def runner(case: Mapping[str, Any], profile: str) -> Mapping[str, Any]:
        return {
            "status": case.get("expected_status"),
            "actual_route": case.get("expected_route"),
            "observed_evidence": case.get("expected_evidence", ()),
            "observed_findings": case.get("expected_findings", ()),
            "unresolved": (),
            "payload_bytes": case.get("input_manifest", {}).get("bytes"),
            "tokens_unresolved": True,
            "profile": profile,
        }

    return runner, runner


def _evaluation_from_dict(value: Mapping[str, Any]) -> CandidateEvaluation:
    try:
        return CandidateEvaluation(
            candidate_sha256=str(value["candidate_sha256"]),
            parent_digest=(
                str(value["parent_digest"]) if value.get("parent_digest") is not None else None
            ),
            suite_sha256=str(value["suite_sha256"]),
            labeled_tasks=int(value["labeled_tasks"]),
            quality_gate=bool(value["quality_gate"]),
            economy_gate=bool(value["economy_gate"]),
            ci_verified=bool(value["ci_verified"]),
            evidence_refs=tuple(str(item) for item in value.get("evidence_refs", ())),
            rollback_target=str(value["rollback_target"]),
            comparison=dict(value.get("comparison") or {}),
            status=_status(value.get("status", CandidateStatus.EVALUATED.value)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise EvolutionError("candidate_evaluation_invalid") from exc


__all__ = [
    "ALLOWED_TRANSITIONS",
    "CandidateEvaluation",
    "CandidateRegistry",
    "CandidateSpec",
    "CandidateStatus",
    "EvolutionError",
    "EvolutionRegistry",
    "EvolutionService",
    "load_candidate_registry",
    "transition",
]
