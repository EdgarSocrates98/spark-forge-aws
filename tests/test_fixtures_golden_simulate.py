"""Golden do simulate (§19), de ponta a ponta pela CLI.

Cada caso de `fixtures/simulate/` declara no `meta.yaml` os facts de um fixture
que ja existe e os `--set`. O caso com `refusal` tem que sair com codigo 2 e o
motivo nomeado; os outros comparam a saida com `expected/result.json` e conferem
o que o `expect` declara: um golden regenerado as cegas nao pode esconder um
achado que devia sumir e nao sumiu.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_SIMULATE=1 pytest tests/test_fixtures_golden_simulate.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "simulate"
REGEN = os.environ.get("SPARKFORGE_REGEN_SIMULATE") == "1"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "meta.yaml").is_file())


def _meta(caso: str) -> dict:
    return yaml.safe_load((FIXTURES / caso / "meta.yaml").read_text(encoding="utf-8"))


SIMULADOS = [c for c in CASOS if "refusal" not in _meta(c)]
RECUSADOS = [c for c in CASOS if "refusal" in _meta(c)]


def _argumentos(meta: dict) -> list[str]:
    argumentos = ["simulate"]
    for relativo in meta["facts"]:
        argumentos += ["--facts", str(ROOT / relativo)]
    for mudanca in meta["sets"]:
        argumentos += ["--set", mudanca]
    return argumentos


def _simular(caso: str, capsys) -> dict:
    assert main(_argumentos(_meta(caso))) == 0
    return json.loads(capsys.readouterr().out)


def test_ha_casos_dos_dois_tipos():
    assert len(SIMULADOS) >= 6 and len(RECUSADOS) >= 3


@pytest.mark.parametrize("caso", SIMULADOS)
def test_golden(caso, capsys):
    saida = _simular(caso, capsys)
    esperado = FIXTURES / caso / "expected" / "result.json"
    texto = json.dumps(saida, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if REGEN:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == esperado.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.parametrize("caso", SIMULADOS)
def test_cada_expectativa_declarada(caso, capsys):
    saida = _simular(caso, capsys)
    expect = _meta(caso)["expect"]
    assert sorted(d["rule_id"] for d in saida["disappeared"]) == expect["disappeared"]
    assert sorted(a["rule_id"] for a in saida["appeared"]) == expect["appeared"]
    if "runtime_glue" in expect:
        antes, depois = expect["runtime_glue"]
        assert saida["runtime"]["before"]["glue"] == antes
        assert saida["runtime"]["after"]["glue"] == depois


@pytest.mark.parametrize("caso", SIMULADOS)
def test_nenhuma_medida_e_prevista(caso, capsys):
    saida = _simular(caso, capsys)
    assert {r["field"] for r in saida["refused"]} == {
        "performance_prediction", "dependency_incompatibility", "execution_graph",
    }
    assert all(c["facts_changed"] >= 1 for c in saida["changes"])


@pytest.mark.parametrize("caso", RECUSADOS)
def test_recusa_sai_com_codigo_2_e_o_motivo(caso, capsys):
    meta = _meta(caso)
    assert main(_argumentos(meta)) == 2
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert f"[{meta['refusal']}]" in capturado.err
