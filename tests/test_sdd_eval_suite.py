"""SDD_EVAL: a suite agentica sobre specs, com gabarito recomputado pelo gate.

Cada teste cobre um criterio de `docs/sdd/SDD_EVAL/define.md`. As fixtures de
`fixtures/sdd/` sao repositorios sinteticos com o hash do upstream gravado em
arquivo versionado; por isso o `.gitattributes` as deixa fora da conversao de
quebra de linha.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from sparkforge.evals.suite import load_suite
from sparkforge.sdd.checks import check
from sparkforge.sdd.status import status

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "evals" / "agentic" / "sdd"
CASOS = ("limpo", "cascata", "cobertura", "tdd", "operador")


def _unica_recusa(repo: Path) -> dict:
    relatorio = check(repo)
    assert relatorio["unresolved"] == [], repo.name
    [recusa] = relatorio["refused"]
    return recusa


def _codigo(repo: Path) -> str:
    return _unica_recusa(repo)["code"]


def _caminho(repo: Path) -> str:
    return _unica_recusa(repo)["path"]


def _criterio_sem_cobertura(repo: Path) -> str:
    recusa = _unica_recusa(repo)
    assert recusa["code"] == "acceptance_uncovered"
    return recusa["unlock"].split()[0]


def _fase(repo: Path) -> str:
    [feature] = status(repo)["features"]
    return feature["phase"]


# A regra de derivacao mora aqui, e nao no YAML: o leitor de suite recusa campo
# desconhecido, e a resposta tem que sair do gate, nunca de quem escreveu a suite.
DERIVA: dict[str, tuple[str, Callable[[Path], str]]] = {
    "sdd-01": ("cascata", _codigo),
    "sdd-02": ("cascata", _caminho),
    "sdd-03": ("cobertura", _criterio_sem_cobertura),
    "sdd-04": ("tdd", _codigo),
    "sdd-05": ("limpo", _fase),
    "sdd-06": ("operador", _codigo),
}


def test_fixtures_sem_conversao_de_quebra():
    texto = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "fixtures/sdd/** -text" in texto.splitlines()
    for caso in CASOS:
        assert (ROOT / "fixtures" / "sdd" / caso / "docs" / "sdd").is_dir(), caso


def test_gabarito_recomputado_pelo_gate():
    suite = load_suite(SUITE_DIR)
    assert sorted(q.id for q in suite.questions) == sorted(DERIVA)
    for pergunta in suite.questions:
        caso, derivar = DERIVA[pergunta.id]
        assert f"fixtures/sdd/{caso}" in pergunta.question, pergunta.id
        assert pergunta.expected == derivar(ROOT / "fixtures" / "sdd" / caso), pergunta.id


def test_runner_conhece_a_suite_sdd():
    from scripts import run_agentic_eval as runner
    from sparkforge.adapters.tools import TOOLS

    assert runner.SDD_SUITE_DIR == SUITE_DIR
    assert runner._suite_dir("sdd") == SUITE_DIR
    assert runner._suite_dir("fase0") == runner.SUITE_DIR
    args = runner._parser().parse_args(["--suite", "sdd", "--runs", "1"])
    assert (args.suite, args.repeat) == ("sdd", 1)
    assert runner._parser().parse_args([]).suite == "fase0"
    for livre in ("evals/agentic/sdd", str(SUITE_DIR), "../sdd"):
        with pytest.raises(SystemExit):
            runner._parser().parse_args(["--suite", livre])
    with pytest.raises(SystemExit):
        runner._suite_dir("evals/agentic/sdd")
    # o fluxo inteiro chega ao workspace de prova: as fixtures vao, o gabarito nao
    assert "fixtures" in runner.WORKSPACE_DIRS and "evals" not in runner.WORKSPACE_DIRS
    negadas = runner._negadas(load_suite(runner._suite_dir("sdd")), "suite")
    visiveis = set(TOOLS) - {n.removeprefix(runner.MCP_PREFIX) for n in negadas}
    assert visiveis == {"sparkforge_sdd_check", "sparkforge_sdd_status"}
