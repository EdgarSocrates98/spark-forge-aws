"""Explicit evaluation policy resolution for candidate families and contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sparkforge.decision.fingerprint import digest


class EvaluationPolicyError(ValueError):
    """Named policy loading and resolution failure."""


@dataclass(frozen=True, slots=True)
class EvaluationPolicy:
    policy_id: str
    policy_version: str
    family: str
    kind: str
    contract_id: str
    contract_version: str
    minimum_labeled_tasks: int
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
    unresolved_deny: tuple[str, ...] = ()
    unresolved_allow: tuple[str, ...] = ()
    required_verified_evidence_kinds: tuple[str, ...] = ()
    evidence_roots: tuple[str, ...] = ()
    policy_sha256: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.family, self.kind, self.contract_id, self.contract_version)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        value = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "family": self.family,
            "kind": self.kind,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "minimum_labeled_tasks": self.minimum_labeled_tasks,
            "quality": {
                "min_status_accuracy": self.min_status_accuracy,
                "min_evidence_recall": self.min_evidence_recall,
                "max_false_positive_rate": self.max_false_positive_rate,
                "max_quality_regression": self.max_quality_regression,
                "min_route_accuracy": self.min_route_accuracy,
                "max_route_regression": self.max_route_regression,
                "require_route_metric": self.require_route_metric,
            },
            "economy": {
                "max_payload_regression": self.max_payload_regression,
                "max_token_regression": self.max_token_regression,
                "max_cost_regression": self.max_cost_regression,
                "require_tokens": self.require_tokens,
                "require_cost": self.require_cost,
            },
            "unresolved": {
                "deny": list(self.unresolved_deny),
                "allow": list(self.unresolved_allow),
            },
            "evidence": {
                "required_verified_kinds": list(self.required_verified_evidence_kinds),
                "roots": list(self.evidence_roots),
            },
        }
        if include_digest:
            value["policy_sha256"] = self.policy_sha256
        return value

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        policy_version: str,
    ) -> EvaluationPolicy:
        if not isinstance(value, Mapping):
            raise EvaluationPolicyError("evaluation_policy_invalid:entry")
        required = (
            "policy_id",
            "family",
            "kind",
            "contract_id",
            "contract_version",
            "minimum_labeled_tasks",
        )
        for field in required:
            if not isinstance(value.get(field), str) and field != "minimum_labeled_tasks":
                raise EvaluationPolicyError(f"evaluation_policy_invalid:{field}")
        minimum = value.get("minimum_labeled_tasks")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            raise EvaluationPolicyError("evaluation_policy_invalid:minimum_labeled_tasks")
        quality = value.get("quality", {})
        economy = value.get("economy", {})
        unresolved = value.get("unresolved", {})
        evidence = value.get("evidence", {})
        if (
            not isinstance(quality, Mapping)
            or not isinstance(economy, Mapping)
            or not isinstance(unresolved, Mapping)
            or not isinstance(evidence, Mapping)
        ):
            raise EvaluationPolicyError("evaluation_policy_invalid:quality_economy")
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
        known_unresolved = {"deny", "allow"}
        known_evidence = {"required_verified_kinds", "roots"}
        unknown = sorted(
            (set(quality) - known_quality)
            | (set(economy) - known_economy)
            | {f"unresolved.{key}" for key in set(unresolved) - known_unresolved}
            | {f"evidence.{key}" for key in set(evidence) - known_evidence}
        )
        if unknown:
            raise EvaluationPolicyError(f"evaluation_policy_unknown_fields:{','.join(unknown)}")

        def strings(section: Mapping[str, Any], name: str) -> tuple[str, ...]:
            raw = section.get(name, ())
            if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
                raise EvaluationPolicyError(f"evaluation_policy_invalid:{name}")
            if any(not isinstance(item, str) or not item.strip() for item in raw):
                raise EvaluationPolicyError(f"evaluation_policy_invalid:{name}")
            return tuple(sorted({item.strip() for item in raw}))

        def number(
            section: Mapping[str, Any],
            name: str,
            default: float,
            optional: bool = False,
        ) -> float | None:
            raw = section.get(name, default)
            if raw is None and optional:
                return None
            if (
                isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not 0 <= float(raw) <= 1
            ):
                raise EvaluationPolicyError(f"evaluation_policy_invalid:{name}")
            return float(raw)

        def boolean(section: Mapping[str, Any], name: str, default: bool) -> bool:
            raw = section.get(name, default)
            if not isinstance(raw, bool):
                raise EvaluationPolicyError(f"evaluation_policy_invalid:{name}")
            return raw

        normalized = cls(
            policy_id=str(value["policy_id"]).strip(),
            policy_version=str(policy_version).strip(),
            family=str(value["family"]).strip(),
            kind=str(value["kind"]).strip(),
            contract_id=str(value["contract_id"]).strip(),
            contract_version=str(value["contract_version"]).strip(),
            minimum_labeled_tasks=minimum,
            min_status_accuracy=float(number(quality, "min_status_accuracy", 1.0)),
            min_evidence_recall=float(number(quality, "min_evidence_recall", 1.0)),
            max_false_positive_rate=float(number(quality, "max_false_positive_rate", 0.0)),
            max_quality_regression=float(number(quality, "max_quality_regression", 0.0)),
            min_route_accuracy=number(quality, "min_route_accuracy", 0.0, optional=True),
            max_route_regression=float(number(quality, "max_route_regression", 0.0)),
            require_route_metric=boolean(quality, "require_route_metric", False),
            max_payload_regression=float(number(economy, "max_payload_regression", 0.0)),
            max_token_regression=float(number(economy, "max_token_regression", 0.0)),
            max_cost_regression=float(number(economy, "max_cost_regression", 0.0)),
            require_tokens=boolean(economy, "require_tokens", False),
            require_cost=boolean(economy, "require_cost", False),
            unresolved_deny=strings(unresolved, "deny"),
            unresolved_allow=strings(unresolved, "allow"),
            required_verified_evidence_kinds=strings(
                evidence, "required_verified_kinds"
            ),
            evidence_roots=strings(evidence, "roots"),
            policy_sha256="",
        )
        expected = digest(normalized.to_dict(include_digest=False))
        declared = value.get("policy_sha256")
        if declared is not None and str(declared).removeprefix("sha256:") != expected:
            raise EvaluationPolicyError(f"evaluation_policy_digest_mismatch:{normalized.policy_id}")
        return replace(normalized, policy_sha256=expected)


class PolicyResolver:
    """Resolve one explicit policy without a default fallback."""

    def __init__(self, policies: Sequence[EvaluationPolicy], *, policy_version: str) -> None:
        self.policy_version = policy_version
        self._policies = tuple(policies)
        keys = [policy.key for policy in self._policies]
        if len(keys) != len(set(keys)):
            duplicate = next(key for key in keys if keys.count(key) > 1)
            raise EvaluationPolicyError(f"evaluation_policy_ambiguous:{duplicate}")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> PolicyResolver:
        version = raw.get("policy_version")
        policies_raw = raw.get("policies", ())
        if not isinstance(version, str) or not version.strip():
            if policies_raw:
                raise EvaluationPolicyError("evaluation_policy_invalid:policy_version")
            version = "legacy"
        if isinstance(policies_raw, (str, bytes)) or not isinstance(policies_raw, Sequence):
            raise EvaluationPolicyError("evaluation_policy_invalid:policies")
        policies = tuple(
            EvaluationPolicy.from_mapping(item, policy_version=version)
            for item in policies_raw
        )
        return cls(policies, policy_version=version.strip())

    @property
    def policies(self) -> tuple[EvaluationPolicy, ...]:
        return self._policies

    def resolve(
        self,
        candidate: Any,
        *,
        family: str | None = None,
        kind: str | None = None,
        contract_id: str | None = None,
        contract_version: str | None = None,
    ) -> EvaluationPolicy:
        key = (
            family or str(getattr(candidate, "family", "")),
            kind or str(getattr(candidate, "kind", "")),
            contract_id or str(getattr(candidate, "contract_id", "")),
            contract_version or str(getattr(candidate, "contract_version", "")),
        )
        matches = [policy for policy in self._policies if policy.key == key]
        if not matches:
            raise EvaluationPolicyError(f"evaluation_policy_missing:{'|'.join(key)}")
        if len(matches) != 1:
            raise EvaluationPolicyError(f"evaluation_policy_ambiguous:{'|'.join(key)}")
        return matches[0]


__all__ = ["EvaluationPolicy", "EvaluationPolicyError", "PolicyResolver"]
