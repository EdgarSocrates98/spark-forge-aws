"""Golden do §15: `change plan` e `change sandbox` sobre repos sinteticos.

Cada caso de `fixtures/change/` traz `input/repo/` (copiado para `tmp_path`
antes de rodar: o sandbox grava `.sparkforge/sandbox/` na raiz), `input/request.json`
(o que pedir), `input/facts.json` (para o plano, extraido do repo pelo extrator
real) e, para o sandbox, o `host.patch` escrito como um host o escreveria.

`SPARKFORGE_REGEN_CHANGE=1` regrava os `expected.json` em vez de comparar.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from sparkforge.adapters import _core
from sparkforge.change import apply_patches, parse_unified_diff

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "change"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "input" / "request.json").is_file())
REGEN = os.environ.get("SPARKFORGE_REGEN_CHANGE") == "1"
CAMPOS_DO_SANDBOX = (
    "applied", "refused", "id", "sandbox", "files_changed", "new", "resolved", "kept_count",
    "moved_candidates", "proof_obligations", "next_steps", "copy_skipped", "scan_refused",
    "main_tree_touched", "stage",
)


def _pedido(caso: str) -> dict[str, Any]:
    return json.loads((FIXTURES / caso / "input" / "request.json").read_text(encoding="utf-8"))


_ESTADO_DO_CHANGE = (".sparkforge/sandbox/", ".sparkforge/proposal/")
# O que o pacote do L3 grava e o golden compara pelo conteudo.
ARQUIVOS_DA_PROPOSTA = (
    "pr_body.md", "commands.md", "change.patch", "rollback.patch", "commit_message.txt",
    "branch.txt",
)


def _hashes(raiz: Path) -> dict[str, str]:
    return {
        p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(raiz.rglob("*"))
        if p.is_file() and not p.relative_to(raiz).as_posix().startswith(_ESTADO_DO_CHANGE)
    }


def _plano(caso: str, repo: Path, sets: list[str] | None = None) -> dict[str, Any]:
    pedido = _pedido(caso)
    return _core.change_plan(
        [str(FIXTURES / caso / "input" / "facts.json")],
        str(repo),
        from_tune=bool(pedido.get("from_tune", False)),
        sets=sets if sets is not None else pedido.get("sets"),
    )


def _executar(caso: str, tmp_path: Path) -> tuple[dict[str, Any], Path, dict[str, str]]:
    pedido = _pedido(caso)
    repo = tmp_path / "repo"
    shutil.copytree(FIXTURES / caso / "input" / "repo", repo)
    antes = _hashes(repo)
    if pedido["kind"] == "plan":
        r = _plano(caso, repo)
        saida = {
            "changes": r["changes"],
            "refused": r["refused"],
            "files": r["files"],
            "diff": r["diff"],
            "rollback_diff": r["rollback_diff"],
            "tune_refused": sorted(x["reason"] for x in r["tune_refused"]),
        }
        return saida, repo, antes
    if "plan_sets" in pedido:
        plano = _plano(caso, repo, sets=pedido["plan_sets"])
        diff = tmp_path / "plano.patch"
        diff.write_text(plano["diff"], encoding="utf-8", newline="\n")
    else:
        diff = FIXTURES / caso / "input" / pedido["diff"]
    r = _core.change_sandbox(str(repo), diff_path=str(diff))
    if pedido["kind"] != "propose":
        return {campo: r[campo] for campo in CAMPOS_DO_SANDBOX}, repo, antes
    proposta = _core.change_propose(
        str(repo),
        sandbox_id=r["id"],
        benchmark_paths=[str(FIXTURES / caso / "input" / b) for b in pedido.get("benchmark", [])]
        or None,
        now=pedido["now"],
    )
    pasta = repo / proposta["proposal"]
    saida = {
        **proposta,
        "conteudo": {
            nome: (pasta / nome).read_text(encoding="utf-8") for nome in ARQUIVOS_DA_PROPOSTA
        },
        "manifest": json.loads((pasta / "manifest.json").read_text(encoding="utf-8")),
    }
    return saida, repo, antes


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso, tmp_path):
    saida, repo, antes = _executar(caso, tmp_path)
    esperado_path = FIXTURES / caso / "expected.json"
    if REGEN:
        esperado_path.write_text(
            json.dumps(saida, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        pytest.skip("expected.json regravado")
    esperado = json.loads(esperado_path.read_text(encoding="utf-8"))
    assert saida == esperado
    assert _hashes(repo) == antes, "a arvore principal mudou fora de .sparkforge/sandbox/"


@pytest.mark.parametrize("caso", [c for c in CASOS if _pedido(c)["kind"] == "plan"])
def test_ida_e_volta_devolve_os_bytes(caso, tmp_path):
    saida, repo, _ = _executar(caso, tmp_path)
    if not saida["diff"]:
        pytest.skip("caso sem mudanca")
    originais = {rel: (repo / rel).read_bytes() for rel in saida["files"]}
    depois = apply_patches(originais, parse_unified_diff(saida["diff"]))
    de_volta = apply_patches(depois, parse_unified_diff(saida["rollback_diff"]))
    assert de_volta == originais
    assert depois != originais


def test_toda_recusa_do_plano_tem_golden():
    from sparkforge.change.refusals import (
        LINHA_NAO_CONFERE,
        PROCEDENCIA_AMBIGUA,
        SEM_PROCEDENCIA,
        VALOR_NAO_LITERAL,
    )

    vistas = set()
    for caso in CASOS:
        esperado = json.loads((FIXTURES / caso / "expected.json").read_text(encoding="utf-8"))
        vistas |= {r["reason"] for r in esperado.get("refused", [])}
    assert {SEM_PROCEDENCIA, LINHA_NAO_CONFERE, PROCEDENCIA_AMBIGUA, VALOR_NAO_LITERAL} <= vistas
