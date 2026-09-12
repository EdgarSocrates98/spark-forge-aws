"""Golden do Change Proof (§20), de ponta a ponta pela CLI.

Cada caso de `fixtures/proof/` declara no `meta.yaml` os findings do antes, a
uniao de facts (com os de funcval e benchmark de fixtures que ja existem), o
depois -- como arquivo de facts ou como codigo, extraido aqui pela mesma porta
do produto (`analyze_pyspark`) -- e o `--applied`. O teste compara a saida com
`expected/result.json` e confere, alem do golden, cada expectativa declarada:
um golden regenerado as cegas nao pode esconder um desfecho errado.

Regenerar depois de mudanca DELIBERADA:
`SPARKFORGE_REGEN_PROOF=1 pytest tests/test_fixtures_golden_proof.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from sparkforge.adapters import _core
from sparkforge.adapters.cli import main

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "proof"
REGEN = os.environ.get("SPARKFORGE_REGEN_PROOF") == "1"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "meta.yaml").is_file())


def _meta(caso: str) -> dict:
    return yaml.safe_load((FIXTURES / caso / "meta.yaml").read_text(encoding="utf-8"))


def _arquivo_de_findings(meta: dict, tmp_path: Path) -> Path:
    todos: list[dict] = []
    for relativo in meta["findings"]:
        todos += json.loads((ROOT / relativo).read_text(encoding="utf-8"))
    destino = tmp_path / "findings.json"
    destino.write_text(json.dumps(todos), encoding="utf-8")
    return destino


def _facts_do_depois(caso: str, meta: dict, tmp_path: Path) -> list[str]:
    if "after_facts" in meta:
        return [str(ROOT / relativo) for relativo in meta["after_facts"]]
    codigo = (FIXTURES / caso / meta["after_input"]).resolve()
    itens = _core.analyze_pyspark(str(codigo), limit=None)["items"]
    destino = tmp_path / "after_facts.json"
    destino.write_text(json.dumps(itens), encoding="utf-8")
    return [str(destino)]


def _provar(caso: str, tmp_path: Path, capsys) -> dict:
    meta = _meta(caso)
    argumentos = ["proof", "--findings", str(_arquivo_de_findings(meta, tmp_path))]
    for relativo in meta["facts"]:
        argumentos += ["--facts", str(ROOT / relativo)]
    for caminho in _facts_do_depois(caso, meta, tmp_path):
        argumentos += ["--after-facts", caminho]
    for pedido in meta["applied"]:
        argumentos += ["--applied", pedido]
    assert main(argumentos) == 0
    return json.loads(capsys.readouterr().out)


def _obrigacao(saida: dict, esperado: dict) -> dict:
    resultado = next(r for r in saida["results"] if r["rule_id"] == esperado["rule_id"])
    return next(
        o
        for o in resultado["obligations"]
        if o["kind"] == esperado["kind"] and o.get("axis") == esperado.get("axis")
    )


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso, tmp_path, capsys):
    saida = _provar(caso, tmp_path, capsys)
    esperado = FIXTURES / caso / "expected" / "result.json"
    texto = json.dumps(saida, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if REGEN:
        esperado.parent.mkdir(parents=True, exist_ok=True)
        esperado.write_text(texto, encoding="utf-8", newline="\n")
    assert texto == esperado.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.parametrize("caso", CASOS)
def test_cada_expectativa_declarada(caso, tmp_path, capsys):
    saida = _provar(caso, tmp_path, capsys)
    for esperado in _meta(caso)["expect"]:
        assert _obrigacao(saida, esperado)["outcome"] == esperado["outcome"], esperado


@pytest.mark.parametrize("caso", CASOS)
def test_nenhum_desfecho_e_provado(caso, tmp_path, capsys):
    saida = _provar(caso, tmp_path, capsys)
    desfechos = {o["outcome"] for r in saida["results"] for o in r["obligations"]}
    assert desfechos <= {"refuted", "not_refuted", "inconclusive", "unproven"}
    assert {r["field"] for r in saida["refused"]} == {"proven", "gain_estimate"}


@pytest.mark.parametrize("caso", CASOS)
def test_toda_obrigacao_unproven_diz_o_que_a_destravaria(caso, tmp_path, capsys):
    saida = _provar(caso, tmp_path, capsys)
    for resultado in saida["results"]:
        for obrigacao in resultado["obligations"]:
            if obrigacao["outcome"] == "unproven":
                assert obrigacao.get("unlock"), obrigacao
