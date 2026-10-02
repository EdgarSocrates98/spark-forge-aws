"""Evidence-first SLO evaluation over previously extracted streaming facts.

This module is a compositor, not an extractor: it never opens an artifact or
calls a provider. It evaluates metrics directly present in
``streaming.progress.batch``, ``kafka.lag`` or ``kinesis.shard`` and refuses
when identity, units, timestamps or window coverage cannot be proven from the
supplied facts.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import re
from typing import Any, Callable

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "streaming_slo@0.1.0"

EMITTED_KINDS = frozenset({"streaming.slo.evaluation", "streaming.slo.unresolved"})

_METRIC_ALIASES = {
    "input_rows_per_second": "input_rows_per_second",
    "inputrowspersecond": "input_rows_per_second",
    "processed_rows_per_second": "processed_rows_per_second",
    "processedrowspersecond": "processed_rows_per_second",
    "batch_duration_ms": "batch_duration_ms",
    "batchdurationms": "batch_duration_ms",
    "num_input_rows": "num_input_rows",
    "numinputrows": "num_input_rows",
    "lag": "lag",
    "max_lag": "lag",
    "maxlag": "lag",
    "iterator_age_ms": "iterator_age_ms",
    "iterator_age_milliseconds": "iterator_age_ms",
    "iteratoragems": "iterator_age_ms",
    "iteratoragemilliseconds": "iterator_age_ms",
}
_METRIC_UNITS = {
    "input_rows_per_second": "rows_per_second",
    "processed_rows_per_second": "rows_per_second",
    "batch_duration_ms": "ms",
    "num_input_rows": "rows",
    "lag": "records",
    "iterator_age_ms": "ms",
}
_UNIT_ALIASES = {
    "ms": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "rows": "rows",
    "row": "rows",
    "rows_per_second": "rows_per_second",
    "rows/s": "rows_per_second",
    "row_per_second": "rows_per_second",
    "row/s": "rows_per_second",
    "records": "records",
    "record": "records",
    "count": "records",
}
_OPERATOR_ALIASES = {
    "lt": "lt",
    "<": "lt",
    "lte": "lte",
    "le": "lte",
    "<=": "lte",
    "gt": "gt",
    ">": "gt",
    "gte": "gte",
    "ge": "gte",
    ">=": "gte",
    "eq": "eq",
    "==": "eq",
}
_WINDOW_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[smhd])\s*$", re.IGNORECASE)
_SOURCE_ALIASES = {"spark_progress", "structured_streaming", "structured streaming", "spark"}
_TRANSPORT_SOURCES = {"kafka": "kafka.lag", "kinesis": "kinesis.shard"}


def _subject(symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<composition>",
        "line": 0,
        "col": 0,
        "symbol": symbol,
        "snippet": "",
    }


def _source_file(fact: Fact) -> str:
    return str((fact.subject or {}).get("file", ""))


def _provenance(facts: Sequence[Fact]) -> dict[str, Any]:
    return {
        "artifact": "<composition>",
        "artifacts": sorted({_source_file(fact) for fact in facts if _source_file(fact)}),
        "extractor": EXTRACTOR_ID,
    }


def _unresolved(
    facts: Sequence[Fact],
    reason: str,
    *,
    slo_name: str | None = None,
    query_name: str | None = None,
    **attrs: Any,
) -> Fact:
    return Fact(
        kind="streaming.slo.unresolved",
        subject=_subject(f"{query_name or '<query>'}:{slo_name or '<slo>'}"),
        attrs={
            "reason": reason,
            "slo_name": slo_name,
            "query_name": query_name,
            "causal_inference": False,
            **attrs,
        },
        provenance=_provenance(facts),
    )


def _number(value: Any) -> float | int | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _parse_window(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    match = _WINDOW_RE.fullmatch(value)
    if match is None:
        return None
    amount = float(match.group("value"))
    multiplier = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}[match.group("unit").lower()]
    return amount * multiplier


def _canonical_metric(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _METRIC_ALIASES.get(value.strip().lower())


def _canonical_unit(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _UNIT_ALIASES.get(value.strip().lower())


def _canonical_operator(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _OPERATOR_ALIASES.get(value.strip().lower())


def _passes(operator: str, observed: float, target: float) -> bool:
    comparators: dict[str, Callable[[float, float], bool]] = {
        "lt": lambda left, right: left < right,
        "lte": lambda left, right: left <= right,
        "gt": lambda left, right: left > right,
        "gte": lambda left, right: left >= right,
        "eq": lambda left, right: left == right,
    }
    return comparators[operator](observed, target)


def _select_slo(
    facts: Sequence[Fact], slo_name: str
) -> tuple[Fact | None, Fact | None]:
    declarations = [fact for fact in facts if fact.kind == "streaming.slo"]
    if slo_name:
        matches = [
            fact
            for fact in declarations
            if slo_name in {str((fact.attrs or {}).get("name", "")), str((fact.subject or {}).get("symbol", ""))}
        ]
        if len(matches) == 1:
            return matches[0], None
        if not matches:
            return None, _unresolved(facts, "slo_not_found", slo_name=slo_name)
        return None, _unresolved(facts, "ambiguous_slo", slo_name=slo_name, match_count=len(matches))
    if len(declarations) == 1:
        return declarations[0], None
    if not declarations:
        return None, _unresolved(facts, "missing_declared_slo")
    return None, _unresolved(facts, "missing_declared_slo_name", match_count=len(declarations))


def build_streaming_slo(
    facts: Sequence[Fact],
    *,
    slo_name: str = "",
    query_name: str = "",
    transport_key: str = "",
) -> list[Fact]:
    """Evaluate one declared SLO over one unambiguous observed series.

    Spark progress requires ``query_name``. Kafka and Kinesis require the
    explicitly declared ``transport_key`` and use only timestamped direct
    lag/iterator-age observations; no CloudWatch interpolation or causal
    inference is performed here.
    """
    source_facts = list({fact.id: fact for fact in facts}.values())
    slo, selection_error = _select_slo(source_facts, slo_name)
    if selection_error is not None:
        derived = [selection_error]
    else:
        assert slo is not None
        attrs = slo.attrs or {}
        declared_name = str(attrs.get("name") or (slo.subject or {}).get("symbol") or slo_name or "")
        source = str(attrs.get("source") or "").strip().lower()
        is_transport = source in _TRANSPORT_SOURCES
        declared_transport_key = transport_key or str(attrs.get("transport_key") or "").strip()
        identity = declared_transport_key if is_transport else query_name
        identity_attrs = {"transport_key": declared_transport_key} if is_transport else {"query_name": query_name}
        if not is_transport and not query_name:
            derived = [_unresolved(source_facts, "missing_declared_query_name", slo_name=declared_name)]
        elif is_transport and not declared_transport_key:
            derived = [_unresolved(source_facts, "missing_declared_transport_key", slo_name=declared_name, **identity_attrs)]
        else:
            required = ("metric", "operator", "unit", "window", "source")
            missing = next((field for field in required if not str(attrs.get(field) or "").strip()), None)
            target = _number((slo.measures or {}).get("target"))
            if missing is not None:
                derived = [_unresolved(source_facts, f"slo_{missing}_missing", slo_name=declared_name, **identity_attrs)]
            elif target is None:
                derived = [_unresolved(source_facts, "slo_target_missing", slo_name=declared_name, **identity_attrs)]
            else:
                metric = _canonical_metric(attrs.get("metric"))
                operator = _canonical_operator(attrs.get("operator"))
                unit = _canonical_unit(attrs.get("unit"))
                window_seconds = _parse_window(attrs.get("window"))
                if metric is None:
                    reason = "metric_not_observed"
                elif operator is None:
                    reason = "unsupported_operator"
                elif unit != _METRIC_UNITS[metric]:
                    reason = "unit_mismatch"
                elif window_seconds is None:
                    reason = "invalid_window"
                elif source not in _SOURCE_ALIASES and source not in _TRANSPORT_SOURCES:
                    reason = "unsupported_observation_source"
                else:
                    reason = ""
                if reason:
                    derived = [_unresolved(source_facts, reason, slo_name=declared_name, **identity_attrs)]
                else:
                    if is_transport:
                        source_kind = _TRANSPORT_SOURCES[source]
                        observations_source = [
                            fact
                            for fact in source_facts
                            if fact.kind == source_kind
                            and identity in {
                                str((fact.attrs or {}).get("group", "")),
                                str((fact.attrs or {}).get("topic", "")),
                                str((fact.attrs or {}).get("stream_name", "")),
                            }
                        ]
                    else:
                        observations_source = [
                            fact
                            for fact in source_facts
                            if fact.kind == "streaming.progress.batch"
                            and str((fact.attrs or {}).get("query_name") or "") == query_name
                        ]
                    source_files = sorted({_source_file(fact) for fact in observations_source})
                    if not observations_source:
                        reason = "transport_not_found" if is_transport else "query_not_found"
                        derived = [_unresolved(source_facts, reason, slo_name=declared_name, **identity_attrs)]
                    elif len(source_files) != 1:
                        reason = "ambiguous_transport" if is_transport else "ambiguous_query"
                        derived = [
                            _unresolved(
                                source_facts,
                                reason,
                                slo_name=declared_name,
                                match_count=len(source_files),
                                **identity_attrs,
                            )
                        ]
                    else:
                        observations: list[tuple[float, datetime, Fact]] = []
                        missing_field = ""
                        for observation in observations_source:
                            value = _number((observation.measures or {}).get(metric))
                            observed_at = (observation.attrs or {}).get("timestamp")
                            if observed_at is None:
                                observed_at = (observation.attrs or {}).get("observed_at")
                            timestamp = _parse_timestamp(observed_at)
                            if value is None:
                                missing_field = "metric"
                                break
                            if timestamp is None:
                                missing_field = "timestamp"
                                break
                            observations.append((float(value), timestamp, observation))
                        if missing_field:
                            derived = [
                                _unresolved(
                                    source_facts,
                                    f"observation_{missing_field}_missing",
                                    slo_name=declared_name,
                                    **identity_attrs,
                                )
                            ]
                        elif len(observations) < 2:
                            derived = [
                                _unresolved(
                                    source_facts,
                                    "insufficient_observations",
                                    slo_name=declared_name,
                                    required_observations=2,
                                    observed_observations=len(observations),
                                    **identity_attrs,
                                )
                            ]
                        else:
                            timestamps = [item[1] for item in observations]
                            observed_span = (max(timestamps) - min(timestamps)).total_seconds()
                            if observed_span < window_seconds:
                                derived = [
                                    _unresolved(
                                        source_facts,
                                        "window_not_covered",
                                        slo_name=declared_name,
                                        observed_span_seconds=observed_span,
                                        window_seconds=window_seconds,
                                        **identity_attrs,
                                    )
                                ]
                            else:
                                values = [item[0] for item in observations]
                                violated_count = sum(
                                    not _passes(operator, observed, float(target)) for observed in values
                                )
                                evaluation_attrs = {
                                    "name": declared_name,
                                    "metric": metric,
                                    "operator": operator,
                                    "unit": unit,
                                    "window": attrs.get("window"),
                                    "source": source,
                                    "query_name": query_name,
                                    "status": "violated" if violated_count else "met",
                                    "window_covered": True,
                                    "causal_inference": False,
                                    "source_fact_ids": sorted([slo.id, *[item[2].id for item in observations]]),
                                }
                                if is_transport:
                                    evaluation_attrs["transport_key"] = declared_transport_key
                                    evaluation_attrs["observation_source"] = _TRANSPORT_SOURCES[source]
                                evaluation_measures = {
                                    "target": target,
                                    "observed_min": min(values),
                                    "observed_max": max(values),
                                    "observation_count": len(values),
                                    "observed_span_seconds": observed_span,
                                    "window_seconds": window_seconds,
                                    "violated_count": violated_count,
                                }
                                derived = [
                                    Fact(
                                        kind="streaming.slo.evaluation",
                                        subject=_subject(f"{identity}:{declared_name}"),
                                        attrs=evaluation_attrs,
                                        measures=evaluation_measures,
                                        provenance=_provenance([slo, *[item[2] for item in observations]]),
                                    )
                                ]
    unknown = {fact.kind for fact in derived} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace streaming_slo: {sorted(unknown)}")
    return sort_facts(derived)


__all__ = ["EMITTED_KINDS", "EXTRACTOR_ID", "build_streaming_slo"]
