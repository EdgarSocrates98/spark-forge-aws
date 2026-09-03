#!/usr/bin/env python3
"""Conta o que `docs/harness/ICEBERG-GAP.md` afirma sobre as 27 camadas.

## Por que um script, e nao um `python -c` no manifesto

O gate de lastro recusa `\\` em `proof.cmd`, e por boa razao: `shlex.split` o
trata como escape POSIX e corrompe o comando entre Windows e Linux. Um regex
como `### [^(]+\\((\\d+)\\)` nao sobrevive a essa passagem.

Entao a contagem mora aqui, e o manifesto chama o script -- que e o mesmo padrao
que `check_status_numbers.py` usa: a MEDICAO e codigo, o valor publicado esta no
documento, e o gate compara os dois.

## O que ele conta

`--secoes` soma os numeros entre parenteses dos cabecalhos `###`, que e a
particao das 27 camadas. Se a soma nao der 27, o documento se contradiz: alguma
camada esta em duas categorias, ou em nenhuma.

`--secao <titulo>` devolve o numero daquela categoria.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "harness" / "ICEBERG-GAP.md"
_CABECALHO = re.compile(r"^### (?P<titulo>[^(]+?)\s*\((?P<n>\d+)\)\s*$", re.M)


def secoes() -> dict[str, int]:
    texto = DOC.read_text(encoding="utf-8")
    return {m.group("titulo").strip(): int(m.group("n")) for m in _CABECALHO.finditer(texto)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secoes", action="store_true", help="a soma das categorias")
    parser.add_argument("--secao", help="o numero de uma categoria, pelo inicio do titulo")
    args = parser.parse_args()

    encontradas = secoes()
    if args.secao:
        for titulo, n in encontradas.items():
            if titulo.startswith(args.secao):
                print(n)
                return 0
        print(f"categoria nao encontrada: {args.secao!r}", file=sys.stderr)
        return 1

    print(sum(encontradas.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
