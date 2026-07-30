import json

import jsonschema
import pytest

from sparkforge.adapters.tools import TOOLS, call_tool

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


class TestToolSurface:
    def test_the_full_tool_surface_is_declared(self):
        """Fase 1: a superficie MCP cresceu para cobrir todo verbo da CLI --
        os 10 tools da Fase 0, mais catalog-schema/fuse/call-graph e os
        extratores sem verbo proprio (event-log, terraform, iceberg, sql,
        athena-workgroup), mais os seis coletores AWS. Um tool que sai desta
        lista sem querer e um capability reachable-por-CLI-mas-nao-por-MCP
        que `parity.yaml`/`test_capability_parity.py` deveriam pegar -- este
        teste falha primeiro, com um diff legivel."""
        assert set(TOOLS) == {
            "sparkforge_case_open",
            "sparkforge_case_get",
            "sparkforge_case_update",
            "sparkforge_next_step",
            "sparkforge_resume",
            "sparkforge_runtime_detect",
            "sparkforge_analyze_pyspark",
            "sparkforge_analyze_catalog_schema",
            "sparkforge_analyze_event_log",
            "sparkforge_analyze_terraform",
            "sparkforge_analyze_iceberg",
            "sparkforge_analyze_sql",
            "sparkforge_analyze_athena_workgroup",
            "sparkforge_analyze_call_graph",
            "sparkforge_fuse",
            "sparkforge_judge",
            "sparkforge_rules_lookup",
            "sparkforge_validate_output",
            "sparkforge_collect_event_log",
            "sparkforge_collect_glue_job",
            "sparkforge_collect_cloudwatch",
            "sparkforge_collect_iceberg_metadata",
            "sparkforge_collect_athena_workgroup",
            "sparkforge_collect_verify",
        }

    def test_every_tool_declares_an_output_schema(self):
        """`sparkforge_judge` pode devolver sucesso ou o shape de erro de
        fronteira (`facts_path` ausente), entao seu outputSchema usa `oneOf`
        em vez de um `type` plano na raiz -- ver TestOutputSchemasAreReal
        para a verificacao real de cada branch."""
        for name, spec in TOOLS.items():
            schema = spec["outputSchema"]
            assert schema.get("type") == "object" or "oneOf" in schema, name

    def test_every_tool_declares_annotations(self):
        for name, spec in TOOLS.items():
            for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                assert key in spec["annotations"], f"{name} sem {key}"

    def test_no_tool_is_destructive(self):
        assert all(s["annotations"]["destructiveHint"] is False for s in TOOLS.values())

    def test_only_collect_tools_are_open_world(self):
        """O nucleo determinístico e offline; os coletores AWS (`collect_*`,
        exceto `collect_verify`, que so le o manifesto local) sao as
        primeiras ferramentas deste projeto que tocam a rede de verdade.
        Antes da Fase 1 nenhum tool era openWorld -- agora a invariante
        precisa e "so collect_* (menos verify)", nao mais "nenhum"."""
        open_world = {n for n, s in TOOLS.items() if s["annotations"]["openWorldHint"] is True}
        assert open_world == {
            "sparkforge_collect_event_log",
            "sparkforge_collect_glue_job",
            "sparkforge_collect_cloudwatch",
            "sparkforge_collect_iceberg_metadata",
            "sparkforge_collect_athena_workgroup",
        }

    def test_every_open_world_tool_is_still_read_only(self):
        """openWorldHint e sobre tocar rede, nao sobre mutar estado: os
        coletores so leem da AWS (`get_object`, `get_job`, `get_metric_data`,
        `SELECT`/`get_work_group`), nunca escrevem do lado AWS."""
        for name, spec in TOOLS.items():
            if spec["annotations"]["openWorldHint"] is True:
                assert spec["annotations"]["readOnlyHint"] is True, name

    def test_only_case_writers_are_not_read_only(self):
        writers = {n for n, s in TOOLS.items() if not s["annotations"]["readOnlyHint"]}
        assert writers == {"sparkforge_case_open", "sparkforge_case_update"}

    def test_every_tool_has_a_description(self):
        for name, spec in TOOLS.items():
            assert len(spec["description"]) > 20, name


