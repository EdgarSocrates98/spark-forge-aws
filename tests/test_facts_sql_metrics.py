"""Testes do extrator de metricas SQL por no do plano."""
from __future__ import annotations

import itertools
import json

from sparkforge.facts.sql_metrics import extract_sql_metrics

SQL_START = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"


def _scan_node(
    node_name="Scan parquet ",
    simple="FileScan parquet db.clientes[id#1]",
    metrics=None,
):
    return {
        "nodeName": node_name,
        "simpleString": simple,
        "children": [],
        "metadata": {"Format": "Parquet", "Location": "InMemoryFileIndex[s3://bucket/x]"},
        "metrics": metrics if metrics is not None else [],
    }


def _start(execution_id=0, plan=None, description="save at Job.scala:1"):
    return json.dumps(
        {
            "Event": SQL_START,
            "executionId": execution_id,
            "description": description,
            "details": "",
            "physicalPlanDescription": "== Physical Plan ==",
            "sparkPlanInfo": plan,
            "time": 1600000000000,
        }
    )


class TestPlanTree:
    def test_scan_node_becomes_a_fact_anchored_on_plan_node(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project [id#1]",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node()],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")

        scans = [f for f in facts if f.kind == "spark.sql.scan"]
        assert len(scans) == 1
        assert scans[0].subject["type"] == "plan_node"
        assert scans[0].subject["execution_id"] == 0
        assert scans[0].subject["relation"] == "db.clientes"
        assert scans[0].attrs["scan_api"] == "v1"
        assert scans[0].attrs["format"] == "parquet"

    def test_node_id_is_the_preorder_index(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node()],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # raiz = 0, primeiro filho em preorder = 1
        assert scan.subject["node_id"] == 1

    def test_symbol_separates_the_same_node_across_executions(self):
        plano = _scan_node()
        facts = extract_sql_metrics(
            [_start(execution_id=0, plan=plano), _start(execution_id=1, plan=plano)],
            "log.jsonl",
        )
        simbolos = {f.subject["symbol"] for f in facts if f.kind == "spark.sql.scan"}

        assert len(simbolos) == 2

    def test_batch_scan_is_marked_v2(self):
        plano = _scan_node(node_name="BatchScan", simple="BatchScan db.eventos[id#1]")
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.attrs["scan_api"] == "v2"
        assert scan.subject["relation"] == "db.eventos"

    def test_execution_fact_counts_the_nodes(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node(), _scan_node(simple="FileScan parquet db.pedidos[id#2]")],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        execucao = [f for f in facts if f.kind == "spark.sql.execution"][0]

        assert execucao.measures == {"scan_nodes": 2, "nodes_total": 3}
        assert execucao.attrs["plan_source"] == "initial"


class TestNoLeak:
    def test_s3_location_never_enters_any_fact(self):
        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        blob = json.dumps([f.to_dict() for f in facts])

        assert "s3://bucket/x" not in blob
        assert "InMemoryFileIndex" not in blob


DRIVER_ACCUM = "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates"


def _metric(name, accumulator_id, metric_type="sum"):
    return {"name": name, "accumulatorId": accumulator_id, "metricType": metric_type}


def _driver_update(execution_id, pares):
    return json.dumps(
        {"Event": DRIVER_ACCUM, "executionId": execution_id, "accumUpdates": pares}
    )


def _task_end(accumulables):
    return json.dumps(
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Task Info": {"Accumulables": accumulables},
        }
    )


def _accumulable(accumulator_id, name, update, value):
    return {
        "ID": accumulator_id,
        "Name": name,
        "Update": str(update),
        "Value": str(value),
        "Internal": False,
        "Count Failed Values": True,
    }


SQL_AQE = "org.apache.spark.sql.execution.ui.SparkListenerSQLAdaptiveExecutionUpdate"
SQL_END = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"


def _aqe(execution_id, plan):
    return json.dumps(
        {
            "Event": SQL_AQE,
            "executionId": execution_id,
            "physicalPlanDescription": "== Physical Plan ==",
            "sparkPlanInfo": plan,
        }
    )


def _end(execution_id):
    return json.dumps(
        {"Event": SQL_END, "executionId": execution_id, "time": 1600000000001}
    )


class TestAQE:
    def test_replanned_execution_declares_the_final_source(self):
        inicial = _scan_node(metrics=[_metric("number of files read", 11)])
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [_start(plan=inicial), _aqe(0, final), _driver_update(0, [[21, 4]]), _end(0)],
            "log.jsonl",
        )
        execucao = [f for f in facts if f.kind == "spark.sql.execution"][0]
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert execucao.attrs["plan_source"] == "final_aqe"
        assert scan.measures["files_read"] == 4

    def test_same_accumulator_in_two_nodes_refuses_to_attribute(self):
        plano = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="FileScan parquet db.pedidos[id#2]",
                    metrics=[_metric("number of files read", 11)],
                ),
            ],
        }
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 9]]), _end(0)], "log.jsonl"
        )
        scans = [f for f in facts if f.kind == "spark.sql.scan"]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "accumulator_reassigned"
        ]

        assert all("files_read" not in s.measures for s in scans)
        assert len(lacunas) == 1

    def test_value_published_before_the_replan_is_not_lost(self):
        inicial = _scan_node(metrics=[_metric("number of files read", 11)])
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [
                _start(plan=inicial),
                _driver_update(0, [[11, 3]]),  # publicado ANTES da reposta
                _aqe(0, final),
                _end(0),
            ],
            "log.jsonl",
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # O valor foi medido sob o plano inicial, e o no continua sendo o mesmo
        # scan. Descarta-lo faria a extracao devolver menos bytes do que o
        # Spark publicou, sem dizer que descartou.
        assert scan.measures["files_read"] == 3

    def test_value_lost_to_a_replan_is_never_silent(self):
        """Se o no do acumulador antigo sumiu do plano novo, e lacuna.

        Nao ha nó a que atribuir, e o silencio faria a soma sair menor sem
        nenhum sinal.
        """
        inicial = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="FileScan parquet db.some[id#9]",
                    metrics=[_metric("number of files read", 12)],
                ),
            ],
        }
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [_start(plan=inicial), _driver_update(0, [[12, 5]]), _aqe(0, final), _end(0)],
            "log.jsonl",
        )
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "value_orphaned_by_replan"
        ]

        assert len(lacunas) == 1
        assert lacunas[0].attrs["accumulator_id"] == 12


