"""Resolve declared evidence into verifiable promotion evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sparkforge_aws.evals.evidence import EvaluationEvidenceBundle, EvidenceRef, canonical_digest
from sparkforge_aws.evals.evidence_adapters import AuthorizedCommandAdapter
from sparkforge_aws.evals.metric_compiler import MetricCompilationError, compile_reports


class EvidenceResolutionError(ValueError):
    """Named failure while resolving evidence or derived metrics."""


ResolutionState = Literal["verified", "unresolved", "invalid"]


@dataclass(frozen=True, slots=True)
class ResolvedEvidence:
    state: ResolutionState
    verified_refs: tuple[str, ...]
    verified_ref_kinds: tuple[str, ...]
    unresolved: tuple[str, ...]
    blocking_unresolved: tuple[str, ...]
    derived_metrics: dict[str, Any]
    producer_identity_sha256: str | None = None


class EvidenceResolver:
    """Verify execution-mode contracts, refs and metrics from local artifacts."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()

    def resolve(
        self,
        bundle: EvaluationEvidenceBundle,
        policy: Any,
        *,
        authorized_commands: Mapping[str, Any] | None = None,
    ) -> ResolvedEvidence:
        producer_identity = self._validate_execution(
            bundle, policy, authorized_commands=authorized_commands
        )
        verified_refs, verified_kinds, ref_unresolved = self._resolve_refs(
            bundle.evidence_refs, policy
        )
        require_raw_metrics = bundle.execution_mode in {"recorded_host", "live_external"}
        try:
            derived = compile_reports(bundle.reports, require_raw=require_raw_metrics)
        except MetricCompilationError:
            derived = {"comparison": {}, "quality": {}, "economy": {}}
            metric_unresolved = ("metrics_unresolved",)
        else:
            metric_unresolved = ()
            self._compare_metrics(bundle, derived)
        unresolved = tuple(
            sorted(set(bundle.unresolved) | set(ref_unresolved) | set(metric_unresolved))
        )
        allowed = set(getattr(policy, "unresolved_allow", ()))
        denied_codes = set(getattr(policy, "unresolved_deny", ()))
        denied = sorted(
            code
            for code in unresolved
            if code not in allowed or code in denied_codes
        )
        required = set(getattr(policy, "required_verified_evidence_kinds", ()))
        missing = sorted(required - set(verified_kinds))
        blocking = tuple(
            sorted(
                {
                    *denied,
                    *(f"evidence_ref_unverified:{kind}" for kind in missing),
                }
            )
        )
        state: ResolutionState = (
            "invalid" if blocking else ("unresolved" if unresolved else "verified")
        )
        return ResolvedEvidence(
            state=state,
            verified_refs=tuple(sorted(verified_refs)),
            verified_ref_kinds=tuple(sorted(verified_kinds)),
            unresolved=unresolved,
            blocking_unresolved=blocking,
            derived_metrics=derived,
            producer_identity_sha256=producer_identity,
        )

    def _validate_execution(
        self,
        bundle: EvaluationEvidenceBundle,
        policy: Any,
        *,
        authorized_commands: Mapping[str, Any] | None,
    ) -> str | None:
        if bundle.execution_mode == "recorded_host":
            for side in ("baseline", "candidate"):
                transcript = bundle.transcripts.get(side)
                if not isinstance(transcript, Mapping):
                    raise EvidenceResolutionError("recorded_host_transcript_required")
                self._verify_transcript(transcript, side, policy)
        elif bundle.execution_mode == "live_external":
            command_id = bundle.execution.get("command_id")
            if not isinstance(command_id, str) or not command_id.strip():
                raise EvidenceResolutionError("live_external_command_id_required")
            if not authorized_commands or command_id not in authorized_commands:
                raise EvidenceResolutionError("live_external_command_not_authorized")
            try:
                expected = AuthorizedCommandAdapter(
                    authorized_commands, repo=self.repo
                ).identity(command_id)
            except Exception as exc:
                raise EvidenceResolutionError(
                    "live_external_producer_identity_unresolved"
                ) from exc
            declared = bundle.execution.get("command_identity_sha256")
            producer = bundle.execution.get("producer_identity")
            if isinstance(producer, Mapping):
                declared = producer.get("command_identity_sha256", declared)
            if not isinstance(declared, str) or not declared.strip():
                raise EvidenceResolutionError("live_external_producer_identity_unresolved")
            if declared.removeprefix("sha256:") != expected.sha256:
                raise EvidenceResolutionError("live_external_producer_identity_mismatch")
        for side in ("baseline", "candidate"):
            transcript = bundle.transcripts.get(side)
            if isinstance(transcript, Mapping):
                self._verify_transcript(transcript, side, policy)
        producer = bundle.execution.get("producer_identity")
        if isinstance(producer, Mapping):
            identity = producer.get("command_identity_sha256")
            return str(identity).removeprefix("sha256:") if identity else None
        identity = bundle.execution.get("command_identity_sha256")
        return str(identity).removeprefix("sha256:") if identity else None

    def _verify_transcript(self, transcript: Mapping[str, Any], side: str, policy: Any) -> None:
        source_ref = transcript.get("source_ref")
        declared = str(transcript.get("sha256", "")).removeprefix("sha256:")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise EvidenceResolutionError(f"transcript_source_required:{side}")
        path = self._source_path(source_ref, policy)
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
        aliases: dict[tuple[str, str], str] = {}
        for ref in refs:
            if ref.kind not in {"ci", "benchmark", "review"}:
                raise EvidenceResolutionError(f"evidence_kind_unknown:{ref.kind}")
            alias_key = (ref.ref, ref.sha256)
            previous_kind = aliases.get(alias_key)
            if previous_kind is not None and previous_kind != ref.kind:
                raise EvidenceResolutionError("evidence_kind_aliasing_detected")
            aliases[alias_key] = ref.kind
            path = self._reference_path(ref.ref, ref.kind, policy)
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

    def _reference_path(self, reference: str, kind: str, policy: Any) -> Path | None:
        value = reference
        if value.startswith("file:"):
            value = value[5:]
        elif value.startswith("path:"):
            value = value[5:]
        elif ":" in value:
            return None
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise EvidenceResolutionError("evidence_ref_path_escape")
        roots = self._roots_for(policy, kind)
        for root_value in roots:
            root = self._authorized_root(root_value)
            target = (root / candidate).resolve()
            if root != target and root not in target.parents:
                raise EvidenceResolutionError("evidence_ref_outside_authorized_root")
            if target.is_file():
                return target
        return None

    def _source_path(self, source_ref: str, policy: Any) -> Path | None:
        value = source_ref
        if value.startswith("file:"):
            value = value[5:]
        elif value.startswith("path:"):
            value = value[5:]
        elif ":" in value:
            return None
        target = Path(value)
        roots = self._all_roots(policy)
        if target.is_absolute():
            resolved = target.resolve()
            if not any(root == resolved or root in resolved.parents for root in roots):
                raise EvidenceResolutionError("transcript_source_outside_authorized_root")
            return resolved
        if ".." in target.parts:
            raise EvidenceResolutionError("transcript_source_outside_authorized_root")
        for root in roots:
            resolved = (root / target).resolve()
            if root != resolved and root not in resolved.parents:
                raise EvidenceResolutionError("transcript_source_outside_authorized_root")
            if resolved.is_file():
                return resolved
        return None

    @staticmethod
    def _roots_for(policy: Any, kind: str) -> tuple[str, ...]:
        try:
            roots = policy.roots_for(kind)
        except AttributeError:
            configured = dict(getattr(policy, "evidence_kind_roots", ()))
            if configured:
                if kind not in configured:
                    raise EvidenceResolutionError(
                        f"evidence_kind_unconfigured:{kind}"
                    ) from None
                roots = configured[kind]
            else:
                roots = getattr(policy, "evidence_roots", ())
        except Exception as exc:
            raise EvidenceResolutionError(str(exc)) from exc
        return tuple(str(root) for root in roots)

    def _all_roots(self, policy: Any) -> tuple[Path, ...]:
        raw: list[str] = []
        configured = dict(getattr(policy, "evidence_kind_roots", ()))
        if configured:
            for roots in configured.values():
                raw.extend(str(root) for root in roots)
        else:
            raw.extend(str(root) for root in getattr(policy, "evidence_roots", ()))
        return tuple(dict.fromkeys(self._authorized_root(root) for root in raw))

    def _authorized_root(self, value: str) -> Path:
        root = (self.repo / Path(value)).resolve()
        if root != self.repo and self.repo not in root.parents:
            raise EvidenceResolutionError("evidence_root_outside_repository")
        return root

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
