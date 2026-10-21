"""Evidence handoff: specialist stdout → ``theforge/EvidenceHandoff/v1`` → disk.

Parsers are typed, never raw passthrough:

- **data-sentinel** emits a ``DiagnosticReport`` (``--json``): ``findings[]``
  carry ``finding_id``/``severity``/``status``/``explanation``/``evidence_ids``.
  ``status`` is the sentinel FindingStatus vocabulary
  (CONFIRMED/PROBABLE/POSSIBLE/UNKNOWN) mapped through
  ``normalize_confidence`` — PROBABLE → LIKELY, POSSIBLE stays POSSIBLE; a
  rename, never a promotion.
- **forge-doctor-data** ``scan --format agent`` emits ``scan-json@3.0``:
  ``findings[]`` carry ``id``/``sev``/``loc``/``fp``. ``sev`` maps through
  ``normalize_severity`` (error→high, warning→medium, info→info). The agent
  format carries no confidence — handed off as ``UNKNOWN``, never invented.

Persisted under ``.sparkforge_aws/delegation/handoffs/`` as canonical JSON —
redacted then integrity-sealed (``governance.redact_handoff`` +
``seal_handoff``) before write. A persisted handoff is evidence, never an
instruction: nothing in the pipeline reads it back as a command.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge_aws.delegation.contracts import (
    EVIDENCE_HANDOFF_SCHEMA,
    MAX_SUMMARY_CHARS,
    EvidenceHandoff,
    EvidenceRef,
    ExecResult,
    HandoffError,
    check_evidence_ref,
    normalize_confidence,
    normalize_severity,
    sha256_of,
    to_dict,
    utc_now,
)
from sparkforge_aws.delegation.governance import (
    idempotency_key,
    redact_handoff,
    seal_handoff,
)

__all__ = [
    "parse_sentinel_report",
    "parse_doctor_scan",
    "build_handoff",
    "persist_handoff",
    "load_handoffs",
    "HANDOFFS_DIR",
]

HANDOFFS_DIR = "delegation/handoffs"
_STATE_DIR = ".sparkforge_aws"


class HandoffParseError(ValueError):
    """A specialist emitted output this parser cannot safely consume."""


# ---------------------------------------------------------------------------
# Output parsers (typed readers — never raw passthrough)
# ---------------------------------------------------------------------------

def _truncate(text: str, cap: int = MAX_SUMMARY_CHARS) -> str:
    return text[:cap]


def _clean_refs(refs: list[str], *, dropped: list[str]) -> list[str]:
    """Keep only refs that satisfy the contract shape; count the rest.

    A specialist's ``evidence_ids``/``loc`` are untrusted text — a ref with
    whitespace or traversal must not crash the whole handoff nor be silently
    rewritten; it is dropped and the count lands in ``limitations``.
    """
    clean: list[str] = []
    for ref in refs[:16]:
        try:
            check_evidence_ref(ref, field="evidence_refs")
        except Exception:
            dropped.append(ref[:40])
            continue
        clean.append(ref)
    return clean


def parse_sentinel_report(stdout: str) -> dict[str, Any]:
    """Parse a data-sentinel ``--json`` DiagnosticReport into handoff fields.

    Returns ``{"findings": [...], "limitations": [...], "summary_refs": [...]}``
    — the *content* of a handoff; identity fields are added by
    ``build_handoff``. Non-JSON or non-report output is a HandoffParseError,
    which callers surface as ``invalid-output`` — never a silent zero.
    """
    try:
        doc = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HandoffParseError(f"sentinel output is not JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise HandoffParseError("sentinel output is not a JSON object")
    raw_findings = doc.get("findings")
    if raw_findings is None:
        # Non-report JSON (e.g. `glue inspect` metadata, `glue runs` list):
        # still evidence — surfaced as a bounded summary ref, no findings.
        return {
            "findings": [],
            "limitations": list(doc.get("limitations") or []),
            "summary_refs": [
                {
                    "kind": "summary",
                    "value": _truncate(json.dumps(doc, ensure_ascii=False)),
                    "detail": "non-report JSON payload",
                }
            ],
        }
    if not isinstance(raw_findings, list):
        raise HandoffParseError("sentinel findings is not a list")
    findings: list[dict[str, Any]] = []
    dropped_refs: list[str] = []
    for i, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            raise HandoffParseError(f"sentinel findings[{i}] is not an object")
        finding_id = item.get("finding_id") or item.get("id")
        if not isinstance(finding_id, str) or not finding_id:
            raise HandoffParseError(f"sentinel findings[{i}] has no finding_id")
        try:
            severity = normalize_severity(str(item.get("severity", "info")))
            confidence = normalize_confidence(str(item.get("status", "UNKNOWN")))
        except Exception as exc:
            raise HandoffParseError(f"sentinel findings[{i}]: {exc}") from exc
        refs = item.get("evidence_ids") or []
        findings.append(
            {
                "id": finding_id,
                "severity": severity,
                "confidence": confidence,
                "summary": _truncate(str(item.get("explanation") or "")),
                "evidence_refs": _clean_refs(
                    [str(r) for r in refs], dropped=dropped_refs
                ),
            }
        )
    limitations = [str(x) for x in doc.get("limitations") or []]
    if dropped_refs:
        limitations.append(
            f"{len(dropped_refs)} evidence ref(s) dropped — invalid ref shape"
        )
    return {"findings": findings, "limitations": limitations, "summary_refs": []}


def parse_doctor_scan(stdout: str) -> dict[str, Any]:
    """Parse a forge-doctor-data ``scan --format agent`` payload (scan-json@3.0).

    ``sev`` renames through ``normalize_severity``; the format carries no
    confidence → ``UNKNOWN`` (unknown ≠ zero, and never promoted).
    """
    try:
        doc = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HandoffParseError(f"doctor output is not JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise HandoffParseError("doctor output is not a JSON object")
    if doc.get("schema_version") not in ("3.0", 3.0):
        raise HandoffParseError(
            f"doctor scan payload schema_version {doc.get('schema_version')!r} "
            "is not '3.0' — the agent format is versioned, never guessed"
        )
    raw_findings = doc.get("findings") or []
    if not isinstance(raw_findings, list):
        raise HandoffParseError("doctor findings is not a list")
    findings: list[dict[str, Any]] = []
    dropped_refs: list[str] = []
    for i, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            raise HandoffParseError(f"doctor findings[{i}] is not an object")
        fid = item.get("id")
        if not isinstance(fid, str) or not fid:
            raise HandoffParseError(f"doctor findings[{i}] has no id")
        try:
            severity = normalize_severity(str(item.get("sev", "info")))
        except Exception as exc:
            raise HandoffParseError(f"doctor findings[{i}]: {exc}") from exc
        refs: list[str] = []
        loc = item.get("loc")
        if isinstance(loc, str) and loc:
            refs.append(loc)
        fp = item.get("fp")
        if isinstance(fp, str) and fp:
            refs.append(f"fp:{fp}")
        findings.append(
            {
                "id": fid,
                "severity": severity,
                "confidence": "UNKNOWN",
                "summary": "",
                "evidence_refs": _clean_refs(refs, dropped=dropped_refs),
            }
        )
    summary = doc.get("summary")
    limitations: list[str] = []
    if isinstance(summary, dict):
        limitations.append(
            "summary: "
            + ", ".join(f"{k}={v}" for k, v in sorted(summary.items()))
        )
    if dropped_refs:
        limitations.append(
            f"{len(dropped_refs)} evidence ref(s) dropped — invalid ref shape"
        )
    return {"findings": findings, "limitations": limitations, "summary_refs": []}


_PARSERS = {
    "data-sentinel-forge": parse_sentinel_report,
    "forge-doctor-data": parse_doctor_scan,
}


def parser_for(provider: str):
    return _PARSERS.get(provider)


# ---------------------------------------------------------------------------
# Handoff construction
# ---------------------------------------------------------------------------

def build_handoff(
    *,
    run_id: str,
    correlation_id: str,
    source_provider: str,
    source_version: str,
    consumer_provider: str,
    capability: str,
    capability_version: str,
    exec_result: ExecResult | None,
    input_refs: list[EvidenceRef],
    parsed: dict[str, Any] | None,
    refusal: HandoffError | None = None,
) -> EvidenceHandoff:
    """Assemble the evidence envelope — then bound, redact and seal it.

    ``parsed`` is the output of ``parse_*``; ``refusal`` the named failure.
    A completed/partial envelope never carries an error; a
    failed/refused/cancelled envelope requires one (contract invariant).
    """
    now = utc_now()
    if refusal is not None:
        status = "refused" if refusal.code in (
            "permission-denied", "policy-refusal", "provider-absent",
            "capability-absent", "version-incompatible", "invalid-input",
            "invalid-output", "insufficient-evidence", "cycle-detected",
            "budget-exhausted",
        ) else ("cancelled" if refusal.code == "cancelled" else "failed")
        doc: dict[str, Any] = {
            "schema": EVIDENCE_HANDOFF_SCHEMA,
            "run_id": run_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key(
                source_provider, capability, run_id,
                sha256_of({"argv": exec_result.argv if exec_result else []}),
            ),
            "source_provider": source_provider,
            "source_version": source_version,
            "consumer_provider": consumer_provider,
            "capability": capability,
            "capability_version": capability_version,
            "status": status,
            "input_refs": [to_dict(r) for r in input_refs],
            "error": {
                "code": refusal.code,
                "detail": refusal.detail,
                "retryable": refusal.retryable,
            },
            "created_at": now,
        }
    else:
        parsed = parsed or {"findings": [], "limitations": [], "summary_refs": []}
        truncated = bool(exec_result and (exec_result.stdout_truncated))
        status = "partial" if truncated else "completed"
        resources = None
        if exec_result is not None:
            resources = {
                "elapsed_ms": exec_result.elapsed_ms,
                "stdout_bytes": exec_result.stdout_bytes,
                "stderr_bytes": exec_result.stderr_bytes,
                "provider_tokens": None,  # never inferred from bytes
            }
        doc = {
            "schema": EVIDENCE_HANDOFF_SCHEMA,
            "run_id": run_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key(
                source_provider, capability, run_id,
                sha256_of({"argv": exec_result.argv if exec_result else []}),
            ),
            "source_provider": source_provider,
            "source_version": source_version,
            "consumer_provider": consumer_provider,
            "capability": capability,
            "capability_version": capability_version,
            "status": status,
            "input_refs": [to_dict(r) for r in input_refs],
            "result_refs": list(parsed.get("summary_refs") or []),
            "findings": parsed["findings"],
            "limitations": parsed["limitations"],
            "created_at": now,
            "started_at": now,
            "finished_at": utc_now(),
            "resources": resources,
        }
    # bound → redact → seal: truncation flags, credential scrub, integrity.
    from sparkforge_aws.delegation.governance import bound_handoff

    handoff = bound_handoff(doc)
    handoff = redact_handoff(handoff)
    return seal_handoff(handoff)


# ---------------------------------------------------------------------------
# Persistence — .sparkforge_aws/delegation/handoffs/
# ---------------------------------------------------------------------------

def _handoffs_root(root: Path) -> Path:
    return Path(root) / _STATE_DIR / HANDOFFS_DIR


def persist_handoff(handoff: EvidenceHandoff, root: Path) -> Path:
    """Write the sealed envelope to the state dir; returns the path.

    The file name is content-addressed (``<correlation>-<capability>.json``
    would collide across runs of the same capability, so the integrity hash
    goes in the name — a replayed delegation is detectable instead of
    silently overwriting).
    """
    out_dir = _handoffs_root(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{handoff.correlation_id}-{handoff.capability}-{handoff.integrity[:12]}.json"
    path = out_dir / name
    path.write_text(
        json.dumps(to_dict(handoff), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load_handoffs(root: Path) -> list[dict[str, Any]]:
    """Read persisted handoffs — bounded, schema-checked, never executed."""
    out_dir = _handoffs_root(root)
    if not out_dir.is_dir():
        return []
    handoffs: list[dict[str, Any]] = []
    for path in sorted(out_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            handoffs.append({"path": path.name, "error": "unreadable or not JSON"})
            continue
        handoffs.append({"path": path.name, "handoff": doc})
    return handoffs
