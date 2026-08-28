"""Testes da escolha de capacidade sob restricao de SLA."""
from __future__ import annotations

from sparkforge.capacity import build_capacity_plan
from sparkforge.findings.models import Fact


def _run(run_id, segundos, worker="G.2X", workers=10, dpu=1000.0, autoscaling=False):
    measures = {"execution_time_s": segundos, "number_of_workers": workers}
    if dpu is not None:
        measures["dpu_seconds"] = dpu
    return Fact(
        kind="glue.job_run",
        subject={
            "type": "job_run",
            "job_name": "etl",
            "job_run_id": run_id,
            "symbol": run_id,
        },
        measures=measures,
        attrs={
            "state": "SUCCEEDED",
            "worker_type": worker,
            "glue_version": "5.0",
            "autoscaling": autoscaling,
            "dpu_source": "derived",
        },
    )


def _scan(bytes_read):
    return Fact(
        kind="spark.sql.scan",
        subject={
            "type": "plan_node",
            "node_id": 1,
            "operator": "Scan parquet",
            "relation": "db.pedidos",
            "symbol": "0:1",
            "execution_id": 0,
        },
        measures={"bytes_read": bytes_read},
        attrs={"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
    )


def _declarado(sla=10, alvo=0.9, tolerancia=0.25):
    measures = {"sla_minutes": sla}
    if alvo is not None:
        measures["reliability_target"] = alvo
    if tolerancia is not None:
        measures["volume_tolerance"] = tolerancia
    return Fact(
        kind="workload.declared",
        subject={"type": "job_run", "symbol": "etl"},
        measures=measures,
    )


def _historico(*runs):
    """Cada elemento e o conjunto de facts de UM run anterior."""
    return list(runs)


class TestEscolha:
    def _tres_capacidades(self, volume=1000):
        """G.1X x10 estoura o SLA; G.2X x10 e G.2X x20 cabem."""
        historico = []
        for i in range(10):
            historico.append(
                [_run(f"a{i}", 900, worker="G.1X", workers=10, dpu=900.0), _scan(volume)]
            )
        for i in range(10):
            historico.append(
                [_run(f"b{i}", 500, worker="G.2X", workers=10, dpu=1000.0), _scan(volume)]
            )
        for i in range(10):
            historico.append(
                [_run(f"c{i}", 200, worker="G.2X", workers=20, dpu=2000.0), _scan(volume)]
            )
        return historico

    def test_chooses_the_cheapest_that_fits_not_the_fastest(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )

        # G.2X x20 e o mais rapido e o mais caro. A escolha certa e o do meio.
        assert plano.chosen is not None
        assert plano.chosen.worker_type == "G.2X"
        assert plano.chosen.number_of_workers == 10

    def test_candidates_are_ordered_by_cost(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )
        custos = [c.dpu_seconds_p95 for c in plano.candidates]

        assert custos == sorted(custos)

    def test_the_capacity_that_misses_the_sla_is_never_chosen(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )
        estourou = [c for c in plano.candidates if c.worker_type == "G.1X"][0]

        assert estourou.meets_sla is False
        assert plano.chosen is not estourou

    def test_when_nothing_fits_it_refuses_instead_of_picking_the_least_bad(self):
        plano = build_capacity_plan(
            [_declarado(sla=1), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is None
        assert len(plano.candidates) == 3
        assert all(c.meets_sla is False for c in plano.candidates)


class TestResolucao:
    def test_a_target_finer_than_the_evidence_is_refused(self):
        historico = [
            [_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(28)
        ]
        plano = build_capacity_plan(
            [_declarado(alvo=0.99), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        candidato = plano.candidates[0]

        # 1/28 = 3,6%. Afirmar 99% exigiria distinguir 1%.
        assert candidato.meets_sla is False
        assert plano.chosen is None
        recusa = [r for r in plano.refused if r["reason"] == "resolution_too_coarse"][0]
        assert recusa["runs_comparable"] == 28
        assert recusa["runs_needed"] >= 100

    def test_the_same_history_fits_a_coarser_target(self):
        historico = [
            [_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(28)
        ]
        plano = build_capacity_plan(
            [_declarado(alvo=0.9), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is not None


class TestComparabilidade:
    def test_only_runs_within_the_volume_tolerance_are_counted(self):
        # 20 runs de dia pequeno, todos rapidos; 5 de dia grande, todos lentos.
        historico = [[_run(f"p{i}", 100, dpu=1000.0), _scan(100)] for i in range(20)]
        historico += [[_run(f"g{i}", 900, dpu=1000.0), _scan(1000)] for i in range(5)]

        plano = build_capacity_plan(
            [_declarado(sla=10, alvo=0.8), _scan(1000)],  # hoje e dia GRANDE
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        candidato = plano.candidates[0]

        # Os 20 dias pequenos estao fora da faixa de 1000 +/- 25%.
        assert candidato.runs_total == 25
        assert candidato.runs_comparable == 5

    def test_the_volume_filter_can_flip_the_answer(self):
        historico = [[_run(f"p{i}", 100, dpu=1000.0), _scan(100)] for i in range(20)]
        historico += [[_run(f"g{i}", 900, dpu=1000.0), _scan(1000)] for i in range(5)]

        # SLA de 5 min: os dias pequenos cabem, os grandes nao.
        grande = build_capacity_plan(
            [_declarado(sla=5, alvo=0.8), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        pequeno = build_capacity_plan(
            [_declarado(sla=5, alvo=0.8), _scan(100)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert pequeno.chosen is not None
        assert grande.chosen is None

    def test_a_run_without_measured_volume_is_discarded_and_counted(self):
        historico = [[_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(10)]
        historico += [[_run("sem_scan", 500, dpu=1000.0)] for _ in range(1)]

        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.discarded_runs["volume_unknown"] == 1


class TestCusto:
    def test_capacity_without_measured_dpu_is_refused_not_ranked(self):
        historico = [
            [_run(f"a{i}", 100, worker="G.2X", workers=10, dpu=1000.0), _scan(1000)]
            for i in range(10)
        ]
        historico += [
            [
                _run(f"s{i}", 100, worker="G.2X", workers=10, dpu=None, autoscaling=True),
                _scan(1000),
            ]
            for i in range(10)
        ]

        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert [r["reason"] for r in plano.refused] == ["cost_unobservable"]
        assert all(c.autoscaling is False for c in plano.candidates)


class TestSemLastro:
    def test_without_a_declaration_the_plan_is_unknown(self):
        plano = build_capacity_plan(
            [_scan(1000)],
            history=[[_run("a", 100), _scan(1000)]],
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is None
        assert plano.sla_minutes is None
        assert any(r["reason"] == "sla_not_declared" for r in plano.refused)

    def test_a_single_observed_capacity_says_there_is_nothing_to_compare(self):
        historico = [[_run(f"b{i}", 100, dpu=1000.0), _scan(1000)] for i in range(10)]
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert len(plano.candidates) == 1
        assert plano.chosen is not None
        assert plano.only_one_capacity_observed is True


class TestSeguranca:
    def test_every_candidate_is_review_and_nothing_applies(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=[[_run(f"b{i}", 100, dpu=1000.0), _scan(1000)] for i in range(10)],
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert all(c.safety == "REVIEW" for c in plano.candidates)
        assert not hasattr(plano, "apply")
