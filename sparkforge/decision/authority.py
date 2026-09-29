"""Single fail-closed authority policy for bounded decision execution.

The decision core is provider-independent.  This module therefore accepts only
typed evidence and repository configuration; it never discovers authority from
benchmark output or from an external provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    """Evidence carried by an explicit promotion request."""

    promotion_id: str = ""
    contract_id: str = ""
    contract_version: str = ""
    contract_sha256: str | None = None
    labeled_tasks: int = 0
    quality_gate: bool = False
    economy_gate: bool = False
    ci_verified: bool = False
    rollback: str = ""
    evidence_refs: tuple[str, ...] = ()
    calibration_version: str = "none"

    def __post_init__(self) -> None:
        if self.labeled_tasks < 0:
            raise ValueError("labeled_tasks must be non-negative")
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted({str(ref).strip() for ref in self.evidence_refs if str(ref).strip()})),
        )

    @classmethod
    def from_value(cls, value: Any | None) -> PromotionEvidence:
        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                promotion_id=str(value.get("promotion_id", "")),
                contract_id=str(value.get("contract_id", "")),
                contract_version=str(value.get("contract_version", "")),
                contract_sha256=(
                    str(value["contract_sha256"])
                    if value.get("contract_sha256") is not None
                    else None
                ),
                labeled_tasks=int(value.get("labeled_tasks", 0)),
                quality_gate=bool(value.get("quality_gate", False)),
                economy_gate=bool(value.get("economy_gate", False)),
                ci_verified=bool(value.get("ci_verified", False)),
                rollback=str(value.get("rollback", "")),
                evidence_refs=tuple(str(item) for item in value.get("evidence_refs", ())),
                calibration_version=str(value.get("calibration_version", "none")),
            )
        return cls(
            promotion_id=str(getattr(value, "promotion_id", "")),
            contract_id=str(getattr(value, "contract_id", "")),
            contract_version=str(getattr(value, "contract_version", "")),
            contract_sha256=getattr(value, "contract_sha256", None),
            labeled_tasks=int(getattr(value, "labeled_tasks", 0)),
            quality_gate=bool(getattr(value, "quality_gate", False)),
            economy_gate=bool(getattr(value, "economy_gate", False)),
            ci_verified=bool(getattr(value, "ci_verified", False)),
            rollback=str(getattr(value, "rollback", "")),
            evidence_refs=tuple(getattr(value, "evidence_refs", ())),
            calibration_version=str(getattr(value, "calibration_version", "none")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "labeled_tasks": self.labeled_tasks,
            "quality_gate": self.quality_gate,
            "economy_gate": self.economy_gate,
            "ci_verified": self.ci_verified,
            "rollback": self.rollback,
            "evidence_refs": list(self.evidence_refs),
            "calibration_version": self.calibration_version,
        }


@dataclass(frozen=True, slots=True)
class AuthorityDecision:
    allowed: bool
    mode: str
    reason: str | None
    policy_version: str
    calibration_version: str
    evidence_refs: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "reason": self.reason,
            "policy_version": self.policy_version,
            "calibration_version": self.calibration_version,
            "evidence_refs": list(self.evidence_refs),
            "unresolved": list(self.unresolved),
        }


class AuthorityPolicy:
    """Repository-scoped authority resolver shared by all promotion paths."""

    def __init__(self, raw: Mapping[str, Any] | None = None) -> None:
        values = dict(raw or {})
        authority = values.get("authority", {})
        if not isinstance(authority, Mapping):
            raise ValueError("authority policy must be a mapping")
        active = authority.get("active", {})
        if not isinstance(active, Mapping):
            raise ValueError("authority.active must be a mapping")
        self.policy_version = str(values.get("policy_version", "agentic-control-v1")).strip()
        if not self.policy_version:
            raise ValueError("policy_version is required")
        self.default_mode = str(authority.get("default_mode", "shadow")).strip().lower()
        self.active_enabled = bool(active.get("enabled", False))
        self.minimum_labeled_tasks = int(active.get("minimum_labeled_tasks", 50))
        self.require_quality_gate = bool(active.get("require_quality_gate", True))
        self.require_economy_gate = bool(active.get("require_economy_gate", True))
        self.require_ci_gate = bool(active.get("require_ci_gate", True))
        self.require_rollback = bool(active.get("require_rollback", True))
        if self.minimum_labeled_tasks < 1:
            raise ValueError("minimum_labeled_tasks must be positive")

    @classmethod
    def from_repo(cls, repo: Path | str = ".") -> AuthorityPolicy:
        root = Path(repo).expanduser().resolve()
        path = root / "config" / "decisions" / "agentic_control_plane.yaml"
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ValueError(f"authority_policy_unreadable:{path}") from exc
        if not isinstance(raw, Mapping):
            raise ValueError("authority policy must be a mapping")
        return cls(raw)

    def authorize_promotion(
        self,
        *,
        mode: str,
        contract: Any | None = None,
        evidence: PromotionEvidence | Mapping[str, Any] | Any | None = None,
        caller_authorized: bool = False,
        evidence_refs: tuple[str, ...] = (),
        unresolved: tuple[str, ...] = (),
    ) -> AuthorityDecision:
        normalized = str(mode).strip().lower()
        contract_policy = self.policy_version
        calibration = str(getattr(contract, "calibration_version", "none"))
        promotion = PromotionEvidence.from_value(evidence)
        refs = tuple(sorted(set(evidence_refs) | set(promotion.evidence_refs)))
        if normalized == "shadow":
            return AuthorityDecision(True, normalized, None, contract_policy, calibration, refs)
        if normalized not in {"assisted", "active"}:
            return self._refused(normalized, "unsupported_authority_mode", calibration, refs)
        if unresolved:
            return self._refused(
                normalized, "promotion_evidence_unresolved", calibration, refs, unresolved
            )
        if normalized == "active" and not self.active_enabled:
            return self._refused(normalized, "active_disabled_by_policy", calibration, refs)
        if not caller_authorized:
            return self._refused(normalized, "explicit_authority_required", calibration, refs)
        if normalized == "active" and contract is not None and not bool(
            getattr(contract, "activation_enabled", True)
        ):
            return self._refused(normalized, "contract_activation_disabled", calibration, refs)
        missing = self._missing_evidence(promotion, contract) if normalized == "active" else ()
        if missing:
            return self._refused(
                normalized,
                "promotion_evidence_incomplete",
                calibration,
                refs,
                tuple(missing),
            )
        return AuthorityDecision(True, normalized, None, contract_policy, calibration, refs)

    def _missing_evidence(
        self, evidence: PromotionEvidence, contract: Any | None
    ) -> tuple[str, ...]:
        missing: list[str] = []
        if not evidence.promotion_id.strip():
            missing.append("promotion_id_missing")
        if contract is not None:
            if evidence.contract_id != str(getattr(contract, "contract_id", "")):
                missing.append("promotion_contract_id_mismatch")
            if evidence.contract_version != str(getattr(contract, "contract_version", "")):
                missing.append("promotion_contract_version_mismatch")
            if evidence.contract_sha256 is not None and evidence.contract_sha256 != getattr(
                contract, "sha256", None
            ):
                missing.append("promotion_contract_sha256_mismatch")
        if evidence.labeled_tasks < self.minimum_labeled_tasks:
            missing.append(f"promotion_corpus_below_{self.minimum_labeled_tasks}_labeled_tasks")
        if self.require_quality_gate and not evidence.quality_gate:
            missing.append("promotion_quality_gate_missing")
        if self.require_economy_gate and not evidence.economy_gate:
            missing.append("promotion_economy_gate_missing")
        if self.require_ci_gate and not evidence.ci_verified:
            missing.append("promotion_ci_gate_missing")
        if self.require_rollback and not evidence.rollback.strip():
            missing.append("promotion_rollback_missing")
        return tuple(missing)

    def _refused(
        self,
        mode: str,
        reason: str,
        calibration: str,
        refs: tuple[str, ...],
        unresolved: tuple[str, ...] = (),
    ) -> AuthorityDecision:
        return AuthorityDecision(
            False,
            mode,
            reason,
            self.policy_version,
            calibration,
            refs,
            tuple(unresolved),
        )


__all__ = ["AuthorityDecision", "AuthorityPolicy", "PromotionEvidence"]
