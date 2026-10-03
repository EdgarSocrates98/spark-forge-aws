from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sparkforge.adapters._core import analyze_flink
from sparkforge.collect import managed_flink
from sparkforge.collect.base import load_manifest


class FakeManagedFlink:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def describe_application(self, **kwargs):
        self.calls.append(("describe_application", kwargs))
        return {
            "ApplicationDetail": {
                "ApplicationName": kwargs["ApplicationName"],
                "ApplicationARN": "arn:aws:kinesisanalytics:us-east-1:111111111111:application/orders",
                "ApplicationStatus": "RUNNING",
                "RuntimeEnvironment": "FLINK-1_20",
                "ApplicationVersionId": 7,
                "ServiceExecutionRole": "arn:aws:iam::111111111111:role/orders-flink",
                "CreateTimestamp": "2026-10-03T00:00:00Z",
                "LastUpdateTimestamp": "2026-10-03T01:00:00Z",
                "SecretToken": "must not be copied",
                "ApplicationConfigurationDescription": {
                    "FlinkApplicationConfigurationDescription": {
                        "CheckpointConfigurationDescription": {
                            "CheckpointingEnabled": True,
                            "CheckpointInterval": 60000,
                            "MinPauseBetweenCheckpoints": 1000,
                        },
                        "MonitoringConfigurationDescription": {
                            "LogLevel": "INFO",
                            "MetricsLevel": "APPLICATION",
                        },
                        "ParallelismConfigurationDescription": {
                            "AutoScalingEnabled": True,
                            "CurrentParallelism": 4,
                            "Parallelism": 4,
                            "ParallelismPerKPU": 1,
                        },
                    },
                    "VpcConfigurationDescriptions": [
                        {
                            "VpcConfigurationId": "vpc-config-1",
                            "VpcId": "vpc-123",
                            "SubnetIds": ["subnet-1"],
                            "SecurityGroupIds": ["sg-1"],
                        }
                    ],
                    "ApplicationCodeConfigurationDescription": {
                        "CodeContentDescription": {
                            "CodeMD5": "abc123",
                            "CodeSize": 1024,
                            "S3ApplicationCodeLocationDescription": {
                                "BucketARN": "arn:aws:s3:::orders-code",
                                "FileKey": "jobs/orders.jar",
                            },
                            "TextContent": "do not collect code",
                        },
                        "CodeContentType": "ZIPFILE",
                    },
                    "ApplicationEncryptionConfigurationDescription": {
                        "KeyType": "CUSTOMER_MANAGED_KEY",
                        "KeyId": "alias/orders",
                    },
                },
                "CloudWatchLoggingOptionDescriptions": [
                    {"CloudWatchLoggingOptionId": "log-1", "LogStreamARN": "arn:aws:logs:::log-stream"}
                ],
            }
        }


class FakeCloudWatch:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get_metric_data(self, **kwargs):
        self.calls.append(kwargs)
        timestamps = [datetime(2026, 10, 3, 1, 0, tzinfo=timezone.utc)]
        results = []
        values = {
            "cpuUtilization": [41.5],
            "heapMemoryUtilization": [62.0],
            "lastCheckpointDuration": [1200.0],
            "lastCheckpointSize": [4096.0],
        }
        for query in kwargs["MetricDataQueries"]:
            name = query["MetricStat"]["Metric"]["MetricName"]
            if name not in values:
                continue
            results.append(
                {
                    "Id": query["Id"],
                    "Label": name,
                    "Timestamps": timestamps,
                    "Values": values[name],
                    "StatusCode": "Complete",
                }
            )
        return {"MetricDataResults": results}


class FakeBoto3:
    def __init__(self, client: FakeManagedFlink, cloudwatch: FakeCloudWatch | None = None) -> None:
        self.client_value = client
        self.cloudwatch_value = cloudwatch or FakeCloudWatch()

    def client(self, name: str, **kwargs):
        assert kwargs["region_name"] == "us-east-1"
        if name == "kinesisanalyticsv2":
            return self.client_value
        assert name == "cloudwatch"
        return self.cloudwatch_value


