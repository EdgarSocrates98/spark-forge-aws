"""Extrai contratos e evolução de schemas de artefatos JSON salvos.

O extrator é deliberadamente offline: não consulta Glue Schema Registry,
Confluent, Kafka ou qualquer catálogo. A compatibilidade é uma conclusão
estrutural limitada ao schema declarado; ausência de contexto vira
``schema.unresolved`` e nunca é preenchida por inferência.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "schema_registry@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "schema.registry",
        "schema.definition",
        "schema.compatibility",
        "schema.diff",
        "schema.unresolved",
        "schema.analyzed",
    }
)


def _subject(artifact: str, line: int, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": artifact,
        "line": line,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _fact(
    kind: str,
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    *,
    attrs: dict[str, Any] | None = None,
    measures: dict[str, Any] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, line, symbol),
        attrs=attrs or {},
        measures=measures or {},
        provenance=provenance,
    )


def _unresolved(
    artifact: str, line: int, provenance: dict[str, Any], reason: str, **attrs: Any
) -> Fact:
    return _fact("schema.unresolved", artifact, line, provenance, attrs={"reason": reason, **attrs})


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return None


def _records(text: str, artifact: str) -> tuple[list[tuple[int, Any]], list[tuple[int, str]]]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        if not artifact.lower().endswith("jsonl"):
            return [], [(1, exc.msg)]
        records: list[tuple[int, Any]] = []
        invalid: list[tuple[int, str]] = []
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                records.append((line, json.loads(raw)))
            except json.JSONDecodeError as line_exc:
                invalid.append((line, line_exc.msg))
        return records, invalid
    if isinstance(value, list):
        return [(index + 1, item) for index, item in enumerate(value)], []
    return [(1, value)], []


def _definition(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    definition = value.get("definition", value.get("schema", value))
    if isinstance(definition, str):
        try:
            definition = json.loads(definition)
        except json.JSONDecodeError:
            return None
    return definition if isinstance(definition, dict) else None


def _type_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "|".join(sorted(_type_name(item) for item in value))
    if isinstance(value, dict):
        return str(value.get("type", value.get("name", "object")))
    return type(value).__name__


def _fields(definition: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    raw = definition.get("fields", definition.get("Fields", []))
    fields: dict[str, str] = {}
    required: list[str] = []
    if not isinstance(raw, list):
        return fields, required
    for field in raw:
        if not isinstance(field, dict):
            continue
        name = _text(field.get("name", field.get("Name")))
        if not name:
            continue
        fields[name] = _type_name(field.get("type", field.get("Type", "unknown")))
        nullable = fields[name].lower().find("null") >= 0
        if "default" not in field and "Default" not in field and not nullable:
            required.append(name)
    return fields, sorted(required)


def _schema_record(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    return (
        data.get("contract", data.get("schema_record", data))
        if isinstance(data.get("contract", data.get("schema_record", data)), dict)
        else None
    )


def _extract_record(data: Any, artifact: str, line: int, provenance: dict[str, Any]) -> list[Fact]:
    record = _schema_record(data)
    if record is None:
        return [_unresolved(artifact, line, provenance, "invalid_schema_record")]
    registry = record.get("registry", record.get("registry_name", {}))
    registry = registry if isinstance(registry, dict) else {"name": registry}
    schema = record.get("schema", record)
    schema = schema if isinstance(schema, dict) else {}
    definition = _definition(schema.get("definition", schema.get("schema", schema)))
    previous = record.get("previous", record.get("previous_schema"))
    previous_definition = _definition(previous)
    name = _text(schema.get("name", schema.get("subject", record.get("subject")))) or ""
    provider = (_text(registry.get("provider", record.get("provider"))) or "generic").lower()
    format_name = (
        _text(schema.get("format", schema.get("data_format", record.get("format")))) or "unknown"
    ).upper()
    compatibility = (
        _text(
            record.get("compatibility", registry.get("compatibility", schema.get("compatibility")))
        )
        or ""
    ).upper()
    auto_register = _bool(record.get("auto_register", schema.get("auto_register")))
    version = record.get("version", schema.get("version"))
    attrs = {
        "registry": _text(registry.get("name")) or "",
        "provider": provider,
        "subject": name,
        "format": format_name,
    }
    if compatibility:
        attrs["compatibility"] = compatibility
    if auto_register is not None:
        attrs["auto_register"] = auto_register
    if isinstance(version, int) and not isinstance(version, bool):
        attrs["version"] = version
    facts = [_fact("schema.registry", artifact, line, provenance, attrs=attrs, symbol=name)]
    if definition is None:
        facts.append(_unresolved(artifact, line, provenance, "missing_definition", subject=name))
        facts.append(
            _fact(
                "schema.analyzed",
                artifact,
                line,
                provenance,
                attrs={"provider": provider, "subject": name},
            )
        )
        return facts
    fields, required = _fields(definition)
    facts.append(
        _fact(
            "schema.definition",
            artifact,
            line,
            provenance,
            attrs={
                "subject": name,
                "type": _type_name(definition.get("type", "record")),
                "fields": fields,
                "field_names": sorted(fields),
                "required_fields": required,
            },
            measures={"field_count": len(fields)},
            symbol=name,
        )
    )
    if compatibility:
        facts.append(
            _fact(
                "schema.compatibility",
                artifact,
                line,
                provenance,
                attrs={"subject": name, "mode": compatibility},
            )
        )
    else:
        facts.append(
            _unresolved(artifact, line, provenance, "compatibility_not_declared", subject=name)
        )
    if previous_definition is not None:
        old_fields, old_required = _fields(previous_definition)
        added = sorted(set(fields) - set(old_fields))
        removed = sorted(set(old_fields) - set(fields))
        type_changes = sorted(
            name for name in set(fields) & set(old_fields) if fields[name] != old_fields[name]
        )
        required_changes = sorted(set(required) - set(old_required))
        backward_breaking = bool(
            set(removed) & set(old_required) or type_changes or set(required_changes) - set()
        )
        forward_breaking = bool(set(added) & set(required) or type_changes)
        mode = compatibility or "UNKNOWN"
        compatible = not (("BACKWARD" in mode or mode == "FULL") and backward_breaking) and not (
            ("FORWARD" in mode or mode == "FULL") and forward_breaking
        )
        facts.append(
            _fact(
                "schema.diff",
                artifact,
                line,
                provenance,
                attrs={
                    "subject": name,
                    "compatibility": mode,
                    "added": added,
                    "removed": removed,
                    "type_changes": type_changes,
                    "required_changes": required_changes,
                    "backward_breaking": backward_breaking,
                    "forward_breaking": forward_breaking,
                    "compatible": compatible,
                },
                measures={
                    "changed_field_count": len(
                        set(removed) | set(type_changes) | set(required_changes) | set(added)
                    )
                },
                symbol=name,
            )
        )
    elif "compatibility" in record or "compatibility" in schema:
        facts.append(
            _unresolved(artifact, line, provenance, "previous_schema_missing", subject=name)
        )
    facts.append(
        _fact(
            "schema.analyzed",
            artifact,
            line,
            provenance,
            attrs={"provider": provider, "subject": name, "format": format_name},
        )
    )
    return facts


def _extract_text(text: str, artifact: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    records, invalid = _records(text, artifact)
    facts: list[Fact] = [
        _unresolved(artifact, line, provenance, "invalid_json") for line, _ in invalid
    ]
    for line, record in records:
        facts.extend(_extract_record(record, artifact, line, provenance))
    if not facts:
        facts.append(_unresolved(artifact, 1, provenance, "empty_artifact"))
    return sort_facts(facts)


def extract_schema_registry_path(
    path: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    target = Path(path)
    rel = str(target.relative_to(repo_root)) if repo_root else str(target)
    return _extract_text(target.read_text(encoding="utf-8"), rel.replace("\\", "/"))


def extract_schema_registry_tree(
    root: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    base = Path(root)
    facts: list[Fact] = []
    for pattern in ("*.json", "*.jsonl"):
        for target in iter_source_files(base, pattern):
            facts.extend(extract_schema_registry_path(target, repo_root=repo_root))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_schema_registry_path",
    "extract_schema_registry_tree",
]
