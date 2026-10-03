#!/usr/bin/env python3
"""Audit canonical SparkForge skills against the repository quality contract."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REQUIRED_HEADINGS = ("## Quando NÃO usar", "## Referência rápida", "## Red flags")
CONTRACT = "## Contrato de qualidade SparkForge (v1)"


@dataclass(frozen=True)
class Finding:
    skill: str
    severity: str
    message: str


def _frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    return text[4:end], text[end + 4 :]


def _first_line(front: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", front, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    if key == "description":
        try:
            parsed = yaml.safe_load(value)
            if isinstance(parsed, str):
                return parsed
        except yaml.YAMLError:
            pass
    return value


def _metadata_values(front: str, key: str) -> list[str]:
    start = front.find("metadata:")
    if start < 0:
        return []
    block = front[start:]
    match = re.search(rf"^  {re.escape(key)}:\s*\n((?:^  - .*\n?)+)", block, re.MULTILINE)
    if not match:
        return []
    return [
        line.strip()[2:].strip()
        for line in match.group(1).splitlines()
        if line.strip().startswith("-")
    ]


def audit_skill(skill_dir: Path) -> list[Finding]:
    name = skill_dir.name
    findings: list[Finding] = []
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return [Finding(name, "error", "SKILL.md ausente")]
    text = path.read_text(encoding="utf-8")
    parsed = _frontmatter(text)
    if parsed is None:
        return [Finding(name, "error", "frontmatter inválido ou ausente")]
    front, body = parsed
    if _first_line(front, "name") != name:
        findings.append(Finding(name, "error", "name não casa com diretório"))
    description = _first_line(front, "description")
    if not description:
        findings.append(Finding(name, "error", "description ausente"))
    elif not description.lower().startswith("use quando"):
        findings.append(Finding(name, "error", "description não começa com Use quando"))
    elif len(description) > 1024:
        findings.append(Finding(name, "error", "description excede 1024 caracteres"))
    if len(text.splitlines()) > 500:
        findings.append(Finding(name, "error", "SKILL.md excede 500 linhas"))
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            findings.append(Finding(name, "error", f"seção ausente: {heading}"))
    if CONTRACT not in text:
        findings.append(Finding(name, "error", "contrato comum ausente"))
    if "fact_id" not in text or "*.unresolved" not in text:
        findings.append(Finding(name, "error", "contrato não explicita fact_id e unresolved"))
    if "validation" not in text or "rollback" not in text:
        findings.append(Finding(name, "error", "contrato não explicita validation e rollback"))
    if "metadata:" not in front or "sparkforge_contract: v1" not in front:
        findings.append(Finding(name, "error", "metadata.sparkforge_contract v1 ausente"))
    for relative in ("evals/evals.json", "references/README.md", "scripts/validate_evidence.py"):
        if not (skill_dir / relative).is_file():
            findings.append(Finding(name, "error", f"asset ausente: {relative}"))
    for key in ("references", "scripts", "primary_verbs"):
        values = _metadata_values(front, key)
        if not values:
            findings.append(Finding(name, "error", f"metadata.{key} ausente"))
        if key in {"references", "scripts"}:
            for relative in values:
                if not (skill_dir / relative).is_file():
                    findings.append(
                        Finding(name, "error", f"metadata.{key} aponta para ausente: {relative}")
                    )
    if "expected_gain" in text:
        findings.append(Finding(name, "error", "skill usa expected_gain proibido pelo contrato"))
    return findings


def audit() -> list[Finding]:
    findings: list[Finding] = []
    dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    if len(dirs) != 60:
        findings.append(
            Finding("catalog", "error", f"esperadas 60 skills fonte; encontradas {len(dirs)}")
        )
    for skill_dir in dirs:
        findings.extend(audit_skill(skill_dir))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 1 when any finding exists")
    parser.add_argument("--out", type=Path, help="write JSON report")
    args = parser.parse_args()
    findings = audit()
    report = {
        "contract": "sparkforge-skill-v1",
        "skills": len([p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()]),
        "errors": sum(item.severity == "error" for item in findings),
        "findings": [asdict(item) for item in findings],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if findings:
        for item in findings:
            print(f"{item.severity}: {item.skill}: {item.message}")
    else:
        print(f"OK: {report['skills']} skills seguem sparkforge-skill-v1")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
