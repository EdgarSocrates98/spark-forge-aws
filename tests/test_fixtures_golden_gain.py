"""Golden do Realized Gain Ledger (§21), de ponta a ponta pela CLI.

Cada caso de `fixtures/gain/` tem `baseline/` e `candidate/` com arquivos de
facts de runs, recortados dos fixtures reais de `capacity` e `finops`.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_GAIN=1 pytest tests/test_fixtures_golden_gain.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from sparkforge.adapters.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "gain"
REGEN = os.environ.get("SPARKFORGE_REGEN_GAIN") == "1"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "meta.yaml").is_file())


def _rodar(caso: str, capsys) -> dict:
    argumentos = ["gain"]
    for lado in ("baseline", "candidate"):
        for arquivo in sorted((FIXTURES / caso / lado).glob("*.json")):
            argumentos += [f"--{lado}", str(arquivo)]
    assert main(argumentos) == 0
    return json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso, capsys):
    saida = _rodar(caso, capsys)
    esperado = FIXTURES / caso / "expected" / "result.json"
    texto = json.dumps(saida, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if REGEN:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == esperado.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_ganho_por_capacidade_bate_com_a_conta(capsys):
    metricas = _rodar("ganho_por_capacidade", capsys)["metrics"]
    assert metricas["execution_time_s"]["baseline"]["median"] == 900.0
    assert metricas["execution_time_s"]["candidate"]["median"] == 500.0
    assert metricas["execution_time_s"]["delta_pct"] == -44.4
    assert metricas["dpu_seconds"]["delta_pct"] == 11.1
    assert "custo_indisponivel" in metricas["cost"]["marks"]


def test_volume_diverge(capsys):
    marcas = _rodar("volume_diverge", capsys)["metrics"]["execution_time_s"]["marks"]
    assert "volume_diverge" in marcas


def test_amostra_insuficiente(capsys):
    marcas = _rodar("amostra_insuficiente", capsys)["metrics"]["execution_time_s"]["marks"]
    assert "amostra_insuficiente" in marcas


def test_custo_por_run(capsys):
    saida = _rodar("custo_por_run", capsys)
    assert saida["currency"] == "USD" and saida["metrics"]["cost"]["delta"] is not None
    assert "custo_indisponivel" not in saida["metrics"]["cost"]["marks"]
    assert "volume_desconhecido" in saida["metrics"]["cost"]["marks"]


def test_jobs_diferentes_saem_2(tmp_path, capsys):
    arquivo = sorted((FIXTURES / "ganho_por_capacidade" / "baseline").glob("*.json"))[0]
    fatos = json.loads(arquivo.read_text(encoding="utf-8"))
    for fato in fatos:
        if fato["kind"] == "glue.job_run":
            fato["subject"]["job_name"] = "outro_job"
    outro = tmp_path / "outro.json"
    outro.write_text(json.dumps(fatos), encoding="utf-8")
    assert main(["gain", "--baseline", str(arquivo), "--candidate", str(outro)]) == 2
