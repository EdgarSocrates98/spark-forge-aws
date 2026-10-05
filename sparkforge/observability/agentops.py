"""Local-first AgentOps inspection, comparison and baseline regression checks."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_trace(db_path: Path | str, run_id: str) -> dict[str, Any] | None:
    path = Path(db_path)
    if not path.exists():
        return None
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        trace = conn.execute("SELECT * FROM traces WHERE run_id = ?", (run_id,)).fetchone()
        if trace is None:
            return None
        result = dict(trace)
        result["spans"] = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM spans WHERE run_id = ? ORDER BY start_time", (run_id,)
            )
        ]
        return result


@dataclass(frozen=True, slots=True)
class WasteAttribution:
    pattern: str
    classification: str
    evidence: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "classification": self.classification,
            "evidence": list(self.evidence),
            "description": self.description,
        }


def _waste(spans: list[dict[str, Any]]) -> list[WasteAttribution]:
    findings: list[WasteAttribution] = []
    seen: dict[str, list[str]] = {}
    for span in spans:
        if span.get("component_type") == "tool":
            key = f"{span.get('name')}:{span.get('metadata_json', '')}"
            seen.setdefault(key, []).append(str(span.get("span_id")))
    for key, ids in seen.items():
        if len(ids) > 1:
            findings.append(
                WasteAttribution(
                    "duplicate_tool_call",
                    "observed",
                    tuple(ids),
                    f"tool call repeated {len(ids)} times: {key[:100]}",
                )
            )
    for span in spans:
        metadata = span.get("metadata_json") or "{}"
        try:
            data = json.loads(metadata) if isinstance(metadata, str) else metadata
        except json.JSONDecodeError:
            data = {}
        if data.get("tier") in {"tier_5_premium", "premium"} and data.get("task_complexity") in {
            "low",
            "deterministic",
        }:
            findings.append(
                WasteAttribution(
                    "premium_model_on_simple_task",
                    "hypothesis",
                    (str(span.get("span_id")),),
                    "routing metadata suggests premium model may be unnecessary",
                )
            )
        if span.get("payload_bytes", 0) and span.get("item_count") == 0:
            findings.append(
                WasteAttribution(
                    "empty_context_payload",
                    "observed",
                    (str(span.get("span_id")),),
                    "tool emitted payload bytes with no returned items",
                )
            )
    return findings


def inspect_run(db_path: Path | str, run_id: str) -> dict[str, Any]:
    trace = _load_trace(db_path, run_id)
    if trace is None:
        return {"status": "unresolved", "run_id": run_id, "unresolved": ["run_not_found"]}
    spans = trace.get("spans", [])
    by_component: dict[str, int] = {}
    for span in spans:
        component = str(span.get("component_type", "unknown"))
        by_component[component] = by_component.get(component, 0) + 1
    evidence = sorted({ref for span in spans for ref in _metadata_list(span, "evidence_refs")})
    unresolved = sorted({ref for span in spans for ref in _metadata_list(span, "unresolved")})
    return {
        "status": "ok",
        "run": {
            key: trace.get(key)
            for key in ("run_id", "task_description", "profile", "status", "start_time", "end_time")
        },
        "spans": {"count": len(spans), "by_component": by_component},
        "context": {
            "bytes": sum(int(span.get("payload_bytes") or 0) for span in spans),
            "tokens": "tokens_unresolved",
            "duplicates": sum(
                1 for finding in _waste(spans) if finding.pattern == "duplicate_tool_call"
            ),
        },
        "models": {
            "calls": by_component.get("model", 0),
            "tokens": trace.get("total_tokens", 0),
            "cost": trace.get("total_cost_usd", 0.0),
        },
        "evidence": {"refs": evidence, "count": len(evidence), "unresolved": unresolved},
        "waste": [finding.to_dict() for finding in _waste(spans)],
    }


def _metadata_list(span: dict[str, Any], key: str) -> list[str]:
    raw = span.get("metadata_json") or "{}"
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return []
    values = data.get(key, []) if isinstance(data, dict) else []
    return [str(value) for value in values] if isinstance(values, list) else []


def compare_runs(db_path: Path | str, run_a: str, run_b: str) -> dict[str, Any]:
    left = inspect_run(db_path, run_a)
    right = inspect_run(db_path, run_b)
    if left.get("status") != "ok" or right.get("status") != "ok":
        return {
            "status": "unresolved",
            "left": left,
            "right": right,
            "unresolved": ["run_not_found"],
        }

    def delta(path: tuple[str, ...]) -> float:
        def read(payload: dict[str, Any]) -> float:
            current: Any = payload
            for part in path:
                current = current[part]
            return float(current)

        return read(right) - read(left)

    return {
        "status": "ok",
        "run_a": run_a,
        "run_b": run_b,
        "delta": {
            "context_bytes": delta(("context", "bytes")),
            "model_calls": delta(("models", "calls")),
            "tokens": "tokens_unresolved",
            "cost": delta(("models", "cost")),
            "evidence_count": delta(("evidence", "count")),
        },
        "quality": {"evidence_recall": "unresolved_without_task_contract"},
        "unresolved": ["provider_tokens_missing", "task_quality_contract_missing"],
    }


def save_baseline(db_path: Path | str, run_id: str, baseline_path: Path | str) -> dict[str, Any]:
    report = inspect_run(db_path, run_id)
    destination = Path(baseline_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {"run_id": run_id, "report": report}, ensure_ascii=True, sort_keys=True, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return {"status": "ok", "path": str(destination), "run_id": run_id, "report": report}


def compare_baseline(db_path: Path | str, run_id: str, baseline_path: Path | str) -> dict[str, Any]:
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    return compare_runs(db_path, str(baseline["run_id"]), run_id)


__all__ = ["WasteAttribution", "compare_baseline", "compare_runs", "inspect_run", "save_baseline"]
