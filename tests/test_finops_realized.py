"""Realized Gain Ledger: estatistica, marcas, descarte, recusas e erros."""
from __future__ import annotations

import pytest

from sparkforge.findings.models import Fact
from sparkforge.finops.realized import GainError, realized_gain

GB = 1_000_000_000


def _run(rid, t, dpu=100.0, state="SUCCEEDED", job="j", wt="G.1X", n=10):
    return Fact(
        kind="glue.job_run",
        subject={"type": "job_run", "symbol": rid, "job_name": job, "job_run_id": rid},
        measures={"execution_time_s": t, "dpu_seconds": dpu, "number_of_workers": n},
        attrs={"state": state, "worker_type": wt, "glue_version": "5.0", "autoscaling": False},
    )


def _scan(rid, volume=GB):
    return Fact(kind="spark.sql.scan", subject={"type": "stage", "symbol": f"s_{rid}"},
                measures={"bytes_read": volume})


def _custo(rid, cost, currency="USD", job="j"):
    return Fact(kind="glue.run_cost",
                subject={"type": "job_run", "symbol": rid, "job_name": job, "job_run_id": rid},
                measures={"cost": cost}, attrs={"currency": currency})


def _lado(prefixo, tempos, volume=GB, **kw):
    """Um arquivo por run, com scan: volume conhecido."""
    return [[_run(f"{prefixo}{i}", t, **kw), _scan(f"{prefixo}{i}", volume)]
            for i, t in enumerate(tempos)]


def test_delta_das_medianas_sem_marca():
    saida = realized_gain(_lado("b", [100, 200, 300]), _lado("c", [50, 60, 70]))
    tempo = saida["metrics"]["execution_time_s"]
    assert tempo["baseline"] == {"n": 3, "median": 200.0, "min": 100.0, "max": 300.0}
    assert tempo["delta"] == -140.0 and tempo["delta_pct"] == -70.0
    assert tempo["marks"] == []


def test_amostra_insuficiente():
    saida = realized_gain(_lado("b", [100, 200, 300]), _lado("c", [50, 60]))
    assert "amostra_insuficiente" in saida["metrics"]["execution_time_s"]["marks"]
    assert saida["metrics"]["execution_time_s"]["delta"] is not None


def test_jobs_diferentes_sao_erro():
    with pytest.raises(GainError, match="jobs diferentes"):
        realized_gain(_lado("b", [1, 2, 3], job="a"), _lado("c", [1, 2, 3], job="b"))


def test_lado_sem_run_valido_e_erro():
    with pytest.raises(GainError, match="candidate"):
        realized_gain(_lado("b", [1, 2, 3]), _lado("c", [1, 2, 3], state="FAILED"))


def test_run_que_falhou_e_descartado_e_contado():
    candidato = _lado("c", [50, 60, 70]) + _lado("f", [999], state="FAILED")
    saida = realized_gain(_lado("b", [100, 200, 300]), candidato)
    assert saida["discarded"] == {"run_nao_sucedido": 1}
    assert saida["metrics"]["execution_time_s"]["candidate"]["max"] == 70.0


def test_volume_diverge():
    saida = realized_gain(_lado("b", [1, 2, 3]), _lado("c", [1, 2, 3], volume=2 * GB))
    assert "volume_diverge" in saida["metrics"]["dpu_seconds"]["marks"]


def test_tolerancia_declarada_no_workload():
    declarado = Fact(kind="workload.declared", subject={"type": "job", "symbol": "j"},
                     measures={"volume_tolerance": 0.5})
    base = _lado("b", [1, 2, 3])
    base[0].append(declarado)
    saida = realized_gain(base, _lado("c", [1, 2, 3], volume=int(1.4 * GB)))
    assert saida["volume_tolerance"] == 0.5
    assert "volume_diverge" not in saida["metrics"]["execution_time_s"]["marks"]


def test_arquivo_com_varios_runs_tem_volume_desconhecido():
    varios = [[_run(f"c{i}", t) for i, t in enumerate([1, 2, 3])] + [_scan("x")]]
    saida = realized_gain(_lado("b", [1, 2, 3]), varios)
    assert "volume_desconhecido" in saida["metrics"]["execution_time_s"]["marks"]
    assert saida["candidate"]["volume_median_bytes"] is None


def test_custo_pelo_job_run_id():
    base = [c + [_custo(f"b{i}", 2.0)] for i, c in enumerate(_lado("b", [1, 2, 3]))]
    cand = [c + [_custo(f"c{i}", 1.0)] for i, c in enumerate(_lado("c", [1, 2, 3]))]
    saida = realized_gain(base, cand)
    assert saida["metrics"]["cost"]["delta"] == -1.0
    assert saida["metrics"]["cost"]["marks"] == [] and saida["currency"] == "USD"


def test_run_sem_custo_marca_so_o_custo():
    base = [c + [_custo(f"b{i}", 2.0)] for i, c in enumerate(_lado("b", [1, 2, 3]))]
    saida = realized_gain(base, _lado("c", [1, 2, 3]))
    assert "custo_indisponivel" in saida["metrics"]["cost"]["marks"]
    assert "custo_indisponivel" not in saida["metrics"]["execution_time_s"]["marks"]


def test_moedas_diferentes_marcam_custo():
    base = [c + [_custo(f"b{i}", 2.0)] for i, c in enumerate(_lado("b", [1, 2, 3]))]
    cand = [c + [_custo(f"c{i}", 1.0, "EUR")] for i, c in enumerate(_lado("c", [1, 2, 3]))]
    saida = realized_gain(base, cand)
    assert "custo_indisponivel" in saida["metrics"]["cost"]["marks"] and saida["currency"] is None


def test_recusas_sempre():
    saida = realized_gain(_lado("b", [1, 2, 3]), _lado("c", [1, 2, 3]))
    assert [r["field"] for r in saida["refused"]] == [
        "economia_mensal", "atribuicao_causal", "intervalo_de_confianca"]


def test_capacidade_de_cada_lado_e_informacao():
    saida = realized_gain(_lado("b", [1, 2, 3]), _lado("c", [1, 2, 3], wt="G.2X", n=20))
    assert saida["candidate"]["capacities"] == [
        {"glue_version": "5.0", "worker_type": "G.2X", "number_of_workers": 20,
         "autoscaling": False, "runs": 3}]
    assert saida["metrics"]["execution_time_s"]["marks"] == []
