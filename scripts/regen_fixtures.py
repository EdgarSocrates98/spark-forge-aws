#!/usr/bin/env python3
"""Regenera os golden outputs das fixtures.

Rode SOMENTE quando a mudanca de comportamento for intencional, e revise o diff:
o golden e a defesa contra falso positivo, e regenerar sem ler o diff a destroi.

Uso:
    python scripts/regen_fixtures.py            # todas
    python scripts/regen_fixtures.py coalesce_one
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.facts.event_log import extract_event_log_path  # noqa: E402
from sparkforge.facts.pyspark_ast import extract_tree  # noqa: E402
from sparkforge.facts.terraform import extract_terraform_tree  # noqa: E402
from sparkforge.rules.engine import judge  # noqa: E402
from sparkforge.rules.loader import load_catalog  # noqa: E402

FIXTURES = ROOT / "fixtures" / "pyspark"
FIXTURES_EVENTLOG = ROOT / "fixtures" / "eventlog"
FIXTURES_TERRAFORM = ROOT / "fixtures" / "terraform"


def _write_expected(directory: Path, facts, findings) -> None:
    out = directory / "expected"
    out.mkdir(exist_ok=True)
    for name, payload in (
        ("facts.json", [f.to_dict() for f in facts]),
        ("findings.json", [f.to_dict() for f in findings]),
    ):
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        # newline="\n" força LF mesmo no Windows: sem isso, write_text() em
        # modo texto traduz para o newline nativo da plataforma (CRLF), e
        # todo golden já commitado (LF) vira diff espúrio de fim de linha.
        (out / name).write_text(text, encoding="utf-8", newline="\n")

    fired = ", ".join(sorted({f.rule_id for f in findings})) or "nenhum"
    print(f"{directory.name}: {len(facts)} facts, {len(findings)} findings ({fired})")


def regen(directory: Path) -> None:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_eventlog(directory: Path) -> None:
    """Como `regen`, mas para fixtures de event log: uma unica *.jsonl sob
    input/, extraida com `extract_event_log_path` em vez de `extract_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    facts = []
    for jsonl in jsonl_files:
        facts.extend(extract_event_log_path(jsonl, repo_root=input_dir))
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_terraform(directory: Path) -> None:
    """Como `regen`, mas para fixtures de Terraform: `*.tf` sob input/, extraida
    com `extract_terraform_tree` em vez de `extract_tree`."""
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_terraform_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def main() -> int:
    targets = sys.argv[1:]

    if targets:
        for name in targets:
            # Um nome pode existir em mais de um corpus (ex.: "clean_job" em
            # fixtures/pyspark E fixtures/terraform -- e o nome mais comum de
            # fixture do repo, cada corpus tem o seu). Regenerar so o
            # primeiro achado regeneraria o corpus errado em silencio;
            # regenerar todos os que casam o nome e a unica opcao segura.
            matches = [
                (FIXTURES / name, regen),
                (FIXTURES_EVENTLOG / name, regen_eventlog),
                (FIXTURES_TERRAFORM / name, regen_terraform),
            ]
            found = [(path, fn) for path, fn in matches if path.is_dir()]
            if not found:
                print(f"fixture nao encontrada: {name}", file=sys.stderr)
                return 1
            if len(found) > 1:
                corpora = ", ".join(path.parent.name for path, _ in found)
                print(f"{name}: nome ambiguo, regenerando em todos os corpus ({corpora})")
            for path, fn in found:
                fn(path)
        return 0

    for directory in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        regen(directory)
    for directory in sorted(p for p in FIXTURES_EVENTLOG.iterdir() if p.is_dir()):
        regen_eventlog(directory)
    for directory in sorted(p for p in FIXTURES_TERRAFORM.iterdir() if p.is_dir()):
        regen_terraform(directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