class TestRefusals:
    def test_log_without_sql_events_says_so_instead_of_looking_broken(self):
        facts = extract_sql_metrics(
            [json.dumps({"Event": "SparkListenerApplicationStart", "App Name": "x"})],
            "log.jsonl",
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved" and f.attrs["reason"] == "no_sql_events"
        ]

        assert sentinela.measures["executions"] == 0
        assert len(lacunas) == 1
        assert not [f for f in facts if f.kind == "spark.sql.scan"]

    def test_malformed_line_is_counted_and_the_pass_continues(self):
        facts = extract_sql_metrics(
            ["{nao e json", _start(plan=_scan_node()), _end(0)], "log.jsonl"
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]

        assert sentinela.measures["malformed_lines"] == 1
        assert len([f for f in facts if f.kind == "spark.sql.scan"]) == 1

    def test_execution_without_an_end_event_is_declared_incomplete(self):
        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "incomplete_execution"
        ]

        assert len(lacunas) == 1

    def test_missing_file_becomes_a_fact_never_an_exception(self, tmp_path):
        from sparkforge.facts.sql_metrics import extract_sql_metrics_path

        facts = extract_sql_metrics_path(tmp_path / "nao-existe.jsonl")
        assert [f.attrs["reason"] for f in facts] == ["read_error"]


class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        plano = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="BatchScan db.eventos[id#2]",
                    metrics=[_metric("metrica que nao existe", 12)],
                ),
            ],
        }
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 2], [12, 3]])], "log.jsonl"
        )

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())

    def test_every_emitted_kind_is_declared(self):
        from sparkforge.facts.sql_metrics import EMITTED_KINDS

        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        assert {f.kind for f in facts} <= EMITTED_KINDS


