import random
import textwrap

from sparkforge.facts.call_graph import EMITTED_KINDS, build_call_graph
from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.models import Fact
from sparkforge.findings.validate import validate_fact

FILE = "lib.py"


def edge(caller: str, callee: str, file: str = FILE, line: int = 1) -> Fact:
    return Fact(
        kind="pyspark.callgraph_edge",
        subject={
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "end_line": line,
            "symbol": caller,
            "snippet": f"{callee}()",
        },
        attrs={"caller": caller, "callee": callee},
        provenance={"artifact": file, "artifact_sha256": "", "extractor": "pyspark_ast@0.1.0"},
    )


def work(symbol: str, kind: str = "pyspark.action", file: str = FILE, line: int = 1) -> Fact:
    return Fact(
        kind=kind,
        subject={
            "type": "source_location",
            "file": file,
            "line": line,
            "col": 0,
            "end_line": line,
            "symbol": symbol,
            "snippet": "df.count()",
        },
        attrs={"method": "count"},
        provenance={"artifact": file, "artifact_sha256": "", "extractor": "pyspark_ast@0.1.0"},
    )


def by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_emitted_kinds_are_exactly_four():
    assert EMITTED_KINDS == {
        "callgraph.function",
        "callgraph.reachable_spark_work",
        "callgraph.summary",
        "callgraph.cycle",
    }


