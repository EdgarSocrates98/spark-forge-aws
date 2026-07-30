"""Testes do parser de plano fisico (`sparkforge.facts.spark_plan`).

Ordem dos blocos: primeiro o divisor consciente de profundidade (a peca que
um split ingenuo por virgula corrompe), depois o reconhecimento de modo,
depois cada fact kind, e por fim os inputs adversariais -- struct aninhado,
plano truncado no meio de um no, arquivo vazio, arquivo que nao e plano,
`PartitionFilters: []` contra ausencia da chave, e AQE com
`isFinalPlan=false`. Cada um precisa produzir ou um fact correto ou um
`plan.unresolved` contado, nunca um numero errado e nunca uma excecao.
"""
from __future__ import annotations

import textwrap

import pytest

from sparkforge.facts.spark_plan import (
    EMITTED_KINDS,
    extract_plan,
    split_top_level,
)


def kinds(facts):
    return {f.kind for f in facts}


def of_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def one(facts, kind):
    matched = of_kind(facts, kind)
    assert len(matched) == 1, [f.to_dict() for f in matched]
    return matched[0]


class TestSplitTopLevel:
    """Um split ingenuo por virgula corrompe `struct<a:int,b:struct<c:int>>`
    e `[isnotnull(a), (a = 1)]`. O divisor precisa contar profundidade de
    `[]`, `()` e `<>` ao mesmo tempo."""

    def test_flat_list(self):
        assert split_top_level("a,b,c") == ["a", "b", "c"]

    def test_ignores_comma_inside_angle_brackets(self):
        assert split_top_level("a:int,b:struct<c:int,d:string>,e:bigint") == [
            "a:int",
            "b:struct<c:int,d:string>",
            "e:bigint",
        ]

    def test_ignores_comma_inside_parens(self):
        assert split_top_level("isnotnull(dt#5),(dt#5 = 2026-01-01)") == [
            "isnotnull(dt#5)",
            "(dt#5 = 2026-01-01)",
        ]

    def test_ignores_comma_inside_square_brackets(self):
        assert split_top_level("a,[b,c],d") == ["a", "[b,c]", "d"]

    def test_doubly_nested_struct_is_one_field(self):
        raw = "id:bigint,payload:struct<a:struct<x:int,y:int>,b:array<string>>,ts:timestamp"
        assert split_top_level(raw) == [
            "id:bigint",
            "payload:struct<a:struct<x:int,y:int>,b:array<string>>",
            "ts:timestamp",
        ]

    def test_empty_string_is_no_fields(self):
        assert split_top_level("") == []
        assert split_top_level("   ") == []

    def test_unbalanced_input_does_not_hang_or_raise(self):
        assert split_top_level("a,struct<b:int") == ["a", "struct<b:int"]

    def test_comparison_operator_is_not_an_open_bracket(self):
        """`>` e `<` tambem sao COMPARACAO em plano fisico. Conta-los como
        colchete deixaria a profundidade aberta para sempre e engoliria todo o
        resto da linha num unico campo."""
        assert split_top_level("(valor#11 > 100.0),(qtd#12 < 5)") == [
            "(valor#11 > 100.0)",
            "(qtd#12 < 5)",
        ]

    def test_map_type_still_nests(self):
        assert split_top_level("a:map<string,int>,b:int") == ["a:map<string,int>", "b:int"]


# --------------------------------------------------------------------------- #
# planos de referencia
# --------------------------------------------------------------------------- #

FORMATTED_PRUNED = textwrap.dedent(
    """\
    == Physical Plan ==
    * Project (3)
    +- * Filter (2)
       +- Scan parquet analytics.eventos (1)


    (1) Scan parquet analytics.eventos
    Output [3]: [cliente_id#10, valor#11, dt#12]
    Batched: true
    Location: InMemoryFileIndex(1 paths)[s3://lake/analytics/eventos/dt=2026-01-01]
    PartitionFilters: [isnotnull(dt#12), (dt#12 = 2026-01-01)]
    PushedFilters: [IsNotNull(cliente_id)]
    ReadSchema: struct<cliente_id:bigint,valor:double>

    (2) Filter [codegen id : 1]
    Input [3]: [cliente_id#10, valor#11, dt#12]
    Condition : isnotnull(cliente_id#10)

    (3) Project [codegen id : 1]
    Output [2]: [cliente_id#10, valor#11]
    Input [3]: [cliente_id#10, valor#11, dt#12]
    """
)

