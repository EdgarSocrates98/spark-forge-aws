from __future__ import annotations

import json

import pytest

from sparkforge.adapters.cli import main
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


class FakeBoto3:
    def __init__(self):
        self.clients = {
            "s3": FakeS3(),
            "glue": FakeGlue(),
            "kinesis": FakeKinesis(),
            "kafka": FakeKafka(),
            "dms": FakeDms(),
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