class TestValues:
    def test_driver_metric_becomes_a_measure(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 7]])], "log.jsonl"
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.measures["files_read"] == 7

    def test_task_metric_sums_the_updates_not_the_running_value(self):
        plano = _scan_node(metrics=[_metric("size of files read", 12, "size")])
        facts = extract_sql_metrics(
            [
                _start(plan=plano),
                _task_end([_accumulable(12, "size of files read", 1000, 1000)]),
                _task_end([_accumulable(12, "size of files read", 500, 1500)]),
            ],
            "log.jsonl",
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # 1000 + 500. Somar `Value` daria 2500, que conta o total duas vezes.
        assert scan.measures["bytes_read"] == 1500

    def test_metric_the_execution_never_published_is_absent_not_zero(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 3]])], "log.jsonl"
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.measures["files_read"] == 3
        assert "bytes_read" not in scan.measures
        assert "rows_output" not in scan.measures

    def test_unknown_metric_name_becomes_unresolved_never_a_guess(self):
        plano = _scan_node(metrics=[_metric("bytes of shuffle write", 13)])
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[13, 999]])], "log.jsonl"
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "unknown_metric_name"
        ]

        assert scan.measures == {}
        assert len(lacunas) == 1
        assert lacunas[0].attrs["metric_name"] == "bytes of shuffle write"

    def test_accumulator_of_no_sql_node_is_counted_not_discarded(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics(
            [
                _start(plan=plano),
                _task_end([_accumulable(9999, "internal.metrics.executorRunTime", 5, 5)]),
            ],
            "log.jsonl",
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]

        assert sentinela.measures["unattributed_accumulators"] == 1


class TestEstruturaDaArvore:
    def _tres_niveis(self):
        """(A join B) join C, com A/B/C sendo scans."""
        interno = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.a[id#1]"),
                _scan_node(simple="FileScan parquet db.b[id#2]"),
            ],
        }
        return {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#3], Inner",
            "metadata": {},
            "metrics": [],
            "children": [interno, _scan_node(simple="FileScan parquet db.c[id#3]")],
        }

    def test_children_of_each_node_are_recorded(self):
        from sparkforge.facts.sql_metrics import _estrutura

        filhos, profundidade = _estrutura(self._tres_niveis())

        # preorder: 0 SortMergeJoin, 1 BroadcastHashJoin, 2 db.a, 3 db.b, 4 db.c
        assert filhos[0] == [1, 4]
        assert filhos[1] == [2, 3]
        assert filhos[2] == []
        assert profundidade == 3

    def test_sources_below_a_node_carry_their_distance_in_joins(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = self._tres_niveis()
        # a partir do filho esquerdo da raiz (o join interno, node_id 1)
        fontes = _fontes_abaixo(arvore, 1)

        assert sorted((f["relation"], f["via_joins"]) for f in fontes) == [
            ("db.a", 0),
            ("db.b", 0),
        ]

    def test_distance_counts_the_joins_in_between(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = self._tres_niveis()
        fontes = _fontes_abaixo(arvore, 0)

        assert sorted((f["relation"], f["via_joins"]) for f in fontes) == [
            ("db.a", 1),
            ("db.b", 1),
            ("db.c", 0),
        ]

    def test_a_node_without_any_scan_below_reports_none(self):
        from sparkforge.facts.sql_metrics import _fontes_abaixo

        arvore = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [
                {
                    "nodeName": "Scan ExistingRDD",
                    "simpleString": "Scan ExistingRDD[id#1]",
                    "metadata": {},
                    "metrics": [],
                    "children": [],
                }
            ],
        }

        assert _fontes_abaixo(arvore, 0) == []


class TestGrafoDeJoins:
    def _broadcast(self):
        return {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.pedidos[id#1]"),
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }

    def test_join_node_becomes_a_fact(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        join = [f for f in facts if f.kind == "spark.sql.join"][0]

        assert join.attrs["strategy"] == "BroadcastHashJoin"
        assert join.attrs["join_type"] == "Inner"
        assert join.attrs["build_side"] == "right"
        assert join.measures == {"inputs_left": 1, "inputs_right": 1}

    def test_each_source_becomes_an_edge_with_its_side(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        arestas = {
            f.attrs["relation"]: f.attrs for f in facts if f.kind == "spark.sql.join_input"
        }

        assert arestas["db.clientes"]["side"] == "build"
        assert arestas["db.clientes"]["position"] == "right"
        assert arestas["db.pedidos"]["side"] == "stream"
        assert arestas["db.pedidos"]["position"] == "left"

    def test_edges_are_anchored_on_the_join_not_on_the_scan(self):
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        join = [f for f in facts if f.kind == "spark.sql.join"][0]
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert all(a.subject["node_id"] == join.subject["node_id"] for a in arestas)

    def test_every_edge_of_an_execution_has_a_distinct_id(self):
        """`id` e identidade. Duas arestas do mesmo join tem subject e measures
        iguais quando o subject so carrega o `node_id` do join -- `attrs`, que e
        onde `relation`/`position`/`side` moram, nao entra no calculo do `id`
        (`Fact.id`, `findings/models.py`). Sem `relation`/`position` no subject,
        as duas arestas de `self._broadcast()` colidem no mesmo id.
        """
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert len(arestas) == 2
        assert len({a.id for a in arestas}) == len(arestas)

    def test_self_join_edges_have_distinct_ids(self):
        """`db.a` dos dois lados do mesmo join: mesma `relation`, ambas
        `via_joins=0`. Sem `position` no subject as duas arestas colidiriam de
        novo, porque `relation` sozinha nao distingue os dois lados.
        """
        plano = {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#2], Inner",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.a[id#1]"),
                _scan_node(simple="FileScan parquet db.a[id#2]"),
            ],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert len(arestas) == 2
        assert {a.attrs["relation"] for a in arestas} == {"db.a"}
        assert len({a.id for a in arestas}) == 2

    def test_edges_of_the_same_join_still_share_the_grouping_symbol(self):
        """A correcao de identidade nao pode quebrar `same_subject`
        (`rules/engine.py::_subject_group_key`), que agrupa por
        `subject["symbol"]`. Duas arestas do mesmo join continuam com o mesmo
        `symbol` mesmo com `relation`/`position` diferentes no subject.
        """
        facts = extract_sql_metrics([_start(plan=self._broadcast())], "log.jsonl")
        join = [f for f in facts if f.kind == "spark.sql.join"][0]
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert len(arestas) == 2
        assert {a.subject["symbol"] for a in arestas} == {join.subject["symbol"]}

    def test_sort_merge_join_has_no_build_side_and_says_so(self):
        plano = {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#2], Inner",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.pedidos[id#1]"),
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]

        assert len(arestas) == 2
        assert {a.attrs["side"] for a in arestas} == {"unknown"}
        assert {a.attrs["position"] for a in arestas} == {"left", "right"}

    def test_nested_join_carries_the_distance(self):
        interno = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(simple="FileScan parquet db.a[id#1]"),
                _scan_node(simple="FileScan parquet db.b[id#2]"),
            ],
        }
        plano = {
            "nodeName": "SortMergeJoin",
            "simpleString": "SortMergeJoin [id#1], [id#3], Inner",
            "metadata": {},
            "metrics": [],
            "children": [interno, _scan_node(simple="FileScan parquet db.c[id#3]")],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        externo = [
            f
            for f in facts
            if f.kind == "spark.sql.join" and f.attrs["strategy"] == "SortMergeJoin"
        ][0]
        do_externo = {
            f.attrs["relation"]: f.measures["via_joins"]
            for f in facts
            if f.kind == "spark.sql.join_input"
            and f.subject["node_id"] == externo.subject["node_id"]
        }

        assert do_externo == {"db.a": 1, "db.b": 1, "db.c": 0}

    def test_side_without_a_named_source_is_a_gap_and_the_other_side_survives(self):
        plano = {
            "nodeName": "BroadcastHashJoin",
            "simpleString": "BroadcastHashJoin [id#1], [id#2], Inner, BuildRight, false",
            "metadata": {},
            "metrics": [],
            "children": [
                {
                    "nodeName": "Scan ExistingRDD",
                    "simpleString": "Scan ExistingRDD[id#1]",
                    "metadata": {},
                    "metrics": [],
                    "children": [],
                },
                _scan_node(simple="FileScan parquet db.clientes[id#2]"),
            ],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        arestas = [f for f in facts if f.kind == "spark.sql.join_input"]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "join_side_without_source"
        ]

        assert [a.attrs["relation"] for a in arestas] == ["db.clientes"]
        assert len(lacunas) == 1
        assert lacunas[0].attrs["position"] == "left"

    def test_a_plan_deeper_than_the_ceiling_is_a_named_gap(self):
        from sparkforge.facts.sql_metrics import _TETO_DE_PROFUNDIDADE

        no = _scan_node()
        for _ in range(_TETO_DE_PROFUNDIDADE + 5):
            no = {
                "nodeName": "Project",
                "simpleString": "Project",
                "metadata": {},
                "metrics": [],
                "children": [no],
            }
        facts = extract_sql_metrics([_start(plan=no)], "log.jsonl")
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved" and f.attrs["reason"] == "plan_too_deep"
        ]

        assert len(lacunas) == 1
        assert not [f for f in facts if f.kind == "spark.sql.join_input"]


class TestCustoDaMontagemDoGrafo:
    """Trava que montar o grafo de joins nao repete a arvore inteira por lado.

    `_fontes_abaixo` e `_fonte_do_proprio_no` fazem uma passada pela arvore
    INTEIRA por chamada. A implementacao antiga de `absorb_plan` chamava as
    duas uma vez por lado de CADA join -- quadratico em plano bushy (medido:
    33s numa arvore de 8191 nos). Um teste de tempo em CI compartilhado e
    fragil (maquina lenta, runner ocupado, falso negativo aleatorio); a
    propriedade que realmente importa -- o numero de passadas completas pela
    arvore nao cresce com o numero de joins -- da para travar contando
    chamadas, sem depender de relogio. Por isso a escolha aqui e contagem, nao
    tempo.
    """

    def _bushy(self, level):
        """Arvore binaria completa de joins com `level` niveis de join.

        level=0 -> um scan isolado. Cada nivel dobra a largura: level=5 tem 15
        joins e 16 scans (31 nos); level=10 tem 1023 joins e 1024 scans (2047
        nos) -- ~68x mais joins que a arvore pequena, para expor com clareza
        se a contagem de passadas cresce junto.
        """
        contador = itertools.count()

        def scan():
            n = next(contador)
            return {
                "nodeName": "Scan parquet ",
                "simpleString": f"FileScan parquet db.t{n}[id#{n}]",
                "children": [],
                "metadata": {"Format": "Parquet"},
                "metrics": [],
            }

        def join(esquerda, direita):
            return {
                "nodeName": "SortMergeJoin",
                "simpleString": "SortMergeJoin [id#1], [id#2], Inner",
                "children": [esquerda, direita],
                "metadata": {},
                "metrics": [],
            }

        def construir(nivel):
            if nivel == 0:
                return scan()
            return join(construir(nivel - 1), construir(nivel - 1))

        return construir(level)

    def test_full_tree_passes_do_not_scale_with_join_count(self, monkeypatch):
        import sparkforge.facts.sql_metrics as sql_metrics

        contagem = {"fontes_abaixo": 0, "fonte_do_proprio_no": 0}
        original_fontes_abaixo = sql_metrics._fontes_abaixo
        original_fonte_do_proprio_no = sql_metrics._fonte_do_proprio_no

        def _contando_fontes_abaixo(plano, alvo):
            contagem["fontes_abaixo"] += 1
            return original_fontes_abaixo(plano, alvo)

        def _contando_fonte_do_proprio_no(plano, alvo):
            contagem["fonte_do_proprio_no"] += 1
            return original_fonte_do_proprio_no(plano, alvo)

        monkeypatch.setattr(sql_metrics, "_fontes_abaixo", _contando_fontes_abaixo)
        monkeypatch.setattr(
            sql_metrics, "_fonte_do_proprio_no", _contando_fonte_do_proprio_no
        )

        extract_sql_metrics([_start(plan=self._bushy(5))], "log.jsonl")
        chamadas_pequena = sum(contagem.values())

        contagem["fontes_abaixo"] = 0
        contagem["fonte_do_proprio_no"] = 0

        extract_sql_metrics([_start(plan=self._bushy(10))], "log.jsonl")
        chamadas_grande = sum(contagem.values())

        # Se a montagem do grafo ainda chamasse uma dessas por lado de join,
        # a arvore grande (1023 joins) dispararia ~68x mais chamadas que a
        # pequena (15 joins). A folga de 20 acomoda uma implementacao futura
        # que faca um numero fixo e pequeno de chamadas por arvore, sem
        # reabrir a porta para uma chamada por lado.
        assert chamadas_grande <= chamadas_pequena + 20
