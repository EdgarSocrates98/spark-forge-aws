"""Testes do diagnostico de timeout.

Quatro mecanismos distintos que o operador chama pelo mesmo nome, e a evidencia
que separa cada um esta em fonte diferente: o estado do run Glue, a razao com
que o executor foi removido, e a razao da stage que falhou.
"""
from __future__ import annotations

from sparkforge.facts.timeout_diagnosis import extract_timeout_diagnosis
from sparkforge.findings.models import Fact


def _run(state="TIMEOUT", run_id="jr_1"):
    return Fact(
        kind="glue.job_run",
        subject={"type": "job_run", "job_name": "etl", "job_run_id": run_id, "symbol": run_id},
        measures={"execution_time_s": 3600, "number_of_workers": 10, "timeout_min": 60},
        attrs={"state": state, "worker_type": "G.2X", "glue_version": "5.0"},
    )


def _executor_lost(reason):
    return Fact(
        kind="spark.executor.lost",
        subject={"type": "job_run", "symbol": "3"},
        attrs={"reason": reason, "heap_oom_in_log": False},
    )


def _stage_failure(reason, stage_id=8):
    return Fact(
        kind="spark.stage.failure",
        subject={"type": "stage", "symbol": f"stage-{stage_id}", "stage_id": stage_id},
        attrs={"reason": reason},
    )


def _diag(facts):
    return [f for f in facts if f.kind == "spark.timeout.diagnosis"]


def _lacunas(facts):
    return [f for f in facts if f.kind == "spark.timeout.unresolved"]


class TestAsQuatroCategorias:
    def test_glue_timeout_state_alone_is_wall_clock(self):
        """O estado do Glue e a DEFINICAO do relogio de parede, nao um indicio.

        A AWS define `TIMEOUT` como a execucao que consumiu o tempo maximo
        antes de terminar. Isso diz QUE o relogio acabou, e nada sobre por que.
        """
        diagnosticos = _diag(extract_timeout_diagnosis([_run()], "facts.json"))

        assert len(diagnosticos) == 1
        assert diagnosticos[0].attrs["category"] == "wall_clock"
        assert diagnosticos[0].attrs["basis"] == "glue_job_run_state"

    def test_executor_heartbeat_phrase_decides_heartbeat(self):
        facts = [_executor_lost("Executor heartbeat timed out after 130000 ms")]
        diagnosticos = _diag(extract_timeout_diagnosis(facts, "facts.json"))

        assert diagnosticos[0].attrs["category"] == "heartbeat"
        assert diagnosticos[0].attrs["basis"] == "executor_removed_reason"

    def test_broadcast_phrase_decides_broadcast(self):
        facts = [_stage_failure("Could not execute broadcast in 300 secs.")]
        diagnosticos = _diag(extract_timeout_diagnosis(facts, "facts.json"))

        assert diagnosticos[0].attrs["category"] == "broadcast"
        assert diagnosticos[0].attrs["basis"] == "stage_failure_reason"

    def test_rpc_phrase_decides_network(self):
        facts = [_stage_failure("Futures timed out after [120 seconds]")]
        diagnosticos = _diag(extract_timeout_diagnosis(facts, "facts.json"))

        assert diagnosticos[0].attrs["category"] == "network"

    def test_evidence_text_is_the_literal_phrase(self):
        """Categoria sem a frase que a produziu e opiniao."""
        frase = "Could not execute broadcast in 300 secs. You can increase the timeout"
        diagnosticos = _diag(extract_timeout_diagnosis([_stage_failure(frase)], "facts.json"))

        assert frase in diagnosticos[0].attrs["evidence_text"]