FORMATTED_NOT_PRUNED = textwrap.dedent(
    """\
    == Physical Plan ==
    * Project (3)
    +- * Filter (2)
       +- Scan parquet analytics.eventos (1)


    (1) Scan parquet analytics.eventos
    Output [3]: [cliente_id#10, valor#11, dt#12]
    Batched: true
    Location: InMemoryFileIndex(3 paths)[s3://lake/analytics/eventos/dt=2026-01-01, \
s3://lake/analytics/eventos/dt=2026-01-02, s3://lake/analytics/eventos/dt=2026-01-03]
    PartitionFilters: []
    PushedFilters: [IsNotNull(cliente_id)]
    ReadSchema: struct<cliente_id:bigint,valor:double>

    (2) Filter [codegen id : 1]
    Input [3]: [cliente_id#10, valor#11, dt#12]
    Condition : isnotnull(cliente_id#10)

    (3) Project [codegen id : 1]
    Output [2]: [cliente_id#10, valor#11]
    Input [3]: [cliente_id#10, valor#11, dt#12]
    """
)


class TestModeDetection:
    def test_formatted_plan_is_recognised(self):
        facts = extract_plan(FORMATTED_PRUNED, "plan.txt")
        assert one(facts, "plan.analyzed").attrs["mode"] == "formatted"

    def test_every_emitted_kind_is_declared(self):
        facts = extract_plan(FORMATTED_PRUNED, "plan.txt")
        assert kinds(facts) <= EMITTED_KINDS

    def test_sentinel_is_always_present(self):
        assert of_kind(extract_plan(FORMATTED_PRUNED, "plan.txt"), "plan.analyzed")


class TestFileScan:
    def test_pruned_scan_is_not_flagged_as_empty(self):
        scan = one(extract_plan(FORMATTED_PRUNED, "plan.txt"), "plan.file_scan")
        assert scan.attrs["partition_filters_empty"] is False
        assert scan.attrs["table_partitioned"] is True

    def test_unpruned_partitioned_scan_is_flagged(self):
        scan = one(extract_plan(FORMATTED_NOT_PRUNED, "plan.txt"), "plan.file_scan")
        assert scan.attrs["partition_filters_empty"] is True
        assert scan.attrs["table_partitioned"] is True

    def test_relation_and_format_are_captured(self):
        scan = one(extract_plan(FORMATTED_PRUNED, "plan.txt"), "plan.file_scan")
        assert scan.attrs["relation"] == "analytics.eventos"
        assert scan.attrs["format"] == "parquet"

    def test_read_schema_columns_counted_depth_aware(self):
        scan = one(extract_plan(FORMATTED_PRUNED, "plan.txt"), "plan.file_scan")
        assert scan.measures["read_schema_columns"] == 2

    def test_subject_anchors_the_node_not_the_file(self):
        scan = one(extract_plan(FORMATTED_PRUNED, "plan.txt"), "plan.file_scan")
        assert scan.subject["type"] == "plan_node"
        assert scan.subject["node_id"] == 1
        assert scan.subject["file"] == "plan.txt"
        assert scan.subject["line"] > 0


class TestDeterminism:
    def test_same_input_same_facts(self):
        first = [f.to_dict() for f in extract_plan(FORMATTED_PRUNED, "plan.txt")]
        second = [f.to_dict() for f in extract_plan(FORMATTED_PRUNED, "plan.txt")]
        assert first == second


class TestAdversarialInputs:
    def test_empty_file_is_a_counted_blind_spot_not_silence(self):
        facts = extract_plan("", "vazio.txt")
        assert one(facts, "plan.unresolved").attrs["reason"] == "empty_input"
        assert one(facts, "plan.analyzed").measures["unresolved_count"] == 1

    def test_file_that_is_not_a_plan_is_rejected_not_half_parsed(self):
        facts = extract_plan("Hello world\nthis is not a plan\n", "readme.txt")
        assert one(facts, "plan.unresolved").attrs["reason"] == "not_a_plan"
        assert not of_kind(facts, "plan.file_scan")

    def test_never_raises_on_arbitrary_bytes(self):
        for junk in ("\x00\x01", "((((", "]]]]", "== Physical Plan ==\n"):
            extract_plan(junk, "junk.txt")  # nao pode levantar


