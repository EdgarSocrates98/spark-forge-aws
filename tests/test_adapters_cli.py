import io
import json

import pytest

from sparkforge.adapters.cli import main
from sparkforge.adapters.tools import call_tool
from sparkforge.collect import aws as collect_aws

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


def run(args, capsys):
    code = main(args)
    return code, capsys.readouterr().out


class TestAnalyze:
    def test_writes_facts_json(self, repo, capsys):
        out = repo / "facts.json"
        code, _ = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "pyspark.partitioning" for f in facts)

    def test_prints_summary_to_stdout(self, repo, capsys):
        _, output = run(["analyze", "pyspark", "--path", str(repo / "lib")], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "by_kind" in payload

    def test_filter_by_kind(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--kind", "pyspark.partitioning"],
            capsys,
        )
        assert set(json.loads(output)["by_kind"]) == {"pyspark.partitioning"}

    def test_limit_reports_truncation(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--limit", "1"], capsys
        )
        payload = json.loads(output)
        assert payload["returned_count"] == 1
        assert payload["filters_applied"]["limit"] == 1


CATALOG_DUMP = json.dumps(
    {
        "tables": [
            {
                "name": "db.eventos",
                "storage_format": "parquet",
                "partition_keys": [{"name": "dt", "type": "string"}],
                "columns": [
                    {"name": "cliente_id", "type": "bigint"},
                    {"name": "dt", "type": "string"},
                ],
            }
        ]
    }
)


class TestAnalyzeCatalogSchema:
    def _dump(self, repo):
        catalog_dir = repo / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        return catalog_dir

    def test_writes_facts_json(self, repo, capsys):
        catalog_dir = self._dump(repo)
        out = repo / "catalog_facts.json"
        code, _ = run(
            ["analyze", "catalog-schema", "--path", str(catalog_dir), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "catalog.table_schema" for f in facts)

    def test_prints_summary_to_stdout(self, repo, capsys):
        catalog_dir = self._dump(repo)
        _, output = run(["analyze", "catalog-schema", "--path", str(catalog_dir)], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "by_kind" in payload

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(
            ["analyze", "catalog-schema", "--path", str(repo / "nope")], capsys
        )
        assert code == 2


class TestFuse:
    def _sql_facts(self, repo, capsys):
        lib = repo / "sql"
        lib.mkdir()
        (lib / "q.sql").write_text("SELECT * FROM db.eventos\n", encoding="utf-8")
        # Nao ha `analyze sql` na CLI (extrator de SQL nao esta cabeado, mesmo
        # gap dos outros extratores da Fase 1) -- gera o arquivo de facts
        # direto pela API Python, como um coletor externo faria.
        from sparkforge.facts.sql_literal import extract_sql_path

        facts = extract_sql_path(lib / "q.sql", repo_root=lib)
        path = repo / "sql_facts.json"
        path.write_text(
            json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _catalog_facts(self, repo, capsys):
        catalog_dir = repo / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        out = repo / "catalog_facts.json"
        run(["analyze", "catalog-schema", "--path", str(catalog_dir), "--out", str(out)], capsys)
        return out

    def test_combines_two_sources_and_produces_enriched_facts(self, repo, capsys):
        sql_path = self._sql_facts(repo, capsys)
        catalog_path = self._catalog_facts(repo, capsys)
        out = repo / "fused.json"
        code, output = run(
            [
                "fuse",
                "--facts", str(sql_path),
                "--facts", str(catalog_path),
                "--out", str(out),
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["summary"]["measures"]["enriched_count"] == 1
        fused = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "sql.projection.enriched" for f in fused)

    def test_fused_facts_feed_judge_directly(self, repo, capsys):
        sql_path = self._sql_facts(repo, capsys)
        catalog_path = self._catalog_facts(repo, capsys)
        fused_path = repo / "fused.json"
        run(
            [
                "fuse",
                "--facts", str(sql_path),
                "--facts", str(catalog_path),
                "--out", str(fused_path),
            ],
            capsys,
        )
        _, output = run(
            ["judge", "--facts", str(fused_path), "--athena", "*"], capsys
        )
        payload = json.loads(output)
        assert "SF-ATH-001" in {f["rule_id"] for f in payload["items"]}

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        code, _ = run(["fuse", "--facts", str(repo / "nope.json")], capsys)
        assert code == 2


class TestJudge:
    def _facts(self, repo, capsys):
        path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(path)], capsys)
        return path

    def test_produces_sf_py_005(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        out = repo / "findings.json"
        code, _ = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--out", str(out)], capsys
        )
        assert code == 0
        assert [f["rule_id"] for f in json.loads(out.read_text(encoding="utf-8"))] == ["SF-PY-005"]

    def test_severity_filter(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--severity", "P4"], capsys
        )
        assert json.loads(output)["returned_count"] == 0

    def test_reports_skipped_rules_with_reason(self, repo, capsys):
        facts_path = self._facts(repo, capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--show-skipped"], capsys
        )
        payload = json.loads(output)
        assert payload["skipped"]
        assert {"requires_facts", "runtime_scope"} & {s["reason"] for s in payload["skipped"]}


TF_WITH_RETRIES = '''resource "aws_glue_job" "etl" {
  name         = "etl"
  glue_version = "5.0"
  max_retries  = 2

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://b/logs/"
  }
}
'''

APPEND_WRITE = 'df.write.mode("append").parquet("s3://b/p")\n'


class TestJudgeCombinesFactsFromSeveralExtractors:
    """`SF-GLUE-004` correlaciona `tf.attribute` (max_retries) com
    `pyspark.write` (mode append) -- metade da evidencia vem do Terraform,
    metade do codigo. Com `judge --facts` aceitando um unico arquivo, avaliar
    essa regra exigia o operador concatenar dois arrays JSON na mao; quem nao
    fizesse isso simplesmente nunca via a regra disparar. `fuse --facts` ja e
    repetivel pela mesma razao."""

    def _tf_facts(self, repo, capsys):
        tf_dir = repo / "infra"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(TF_WITH_RETRIES, encoding="utf-8")
        out = repo / "tf_facts.json"
        run(["analyze", "terraform", "--path", str(tf_dir), "--out", str(out)], capsys)
        return out

    def _py_facts(self, repo, capsys):
        lib = repo / "job"
        lib.mkdir()
        (lib / "w.py").write_text(APPEND_WRITE, encoding="utf-8")
        out = repo / "py_facts.json"
        run(["analyze", "pyspark", "--path", str(lib), "--out", str(out)], capsys)
        return out

    def test_repeated_facts_flag_lets_sf_glue_004_fire(self, repo, capsys):
        tf_path = self._tf_facts(repo, capsys)
        py_path = self._py_facts(repo, capsys)
        code, output = run(
            [
                "judge",
                "--facts", str(tf_path),
                "--facts", str(py_path),
                "--glue", "5.0",
            ],
            capsys,
        )
        assert code == 0
        assert "SF-GLUE-004" in {f["rule_id"] for f in json.loads(output)["items"]}

    def test_each_file_alone_never_fires_the_correlated_rule(self, repo, capsys):
        for path in (self._tf_facts(repo, capsys), self._py_facts(repo, capsys)):
            _, output = run(["judge", "--facts", str(path), "--glue", "5.0"], capsys)
            assert "SF-GLUE-004" not in {f["rule_id"] for f in json.loads(output)["items"]}

    def test_single_file_invocation_is_unchanged(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(["judge", "--facts", str(facts_path), "--glue", "5.0"], capsys)
        assert [f["rule_id"] for f in json.loads(output)["items"]] == ["SF-PY-005"]

    def test_overlapping_files_do_not_duplicate_evidence(self, repo, capsys):
        """O mesmo arquivo duas vezes nao pode virar duas evidencias do mesmo
        fact: evidencia repetida faz um achado parecer duas vezes mais
        sustentado do que e."""
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--facts", str(facts_path), "--glue", "5.0"],
            capsys,
        )
        items = json.loads(output)["items"]
        assert [f["rule_id"] for f in items] == ["SF-PY-005"]
        assert len(items[0]["evidence"]) == len(set(items[0]["evidence"]))


class TestCaseLifecycle:
    def _open(self, repo, capsys):
        return run(
            ["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", "2026-07-30T00:00:00Z", "--glue", "5.0"],
            capsys,
        )

    def test_open_then_get(self, repo, capsys):
        assert self._open(repo, capsys)[0] == 0
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["case_id"] == "c1"

    def test_next_step_after_open(self, repo, capsys):
        self._open(repo, capsys)
        _, output = run(["next-step", "--repo", str(repo)], capsys)
        assert json.loads(output)["recommended_skill"]

    def test_handoff_writes_markdown(self, repo, capsys):
        self._open(repo, capsys)
        code, _ = run(["handoff", "--repo", str(repo)], capsys)
        assert code == 0
        assert (repo / ".sparkforge" / "handoff.md").is_file()


class TestErrorsAreActionable:
    def test_missing_case_names_the_command_that_fixes_it(self, repo, capsys):
        assert main(["case", "get", "--repo", str(repo)]) == 2
        assert "sparkforge case open" in capsys.readouterr().err

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        assert main(["judge", "--facts", str(repo / "nope.json"), "--glue", "5.0"]) == 2
        assert "sparkforge analyze pyspark" in capsys.readouterr().err


class TestRuntimeAndRules:
    def test_runtime_detect_reports_matrix(self, capsys):
        _, output = run(["runtime", "detect", "--glue", "5.0"], capsys)
        payload = json.loads(output)
        assert payload["spark"] == "3.5.4"
        assert payload["iceberg"] == "1.7.1"

    def test_rules_lookup_by_id_returns_full_rule(self, capsys):
        _, output = run(["rules", "lookup", "--id", "SF-PY-005"], capsys)
        rule = json.loads(output)["rules"][0]
        assert rule["id"] == "SF-PY-005"
        assert rule["sources"]
        assert rule["validation"]

    def test_rules_lookup_by_category(self, capsys):
        _, output = run(["rules", "lookup", "--category", "athena"], capsys)
        assert json.loads(output)["total_count"] == 5

    def test_validate_rejects_unbacked_gain(self, tmp_path, capsys):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40% do runtime", "benchmark_ref": "",
        }
        path = tmp_path / "f.json"
        path.write_text(json.dumps([payload]), encoding="utf-8")
        assert main(["validate", "--findings", str(path)]) == 1
        assert "benchmark_ref" in capsys.readouterr().err


class _FakeS3Client:
    def __init__(self):
        self.calls = []

    def list_objects_v2(self, **kwargs):
        self.calls.append(("list_objects_v2", kwargs))
        return {"Contents": [{"Key": f"{kwargs['Prefix']}part-00000"}]}

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))
        return {"Body": io.BytesIO(b'{"Event":"SparkListenerJobStart"}\n')}


