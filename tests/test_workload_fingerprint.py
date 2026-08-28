"""Testes da montagem do fingerprint a partir dos facts."""
from __future__ import annotations

from sparkforge.findings.models import Fact
from sparkforge.workload.fingerprint import build_fingerprint


def _scan(bytes_read=1000, files_read=10, execution_id=0, node_id=1):
    return Fact(
        kind="spark.sql.scan",
        subject={
            "type": "plan_node",
            "node_id": node_id,
            "operator": "Scan parquet",
            "relation": "db.clientes",
            "symbol": f"{execution_id}:{node_id}",
            "execution_id": execution_id,
        },
        measures={"bytes_read": bytes_read, "files_read": files_read},
        attrs={"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
    )


def _history(*totais_de_bytes):
    """Um "run anterior" por elemento, cada um como a lista de facts daquele run.

    `glue.job_run.distribution` NAO serve aqui: ele carrega duracao e DPU, nunca
    bytes -- `glue.get_job_runs` nao publica volume lido. O historico de uma
    metrica de volume so pode vir da mesma medicao repetida.
    """
    return [[_scan(bytes_read=total)] for total in totais_de_bytes]


def _task_duration(p50_ms=100, p95_ms=1000):
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": "stage-1", "stage_id": 1},
        measures={"p50_ms": p50_ms, "p95_ms": p95_ms, "task_count": 20},
    )


class TestEixosMedidos:
    def test_scan_above_p99_is_extreme(self):
        fp = build_fingerprint(
            [_scan(bytes_read=5000)],
            history=_history(100, 200, 300, 400, 500),
            job_name="etl",
            job_run_id="jr_1",
        )

        assert fp.axes["scan_intensity"].value == "extreme"
        assert fp.axes["scan_intensity"].confidence == "measured"
        assert fp.axes["scan_intensity"].evidence

    def test_scan_below_p50_is_low(self):
        fp = build_fingerprint(
            [_scan(bytes_read=100)],
            history=_history(1000, 2000, 3000, 4000, 5000),
            job_name="etl",
            job_run_id="jr_1",
        )

        assert fp.axes["scan_intensity"].value == "low"

    def test_history_shorter_than_three_runs_refuses_to_claim_a_p99(self):
        fp = build_fingerprint(
            [_scan(bytes_read=5000)],
            history=_history(100, 200),
            job_name="etl",
            job_run_id="jr_1",
        )
        eixo = fp.axes["scan_intensity"]

        assert eixo.value == "unknown"
        assert eixo.missing == "history_too_short"

    def test_skew_uses_the_run_itself_not_the_history(self):
        fp = build_fingerprint(
            [_task_duration(p50_ms=100, p95_ms=1000)], job_name="etl", job_run_id="jr_1"
        )
        eixo = fp.axes["skew_risk"]

        # p95/p50 = 10x. Sem historico nenhum nos facts, e mesmo assim medido.
        assert eixo.confidence == "measured"
        assert eixo.value in ("high", "extreme")


class TestSemLastro:
    def test_no_history_leaves_volume_axes_unknown_with_the_command(self):
        fp = build_fingerprint([_scan()], job_name="etl", job_run_id="jr_1")
        eixo = fp.axes["scan_intensity"]

        assert eixo.value == "unknown"
        assert eixo.missing
        assert "collect glue-job-runs" in eixo.collect_command

    def test_axes_that_do_not_need_history_stay_filled(self):
        fp = build_fingerprint(
            [_scan(), _task_duration()], job_name="etl", job_run_id="jr_1"
        )

        assert fp.axes["scan_intensity"].value == "unknown"
        assert fp.axes["skew_risk"].value != "unknown"
        assert fp.axes["file_pressure"].value != "unknown"

    def test_no_axis_is_medium_by_omission(self):
        fp = build_fingerprint([], job_name="etl", job_run_id="jr_1")

        for nome, eixo in fp.axes.items():
            assert eixo.value == "unknown" or eixo.basis, nome

    def test_unknown_axes_are_listed_so_nobody_has_to_scan_field_by_field(self):
        fp = build_fingerprint([], job_name="etl", job_run_id="jr_1")

        assert set(fp.unknown_axes()) == set(fp.axes)


class TestDeclarado:
    def _declared(self, primary="db.clientes"):
        attrs = {"primary_source": primary} if primary else {}
        return Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "etl"},
            measures={"sla_minutes": 45},
            attrs=attrs,
        )

    def test_declared_axis_is_never_measured(self):
        fp = build_fingerprint(
            [self._declared(), _scan()],
            history=_history(100, 200, 300),
            job_name="etl",
            job_run_id="jr_1",
        )

        assert fp.axes["sla_class"].confidence == "declared"
        assert fp.axes["sla_class"].confidence != "measured"

    def test_declaration_for_another_job_is_ignored(self):
        outro = self._declared()
        outro = Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "outro-job"},
            measures={"sla_minutes": 45},
        )
        fp = build_fingerprint([outro], job_name="etl", job_run_id="jr_1")

        assert fp.axes["sla_class"].value == "unknown"

    def test_declared_source_that_no_scan_matches_is_a_named_gap(self):
        fp = build_fingerprint(
            [self._declared(primary="db.inexistente"), _scan()],
            job_name="etl",
            job_run_id="jr_1",
        )
        eixo = fp.axes["primary_input_class"]

        assert eixo.value == "unknown"
        assert eixo.missing == "declared_source_not_observed"


class TestSerializacao:
    def test_to_dict_carries_every_axis_and_the_run(self):
        fp = build_fingerprint(
            [_scan()], history=_history(100, 200, 300), job_name="etl", job_run_id="jr_1"
        )
        saida = fp.to_dict()

        assert saida["job_name"] == "etl"
        assert saida["job_run_id"] == "jr_1"
        assert set(saida["axes"]) == set(fp.axes)
        assert saida["source_count"] == 1