class TestLinearChainDepth:
    def test_collect_two_levels_deep_reports_min_depth_two(self):
        facts = [edge("main", "a"), edge("a", "b"), work("b", "pyspark.driver_collect")]
        out = build_call_graph(facts, path_hint=FILE)

        reachable = by_kind(out, "callgraph.reachable_spark_work")
        collect_fact = next(
            f for f in reachable if f.attrs["work_kind"] == "pyspark.driver_collect"
        )
        assert collect_fact.measures["min_depth"] == 2
        assert collect_fact.attrs["via"] == ["main", "a", "b"]
        assert collect_fact.attrs["entrypoint"] == "main"

    def test_entrypoint_has_no_callers(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        functions = {f.subject["symbol"]: f for f in by_kind(out, "callgraph.function")}
        assert functions["main"].measures["fan_in"] == 0
        assert functions["main"].attrs["is_entrypoint"] is True
        assert functions["a"].attrs["is_entrypoint"] is False

    def test_terminal_function_is_a_leaf(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        functions = {f.subject["symbol"]: f for f in by_kind(out, "callgraph.function")}
        assert functions["b"].measures["fan_out"] == 0
        assert functions["b"].attrs["is_leaf"] is True
        assert functions["main"].attrs["is_leaf"] is False

    def test_summary_reports_max_depth_and_no_unreachable(self):
        facts = [edge("main", "a"), edge("a", "b")]
        out = build_call_graph(facts, path_hint=FILE)
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["max_depth"] == 2
        assert summary.measures["function_count"] == 3
        assert summary.measures["edge_count"] == 2
        assert summary.measures["unreachable_function_count"] == 0
        assert summary.attrs["entrypoints"] == ["main"]
        assert summary.attrs["has_cycle"] is False


class TestCycles:
    def test_direct_recursion_produces_self_cycle(self):
        facts = [edge("f", "f")]
        out = build_call_graph(facts, path_hint=FILE)
        cycles = by_kind(out, "callgraph.cycle")
        assert len(cycles) == 1
        assert cycles[0].attrs["functions"] == ["f"]
        assert cycles[0].measures["length"] == 1

        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.attrs["has_cycle"] is True

    def test_mutual_recursion_produces_one_canonical_cycle_regardless_of_edge_order(self):
        forward = [edge("f", "g"), edge("g", "f")]
        backward = [edge("g", "f"), edge("f", "g")]

        out_forward = build_call_graph(forward, path_hint=FILE)
        out_backward = build_call_graph(backward, path_hint=FILE)

        assert [f.to_dict() for f in out_forward] == [f.to_dict() for f in out_backward]

        cycles = by_kind(out_forward, "callgraph.cycle")
        assert len(cycles) == 1
        assert cycles[0].attrs["functions"] == ["f", "g"]

    def test_cycle_containing_spark_work_is_flagged(self):
        facts = [edge("f", "g"), edge("g", "f"), work("g", "pyspark.write")]
        out = build_call_graph(facts, path_hint=FILE)
        cycle = by_kind(out, "callgraph.cycle")[0]
        assert cycle.attrs["contains_spark_work"] is True
        assert cycle.measures["spark_work_count"] == 1

    def test_cycle_with_no_entrypoint_counts_as_unreachable(self):
        # f <-> g calling each other, nothing outside calls either: no
        # entrypoint exists, so no BFS ever visits them.
        facts = [edge("f", "g"), edge("g", "f")]
        out = build_call_graph(facts, path_hint=FILE)
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["entrypoint_count"] == 0
        assert summary.measures["unreachable_function_count"] == 2
        assert by_kind(out, "callgraph.reachable_spark_work") == []


class TestIsolatedFunction:
    def test_function_with_no_edges_produces_no_node_and_does_not_crash(self):
        facts = [work("solo", "pyspark.action")]
        out = build_call_graph(facts, path_hint=FILE)
        assert by_kind(out, "callgraph.function") == []
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["function_count"] == 0
        assert summary.measures["edge_count"] == 0


class TestDeterminism:
    def test_output_is_identical_across_shuffled_input_order(self):
        source = textwrap.dedent(
            """
            def main():
                stage_one()
                stage_two()

            def stage_one():
                helper()

            def stage_two():
                df.write.parquet("s3://out")

            def helper():
                df.collect()
            """
        )
        facts = extract_source(source, FILE)
        ordered = build_call_graph(facts, path_hint=FILE)

        shuffled = list(facts)
        random.Random(42).shuffle(shuffled)  # noqa: S311 -- deterministico p/ teste, nao cripto
        reshuffled = build_call_graph(shuffled, path_hint=FILE)

        assert [f.to_dict() for f in ordered] == [f.to_dict() for f in reshuffled]

    def test_writing_twice_produces_byte_identical_fact_ids(self):
        facts = [edge("main", "a"), work("a", "pyspark.driver_collect")]
        first = [f.id for f in build_call_graph(facts, path_hint=FILE)]
        second = [f.id for f in build_call_graph(list(reversed(facts)), path_hint=FILE)]
        assert first == second


class TestDeepChainDoesNotRecurse:
    def test_five_hundred_deep_chain_does_not_raise_recursion_error(self):
        depth = 500
        facts = [edge(f"f{i}", f"f{i + 1}") for i in range(depth)]
        facts.append(work(f"f{depth}", "pyspark.driver_collect"))

        out = build_call_graph(facts, path_hint=FILE)

        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["max_depth"] == depth
        assert summary.measures["function_count"] == depth + 1

        reachable = by_kind(out, "callgraph.reachable_spark_work")
        deep_work = next(f for f in reachable if f.attrs["work_kind"] == "pyspark.driver_collect")
        assert deep_work.measures["min_depth"] == depth


class TestSchemaValidity:
    def test_every_emitted_fact_validates_against_fact_schema(self):
        facts = [
            edge("main", "a"),
            edge("a", "b"),
            edge("f", "f"),
            edge("g", "h"),
            edge("h", "g"),
            work("b", "pyspark.driver_collect"),
            work("g", "pyspark.write"),
        ]
        out = build_call_graph(facts, path_hint=FILE)
        assert out  # sanity: something was produced
        for fact in out:
            validate_fact(fact.to_dict())


class TestFixtureIntegration:
    def test_action_in_loop_fixture_produces_a_valid_call_graph(self):
        from pathlib import Path

        fixture = (
            Path(__file__).resolve().parents[1] / "fixtures" / "pyspark" / "action_in_loop"
        )
        source_path = fixture / "input" / "lib" / "job.py"
        facts = extract_source(source_path.read_text(encoding="utf-8"), "input/lib/job.py")
        out = build_call_graph(facts, path_hint="input/lib/job.py")
        summary = by_kind(out, "callgraph.summary")[0]
        assert summary.measures["function_count"] >= 0
        for fact in out:
            validate_fact(fact.to_dict())
