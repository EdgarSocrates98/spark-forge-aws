"""The ``sparkforge-aws evals`` surface — §7.2 ops ``evals.list``,
``evals.describe``, ``evals.run``, ``evals.result`` over the classified
taxonomy of ``sparkforge_aws.evals.taxonomy``.

Security contract (§7.3), enforced here and tested in
``tests/test_evals_surface.py``:

* sealed expected answers are NEVER emitted — ``list``/``describe`` carry
  counts, locations and an integrity hash only;
* suites a host must execute refuse ``EVALS-REQUIRES-HOST`` instead of
  being impersonated by the CLI — the executor and the evaluator are
  different actors;
* every run result marks ``environment`` — ``deterministic``/``simulated``
  are never reported as real-environment proof.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from sparkforge_aws.evals import taxonomy

_REPO_DIR = Path(__file__).resolve().parents[2]

# Run dir names: first char alnum, then word chars/dots/dashes — no
# separators, no ``..`` escape, no absolute paths (§13.1).
_SAFE_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# Timeout for delegated gates — deterministic, bounded, never a hang.
_RUN_TIMEOUT_S = 300


def _envelope(suite: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Every result carries the §7.3 markers: what environment proved it and
    whether the answers stay sealed."""
    return {
        "schema": "sparkforge-aws/evals-run/v1",
        "suite": suite["id"],
        "kind": suite["kind"],
        "environment": suite["environment"],
        "real_environment_proof": suite["environment"] == "host",
        "sealed": suite["sealed"],
        **extra,
    }


def run(suite_id: str) -> dict[str, Any]:
    """evals.run — dispatch to the suite's declared runner.

    Host-required suites are a named refusal, not a synthetic execution:
    the agent-level suite measures a host agent, and a CLI that faked the
    run would be the evaluator impersonating the executor (§7.3).
    """
    s = taxonomy.get(suite_id)
    spec = s["run"]
    if spec is None:
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_HOST}: suite {suite_id!r} mede um agente de host; "
            "a CLI nao a executa (executor != avaliador). Execute no host e "
            f"pontue com `{s['runner_label']}`"
        )
    kind = spec["kind"]
    if kind == "native":
        return _envelope(s, **_run_native(spec["name"], s))
    if kind in ("script", "pytest"):
        return _envelope(s, **_run_delegated(spec, s))
    raise taxonomy.TaxonomyError(
        f"{taxonomy.E_UNAVAILABLE}: runner kind {kind!r} desconhecido para {suite_id!r}"
    )


def _run_native(name: str, suite: dict[str, Any]) -> dict[str, Any]:
    if name == "holdout":
        return _run_holdout(suite)
    if name == "lab-verify":
        return _run_lab_verify()
    if name == "decision-benchmark":
        return _run_decision_benchmark(suite)
    raise taxonomy.TaxonomyError(
        f"{taxonomy.E_UNAVAILABLE}: runner nativo {name!r} desconhecido"
    )


def _run_delegated(spec: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    """script/pytest gates run as documented: the same argv a developer
    types, in a subprocess, captured and bounded. Outside the checkout the
    file is absent and the refusal is named — an installed wheel honestly
    reports the gate as ``unavailable`` instead of inventing a verdict."""
    path = _REPO_DIR / spec["path"]
    if not path.is_file():
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: {spec['path']} so existe no checkout; "
            "o pacote instalado nao carrega os gates de desenvolvimento"
        )
    if spec["kind"] == "pytest":
        argv = [sys.executable, "-m", "pytest", spec["path"], "-q"]
    else:
        args = [a.replace("{location}", suite["location"]) for a in spec.get("args", ())]
        argv = [sys.executable, spec["path"], *args]
    proc = subprocess.run(  # noqa: S603 — argv e a spec declarada da suite (sys.executable + arquivo versionado)
        argv,
        cwd=_REPO_DIR,
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_S,
        check=False,
    )
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "exit_code": proc.returncode,
        "runner": spec["path"],
        "output_tail": (proc.stdout + proc.stderr).strip()[-2000:],
    }


def _run_holdout(suite: dict[str, Any]) -> dict[str, Any]:
    """Recompute each holdout scenario (extract + assess) and compare with
    the sealed golden. The report says match/mismatch and which rule_ids
    the ENGINE fired — it never echoes the expected answer payload back,
    so the run artifact is safe to paste anywhere."""
    import yaml

    from sparkforge_aws.facts.migration import extract_migration_tree
    from sparkforge_aws.facts.scan import iter_source_files
    from sparkforge_aws.facts.terraform import extract_terraform_tree
    from sparkforge_aws.migration.assessment import assess

    base = _REPO_DIR / suite["location"]
    if not base.is_dir():
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: {suite['location']} ausente "
            "(o corpus de holdout vive no checkout, nao no wheel)"
        )
    results: list[dict[str, Any]] = []
    for scenario_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        meta = yaml.safe_load((scenario_dir / "meta.yaml").read_text(encoding="utf-8"))
        input_dir = scenario_dir / "input"
        facts = list(extract_migration_tree(input_dir, repo_root=input_dir))
        if any(iter_source_files(input_dir, "*.tf")):
            facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        resultado = assess(facts, source=str(meta["source"]), target=str(meta["target"]))
        expected = json.loads(
            (scenario_dir / "expected" / "assessment.json").read_text(encoding="utf-8")
        )
        results.append(
            {
                "scenario": scenario_dir.name,
                "match": resultado.to_dict() == expected,
                "rules_fired": sorted({f.rule_id for f in resultado.findings}),
                "facts": len(facts),
            }
        )
    return {
        "status": "pass" if all(r["match"] for r in results) else "fail",
        "scenarios": results,
        "expected_answers": "sealed — compared server-side, never echoed",
    }


