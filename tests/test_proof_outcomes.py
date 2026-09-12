"""Os desfechos do Change Proof, ramo a ramo, com entrada sintetica.

A politica e a real (`rules/catalog/proof_axes.yaml`): o que se testa aqui e a
leitura dela, e uma politica de teste provaria so a si mesma.
"""
from __future__ import annotations

import pytest

from sparkforge.proof import load_policy, prove, select_applied
from sparkforge.proof.axis import bench_outcome, funcval_outcome, none_outcome
from sparkforge.proof.resolution import resolve


@pytest.fixture(scope="module")
def politica():
    return load_policy()


CHAVE = {"type": "source_location", "file": "job.py", "symbol": "principal"}
SUBJECT = {**CHAVE, "line": 9, "col": 13, "snippet": "x.collect()"}


def achado(rule_id="SF-PY-002", subject=None, moves=("correctness.write_result",)):
    return {"rule_id": rule_id, "subject": subject or SUBJECT, "evidence": ["f_antes"],
            "action": {"moves": list(moves)}}


# --- resolucao ------------------------------------------------------------


def test_resolucao_sem_disparo_no_depois_nao_e_refutada(politica):
    o = resolve("SF-PY-002", CHAVE, [], [], politica["stable_keys"], {}, ["f_sentinela"])
    assert o["outcome"] == "not_refuted"
    assert o["evidence"] == ["f_sentinela"]


def test_resolucao_com_disparo_na_mesma_chave_e_refutada_mesmo_em_outra_linha(politica):
    depois = achado(subject={**SUBJECT, "line": 42, "snippet": "outra linha"})
    o = resolve("SF-PY-002", CHAVE, [depois], [], politica["stable_keys"], {}, [])
    assert o["outcome"] == "refuted"


def test_resolucao_com_disparo_em_outra_chave_nao_refuta(politica):
    depois = achado(subject={**SUBJECT, "symbol": "outra_funcao"})
    o = resolve("SF-PY-002", CHAVE, [depois], [], politica["stable_keys"], {}, [])
    assert o["outcome"] == "not_refuted"


def test_regra_muda_por_falta_de_artefato_e_unproven_com_o_que_falta(politica):
    pulada = [{"rule_id": "SF-PY-002", "reason": "requires_facts", "missing": ["pyspark.collect"]}]
    o = resolve("SF-PY-002", CHAVE, [], pulada, politica["stable_keys"],
                {"pyspark.collect": "pyspark_ast"}, [])
    assert o["outcome"] == "unproven"
    assert o["unlock"] == {"pyspark.collect": "pyspark_ast"}


def test_kind_ausente_com_o_extrator_rodado_e_correcao_e_nao_lacuna(politica):
    """O caso medido: a correcao tira o `collect()`, `pyspark.driver_collect`
    some, e `SF-PY-002` cai em `requires_facts`. O extrator rodou -- o depois
    tem `pyspark.module_analyzed` do mesmo modulo --, entao a ausencia e
    evidencia de que o padrao sumiu."""
    pulada = [{"rule_id": "SF-PY-002", "reason": "requires_facts",
               "missing": ["pyspark.driver_collect"]}]
    o = resolve("SF-PY-002", CHAVE, [], pulada, politica["stable_keys"],
                {"pyspark.driver_collect": "pyspark_ast"}, [],
                {"pyspark_ast": ["f_modulo_analisado"]})
    assert (o["outcome"], o["reason"]) == ("not_refuted", "padrao_ausente_com_extrator_rodado")
    assert o["evidence"] == ["f_modulo_analisado"]


def test_kind_de_modulo_desconhecido_continua_lacuna(politica):
    pulada = [{"rule_id": "SF-X-001", "reason": "requires_facts", "missing": ["kind.orfao"]}]
    o = resolve("SF-X-001", CHAVE, [], pulada, politica["stable_keys"], {}, [],
                {"pyspark_ast": ["f_1"]})
    assert o["outcome"] == "unproven"
    assert o["missing_kinds"] == ["kind.orfao"]