class TestCallTool:
    def test_analyze_returns_structured_content(self, repo):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        assert result["total_count"] >= 1
        assert result["by_kind"]["pyspark.partitioning"] == 1

    def test_judge_finds_sf_py_005(self, repo):
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        result = call_tool("sparkforge_judge", {"facts": facts["items"], "glue": "5.0"})
        assert [f["rule_id"] for f in result["items"]] == ["SF-PY-005"]

    def test_rules_lookup_returns_thresholds_and_sources(self):
        rule = call_tool("sparkforge_rules_lookup", {"id": ["SF-PY-007"]})["rules"][0]
        assert rule["threshold"] == {"run_length": 10}
        assert rule["sources"]

    def test_validate_output_rejects_unbacked_gain(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40%", "benchmark_ref": "",
        }
        result = call_tool("sparkforge_validate_output", {"finding": payload})
        assert result["valid"] is False
        assert "benchmark_ref" in result["errors"][0]

    def test_validate_output_accepts_a_clean_finding(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
        }
        assert call_tool("sparkforge_validate_output", {"finding": payload})["valid"] is True

    def test_case_open_then_next_step(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-07-30T00:00:00Z", "glue": "5.0"},
        )
        assert call_tool("sparkforge_next_step", {"repo": str(repo)})["recommended_skill"]

    def test_unknown_tool_raises_with_the_valid_names(self):
        with pytest.raises(KeyError, match="sparkforge_judge"):
            call_tool("sparkforge_nope", {})

    def test_error_result_carries_a_collect_command(self, repo):
        result = call_tool("sparkforge_judge", {"facts_path": str(repo / "nope.json")})
        assert "sparkforge analyze pyspark" in json.dumps(result)


class TestUnresolvedIsAlwaysReported:
    """Regra 7 do AGENT_PROTOCOL.md: no nao resolvido e ponto cego, nao ausencia
    de problema. Se a tool nao devolve a contagem, o protocolo exige do agente
    algo que a ferramenta nao fornece."""

    def _repo(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "a.py").write_text(
            "getattr(df, metodo)(1)\ndf.coalesce(1)\n", encoding="utf-8"
        )
        return lib

    def test_analyze_reports_unresolved_count(self, tmp_path):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(self._repo(tmp_path))})
        assert result["unresolved"] == 1

    def test_analyze_reports_where_each_blind_spot_is(self, tmp_path):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(self._repo(tmp_path))})
        spot = result["unresolved_at"][0]
        assert spot["reason"] == "getattr"
        assert spot["line"] == 1
        assert spot["file"].endswith("a.py")

    def test_filtering_by_kind_cannot_hide_the_blind_spot(self, tmp_path):
        """Filtrar por kind nao pode fazer o ponto cego sumir do relatorio."""
        result = call_tool(
            "sparkforge_analyze_pyspark",
            {"path": str(self._repo(tmp_path)), "kind": ["pyspark.partitioning"]},
        )
        assert result["by_kind"] == {"pyspark.partitioning": 1}
        assert result["unresolved"] == 1

    def test_clean_source_reports_zero_not_absent(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "a.py").write_text('df.select("a")\n', encoding="utf-8")
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
        assert result["unresolved"] == 0
        assert result["unresolved_at"] == []


class TestOutputSchemasAreReal:
    """Um outputSchema `{"type": "object"}` generico passa no teste e nao entrega
    nada: o cliente volta a adivinhar a forma, que e exatamente o que esta
    arquitetura existe para evitar."""

    def _branches(self, spec):
        """`sparkforge_judge` descreve sucesso e erro via `oneOf`; as demais
        ferramentas sao um schema plano. Normaliza os dois casos para uma
        lista de sub-schemas a inspecionar."""
        schema = spec["outputSchema"]
        return schema.get("oneOf") or [schema]

    def test_every_tool_declares_properties(self):
        for name, spec in TOOLS.items():
            for branch in self._branches(spec):
                assert branch.get("properties"), name

    def test_every_tool_declares_required_keys(self):
        for name, spec in TOOLS.items():
            for branch in self._branches(spec):
                assert branch.get("required"), name

    def test_no_tool_uses_a_bare_object_schema(self):
        for name, spec in TOOLS.items():
            schema = spec["outputSchema"]
            assert set(schema) > {"type"} or "oneOf" in schema, name


_CASE_OPEN_ARGS = {"case_id": "c1", "now": "2026-07-30T00:00:00Z", "glue": "5.0"}

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

