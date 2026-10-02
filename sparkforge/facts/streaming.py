"""Extrator offline de ``StreamingQueryProgress`` em JSON/JSONL.

O formato aceito acompanha o dicionário público retornado por
``StreamingQuery.lastProgress``/``recentProgress``. O módulo não abre
checkpoint interno, não chama Spark e não interpreta offsets como capacidade:
quando um campo ou uma série não pode ser lida, emite ``unresolved``.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_progress@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "streaming.progress.batch",
        "streaming.progress.source",
        "streaming.progress.sink",
        "streaming.progress.event_time",
        "streaming.progress.state_operator",
        "streaming.progress.series",
        "streaming.progress.unresolved",
        "streaming.progress.analyzed",
    }
)

_NUMBER = int | float
_SAFE_KEY = re.compile(r"[^a-zA-Z0-9_]+")


def _number(value: Any) -> _NUMBER | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _safe_key(value: str) -> str:
    return _SAFE_KEY.sub("_", value).strip("_") or "unknown"


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
    measures: dict[str, Any] | None = None,
    attrs: dict[str, Any] | None = None,
    symbol: str = "",
) -> Fact:
    return Fact(
        kind=kind,
        subject=_subject(artifact, line, symbol),
        measures=measures or {},
        attrs=attrs or {},
        provenance=provenance,
    )


def _unresolved(
    artifact: str,
    line: int,
    provenance: dict[str, Any],
    reason: str,
    **attrs: Any,
) -> Fact:
    return _fact(
        "streaming.progress.unresolved",
        artifact,
        line,
        provenance,
        attrs={"reason": reason, **attrs},
    )


def _numeric_measure(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = _number(record.get(key))
    return {key: value} if value is not None else {}


def _parse_records(text: str, suffix: str) -> tuple[list[tuple[int, Any]], list[tuple[int, str]]]:
    """Return ``(records, invalid_lines)`` while retaining observed positions."""
    records: list[tuple[int, Any]] = []
    invalid: list[tuple[int, str]] = []
    if suffix.lower().endswith("jsonl") or "\n" in text.strip():
        for line_no, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                records.append((line_no, json.loads(raw)))
            except json.JSONDecodeError as exc:
                invalid.append((line_no, f"{exc.msg}"))
        return records, invalid

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [(1, exc.msg)]
    if isinstance(decoded, list):
        return [(index + 1, item) for index, item in enumerate(decoded)], []
    return [(1, decoded)], []


def _progress_facts(
    records: list[tuple[int, Any]], artifact: str, provenance: dict[str, Any]
) -> list[Fact]:
    facts: list[Fact] = []
    valid: list[tuple[int, dict[str, Any], int]] = []
    for observed_index, (line, value) in enumerate(records):
        if not isinstance(value, dict):
            facts.append(
                _unresolved(
                    artifact,
                    line,
                    provenance,
                    "invalid_progress_record",
                    observed_index=observed_index,
                    value_type=type(value).__name__,
                )
            )
            continue
        batch_id = _number(value.get("batchId"))
        timestamp = value.get("timestamp")
        if batch_id is None or not isinstance(timestamp, str):
            facts.append(
                _unresolved(
                    artifact,
                    line,
                    provenance,
                    "missing_required_field",
                    observed_index=observed_index,
                    required=["batchId", "timestamp"],
                )
            )
            continue
        batch_id = int(batch_id)
        valid.append((line, value, observed_index))
        measures: dict[str, Any] = {"batch_id": batch_id, "observed_index": observed_index}
        for key, output in (
            ("batchDuration", "batch_duration_ms"),
            ("numInputRows", "num_input_rows"),
            ("inputRowsPerSecond", "input_rows_per_second"),
            ("processedRowsPerSecond", "processed_rows_per_second"),
        ):
            number = _number(value.get(key))
            if number is not None:
                measures[output] = number
        duration = value.get("durationMs")
        if isinstance(duration, dict):
            for key, number in duration.items():
                number = _number(number)
                if number is not None:
                    measures[f"duration_ms_{_safe_key(str(key))}"] = number
        facts.append(
            _fact(
                "streaming.progress.batch",
                artifact,
                line,
                provenance,
                measures=measures,
                attrs={
                    "timestamp": timestamp,
                    "query_id": value.get("id"),
                    "run_id": value.get("runId"),
                    "query_name": value.get("name"),
                },
            )
        )

        event_time = value.get("eventTime")
        if isinstance(event_time, dict):
            facts.append(
                _fact(
                    "streaming.progress.event_time",
                    artifact,
                    line,
                    provenance,
                    measures={"batch_id": batch_id, "observed_index": observed_index},
                    attrs={"values": event_time},
                )
            )

        sources = value.get("sources")
        if isinstance(sources, list):
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict):
                    facts.append(
                        _unresolved(
                            artifact,
                            line,
                            provenance,
                            "invalid_source_record",
                            batch_id=batch_id,
                            source_index=source_index,
                        )
                    )
                    continue
                source_measures = {"batch_id": batch_id, "observed_index": observed_index}
                for key, output in (
                    ("numInputRows", "num_input_rows"),
                    ("inputRowsPerSecond", "input_rows_per_second"),
                    ("processedRowsPerSecond", "processed_rows_per_second"),
                ):
                    number = _number(source.get(key))
                    if number is not None:
                        source_measures[output] = number
                facts.append(
                    _fact(
                        "streaming.progress.source",
                        artifact,
                        line,
                        provenance,
                        measures=source_measures,
                        attrs={
                            "source_index": source_index,
                            "description": source.get("description"),
                            "start_offset": source.get("startOffset"),
                            "end_offset": source.get("endOffset"),
                            "latest_offset": source.get("latestOffset"),
                        },
                    )
                )

        sink = value.get("sink")
        if isinstance(sink, dict):
            sink_measures = {"batch_id": batch_id, "observed_index": observed_index}
            output_rows = _number(sink.get("numOutputRows"))
            if output_rows is not None:
                sink_measures["num_output_rows"] = output_rows
            facts.append(
                _fact(
                    "streaming.progress.sink",
                    artifact,
                    line,
                    provenance,
                    measures=sink_measures,
                    attrs={"description": sink.get("description")},
                )
            )

        state_operators = value.get("stateOperators")
        if isinstance(state_operators, list):
            for state_index, state in enumerate(state_operators):
                if not isinstance(state, dict):
                    facts.append(
                        _unresolved(
                            artifact,
                            line,
                            provenance,
                            "invalid_state_operator_record",
                            batch_id=batch_id,
                            state_index=state_index,
                        )
                    )
                    continue
                state_measures = {"batch_id": batch_id, "observed_index": observed_index}
                for key, output in (
                    ("numRowsTotal", "num_rows_total"),
                    ("numRowsUpdated", "num_rows_updated"),
                    ("memoryUsedBytes", "memory_used_bytes"),
                    ("numDroppedDuplicateRows", "num_dropped_duplicate_rows"),
                    ("numRowsRemoved", "num_rows_removed"),
                ):
                    number = _number(state.get(key))
                    if number is not None:
                        state_measures[output] = number
                facts.append(
                    _fact(
                        "streaming.progress.state_operator",
                        artifact,
                        line,
                        provenance,
                        measures=state_measures,
                        attrs={
                            "state_index": state_index,
                            "operator_name": state.get("operatorName"),
                            "custom_metrics": state.get("customMetrics", {}),
                        },
                    )
                )

    if len(valid) < 2:
        facts.append(
            _unresolved(
                artifact,
                valid[0][0] if valid else 1,
                provenance,
                "insufficient_series",
                required_observations=2,
                observed_observations=len(valid),
                required_measurements=["inputRowsPerSecond", "processedRowsPerSecond"],
            )
        )
    else:
        rate_rows = [
            (value.get("inputRowsPerSecond"), value.get("processedRowsPerSecond"))
            for _, value, _ in valid
        ]
        if all(_number(left) is not None and _number(right) is not None for left, right in rate_rows):
            inputs = [float(left) for left, _ in rate_rows]
            processed = [float(right) for _, right in rate_rows]
            state_totals: list[float] = []
            for _, value, _ in valid:
                operators = value.get("stateOperators")
                total = sum(
                    float(_number(item.get("numRowsTotal")) or 0)
                    for item in operators
                    if isinstance(item, dict) and _number(item.get("numRowsTotal")) is not None
                ) if isinstance(operators, list) else None
                if total is None:
                    state_totals = []
                    break
                state_totals.append(total)
            measures = {
                "observation_count": len(valid),
                "first_batch_id": valid[0][1]["batchId"],
                "last_batch_id": valid[-1][1]["batchId"],
                "input_rows_per_second_first": inputs[0],
                "input_rows_per_second_last": inputs[-1],
                "processed_rows_per_second_first": processed[0],
                "processed_rows_per_second_last": processed[-1],
            }
            series_attrs = {
                "first_observed_index": valid[0][2],
                "last_observed_index": valid[-1][2],
                "all_processed_below_input": all(right < left for left, right in rate_rows),
            }
            if state_totals:
                measures.update(
                    {
                        "state_rows_total_first": state_totals[0],
                        "state_rows_total_last": state_totals[-1],
                    }
                )
                series_attrs["state_growth_observed"] = state_totals[-1] > state_totals[0]
            facts.append(
                _fact(
                    "streaming.progress.series",
                    artifact,
                    valid[0][0],
                    provenance,
                    measures=measures,
                    attrs=series_attrs,
                )
            )
        else:
            facts.append(
                _unresolved(
                    artifact,
                    valid[0][0],
                    provenance,
                    "missing_series_measurement",
                    required_observations=2,
                    observed_observations=len(valid),
                    required_measurements=["inputRowsPerSecond", "processedRowsPerSecond"],
                )
            )
    return facts


def extract_streaming_progress_text(text: str, artifact: str, suffix: str = ".jsonl") -> list[Fact]:
    """Extract progress facts from text already held by the caller."""
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": artifact, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    records, invalid = _parse_records(text, suffix)
    facts = [
        _unresolved(artifact, line, provenance, "invalid_json", detail=detail)
        for line, detail in invalid
    ]
    facts.extend(_progress_facts(records, artifact, provenance))
    facts.append(
        _fact(
            "streaming.progress.analyzed",
            artifact,
            0,
            provenance,
            measures={
                "record_count": len(records),
                "unresolved_count": sum(1 for fact in facts if fact.kind.endswith(".unresolved")),
                "series_count": sum(1 for fact in facts if fact.kind == "streaming.progress.series"),
            },
            attrs={"parsed": True},
        )
    )
    unknown = {fact.kind for fact in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace streaming: {sorted(unknown)}")
    return sort_facts(facts)


def extract_streaming_progress_path(path: Path | str, repo_root: Path | str | None = None) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(target)
    return extract_streaming_progress_text(
        target.read_text(encoding="utf-8"), str(target), target.suffix
    )


def extract_streaming_progress_tree(root: Path | str, repo_root: Path | str | None = None) -> list[Fact]:
    base = Path(root)
    facts: list[Fact] = []
    for path in iter_source_files(base, "*.json*"):
        facts.extend(extract_streaming_progress_path(path, repo_root=repo_root or base))
    return sort_facts(facts)