@pytest.mark.parametrize(
    "razao, esperado",
    [("runtime_scope", "regra_fora_do_escopo_no_depois"), ("blocked_on", "regra_bloqueada")],
)
def test_silencio_de_escopo_e_inconclusivo_e_nao_resolucao(politica, razao, esperado):
    pulada = [{"rule_id": "SF-PY-002", "reason": razao}]
    o = resolve("SF-PY-002", CHAVE, [], pulada, politica["stable_keys"], {}, [])
    assert (o["outcome"], o["reason"]) == ("inconclusive", esperado)


def test_subject_sem_chave_estavel_e_inconclusivo(politica):
    o = resolve("SF-TIMEOUT-002", None, [], [], politica["stable_keys"], {}, [])
    assert (o["outcome"], o["reason"]) == ("inconclusive", "subject_sem_chave_estavel")


# --- funcval --------------------------------------------------------------


def test_funcval_sem_analise_e_unproven():
    assert funcval_outcome("correctness.write_result", set(), False)["outcome"] == "unproven"


def test_funcval_divergente_refuta_e_vence_a_validacao_parcial():
    o = funcval_outcome("correctness.write_result", {"SF-FVAL-001", "SF-FVAL-005"}, True)
    assert (o["outcome"], o["verdicts"]) == ("refuted", ["SF-FVAL-001"])


def test_funcval_parcial_e_inconclusivo():
    o = funcval_outcome("correctness.write_result", {"SF-FVAL-005"}, True)
    assert o["outcome"] == "inconclusive"


def test_funcval_limpo_nao_e_refutado_e_diz_o_limite():
    o = funcval_outcome("correctness.write_result", set(), True)
    assert o["outcome"] == "not_refuted"
    assert "nao prova identidade" in o["limit"]


# --- bench ----------------------------------------------------------------


def delta(**pcts):
    return {f"{medida}_delta_pct": valor for medida, valor in pcts.items()}


def eixo(politica, nome):
    return politica["axes"][nome]


def test_bench_sem_run_delta_e_unproven(politica):
    spec = eixo(politica, "runtime.wall_clock")
    o = bench_outcome("runtime.wall_clock", spec, set(), None, [], False)
    assert o["outcome"] == "unproven"


def test_stages_nao_casados_vence_tudo(politica):
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"),
                      {"SF-BENCH-004", "SF-BENCH-002"}, delta(total_task_ms=30.0), [], False)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "stages_nao_casados")


def test_volume_diferente_vence_o_piorou(politica):
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"),
                      {"SF-BENCH-001", "SF-BENCH-002"}, delta(total_task_ms=30.0), [], False)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "volumes_de_entrada_diferentes")


def test_no_eixo_de_leitura_volume_e_leitura_sao_indistinguiveis(politica):
    o = bench_outcome("scan.bytes_read", eixo(politica, "scan.bytes_read"),
                      {"SF-BENCH-001"}, delta(total_input_bytes=-60.0), [], False)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "volume_ou_leitura_indistinguiveis")


def test_event_log_ausente_num_lado_invalida(politica):
    furos = [{"reason": "missing_log_analyzed", "measure": ""}]
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"), set(),
                      delta(total_task_ms=-10.0), furos, False)
    assert o["reason"] == "event_log_ausente_num_lado"


def test_rotulo_de_runtime_nao_invalida(politica):
    furos = [{"reason": "same_runtime_label", "measure": ""}]
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"), set(),
                      delta(total_task_ms=-10.0), furos, False)
    assert o["outcome"] == "not_refuted"


def test_furo_da_propria_medida_e_inconclusivo(politica):
    furos = [{"reason": "measure_partial_keys", "measure": "total_spill_bytes"}]
    o = bench_outcome("shuffle.spill_bytes", eixo(politica, "shuffle.spill_bytes"), set(),
                      delta(total_spill_bytes=-5.0), furos, False)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "measure_partial_keys")


def test_delta_omitido_e_inconclusivo(politica):
    o = bench_outcome("scan.task_count", eixo(politica, "scan.task_count"), set(), {}, [], False)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "delta_sem_base")


