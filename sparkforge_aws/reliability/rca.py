"""Data Platform Reliability Engineering and Root Cause Analysis (RCA) Engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TimelineEvent:
    timestamp: str
    source: str  # cloudwatch, cloudtrail, spark_eventlog, dlq, glue
    event: str
    resource: str
    severity: str  # critical, error, warning, info
    correlation_id: str | None = None


@dataclass
class RCAReport:
    incident_id: str
    primary_root_cause: str
    confidence: float
    contributing_factors: list[str] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    immediate_mitigations: list[str] = field(default_factory=list)
    preventative_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReliabilityAnalyzer:
    """Correlates logs, metrics, and event traces to produce grounded RCA reports."""

    def analyze_incident(
        self,
        incident_id: str,
        events: list[dict[str, Any]],
    ) -> RCAReport:
        timeline_objs: list[TimelineEvent] = []
        for e in events:
            timeline_objs.append(
                TimelineEvent(
                    timestamp=e.get("timestamp", ""),
                    source=e.get("source", "unknown"),
                    event=e.get("event", ""),
                    resource=e.get("resource", ""),
                    severity=e.get("severity", "info"),
                    correlation_id=e.get("correlation_id"),
                )
            )

        # Sort timeline
        timeline_objs.sort(key=lambda x: x.timestamp)

        # Find primary trigger
        critical_events = [ev for ev in timeline_objs if ev.severity in ("critical", "error")]
        primary = "Unknown root cause (insufficient critical log events)."
        factors = []
        mitigations = []
        preventatives = []

        if critical_events:
            first_err = critical_events[0]
            if "oom" in first_err.event.lower() or "memory" in first_err.event.lower():
                primary = (
                    f"Out of Memory (OOM) on resource {first_err.resource} "
                    f"caused by memory partition "
                    f"skew."
                )
                mitigations.append("Increase worker memory or scale DPU temporarily.")
                preventatives.append("Implement key salting and broadcast join thresholds.")
            elif (
                "throttl" in first_err.event.lower()
                or "provisionedthroughput" in first_err.event.lower()
            ):
                primary = f"Downstream database throttling on {first_err.resource}."
                mitigations.append("Enable exponential retry backoff and rate-limiting.")
                preventatives.append("Switch table to On-Demand billing or scale provisioned WCU.")
            else:
                primary = f"Failure trigger: {first_err.event} on {first_err.resource}"
                mitigations.append(
                    "Inspect component logs and restart failed step with checkpoint."
                )

        return RCAReport(
            incident_id=incident_id,
            primary_root_cause=primary,
            confidence=0.95 if critical_events else 0.50,
            contributing_factors=factors,
            timeline=timeline_objs,
            immediate_mitigations=mitigations,
            preventative_actions=preventatives,
        )
