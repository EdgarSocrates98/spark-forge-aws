"""Leitura do journal: a cadeia confere, e o que ficou sem `finished`.

`verify` recalcula `seq` e `prev` linha a linha sobre os BYTES de cada linha --
reformatar uma linha, trocar um campo ou apagar uma linha quebra a cadeia no
`seq` exato. So a ultima linha pode estar cortada por uma queda (`torn_tail`).

O LIMITE, medido no golden: editar a ULTIMA linha nao quebra nada, porque
nenhuma linha posterior guarda o hash dela. Quem protege a ultima linha e o
historico do git (o journal e commitavel), nao a cadeia. `last_seq` sai no
resultado para quem quiser comparar com o que foi commitado.

`estado` e o que o `resume` le. `open_calls` sao os `started` sem `finished`,
e isso NAO e "caiu": outro processo ainda rodando tem a mesma cara, e quem le
precisa ouvir as duas hipoteses.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.case.store import CASE_DIR
from sparkforge.journal import JOURNAL_FILE, journal_path
from sparkforge.journal.record import sha256_texto

INTACT = "intact"
BROKEN = "broken"
TORN_TAIL = "torn_tail"
ABSENT = "absent"
UNREADABLE = "unreadable"


def _ler(caminho: Path) -> tuple[list[dict[str, Any]], bool, int | None]:
    """`(eventos validos em ordem, cauda cortada, seq onde quebrou)`."""
    conteudo = caminho.read_bytes()
    pedacos = conteudo.split(b"\n")
    termina_em_quebra = conteudo.endswith(b"\n")
    eventos: list[dict[str, Any]] = []
    anterior: str | None = None
    esperado = 1
    for indice, bruto in enumerate(pedacos, start=1):
        linha = bruto.rstrip(b"\r")
        if not linha.strip():
            continue
        ultimo = indice == len(pedacos) and not termina_em_quebra
        try:
            texto = linha.decode("utf-8")
            evento = json.loads(texto)
        except (UnicodeDecodeError, ValueError):
            if ultimo:
                return eventos, True, None
            return eventos, False, esperado
        prev_esperado = sha256_texto(anterior) if anterior is not None else None
        if (
            not isinstance(evento, dict)
            or evento.get("seq") != esperado
            or evento.get("prev") != prev_esperado
        ):
            return eventos, False, esperado
        eventos.append(evento)
        anterior = texto
        esperado += 1
    return eventos, False, None


def verify(raiz: Path | str) -> dict[str, Any]:
    """`intact`, `broken` (com `broken_at`), `torn_tail` ou `absent`."""
    caminho = journal_path(raiz)
    base: dict[str, Any] = {
        "path": f"{CASE_DIR}/{JOURNAL_FILE}",
        "events": 0,
        "last_seq": 0,
        "broken_at": None,
        "torn_tail": False,
    }
    if not caminho.is_file():
        return {**base, "status": ABSENT}
    eventos, torn, quebra = _ler(caminho)
    status = BROKEN if quebra is not None else (TORN_TAIL if torn else INTACT)
    return {
        **base,
        "status": status,
        "events": len(eventos),
        "last_seq": eventos[-1]["seq"] if eventos else 0,
        "broken_at": quebra,
        "torn_tail": torn,
    }


def estado(raiz: Path | str) -> dict[str, Any]:
    """O bloco `journal` do `resume`. Nunca levanta: journal ilegivel e um estado."""
    caminho = journal_path(raiz)
    vazio: dict[str, Any] = {
        "last_seq": 0,
        "open_calls": [],
        "chain": ABSENT,
        "broken_at": None,
        "torn_tail": False,
    }
    if not caminho.is_file():
        return vazio
    try:
        eventos, torn, quebra = _ler(caminho)
    except OSError:
        return {**vazio, "chain": UNREADABLE}
    fechados = {e.get("started_seq") for e in eventos if e.get("event") == "finished"}
    abertos = [
        {"seq": e["seq"], "tool": e.get("tool"), "port": e.get("port"), "at": e.get("at")}
        for e in eventos
        if e.get("event") == "started" and e["seq"] not in fechados
    ]
    return {
        "last_seq": eventos[-1]["seq"] if eventos else 0,
        "open_calls": abertos,
        "chain": BROKEN if quebra is not None else INTACT,
        "broken_at": quebra,
        "torn_tail": torn,
    }
