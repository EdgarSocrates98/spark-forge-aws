"""Tests for Spark EventLog and Physical Plan Profilers."""

import json

from sparkforge.spark.eventlog_analyzer import SparkEventLogAnalyzer
from sparkforge.spark.plan_profiler import SparkPlanProfiler


def test_spark_eventlog_analyzer_skew_and_spill():
    analyzer = SparkEventLogAnalyzer()
    lines = [
        json.dumps(
            {
                "Event": "SparkListenerStageCompleted",
                "Stage Info": {"Stage ID": 0, "Submission Time": 100, "Completion Time": 5000},
            }
        ),
        json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Task Info": {"Duration": 100, "Failed": False},
                "Task Metrics": {"Disk Bytes Spilled": 50000000},
            }
        ),
        json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Task Info": {"Duration": 100, "Failed": False},
                "Task Metrics": {},
            }
        ),
        json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Task Info": {"Duration": 100, "Failed": False},
                "Task Metrics": {},
            }
        ),
        json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Task Info": {"Duration": 100, "Failed": False},
                "Task Metrics": {},
            }
        ),
        json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Task Info": {"Duration": 5000, "Failed": False},
                "Task Metrics": {},
            }
        ),
    ]
    metric = analyzer.analyze_event_log(lines)
    assert metric.total_stages == 1
    assert metric.total_tasks == 5
    assert metric.has_spill is True
    assert metric.has_skew is True
    assert len(metric.bottlenecks) >= 2


def test_spark_plan_profiler_cartesian():
    profiler = SparkPlanProfiler()
    plan_text = """
    == Physical Plan ==
    (3) CartesianProduct
    :- (1) Scan parquet tpch.customer
    +- (2) Scan parquet tpch.orders
    """
    report = profiler.profile_plan(plan_text)
    assert report.has_cartesian_product is True
    assert len(report.findings) > 0
    assert report.findings[0].severity == "critical"