SIMPLE_PLAN = textwrap.dedent(
    """\
    == Physical Plan ==
    AdaptiveSparkPlan isFinalPlan=false
    +- Project [cliente_id#10, total#30]
       +- HashAggregate(keys=[cliente_id#10], functions=[sum(valor#11)])
          +- Exchange hashpartitioning(cliente_id#10, 200), ENSURE_REQUIREMENTS, [plan_id=42]
             +- HashAggregate(keys=[cliente_id#10], functions=[partial_sum(valor#11)])
                +- BatchEvalPython [normaliza(valor#11)#40], [valor#11]
                   +- BroadcastHashJoin [cliente_id#10], [cliente_id#20], Inner, BuildRight, false
                      :- FileScan parquet analytics.eventos[cliente_id#10,valor#11,dt#12] \
Batched: true, DataFilters: [(valor#11 > 100.0)], Format: Parquet, \
Location: InMemoryFileIndex(1 paths)[s3://lake/eventos], PartitionFilters: [], \
PushedFilters: [IsNotNull(cliente_id)], ReadSchema: struct<cliente_id:bigint,valor:double>
                      +- BroadcastExchange HashedRelationBroadcastMode(List(input[0, bigint]))
                         +- FileScan parquet analytics.clientes[cliente_id#20] Batched: true, \
DataFilters: [], Format: Parquet, Location: InMemoryFileIndex(1 paths)[s3://lake/clientes], \
PartitionFilters: [], PushedFilters: [], ReadSchema: struct<cliente_id:bigint>
    """
)

FORMATTED_WIDE_READ_SCHEMA = textwrap.dedent(
    """\
    == Physical Plan ==
    * Project (2)
    +- Scan parquet analytics.transacoes (1)


    (1) Scan parquet analytics.transacoes
    Output [9]: [c1#1, c2#2, c3#3, c4#4, c5#5, c6#6, c7#7, c8#8, c9#9]
    Batched: true
    Location: InMemoryFileIndex(1 paths)[s3://lake/analytics/transacoes]
    PartitionFilters: []
    PushedFilters: []
    ReadSchema: struct<c1:bigint,c2:string,c3:string,c4:string,c5:string,c6:string,\
c7:struct<x:int,y:int>,c8:string,c9:string>

    (2) Project [codegen id : 1]
    Output [2]: [c1#1, c2#2]
    Input [9]: [c1#1, c2#2, c3#3, c4#4, c5#5, c6#6, c7#7, c8#8, c9#9]
    """
)

FORMATTED_TRUNCATED = textwrap.dedent(
    """\
    == Physical Plan ==
    * Project (2)
    +- Scan parquet analytics.transacoes (1)


    (1) Scan parquet analytics.transacoes
    Output [80]: [c1#1, c2#2, c3#3, ... 77 more fields]
    Batched: true
    Location: InMemoryFileIndex(1 paths)[s3://lake/analytics/transacoes]
    PartitionFilters: []
    PushedFilters: []
    ReadSchema: struct<c1:bigint,c2:string,c3:string,... 77 more fields>

    (2) Project [codegen id : 1]
    Output [2]: [c1#1, c2#2]
    """
)

BATCH_SCAN_NO_PARTITION_FILTERS = textwrap.dedent(
    """\
    == Physical Plan ==
    * Project (2)
    +- BatchScan glue_catalog.db.iceberg_tbl (1)


    (1) BatchScan glue_catalog.db.iceberg_tbl
    Output [2]: [id#1, nome#2]
    Arguments: id#1, nome#2, IcebergScan(table=glue_catalog.db.iceberg_tbl)
    RuntimeFilters: []

    (2) Project [codegen id : 1]
    Output [1]: [id#1]
    Input [2]: [id#1, nome#2]
    """
)


