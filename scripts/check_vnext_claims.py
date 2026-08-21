#!/usr/bin/env python3
"""Gate de lastro das alegações publicadas em `docs/vnext/`.

Fonte da verdade: `docs/vnext/claims.lock.json`. Toda alegação dos documentos
precisa existir no manifesto, e toda entrada do manifesto precisa existir nos
documentos -- fail-closed nos dois sentidos, pela mesma razão registrada em
`tests/test_docs_coverage.py`: lista copiada envelhece sem que nada acuse.

Uso:
    python scripts/check_vnext_claims.py           # audita; sai 1 se divergir
    python scripts/check_vnext_claims.py --full    # inclui provas `tier: slow`
    python scripts/check_vnext_claims.py --seed    # gera manifesto semente
    python scripts/check_vnext_claims.py --report  # tabela de lastro em Markdown
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VNEXT = ROOT / "docs" / "vnext"
MANIFEST = VNEXT / "claims.lock.json"
SOURCES_LOCK = ROOT / "knowledge" / "sources.lock.json"

SCHEMA_VERSION = 1
STATES = frozenset({"PROVADA", "SEM_LASTRO", "REMOVIDA"})
TYPES = frozenset({"number", "capability", "external_fact"})
TIERS = frozenset({"fast", "slow"})
PROOF_KINDS = frozenset({"command", "artifact", "source"})


def rel(path: Path) -> str:
    """Caminho relativo à raiz, sempre com `/`, para o manifesto não mudar
    conforme o sistema operacional de quem rodou o `--seed`."""
    return path.resolve().relative_to(ROOT).as_posix()


def audited_docs(root: Path = VNEXT) -> list[Path]:
    # Fail-open deliberado: `adrs/` ausente ou renomeado devolve glob vazio,
    # nao erro -- um gate que degrada em silencio para de vigiar sem avisar.
    return sorted(root.glob("*.md")) + sorted((root / "adrs").glob("*.md"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Inclui provas tier slow.")
    parser.add_argument("--seed", action="store_true", help="Gera manifesto semente.")
    parser.add_argument("--report", action="store_true", help="Tabela de lastro.")
    args = parser.parse_args()
    # `seed`/`report`/`audit` chegam nas Tasks 6 e 7 -- nenhum teste desta
    # task chama `main()`, e o noqa e temporario ate essas funcoes existirem.
    if args.seed:
        return seed()  # noqa: F821
    if args.report:
        return report()  # noqa: F821
    return audit(include_slow=args.full)  # noqa: F821


if __name__ == "__main__":
    raise SystemExit(main())
