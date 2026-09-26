"""Bounded, offline DQDL syntax validation."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact

EXTRACTOR_ID = "dqdl_validator@0.1.0"
EMITTED_KINDS = frozenset({"dq.dqdl", "dq.dqdl.unresolved"})

_KNOWN_RULES = frozenset(
    {
        "ColumnDataType",
        "ColumnLength",
        "ColumnValues",
        "Completeness",
        "CustomSql",
        "DataFreshness",
        "DatasetMatch",
        "DetectAnomalies",
        "Entropy",
        "IsComplete",
        "IsPrimaryKey",
        "IsUnique",
        "Mean",
        "ReferentialIntegrity",
        "RowCount",
        "SchemaMatch",
        "StandardDeviation",
        "Sum",
        "Uniqueness",
    }
)
_HEADER = re.compile(r"^\s*Rules\s*=\s*\[", re.IGNORECASE)
_RULE_NAME = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\b")


def _subject(subject: dict[str, Any] | None, path: str) -> dict[str, Any]:
    return subject or {"type": "source_location", "file": path, "line": 0, "col": 0, "symbol": ""}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_rules(body: str) -> list[str]:
    entries: list[str] = []
    start = 0
    depth = 0
    quote = False
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
        elif char in "[({":
            depth += 1
        elif char in "]) }".replace(" ", ""):
            depth -= 1
            if depth < 0:
                raise ValueError("closing delimiter without opening delimiter")
        elif char == "," and depth == 0:
            item = body[start:index].strip()
            if item:
                entries.append(item)
            start = index + 1
    if quote or depth != 0:
        raise ValueError("unclosed string or delimiter")
    item = body[start:].strip()
    if item:
        entries.append(item)
    return entries


def _validate(text: str) -> tuple[list[str], str | None]:
    if not text.strip():
        return [], "empty_dqdl"
    if not _HEADER.match(text):
        return [], "missing_rules_header"
    opening = text.find("[")
    closing = text.rfind("]")
    if opening < 0 or closing <= opening or text[closing + 1 :].strip():
        return [], "invalid_rules_delimiters"
    entries = _split_rules(text[opening + 1 : closing])
    if not entries:
        return [], "empty_ruleset"
    names: list[str] = []
    for entry in entries:
        match = _RULE_NAME.match(entry)
        if match is None:
            return [], "invalid_rule_expression"
        name = match.group(1)
        if name not in _KNOWN_RULES:
            return [], "unsupported_rule_type"
        names.append(name)
    return names, None


def validate_dqdl_text(
    text: str, path: str, subject: dict[str, Any] | None = None
) -> list[Fact]:
    names, reason = _validate(text)
    provenance = {
        "extractor": EXTRACTOR_ID,
        "artifact": path,
        "artifact_sha256": _digest(text),
    }
    target = _subject(subject, path)
    if reason is not None:
        return [
            Fact(
                kind="dq.dqdl.unresolved",
                subject=target,
                attrs={
                    "reason": reason,
                    "validation_status": "invalid",
                    "validation_scope": "syntax_only",
                    "dqdl_sha256": _digest(text),
                },
                provenance=provenance,
            )
        ]
    return [
        Fact(
            kind="dq.dqdl",
            subject=target,
            measures={"rule_count": len(names)},
            attrs={
                "validation_status": "valid",
                "validation_scope": "syntax_only",
                "rule_names": names,
                "dqdl_sha256": _digest(text),
            },
            provenance=provenance,
        )
    ]


def validate_dqdl_path(path: str | Path, subject: dict[str, Any] | None = None) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    return validate_dqdl_text(target.read_text(encoding="utf-8"), str(target), subject)
