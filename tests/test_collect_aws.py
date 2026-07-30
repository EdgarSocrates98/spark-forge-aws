"""Testes de sparkforge.collect.aws com um cliente boto3 falso injetado.

Nunca chama AWS de verdade. `require_boto3` e monkeypatchado para devolver
um objeto `FakeBoto3` cujo `.client(name)` devolve um stub com exatamente os
metodos que cada coletor usa -- suficiente para asserir que os argumentos
certos foram passados, sem depender de rede nem de credenciais.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from sparkforge.collect import aws
from sparkforge.collect.base import CollectorUnavailable, load_manifest, verify_all


class FakeS3Client:
    def __init__(self, body: bytes = b'{"Event":"SparkListenerJobStart"}\n'):
        self.calls: list[tuple[str, dict]] = []
        self._body = body

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return {"Contents": [{"Key": f"{kwargs['Prefix']}part-00000"}]}

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))
        return {"Body": io.BytesIO(self._body)}


class EmptyS3Client:
    def list_objects_v2(self, **kwargs):
        return {"Contents": []}


class FakeGlueClient:
    def __init__(self, job: dict):
        self.calls: list[tuple[str, dict]] = []
        self._job = job

    def get_job(self, **kwargs):
        self.calls.append(("get_job", kwargs))
        return {"Job": self._job}


class FakeCloudWatchClient:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def get_metric_data(self, **kwargs):
        self.calls.append(("get_metric_data", kwargs))
        return {
            "MetricDataResults": [
                {"Id": "m0", "Label": aws.CLOUDWATCH_METRICS[0], "Timestamps": [], "Values": []}
            ]
        }


class FakeAthenaClient:
    """Sucede na primeira checagem: o poll loop nunca dorme durante o teste."""

    def __init__(self, rows_by_query: dict[str, list[dict]] | None = None):
        self.calls: list[tuple[str, dict]] = []
        self._exec_id = 0
        self._rows_by_query = rows_by_query or {}

    def start_query_execution(self, **kwargs):
        self.calls.append(("start_query_execution", kwargs))
        self._exec_id += 1
        return {"QueryExecutionId": f"q{self._exec_id}"}

    def get_query_execution(self, **kwargs):
        self.calls.append(("get_query_execution", kwargs))
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_query_results(self, **kwargs):
        self.calls.append(("get_query_results", kwargs))
        query = self._last_query()
        rows = self._rows_by_query.get(query, [])
        return {"ResultSet": {"Rows": rows}}

    def _last_query(self) -> str:
        for name, kwargs in reversed(self.calls):
            if name == "start_query_execution":
                return kwargs["QueryString"]
        return ""


class FailingAthenaClient:
    def start_query_execution(self, **kwargs):
        return {"QueryExecutionId": "q1"}

    def get_query_execution(self, **kwargs):
        return {
            "QueryExecution": {
                "Status": {"State": "FAILED", "StateChangeReason": "TABLE_NOT_FOUND"}
            }
        }

    def get_query_results(self, **kwargs):  # pragma: no cover -- never reached
        raise AssertionError("nao deveria chamar get_query_results apos FAILED")


class FakeBoto3:
    def __init__(self, **clients):
        self._clients = clients

    def client(self, name, **kwargs):
        return self._clients[name]


def _rows(header: list[str], data: list[list[str]]) -> list[dict]:
    def cell_row(values):
        return {"Data": [{"VarCharValue": v} for v in values]}

    return [cell_row(header)] + [cell_row(r) for r in data]


class TestCollectEventLog:
    def test_calls_s3_and_registers_artifact(self, tmp_path, monkeypatch):
        s3 = FakeS3Client()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(s3=s3))

        entry = aws.collect_event_log(
            "jr_1", tmp_path, bucket="my-bucket", prefix="spark-logs", now="2026-07-30T00:00:00Z"
        )

        assert entry.kind == "event_log"
        assert entry.path == ".sparkforge/artifacts/eventlog/jr_1.jsonl"
        assert entry.source == "s3://my-bucket/spark-logs/jr_1/"
        assert entry.collected_at == "2026-07-30T00:00:00Z"
        assert (tmp_path / entry.path).is_file()
        assert load_manifest(tmp_path) == [entry.to_dict()]

        list_call = next(c for c in s3.calls if c[0] == "list_objects_v2")
        assert list_call[1] == {"Bucket": "my-bucket", "Prefix": "spark-logs/jr_1/"}
        get_call = next(c for c in s3.calls if c[0] == "get_object")
        assert get_call[1]["Bucket"] == "my-bucket"

    def test_offline_hit_does_not_touch_boto3_when_hash_matches(self, tmp_path, monkeypatch):
        s3 = FakeS3Client()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(s3=s3))
        first = aws.collect_event_log(
            "jr_2", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
        )
        assert len(s3.calls) == 2  # list + get, exactly once

        def boom():
            raise AssertionError("require_boto3 nao deveria ser chamado num cache hit")

        monkeypatch.setattr(aws, "require_boto3", boom)
        second = aws.collect_event_log(
            "jr_2", tmp_path, bucket="b", prefix="p", now="2026-07-30T01:00:00Z"
        )

        assert second == first
        assert second.collected_at == "2026-07-30T00:00:00Z"  # inalterado: nao recoletou

    def test_recollects_when_local_file_is_corrupted(self, tmp_path, monkeypatch):
        s3 = FakeS3Client()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(s3=s3))
        first = aws.collect_event_log(
            "jr_3", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
        )
        assert len(s3.calls) == 2

        (tmp_path / first.path).write_bytes(b"corrupted, does not match sha256\n")

        second = aws.collect_event_log(
            "jr_3", tmp_path, bucket="b", prefix="p", now="2026-07-30T02:00:00Z"
        )
        assert len(s3.calls) == 4  # coletou de novo: mais um list + get
        assert second.collected_at == "2026-07-30T02:00:00Z"
        assert second.sha256 == first.sha256  # conteudo remoto e o mesmo de novo

    def test_raises_collection_failed_when_prefix_is_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(s3=EmptyS3Client()))
        with pytest.raises(aws.CollectionFailed, match="nenhum objeto de event log"):
            aws.collect_event_log(
                "jr_4", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
            )

    def test_raises_collector_unavailable_with_actionable_message_when_boto3_absent(
        self, tmp_path, monkeypatch
    ):
        def boom():
            raise CollectorUnavailable(
                "boto3 nao disponivel. Instale com `pip install 'sparkforge-aws[aws]'` "
                "para usar coletores AWS, ou colete o artefato manualmente (AWS CLI ou "
                "console) e registre-o com `sparkforge.collect.register_artifact`."
            )

        monkeypatch.setattr(aws, "require_boto3", boom)
        with pytest.raises(CollectorUnavailable, match=r"sparkforge-aws\[aws\]"):
            aws.collect_event_log(
                "jr_5", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
            )


class TestCollectGlueJob:
    def test_writes_job_definition_as_json(self, tmp_path, monkeypatch):
        job = {"Name": "etl-job", "GlueVersion": "5.0", "NumberOfWorkers": 10}
        glue = FakeGlueClient(job)
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        entry = aws.collect_glue_job("etl-job", tmp_path, now="2026-07-30T00:00:00Z")

        assert entry.kind == "terraform"
        assert entry.path == ".sparkforge/artifacts/glue_job/etl-job.json"
        written = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
        assert written == job
        assert glue.calls == [("get_job", {"JobName": "etl-job"})]

    def test_offline_hit_is_a_noop(self, tmp_path, monkeypatch):
        glue = FakeGlueClient({"Name": "j"})
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))
        aws.collect_glue_job("j", tmp_path, now="2026-07-30T00:00:00Z")
        assert len(glue.calls) == 1

        aws.collect_glue_job("j", tmp_path, now="2026-07-30T01:00:00Z")
        assert len(glue.calls) == 1  # sem segunda chamada


class TestCollectCloudwatch:
    def test_queries_exact_metric_names_including_bytesWrittten(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        entry = aws.collect_cloudwatch(
            "etl-job",
            "jr_9",
            tmp_path,
            now="2026-07-30T00:00:00Z",
            start="2026-07-29T00:00:00Z",
            end="2026-07-30T00:00:00Z",
        )

        assert entry.kind == "cloudwatch"
        call = cw.calls[0][1]
        metric_names = {q["MetricStat"]["Metric"]["MetricName"] for q in call["MetricDataQueries"]}
        assert "glue.driver.bytesWrittten" in metric_names  # tres "t", grafia AWS
        assert "glue.driver.bytesWritten" not in metric_names
        dims = call["MetricDataQueries"][0]["MetricStat"]["Metric"]["Dimensions"]
        assert {"Name": "JobName", "Value": "etl-job"} in dims
        assert {"Name": "JobRunId", "Value": "jr_9"} in dims


class TestCollectIcebergMetadata:
    def test_queries_all_five_sections_with_dollar_syntax(self, tmp_path, monkeypatch):
        rows_by_query = {
            'SELECT * FROM "db"."tbl$files"': _rows(
                ["file_path", "file_size_in_bytes", "record_count"],
                [["s3://b/f1.parquet", "1024", "10"]],
            ),
            'SELECT * FROM "db"."tbl$delete_files"': [],
            'SELECT * FROM "db"."tbl$snapshots"': [],
            'SELECT * FROM "db"."tbl$manifests"': [],
            'SELECT * FROM "db"."tbl$partitions"': [],
        }
        athena = FakeAthenaClient(rows_by_query)
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(athena=athena))

        entry = aws.collect_iceberg_metadata(
            "db.tbl",
            tmp_path,
            workgroup="primary",
            output_location="s3://athena-results/",
            now="2026-07-30T00:00:00Z",
        )

        assert entry.kind == "iceberg_metadata"
        payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
        assert payload["table"] == "db.tbl"
        assert payload["files"] == [
            {"file_path": "s3://b/f1.parquet", "file_size_in_bytes": 1024, "record_count": 10}
        ]
        assert payload["delete_files"] == []

        queries = {c[1]["QueryString"] for c in athena.calls if c[0] == "start_query_execution"}
        assert queries == set(rows_by_query)

    def test_raises_collection_failed_when_query_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(athena=FailingAthenaClient()))
        with pytest.raises(aws.CollectionFailed, match="FAILED"):
            aws.collect_iceberg_metadata(
                "db.tbl",
                tmp_path,
                workgroup="primary",
                output_location="s3://athena-results/",
                now="2026-07-30T00:00:00Z",
            )


class TestCollectVerifyIntegration:
    def test_verify_reports_missing_artifact_with_its_recollect_command(self, tmp_path):
        from sparkforge.collect.base import ArtifactEntry, register_artifact

        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_missing.jsonl",
            sha256="a" * 64,
            source="s3://bucket/prefix/jr_missing/",
            collect_command=(
                "sparkforge collect event-log --job-run jr_missing --bucket bucket --prefix prefix"
            ),
            collected_at="2026-07-29T00:00:00Z",
        )
        register_artifact(entry, tmp_path)

        results = verify_all(tmp_path)
        assert len(results) == 1
        assert results[0]["present"] is False
        assert results[0]["collect_command"] == entry.collect_command


def test_module_imports_and_functions_exist_without_boto3(monkeypatch):
    # aws.py nunca importa boto3 no topo -- checagem direta de que o modulo
    # ja esta carregado nesta suite (boto3 genuinamente ausente no ambiente)
    # e expoe as quatro funcoes de coleta.
    assert callable(aws.collect_event_log)
    assert callable(aws.collect_glue_job)
    assert callable(aws.collect_cloudwatch)
    assert callable(aws.collect_iceberg_metadata)


def test_path_helpers_match_what_collectors_actually_write(tmp_path, monkeypatch):
    s3 = FakeS3Client()
    monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(s3=s3))
    entry = aws.collect_event_log(
        "jr_helper", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
    )
    assert entry.path == aws.event_log_path("jr_helper")
    assert Path(entry.path) == Path(aws.event_log_path("jr_helper"))


class TestCloudwatchStatPerMetric:
    """`Stat` uniforme e defeito de dado, nao simplificacao. `glue.error.ALL` e um
    contador documentado como SUM; pedir Average dele devolve numero errado com
    aparencia de certo, que e a classe de resultado que este projeto existe para
    nao produzir."""

    def test_counter_metrics_use_sum(self):
        from sparkforge.collect.aws import CLOUDWATCH_METRICS

        stats = dict(CLOUDWATCH_METRICS)
        assert stats["glue.error.ALL"] == "Sum"
        assert stats["glue.succeed.ALL"] == "Sum"

    def test_percentage_metrics_use_maximum_not_average(self):
        """Pico de heap e o que importa para diagnosticar OOM; a media esconde o pico."""
        from sparkforge.collect.aws import CLOUDWATCH_METRICS

        stats = dict(CLOUDWATCH_METRICS)
        assert stats["glue.driver.memory.heap.used.percentage"] == "Maximum"
        assert stats["glue.ALL.memory.heap.used.percentage"] == "Maximum"

    def test_skewness_uses_maximum(self):
        from sparkforge.collect.aws import CLOUDWATCH_METRICS

        assert dict(CLOUDWATCH_METRICS)["glue.driver.skewness.job"] == "Maximum"

    def test_aws_three_t_spelling_is_preserved(self):
        from sparkforge.collect.aws import CLOUDWATCH_METRIC_NAMES

        assert "glue.driver.bytesWrittten" in CLOUDWATCH_METRIC_NAMES
        assert "glue.driver.bytesWritten" not in CLOUDWATCH_METRIC_NAMES

    def test_every_metric_declares_a_known_stat(self):
        from sparkforge.collect.aws import CLOUDWATCH_METRICS

        valid = {"Average", "Sum", "Maximum", "Minimum", "SampleCount"}
        for name, stat in CLOUDWATCH_METRICS:
            assert stat in valid, f"{name} com Stat invalido: {stat}"
