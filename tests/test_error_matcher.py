"""Tests for Deterministic Error Matcher and Reliability RCA."""
import pytest
from sparkforge.errors.matcher import DeterministicErrorMatcher
from sparkforge.reliability.rca import ReliabilityAnalyzer


def test_error_matcher_oom():
    matcher = DeterministicErrorMatcher()
    log = "ERROR YarnClusterScheduler: Container killed by YARN for exceeding memory limits. 5.5 GB of 5.0 GB physical memory used."
    matches = matcher.match_log(log)
    assert len(matches) > 0
    assert matches[0].error_id == "ERR-GLUE-001"
    assert matches[0].service == "glue"
    assert matches[0].confidence > 0.90


def test_reliability_rca():
    analyzer = ReliabilityAnalyzer()
    events = [
        {"timestamp": "2026-08-20T10:00:00Z", "source": "cloudwatch", "event": "Task failure", "resource": "glue_job_1", "severity": "info"},
        {"timestamp": "2026-08-20T10:05:00Z", "source": "spark_eventlog", "event": "Container killed for exceeding memory limits (OOM)", "resource": "executor-2", "severity": "critical"},
    ]
    report = analyzer.analyze_incident("INC-001", events)
    assert "Out of Memory" in report.primary_root_cause
    assert report.confidence >= 0.90
    assert len(report.immediate_mitigations) > 0
