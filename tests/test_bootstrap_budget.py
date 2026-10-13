"""Teto dos arquivos de instrucao carregados em toda sessao.

`CLAUDE.md` e `AGENTS.md` sao lidos pelo host antes de qualquer pergunta: cada byte
deles e custo fixo de toda sessao, em todo agente. Em 2026-09-15 eles tinham 34 889
e 56 657 bytes, e boa parte era historico datado -- medidas antigas e narrativa de
cada frente. O historico foi para `docs/historico/instrucoes-arquivadas.md`, e este
teste impede que ele volte a crescer calado.

O teto e POLITICA DECLARADA, nao medida: nenhuma fonte publica "N bytes e demais".
Mudar o teto e permitido; o que este teste exige e que a mudanca apareca no diff.

Ele trava tambem a numeracao das regras do `CLAUDE.md`: testes, docstrings e
documentos citam "regra 13", "regra 23", "§20" -- renumerar ou apagar uma regra
deixaria essas citacoes apontando para outra coisa.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TETO_EM_BYTES = {
    "CLAUDE.md": 26_000,
    "AGENTS.md": 26_000,
}
REGRAS_DO_CLAUDE_MD = range(1, 34)


def _bytes(nome: str) -> int:
    return len((ROOT / nome).read_bytes())


def test_arquivos_de_instrucao_cabem_no_teto() -> None:
    estourados = {
        nome: (_bytes(nome), teto)
        for nome, teto in TETO_EM_BYTES.items()
        if _bytes(nome) > teto
    }
    assert not estourados, (
        f"arquivo de instrucao acima do teto (bytes, teto): {estourados}. Mova "
        "historico para docs/historico/instrucoes-arquivadas.md ou suba o teto "
        "declarado aqui, a vista no diff."
    )


def test_regras_do_claude_md_mantem_a_numeracao() -> None:
    texto = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    presentes = {int(n) for n in re.findall(r"(?m)^\s{0,4}(\d{1,2})\. ", texto)}
    faltando = [n for n in REGRAS_DO_CLAUDE_MD if n not in presentes]
    assert not faltando, f"regras do CLAUDE.md sem numero: {faltando}"


def test_historico_arquivado_existe() -> None:
    assert (ROOT / "docs" / "historico" / "instrucoes-arquivadas.md").is_file()