class TestSimpleMode:
    def test_simple_mode_is_recognised(self):
        assert one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.analyzed").attrs["mode"] == "simple"

    def test_inline_scan_metadata_is_split_depth_aware(self):
        scans = of_kind(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.file_scan")
        eventos = next(f for f in scans if f.attrs["relation"] == "analytics.eventos")
        assert eventos.attrs["format"] == "parquet"
        assert eventos.measures["read_schema_columns"] == 2
        assert eventos.measures["data_filter_count"] == 1
        assert eventos.measures["pushed_filter_count"] == 1

    def test_both_scans_are_found(self):
        assert len(of_kind(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.file_scan")) == 2

    def test_join_strategy_is_captured(self):
        join = one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.join")
        assert join.attrs["strategy"] == "BroadcastHashJoin"
        assert join.attrs["join_type"] == "Inner"
        assert join.attrs["build_side"] == "right"

    def test_exchange_and_broadcast_exchange_are_both_counted(self):
        exchanges = of_kind(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.exchange")
        assert {f.attrs["operator"] for f in exchanges} == {"Exchange", "BroadcastExchange"}
        assert one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.analyzed").measures[
            "exchange_count"
        ] == 2

    def test_python_udf_in_the_plan_is_a_fact(self):
        udf = one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.python_udf")
        assert udf.attrs["operator"] == "BatchEvalPython"
        assert udf.attrs["udf_type"] == "python"

    def test_cost_operators_use_the_closed_vocabulary(self):
        facts = extract_plan(SIMPLE_PLAN, "p.txt")
        assert {f.attrs["operator"] for f in of_kind(facts, "plan.operator")} == {"HashAggregate"}


class TestAqe:
    def test_non_final_plan_is_recorded_not_treated_as_final(self):
        aqe = one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.aqe")
        assert aqe.attrs["is_final_plan"] is False
        assert one(extract_plan(SIMPLE_PLAN, "p.txt"), "plan.analyzed").attrs[
            "aqe_final_plan"
        ] is False

    def test_final_plan_is_distinguished(self):
        text = SIMPLE_PLAN.replace("isFinalPlan=false", "isFinalPlan=true")
        assert one(extract_plan(text, "p.txt"), "plan.aqe").attrs["is_final_plan"] is True

    def test_plan_without_aqe_says_unknown_not_false(self):
        sentinel = one(extract_plan(FORMATTED_PRUNED, "p.txt"), "plan.analyzed")
        assert sentinel.attrs["aqe_present"] is False
        assert sentinel.attrs["aqe_final_plan"] == "unknown"


class TestColumnPruning:
    def test_wide_read_schema_against_narrow_usage(self):
        scan = one(extract_plan(FORMATTED_WIDE_READ_SCHEMA, "p.txt"), "plan.file_scan")
        assert scan.measures["read_schema_columns"] == 9
        assert scan.measures["referenced_columns"] == 2

    def test_nested_struct_counts_as_one_column(self):
        scan = one(extract_plan(FORMATTED_WIDE_READ_SCHEMA, "p.txt"), "plan.file_scan")
        assert scan.measures["read_schema_columns"] == 9  # c7:struct<x,y> conta 1, nao 3

    def test_input_field_is_plumbing_not_usage(self):
        """`Input [9]` do Project apenas repete o Output do filho. Conta-lo como
        uso faria toda coluna lida parecer referenciada e SF-PQ-004 nunca
        dispararia."""
        scan = one(extract_plan(FORMATTED_WIDE_READ_SCHEMA, "p.txt"), "plan.file_scan")
        assert scan.measures["referenced_columns"] < scan.measures["read_schema_columns"]


class TestTruncation:
    def test_truncated_field_list_is_a_blind_spot_not_a_number(self):
        facts = extract_plan(FORMATTED_TRUNCATED, "p.txt")
        scan = one(facts, "plan.file_scan")
        assert scan.attrs["output_truncated"] is True
        assert scan.attrs["read_schema_truncated"] is True
        assert "read_schema_columns" not in scan.measures
        assert "referenced_columns" not in scan.measures

    def test_truncation_is_counted_as_unresolved(self):
        facts = extract_plan(FORMATTED_TRUNCATED, "p.txt")
        reasons = {f.attrs["reason"] for f in of_kind(facts, "plan.unresolved")}
        assert "truncated_field_list" in reasons
        assert one(facts, "plan.analyzed").measures["unresolved_count"] >= 1


class TestPartitionFiltersSemantics:
    """`PartitionFilters: []` e a AUSENCIA da chave significam coisas
    diferentes. Confundi-las fabrica um P0 falso."""

    def test_empty_list_without_evidence_is_unknown_not_partitioned(self):
        """`analytics.clientes` le uma coluna so, e ela esta no ReadSchema: nao
        ha coluna de particao visivel, nao ha filtro de particao, e o Location e
        a raiz da tabela. O plano simplesmente NAO diz se a tabela e
        particionada -- e a resposta honesta e `unknown`, nunca `false` (que
        afirmaria o que nao foi observado) nem `true` (que acusaria SF-PQ-002
        sem evidencia)."""
        facts = extract_plan(SIMPLE_PLAN, "p.txt")
        clientes = next(
            f
            for f in of_kind(facts, "plan.file_scan")
            if f.attrs["relation"] == "analytics.clientes"
        )
        assert clientes.attrs["partition_filters_present"] is True
        assert clientes.attrs["partition_filters_empty"] is True
        assert clientes.attrs["table_partitioned"] == "unknown"

    def test_partition_column_visible_in_simple_mode_too(self):
        """`analytics.eventos` expoe `dt#12` no Output e nao no ReadSchema: e
        coluna de particao, e o `PartitionFilters: []` vazio ao lado disso e o
        achado de SF-PQ-002."""
        facts = extract_plan(SIMPLE_PLAN, "p.txt")
        eventos = next(
            f
            for f in of_kind(facts, "plan.file_scan")
            if f.attrs["relation"] == "analytics.eventos"
        )
        assert eventos.attrs["table_partitioned"] is True
        assert eventos.attrs["partition_filters_empty"] is True

    def test_indecidible_scan_is_reported_as_a_blind_spot(self):
        facts = extract_plan(SIMPLE_PLAN, "p.txt")
        reasons = {f.attrs["reason"] for f in of_kind(facts, "plan.unresolved")}
        assert "partition_status_unknown" in reasons

    def test_missing_key_never_claims_empty(self):
        scan = one(extract_plan(BATCH_SCAN_NO_PARTITION_FILTERS, "p.txt"), "plan.file_scan")
        assert scan.attrs["scan_api"] == "v2_batch_scan"
        assert scan.attrs["partition_filters_present"] is False
        assert scan.attrs["partition_filters_empty"] == "unknown"
        assert scan.attrs["table_partitioned"] == "unknown"

    def test_partition_column_in_output_but_not_read_schema_proves_partitioned(self):
        scan = one(extract_plan(FORMATTED_NOT_PRUNED, "p.txt"), "plan.file_scan")
        assert scan.attrs["partitioned_evidence"] == "output_minus_read_schema"


class TestExtendedMode:
    def test_only_the_physical_section_is_parsed(self):
        text = (
            "== Parsed Logical Plan ==\n"
            "'Project [*]\n"
            "+- 'UnresolvedRelation [analytics, eventos]\n"
            "\n"
            "== Analyzed Logical Plan ==\n"
            "cliente_id: bigint\n"
            "Project [cliente_id#10]\n"
            "\n" + FORMATTED_PRUNED
        )
        facts = extract_plan(text, "p.txt")
        sentinel = one(facts, "plan.analyzed")
        assert sentinel.measures["skipped_logical_lines"] > 0
        assert one(facts, "plan.file_scan").attrs["relation"] == "analytics.eventos"


class TestRejectedModes:
    def test_codegen_mode_is_rejected_not_half_parsed(self):
        text = "Found 1 WholeStageCodegen subtrees.\n== Subtree 1 ==\nGenerated code:\n"
        facts = extract_plan(text, "p.txt")
        unresolved = one(facts, "plan.unresolved")
        assert unresolved.attrs["reason"] == "unsupported_mode"
        assert not of_kind(facts, "plan.file_scan")


def test_extract_plan_returns_only_declared_kinds():
    for text in (FORMATTED_PRUNED, FORMATTED_NOT_PRUNED, "", "nada"):
        assert kinds(extract_plan(text, "x.txt")) <= EMITTED_KINDS


@pytest.mark.parametrize("text", [FORMATTED_PRUNED, FORMATTED_NOT_PRUNED])
def test_sentinel_counts_lines(text):
    sentinel = one(extract_plan(text, "plan.txt"), "plan.analyzed")
    assert sentinel.measures["line_count"] == len(text.splitlines())
