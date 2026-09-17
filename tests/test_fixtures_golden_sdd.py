"""Corpus `fixtures/sdd/`: cinco repositorios sinteticos para o eval do SDD.

Cada caso foi montado para quebrar UMA coisa (ou nenhuma, no `limpo`), com o
`stamp` real gravando o hash do upstream. O que este modulo trava e que o gate
continua dando exatamente aquela recusa, e nenhuma outra: e o que torna as
perguntas de `evals/agentic/sdd/suite.yaml` respondiveis com um valor so.

A tabela abaixo NAO e saida copiada do gate: e a intencao de cada caso, escrita
antes de gerar. `tests/test_sdd_eval_suite.py` recomputa o gabarito da suite
rodando o gate; este modulo roda tambem no gate de wheel, contra o pacote
instalado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.sdd.checks import check
from sparkforge.sdd.status import status

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sdd"

ESPERADO = {
    "limpo": [],
    "cascata": [("upstream_stale", "docs/sdd/IMPORTACAO/design.md", "upstream/sha256")],
    "cobertura": [("acceptance_uncovered", "docs/sdd/CADASTRO/design.md", "covers")],
    "tdd": [("red_not_declared", "docs/sdd/FATURAMENTO/build_report.md", "tasks/0/red")],
    "operador": [("change_missing", "docs/sdd/JOB_VENDAS/build_report.md", "change_id")],
}


def test_o_corpus_tem_os_cinco_casos():
    assert sorted(p.name for p in FIXTURES.iterdir() if p.is_dir()) == sorted(ESPERADO)


@pytest.mark.parametrize("caso", sorted(ESPERADO))
def test_cada_caso_da_so_a_recusa_que_foi_montada(caso):
    relatorio = check(FIXTURES / caso)
    recusas = [(r["code"], r["path"], r["field"]) for r in relatorio["refused"]]
    assert recusas == ESPERADO[caso]
    assert relatorio["unresolved"] == []
    assert relatorio["ok"] is (not ESPERADO[caso])


def test_o_caso_limpo_esta_no_ship():
    [feature] = status(FIXTURES / "limpo")["features"]
    assert (feature["feature"], feature["phase"], feature["status"]) == (
        "EXPORTACAO", "ship", "done",
    )
