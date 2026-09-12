"""O `--set` do simulate: parse, alteracao e recusas."""
from __future__ import annotations

import pytest

from sparkforge.findings.models import Fact
from sparkforge.simulate import Mudanca, SimulateError, apply_sets, parse_sets


def tf_attr(key, value, measures=None):
    return Fact(kind="tf.attribute", subject={"type": "tf_resource", "symbol": f"job#{key}"},
                measures=measures or {}, attrs={"key": key, "value": value})


def test_parse_separa_camada_chave_e_valor_com_dois_pontos_no_valor():
    [m] = parse_sets(["tf:spark.hadoop.fs.s3.impl=com.x:Classe"])
    assert m == Mudanca("tf", "spark.hadoop.fs.s3.impl", "com.x:Classe")


@pytest.mark.parametrize("bruto, razao", [
    ("max_concurrent_runs=1", "camada_invalida"),
    ("nuvem:x=1", "camada_invalida"),
    ("tf:sem_igual", "set_malformado"),
    ("tf:=1", "set_malformado"),
])
def test_parse_recusa_com_razao(bruto, razao):
    with pytest.raises(SimulateError) as erro:
        parse_sets([bruto])
    assert erro.value.reason == razao


def test_sem_set_e_recusado():
    with pytest.raises(SimulateError) as erro:
        parse_sets([])
    assert erro.value.reason == "sem_set"


def test_valor_numerico_atualiza_texto_e_medida():
    fatos, changes = apply_sets([tf_attr("max_concurrent_runs", "3", {"value": 3})],
                                [Mudanca("tf", "max_concurrent_runs", "1")])
    assert fatos[0].attrs["value"] == "1" and fatos[0].measures["value"] == 1
    assert changes == [{"layer": "tf", "key": "max_concurrent_runs", "old_values": ["3"],
                        "new_value": "1", "facts_changed": 1}]


def test_valor_decimal_vira_float():
    fatos, _ = apply_sets([tf_attr("timeout", "2.5", {"value": 2.5})],
                          [Mudanca("tf", "timeout", "7.5")])
    assert fatos[0].measures["value"] == 7.5


def test_texto_sem_medida_so_troca_o_texto():
    fatos, _ = apply_sets([tf_attr("worker_type", "G.2X")], [Mudanca("tf", "worker_type", "G.1X")])
    assert fatos[0].attrs["value"] == "G.1X" and fatos[0].measures == {}


def test_nao_numerico_para_medida_numerica_e_recusado():
    with pytest.raises(SimulateError) as erro:
        apply_sets([tf_attr("max_concurrent_runs", "3", {"value": 3})],
                   [Mudanca("tf", "max_concurrent_runs", "muitos")])
    assert erro.value.reason == "valor_nao_numerico_para_medida"


def test_chave_ausente_na_camada_e_recusada():
    with pytest.raises(SimulateError) as erro:
        apply_sets([tf_attr("worker_type", "G.2X")], [Mudanca("tf", "nao_existe", "1")])
    assert erro.value.reason == "chave_ausente_na_camada"


def test_outra_camada_nao_e_tocada():
    code = Fact(kind="pyspark.conf_set", subject={"type": "source_location", "file": "j.py"},
                attrs={"key": "worker_type", "value": "x"})
    fatos, changes = apply_sets([tf_attr("worker_type", "G.2X"), code],
                                [Mudanca("tf", "worker_type", "G.1X")])
    assert fatos[1].attrs["value"] == "x"
    assert changes[0]["facts_changed"] == 1


def test_todos_os_facts_da_camada_com_a_chave_mudam():
    a = tf_attr("number_of_workers", "2", {"value": 2})
    b = Fact(kind="tf.attribute", subject={"type": "tf_resource", "symbol": "outro#n"},
             measures={"value": 4}, attrs={"key": "number_of_workers", "value": "4"})
    fatos, changes = apply_sets([a, b], [Mudanca("tf", "number_of_workers", "1")])
    assert [f.measures["value"] for f in fatos] == [1, 1]
    assert changes[0]["old_values"] == ["2", "4"] and changes[0]["facts_changed"] == 2
