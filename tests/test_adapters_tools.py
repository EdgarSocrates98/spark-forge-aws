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
    def test_the_ten_phase_zero_tools_are_declared(self):
        assert set(TOOLS) == {
            "sparkforge_case_open",
            "sparkforge_case_get",
            "sparkforge_case_update",
            "sparkforge_next_step",
            "sparkforge_resume",
            "sparkforge_runtime_detect",
            "sparkforge_analyze_pyspark",
            "sparkforge_judge",
            "sparkforge_rules_lookup",
            "sparkforge_validate_output",
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

    def test_no_phase_zero_tool_is_destructive(self):
        assert all(s["annotations"]["destructiveHint"] is False for s in TOOLS.values())

    def test_no_phase_zero_tool_is_open_world(self):
        """Nucleo e offline. Coletores AWS da Fase 1 serao openWorld."""
        assert all(s["annotations"]["openWorldHint"] is False for s in TOOLS.values())

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


def _open_case(repo):
    call_tool("sparkforge_case_open", {"repo": str(repo), **_CASE_OPEN_ARGS})


def _write_job(repo):
    lib = repo / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return lib


def _real_output_for(name, tmp_path):
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

    raise AssertionError(f"sem construtor de argumentos reais para {name}")


class TestRealOutputValidatesAgainstItsOwnSchema:
    """O ponto do trabalho: sem isto, os schemas sao documentacao que pode
    apodrecer a qualquer refactor de `_core.py` sem que nenhum teste perceba."""

    @pytest.mark.parametrize("name", sorted(TOOLS))
    def test_real_output_matches_declared_schema(self, name, tmp_path):
        result = _real_output_for(name, tmp_path)
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
        ("sparkforge_judge", {"facts_path": "<tmp>/nao-existe.json"}),
    )

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_response_validates_against_its_own_schema(self, name, args, tmp_path):
        import jsonschema

        resolved = {k: str(v).replace("<tmp>", str(tmp_path)) for k, v in args.items()}
        result = call_tool(name, resolved)
        assert "error" in result, f"{name} deveria ter falhado neste input"
        jsonschema.validate(result, TOOLS[name]["outputSchema"])

    @pytest.mark.parametrize("name,args", FAILABLE, ids=[n for n, _ in FAILABLE])
    def test_error_message_is_actionable(self, name, args, tmp_path):
        resolved = {k: str(v).replace("<tmp>", str(tmp_path)) for k, v in args.items()}
        message = call_tool(name, resolved)["error"]
        assert "sparkforge" in message, f"{name}: erro sem comando que resolve"

    def test_every_failable_tool_declares_both_shapes(self):
        for name, _ in self.FAILABLE:
            assert "oneOf" in TOOLS[name]["outputSchema"], name
