"""Thin, optional projection of AWS diagnostics into Obsidian Markdown.

The AWS analyzers remain authoritative.  This module only formats already
validated findings and evidence, redacts sensitive fields, and returns a
versioned note reference; it never reads or writes a vault.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import yaml

_SENSITIVE = ("secret", "token", "password", "credential", "access_key", "session_key")
_SENSITIVE_TEXT = re.compile(
    r"(?i)(\b(?:secret|token|password|credential|access[_-]?key|session[_-]?key)\s*[:=]\s*)([^\s,;]+)"
)


def _safe(value: Any, key: str = "") -> Any:
    if any(marker in key.lower() for marker in _SENSITIVE):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _safe(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(item, key) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_TEXT.sub(r"\1[REDACTED]", value)
    return value


def _lines(values: list[Any]) -> str:
    return "\n".join(f"- {_safe(value)}" for value in values) or "- None reported"


def build_obsidian_diagnostic(
    *,
    title: str,
    summary: str,
    workspace: str,
    vault_id: str,
    findings: list[Any] | None = None,
    evidence: list[Any] | None = None,
    note_path: str = "spark-diagnostics/diagnostic.md",
    runtime: str | None = None,
    services: list[str] | None = None,
    versions: dict[str, str] | None = None,
    related_runbooks: list[str] | None = None,
    confidence: str = "unknown",
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_title = str(_safe(title.strip() or "Spark diagnostic"))
    safe_summary = str(_safe(summary.strip()))
    metadata = _safe(
        {
            "type": "spark-diagnostic",
            "source": "spark-forge-aws",
            "classification": "internal",
            "confidence": confidence,
            "runtime": runtime,
            "services": services or [],
            "versions": versions or {},
            "related_runbooks": related_runbooks or [],
            "provenance": provenance or {},
        }
    )
    body = "\n".join(
        [
            "---",
            yaml.safe_dump(metadata, sort_keys=True, allow_unicode=True).rstrip(),
            "---",
            f"# {safe_title}",
            "",
            safe_summary,
            "",
            "## Findings",
            _lines(findings or []),
            "",
            "## Evidence",
            _lines(evidence or []),
        ]
    ) + "\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return {
        "schema": "theforge/ObsidianNoteRef/v1",
        "version": "v1",
        "workspace": workspace,
        "vault_id": vault_id,
        "path": note_path,
        "source": "spark-forge-aws",
        "classification": "internal",
        "content_hash": digest,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "outcome": "projected",
        "provenance": {"adapter": "spark-forge-aws", **_safe(provenance or {})},
        "content": body,
        "warnings": [],
        "unresolved": [],
    }
