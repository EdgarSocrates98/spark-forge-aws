#!/usr/bin/env python3
"""Gate da superficie do SparkForge: o que ela pesa antes de qualquer chamada.

Fonte da verdade: `docs/surface.lock.json`. O lock nao e limiar -- ele e o
numero medido de hoje, e crescer a superficie passa a exigir declarar o
crescimento, no mesmo mecanismo de `docs/claims.lock.json`.

Ele mede SEM EXECUTAR NADA, e isso e o ponto: a suite inteira nao cabe num job
de CI (o runner mata com SIGXCPU), entao um gate que dependesse dela nao teria
onde rodar.

O que `by_name_sha256` acrescenta, e o que ele NAO cobre
---------------------------------------------------------

Os seis campos agregados (`tool_count`, `total_bytes` por superficie) travam o
TOTAL, e uma troca compensada passa por baixo deles: uma tool que encolhe
enquanto outra cresce na mesma proporcao, ou uma skill renomeada com o mesmo
tamanho em bytes, nao move nenhum agregado. `measure_surface()` ja constroi
`by_name` item a item para as tres superficies -- este gate soma um
`by_name_sha256` por superficie, o sha256 de
`json.dumps(by_name, sort_keys=True, ensure_ascii=False)`, ao lado dos
agregados. `sort_keys=True` importa: sem ele, a mesma composicao de itens
gera hash diferente so por causa da ordem de iteracao do dicionario, e o gate
acusaria uma superficie que nao mudou.

O hash diz QUE algo mudou dentro da superficie; ele nao diz O QUE. Quando ele
diverge, quem le a mensagem nao sabe qual item se moveu -- so que a
composicao inteira (nomes e bytes de cada um) parou de bater. O jeito de
descobrir o que mudou e rodar `--update` e olhar o `git diff` de
`docs/surface.lock.json`: os agregados no diff apontam a superficie, e para
ver o item exato e preciso comparar `by_name` de antes e depois (fora deste
lock, que so guarda o hash, nao o dicionario inteiro). Limitacao conhecida e
escrita aqui vale mais que um invariante mais forte e silencioso sobre por
que decidiu nao existir.

Uso:
    python scripts/check_surface_lock.py            # audita; sai 1 se divergir
    python scripts/check_surface_lock.py --update   # regrava o lock medido
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sparkforge.observability.surface import (  # noqa: E402 -- depois do sys.path
    SERIALIZATION_BASIS,
    measure_surface,
)

LOCK = ROOT / "docs" / "surface.lock.json"

_CAMPOS = (
    ("tools", "tool_count"),
    ("tools", "total_bytes"),
    ("tools", "by_name_sha256"),
    ("skills", "document_count"),
    ("skills", "total_bytes"),
    ("skills", "by_name_sha256"),
    ("knowledge", "document_count"),
    ("knowledge", "total_bytes"),
    ("knowledge", "by_name_sha256"),
)


def _by_name_sha256(by_name: dict) -> str:
    """Sha256 de `by_name` ordenado por chave. `sort_keys=True` e obrigatorio:
    o mesmo conjunto de itens em outra ordem de iteracao do dicionario nao
    pode produzir hash diferente, ou o gate acusaria mudanca onde nao houve
    nenhuma."""
    serializado = json.dumps(by_name, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _payload() -> dict:
    medida = measure_surface()
    return {
        "schema_version": 1,
        "basis": SERIALIZATION_BASIS,
        "tools": {
            "tool_count": medida["tools"]["tool_count"],
            "total_bytes": medida["tools"]["total_bytes"],
            "by_name_sha256": _by_name_sha256(medida["tools"]["by_name"]),
        },
        "skills": {
            "document_count": medida["skills"]["document_count"],
            "total_bytes": medida["skills"]["total_bytes"],
            "by_name_sha256": _by_name_sha256(medida["skills"]["by_name"]),
        },
        "knowledge": {
            "document_count": medida["knowledge"]["document_count"],
            "total_bytes": medida["knowledge"]["total_bytes"],
            "by_name_sha256": _by_name_sha256(medida["knowledge"]["by_name"]),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--update", action="store_true", help="Regrava o lock medido.")
    args = parser.parse_args(argv)

    atual = _payload()

    if args.update:
        LOCK.write_text(
            json.dumps(atual, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"lock atualizado: {LOCK.relative_to(ROOT)}")
        return 0

    if not LOCK.is_file():
        # Tudo em stdout, sem excecao -- mesmo mecanismo de
        # scripts/check_vnext_claims.py: quem redireciona so stdout ainda ve
        # a mensagem inteira, e o codigo de saida (nao o stream) e o que o
        # CI confere.
        print(f"{LOCK.relative_to(ROOT)} nao existe. Rode com --update.")
        return 1

    travado = json.loads(LOCK.read_text(encoding="utf-8"))
    divergencias = [
        f"{secao}.{campo}: lock {travado[secao][campo]}, medido {atual[secao][campo]}"
        for secao, campo in _CAMPOS
        if travado.get(secao, {}).get(campo) != atual[secao][campo]
    ]

    for linha in divergencias:
        print(linha)
    if divergencias:
        print(
            f"{len(divergencias)} divergencia(s). A superficie mudou: rode "
            f"`python scripts/check_surface_lock.py --update` e DECLARE o "
            f"crescimento na mensagem do commit."
        )
        return 1
    print("0 divergencia(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
