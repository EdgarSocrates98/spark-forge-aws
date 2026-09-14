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

        assert "spark.speculation" in sem_base
        # Overhead, heap, split e broadcast deixaram de ser `no_measured_basis`:
        # sem a medida, cada um sai recusado pela medida que falta.
        por_chave = {r["property"]: r["reason"] for r in relatorio["refused"]}
        assert por_chave["spark.executor.memoryOverhead"] == "sem_memoria_por_executor"
        assert por_chave["spark.executor.memory"] == "sem_memoria_por_executor"
        assert por_chave["spark.sql.files.maxPartitionBytes"] == "sem_footer"
        assert por_chave["spark.sql.autoBroadcastJoinThreshold"] == "sem_explain_cost"

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


def _uso(executor, heap=None, offheap=None, python=None):
    medidas = {
        chave: float(valor)
        for chave, valor in (
            ("peak_jvm_heap_bytes", heap),
            ("peak_jvm_offheap_bytes", offheap),
            ("peak_python_rss_bytes", python),
        )
        if valor is not None
    }
    return Fact(
        kind="spark.executor.memory_usage",
        subject={"type": "job_run", "symbol": executor},
        measures=medidas,
        attrs={"executor_id": executor},
    )


def _join(left, right, *, left_stats=True, right_stats=True, line=2):
    return Fact(
        kind="plan.join_side_stats",
        subject={"type": "plan_node", "file": "plan.txt", "line": line, "symbol": "Join Inner",
                 "node_id": 0, "operator": "Join", "relation": ""},
        measures={"left_bytes": float(left), "right_bytes": float(right)},
        attrs={"join_type": "Inner", "left_has_stats": left_stats,
               "right_has_stats": right_stats, "left_node": "Filter", "right_node": "Filter"},
    )


def _row_group(prefix, comprimido, indice=0):
    return Fact(
        kind="parquet.row_group",
        subject={"type": "table", "symbol": f"{prefix}part-0.parquet", "row_group": indice},
        measures={"num_rows": 1000.0, "total_byte_size": float(comprimido * 2)},
        attrs={"prefix": prefix, "total_compressed_bytes": comprimido},
    )


_RT = {"glue": "5.0"}


class TestMemoriaDoExecutor:
    def test_the_overhead_is_the_worst_executor_outside_the_heap(self):
        relatorio = build_conf_advice(
            [_uso("1", offheap=256 * MIB, python=768 * MIB),
             _uso("2", offheap=128 * MIB, python=1024 * MIB)],
            runtime=_RT,
        )
        derivado = _propriedade(relatorio, "spark.executor.memoryOverhead")["derived"]

        assert derivado["value"] == 1152
        assert derivado["basis"]["worst_executor"] == "2"
        assert derivado["basis"]["python_counted"] is True

    def test_headroom_multiplies_the_floor_and_travels_in_the_basis(self):
        relatorio = build_conf_advice(
            [_uso("1", offheap=100 * MIB, python=900 * MIB)], runtime=_RT, headroom=0.2
        )
        derivado = _propriedade(relatorio, "spark.executor.memoryOverhead")["derived"]

        assert derivado["value"] == 1200
        assert derivado["basis"]["headroom"] == 0.2
        assert derivado["basis"]["headroom_source"] == "declared"

    def test_without_headroom_the_floor_has_no_slack(self):
        relatorio = build_conf_advice([_uso("1", offheap=100 * MIB, python=900 * MIB)], runtime=_RT)
        derivado = _propriedade(relatorio, "spark.executor.memoryOverhead")["derived"]

        assert derivado["value"] == 1000
        assert derivado["basis"]["headroom_source"] == "none"

    def test_pyspark_memory_takes_python_out_of_the_overhead(self):
        """Com `spark.executor.pyspark.memory`, o Python tem limite proprio e nao soma."""
        relatorio = build_conf_advice(
            [_uso("1", offheap=100 * MIB, python=900 * MIB),
             _conf("spark.executor.pyspark.memory", "1g")],
            runtime=_RT,
        )
        derivado = _propriedade(relatorio, "spark.executor.memoryOverhead")["derived"]

        assert derivado["value"] == 100
        assert derivado["basis"]["python_counted"] is False
        assert "peak_python_rss_bytes" not in derivado["formula"]

    def test_the_effective_default_is_shown_beside_when_memory_is_known(self):
        relatorio = build_conf_advice(
            [_uso("1", offheap=100 * MIB, python=900 * MIB), _conf("spark.executor.memory", "10g")],
            runtime=_RT,
        )
        base = _propriedade(relatorio, "spark.executor.memoryOverhead")["derived"]["basis"]

        assert base["effective_default_mib"] == 1024

    def test_without_process_tree_the_overhead_is_refused_by_name(self):
        relatorio = build_conf_advice(
            [_uso("1", heap=3 * 1024 * MIB, offheap=256 * MIB)], runtime=_RT
        )
        por_chave = {r["property"]: r for r in relatorio["refused"]}

        assert por_chave["spark.executor.memoryOverhead"]["reason"] == "sem_process_tree"
        assert "processTreeMetrics" in por_chave["spark.executor.memoryOverhead"]["detail"]
        assert _propriedade(relatorio, "spark.executor.memory")["derived"]["value"] == 3072

    def test_without_heap_peak_the_memory_is_refused(self):
        relatorio = build_conf_advice([_uso("1", offheap=100 * MIB, python=900 * MIB)], runtime=_RT)

        assert "sem_pico_de_heap" in _recusas(relatorio)


