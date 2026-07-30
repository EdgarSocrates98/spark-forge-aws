import io
import json

import pytest

from sparkforge.adapters.cli import main
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
