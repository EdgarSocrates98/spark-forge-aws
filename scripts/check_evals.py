#!/usr/bin/env python3
"""Reconfere cada resposta de evals/fase0.xml contra o corpus real.

Uma resposta que nao se reproduz e uma resposta errada no XML, nunca um
defeito do analisador -- o analisador ja e coberto por
tests/test_fixtures_golden.py. Este script recomputa os dez valores a partir
do codigo em execucao (fixtures, catalogo, GLUE_MATRIX) e compara com o texto
committado em evals/fase0.xml.

Usa defusedxml, nao xml.etree: o parser stdlib e vulneravel a XXE e billion
laughs por padrao. O arquivo e hoje controlado pelo repositorio, mas um
parser que so e seguro por causa de quem escreveu a entrada nao e seguro.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVAL_FILE = ROOT / "evals" / "fase0.xml"
FIXTURES = ROOT / "fixtures" / "pyspark"


def _pairs() -> list[tuple[str, str]]:
    tree = ET.parse(EVAL_FILE)
    return [
        (p.findtext("question", "").strip(), p.findtext("answer", "").strip())
        for p in tree.getroot().findall("qa_pair")
    ]


def _run_fixture(name: str) -> tuple[list[Any], list[Any]]:
    import yaml

    from sparkforge.facts.pyspark_ast import extract_tree
    from sparkforge.rules.engine import judge
    from sparkforge.rules.loader import load_catalog

    directory = FIXTURES / name
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings, _skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return facts, findings


def _compute_coalesce_one() -> str:
    _facts, findings = _run_fixture("coalesce_one")
    finding = findings[0]
    return f"{finding.rule_id}:{finding.subject['line']}"


def _compute_action_in_loop() -> str:
    _facts, findings = _run_fixture("action_in_loop")
    finding = findings[0]
    return f"{finding.severity}:{finding.measured['loop_depth']}"


def _compute_near_threshold() -> str:
    facts, findings = _run_fixture("near_threshold")
    run_fact = next(f for f in facts if f.kind == "pyspark.withcolumn_run")
    return f"{run_fact.measures['run_length']}:{len(findings)}"


def _compute_dynamic_dispatch() -> str:
    facts, findings = _run_fixture("dynamic_dispatch")
    unresolved = next(f for f in facts if f.kind == "pyspark.unresolved")
    return f"{len(findings)}:{unresolved.attrs['reason']}"


def _compute_clean_job() -> str:
    _facts, findings = _run_fixture("clean_job")
    return str(len(findings))


def _compute_sf_py_007() -> str:
    from sparkforge.rules.loader import load_catalog

    rules = load_catalog()
    rule = next(r for r in rules if r["id"] == "SF-PY-007")
    threshold = rule["threshold"]["run_length"]
    expr = rule["when"]["all"][0]["expr"]
    measure = expr.split(">=")[0].strip()
    return f"{threshold}:{measure}"


def _compute_glue_51_rule() -> str:
    from sparkforge.rules.loader import load_catalog

    rules = load_catalog()
    rule = next(r for r in rules if r.get("runtime_scope", {}).get("glue") == ">=5.1")
    return f"{rule['id']}:{rule['severity_default']}"


def _compute_glue_matrix() -> str:
    from sparkforge.facts.runtime_detect import GLUE_MATRIX

    entry = GLUE_MATRIX["5.0"]
    return f"{entry['spark']}:{entry['iceberg']}"


def _compute_join_before_reduction() -> str:
    _facts, findings = _run_fixture("join_before_reduction")
    finding = findings[0]
    return f"{finding.measured['join_index']}:{finding.measured['first_reduction_index']}"


def _compute_rule_counts() -> str:
    from sparkforge.rules.loader import load_catalog

    rules = load_catalog()
    athena = sum(1 for r in rules if r.get("category") == "athena")
    return f"{len(rules)}:{athena}"


# (marker, compute) -- marker deve ser uma substring unica de exatamente uma
# pergunta em evals/fase0.xml. A ordem aqui nao importa; o casamento e por
# conteudo, nao por posicao, para que reordenar perguntas no XML nao quebre
# o checker.
_CHECKS: tuple[tuple[str, Any], ...] = (
    ("coalesce_one", _compute_coalesce_one),
    ("action_in_loop", _compute_action_in_loop),
    ("near_threshold", _compute_near_threshold),
    ("dynamic_dispatch", _compute_dynamic_dispatch),
    ("clean_job", _compute_clean_job),
    ("SF-PY-007", _compute_sf_py_007),
    ("Glue >= 5.1", _compute_glue_51_rule),
    ("GLUE_MATRIX", _compute_glue_matrix),
    ("join_before_reduction", _compute_join_before_reduction),
    ("categoria athena", _compute_rule_counts),
)


def verify_all() -> list[str]:
    """Recomputa cada resposta do corpus e devolve a lista de divergencias."""
    if not EVAL_FILE.is_file():
        return [f"arquivo de eval ausente: {EVAL_FILE}"]

    pairs = _pairs()
    mismatches: list[str] = []

    for marker, compute in _CHECKS:
        matches = [(q, a) for q, a in pairs if marker in q]
        if len(matches) != 1:
            mismatches.append(
                f"marcador {marker!r} deveria casar exatamente 1 pergunta, casou {len(matches)}"
            )
            continue

        question, answer = matches[0]
        try:
            expected = compute()
        except Exception as exc:  # noqa: BLE001 -- reportado como divergencia, nao crash
            mismatches.append(f"{question!r}: falha ao recomputar: {exc}")
            continue

        if answer != expected:
            mismatches.append(
                f"{question!r}: resposta no XML é {answer!r}, recomputado é {expected!r}"
            )

    return mismatches


def main() -> int:
    mismatches = verify_all()
    if mismatches:
        for message in mismatches:
            print(message, file=sys.stderr)
        return 1
    print(f"{len(_pairs())} respostas verificadas contra o corpus, todas reproduzem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
