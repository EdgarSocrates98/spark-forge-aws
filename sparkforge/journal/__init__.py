"""Journal de eventos do case: um `started` e um `finished` por verbo que muda estado.

O journal responde a pergunta que o `resume` nao tinha como responder sozinho:
o que estava rodando quando a sessao caiu. Um `started` sem `finished` e esse
dado -- e o `in_flight` deixa de ser o texto que alguem lembrou de escrever.

Tres garantias, e os limites de cada uma:

- a CADEIA (`seq` + `prev`, o sha256 da linha anterior) prova ordem e que
  nenhuma linha foi removida ou editada depois; nao prova autoria (nao ha
  chave, como no `receipt`);
- os ARGUMENTOS entram como sha256 do valor canonico, e so a lista fechada de
  `LITERAL_KEYS` entra literal, e so com valor que nao seja caminho absoluto: o
  journal viaja no commit, e o repositorio e publico;
- nada gera hora: `at` e o `now` que o verbo recebeu, ou `null`.

O conjunto de verbos NAO e uma lista escrita a mao: sai das anotacoes das tools
(`readOnlyHint: false`, menos `code_*`, que so grava o indice de codigo). Tool
nova que grava entra no journal sem ninguem lembrar -- a mesma fonte que a
policy (§16) usa para a classe de autorizacao.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sparkforge.case.store import CASE_DIR

JOURNAL_FILE = "journal.jsonl"
SCHEMA_VERSION = 1

LITERAL_KEYS = frozenset(
    {
        "rules",
        "debate_id",
        "debate",
        "sandbox",
        "sandbox_id",
        "fail_on",
        "format",
        "output_format",
        "phase",
        "gate",
    }
)


def journal_path(raiz: Path | str) -> Path:
    return Path(raiz) / CASE_DIR / JOURNAL_FILE


@lru_cache(maxsize=1)
def journaled() -> frozenset[str]:
    """Os verbos que gravam no journal, derivados de `TOOLS`.

    Import tardio: `sparkforge.policy.hook` nao pode arrastar `adapters.tools`
    (0,48 s medidos no §16) so porque um modulo importou o journal.
    """
    from sparkforge.adapters.tools import TOOLS

    return frozenset(
        nome
        for nome, spec in TOOLS.items()
        if not (spec.get("annotations") or {}).get("readOnlyHint", True)
        and not nome.startswith("sparkforge_code_")
    )
