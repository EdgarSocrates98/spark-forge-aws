"""Testes do relatorio financeiro."""
from __future__ import annotations

from sparkforge.findings.models import Fact
from sparkforge.finops import build_finops_report


def _run(run_id, segundos, workers, dpu, worker="G.2X", state="SUCCEEDED"):
    return Fact(
        kind="glue.job_run",
        subject={
            "type": "job_run",
            "job_name": "etl",
            "job_run_id": run_id,
            "symbol": run_id,
        },
        measures={
            "execution_time_s": segundos,
            "number_of_workers": workers,
            "dpu_seconds": dpu,
        },
        attrs={
            "state": state,
            "worker_type": worker,
            "glue_version": "5.0",
            "autoscaling": False,
            "dpu_source": "derived",
        },
    )


class TestFronteira:
    def _duas_capacidades(self):
        """x10 em 500 s custa 10.000 DPU-s; x20 em 200 s custa 8.000."""
        facts = []
        for i in range(6):
            facts.append(_run(f"a{i}", 500, 10, 10000.0))
        for i in range(6):
            facts.append(_run(f"b{i}", 200, 20, 8000.0))
        return facts

    def test_more_resource_can_cost_less_and_the_report_shows_it(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")
        linhas = {
            (c["worker_type"], c["number_of_workers"]): c
            for c in relatorio["frontier"]
        }

        vinte = linhas[("G.2X", 20)]
        dez = linhas[("G.2X", 10)]

        # O DOBRO do recurso, e mais barato -- porque o tempo caiu para 40%.
        assert vinte["number_of_workers"] > dez["number_of_workers"]
        assert vinte["cost_per_run_p95"] < dez["cost_per_run_p95"]
        assert vinte["runtime_p95_s"] < dez["runtime_p95_s"]

    def test_the_frontier_is_ordered_by_cost(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")
        custos = [c["cost_per_run_p95"] for c in relatorio["frontier"]]

        assert custos == sorted(custos)

    def test_relative_cost_is_against_the_cheapest(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")

        assert relatorio["frontier"][0]["cost_relative"] == 1.0
        assert relatorio["frontier"][1]["cost_relative"] > 1.0

    def test_a_capacity_without_cost_is_named_not_dropped(self):
        facts = self._duas_capacidades()
        facts.append(
            Fact(
                kind="glue.job_run",
                subject={
                    "type": "job_run",
                    "job_name": "etl",
                    "job_run_id": "s1",
                    "symbol": "s1",
                },
                measures={"execution_time_s": 300, "number_of_workers": 10},
                attrs={
                    "state": "SUCCEEDED",
                    "worker_type": "G.4X",
                    "glue_version": "5.0",
                    "autoscaling": True,
                    "dpu_source": "",
                },
            )
        )
        relatorio = build_finops_report(facts, job_name="etl")

        assert any(
            r["reason"] == "cost_unobservable" for r in relatorio["refused"]
        )
        assert not [
            c for c in relatorio["frontier"] if c["worker_type"] == "G.4X"
        ]
