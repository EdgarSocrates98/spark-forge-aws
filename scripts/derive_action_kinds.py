"""Imprime area, id, titulo e proposed_change de cada regra executavel.

Ferramenta de LEITURA. O vocabulario de `action.kind` e escrito a mao a partir
desta saida -- agrupar por palavra produziria kind derivado de texto, e o eixo
de uma acao nao esta no verbo que a descreve.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Os `proposed_change` tem acento e travessao. Redirecionado no Windows, o
# stdout nasce em cp1252 e a primeira linha com `‐` derruba o script --
# o que faria a leitura parecer curta em vez de falhar alto.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

from sparkforge.rules.loader import load_catalog  # noqa: E402


def main() -> int:
    rules = [r for r in load_catalog() if r.get("executable", True)]
    for rule in sorted(rules, key=lambda r: r["id"]):
        print(f"## {rule['id']} -- {rule['title']}")
        for line in rule.get("proposed_change") or []:
            print(f"  - {line}")
        print()
    print(f"total: {len(rules)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