_EVENT_LOG_LINE = json.dumps({"Event": "SparkListenerApplicationStart"}) + "\n"

_TERRAFORM_SOURCE = (
    'resource "aws_glue_job" "etl" {\n'
    '  glue_version = "5.0"\n'
    '  worker_type = "G.1X"\n'
    "  number_of_workers = 10\n"
    "}\n"
)

_ICEBERG_DUMP = json.dumps(
    {
        "table": "db.tbl",
        "files": [
            {"file_path": "s3://b/f1.parquet", "file_size_in_bytes": 1024, "record_count": 10}
        ],
    }
)

_SQL_TEXT = "SELECT a, b FROM db.eventos WHERE dt = '2026-01-01'\n"

_PYSPARK_SQL_SOURCE = 'spark.sql("SELECT a FROM db.eventos")\n'

_ATHENA_WORKGROUP_DUMP = json.dumps(
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


def _open_case(repo):
    call_tool("sparkforge_case_open", {"repo": str(repo), **_CASE_OPEN_ARGS})


def _write_job(repo):
    lib = repo / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return lib


def _write_facts_file(tmp_path):
    lib = _write_job(tmp_path)
    facts = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(facts["items"], ensure_ascii=False), encoding="utf-8")
    return path


class _FakeS3Client:
    def list_objects_v2(self, **kwargs):
        return {"Contents": [{"Key": f"{kwargs['Prefix']}part-00000"}]}

    def get_object(self, **kwargs):
        import io

        return {"Body": io.BytesIO(b'{"Event":"SparkListenerJobStart"}\n')}


class _FakeGlueClient:
    def get_job(self, **kwargs):
        return {"Job": {"Name": kwargs.get("JobName", "job"), "GlueVersion": "5.0"}}


class _FakeCloudWatchClient:
    def get_metric_data(self, **kwargs):
        return {"MetricDataResults": []}


class _FakeAthenaClient:
    def __init__(self):
        self._exec_id = 0

    def start_query_execution(self, **kwargs):
        self._exec_id += 1
        return {"QueryExecutionId": f"q{self._exec_id}"}

    def get_query_execution(self, **kwargs):
        return {"QueryExecution": {"Status": {"State": "SUCCEEDED"}}}

    def get_query_results(self, **kwargs):
        return {"ResultSet": {"Rows": []}}

    def get_work_group(self, **kwargs):
        return {
            "WorkGroup": {
                "Name": kwargs.get("WorkGroup", "primary"),
                "State": "ENABLED",
                "Configuration": {
                    "EngineVersion": {
                        "EffectiveEngineVersion": "Athena engine version 3",
                        "SelectedEngineVersion": "AUTO",
                    },
                    "BytesScannedCutoffPerQuery": 100,
                    "ResultConfiguration": {"OutputLocation": "s3://bucket/results/"},
                },
            }
        }


class _FakeBoto3ForCollect:
    def __init__(self):
        self._clients = {
            "s3": _FakeS3Client(),
            "glue": _FakeGlueClient(),
            "cloudwatch": _FakeCloudWatchClient(),
            "athena": _FakeAthenaClient(),
        }

    def client(self, name, **kwargs):
        return self._clients[name]


def _fake_collect_boto3(monkeypatch):
    """Injeta um client AWS falso para as ferramentas `collect_*` -- nunca toca
    rede nem credenciais de verdade, mesma convencao de `tests/test_collect_aws.py`."""
    from sparkforge.collect import aws as collect_aws

    monkeypatch.setattr(collect_aws, "require_boto3", lambda: _FakeBoto3ForCollect())


