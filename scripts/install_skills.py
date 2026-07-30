#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def copy_tree(src: Path, dst: Path, force: bool) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        relative = item.relative_to(src)
        target = dst / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            print(f"SKIP {target} (use --force)")
            continue
        shutil.copy2(item, target)
        print(f"COPY {target}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Install SparkForge AWS skills")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--claude", action="store_true")
    parser.add_argument("--devin", action="store_true")
    parser.add_argument("--copilot", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target = args.target.resolve()
    selected = args.all or not (args.claude or args.devin or args.copilot)

    if args.all or args.claude or selected:
        copy_tree(ROOT / ".claude", target / ".claude", args.force)
        for name in ("CLAUDE.md", "PROMPT_INICIAL_MESTRE.md", "GUIA_DE_USO.md"):
            src = ROOT / name
            dst = target / name
            if not dst.exists() or args.force:
                shutil.copy2(src, dst)

    if args.all or args.devin or selected:
        copy_tree(ROOT / ".agents", target / ".agents", args.force)
        for name in ("AGENTS.md", "PROMPT_INICIAL_MESTRE.md", "GUIA_DE_USO.md"):
            src = ROOT / name
            dst = target / name
            if not dst.exists() or args.force:
                shutil.copy2(src, dst)

    if args.all or args.copilot or selected:
        copy_tree(ROOT / ".github", target / ".github", args.force)

    # Shared references are needed by the skills.
    for folder in ("knowledge", "templates", "checklists", "skills"):
        copy_tree(ROOT / folder, target / folder, args.force)

    print("SparkForge AWS installed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