def test_collector_normalizes_describe_response(monkeypatch, tmp_path):
    fake_client = FakeManagedFlink()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(fake_client))

    entry = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-03T02:00:00Z",
    )
    payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))

    assert entry.kind == "managed_flink_application"
    assert payload["application"]["application_name"] == "orders"
    assert payload["application"]["runtime_version"] == "FLINK-1_20"
    assert payload["configuration"]["checkpoint_interval_ms"] == 60000
    assert payload["configuration"]["current_parallelism"] == 4
    assert payload["configuration"]["vpc_configuration_count"] == 1
    assert payload["configuration"]["cloudwatch_logging_option_count"] == 1
    assert payload["collection"]["read_only"] is True
    assert payload["collection"]["include_additional_details"] is False
    assert "managed_flink_metrics_not_observed" in payload["unresolved"]
    assert "managed_flink_connectors_not_observed" in payload["unresolved"]
    assert "SecretToken" not in json.dumps(payload)
    assert "TextContent" not in json.dumps(payload)
    assert fake_client.calls == [
        ("describe_application", {"ApplicationName": "orders", "IncludeAdditionalDetails": False})
    ]


def test_collector_cache_is_offline_and_manifested(monkeypatch, tmp_path):
    fake_client = FakeManagedFlink()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(fake_client))
    first = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-03T02:00:00Z",
    )

    def boom():
        raise AssertionError("cache hit não pode tocar AWS")

    monkeypatch.setattr(managed_flink, "require_boto3", boom)
    second = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-04T02:00:00Z",
    )
    assert second == first
    manifest = load_manifest(tmp_path)
    assert manifest[0]["kind"] == "managed_flink_application"
    assert manifest[0]["collect_command"].startswith("sparkforge collect managed-flink")


def test_managed_flink_temporal_metrics_are_collected_and_normalized(monkeypatch, tmp_path):
    fake_client = FakeManagedFlink()
    cloudwatch = FakeCloudWatch()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(fake_client, cloudwatch))

    entry = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-03T02:00:00Z",
        metrics_start="2026-10-03T00:00:00Z",
        metrics_end="2026-10-03T02:00:00Z",
        metrics_period=60,
    )
    payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    names = {item["name"] for item in metrics["metric_definitions"]}

    assert entry.path.endswith("__metrics_2026-10-03T00_00_00Z_2026-10-03T02_00_00Z_60.json")
    assert metrics["namespace"] == "AWS/KinesisAnalytics"
    assert metrics["start"] == "2026-10-03T00:00:00Z"
    assert metrics["end"] == "2026-10-03T02:00:00Z"
    assert metrics["period_seconds"] == 60
    assert names == {
        "cpuUtilization",
        "heapMemoryUtilization",
        "lastCheckpointDuration",
        "lastCheckpointSize",
        "numberOfFailedCheckpoints",
    }
    assert all(
        definition["dimensions"] == [{"Name": "Application", "Value": "orders"}]
        for definition in metrics["metric_definitions"]
    )
    assert len(cloudwatch.calls) == 1
    request = cloudwatch.calls[0]
    assert len(request["MetricDataQueries"]) == 5
    assert request["ScanBy"] == "TimestampAscending"
    assert request["StartTime"].isoformat() == "2026-10-03T00:00:00+00:00"
    assert request["EndTime"].isoformat() == "2026-10-03T02:00:00+00:00"
    assert metrics["metrics_missing"] == ["numberOfFailedCheckpoints"]
    assert metrics["metrics_returned"] == 4
    assert metrics["observations"]
    assert all(observation["observed_at"] == "2026-10-03T01:00:00+00:00" for observation in metrics["observations"])
    assert all(observation["value"] != 0 for observation in metrics["observations"])
    assert "managed_flink_metric_missing:numberOfFailedCheckpoints" in payload["unresolved"]


