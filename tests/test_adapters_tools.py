import json

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
        for name, spec in TOOLS.items():
            assert spec["outputSchema"]["type"] == "object", name

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
