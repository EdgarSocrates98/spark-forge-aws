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


class TestCustoPorDesfecho:
    def _declarado(self, sla=10, alvo=0.8):
        return Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "etl"},
            measures={"sla_minutes": sla, "reliability_target": alvo},
        )

    def _misto(self):
        """x10 e barata por run e estoura o SLA em 4 de 10.

        x20 custa mais por run e cumpre sempre. Os 4 runs que estouram nao sao
        so mais lentos: em 900s custam mais DPU-segundos que a media dos que
        cumprem, o suficiente para o custo por desfecho (dividido so pelos 6
        que serviram) superar o de x20 -- mesmo com x10 ainda vencendo por
        run (frontier).
        """
        facts = [self._declarado()]
        for i in range(6):
            facts.append(_run(f"a{i}", 300, 10, 6000.0))
        for i in range(4):
            facts.append(_run(f"b{i}", 900, 10, 15300.0))  # estoura 10 min
        for i in range(10):
            facts.append(_run(f"c{i}", 400, 20, 16000.0))
        return facts

    def test_cheaper_per_run_can_be_costlier_per_outcome(self):
        relatorio = build_finops_report(self._misto(), job_name="etl")
        por_desfecho = {
            (c["worker_type"], c["number_of_workers"]): c
            for c in relatorio["per_sla_outcome"]
        }

        dez = por_desfecho[("G.2X", 10)]
        vinte = por_desfecho[("G.2X", 20)]

        assert dez["reliability"] < vinte["reliability"]
        assert dez["cost_per_sla_success"] > vinte["cost_per_sla_success"]

    def test_short_term_and_long_term_can_disagree(self):
        relatorio = build_finops_report(self._misto(), job_name="etl")

        mais_barata_por_run = relatorio["frontier"][0]
        mais_barata_por_desfecho = relatorio["per_sla_outcome"][0]

        assert (
            mais_barata_por_run["number_of_workers"]
            != mais_barata_por_desfecho["number_of_workers"]
        )

    def test_a_capacity_without_resolution_leaves_the_long_term_view(self):
        facts = [self._declarado(alvo=0.99)]
        for i in range(10):
            facts.append(_run(f"a{i}", 300, 10, 6000.0))
        relatorio = build_finops_report(facts, job_name="etl")

        # 1/10 nao sustenta afirmacao de 99%.
        assert relatorio["per_sla_outcome"] == []
        assert any(
            r["reason"] == "resolution_too_coarse" for r in relatorio["refused"]
        )
        # E continua na visao de curto prazo.
        assert relatorio["frontier"]

    def test_without_a_declared_sla_there_is_no_long_term_view(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(facts, job_name="etl")

        assert relatorio["per_sla_outcome"] == []
        assert any(r["reason"] == "sla_not_declared" for r in relatorio["refused"])


class TestSintomas:
    def test_symptoms_sit_beside_the_cost_without_being_subtracted(self):
        facts = [_run("a1", 300, 10, 6000.0)]
        facts.append(
            Fact(
                kind="spark.stage.task_duration",
                subject={"type": "stage", "symbol": "s1", "stage_id": 1},
                measures={"p50_ms": 100, "p95_ms": 1140, "task_count": 20},
            )
        )
        relatorio = build_finops_report(facts, job_name="etl")

        assert relatorio["symptoms"]["skew_p95_over_p50"] == 11.4
        blob = str(relatorio).lower()
        assert "desperd" not in blob
        assert "waste" not in blob


class TestAlavanca:
    def _finding(self, rule_id):
        from sparkforge.findings.models import Finding

        return Finding(
            rule_id=rule_id,
            title=f"achado {rule_id}",
            severity="P1",
            confidence="high",
            status="confirmed",
            subject={"type": "source_location", "file": "etl.py", "line": 10},
            evidence=["f_abc123"],
        )

    def test_code_findings_are_listed_under_the_code_lever(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts,
            job_name="etl",
            findings=[self._finding("SF-PY-004"), self._finding("SF-PQ-002")],
        )

        codigo = relatorio["levers"]["code"]
        assert sorted(f["rule_id"] for f in codigo["findings"]) == [
            "SF-PQ-002",
            "SF-PY-004",
        ]

    def test_a_code_finding_never_appears_under_the_capacity_lever(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts, job_name="etl", findings=[self._finding("SF-PY-004")]
        )

        capacidade = str(relatorio["levers"]["capacity"])
        assert "SF-PY-004" not in capacidade

    def test_infrastructure_findings_are_not_code(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts, job_name="etl", findings=[self._finding("SF-GLUE-007")]
        )

        assert not relatorio["levers"]["code"]["findings"]

    def test_no_finding_and_sized_capacity_is_an_answer_not_a_gap(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(facts, job_name="etl", findings=[])

        assert relatorio["levers"]["none_found"] is True

    def test_findings_are_never_ranked_by_estimated_saving(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts,
            job_name="etl",
            findings=[self._finding("SF-PY-004"), self._finding("SF-UI-006")],
        )

        blob = str(relatorio).lower()
        for palavra in ("estimated_saving", "economia", "saving"):
            assert palavra not in blob
