from sparkforge.case.router import ROUTING_OPERATORS, next_step
from sparkforge.case.store import new_case, set_gate, set_phase

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def case(phase="diagnosis", **over):
    base = set_phase(new_case("c", "2026-07-29T00:00:00Z", RUNTIME), phase)
    for key, value in over.items():
        base[key] = value
    return base


class TestOperators:
    def test_declared_operator_set_is_closed(self):
        assert ROUTING_OPERATORS == frozenset(
            {"equals", "absent", "present", "count_gt", "count_eq", "contains", "any_where"}
        )


class TestIntake:
    def test_missing_runtime_routes_to_diagnose(self):
        step = next_step(case(phase="intake", runtime={}), [])
        assert step["recommended_skill"] == "sparkforge-diagnose"
        assert step["reason"].startswith("ROUTE-001")

    def test_divergent_runtime_routes_to_diagnose(self):
        divergent = case(phase="intake", runtime=dict(RUNTIME, divergences=["spark: ..."]))
        assert next_step(divergent, [])["reason"].startswith("ROUTE-001")

    def test_no_facts_routes_to_call_graph(self):
        assert next_step(case(phase="inventory"), [])["recommended_skill"] == (
            "analyze-library-call-graph"
        )


class TestFindingDrivenRouting:
    def test_loop_finding_routes_to_batch_loop(self):
        assert next_step(case(), ["SF-PY-004"])["recommended_skill"] == "analyze-batch-loop"

    def test_pruning_finding_routes_to_plan_analysis(self):
        assert next_step(case(), ["SF-PQ-002"])["recommended_skill"] == "analyze-spark-plan"

    def test_skew_with_input_skew_routes_to_data_skew(self):
        step = next_step(case(), ["SF-UI-001", "SF-UI-002"])
        assert step["recommended_skill"] == "diagnose-data-skew"

    def test_skew_without_input_skew_routes_to_code(self):
        """Duracao desigual com input uniforme e skew de computacao."""
        assert next_step(case(), ["SF-UI-001"])["recommended_skill"] == "optimize-pyspark-code"

    def test_alternatives_are_ranked(self):
        step = next_step(case(), ["SF-PY-004", "SF-PQ-002"])
        assert step["alternatives"]
        assert step["alternatives"][0]["rank"] == 2


class TestGatesAreAdvisory:
    def test_missing_baseline_is_reported_not_blocking(self):
        ready = set_gate(case(), "dominant_bottleneck_identified", True)
        step = next_step(ready, [])
        assert step["recommended_skill"] == "benchmark-pyspark-job"
        assert "baseline_captured" in step["blocked_by"]

    def test_blocked_by_is_empty_when_gates_satisfied(self):
        ready = set_gate(
            set_gate(case(), "dominant_bottleneck_identified", True), "baseline_captured", True
        )
        assert next_step(ready, [])["blocked_by"] == []


class TestFallback:
    def test_unmatched_state_falls_back_and_says_so(self):
        odd = case(phase="report")
        odd["gates"] = dict.fromkeys(odd["gates"], True)
        step = next_step(odd, [])
        assert step["recommended_skill"] == "sparkforge-diagnose"
        assert "Nenhuma regra" in step["reason"]


class TestDeterminism:
    def test_same_case_yields_same_step(self):
        assert next_step(case(), ["SF-UI-001", "SF-UI-002"]) == next_step(
            case(), ["SF-UI-002", "SF-UI-001"]
        )

    def test_reason_always_cites_a_rule_id_or_says_fallback(self):
        for findings in ([], ["SF-PY-004"], ["SF-UI-001"], ["SF-ICE-002"]):
            assert next_step(case(), findings)["reason"][:5] in ("ROUTE", "Nenhu")
