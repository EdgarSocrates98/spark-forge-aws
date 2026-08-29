#!/usr/bin/env python3
"""Gate da superficie do SparkForge: o que ela pesa antes de qualquer chamada.

Fonte da verdade: `docs/surface.lock.json`. O lock nao e limiar -- ele e o
numero medido de hoje, e crescer a superficie passa a exigir declarar o
crescimento, no mesmo mecanismo de `docs/claims.lock.json`.

Ele mede SEM EXECUTAR NADA, e isso e o ponto: a suite inteira nao cabe num job
de CI (o runner mata com SIGXCPU), entao um gate que dependesse dela nao teria
onde rodar.

Uso:
    python scripts/check_surface_lock.py            # audita; sai 1 se divergir
    python scripts/check_surface_lock.py --update   # regrava o lock medido
"""
from __future__ import annotations

import argparse
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
    ("skills", "document_count"),
    ("skills", "total_bytes"),
    ("knowledge", "document_count"),
    ("knowledge", "total_bytes"),
)


def _payload() -> dict:
    medida = measure_surface()
    return {
        "schema_version": 1,
        "basis": SERIALIZATION_BASIS,
        "tools": {
            "tool_count": medida["tools"]["tool_count"],
            "total_bytes": medida["tools"]["total_bytes"],
        },
        "skills": {
            "document_count": medida["skills"]["document_count"],
            "total_bytes": medida["skills"]["total_bytes"],
        },
        "knowledge": {
            "document_count": medida["knowledge"]["document_count"],
            "total_bytes": medida["knowledge"]["total_bytes"],
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
        print(f"{LOCK.relative_to(ROOT)} nao existe. Rode com --update.", file=sys.stderr)
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
            f"crescimento na mensagem do commit.",
            file=sys.stderr,
        )
        return 1
    print("0 divergencia(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
