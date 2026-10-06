"""Extract declared streaming SLO, FinOps, security and serving facts.

The input is a saved JSON contract. Values are copied only when they are
declared and safe to persist. Secret-like keys are never copied into facts.
This extractor measures declarations; it does not calculate price, attribute
cost to a cause, or prove a security control is effective at runtime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge_aws.facts.scan import iter_source_files
from sparkforge_aws.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_ops@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.slo",
        "streaming.finops",
        "streaming.security",
        "streaming.serving",
        "streaming.lakehouse",
        "streaming_ops.unresolved",
        "streaming_ops.analyzed",
    }
)

_SENSITIVE_TOKENS = (
    "secret",
    "password",
    "token",
    "credential",
    "private_key",
    "access_key",
)


def _subject(artifact: str, symbol: str = "") -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": artifact,
        "line": 1,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(text: str, artifact: str) -> dict[str, Any]:
    return {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }


def _fact(
    kind: str,
    artifact: str,
    provenance: dict[str, Any],
    *,
    attrs: dict[str, Any] | None = None,
    measures: dict[str, float] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, symbol),
        attrs=attrs or {},
        measures=measures or {},
        provenance=provenance,
    )


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _number(value: Any) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _sensitive_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(token in normalized for token in _SENSITIVE_TOKENS)


def _sensitive_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key == "secrets_manager" and isinstance(child, (str, bool)):
                continue
            if _sensitive_key(key):
                paths.append(path)
            else:
                paths.extend(_sensitive_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_sensitive_paths(child, f"{prefix}[{index}]"))
    return paths


def _safe_attrs(item: dict[str, Any], names: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    attrs: dict[str, Any] = {}
    unresolved: list[str] = []
    for name in names:
        value = item.get(name)
        if value is None:
            continue
        if _sensitive_key(name) and name != "secrets_manager":
            unresolved.append(f"sensitive_field_redacted:{name}")
            continue
        if isinstance(value, (str, bool, int, float)):
            attrs[name] = value
        elif isinstance(value, list) and all(isinstance(entry, str) for entry in value):
            attrs[name] = sorted(value)
        else:
            unresolved.append(f"field_not_scalar:{name}")
    return attrs, unresolved


def _items(data: Any, section: str) -> tuple[list[dict[str, Any]], list[str]]:
    if section not in data:
        return [], [f"{section}_declaration_missing"]
    value = data[section]
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return [], [f"{section}_must_be_list"]
    invalid = [f"{section}_item_invalid" for item in value if not isinstance(item, dict)]
    return [item for item in value if isinstance(item, dict)], invalid


def _slo(
    data: dict[str, Any], artifact: str, provenance: dict[str, Any]
) -> tuple[list[Fact], list[str]]:
    items, unresolved = _items(data, "slo")
    facts: list[Fact] = []
    for item in items:
        name = _text(item.get("name")) or "unresolved"
        attrs, safe_unresolved = _safe_attrs(
            item,
            (
                "name",
                "metric",
                "operator",
                "unit",
                "window",
                "source",
                "transport_key",
                "sink_name",
                "statistic",
            ),
        )
        unresolved.extend(safe_unresolved)
        statistic = _text(item.get("statistic"))
        if statistic is not None and statistic.lower() not in {"all", "p95"}:
            unresolved.append(f"slo_statistic_unsupported:{name}")
            continue
        if statistic is not None:
            attrs["statistic"] = statistic.lower()
        target = _number(item.get("target"))
        if target is None:
            unresolved.append(f"slo_target_missing:{name}")
        else:
            facts.append(
                _fact(
                    "streaming.slo",
                    artifact,
                    provenance,
                    attrs=attrs,
                    measures={"target": target},
                    symbol=name,
                )
            )
    return facts, unresolved


def _finops(
    data: dict[str, Any], artifact: str, provenance: dict[str, Any]
) -> tuple[list[Fact], list[str]]:
    items, unresolved = _items(data, "finops")
    facts: list[Fact] = []
    required = ("metric", "unit", "period", "region", "tier", "source")
    for item in items:
        name = _text(item.get("metric")) or "unresolved"
        attrs, safe_unresolved = _safe_attrs(item, required)
        unresolved.extend(safe_unresolved)
        value = _number(item.get("value"))
        if value is None:
            unresolved.append(f"finops_measurement_missing:{name}")
        missing = [
            field for field in ("unit", "period", "region", "source") if not _text(item.get(field))
        ]
        unresolved.extend(f"finops_context_missing:{name}:{field}" for field in missing)
        if value is not None and not missing:
            facts.append(
                _fact(
                    "streaming.finops",
                    artifact,
                    provenance,
                    attrs=attrs,
                    measures={"value": value},
                    symbol=name,
                )
            )
    return facts, unresolved


def _security(
    data: dict[str, Any], artifact: str, provenance: dict[str, Any]
) -> tuple[list[Fact], list[str]]:
    items, unresolved = _items(data, "security")
    facts: list[Fact] = []
    controls = (
        "transport",
        "auth",
        "tls",
        "kms",
        "vpc",
        "secrets_manager",
        "cross_account",
        "resource_policy",
    )
    for index, item in enumerate(items):
        attrs, safe_unresolved = _safe_attrs(item, controls + ("system", "source"))
        unresolved.extend(safe_unresolved)
        if not attrs:
            unresolved.append(f"security_controls_missing:{index}")
            continue
        missing = [control for control in controls if control not in item]
        unresolved.extend(f"security_control_unresolved:{index}:{control}" for control in missing)
        facts.append(
            _fact("streaming.security", artifact, provenance, attrs=attrs, symbol=str(index))
        )
    return facts, unresolved


def _serving(
    data: dict[str, Any], artifact: str, provenance: dict[str, Any]
) -> tuple[list[Fact], list[str]]:
    items, unresolved = _items(data, "serving")
    facts: list[Fact] = []
    for item in items:
        name = _text(item.get("name", item.get("system"))) or "unresolved"
        attrs, safe_unresolved = _safe_attrs(
            item, ("name", "system", "source", "mode", "schema", "consumer_count")
        )
        unresolved.extend(safe_unresolved)
        if not _text(item.get("system", item.get("name"))):
            unresolved.append(f"serving_system_missing:{name}")
        latency = _number(item.get("latency_target_ms"))
        measures = {"latency_target_ms": latency} if latency is not None else {}
        facts.append(
            _fact(
                "streaming.serving",
                artifact,
                provenance,
                attrs=attrs,
                measures=measures,
                symbol=name,
            )
        )
    return facts, unresolved


def _lakehouse(
    data: dict[str, Any], artifact: str, provenance: dict[str, Any]
) -> tuple[list[Fact], list[str]]:
    items, unresolved = _items(data, "lakehouse")
    facts: list[Fact] = []
    for item in items:
        name = _text(item.get("name", item.get("format"))) or "unresolved"
        attrs, safe_unresolved = _safe_attrs(
            item,
            ("name", "format", "mode", "change_feed", "checkpoint", "schema_evolution", "features"),
        )
        unresolved.extend(safe_unresolved)
        if not _text(item.get("format")):
            unresolved.append(f"lakehouse_format_missing:{name}")
        facts.append(_fact("streaming.lakehouse", artifact, provenance, attrs=attrs, symbol=name))
    return facts, unresolved


def _extract_text(text: str, artifact: str) -> list[Fact]:
    provenance = _provenance(text, artifact)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [
            _fact(
                "streaming_ops.unresolved",
                artifact,
                provenance,
                attrs={"reason": "invalid_json", "line": exc.lineno},
            )
        ]
    if not isinstance(data, dict):
        return [
            _fact(
                "streaming_ops.unresolved",
                artifact,
                provenance,
                attrs={"reason": "root_must_be_object"},
            )
        ]

    facts: list[Fact] = []
    reasons: list[str] = []
    for section in ("slo", "finops", "security", "serving", "lakehouse"):
        builder = {
            "slo": _slo,
            "finops": _finops,
            "security": _security,
            "serving": _serving,
            "lakehouse": _lakehouse,
        }[section]
        section_facts, section_reasons = builder(data, artifact, provenance)
        facts.extend(section_facts)
        reasons.extend(section_reasons)
    for path in _sensitive_paths(data):
        reasons.append(f"artifact_secret_redacted:{path}")
    for reason in sorted(set(reasons)):
        facts.append(
            _fact(
                "streaming_ops.unresolved",
                artifact,
                provenance,
                attrs={"reason": reason, "domain": reason.split("_", 1)[0]},
            )
        )
    facts.append(
        _fact(
            "streaming_ops.analyzed",
            artifact,
            provenance,
            attrs={
                "sections": sorted(
                    section
                    for section in ("slo", "finops", "security", "serving", "lakehouse")
                    if section in data
                )
            },
            measures={"fact_count": len(facts)},
        )
    )
    return sort_facts(facts)


def extract_streaming_ops_path(
    path: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    target = Path(path)
    rel = str(target.relative_to(repo_root)) if repo_root else str(target)
    return _extract_text(target.read_text(encoding="utf-8"), rel.replace("\\", "/"))


def extract_streaming_ops_tree(
    root: str | Path, *, repo_root: str | Path | None = None
) -> list[Fact]:
    facts: list[Fact] = []
    for path in iter_source_files(Path(root), "*.json"):
        facts.extend(extract_streaming_ops_path(path, repo_root=repo_root))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_streaming_ops_path",
    "extract_streaming_ops_tree",
]
