"""Resolve declared evidence into verifiable promotion evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sparkforge.evals.evidence import EvaluationEvidenceBundle, EvidenceRef, canonical_digest


class EvidenceResolutionError(ValueError):
    """Named failure while resolving evidence or derived metrics."""


ResolutionState = Literal["verified", "unresolved", "invalid"]


@dataclass(frozen=True, slots=True)
class ResolvedEvidence:
    state: ResolutionState
    verified_refs: tuple[str, ...]
    verified_ref_kinds: tuple[str, ...]
    unresolved: tuple[str, ...]
    derived_metrics: dict[str, Any]


class EvidenceResolver:
    """Verify execution-mode contracts, refs and metrics from local artifacts."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()

    def resolve(self, bundle: EvaluationEvidenceBundle, policy: Any) -> ResolvedEvidence:
        self._validate_execution(bundle)
        verified_refs, verified_kinds, ref_unresolved = self._resolve_refs(
            bundle.evidence_refs, policy
        )
        derived = self._compile_metrics(bundle.reports)
        self._compare_metrics(bundle, derived)
        unresolved = tuple(sorted(set(bundle.unresolved) | set(ref_unresolved)))
        allowed = set(getattr(policy, "unresolved_allow", ()))
        denied = sorted(
            code
            for code in unresolved
            if code not in allowed or code in set(getattr(policy, "unresolved_deny", ()))
        )
        if denied:
            raise EvidenceResolutionError(
                f"unresolved_not_allowed:{','.join(denied)}"
            )
        required = set(getattr(policy, "required_verified_evidence_kinds", ()))
        missing = sorted(required - set(verified_kinds))
        if missing:
            raise EvidenceResolutionError(
                f"evidence_ref_unverified:{','.join(missing)}"
            )
        state: ResolutionState = "unresolved" if unresolved else "verified"
        return ResolvedEvidence(
            state=state,
            verified_refs=tuple(sorted(verified_refs)),
            verified_ref_kinds=tuple(sorted(verified_kinds)),
            unresolved=unresolved,
            derived_metrics=derived,
        )

    def _validate_execution(self, bundle: EvaluationEvidenceBundle) -> None:
        if bundle.execution_mode == "recorded_host":
            for side in ("baseline", "candidate"):
                transcript = bundle.transcripts.get(side)
                if not isinstance(transcript, Mapping):
                    raise EvidenceResolutionError("recorded_host_transcript_required")
                self._verify_transcript(transcript, side)
        elif bundle.execution_mode == "live_external":
            identity = bundle.execution.get("producer_identity")
            command_id = bundle.execution.get("command_id")
            if not isinstance(identity, (str, Mapping)) or not identity:
                raise EvidenceResolutionError("live_external_identity_required")
            if not isinstance(command_id, str) or not command_id.strip():
                raise EvidenceResolutionError("live_external_command_id_required")
        for side in ("baseline", "candidate"):
            transcript = bundle.transcripts.get(side)
            if isinstance(transcript, Mapping):
                self._verify_transcript(transcript, side)

    def _verify_transcript(self, transcript: Mapping[str, Any], side: str) -> None:
        source_ref = transcript.get("source_ref")
        declared = str(transcript.get("sha256", "")).removeprefix("sha256:")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise EvidenceResolutionError(f"transcript_source_required:{side}")
        path = self._source_path(source_ref)
        if path is None:
            raise EvidenceResolutionError(f"transcript_source_unresolved:{side}")
        if not path.is_file():
            raise EvidenceResolutionError(f"transcript_source_missing:{side}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != declared:
            raise EvidenceResolutionError(f"transcript_sha256_mismatch:{side}")

    def _resolve_refs(
        self, refs: Sequence[EvidenceRef], policy: Any
    ) -> tuple[list[str], list[str], list[str]]:
        verified: list[str] = []
        kinds: list[str] = []
        unresolved: list[str] = []
        for ref in refs:
            path = self._reference_path(ref.ref, policy)
            if path is None:
                unresolved.append(f"evidence_ref_unresolved:{ref.kind}")
                continue
            if not path.is_file():
                unresolved.append(f"evidence_ref_missing:{ref.kind}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != ref.sha256:
                raise EvidenceResolutionError(f"evidence_ref_sha256_mismatch:{ref.kind}")
            verified.append(ref.ref)
            kinds.append(ref.kind)
        return verified, kinds, unresolved

    def _reference_path(self, reference: str, policy: Any) -> Path | None:
        value = reference
        if value.startswith("file:"):
            value = value[5:]
        elif value.startswith("path:"):
            value = value[5:]
        elif ":" in value:
            return None
        roots = tuple(getattr(policy, "evidence_roots", ()))
        search_roots = [self.repo]
        search_roots.extend(self.repo / Path(root) for root in roots)
        candidate = Path(value)
        for root in search_roots:
            target = (root / candidate).resolve()
            if target == self.repo or self.repo not in target.parents:
                continue
            if target.is_file():
                return target
        return None

    def _source_path(self, source_ref: str) -> Path | None:
        value = source_ref
        if value.startswith("file:"):
            value = value[5:]
        elif value.startswith("path:"):
            value = value[5:]
        elif ":" in value:
            return None
        target = Path(value)
        if not target.is_absolute():
            target = self.repo / target
        target = target.resolve()
        if target != self.repo and self.repo not in target.parents:
            return None
        return target

    @staticmethod
    def _compile_metrics(reports: Mapping[str, Any]) -> dict[str, Any]:
        derived = reports.get("derived_metrics")
        if isinstance(derived, Mapping):
            return {
                "comparison": dict(derived.get("comparison", {})),
                "quality": dict(derived.get("quality", {})),
                "economy": dict(derived.get("economy", {})),
            }
        comparison = reports.get("comparison")
        if isinstance(comparison, Mapping):
            return {
                "comparison": dict(comparison),
                "quality": dict(reports.get("quality", {})),
                "economy": dict(reports.get("economy", {})),
            }
        baseline = reports.get("baseline")
        candidate = reports.get("candidate")
        if isinstance(baseline, Mapping) and isinstance(candidate, Mapping):
            baseline_metrics = baseline.get("metrics")
            candidate_metrics = candidate.get("metrics")
            if isinstance(baseline_metrics, Mapping) and isinstance(candidate_metrics, Mapping):
                return {
                    "comparison": {
                        "metrics": {
                            "baseline": dict(baseline_metrics),
                            "candidate": dict(candidate_metrics),
                        },
                        "cells": list(reports.get("cells", [])),
                    },
                    "quality": dict(reports.get("quality", {})),
                    "economy": dict(reports.get("economy", {})),
                }
        raise EvidenceResolutionError("metrics_unresolved")

    @staticmethod
    def _compare_metrics(
        bundle: EvaluationEvidenceBundle, derived: Mapping[str, Any]
    ) -> None:
        supplied = {
            "comparison": bundle.metrics.get("comparison"),
            "quality": bundle.metrics.get("quality"),
            "economy": bundle.metrics.get("economy"),
        }
        expected = {
            "comparison": derived.get("comparison"),
            "quality": derived.get("quality"),
            "economy": derived.get("economy"),
        }
        for name in ("comparison", "quality", "economy"):
            if canonical_digest(supplied[name]) != canonical_digest(expected[name]):
                raise EvidenceResolutionError(f"metrics_mismatch:{name}")


__all__ = ["EvidenceResolutionError", "EvidenceResolver", "ResolvedEvidence", "ResolutionState"]
