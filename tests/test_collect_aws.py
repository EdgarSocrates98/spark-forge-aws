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


class FakeGlueRunsClient:
    """`get_job_runs` paginado. Cada item de `pages` e uma resposta completa."""

    def __init__(self, pages: list[dict]):
        self.calls: list[tuple[str, dict]] = []
        self._pages = pages

    def get_job_runs(self, **kwargs):
        self.calls.append(("get_job_runs", kwargs))
        index = 0 if "NextToken" not in kwargs else int(kwargs["NextToken"])
        return self._pages[index]


class EntityNotFoundException(Exception):
    """Reproduz o nome da excecao que botocore levanta para job inexistente."""


class MissingJobGlueClient:
    def get_job_runs(self, **kwargs):
        raise EntityNotFoundException("Job with name: nope not found")


def _run(run_id: str, state: str = "SUCCEEDED", **extra) -> dict:
    base = {
        "Id": run_id,
        "JobName": "my-job",
        "JobRunState": state,
        "StartedOn": "2026-08-01T10:00:00+00:00",
        "CompletedOn": "2026-08-01T10:20:00+00:00",
        "ExecutionTime": 1200,
        "GlueVersion": "5.0",
        "WorkerType": "G.1X",
        "NumberOfWorkers": 10,
        "Timeout": 60,
    }
    base.update(extra)
    return base


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


