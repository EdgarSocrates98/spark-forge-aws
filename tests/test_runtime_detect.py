from sparkforge.facts.runtime_detect import GLUE_MATRIX, detect_runtime


class TestMatrix:
    def test_matrix_matches_committed_knowledge(self):
        """Espelha knowledge/glue/runtime-matrix.md. Divergir aqui e bug de dado."""
        assert GLUE_MATRIX["5.1"] == {
            "spark": "3.5.6",
            "python": "3.11",
            "iceberg": "1.10.0",
        }
        assert GLUE_MATRIX["5.0"]["iceberg"] == "1.7.1"
        assert GLUE_MATRIX["4.0"]["iceberg"] == "1.0.0"
        assert GLUE_MATRIX["3.0"]["spark"] == "3.1.1"


class TestDerivation:
    def test_glue_version_derives_spark_python_iceberg(self):
        context, facts = detect_runtime({"terraform": {"glue_version": "5.0"}})
        assert context.spark == "3.5.4"
        assert context.iceberg == "1.7.1"
        assert "terraform" in context.detected_from
        assert facts

    def test_event_log_spark_version_is_used_directly(self):
        context, _ = detect_runtime({"event_log": {"spark_version": "3.5.6"}})
        assert context.spark == "3.5.6"


class TestDivergence:
    def test_conflicting_spark_version_is_recorded_not_resolved(self):
        sources = {
            "terraform": {"glue_version": "5.0"},  # implica Spark 3.5.4
            "event_log": {"spark_version": "3.3.0"},
        }
        context, facts = detect_runtime(sources)
        assert context.divergences
        assert any("spark" in d for d in context.divergences)

    def test_divergence_emits_runtime_signal_fact_with_count(self):
        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.3.0"},
        }
        _, facts = detect_runtime(sources)
        signal = [f for f in facts if f.kind == "env.runtime_signal"]
        assert signal
        assert signal[0].measures["distinct_versions"] >= 2

    def test_agreement_yields_single_distinct_version(self):
        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.5.4"},
        }
        context, facts = detect_runtime(sources)
        assert context.divergences == []
        signal = [f for f in facts if f.kind == "env.runtime_signal"][0]
        assert signal.measures["distinct_versions"] == 1


class TestSfEnv001FiresOnDivergence:
    def test_divergence_produces_sf_env_001(self):
        from sparkforge.rules.engine import judge
        from sparkforge.rules.loader import load_catalog

        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.3.0"},
        }
        context, facts = detect_runtime(sources)
        rules = [r for r in load_catalog() if r["id"] == "SF-ENV-001"]
        findings = judge(facts, rules, context.to_dict())
        assert [f.rule_id for f in findings] == ["SF-ENV-001"]
        assert findings[0].severity == "P0"
