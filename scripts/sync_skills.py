#!/usr/bin/env python3
"""Sincroniza as skills canônicas (skills/) para os adaptadores de plataforma.

Fonte da verdade: skills/
Espelhos gerados: .claude/skills/ e .agents/skills/

Uso:
    python scripts/sync_skills.py          # regenera os espelhos a partir de skills/
    python scripts/sync_skills.py --check   # falha (exit 1) se algum espelho divergir

O modo --check é usado pelos testes e pode ser plugado em CI para impedir drift.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "skills"
MIRRORS = (ROOT / ".claude" / "skills", ROOT / ".agents" / "skills")


def iter_skill_files() -> list[Path]:
    return sorted(p for p in CANONICAL.rglob("*") if p.is_file())


def check() -> int:
    problems: list[str] = []
    canonical_rel = {p.relative_to(CANONICAL) for p in iter_skill_files()}

    for mirror in MIRRORS:
        mirror_rel = {
            p.relative_to(mirror) for p in mirror.rglob("*") if p.is_file()
        } if mirror.exists() else set()

        for rel in sorted(canonical_rel):
            src = CANONICAL / rel
            dst = mirror / rel
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"DIVERGENTE {dst}")

        for rel in sorted(mirror_rel - canonical_rel):
            problems.append(f"ORFAO {mirror / rel}")

    if problems:
        print("Espelhos fora de sincronia com skills/ (rode: python scripts/sync_skills.py):")
        for line in problems:
            print(f"  {line}")
        return 1

    print("OK: .claude/skills e .agents/skills idênticos a skills/.")
    return 0


def sync() -> int:
    canonical_rel = {p.relative_to(CANONICAL) for p in iter_skill_files()}
    changed = 0

    for mirror in MIRRORS:
        # Copia/atualiza arquivos canônicos.
        for rel in sorted(canonical_rel):
            src = CANONICAL / rel
            dst = mirror / rel
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
            changed += 1

        # Remove órfãos que não existem mais no canônico.
        if mirror.exists():
            for path in sorted(
                (p for p in mirror.rglob("*") if p.is_file()), reverse=True
            ):
                if path.relative_to(mirror) not in canonical_rel:
                    path.unlink()
                    print(f"DEL  {path}")
                    changed += 1

    print(f"Sync concluído ({changed} alteração(ões)).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Apenas verifica sincronia; não escreve nada.",
    )
    args = parser.parse_args()
    return check() if args.check else sync()


if __name__ == "__main__":
    raise SystemExit(main())