def _real_output_for(name, tmp_path, monkeypatch=None):
    """Chama `name` com argumentos realistas, criando qualquer estado
    (case, facts) de que a ferramenta dependa, e devolve o dict cru que um
    cliente MCP receberia como `structuredContent`."""
    if name == "sparkforge_case_open":
        return call_tool("sparkforge_case_open", {"repo": str(tmp_path), **_CASE_OPEN_ARGS})

    if name == "sparkforge_case_get":
        _open_case(tmp_path)
        return call_tool("sparkforge_case_get", {"repo": str(tmp_path)})

    if name == "sparkforge_case_update":
        _open_case(tmp_path)
        return call_tool(
            "sparkforge_case_update",
            {
                "repo": str(tmp_path),
                "phase": "facts",
                "gate": "baseline_captured",
                "gate_value": True,
                "skill": "analyze-spark-plan",
                "now": "2026-07-30T01:00:00Z",
                "outcome": "ok",
            },
        )

    if name == "sparkforge_next_step":
        _open_case(tmp_path)
        return call_tool("sparkforge_next_step", {"repo": str(tmp_path)})

    if name == "sparkforge_resume":
        _open_case(tmp_path)
        return call_tool(
            "sparkforge_resume", {"repo": str(tmp_path), "findings": [], "unresolved": 0}
        )

    if name == "sparkforge_runtime_detect":
        return call_tool("sparkforge_runtime_detect", {"glue": "5.0"})

    if name == "sparkforge_analyze_pyspark":
        lib = _write_job(tmp_path)
        return call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})

    if name == "sparkforge_judge":
        lib = _write_job(tmp_path)
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(lib)})
        return call_tool(
            "sparkforge_judge",
            {"facts": facts["items"], "glue": "5.0", "show_skipped": True},
        )

    if name == "sparkforge_rules_lookup":
        return call_tool("sparkforge_rules_lookup", {"id": ["SF-PY-007"]})

    if name == "sparkforge_validate_output":
        payload = {
            "rule_id": "SF-PY-005",
            "schema_version": 1,
            "title": "t",
            "severity": "P0",
            "confidence": "high",
            "status": "structural",
            "subject": {"type": "source_location"},
            "evidence": ["f_abc123"],
        }
        return call_tool("sparkforge_validate_output", {"finding": payload})

    if name == "sparkforge_analyze_catalog_schema":
        catalog_dir = tmp_path / "catalog"
        catalog_dir.mkdir()
        (catalog_dir / "dump.json").write_text(CATALOG_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_catalog_schema", {"path": str(catalog_dir)})

    if name == "sparkforge_analyze_event_log":
        log_path = tmp_path / "log.jsonl"
        log_path.write_text(_EVENT_LOG_LINE, encoding="utf-8")
        return call_tool("sparkforge_analyze_event_log", {"path": str(log_path)})

    if name == "sparkforge_analyze_terraform":
        tf_path = tmp_path / "main.tf"
        tf_path.write_text(_TERRAFORM_SOURCE, encoding="utf-8")
        return call_tool("sparkforge_analyze_terraform", {"path": str(tf_path)})

    if name == "sparkforge_analyze_iceberg":
        ice_path = tmp_path / "iceberg.json"
        ice_path.write_text(_ICEBERG_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_iceberg", {"path": str(ice_path)})

    if name == "sparkforge_analyze_sql":
        sql_path = tmp_path / "q.sql"
        sql_path.write_text(_SQL_TEXT, encoding="utf-8")
        return call_tool("sparkforge_analyze_sql", {"path": str(sql_path)})

    if name == "sparkforge_analyze_athena_workgroup":
        wg_path = tmp_path / "wg.json"
        wg_path.write_text(_ATHENA_WORKGROUP_DUMP, encoding="utf-8")
        return call_tool("sparkforge_analyze_athena_workgroup", {"path": str(wg_path)})

    if name == "sparkforge_analyze_call_graph":
        facts_path = _write_facts_file(tmp_path)
        return call_tool("sparkforge_analyze_call_graph", {"facts_path": str(facts_path)})

    if name == "sparkforge_fuse":
        facts_path = _write_facts_file(tmp_path)
        return call_tool("sparkforge_fuse", {"facts_paths": [str(facts_path)]})

    if name in (
        "sparkforge_collect_event_log",
        "sparkforge_collect_glue_job",
        "sparkforge_collect_cloudwatch",
        "sparkforge_collect_iceberg_metadata",
        "sparkforge_collect_athena_workgroup",
    ):
        assert monkeypatch is not None, f"{name} precisa de monkeypatch para o client AWS falso"
        _fake_collect_boto3(monkeypatch)
        args = {
            "sparkforge_collect_event_log": {
                "repo": str(tmp_path),
                "job_run_id": "jr_1",
                "bucket": "my-bucket",
                "prefix": "spark-logs",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_glue_job": {
                "repo": str(tmp_path),
                "job_name": "etl-job",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_cloudwatch": {
                "repo": str(tmp_path),
                "job_name": "etl-job",
                "job_run_id": "jr_1",
                "start": "2026-07-29T00:00:00Z",
                "end": "2026-07-30T00:00:00Z",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_iceberg_metadata": {
                "repo": str(tmp_path),
                "table": "db.tbl",
                "workgroup": "primary",
                "output_location": "s3://athena-results/",
                "now": "2026-07-30T00:00:00Z",
            },
            "sparkforge_collect_athena_workgroup": {
                "repo": str(tmp_path),
                "workgroup": "primary",
                "now": "2026-07-30T00:00:00Z",
            },
        }[name]
        return call_tool(name, args)

    if name == "sparkforge_collect_verify":
        return call_tool("sparkforge_collect_verify", {"repo": str(tmp_path)})

    raise AssertionError(f"sem construtor de argumentos reais para {name}")


class TestRealOutputValidatesAgainstItsOwnSchema:
    """O ponto do trabalho: sem isto, os schemas sao documentacao que pode
    apodrecer a qualquer refactor de `_core.py` sem que nenhum teste perceba."""

    @pytest.mark.parametrize("name", sorted(TOOLS))
    def test_real_output_matches_declared_schema(self, name, tmp_path, monkeypatch):
        result = _real_output_for(name, tmp_path, monkeypatch)
        jsonschema.validate(result, TOOLS[name]["outputSchema"])

    def test_judge_error_shape_also_matches_its_schema(self, tmp_path):
        """`facts_path` ausente e o outro branch do `oneOf` de sparkforge_judge:
        um dict de erro de fronteira, nunca uma excecao."""
        result = call_tool("sparkforge_judge", {"facts_path": str(tmp_path / "nope.json")})
        assert "error" in result
        jsonschema.validate(result, TOOLS["sparkforge_judge"]["outputSchema"])


class TestErrorShapesValidateToo:
    """`call_tool` converte AdapterError em `{"error", "exit_code"}` em vez de
    propagar excecao. Um schema so-de-sucesso e promessa falsa: o cliente que
    validar uma resposta de "case nao existe" recebe falha de validacao em cima
    de um erro que a tool ja tratou corretamente."""

    FAILABLE = (
        ("sparkforge_case_get", {"repo": "<tmp>"}),
        ("sparkforge_case_update", {"repo": "<tmp>", "phase": "diagnosis"}),
        ("sparkforge_next_step", {"repo": "<tmp>"}),
        ("sparkforge_resume", {"repo": "<tmp>"}),
        ("sparkforge_analyze_pyspark", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_catalog_schema", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_event_log", {"path": "<tmp>/inexistente.jsonl"}),
        ("sparkforge_analyze_terraform", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_iceberg", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_sql", {"path": "<tmp>/inexistente.sql"}),
        ("sparkforge_analyze_athena_workgroup", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_call_graph", {"facts_path": "<tmp>/nao-existe.json"}),
        ("sparkforge_fuse", {"facts_paths": ["<tmp>/nao-existe.json"]}),
        ("sparkforge_judge", {"facts_path": "<tmp>/nao-existe.json"}),
    )

    @staticmethod
    def _resolve(value, tmp_path):
        """Substitui `<tmp>` pelo tmp_path real, preservando listas -- `str(v)`
        num valor de lista (`facts_paths`) produziria `"['<tmp>/x.json']"`, uma
        string malformada em vez de uma lista real."""
        if isinstance(value, list):
            return [str(v).replace("<tmp>", str(tmp_path)) for v in value]
        return str(value).replace("<tmp>", str(tmp_path))

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_response_validates_against_its_own_schema(self, name, args, tmp_path):
        import jsonschema

        resolved = {k: self._resolve(v, tmp_path) for k, v in args.items()}
        result = call_tool(name, resolved)
        assert "error" in result, f"{name} deveria ter falhado neste input"
        jsonschema.validate(result, TOOLS[name]["outputSchema"])

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_message_is_actionable(self, name, args, tmp_path):
        resolved = {k: self._resolve(v, tmp_path) for k, v in args.items()}
        message = call_tool(name, resolved)["error"]
        assert "sparkforge" in message, f"{name}: erro sem comando que resolve"

    def test_every_failable_tool_declares_both_shapes(self):
        for name, _ in self.FAILABLE:
            assert "oneOf" in TOOLS[name]["outputSchema"], name
