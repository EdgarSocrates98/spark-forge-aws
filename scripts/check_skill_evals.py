#!/usr/bin/env python3
"""Validate skill-creator evals/evals.json coverage for every source skill."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REQUIRED_EXPECTATION_TERMS = ("fact_id", "unresolved", "validation", "rollback")


def check_one(skill_dir: Path) -> list[str]:
    name = skill_dir.name
    path = skill_dir / "evals" / "evals.json"
    if not path.is_file():
        return [f"{name}: evals/evals.json ausente"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{name}: JSON inválido: {exc}"]
    errors: list[str] = []
    if payload.get("skill_name") != name:
        errors.append(f"{name}: skill_name divergente")
    cases = payload.get("evals")
    if not isinstance(cases, list) or len(cases) < 2:
        return errors + [f"{name}: exige ao menos 2 casos"]
    ids = []
    for case in cases:
        if not isinstance(case, dict):
            errors.append(f"{name}: caso não é objeto")
            continue
        ids.append(case.get("id"))
        for key in ("prompt", "expected_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                errors.append(f"{name}: caso {case.get('id')} sem {key}")
        expectations = case.get("expectations")
        if not isinstance(expectations, list) or len(expectations) < 5:
            errors.append(f"{name}: caso {case.get('id')} tem menos de 5 expectations")
        else:
            joined = " ".join(str(item) for item in expectations).lower()
            for term in REQUIRED_EXPECTATION_TERMS:
                if term not in joined:
                    errors.append(f"{name}: caso {case.get('id')} sem expectation {term}")
        for relative in case.get("files", []) or []:
            candidate = Path(relative)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{name}: caso {case.get('id')} tem file inseguro: {relative}")
            elif not (skill_dir / candidate).is_file():
                errors.append(f"{name}: caso {case.get('id')} referencia arquivo ausente: {relative}")
    if len(set(ids)) != len(ids):
        errors.append(f"{name}: ids de eval duplicados")
    return errors


def errors() -> list[str]:
    return [error for skill_dir in sorted(SKILLS.iterdir()) if skill_dir.is_dir() and (skill_dir / "SKILL.md").is_file() for error in check_one(skill_dir)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    problems = errors()
    if problems:
        print("\n".join(problems))
    else:
        count = sum(1 for path in SKILLS.iterdir() if path.is_dir() and (path / "evals" / "evals.json").is_file())
        print(f"OK: {count} skill eval manifests válidos")
    return 1 if args.strict and problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
