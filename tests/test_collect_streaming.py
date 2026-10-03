from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import call_tool
from sparkforge.collect import streaming
from sparkforge.collect.base import CollectorUnavailable, load_manifest


class FakeS3:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return {
            "Contents": [
                {"Key": f"{kwargs['Prefix']}offsets/0", "Size": 20, "ETag": '"a"'},
                {"Key": f"{kwargs['Prefix']}commits/0", "Size": 10, "ETag": '"b"'},
            ]
        }


class FakeGlue:
    def get_job(self, **kwargs):
        return {
            "Job": {
                "Name": kwargs["Name"],
                "Command": {"Name": "gluestreaming"},
                "DefaultArguments": {"--password": "do-not-persist", "--window": "10s"},
            }
        }


class FakeKinesis:
    def describe_stream_summary(self, **kwargs):
        return {"StreamDescriptionSummary": {"StreamName": kwargs["StreamName"], "OpenShardCount": 1}}

    def list_shards(self, **kwargs):
        return {"Shards": [{"ShardId": "shardId-000000000000", "SequenceNumberRange": {}}]}


class FakeKafka:
    def describe_cluster_v2(self, **kwargs):
        return {"ClusterInfo": {"ClusterArn": kwargs["ClusterArn"], "CurrentBrokerSoftwareInfo": {}}}


class FakeDms:
    def describe_replication_tasks(self, **kwargs):
        return {"ReplicationTasks": [{"ReplicationTaskArn": kwargs["Filters"][0]["Values"][0]}]}


class FakeCloudWatch:
    def __init__(self):
        self.calls: list[dict] = []

    def get_metric_data(self, **kwargs):
        self.calls.append(kwargs)
        results = []
        for query in kwargs["MetricDataQueries"]:
            metric = query["MetricStat"]["Metric"]["MetricName"]
            results.append(
                {
                    "Id": query["Id"],
                    "Label": query["Label"],
                    "Timestamps": ["2026-10-02T00:00:00+00:00", "2026-10-02T00:01:00+00:00"],
                    "Values": [100.0 if metric == "IncomingBytes" else 2.0, 120.0 if metric == "IncomingBytes" else 3.0],
                    "StatusCode": "Complete",
                }
            )
        return {"MetricDataResults": results}


class FakeBoto3:
    def __init__(self):
        self.clients = {
            "s3": FakeS3(),
            "glue": FakeGlue(),
            "kinesis": FakeKinesis(),
            "kafka": FakeKafka(),
            "dms": FakeDms(),
            "cloudwatch": FakeCloudWatch(),
        }

    def client(self, name, **kwargs):
        return self.clients[name]


def _ids() -> dict[str, str]:
    return {
        "checkpoint_s3_uri": "s3://analytics/checkpoints/orders",
        "glue_job_name": "orders-stream",
        "kinesis_stream_name": "orders",
        "msk_cluster_arn": "arn:aws:kafka:us-east-1:111111111111:cluster/orders/abc",
        "dms_task_arn": "arn:aws:dms:us-east-1:111111111111:task:orders",
    }


def test_collector_composes_read_only_snapshots_and_redacts(monkeypatch, tmp_path):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)

    entry = streaming.collect_streaming_integrations(
        tmp_path, now="2026-10-02T00:00:00Z", **_ids()
    )

    payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
    assert entry.kind == "streaming_integrations"
    assert payload["collection"]["read_only"] is True
    assert sorted(payload["collection"]["sections"]) == [
        "checkpoint",
        "dms",
        "glue_streaming",
        "kinesis",
        "msk",
    ]
    assert payload["glue_streaming"]["job"]["DefaultArguments"]["--password"] == "<redacted>"
    assert payload["checkpoint"]["object_count"] == 2
    assert payload["kinesis"]["shard_count"] == 1
    assert payload["msk"]["api"] == "describe_cluster_v2"
    assert load_manifest(tmp_path)[0]["kind"] == "streaming_integrations"


def test_kinesis_temporal_metrics_are_collected_and_normalized(monkeypatch, tmp_path):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)

    entry = streaming.collect_streaming_integrations(
        tmp_path,
        now="2026-10-02T00:10:00Z",
        kinesis_stream_name="orders",
        region_name="us-east-1",
        metrics_start="2026-10-02T00:00:00Z",
        metrics_end="2026-10-02T00:05:00Z",
        metrics_period=60,
    )

    payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
    metrics = payload["kinesis"]["metrics"]
    assert entry.path.endswith("__metrics_2026-10-02T00_00_00Z_2026-10-02T00_05_00Z_60.json")
    assert metrics["namespace"] == "AWS/Kinesis"
    assert metrics["metrics_requested"] == 5
    assert metrics["metrics_returned"] == 5
    assert metrics["metrics_missing"] == []
    assert len(metrics["observations"]) == 10
    assert {item["name"] for item in metrics["observations"]} == {
        "IncomingBytes",
        "IncomingRecords",
        "GetRecords.IteratorAgeMilliseconds",
        "ReadProvisionedThroughputExceeded",
        "WriteProvisionedThroughputExceeded",
    }
    call = fake.clients["cloudwatch"].calls[0]
    assert call["StartTime"].isoformat() == "2026-10-02T00:00:00+00:00"
    assert call["EndTime"].isoformat() == "2026-10-02T00:05:00+00:00"
    assert all(
        query["MetricStat"]["Metric"]["Dimensions"] == [{"Name": "StreamName", "Value": "orders"}]
        for query in call["MetricDataQueries"]
    )
    assert fake.clients["cloudwatch"].calls[0]["ScanBy"] == "TimestampAscending"


