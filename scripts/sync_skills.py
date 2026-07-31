#!/usr/bin/env python3
"""Sincroniza skills e agents canônicos para os adaptadores de plataforma.

Fontes da verdade: skills/ e agents/
Espelhos gerados:
    - skills/  -> .claude/skills/ e .agents/skills/
    - agents/  -> .claude/agents/, .agents/agents/ e .github/agents/ (sufixo .agent.md)

Uso:
    python scripts/sync_skills.py          # regenera os espelhos a partir de skills/ e agents/
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

AGENTS_SRC = ROOT / "agents"
AGENT_MIRRORS = (
    (ROOT / ".claude" / "agents", "{stem}.md"),
    (ROOT / ".agents" / "agents", "{stem}.md"),
    (ROOT / ".github" / "agents", "{stem}.agent.md"),
)
STALE_AGENTS = (ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md",)


def iter_skill_files() -> list[Path]:
    return sorted(p for p in CANONICAL.rglob("*") if p.is_file())


def iter_agent_files() -> list[Path]:
    return sorted(p for p in AGENTS_SRC.glob("*.md") if p.is_file())


def check_skills() -> list[str]:
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

    return problems


def check_agents() -> list[str]:
    problems: list[str] = []
    agent_files = iter_agent_files()

    for mirror_dir, name_pattern in AGENT_MIRRORS:
        expected_names = {name_pattern.format(stem=p.stem) for p in agent_files}
        mirror_names = (
            {p.name for p in mirror_dir.glob("*.md") if p.is_file()}
            if mirror_dir.exists()
            else set()
        )

        for src in agent_files:
            dst = mirror_dir / name_pattern.format(stem=src.stem)
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"DIVERGENTE {dst}")

        for orphan_name in sorted(mirror_names - expected_names):
            problems.append(f"ORFAO {mirror_dir / orphan_name}")

    for stale in STALE_AGENTS:
        if stale.exists():
            problems.append(f"OBSOLETO {stale}")

    return problems


def check() -> int:
    problems = check_skills() + check_agents()

    if problems:
        print(
            "Espelhos fora de sincronia com skills/ e agents/ "
            "(rode: python scripts/sync_skills.py):"
        )
        for line in problems:
            print(f"  {line}")
        return 1

    print("OK: .claude, .agents e .github idênticos a skills/ e agents/.")
    return 0


def sync_skills() -> int:
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

    return changed


def sync_agents() -> int:
    agent_files = iter_agent_files()
    changed = 0

    for mirror_dir, name_pattern in AGENT_MIRRORS:
        expected_names = {name_pattern.format(stem=p.stem) for p in agent_files}

        for src in agent_files:
            dst = mirror_dir / name_pattern.format(stem=src.stem)
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
            changed += 1

        if mirror_dir.exists():
            for path in sorted(
                (p for p in mirror_dir.glob("*.md") if p.is_file()), reverse=True
            ):
                if path.name not in expected_names:
                    path.unlink()
                    print(f"DEL  {path}")
                    changed += 1

    for stale in STALE_AGENTS:
        if stale.exists():
            stale.unlink()
            print(f"DEL  {stale}")
            changed += 1

    return changed


def sync() -> int:
    changed = sync_skills() + sync_agents()
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