class TestCollectGlueJobRuns:
    def test_writes_one_artifact_per_terminal_run(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1"), _run("jr_2")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 2
        assert (tmp_path / aws.glue_job_run_path("my-job", "jr_1")).is_file()
        assert (tmp_path / aws.glue_job_run_path("my-job", "jr_2")).is_file()
        kinds = {e["kind"] for e in load_manifest(tmp_path)}
        assert kinds == {"glue_job_run"}

    def test_non_terminal_run_is_skipped_not_written(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient(
            [{"JobRuns": [_run("jr_1"), _run("jr_2", state="RUNNING")]}]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 1
        assert result["skipped"] == [{"job_run_id": "jr_2", "state": "RUNNING"}]
        assert not (tmp_path / aws.glue_job_run_path("my-job", "jr_2")).exists()

    def test_second_collection_only_writes_the_new_runs(self, tmp_path, monkeypatch):
        first = FakeGlueRunsClient([{"JobRuns": [_run("jr_1"), _run("jr_2")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=first))
        aws.collect_glue_job_runs("my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z")

        second = FakeGlueRunsClient(
            [{"JobRuns": [_run("jr_3"), _run("jr_1"), _run("jr_2")]}]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=second))
        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-27T00:00:00Z"
        )

        cache_hits = [a for a in result["artifacts"] if a["cache_hit"]]
        fresh = [a for a in result["artifacts"] if not a["cache_hit"]]
        assert len(cache_hits) == 2
        assert len(fresh) == 1
        assert fresh[0]["path"] == aws.glue_job_run_path("my-job", "jr_3")

    def test_recollects_when_local_file_is_corrupted(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1")]}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))
        aws.collect_glue_job_runs("my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z")

        target = tmp_path / aws.glue_job_run_path("my-job", "jr_1")
        target.write_text("corrompido", encoding="utf-8")

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-27T00:00:00Z"
        )

        assert result["artifacts"][0]["cache_hit"] is False
        assert json.loads(target.read_text(encoding="utf-8"))["Id"] == "jr_1"
        assert all(v["hash_matches"] for v in verify_all(tmp_path))

    def test_follows_pagination_until_max_runs(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient(
            [
                {"JobRuns": [_run("jr_1")], "NextToken": "1"},
                {"JobRuns": [_run("jr_2")]},
            ]
        )
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert len(result["artifacts"]) == 2
        assert len(glue.calls) == 2

    def test_stops_at_max_runs_without_extra_calls(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": [_run("jr_1")], "NextToken": "1"}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=1, now="2026-08-26T00:00:00Z"
        )

        assert result["runs_listed"] == 1
        assert len(glue.calls) == 1

    def test_job_without_runs_succeeds_with_nothing_collected(self, tmp_path, monkeypatch):
        glue = FakeGlueRunsClient([{"JobRuns": []}])
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(glue=glue))

        result = aws.collect_glue_job_runs(
            "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
        )

        assert result["artifacts"] == []
        assert result["skipped"] == []

    def test_missing_job_raises_collection_failed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(glue=MissingJobGlueClient())
        )
        with pytest.raises(aws.CollectionFailed, match="nao existe"):
            aws.collect_glue_job_runs(
                "nope", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
            )

    def test_raises_collector_unavailable_when_boto3_absent(self, tmp_path, monkeypatch):
        def boom():
            raise CollectorUnavailable("boto3 nao disponivel")

        monkeypatch.setattr(aws, "require_boto3", boom)
        with pytest.raises(CollectorUnavailable, match="boto3"):
            aws.collect_glue_job_runs(
                "my-job", tmp_path, max_runs=30, now="2026-08-26T00:00:00Z"
            )


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


class TestCloudWatchPeriod:
    def test_recent_run_uses_the_finest_period(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_1",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-26T10:00:00Z",
            end="2026-08-26T10:20:00Z",
        )

        periods = {
            q["MetricStat"]["Period"]
            for _, kwargs in cw.calls
            for q in kwargs["MetricDataQueries"]
        }
        assert periods == {60}

    def test_old_run_escalates_the_period(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_old",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-01T10:00:00Z",
            end="2026-08-01T10:20:00Z",
        )

        periods = {
            q["MetricStat"]["Period"]
            for _, kwargs in cw.calls
            for q in kwargs["MetricDataQueries"]
        }
        assert periods == {300}

    def test_expired_run_fails_instead_of_querying(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        with pytest.raises(aws.CollectionFailed, match="expirad"):
            aws.collect_cloudwatch(
                "my-job",
                "jr_ancient",
                tmp_path,
                now="2026-08-26T00:00:00Z",
                start="2020-01-01T10:00:00Z",
                end="2020-01-01T10:20:00Z",
            )
        assert cw.calls == []

    def test_period_is_recorded_in_the_artifact(self, tmp_path, monkeypatch):
        cw = FakeCloudWatchClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(cloudwatch=cw))

        aws.collect_cloudwatch(
            "my-job",
            "jr_1",
            tmp_path,
            now="2026-08-26T00:00:00Z",
            start="2026-08-26T10:00:00Z",
            end="2026-08-26T10:20:00Z",
        )

        payload = json.loads(
            (tmp_path / aws.cloudwatch_path("my-job", "jr_1")).read_text(encoding="utf-8")
        )
        assert payload["period_seconds"] == 60


class TestCollectIcebergMetadata:
    def test_queries_as_quatro_secoes_que_o_athena_EXPOE(self, tmp_path, monkeypatch):
        """Quatro, e nao cinco -- MEDIDO contra o Athena real em 2026-09-03.

        `delete_files` estava nesta lista e NAO PODIA FUNCIONAR: o Athena
        responde `TABLE_REDIRECTION_ERROR: ... the target table does not
        exist`. Toda coleta falhava naquela secao, e o extrator recebia o dump
        sem ela -- indistinguivel de uma tabela sem deletes.

        E O FAKE ERA O QUE ESCONDIA ISSO. `FakeAthenaClient` respondia
        `$delete_files` de bom grado, entao o teste ficava verde sobre uma
        consulta impossivel. Um fake que aceita tudo prova que o codigo chama o
        que ele espera, nunca que o servico responde.

        Os deletes vem de `$files` pela coluna `content` (0 data, 1 position,
        2 equality) -- a mesma que `iceberg_metadata.py` conta.
        """
        rows_by_query = {
            'SELECT * FROM "db"."tbl$files"': _rows(
                ["file_path", "file_size_in_bytes", "record_count"],
                [["s3://b/f1.parquet", "1024", "10"]],
            ),
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
        assert "delete_files" not in payload, (
            "`$delete_files` nao existe no Athena; pedi-la e TABLE_REDIRECTION_ERROR"
        )

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


class FakeEmrClient:
    """Cluster de instance GROUPS, paginado, com fleets inaplicavel.

    `list_instance_fleets` levanta como a API real levanta quando o modelo nao
    se aplica, e `get_managed_scaling_policy` devolve `{}` como quando nao ha
    politica: sao os dois caminhos que provam a diferenca entre "secao omitida"
    e "secao vazia".
    """

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def describe_cluster(self, **kwargs):
        self.calls.append(("describe_cluster", kwargs))
        return {
            "Cluster": {
                "Id": kwargs["ClusterId"],
                "ReleaseLabel": "emr-7.5.0",
                "InstanceCollectionType": "INSTANCE_GROUP",
                "LogUri": "s3://bucket/elasticmapreduce/",
                "AutoTerminate": False,
                "Applications": [{"Name": "Spark", "Version": "3.5.2-amzn-1"}],
                "Status": {"State": "RUNNING"},
            }
        }

    def list_instance_groups(self, **kwargs):
        self.calls.append(("list_instance_groups", kwargs))
        if kwargs.get("Marker") == "pagina-2":
            return {
                "InstanceGroups": [
                    {
                        "Id": "ig-TASK",
                        "InstanceGroupType": "TASK",
                        "Market": "SPOT",
                        "InstanceType": "r5.xlarge",
                        "RequestedInstanceCount": 4,
                    }
                ]
            }
        return {
            "InstanceGroups": [
                {
                    "Id": "ig-MASTER",
                    "InstanceGroupType": "MASTER",
                    "Market": "ON_DEMAND",
                    "InstanceType": "m5.xlarge",
                    "RequestedInstanceCount": 1,
                }
            ],
            "Marker": "pagina-2",
        }

    def list_instance_fleets(self, **kwargs):
        raise RuntimeError("InvalidRequestException: cluster nao usa instance fleets")

    def list_bootstrap_actions(self, **kwargs):
        self.calls.append(("list_bootstrap_actions", kwargs))
        return {"BootstrapActions": []}

    def get_managed_scaling_policy(self, **kwargs):
        return {}

    def get_auto_termination_policy(self, **kwargs):
        return {"AutoTerminationPolicy": {"IdleTimeout": 3600}}


class TestCollectEmrCluster:
    def _collect(self, tmp_path, monkeypatch):
        emr = FakeEmrClient()
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(emr=emr))
        entry = aws.collect_emr_cluster("j-1EXAMPLE", tmp_path, now="2026-08-01T00:00:00Z")
        return emr, entry, json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))

    def test_writes_the_union_of_the_dumps_in_the_shape_the_extractor_reads(
        self, tmp_path, monkeypatch
    ):
        _, entry, payload = self._collect(tmp_path, monkeypatch)
        assert entry.kind == "emr_cluster"
        assert payload["Cluster"]["ReleaseLabel"] == "emr-7.5.0"
        assert payload["AutoTerminationPolicy"] == {"IdleTimeout": 3600}

    def test_paginates_until_the_marker_runs_out(self, tmp_path, monkeypatch):
        """Parar na primeira pagina esconderia o grupo TASK -- e um cluster sem
        TASK parece um cluster sem capacidade Spot, que e a conclusao errada."""
        _, _, payload = self._collect(tmp_path, monkeypatch)
        assert [g["Id"] for g in payload["InstanceGroups"]] == ["ig-MASTER", "ig-TASK"]

    def test_inapplicable_section_is_omitted_never_written_empty(
        self, tmp_path, monkeypatch
    ):
        """`InstanceFleets: []` num cluster de grupos seria lido pelo extrator
        como "coletado e vazio", e ele deixaria de reportar dump incompleto.
        Politica de scaling ausente segue a mesma regra."""
        _, _, payload = self._collect(tmp_path, monkeypatch)
        assert "InstanceFleets" not in payload
        assert "ManagedScalingPolicy" not in payload

    def test_the_written_artifact_is_readable_by_the_extractor(self, tmp_path, monkeypatch):
        """O contrato entre coletor e extrator, provado ponta a ponta: o
        arquivo que este coletor grava tem que produzir facts, nao
        `emr.unresolved`."""
        from sparkforge.facts.emr_cluster import extract_emr_cluster_path

        _, entry, _ = self._collect(tmp_path, monkeypatch)
        facts = extract_emr_cluster_path(tmp_path / entry.path, repo_root=tmp_path)
        kinds = {f.kind for f in facts}
        assert "emr.unresolved" not in kinds
        assert {"emr.cluster", "emr.instance_capacity", "emr.application"} <= kinds

    def test_second_call_is_a_local_no_op(self, tmp_path, monkeypatch):
        emr, first, _ = self._collect(tmp_path, monkeypatch)
        before = len(emr.calls)
        monkeypatch.setattr(aws, "require_boto3", lambda: FakeBoto3(emr=emr))
        second = aws.collect_emr_cluster("j-1EXAMPLE", tmp_path, now="2026-08-01T01:00:00Z")
        assert second.collected_at == first.collected_at
        assert len(emr.calls) == before