def _run_lab_verify() -> dict[str, Any]:
    """`lab verify` in-process: registry + Golden 20 + schemas + action
    plans, offline. ``environment: simulated`` — a green proves the lab
    contracts, not a live cluster."""
    import argparse

    from sparkforge_aws.lab.cli import dispatch
    from sparkforge_aws.lab.contract import LabContractError

    try:
        payload = dispatch(argparse.Namespace(lab_action="verify", repo=str(_REPO_DIR)))
    except LabContractError as exc:
        raise taxonomy.TaxonomyError(f"{taxonomy.E_UNAVAILABLE}: {exc}") from exc
    return {"status": "pass" if payload.get("valid") else "fail", "verify": payload}


def _run_decision_benchmark(suite: dict[str, Any]) -> dict[str, Any]:
    from sparkforge_aws.economy.decision_evaluation import DecisionEvaluationRunner

    fixture = _REPO_DIR / suite["location"]
    if not fixture.is_file():
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: {suite['location']} ausente no checkout"
        )
    payload = DecisionEvaluationRunner(str(_REPO_DIR)).run(str(fixture))
    return {
        "status": "pass" if payload.get("seed_passed") else "fail",
        "benchmark": payload,
    }


def _safe_run_dir(runs_root: Path, run_name: str) -> Path:
    """Resolve ``runs_root / run_name`` refusing traversal and absolute
    paths — a run is a directory *inside* the runs root, never an escape.
    Belt-and-suspenders: the name must match a safe pattern AND the
    resolved path must stay under the root."""
    if not _SAFE_RUN_NAME.match(run_name or ""):
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: run name {run_name!r} invalido — "
            "use [A-Za-z0-9._-] sem separadores"
        )
    root = runs_root.resolve()
    run_dir = (root / run_name).resolve()
    if run_dir != root and root not in run_dir.parents:
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: run {run_name!r} fora de {root}"
        )
    return run_dir


def result(suite_id: str, run_name: str) -> dict[str, Any]:
    """evals.result — the scorecard of a recorded agentic run.

    Only meaningful for host-executed suites (the deterministic ones emit
    their result at run time). Reads the run dir under
    ``~/.sparkforge_aws/agentic-evals/<run>`` and grades it — the same
    computation as ``python -m sparkforge_aws.evals grade`` — but never
    echoes the sealed gabarito: the scorecard carries per-question
    pass/fail, not the expected answers.
    """
    s = taxonomy.get(suite_id)
    if not suite_id.startswith("agentic-"):
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: evals.result aplica-se a suites "
            "executadas por host (agentic-*); suites deterministicas emitem "
            "o resultado no proprio `evals run`"
        )
    from sparkforge_aws.evals.cli import (
        DEBATE_RUNS_ROOT,
        RUNS_ROOT,
        SCORECARD,
        EvalError,
        eval_grade,
    )
    from sparkforge_aws.evals.debate_grade import GRADE_FILE, DebateGradeError, grade_debate_run
    from sparkforge_aws.evals.paths import suite_dir

    agentic_name = suite_id[len("agentic-"):]
    debate = agentic_name == "debate"
    runs_root = DEBATE_RUNS_ROOT if debate else RUNS_ROOT
    run_dir = _safe_run_dir(runs_root, run_name)
    if not run_dir.is_dir():
        raise taxonomy.TaxonomyError(
            f"{taxonomy.E_UNAVAILABLE}: run {run_name!r} ausente em {runs_root}; "
            "grave-o executando a suite num host"
        )
    scorecard_path = run_dir / (GRADE_FILE if debate else SCORECARD)
    if scorecard_path.is_file():
        payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    else:
        try:
            payload = (
                grade_debate_run(suite_dir(agentic_name), run_dir)
                if debate
                else eval_grade(suite_dir(agentic_name), run_dir)
            )
        except (EvalError, DebateGradeError) as exc:
            raise taxonomy.TaxonomyError(str(exc)) from exc
        scorecard_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return _envelope(s, status="ok", run=run_name, scorecard=payload)


__all__ = ["result", "run"]
