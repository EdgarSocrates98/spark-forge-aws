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
