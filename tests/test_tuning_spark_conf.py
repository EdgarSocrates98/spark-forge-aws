"""Testes da configuracao Spark derivada.

O documento de origem poe em letras grandes: `spark.sql.shuffle.partitions`
passa a ser DERIVED, e nao HARDCODED. O que este modulo prova e que a derivacao
carrega a formula, a base medida e o alvo declarado -- e que sem shuffle medido
ela recusa por nome em vez de inventar um numero com aparencia de calculo.
"""
from __future__ import annotations

from sparkforge.findings.models import Fact
from sparkforge.tuning import build_conf_advice

MIB = 1024 * 1024


def _shuffle(write_bytes, stage_id=4):
    return Fact(
        kind="spark.stage.shuffle",
        subject={"type": "stage", "symbol": f"stage-{stage_id}", "stage_id": stage_id},
        measures={
            "read_bytes": 0.0,
            "write_bytes": float(write_bytes),
            "write_records": 1000.0,
            "fetch_wait_ms": 0.0,
        },
    )


def _conf(key, value):
    return Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": key},
        attrs={"key": key, "value": str(value), "app_id": "app-1"},
    )


def _conf_set_no_codigo(key, value):
    return Fact(
        kind="pyspark.conf_set",
        subject={"type": "source_location", "file": "job.py", "line": 12, "symbol": "main"},
        attrs={"key": key, "value": str(value)},
    )


def _conf_no_terraform(key, value):
    return Fact(
        kind="tf.spark_conf",
        subject={"type": "tf_resource", "file": "main.tf", "line": 30, "symbol": f"job#{key}"},
        attrs={"key": key, "value": str(value)},
    )


def _propriedade(relatorio, key="spark.sql.shuffle.partitions"):
    return next(p for p in relatorio["properties"] if p["key"] == key)


def _recusas(relatorio):
    return {r["reason"] for r in relatorio["refused"]}


class TestADerivacao:
    def test_the_value_is_the_measured_shuffle_over_the_target(self):
        """640 MiB de shuffle sobre o alvo de 64 MiB do AQE = 10 particoes."""
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})
        derivado = _propriedade(relatorio)["derived"]

        assert derivado["value"] == 10
        assert derivado["basis"]["shuffle_write_bytes"] == float(640 * MIB)
        assert derivado["basis"]["target_partition_bytes"] == float(64 * MIB)

    def test_a_partial_partition_rounds_up_never_down(self):
        """Arredondar para baixo produz particao maior que o alvo."""
        relatorio = build_conf_advice([_shuffle(65 * MIB)], runtime={"glue": "5.0"})

        assert _propriedade(relatorio)["derived"]["value"] == 2

    def test_the_shuffle_of_every_stage_is_summed(self):
        facts = [_shuffle(320 * MIB, stage_id=1), _shuffle(320 * MIB, stage_id=2)]
        relatorio = build_conf_advice(facts, runtime={"glue": "5.0"})

        assert _propriedade(relatorio)["derived"]["value"] == 10

    def test_the_formula_travels_with_the_number(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        assert "shuffle_write_bytes" in _propriedade(relatorio)["derived"]["formula"]

    def test_an_operator_declared_target_wins_over_the_default(self):
        """O alvo do operador ganha: ele declarou o tamanho que persegue."""
        facts = [
            _shuffle(640 * MIB),
            _conf("spark.sql.adaptive.advisoryPartitionSizeInBytes", str(128 * MIB)),
        ]
        relatorio = build_conf_advice(facts, runtime={"glue": "5.0"})
        derivado = _propriedade(relatorio)["derived"]

        assert derivado["basis"]["target_partition_bytes"] == float(128 * MIB)
        assert derivado["basis"]["target_source"] == "declared"
        assert derivado["value"] == 5

    def test_the_default_target_says_it_is_the_default(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        assert _propriedade(relatorio)["derived"]["basis"]["target_source"] == "spark_default"


class TestAQEMudaOSignificado:
    def test_with_aqe_the_number_is_an_initial_floor(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        assert relatorio["runtime"]["aqe_default"] is True
        assert "coalesc" in _propriedade(relatorio)["explanation"].lower()

    def test_without_aqe_the_number_is_final(self):
        """Glue 3.0 roda Spark 3.1.1, e AQE so e default a partir de 3.2.

        Recomendar "confie no AQE" para Glue 3.0 e erro de versao, e o arquivo
        de conhecimento ja diz isso.
        """
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "3.0"})

        assert relatorio["runtime"]["aqe_default"] is False
        assert "coalesc" not in _propriedade(relatorio)["explanation"].lower()

    def test_the_derived_value_does_not_change_with_aqe(self):
        """A conta e a mesma; o que muda e o que o numero significa."""
        com = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})
        sem = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "3.0"})

        assert _propriedade(com)["derived"]["value"] == _propriedade(sem)["derived"]["value"]