class FakeEmrServerlessClient:
    """UMA operacao, e e a unica que este coletor conhece.

    O contraste com `FakeEmrClient` e o ponto: la a API espalha grupos, fleets,
    bootstrap actions e politicas por seis chamadas, e metade delas pode nao se
    aplicar ao cluster; aqui `GetApplication` devolve capacidade inicial, maxima,
    auto-stop, `runtimeConfiguration` e `monitoringConfiguration` no mesmo objeto.
    Nao ha `_emr_optional` equivalente porque nao ha secao opcional a omitir.
    """

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def get_application(self, **kwargs):
        self.calls.append(("get_application", kwargs))
        return {
            "application": {
                "applicationId": kwargs["applicationId"],
                "arn": "arn:aws:emr-serverless:us-east-1:123456789012:/applications/00fEXAMPLE",
                "name": "etl",
                "releaseLabel": "emr-7.5.0",
                "type": "Spark",
                "state": "STARTED",
                "architecture": "X86_64",
                "autoStopConfiguration": {"enabled": True, "idleTimeoutMinutes": 15},
                "initialCapacity": {
                    "DRIVER": {
                        "workerCount": 1,
                        "workerConfiguration": {
                            "cpu": "4vCPU",
                            "memory": "16GB",
                            "disk": "20GB",
                        },
                    }
                },
                # Teto E `disk` no worker sao deliberados. Os dois sao
                # `Required: No` na API, e sem qualquer um deles o extrator emite
                # `emrs.unresolved` com `capacity_comparison_undecidable` -- que e
                # o comportamento CERTO, e nao o que este teste de coletor quer
                # exercitar. Uma application com o eixo faltando e caso de fixture
                # (Task 4); aqui o payload e completo justamente para que
                # "artefato legivel sem ponto cego" seja uma afirmacao verificavel.
                "maximumCapacity": {"cpu": "400vCPU", "memory": "3000GB", "disk": "20000GB"},
                "runtimeConfiguration": [
                    {
                        "classification": "spark-defaults",
                        "properties": {"spark.executor.cores": "4"},
                    }
                ],
                "monitoringConfiguration": {
                    "s3MonitoringConfiguration": {"logUri": "s3://bucket/emrs-logs/"}
                },
            }
        }


