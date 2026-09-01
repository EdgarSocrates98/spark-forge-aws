"""A receita de lotes cobre a suite inteira -- medido, nao afirmado.

## Por que este arquivo existe

`CLAUDE.md` e `docs/superpowers/STATUS.md` publicam uma receita de lotes, porque
a suite inteira num processo so nao sobrevive neste repositorio. A receita era
PROSA, e prosa nao e conferida por ninguem.

A auditoria de 2026-09-01 mediu a consequencia: `tests/test_fixtures_golden.py`
-- **90 testes** -- nao caia em lote nenhum. Ele comeca com `f`, entao o lote
`test_f*` deveria pega-lo; mas aquele lote se escrevia `ls tests/test_f*.py |
grep -v golden`, e o `grep -v golden` o excluia junto com os
`test_fixtures_golden_*`. E ele nao tem o underscore que o lote de goldens exige.

Resultado medido: a suite coleta 8662 testes e a receita publicada somava 8572.
A diferenca eram exatamente esses 90 -- que passam quando rodados, mas que
ninguem rodava. Fechar verde seguindo o procedimento publicado deixava 90 testes
sem execucao, e nada acusava.

## O que este arquivo trava

`LOTES` abaixo e a receita EXECUTAVEL, e a prosa dos dois documentos aponta para
ela em vez de repeti-la. Os dois invariantes:

1. **Cobertura** -- todo `tests/test_*.py` cai em ao menos um lote.
2. **Disjuncao** -- nenhum arquivo cai em dois, porque arquivo rodado duas vezes
   infla a soma e esconde o custo real da suite.

Acrescentar arquivo de teste com nome que nenhum lote pega passa a derrubar este
teste, que e o alarme que nao existia.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTES = ROOT / "tests"

# A receita, e ela e a fonte da verdade. Cada entrada e (nome, inclui, exclui).
#
# O lote de goldens e quebrado em cinco por medida, nao por gosto: cada golden
# reextrai o corpus, e o corpus cresceu. `CLAUDE.md` ja mandava "quebrar outra
# vez"; hoje sao cinco partes.
#
# ATENCAO ao terceiro lote: o exclui e `test_fixtures_golden_*.py`, COM
# underscore. Escrever `*golden*` aqui reabriria exatamente o buraco que este
# arquivo fecha -- `test_fixtures_golden.py` cairia fora de todos.
LOTES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("a-c", ("test_[a-c]*.py",), ()),
    ("d-e", ("test_[d-e]*.py",), ()),
    ("f-sem-golden", ("test_f*.py",), ("test_fixtures_golden_*.py",)),
    ("goldens-1", ("test_fixtures_golden_[a-e]*.py",), ()),
    ("goldens-2", ("test_fixtures_golden_[f-h]*.py",), ()),
    ("goldens-3", ("test_fixtures_golden_[i-o]*.py",), ()),
    ("goldens-4", ("test_fixtures_golden_[p-r]*.py",), ()),
    ("goldens-5", ("test_fixtures_golden_[s-z]*.py",), ()),
    ("g-z", ("test_[g-z]*.py",), ()),
)


def _arquivos_de_teste() -> set[str]:
    return {p.name for p in TESTES.glob("test_*.py")}


def _arquivos_do_lote(nome: str) -> set[str]:
    inclui, exclui = next((i, e) for n, i, e in LOTES if n == nome)
    achados: set[str] = set()
    for padrao in inclui:
        achados |= {f for f in _arquivos_de_teste() if fnmatch.fnmatch(f, padrao)}
    for padrao in exclui:
        achados -= {f for f in achados if fnmatch.fnmatch(f, padrao)}
    return achados


def test_todo_arquivo_de_teste_cai_em_algum_lote():
    """O invariante que faltava, e o contrafactual que o provou.

    Contrafactual medido em 2026-09-01: com o terceiro lote escrito como
    `grep -v golden`, `test_fixtures_golden.py` ficava de fora de todos os nove.
    """
    coberto: set[str] = set()
    for nome, _, _ in LOTES:
        coberto |= _arquivos_do_lote(nome)
    orfaos = sorted(_arquivos_de_teste() - coberto)
    assert not orfaos, (
        f"arquivos de teste que lote nenhum roda: {orfaos}. "
        f"Quem seguir a receita publicada em `CLAUDE.md` fecha verde sem "
        f"executa-los, e nada acusa. Ou o arquivo entra num lote, ou a receita "
        f"ganha um lote novo -- apagar esta assercao e a unica saida errada."
    )


def test_nenhum_arquivo_cai_em_dois_lotes():
    """Arquivo rodado duas vezes infla a soma e esconde o custo real da suite."""
    dono: dict[str, str] = {}
    duplicados: list[tuple[str, str, str]] = []
    for nome, _, _ in LOTES:
        for arquivo in _arquivos_do_lote(nome):
            if arquivo in dono:
                duplicados.append((arquivo, dono[arquivo], nome))
            else:
                dono[arquivo] = nome
    assert not duplicados, (
        f"arquivo em mais de um lote (arquivo, lote, lote): {sorted(duplicados)}. "
        f"A soma dos lotes deixa de ser o tamanho da suite."
    )


def test_nenhum_lote_esta_vazio():
    """Lote vazio e receita que envelheceu: o padrao deixou de casar qualquer
    coisa, e a soma continua fechando porque nada faltou."""
    vazios = [nome for nome, _, _ in LOTES if not _arquivos_do_lote(nome)]
    assert not vazios, (
        f"lotes que nao casam arquivo nenhum: {vazios}. O padrao envelheceu, e "
        f"a receita esta descrevendo uma arvore que nao existe mais."
    )


def test_a_soma_dos_lotes_e_o_tamanho_da_suite():
    """Fecha a conta pelos dois lados: cobertura mais disjuncao implicam
    igualdade, e medir a igualdade e o que torna a soma publicavel."""
    total_por_lote = sum(len(_arquivos_do_lote(nome)) for nome, _, _ in LOTES)
    assert total_por_lote == len(_arquivos_de_teste()), (
        f"soma dos lotes {total_por_lote} != arquivos de teste "
        f"{len(_arquivos_de_teste())}"
    )