def test_kinesis_temporal_metrics_feed_transport_analyzer(monkeypatch, tmp_path):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)
    entry = streaming.collect_streaming_integrations(
        tmp_path,
        now="2026-10-02T00:10:00Z",
        kinesis_stream_name="orders",
        metrics_start="2026-10-02T00:00:00Z",
        metrics_end="2026-10-02T00:05:00Z",
        metrics_period=60,
    )

    from sparkforge.facts.transport import extract_transport_path

    facts = extract_transport_path(tmp_path / entry.path, artifact_type="kinesis")
    metric_facts = [fact for fact in facts if fact.kind == "kinesis.metric"]
    assert len(metric_facts) == 10
    assert {fact.attrs["name"] for fact in metric_facts} == {
        "IncomingBytes",
        "IncomingRecords",
        "GetRecords.IteratorAgeMilliseconds",
        "ReadProvisionedThroughputExceeded",
        "WriteProvisionedThroughputExceeded",
    }
    assert all(fact.attrs["observed_at"].endswith("+00:00") for fact in metric_facts)
    assert all(fact.attrs["stream_name"] == "orders" for fact in metric_facts)
    assert not any(fact.attrs.get("reason") == "kinesis_metric_missing" for fact in facts)


def test_offline_hit_does_not_touch_aws(monkeypatch, tmp_path):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)
    first = streaming.collect_streaming_integrations(
        tmp_path, now="2026-10-02T00:00:00Z", **_ids()
    )

    def boom():
        raise AssertionError("cache hit deveria permanecer offline")

    monkeypatch.setattr(streaming, "require_boto3", boom)
    second = streaming.collect_streaming_integrations(
        tmp_path, now="2026-10-03T00:00:00Z", **_ids()
    )
    assert second == first


def test_missing_source_and_bounds_are_actionable(tmp_path, monkeypatch):
    with pytest.raises(streaming.CollectionFailed, match="ao menos uma fonte"):
        streaming.collect_streaming_integrations(tmp_path, now="2026-10-02T00:00:00Z")

    monkeypatch.setattr(streaming, "require_boto3", lambda: FakeBoto3())
    with pytest.raises(ValueError, match="max_objects"):
        streaming.collect_streaming_integrations(
            tmp_path,
            now="2026-10-02T00:00:00Z",
            checkpoint_s3_uri="s3://bucket/prefix",
            max_objects=501,
        )


def test_boto3_absence_keeps_manual_recollection_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        streaming,
        "require_boto3",
        lambda: (_ for _ in ()).throw(CollectorUnavailable("boto3 ausente")),
    )
    with pytest.raises(CollectorUnavailable):
        streaming.collect_streaming_integrations(
            tmp_path,
            now="2026-10-02T00:00:00Z",
            kinesis_stream_name="orders",
        )


def test_cli_parser_and_handler_are_wired(monkeypatch, tmp_path, capsys):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)
    code = main(
        [
            "collect",
            "streaming-integrations",
            "--repo",
            str(tmp_path),
            "--kinesis-stream",
            "orders",
            "--now",
            "2026-10-02T00:00:00Z",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "streaming_integrations"
    assert payload["cache_hit"] is False


def test_cli_and_mcp_streaming_temporal_collection_match(monkeypatch, tmp_path, capsys):
    fake = FakeBoto3()
    monkeypatch.setattr(streaming, "require_boto3", lambda: fake)
    common = [
        "--kinesis-stream",
        "orders",
        "--metrics-start",
        "2026-10-02T00:00:00Z",
        "--metrics-end",
        "2026-10-02T00:05:00Z",
        "--metrics-period",
        "60",
        "--now",
        "2026-10-02T00:10:00Z",
    ]

    cli_code = main(
        ["collect", "streaming-integrations", "--repo", str(tmp_path / "cli"), *common]
    )
    cli_payload = json.loads(capsys.readouterr().out)
    mcp_payload = call_tool(
        "sparkforge_collect_streaming_integrations",
        {
            "repo": str(tmp_path / "mcp"),
            "kinesis_stream_name": "orders",
            "metrics_start": "2026-10-02T00:00:00Z",
            "metrics_end": "2026-10-02T00:05:00Z",
            "metrics_period": 60,
            "now": "2026-10-02T00:10:00Z",
        },
    )

    assert cli_code == 0
    assert cli_payload["kind"] == mcp_payload["kind"] == "streaming_integrations"
    assert cli_payload["path"] == mcp_payload["path"]
    assert cli_payload["sha256"] == mcp_payload["sha256"]


def test_kinesis_temporal_docs_state_window_and_limits():
    root = Path(__file__).parents[1]
    knowledge = (root / "knowledge/transport-diagnostics.md").read_text(encoding="utf-8")
    integrations = (root / "knowledge/streaming-integrations.md").read_text(encoding="utf-8")
    coverage = (root / "docs/streaming/prompt-coverage.md").read_text(encoding="utf-8")
    cli = (root / "docs/guia/03-cli.md").read_text(encoding="utf-8")
    mcp = (root / "docs/guia/04-mcp.md").read_text(encoding="utf-8")

    for text in (knowledge, integrations, coverage, cli, mcp):
        assert "metrics_start" in text or "--metrics-start" in text
        assert "metrics_end" in text or "--metrics-end" in text
        assert "enhanced" in text.lower()
        assert "unresolved" in text
    assert "GetRecords.IteratorAgeMilliseconds" in knowledge
    assert "STREAMING_KINESIS_TEMPORAL_METRICS" in coverage
