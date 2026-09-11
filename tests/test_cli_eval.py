"""`python -m sparkforge.evals grade|compare` de ponta a ponta, sobre as fixtures.

A CLI aceita NOMES sob bases fixas -- a suite em `<cwd>/evals/agentic/`, as
execucoes em `RUNS_ROOT`, os baselines em `evals/agentic/<suite>/baselines/`.
Cada teste monta essa geografia num diretorio temporario (`chdir` para um
repositorio falso e `RUNS_ROOT` apontado para outro) e copia as fixtures para
dentro dela, para que a CLI rode exatamente como o operador a roda.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sparkforge.evals import cli

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "host_transcript"
SUITE = "fixtures_suite"


@pytest.fixture
def geografia(tmp_path, monkeypatch):
    repo, runs = tmp_path / "repo", tmp_path / "runs"
    suite_dir = repo / "evals" / "agentic" / SUITE
    shutil.copytree(FIXTURES / "_suite", suite_dir)
    runs.mkdir()
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "RUNS_ROOT", runs)
    return suite_dir, runs


def _json(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def _esperado(caso: str, nome: str) -> dict:
    return json.loads((FIXTURES / caso / "expected" / nome).read_text(encoding="utf-8"))


def test_grade_imprime_e_grava_o_scorecard_na_execucao(geografia, capsys):
    _, runs = geografia
    shutil.copytree(FIXTURES / "run_full" / "input", runs / "input")
    assert cli.main(["grade", "--suite", SUITE, "--run", "input"]) == 0
    impresso = _json(capsys)
    gravado = json.loads((runs / "input" / cli.SCORECARD).read_text(encoding="utf-8"))
    assert impresso == gravado == _esperado("run_full", "scorecard.json")


@pytest.mark.parametrize("nome", ["../input", "a/b", "..", ".", "C:\\x"])
def test_nome_com_separador_e_recusado(geografia, capsys, nome):
    assert cli.main(["grade", "--suite", SUITE, "--run", nome]) == 2
    assert "NOME" in capsys.readouterr().err


def test_suite_com_separador_e_recusada(geografia, capsys):
    assert cli.main(["grade", "--suite", "../x", "--run", "input"]) == 2
    assert "NOME" in capsys.readouterr().err


def test_suite_invalida_sai_com_codigo_2(geografia, capsys):
    suite_dir, runs = geografia
    (suite_dir / "suite.yaml").write_text("schema_version: 9\n", encoding="utf-8")
    shutil.copytree(FIXTURES / "run_full" / "input", runs / "input")
    assert cli.main(["grade", "--suite", SUITE, "--run", "input"]) == 2
    assert "suite invalida" in capsys.readouterr().err


def test_execucao_ausente_sai_com_codigo_2(geografia, capsys):
    assert cli.main(["grade", "--suite", SUITE, "--run", "nao_existe"]) == 2
    assert "ausente" in capsys.readouterr().err


def _conjuntos(suite_dir: Path, runs: Path, caso: str) -> None:
    shutil.copytree(FIXTURES / caso / "input" / "baseline", suite_dir / "baselines" / "base")
    shutil.copytree(FIXTURES / caso / "input" / "candidate", runs / "cand")


def test_compare_entre_baseline_commitado_e_conjunto_recem_rodado(geografia, capsys):
    suite_dir, runs = geografia
    _conjuntos(suite_dir, runs, "compare_flip")
    assert cli.main(["compare", "--suite", SUITE, "--baseline", "base", "--candidate", "cand"]) == 0
    assert _json(capsys) == _esperado("compare_flip", "compare.json")


def test_compare_com_nome_nas_duas_bases_e_ambiguo(geografia, capsys):
    suite_dir, runs = geografia
    _conjuntos(suite_dir, runs, "compare_stable")
    shutil.copytree(runs / "cand", suite_dir / "baselines" / "cand")
    assert cli.main(["compare", "--suite", SUITE, "--baseline", "base", "--candidate", "cand"]) == 2
    assert "exatamente um" in capsys.readouterr().err


def test_compare_com_lado_vazio_e_recusa_nao_falha(geografia, capsys):
    suite_dir, runs = geografia
    _conjuntos(suite_dir, runs, "compare_stable")
    (runs / "vazio").mkdir()
    codigo = cli.main(["compare", "--suite", SUITE, "--baseline", "base", "--candidate", "vazio"])
    assert codigo == 0
    assert _json(capsys)["refused"] == {"reason": "empty_side", "sides": ["candidate"]}


def test_compare_ignora_json_que_nao_e_scorecard(geografia, capsys):
    suite_dir, runs = geografia
    _conjuntos(suite_dir, runs, "compare_stable")
    (suite_dir / "baselines" / "base" / "run.json").write_text('{"argv": []}', encoding="utf-8")
    assert cli.main(["compare", "--suite", SUITE, "--baseline", "base", "--candidate", "cand"]) == 0
    assert _json(capsys)["baseline"]["n"] == 3


def test_compare_recusa_gabaritos_misturados_no_mesmo_lado(geografia, capsys):
    suite_dir, runs = geografia
    _conjuntos(suite_dir, runs, "compare_stable")
    estranho = FIXTURES / "compare_suite_mismatch" / "input" / "candidate" / "cand-1.json"
    shutil.copy(estranho, suite_dir / "baselines" / "base" / "zz-outro.json")
    assert cli.main(["compare", "--suite", SUITE, "--baseline", "base", "--candidate", "cand"]) == 0
    assert _json(capsys)["refused"]["reason"] == "suite_mismatch_within_side"