class TestPrecedencia:
    def test_precedence_keeps_what_it_did_not_choose(self):
        """Heartbeat vence wall-clock, e o preterido continua legivel.

        Escolher em silencio seria escolher pelo operador: o run estourou o
        relogio do Glue PORQUE o executor morreu, e quem le precisa dos dois.
        """
        facts = [_run(), _executor_lost("Executor heartbeat timed out after 130000 ms")]
        diagnostico = _diag(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert diagnostico.attrs["category"] == "heartbeat"
        assert diagnostico.attrs["also_seen"] == ["wall_clock"]

    def test_network_wins_over_broadcast_and_wall_clock(self):
        facts = [
            _run(),
            _stage_failure("Could not execute broadcast in 300 secs.", stage_id=8),
            _stage_failure("Futures timed out after [120 seconds]", stage_id=9),
        ]
        diagnostico = _diag(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert diagnostico.attrs["category"] == "network"
        assert diagnostico.attrs["also_seen"] == ["broadcast", "wall_clock"]

    def test_a_single_signal_has_an_empty_also_seen(self):
        diagnostico = _diag(extract_timeout_diagnosis([_run()], "facts.json"))[0]

        assert diagnostico.attrs["also_seen"] == []


class TestRecusas:
    def test_no_signal_produces_no_diagnosis_and_a_named_gap(self):
        saida = extract_timeout_diagnosis([_run(state="SUCCEEDED")], "facts.json")

        assert not _diag(saida)
        assert [f.attrs["reason"] for f in _lacunas(saida)] == ["no_timeout_evidence"]

    def test_timeout_state_without_log_says_what_is_missing(self):
        """`wall_clock` e a resposta honesta, e a lacuna diz o que a refina."""
        saida = extract_timeout_diagnosis([_run()], "facts.json")

        assert _diag(saida)
        lacuna = _lacunas(saida)[0]
        assert lacuna.attrs["reason"] == "state_without_log"
        assert "collect event-log" in lacuna.attrs["detail"]

    def test_an_event_log_without_timeout_signal_is_not_a_gap_by_itself(self):
        """Log lido, run saudavel: a resposta e `no_timeout_evidence`, uma so."""
        facts = [_run(state="SUCCEEDED"), _stage_failure("Job aborted due to stage failure")]
        saida = extract_timeout_diagnosis(facts, "facts.json")

        assert not _diag(saida)
        assert [f.attrs["reason"] for f in _lacunas(saida)] == ["no_timeout_evidence"]

    def test_an_empty_pool_produces_nothing_at_all(self):
        """Sem fact nenhum nao ha nem diagnostico nem lacuna: nada foi lido."""
        assert extract_timeout_diagnosis([], "facts.json") == []


class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        casos = [
            [_run()],
            [_run(state="SUCCEEDED")],
            [_executor_lost("Executor heartbeat timed out after 130000 ms")],
            [_stage_failure("Futures timed out after [120 seconds]")],
        ]
        emitidos = 0
        for pool in casos:
            for fact in extract_timeout_diagnosis(pool, "facts.json"):
                validate_fact(fact.to_dict())
                emitidos += 1

        assert emitidos

    def test_nothing_recommends_a_new_timeout_value(self):
        """Derivar valor de configuracao e outro subprojeto (criterio 17)."""
        facts = [_run(), _executor_lost("Executor heartbeat timed out after 130000 ms")]
        blob = str([f.to_dict() for f in extract_timeout_diagnosis(facts, "facts.json")]).lower()

        for palavra in ("recommend", "aumente", "increase to", "suggested_value"):
            assert palavra not in blob


def _conf(key, value):
    return Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": key},
        attrs={"key": key, "value": value, "app_id": "app-1"},
    )


def _relacoes(facts):
    return [f for f in facts if f.kind == "spark.timeout.relation"]


class TestOsSintomasAoLado:
    """O fact mede; o limiar e da regra.

    Sem os sintomas no proprio fact, `SF-TIMEOUT-001` precisaria correlacionar
    quatro kinds diferentes dentro do `when`, e a DSL do catalogo casa um fact
    por clausula.
    """

    def test_skew_ratio_travels_with_the_diagnosis(self):
        facts = [
            _run(),
            Fact(
                kind="spark.stage.task_duration",
                subject={"type": "stage", "symbol": "s8", "stage_id": 8},
                measures={"p50_ms": 100.0, "p95_ms": 1140.0, "task_count": 20},
            ),
        ]
        diagnostico = _diag(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert diagnostico.measures["skew_p95_over_p50"] == 11.4

    def test_spill_and_gc_and_executor_loss_travel_too(self):
        facts = [
            _run(),
            Fact(
                kind="spark.stage.spill",
                subject={"type": "stage", "symbol": "s8", "stage_id": 8},
                measures={
                    "memory_spill_bytes": 300.0,
                    "disk_spill_bytes": 100.0,
                    "input_bytes": 1000.0,
                },
            ),
            Fact(
                kind="spark.stage.gc",
                subject={"type": "stage", "symbol": "s8", "stage_id": 8},
                measures={"gc_time_ms": 300.0, "task_time_ms": 1000.0},
            ),
            _executor_lost("Container killed by YARN"),
        ]
        diagnostico = _diag(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert diagnostico.measures["spill_over_input"] == 0.4
        assert diagnostico.measures["gc_ratio"] == 0.3
        assert diagnostico.measures["executor_lost_count"] == 1

    def test_a_symptom_without_source_is_absent_never_zero(self):
        """Zero diria que foi medido e deu zero. Ausente diz que nao foi."""
        diagnostico = _diag(extract_timeout_diagnosis([_run()], "facts.json"))[0]

        assert "skew_p95_over_p50" not in diagnostico.measures
        assert "spill_over_input" not in diagnostico.measures
        assert diagnostico.measures["executor_lost_count"] == 0


class TestRelacaoEntreAsDuasPropriedades:
    """`network.timeout = 120s` nao e certo nem errado sozinho.

    `heartbeatInterval >= network.timeout` e errado sempre, porque quebra o
    mecanismo que detecta executor morto. A relacao e conferivel; o valor
    isolado nao e.
    """

    def test_both_keys_observed_produce_the_relation_in_seconds(self):
        facts = [
            _run(state="SUCCEEDED"),
            _conf("spark.executor.heartbeatInterval", "10s"),
            _conf("spark.network.timeout", "120s"),
        ]
        relacao = _relacoes(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert relacao.measures["heartbeat_s"] == 10.0
        assert relacao.measures["network_timeout_s"] == 120.0

    def test_a_value_without_suffix_is_read_as_seconds(self):
        facts = [
            _conf("spark.executor.heartbeatInterval", "10"),
            _conf("spark.network.timeout", "1min"),
        ]
        relacao = _relacoes(extract_timeout_diagnosis(facts, "facts.json"))[0]

        assert relacao.measures["heartbeat_s"] == 10.0
        assert relacao.measures["network_timeout_s"] == 60.0

    def test_only_one_key_observed_is_a_named_gap_not_a_comparison(self):
        facts = [_conf("spark.network.timeout", "120s")]
        saida = extract_timeout_diagnosis(facts, "facts.json")

        assert not _relacoes(saida)
        assert any(f.attrs["reason"] == "conf_not_observed" for f in _lacunas(saida))

    def test_no_conf_at_all_produces_no_relation_gap(self):
        """Sem configuracao nenhuma, a ausencia ja e a resposta do log."""
        saida = extract_timeout_diagnosis([_run(state="SUCCEEDED")], "facts.json")

        assert not [f for f in _lacunas(saida) if f.attrs["reason"] == "conf_not_observed"]

    def test_an_unparseable_duration_is_a_gap_not_a_guess(self):
        facts = [
            _conf("spark.executor.heartbeatInterval", "dez segundos"),
            _conf("spark.network.timeout", "120s"),
        ]
        saida = extract_timeout_diagnosis(facts, "facts.json")

        assert not _relacoes(saida)
        assert any(f.attrs["reason"] == "conf_not_observed" for f in _lacunas(saida))