class TestProcedencia:
    def test_a_value_set_in_code_is_named_code(self):
        facts = [
            _shuffle(640 * MIB),
            _conf("spark.sql.shuffle.partitions", "800"),
            _conf_set_no_codigo("spark.sql.shuffle.partitions", "800"),
        ]
        atual = _propriedade(build_conf_advice(facts, runtime={"glue": "5.0"}))["current"]

        assert atual["provenance"] == "code"
        assert atual["value"] == "800"

    def test_a_value_declared_in_terraform_is_named_terraform(self):
        facts = [
            _shuffle(640 * MIB),
            _conf("spark.sql.shuffle.partitions", "800"),
            _conf_no_terraform("spark.sql.shuffle.partitions", "800"),
        ]
        atual = _propriedade(build_conf_advice(facts, runtime={"glue": "5.0"}))["current"]

        assert atual["provenance"] == "terraform"

    def test_effective_without_anyone_asking_is_runtime_or_cluster(self):
        """Ninguem no repositorio pediu: veio do cluster ou do default."""
        facts = [_shuffle(640 * MIB), _conf("spark.sql.shuffle.partitions", "800")]
        atual = _propriedade(build_conf_advice(facts, runtime={"glue": "5.0"}))["current"]

        assert atual["provenance"] == "runtime_or_cluster"

    def test_a_hand_written_default_is_named_as_such(self):
        """O sintoma do 36: configuracao que alguem escreveu e nao muda nada."""
        facts = [
            _shuffle(640 * MIB),
            _conf("spark.sql.shuffle.partitions", "200"),
            _conf_set_no_codigo("spark.sql.shuffle.partitions", "200"),
        ]
        atual = _propriedade(build_conf_advice(facts, runtime={"glue": "5.0"}))["current"]

        assert atual["provenance"] == "spark_default_explicit"

    def test_a_property_nobody_set_is_unset(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})
        atual = _propriedade(relatorio)["current"]

        assert atual["provenance"] == "unset"
        assert atual["value"] == ""


class TestRecusas:
    def test_without_measured_shuffle_there_is_no_proposal(self):
        relatorio = build_conf_advice([], runtime={"glue": "5.0"})

        assert relatorio["properties"] == []
        assert "no_shuffle_measured" in _recusas(relatorio)

    def test_zero_shuffle_is_a_refusal_not_a_zero_partition_proposal(self):
        """Zero particoes nao e configuracao, e um job sem shuffle."""
        relatorio = build_conf_advice([_shuffle(0)], runtime={"glue": "5.0"})

        assert relatorio["properties"] == []
        assert "no_shuffle_measured" in _recusas(relatorio)

    def test_an_unknown_runtime_refuses_by_name(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={})

        assert relatorio["properties"] == []
        assert "runtime_unknown" in _recusas(relatorio)

    def test_every_property_of_the_document_without_basis_is_named(self):
        """Listar a recusa e a diferenca entre nao sei e nao perguntei."""
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})
        sem_base = {
            r["property"] for r in relatorio["refused"] if r["reason"] == "no_measured_basis"
        }

        assert "spark.sql.autoBroadcastJoinThreshold" in sem_base
        assert "spark.executor.memoryOverhead" in sem_base
        assert "spark.speculation" in sem_base

    def test_the_refusals_say_what_would_unlock_them(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        for recusa in relatorio["refused"]:
            assert recusa["detail"].strip(), recusa


class TestSegurancaEFronteira:
    def test_every_proposal_carries_a_safety_level(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        assert _propriedade(relatorio)["safety"] == "REVIEW"

    def test_nothing_applies_and_nothing_is_ranked_by_estimated_gain(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})
        blob = str(relatorio).lower()

        for palavra in ("applied", "estimated_saving", "economia", "expected_gain"):
            assert palavra not in blob

    def test_the_runtime_block_names_the_spark_version(self):
        relatorio = build_conf_advice([_shuffle(640 * MIB)], runtime={"glue": "5.0"})

        assert relatorio["runtime"]["spark_version"].startswith("3.5")