class _FakeBoto3:
    def __init__(self, **clients):
        self._clients = clients

    def client(self, name, **kwargs):
        return self._clients[name]


class TestCollect:
    def test_event_log_writes_artifact_and_prints_manifest_entry(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))

        code, output = run(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_1",
                "--bucket", "my-bucket",
                "--prefix", "spark-logs",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["kind"] == "event_log"
        assert payload["cache_hit"] is False
        assert (repo / payload["path"]).is_file()

    def test_event_log_second_call_is_a_cache_hit(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))
        args = [
            "collect", "event-log",
            "--repo", str(repo),
            "--job-run", "jr_2",
            "--bucket", "b",
            "--prefix", "p",
            "--now", "2026-07-30T00:00:00Z",
        ]
        run(args, capsys)
        args[-1] = "2026-07-30T01:00:00Z"
        code, output = run(args, capsys)
        assert code == 0
        assert json.loads(output)["cache_hit"] is True

    def test_missing_boto3_names_pip_install_and_manual_path(self, repo, capsys, monkeypatch):
        from sparkforge.collect.base import CollectorUnavailable

        def boom():
            raise CollectorUnavailable(
                "boto3 nao disponivel. Instale com `pip install 'sparkforge-aws[aws]'` "
                "para usar coletores AWS, ou colete o artefato manualmente (AWS CLI ou "
                "console) e registre-o com `sparkforge.collect.register_artifact`."
            )

        monkeypatch.setattr(collect_aws, "require_boto3", boom)
        code = main(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_3",
                "--bucket", "b",
                "--prefix", "p",
                "--now", "2026-07-30T00:00:00Z",
            ]
        )
        assert code == 2
        err = capsys.readouterr().err
        assert "pip install 'sparkforge-aws[aws]'" in err
        assert "Alternativa manual" in err
        assert "jr_3.jsonl" in err

    def test_verify_reports_missing_artifact_with_recollect_command(self, repo, capsys):
        from sparkforge.collect.base import ArtifactEntry, register_artifact

        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_gone.jsonl",
            sha256="a" * 64,
            source="s3://bucket/prefix/jr_gone/",
            collect_command="sparkforge collect event-log --job-run jr_gone",
            collected_at="2026-07-29T00:00:00Z",
        )
        register_artifact(entry, repo)

        code, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["missing_count"] == 1
        assert payload["artifacts"][0]["present"] is False
        assert payload["artifacts"][0]["collect_command"] == entry.collect_command

    def test_verify_reports_hash_mismatch_after_local_corruption(self, repo, capsys, monkeypatch):
        s3 = _FakeS3Client()
        monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3(s3=s3))
        run(
            [
                "collect", "event-log",
                "--repo", str(repo),
                "--job-run", "jr_corrupt",
                "--bucket", "b",
                "--prefix", "p",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        target = repo / ".sparkforge" / "artifacts" / "eventlog" / "jr_corrupt.jsonl"
        target.write_bytes(b"corrupted")

        code, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["mismatched_count"] == 1
        assert payload["artifacts"][0]["present"] is True
        assert payload["artifacts"][0]["hash_matches"] is False


EVENT_LOG_LINE = json.dumps({"Event": "SparkListenerApplicationStart"}) + "\n"

TERRAFORM_SOURCE = (
    'resource "aws_glue_job" "etl" {\n'
    '  glue_version = "5.0"\n'
    '  worker_type = "G.1X"\n'
    "  number_of_workers = 10\n"
    "}\n"
)

ICEBERG_DUMP = json.dumps(
    {
        "table": "db.tbl",
        "files": [
            {"file_path": "s3://b/f1.parquet", "file_size_in_bytes": 1024, "record_count": 10}
        ],
    }
)

SQL_TEXT = "SELECT a, b FROM db.eventos WHERE dt = '2026-01-01'\n"

PYSPARK_SQL_SOURCE = 'spark.sql("SELECT a FROM db.eventos")\n'

ATHENA_WORKGROUP_DUMP = json.dumps(
    {
        "workgroups": [
            {
                "name": "primary",
                "engine_version": {
                    "effective_engine_version": "Athena engine version 2",
                    "selected_engine_version": "AUTO",
                },
                "state": "ENABLED",
                "bytes_scanned_cutoff": 1099511627776,
            }
        ]
    }
)


class TestAnalyzeEventLog:
    def test_prints_summary_and_reports_unresolved(self, repo, capsys):
        log_path = repo / "log.jsonl"
        log_path.write_text(EVENT_LOG_LINE, encoding="utf-8")
        code, output = run(["analyze", "event-log", "--path", str(log_path)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert payload["unresolved"] == 0
        assert payload["unresolved_at"] == []

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "event-log", "--path", str(repo / "nope.jsonl")], capsys)
        assert code == 2


class TestAnalyzeTerraform:
    def test_writes_facts_json(self, repo, capsys):
        tf_path = repo / "main.tf"
        tf_path.write_text(TERRAFORM_SOURCE, encoding="utf-8")
        out = repo / "tf_facts.json"
        code, _ = run(
            ["analyze", "terraform", "--path", str(tf_path), "--out", str(out)], capsys
        )
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "tf.resource" for f in facts)

    def test_directory_is_accepted(self, repo, capsys):
        tf_dir = repo / "infra"
        tf_dir.mkdir()
        (tf_dir / "main.tf").write_text(TERRAFORM_SOURCE, encoding="utf-8")
        _, output = run(["analyze", "terraform", "--path", str(tf_dir)], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert payload["unresolved"] == 0


PLAN_TEXT = (
    "== Physical Plan ==\n"
    "* Project (2)\n"
    "+- Scan parquet analytics.eventos (1)\n"
    "\n"
    "\n"
    "(1) Scan parquet analytics.eventos\n"
    "Output [3]: [cliente_id#10, valor#11, dt#12]\n"
    "Batched: true\n"
    "Location: InMemoryFileIndex [s3://lake/analytics/eventos]\n"
    "ReadSchema: struct<cliente_id:bigint,valor:double>\n"
    "\n"
    "(2) Project [codegen id : 1]\n"
    "Output [1]: [cliente_id#10]\n"
    "Input [3]: [cliente_id#10, valor#11, dt#12]\n"
)


class TestAnalyzePlan:
    def test_writes_facts_json(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        out = repo / "plan_facts.json"
        code, _ = run(["analyze", "plan", "--path", str(plan_path), "--out", str(out)], capsys)
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "plan.file_scan" for f in facts)
        assert any(f["kind"] == "plan.analyzed" for f in facts)

    def test_prints_summary_and_reports_unresolved(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        code, output = run(["analyze", "plan", "--path", str(plan_path)], capsys)
        assert code == 0
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "unresolved" in payload
        assert "unresolved_at" in payload

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "plan", "--path", str(repo / "nope.txt")], capsys)
        assert code == 2

    def test_mcp_tool_matches_the_cli(self, repo, capsys):
        plan_path = repo / "plan.txt"
        plan_path.write_text(PLAN_TEXT, encoding="utf-8")
        _, output = run(["analyze", "plan", "--path", str(plan_path), "--limit", "50"], capsys)
        from_cli = json.loads(output)
        from_mcp = call_tool("sparkforge_analyze_plan", {"path": str(plan_path)})
        assert from_cli["items"] == from_mcp["items"]


class TestAnalyzeIceberg:
    def test_prints_summary(self, repo, capsys):
        ice_path = repo / "iceberg.json"
        ice_path.write_text(ICEBERG_DUMP, encoding="utf-8")
        _, output = run(["analyze", "iceberg", "--path", str(ice_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["iceberg.files_summary"] == 1
        assert payload["unresolved"] == 0


class TestAnalyzeSql:
    def test_path_mode(self, repo, capsys):
        sql_path = repo / "q.sql"
        sql_path.write_text(SQL_TEXT, encoding="utf-8")
        _, output = run(["analyze", "sql", "--path", str(sql_path)], capsys)
        payload = json.loads(output)
        assert "sql.projection" in payload["by_kind"]

    def test_from_pyspark_mode(self, repo, capsys):
        py_path = repo / "q.py"
        py_path.write_text(PYSPARK_SQL_SOURCE, encoding="utf-8")
        _, output = run(["analyze", "sql", "--from-pyspark", str(py_path)], capsys)
        payload = json.loads(output)
        assert "sql.projection" in payload["by_kind"]

    def test_neither_path_nor_from_pyspark_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "sql"], capsys)
        assert code == 2


class TestAnalyzeAthenaWorkgroup:
    def test_prints_summary(self, repo, capsys):
        wg_path = repo / "wg.json"
        wg_path.write_text(ATHENA_WORKGROUP_DUMP, encoding="utf-8")
        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["athena.workgroup"] == 1
        assert payload["unresolved"] == 0

    def test_unparseable_engine_version_is_reported_as_unresolved_not_fabricated(
        self, repo, capsys
    ):
        dump = json.dumps(
            {
                "workgroups": [
                    {"name": "primary", "engine_version": {"effective_engine_version": "AUTO"}}
                ]
            }
        )
        wg_path = repo / "wg.json"
        wg_path.write_text(dump, encoding="utf-8")
        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("athena.workgroup", 0) == 0
        assert payload["unresolved"] == 1
        assert payload["unresolved_at"][0]["reason"] == "unparseable_engine_version"


class TestAnalyzeEmrCluster:
    _DUMP = json.dumps(
        {
            "Cluster": {
                "Id": "j-1EXAMPLE",
                "ReleaseLabel": "emr-7.5.0",
                "InstanceCollectionType": "INSTANCE_GROUP",
                "LogUri": "s3://bucket/elasticmapreduce/",
                "AutoTerminate": False,
                "Status": {"State": "RUNNING"},
            },
            "InstanceGroups": [
                {
                    "Id": "ig-TASK",
                    "InstanceGroupType": "TASK",
                    "Market": "SPOT",
                    "InstanceType": "r5.xlarge",
                    "RequestedInstanceCount": 4,
                }
            ],
        }
    )

    def test_prints_summary(self, repo, capsys):
        dump = repo / "cluster.json"
        dump.write_text(self._DUMP, encoding="utf-8")
        _, output = run(["analyze", "emr-cluster", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"]["emr.instance_capacity"] == 1
        assert payload["unresolved"] == 0

    def test_dump_without_instance_lists_reports_unresolved_not_zero_capacity(
        self, repo, capsys
    ):
        """Pelo verbo, a mesma disciplina do extrator: lista de instancias nao
        coletada aparece como ponto cego, nao como cluster sem capacidade."""
        dump = repo / "cluster.json"
        dump.write_text(json.dumps({"Cluster": {"Id": "j-1", "ReleaseLabel": "emr-7.5.0"}}))
        _, output = run(["analyze", "emr-cluster", "--path", str(dump)], capsys)
        payload = json.loads(output)
        assert payload["by_kind"].get("emr.instance_capacity", 0) == 0
        assert payload["unresolved"] == 1
        assert payload["unresolved_at"][0]["reason"] == "missing_instance_model"

    def test_missing_path_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "emr-cluster", "--path", str(repo / "nope.json")], capsys)
        assert code == 2


class TestAnalyzeCallGraph:
    def test_derives_from_pyspark_facts(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys
        )
        _, output = run(["analyze", "call-graph", "--facts", str(facts_path)], capsys)
        payload = json.loads(output)
        assert "callgraph.summary" in payload["by_kind"]
        assert "unresolved" not in payload

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        code, _ = run(["analyze", "call-graph", "--facts", str(repo / "nope.json")], capsys)
        assert code == 2


class TestCollectAthenaWorkgroup:
    def test_writes_artifact_and_registers_manifest(self, repo, capsys, monkeypatch):
        class _FakeAthenaWorkgroupClient:
            def get_work_group(self, WorkGroup):  # noqa: N803 - assinatura boto3
                return {
                    "WorkGroup": {
                        "Name": WorkGroup,
                        "State": "ENABLED",
                        "Configuration": {
                            "EngineVersion": {
                                "EffectiveEngineVersion": "Athena engine version 2",
                                "SelectedEngineVersion": "AUTO",
                            },
                            "BytesScannedCutoffPerQuery": 100,
                            "ResultConfiguration": {"OutputLocation": "s3://b/results/"},
                        },
                    }
                }

        monkeypatch.setattr(
            collect_aws,
            "require_boto3",
            lambda: _FakeBoto3(athena=_FakeAthenaWorkgroupClient()),
        )
        code, output = run(
            [
                "collect", "athena-workgroup",
                "--repo", str(repo),
                "--workgroup", "primary",
                "--now", "2026-07-30T00:00:00Z",
            ],
            capsys,
        )
        assert code == 0
        payload = json.loads(output)
        assert payload["kind"] == "athena_workgroup"
        assert payload["cache_hit"] is False
        written = json.loads((repo / payload["path"]).read_text(encoding="utf-8"))
        assert written["workgroups"][0]["engine_version"]["effective_engine_version"] == (
            "Athena engine version 2"
        )


class TestCliMcpEquivalence:
    """A garantia central da Fase 1: CLI e MCP chamam a mesma funcao de
    `_core.py`, entao para o mesmo input o payload precisa ser identico --
    nunca um subconjunto de campos, nunca uma serializacao diferente. Aqui
    comparado byte-a-byte (via round-trip JSON, para casar tipos) para pelo
    menos tres das capacidades novas desta fase."""

    def test_analyze_terraform_matches(self, repo, capsys):
        tf_path = repo / "main.tf"
        tf_path.write_text(TERRAFORM_SOURCE, encoding="utf-8")

        _, output = run(["analyze", "terraform", "--path", str(tf_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_terraform", {"path": str(tf_path)})
        assert cli_payload == mcp_payload

    def test_analyze_athena_workgroup_matches(self, repo, capsys):
        wg_path = repo / "wg.json"
        wg_path.write_text(ATHENA_WORKGROUP_DUMP, encoding="utf-8")

        _, output = run(["analyze", "athena-workgroup", "--path", str(wg_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_athena_workgroup", {"path": str(wg_path)})
        assert cli_payload == mcp_payload

    def test_analyze_sql_matches(self, repo, capsys):
        sql_path = repo / "q.sql"
        sql_path.write_text(SQL_TEXT, encoding="utf-8")

        _, output = run(["analyze", "sql", "--path", str(sql_path)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_analyze_sql", {"path": str(sql_path)})
        assert cli_payload == mcp_payload

    def test_rules_lookup_matches(self, repo, capsys):
        _, output = run(["rules", "lookup", "--id", "SF-ENV-001"], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_rules_lookup", {"id": ["SF-ENV-001"]})
        assert cli_payload == mcp_payload
        # Trava especifica da Task 5: os dois caminhos precisam concordar tambem
        # no campo novo `knowledge_refs`, nao so no restante do payload.
        assert cli_payload["rules"][0]["knowledge_refs"]

    def test_playbook_matches(self, repo, capsys):
        """Omitir este teste ja custou uma rodada de revisao na Fase 3a --
        `playbook` e capacidade nova da Task 5 e precisa da mesma trava."""
        _, output = run(["playbook", "glue-infra-reviewer", "--repo", str(repo)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool(
            "sparkforge_playbook", {"coordinator": "glue-infra-reviewer", "repo": str(repo)}
        )
        assert cli_payload == mcp_payload
        assert cli_payload["steps"][0]["executor"] == "sf-inventory"

    def test_playbook_unknown_coordinator_matches(self, repo, capsys):
        assert main(["playbook", "nao-existe", "--repo", str(repo)]) == 2
        cli_message = capsys.readouterr().err.strip()

        mcp_payload = call_tool(
            "sparkforge_playbook", {"coordinator": "nao-existe", "repo": str(repo)}
        )
        assert "error" in mcp_payload
        assert cli_message == mcp_payload["error"]

    def test_knowledge_path_matches(self, repo, capsys):
        _, output = run(["knowledge", "path", "--file", "glue/runtime-matrix.md"], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool(
            "sparkforge_knowledge_path", {"file": "glue/runtime-matrix.md"}
        )
        assert cli_payload == mcp_payload

    def test_collect_verify_matches(self, repo, capsys):
        from sparkforge.collect.base import ArtifactEntry, register_artifact

        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_x.jsonl",
            sha256="a" * 64,
            source="s3://bucket/prefix/jr_x/",
            collect_command="sparkforge collect event-log --job-run jr_x",
            collected_at="2026-07-29T00:00:00Z",
        )
        register_artifact(entry, repo)

        _, output = run(["collect", "verify", "--repo", str(repo)], capsys)
        cli_payload = json.loads(output)

        mcp_payload = call_tool("sparkforge_collect_verify", {"repo": str(repo)})
        assert cli_payload == mcp_payload


class TestEmrFlag:
    """`--emr` nos tres verbos que aceitam runtime, e a mesma flag no MCP.

    A divida era de superficie, nao de motor: `detect_runtime` sempre soube ler
    `emr_release` de qualquer fonte, e so `emr.cluster` a alimentava. Quem sabe
    a release e nao tem dump ficava sem caminho -- e o MCP ficaria sem caminho
    mesmo com a flag na CLI, o que recriaria a assimetria um nivel acima."""

    def test_runtime_detect_derives_the_matrix_from_the_flag(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "emr-7.5.0"], capsys)
        payload = json.loads(output)
        assert payload["emr"] == "7.5.0"
        assert payload["spark"] == "3.5.2-amzn-1"
        assert payload["iceberg"] == "1.6.1-amzn-1"

    def test_the_numeric_spelling_reaches_the_same_row(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "7.5.0"], capsys)
        assert json.loads(output)["spark"] == "3.5.2-amzn-1"

    def test_judge_reports_the_runtime_the_flag_declared(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)

        _, output = run(["judge", "--facts", str(facts_path), "--emr", "emr-6.15.0"], capsys)
        assert json.loads(output)["runtime"]["emr"] == "6.15.0"

    def test_case_open_stores_the_release(self, repo, capsys):
        run(
            ["case", "open", "--repo", str(repo), "--case-id", "c-emr",
             "--now", "2026-08-01T00:00:00Z", "--emr", "emr-7.5.0"],
            capsys,
        )
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["runtime"]["emr"] == "7.5.0"

    def test_cli_and_mcp_agree(self, capsys):
        _, output = run(["runtime", "detect", "--emr", "emr-7.5.0"], capsys)
        assert json.loads(output) == call_tool("sparkforge_runtime_detect", {"emr": "emr-7.5.0"})