class TestCollectEmrServerless:
    def _collect(self, tmp_path, monkeypatch, now="2026-08-04T00:00:00Z"):
        emrs = FakeEmrServerlessClient()
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(**{"emr-serverless": emrs})
        )
        entry = aws.collect_emr_serverless("00fEXAMPLE", tmp_path, now=now)
        return emrs, entry, json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))

    def test_writes_the_response_in_the_shape_the_extractor_reads(self, tmp_path, monkeypatch):
        _, entry, payload = self._collect(tmp_path, monkeypatch)
        assert entry.kind == "emr_serverless"
        assert entry.path == aws.emr_serverless_path("00fEXAMPLE")
        # camelCase preservado, sem traducao: o arquivo tem que ser
        # indistinguivel do que `aws emr-serverless get-application` imprime.
        assert payload["application"]["releaseLabel"] == "emr-7.5.0"
        assert payload["application"]["initialCapacity"]["DRIVER"]["workerCount"] == 1

    def test_one_call_and_only_get_application(self, tmp_path, monkeypatch):
        """Job runs estao fora do escopo desta fase, e `list-applications` esta
        fora por identidade: `name` e opcional na API e nenhuma fonte o declara
        unico, entao resolver id por nome escolheria uma entre homonimas em
        silencio."""
        emrs, _, _ = self._collect(tmp_path, monkeypatch)
        assert [name for name, _ in emrs.calls] == ["get_application"]
        assert emrs.calls[0][1] == {"applicationId": "00fEXAMPLE"}

    def test_the_written_artifact_is_readable_by_the_extractor(self, tmp_path, monkeypatch):
        """O contrato entre coletor e extrator, provado ponta a ponta."""
        from sparkforge.facts.emr_serverless import extract_emr_serverless_path

        _, entry, _ = self._collect(tmp_path, monkeypatch)
        facts = extract_emr_serverless_path(tmp_path / entry.path, repo_root=tmp_path)
        kinds = {f.kind for f in facts}
        assert "emrs.unresolved" not in kinds
        assert {"emrs.application", "emrs.initial_capacity", "emrs.configuration"} <= kinds

    def test_second_call_is_a_local_no_op(self, tmp_path, monkeypatch):
        emrs, first, _ = self._collect(tmp_path, monkeypatch)
        before = len(emrs.calls)
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(**{"emr-serverless": emrs})
        )
        second = aws.collect_emr_serverless("00fEXAMPLE", tmp_path, now="2026-08-04T01:00:00Z")
        assert second.collected_at == first.collected_at
        assert len(emrs.calls) == before

    def test_the_recollect_command_is_the_verb_the_cli_really_has(self, tmp_path, monkeypatch):
        """`collect_command` cego deixa `resume()` sem saida: o case sabe que
        falta o artefato e nao sabe como obte-lo."""
        _, entry, _ = self._collect(tmp_path, monkeypatch)
        assert entry.collect_command == (
            "sparkforge collect emr-serverless --application-id 00fEXAMPLE"
        )