def test_varias_mudancas_tornam_a_atribuicao_compartilhada(politica):
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"),
                      {"SF-BENCH-002"}, delta(total_task_ms=30.0), [], True)
    assert (o["outcome"], o["reason"]) == ("inconclusive", "attribution_shared")


def test_regra_que_julga_o_eixo_refuta(politica):
    o = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"),
                      {"SF-BENCH-002"}, delta(total_task_ms=30.0), [], False)
    assert (o["outcome"], o["verdicts"]) == ("refuted", ["SF-BENCH-002"])
    assert o["proxy"] == "task_ms_nao_e_wall_clock"


def test_ganho_com_spill_refuta_so_o_eixo_de_spill(politica):
    verdicts = {"SF-BENCH-003"}
    medidas = delta(total_task_ms=-20.0, total_spill_bytes=80.0)
    tempo = bench_outcome("runtime.wall_clock", eixo(politica, "runtime.wall_clock"), verdicts,
                          medidas, [], False)
    spill = bench_outcome("shuffle.spill_bytes", eixo(politica, "shuffle.spill_bytes"), verdicts,
                          medidas, [], False)
    assert (tempo["outcome"], spill["outcome"]) == ("not_refuted", "refuted")


@pytest.mark.parametrize(
    "pct, esperado", [(-0.1, "not_refuted"), (0.0, "refuted"), (4.0, "refuted")]
)
def test_sem_regra_o_sinal_decide_pela_convencao(politica, pct, esperado):
    o = bench_outcome("scan.task_count", eixo(politica, "scan.task_count"), set(),
                      delta(total_task_count=pct), [], False)
    assert o["outcome"] == esperado
    assert o["convention"] == "delta_sign_convention"


# --- none e montagem ------------------------------------------------------


def test_eixo_sem_comparador_e_unproven_com_unlock(politica):
    nome = "dependency.delivered_artifacts"
    o = none_outcome(nome, eixo(politica, nome))
    assert o["outcome"] == "unproven"
    assert o["unlock"]


def test_eixo_fora_da_politica_e_unproven_nomeado():
    assert none_outcome("eixo.novo", None)["reason"] == "eixo_sem_politica"


def test_applied_seleciona_por_regra_e_por_simbolo():
    a = achado()
    b = achado(subject={**SUBJECT, "symbol": "outra"})
    todos, faltam = select_applied([a, b], ["SF-PY-002"])
    assert len(todos) == 2 and faltam == []
    um, _ = select_applied([a, b], ["SF-PY-002:outra"])
    assert um == [b]


def test_applied_inexistente_vira_lacuna():
    _, faltam = select_applied([achado()], ["SF-NAO-EXISTE"])
    assert faltam == [{"field": "applied.SF-NAO-EXISTE", "reason": "applied_nao_encontrado"}]


def test_prova_montada_nunca_diz_proven_e_resume_por_desfecho(politica):
    saida = prove(
        [achado(moves=("correctness.write_result", "dependency.delivered_artifacts"))],
        union_verdicts=[{"rule_id": "SF-FVAL-001"}],
        union_facts=[{"kind": "funcval.analyzed", "id": "f_fv"}],
        after_findings=[], after_skipped=[],
        after_facts=[{"kind": "pyspark.collect", "id": "f_depois"}],
        policy=politica,
        rules_by_id={"SF-PY-002": {"when": {"all": [{"fact": "pyspark.collect"}]}}},
        emitted_by={},
    )
    resultado = saida["results"][0]
    desfechos = [o["outcome"] for o in resultado["obligations"]]
    assert desfechos == ["not_refuted", "refuted", "unproven"]
    assert resultado["obligations"][0]["evidence"] == ["f_depois"]
    esperado = {"refuted": 1, "not_refuted": 1, "inconclusive": 0, "unproven": 1}
    assert resultado["summary"] == esperado
    assert {r["field"] for r in saida["refused"]} == {"proven", "gain_estimate"}
    assert all(o["outcome"] != "proven" for o in resultado["obligations"])
