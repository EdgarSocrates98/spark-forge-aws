"""Testes do resumo de utilizacao.

A seccao 37 do documento de origem pede que o financeiro encontre desperdicio, e
avisa no mesmo paragrafo que utilizacao baixa com skew extremo NAO significa
reduzir workers: noventa por cento dos executores podem estar ociosos porque uma
task ficou catorze minutos numa particao torta. Reduzir worker ali nao resolve a
causa.

Este modulo correlaciona as duas medidas num fact so, para que a regra possa
julgar as duas na mesma clausula.
"""
from __future__ import annotations

from sparkforge.facts.utilization import extract_utilization
from sparkforge.findings.models import Fact


def _metric(name, p50=None, p95=None):
    measures = {"min": 0.0, "max": 100.0, "datapoints": 12.0}
    if p50 is not None:
        measures["p50"] = float(p50)
    if p95 is not None:
        measures["p95"] = float(p95)
    return Fact(
        kind="glue.metric",
        subject={"type": "job_run", "symbol": "etl"},
        measures=measures,
        attrs={"name": name, "stat": "Average", "period_s": 60},
    )


def _task_duration(p50, p95, stage_id=4):
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": f"stage-{stage_id}", "stage_id": stage_id},
        measures={"p50_ms": float(p50), "p95_ms": float(p95), "task_count": 20.0},
    )


def _resumo(facts):
    return [f for f in facts if f.kind == "glue.utilization.summary"]


def _lacunas(facts):
    return [f for f in facts if f.kind == "glue.utilization.unresolved"]


class TestOResumo:
    def test_worker_utilization_is_carried_from_cloudwatch(self):
        facts = [_metric("glue.driver.workerUtilization", p50=0.31)]
        resumo = _resumo(extract_utilization(facts, "facts.json"))[0]

        assert resumo.measures["worker_utilization_p50"] == 0.31

    def test_memory_and_disk_travel_together(self):
        facts = [
            _metric("glue.driver.workerUtilization", p50=0.31),
            _metric("glue.ALL.memory.total.used.percentage", p95=22.0),
            _metric("glue.driver.disk.used.percentage", p95=9.0),
        ]
        resumo = _resumo(extract_utilization(facts, "facts.json"))[0]

        assert resumo.measures["memory_used_pct_p95"] == 22.0
        assert resumo.measures["disk_used_pct_p95"] == 9.0

    def test_the_skew_ratio_comes_from_the_event_log(self):
        facts = [
            _metric("glue.driver.workerUtilization", p50=0.31),
            _task_duration(100.0, 1140.0),
        ]
        resumo = _resumo(extract_utilization(facts, "facts.json"))[0]

        assert resumo.measures["skew_p95_over_p50"] == 11.4

    def test_the_worst_stage_wins_the_skew_ratio(self):
        """Skew e o pior stage, e nao a media: a media dilui exatamente o
        stage que segura o job."""
        facts = [
            _metric("glue.driver.workerUtilization", p50=0.31),
            _task_duration(100.0, 110.0, stage_id=1),
            _task_duration(100.0, 1140.0, stage_id=2),
        ]
        resumo = _resumo(extract_utilization(facts, "facts.json"))[0]

        assert resumo.measures["skew_p95_over_p50"] == 11.4

    def test_a_measure_without_source_is_absent_never_zero(self):
        """Zero por cento de memoria usada seria uma afirmacao, e falsa."""
        facts = [_metric("glue.driver.workerUtilization", p50=0.31)]
        resumo = _resumo(extract_utilization(facts, "facts.json"))[0]

        assert "memory_used_pct_p95" not in resumo.measures
        assert "disk_used_pct_p95" not in resumo.measures
        assert "skew_p95_over_p50" not in resumo.measures


class TestRecusas:
    def test_without_worker_utilization_there_is_no_summary(self):
        """Utilizacao e o eixo da pergunta: sem ela nao ha o que resumir."""
        saida = extract_utilization([_task_duration(100.0, 1140.0)], "facts.json")

        assert not _resumo(saida)
        assert [f.attrs["reason"] for f in _lacunas(saida)] == ["utilization_not_observed"]

    def test_the_gap_says_which_metric_would_fill_it(self):
        saida = extract_utilization([_task_duration(100.0, 1140.0)], "facts.json")

        assert "workerUtilization" in _lacunas(saida)[0].attrs["detail"]
        assert "collect cloudwatch" in _lacunas(saida)[0].attrs["detail"]

    def test_an_empty_pool_produces_nothing_at_all(self):
        assert extract_utilization([], "facts.json") == []

    def test_nothing_quantifies_a_saving(self):
        """A economia possivel exigiria o custo do run que NAO aconteceu."""
        facts = [_metric("glue.driver.workerUtilization", p50=0.31)]
        blob = str([f.to_dict() for f in extract_utilization(facts, "facts.json")]).lower()

        for palavra in ("saving", "economia", "desperd", "waste"):
            assert palavra not in blob


class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        casos = [
            [_metric("glue.driver.workerUtilization", p50=0.31), _task_duration(100.0, 1140.0)],
            [_task_duration(100.0, 1140.0)],
        ]
        emitidos = 0
        for pool in casos:
            for fact in extract_utilization(pool, "facts.json"):
                validate_fact(fact.to_dict())
                emitidos += 1

        assert emitidos