class TestSplitPeloFooter:
    def test_the_split_is_the_median_compressed_row_group(self):
        relatorio = build_conf_advice(
            [_row_group("s3://b/t/", c, i) for i, c in enumerate((96 * MIB, 128 * MIB, 112 * MIB))],
            runtime=_RT,
        )
        derivado = _propriedade(relatorio, "spark.sql.files.maxPartitionBytes")["derived"]

        assert derivado["value"] == 112 * MIB
        assert derivado["basis"]["row_groups"] == 3

    def test_two_sources_with_different_medians_are_refused(self):
        relatorio = build_conf_advice(
            [_row_group("s3://b/a/", 128 * MIB), _row_group("s3://b/c/", 8 * MIB)], runtime=_RT
        )

        assert "fontes_divergentes" in _recusas(relatorio)


class TestLimiarDeBroadcast:
    def test_one_candidate_join_gives_the_floor_of_the_smaller_side(self):
        relatorio = build_conf_advice([_join(1200 * MIB, 23.5 * MIB)], runtime=_RT)
        derivado = _propriedade(relatorio, "spark.sql.autoBroadcastJoinThreshold")["derived"]

        assert derivado["value"] == 24 * MIB
        assert derivado["basis"]["threshold_source"] == "spark_default"

    def test_a_disabled_threshold_is_not_turned_back_on(self):
        relatorio = build_conf_advice(
            [_join(1200 * MIB, 24 * MIB), _conf("spark.sql.autoBroadcastJoinThreshold", "-1")],
            runtime=_RT,
        )

        assert "broadcast_desligado" in _recusas(relatorio)

    def test_a_side_that_already_fits_is_refused(self):
        relatorio = build_conf_advice(
            [_join(1200 * MIB, 24 * MIB), _conf("spark.sql.autoBroadcastJoinThreshold", "64MB")],
            runtime=_RT,
        )

        assert "ja_cabe_no_threshold" in _recusas(relatorio)

    def test_a_side_above_8gb_is_refused(self):
        relatorio = build_conf_advice([_join(20 * 1024 * MIB, 9 * 1024 * MIB)], runtime=_RT)

        assert "lado_acima_de_8gb" in _recusas(relatorio)

    def test_a_side_without_statistics_never_becomes_the_candidate(self):
        """O lado sem estatistica carrega 8.0 EiB, e o com estatistica decide sozinho."""
        relatorio = build_conf_advice(
            [_join(8.0 * (1 << 60), 30 * MIB, left_stats=False)], runtime=_RT
        )
        derivado = _propriedade(relatorio, "spark.sql.autoBroadcastJoinThreshold")["derived"]

        assert derivado["value"] == 30 * MIB


class TestPortaDoHeadroom:
    def test_a_negative_headroom_is_an_input_error(self, tmp_path):
        import pytest

        from sparkforge.adapters._core import AdapterError, tune_conf

        facts = tmp_path / "facts.json"
        facts.write_text("[]", encoding="utf-8")
        with pytest.raises(AdapterError) as erro:
            tune_conf(str(facts), headroom=-0.1)

        assert erro.value.exit_code == 2
