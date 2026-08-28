"""Testes do extrator de metricas SQL por no do plano."""
from __future__ import annotations

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