class FakeEmrContainersClient:
    """DUAS operacoes, em contraste deliberado com `FakeEmrServerlessClient`
    (uma) e `FakeEmrClient` (seis): `DescribeVirtualCluster` e `DescribeJobRun`
    moram em APIs separadas e o coletor precisa das duas para montar o
    arquivo autocontido que o extrator le."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def describe_virtual_cluster(self, **kwargs):
        self.calls.append(("describe_virtual_cluster", kwargs))
        return {
            "virtualCluster": {
                "id": kwargs["id"],
                "name": "meu-cluster",
                "state": "RUNNING",
                "containerProvider": {
                    "type": "EKS",
                    "id": "meu-cluster-eks",
                    "info": {"eksInfo": {"namespace": "spark-jobs"}},
                },
            }
        }

    def describe_job_run(self, **kwargs):
        self.calls.append(("describe_job_run", kwargs))
        return {
            "jobRun": {
                "id": kwargs["id"],
                "name": "etl-diario",
                "virtualClusterId": kwargs["virtualClusterId"],
                "state": "COMPLETED",
                "releaseLabel": "emr-7.5.0-latest",
            }
        }


class TestCollectEmrEks:
    def _collect(self, tmp_path, monkeypatch, now="2026-08-31T00:00:00Z"):
        emrc = FakeEmrContainersClient()
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(**{"emr-containers": emrc})
        )
        entry = aws.collect_emr_eks("0abc", "0run", tmp_path, now=now)
        return emrc, entry, json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))

    def test_collect_emr_eks_grava_as_duas_respostas_num_arquivo(self, tmp_path, monkeypatch):
        emrc, entry, gravado = self._collect(tmp_path, monkeypatch)
        assert set(gravado) == {"virtualCluster", "jobRun"}
        assert gravado["jobRun"]["id"] == "0run"
        assert gravado["virtualCluster"]["state"] == "RUNNING"
        assert entry.path == ".sparkforge/artifacts/emr_eks/0abc_0run.json"
        assert emrc.calls == [
            ("describe_virtual_cluster", {"id": "0abc"}),
            ("describe_job_run", {"id": "0run", "virtualClusterId": "0abc"}),
        ]

    def test_the_written_artifact_is_readable_by_the_extractor(self, tmp_path, monkeypatch):
        """O contrato entre coletor e extrator, provado ponta a ponta: se o
        shape divergir, este teste fica vermelho."""
        from sparkforge.facts.emr_eks import extract_emr_eks_path

        _, entry, _ = self._collect(tmp_path, monkeypatch)
        facts = extract_emr_eks_path(tmp_path / entry.path, repo_root=tmp_path)
        kinds = {f.kind for f in facts}
        assert "emrc.unresolved" not in kinds
        assert {"emrc.virtual_cluster", "emrc.job_run"} <= kinds

    def test_offline_hit_does_not_touch_boto3(self, tmp_path, monkeypatch):
        emrc, first, _ = self._collect(tmp_path, monkeypatch)
        before = len(emrc.calls)
        monkeypatch.setattr(
            aws, "require_boto3", lambda: FakeBoto3(**{"emr-containers": emrc})
        )
        second = aws.collect_emr_eks("0abc", "0run", tmp_path, now="2026-08-31T01:00:00Z")
        assert second.collected_at == first.collected_at
        assert len(emrc.calls) == before


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


class TestEventLogListingIsRobust:
    """A AWS documenta `--spark-event-logs-path` e o backup a cada 30s, mas nao
    documenta a convencao de nome nem o layout de objetos por job run. Por isso o
    coletor lista em vez de construir chave, e nao para na primeira pagina."""

    def _client(self, pages, bodies):
        class _Body:
            def __init__(self, data):
                self._data = data

            def read(self):
                return self._data

        class _S3:
            def __init__(self):
                self.calls = []

            def list_objects_v2(self, **kwargs):
                self.calls.append(kwargs)
                return pages.pop(0) if pages else {"Contents": []}

            def get_object(self, Bucket, Key):  # noqa: N803 - assinatura boto3
                return {"Body": _Body(bodies[Key])}

        return _S3()

    def test_pagination_is_followed_so_a_long_log_is_not_truncated(self, monkeypatch, tmp_path):
        from sparkforge.collect import aws

        pages = [
            {"Contents": [{"Key": "p/jr/1"}], "IsTruncated": True, "NextContinuationToken": "t"},
            {"Contents": [{"Key": "p/jr/2"}], "IsTruncated": False},
        ]
        client = self._client(pages, {"p/jr/1": b'{"Event":"A"}', "p/jr/2": b'{"Event":"B"}'})
        fake = type("B", (), {"client": lambda *_: client})()
        monkeypatch.setattr(aws, "require_boto3", lambda: fake)
        aws.collect_event_log("jr", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z")
        written = (tmp_path / aws.event_log_path("jr")).read_text(encoding="utf-8")
        assert '{"Event":"A"}' in written and '{"Event":"B"}' in written

    def test_falls_back_to_parent_prefix_when_layout_differs(self, monkeypatch, tmp_path):
        """Layout diferente do esperado degrada para 'achei por outro caminho',
        nao para 'nenhum objeto' com o log existindo."""
        from sparkforge.collect import aws

        pages = [
            {"Contents": [], "IsTruncated": False},
            {"Contents": [{"Key": "p/outro-layout-jr-xyz.jsonl"}], "IsTruncated": False},
        ]
        client = self._client(pages, {"p/outro-layout-jr-xyz.jsonl": b'{"Event":"C"}'})
        fake = type("B", (), {"client": lambda *_: client})()
        monkeypatch.setattr(aws, "require_boto3", lambda: fake)
        aws.collect_event_log("jr", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z")
        assert '{"Event":"C"}' in (tmp_path / aws.event_log_path("jr")).read_text(encoding="utf-8")

    def test_error_names_the_manual_alternative(self, monkeypatch, tmp_path):
        from sparkforge.collect import aws

        client = self._client([], {})
        fake = type("B", (), {"client": lambda *_: client})()
        monkeypatch.setattr(aws, "require_boto3", lambda: fake)
        with pytest.raises(aws.CollectionFailed, match="register_artifact"):
            aws.collect_event_log(
                "jr", tmp_path, bucket="b", prefix="p", now="2026-07-30T00:00:00Z"
            )


class TestLakeFormationTrapIsNamed:
    """AccessDenied numa metadata table quase nunca e IAM: o Athena recusa
    `$files`/`$snapshots` em tabela com filtro de linha/celula do Lake Formation.
    Mandar revisar IAM manda procurar no lugar errado."""

    def test_iceberg_sections_are_documented_in_the_module(self):
        import inspect

        from sparkforge.collect import aws

        source = inspect.getsource(aws)
        assert "Lake Formation" in source
        assert "AccessDeniedException" in source

    def test_access_denied_error_points_at_lake_formation(self, monkeypatch, tmp_path):
        from sparkforge.collect import aws

        class _Athena:
            def start_query_execution(self, **_):
                return {"QueryExecutionId": "q1"}

            def get_query_execution(self, **_):
                return {
                    "QueryExecution": {
                        "Status": {
                            "State": "FAILED",
                            "StateChangeReason": "AccessDeniedException: not authorized",
                        }
                    }
                }

        monkeypatch.setattr(
            aws, "require_boto3", lambda: type("B", (), {"client": lambda *_: _Athena()})()
        )
        with pytest.raises(aws.CollectionFailed, match="Lake Formation"):
            aws.collect_iceberg_metadata(
                "db.tbl",
                tmp_path,
                workgroup="wg",
                output_location="s3://o/",
                now="2026-07-30T00:00:00Z",
            )