def test_cli_and_mcp_managed_flink_collection_match(monkeypatch, tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    first_client = FakeManagedFlink()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(first_client))
    mcp = call_tool(
        "sparkforge_collect_managed_flink",
        {
            "repo": str(tmp_path / "mcp"),
            "application_name": "orders",
            "region_name": "us-east-1",
            "now": "2026-10-03T02:00:00Z",
        },
    )
    assert capsys.readouterr().err == ""

    second_client = FakeManagedFlink()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(second_client))
    code = main(
        [
            "collect",
            "managed-flink",
            "--repo",
            str(tmp_path / "cli"),
            "--application-name",
            "orders",
            "--region",
            "us-east-1",
            "--now",
            "2026-10-03T02:00:00Z",
        ]
    )
    cli = json.loads(capsys.readouterr().out)
    assert code == 0
    for payload in (mcp, cli):
        assert payload["kind"] == "managed_flink_application"
        assert payload["cache_hit"] is False
        payload.pop("path")
        payload.pop("journal", None)
        payload.pop("journal_reason", None)
    assert cli == mcp


def test_collected_artifact_feeds_managed_flink_analyzer(monkeypatch, tmp_path):
    fake_client = FakeManagedFlink()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(fake_client))
    entry = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-03T02:00:00Z",
    )

    result = analyze_flink(str(tmp_path / entry.path), artifact="managed_flink", limit=100)
    kinds = {item["kind"] for item in result["items"]}
    assert {"managed_flink.application", "managed_flink.config", "managed_flink.unresolved"} <= kinds
    assert "flink.application" not in kinds
    application = next(item for item in result["items"] if item["kind"] == "managed_flink.application")
    assert application["attrs"]["application_version_id"] == 7
    assert any(
        item["attrs"].get("reason") == "managed_flink_connectors_not_observed"
        for item in result["items"]
        if item["kind"] == "managed_flink.unresolved"
    )


def test_managed_flink_temporal_metrics_feed_analyzer(monkeypatch, tmp_path):
    fake_client = FakeManagedFlink()
    cloudwatch = FakeCloudWatch()
    monkeypatch.setattr(managed_flink, "require_boto3", lambda: FakeBoto3(fake_client, cloudwatch))
    entry = managed_flink.collect_managed_flink(
        tmp_path,
        application_name="orders",
        region_name="us-east-1",
        now="2026-10-03T02:00:00Z",
        metrics_start="2026-10-03T00:00:00Z",
        metrics_end="2026-10-03T02:00:00Z",
        metrics_period=60,
    )

    result = analyze_flink(str(tmp_path / entry.path), artifact="managed_flink", limit=100)
    metrics = [item for item in result["items"] if item["kind"] == "managed_flink.metric"]

    assert {item["attrs"]["name"] for item in metrics} == {
        "cpuUtilization",
        "heapMemoryUtilization",
        "lastCheckpointDuration",
        "lastCheckpointSize",
    }
    cpu = next(item for item in metrics if item["attrs"]["name"] == "cpuUtilization")
    assert cpu["measures"]["value"] == 41.5
    assert cpu["attrs"]["unit"] == "Percent"
    assert cpu["attrs"]["stat"] == "Average"
    assert cpu["attrs"]["observed_at"] == "2026-10-03T01:00:00+00:00"
    assert any(
        item["attrs"].get("reason") == "managed_flink_metric_missing:numberOfFailedCheckpoints"
        for item in result["items"]
        if item["kind"] == "managed_flink.unresolved"
    )
    assert all(item["kind"] != "flink.application" for item in result["items"])


def test_managed_flink_collection_docs_state_read_only_limits():
    root = Path(__file__).parents[1]
    documents = [
        (root / "knowledge/flink-streaming.md").read_text(encoding="utf-8"),
        (root / "docs/streaming/prompt-coverage.md").read_text(encoding="utf-8"),
        (root / "docs/guia/03-cli.md").read_text(encoding="utf-8"),
        (root / "docs/guia/04-mcp.md").read_text(encoding="utf-8"),
    ]
    for document in documents:
        assert "managed-flink" in document or "Managed Flink" in document
        assert "read-only" in document or "somente leitura" in document
        assert "metrics" in document.lower() or "métricas" in document.lower()
