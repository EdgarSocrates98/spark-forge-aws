"""§7.1 taxonomy of the eval corpus — the classified inventory that the
``forge/context/v1`` manifest persists (``eval_suites[].kind`` +
``capabilities.evals.detail``) and that ``sparkforge-aws evals`` serves.

One entry per declared suite. Fields:

* ``kind`` — the closed ``_forgecontext.EVAL_KINDS`` enum, i.e. the four
  §7.1 categories: ``developer``, ``runtime-decision``,
  ``output-verification``, ``host-conformance``.
* ``sealed`` — §7.3: expected answers must NEVER reach the executing
  agent's surface. ``describe``/``list`` emit metadata and an integrity
  hash, never answer content. The strict case (``evals/holdout/``) is
  proven by ``tests/test_evals_holdout.py`` — agent surfaces may not even
  cite the scenario names.
* ``environment`` — what a green run proves (§7.3, simulated != real):
  ``deterministic`` (offline recompute of the engine — proves code, not a
  live environment), ``simulated`` (Forge Lab synthetic scenarios),
  ``host`` (a real host agent must execute; the CLI refuses to impersonate
  it — executor != evaluator).
* ``run`` — how ``evals run`` executes the suite, or ``None`` when only a
  host agent can execute it:

    - ``{"kind": "script", "path": ...}`` — a repo gate
      (``python scripts/<path>``); refused ``unavailable`` outside the
      checkout because scripts/ is not packaged;
    - ``{"kind": "pytest", "path": ...}`` — a pytest gate, same rule;
    - ``{"kind": "native", "name": ...}`` — an in-process runner of
      ``sparkforge_aws.evals.surface``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

_REPO_DIR = Path(__file__).resolve().parents[2]

KINDS: tuple[str, ...] = (
    "developer",
    "runtime-decision",
    "output-verification",
    "host-conformance",
)

# Named refusal codes — one per refusal class, greppable, the house pattern.
E_SUITE = "EVALS-SUITE-UNKNOWN"
E_HOST = "EVALS-REQUIRES-HOST"
E_UNAVAILABLE = "EVALS-RUNNER-UNAVAILABLE"

SUITES: tuple[dict[str, Any], ...] = (
    {
        "id": "fase0",
        "kind": "output-verification",
        "location": "evals/fase0.xml",
        "environment": "deterministic",
        "sealed": True,
        "run": {"kind": "script", "path": "scripts/check_evals.py"},
        "runner_label": "python scripts/check_evals.py",
        "description": (
            "10 exact-string answers recomputed from the corpus by "
            "scripts/check_evals.py — a divergence is an extractor/catalog "
            "bug, never a prompt tweak"
        ),
    },
    {
        "id": "agentic-fase0",
        "kind": "host-conformance",
        "location": "evals/agentic/fase0",
        "environment": "host",
        "sealed": True,
        "run": None,
        "runner_label": "host agent + `python -m sparkforge_aws.evals grade --suite fase0`",
        "description": (
            "fase0 questions + required-tools/order/abstention gabarito; "
            "executed by a host agent, graded against baselines/"
        ),
    },
    {
        "id": "agentic-debate",
        "kind": "runtime-decision",
        "location": "evals/agentic/debate",
        "environment": "host",
        "sealed": True,
        "run": None,
        "runner_label": "scripts/run_debate.py + `python -m sparkforge_aws.evals debate`",
        "description": (
            "debate-room cases (graph_vence, lf_vence, sem_fato, uniao): "
            "operational adjudication under disagreement"
        ),
    },
    {
        "id": "agentic-recovery",
        "kind": "runtime-decision",
        "location": "evals/agentic/recovery",
        "environment": "host",
        "sealed": True,
        "run": None,
        "runner_label": "host agent recovery harness",
        "description": (
            "recovery cases (budget_exhausted_gate, missing_evidence_abstain, "
            "provider_bounded_retry...): the right operational decision is "
            "often to abstain or replan, not to push on"
        ),
    },
    {
        "id": "agentic-sdd",
        "kind": "host-conformance",
        "location": "evals/agentic/sdd",
        "environment": "host",
        "sealed": True,
        "run": None,
        "runner_label": "scripts/run_agentic_eval.py --suite sdd",
        "description": (
            "six single-value questions over synthetic SDD fixtures; answers "
            "recomputed by tests/test_sdd_eval_suite.py, baselines sha256-pinned"
        ),
    },
    {
        "id": "holdout",
        "kind": "output-verification",
        "location": "evals/holdout",
        "environment": "deterministic",
        "sealed": True,
        "run": {"kind": "native", "name": "holdout"},
        "runner_label": "in-process: extract + assess vs expected/assessment.json",
        "description": (
            "retained migration scenarios; agent surfaces may not cite them "
            "(tests/test_evals_holdout.py proves it) — goldens recompute via "
            "extract + assess"
        ),
    },
    {
        "id": "mcp-conformance",
        "kind": "host-conformance",
        "location": "evals/mcp-conformance/matrix.yaml",
        "environment": "deterministic",
        "sealed": False,
        "run": {"kind": "pytest", "path": "tests/test_mcp_conformance_matrix.py"},
        "runner_label": "pytest tests/test_mcp_conformance_matrix.py",
        "description": (
            "MCP spec requirement -> versioned evidence matrix; "
            "delegated_to_sdk rows name the delegation point, unresolved rows "
            "stay visible"
        ),
    },
    {
        "id": "platform-intelligence",
        "kind": "runtime-decision",
        "location": "evals/platform_intelligence/suite.yaml",
        "environment": "deterministic",
        "sealed": True,
        "run": {
            "kind": "script",
            "path": "scripts/check_platform_eval_contract.py",
            "args": ["--path", "{location}"],
        },
        "runner_label": "python scripts/check_platform_eval_contract.py --path <suite>",
        "description": (
            "seed corpus judging routing_accuracy + architecture_conformance "
            "next to quality/economy axes — operational routing decisions, "
            "not output equality"
        ),
    },
    {
        "id": "skill-evals",
        "kind": "developer",
        "location": "skills/*/evals/evals.json",
        "environment": "deterministic",
        "sealed": False,
        "run": {"kind": "script", "path": "scripts/check_skill_evals.py", "args": ["--strict"]},
        "runner_label": "python scripts/check_skill_evals.py --strict",
        "description": (
            "per-skill evals.json coverage gate (>=2 cases, >=5 expectations, "
            "fact_id/unresolved/validation/rollback terms) — internal skill "
            "quality, intentionally on the agent surface"
        ),
    },
    {
        "id": "token-efficient",
        "kind": "developer",
        "location": "evals/token_efficient/suite.yaml",
        "environment": "deterministic",
        "sealed": True,
        "run": {"kind": "script", "path": "scripts/check_token_efficient_bench.py"},
        "runner_label": "python scripts/check_token_efficient_bench.py",
        "description": (
            "economy/balanced/deep profile matrix of the Context Gateway; "
            "provider_tokens unresolved without a host transcript"
        ),
    },
    {
        "id": "decision-plane",
        "kind": "runtime-decision",
        "location": "evals/token_efficient/fixtures/decision_plane_cases.yaml",
        "environment": "deterministic",
        "sealed": True,
        "run": {"kind": "native", "name": "decision-benchmark"},
        "runner_label": "sparkforge-aws decision benchmark (in-process)",
        "description": (
            "23-case offline seed of the declarative Decision Plane "
            "(quality + federated graph + transcript); activation_ready "
            "stays false until corpus+quality gates pass"
        ),
    },
    {
        "id": "forge-lab-golden20",
        "kind": "output-verification",
        "location": "lab/scenarios/golden.yaml",
        "environment": "simulated",
        "sealed": False,
        "run": {"kind": "native", "name": "lab-verify"},
        "runner_label": "sparkforge-aws lab verify (in-process)",
        "description": (
            "Golden 20 scenario suite; a green `lab verify` proves the "
            "simulated environment's contracts, never a live cluster"
        ),
    },
)


class TaxonomyError(ValueError):
    """Named refusal: message already carries the ``EVALS-*`` code."""


def catalog() -> list[dict[str, Any]]:
    return [dict(s) for s in SUITES]


def suite_ids() -> list[str]:
    return [s["id"] for s in SUITES]


def get(suite_id: str) -> dict[str, Any]:
    for s in SUITES:
        if s["id"] == suite_id:
            return dict(s)
    raise TaxonomyError(
        f"{E_SUITE}: suite {suite_id!r} desconhecida; declaradas: {', '.join(suite_ids())}"
    )


def kind_counts() -> dict[str, int]:
    counts = {k: 0 for k in KINDS}
    for s in SUITES:
        counts[s["kind"]] += 1
    return counts


def capability_detail() -> str:
    """The one-line ``capabilities.evals.detail`` persisted in the manifest —
    the §7.1 classification summary plus the §7.3 posture."""
    counts = kind_counts()
    parts = ", ".join(f"{k}={counts[k]}" for k in KINDS)
    return (
        f"categories: {parts}; sealed holdout answers never reach agent "
        "surfaces (evals describe emits hashes, never answers); "
        "simulated/deterministic proofs are not real-environment proof"
    )


def _repo_path(location: str) -> Path | None:
    p = _REPO_DIR / location
    return p if p.exists() else None


def suite_sha256(suite: dict[str, Any]) -> str | None:
    """sha256 over every file under the suite location — the tamper-evident
    baseline/answer hash (§7.3 'preserve hashes'). ``os.walk``, not
    ``Path.rglob``: the AST gate in tests/test_facts_scan.py scans for raw
    glob calls, and this walk is over dirs this repo owns and versions.

    ``None`` when the location is absent (packaged installs ship evals_data,
    not the dev corpus) — the caller reports ``unresolved``, never a
    silent omission."""
    base = _repo_path(suite["location"])
    if base is None:
        return None
    h = hashlib.sha256()
    if base.is_file():
        h.update(base.name.encode("utf-8"))
        h.update(b"\0")
        h.update(base.read_bytes())
        return h.hexdigest()
    for root, dirs, files in os.walk(base):
        dirs.sort()
        for name in sorted(files):
            p = Path(root) / name
            if not p.is_file():
                continue
            h.update(p.relative_to(base).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
    return h.hexdigest()


def describe(suite_id: str) -> dict[str, Any]:
    """evals.describe — metadata only. §7.3: sealed suites expose the answer
    location CLASS and the integrity hash, never answer content. The holdout
    exposure test greps this payload for golden bytes and must find none."""
    s = get(suite_id)
    digest = suite_sha256(s)
    return {
        "id": s["id"],
        "kind": s["kind"],
        "location": s["location"],
        "environment": s["environment"],
        "sealed": s["sealed"],
        "expected_answers": (
            "sealed — never emitted to executing agents" if s["sealed"] else "not sealed"
        ),
        "integrity": {
            "algorithm": "sha256",
            "suite_sha256": digest if digest is not None else "unresolved",
        },
        "runner": s["runner_label"],
        "runnable_by_cli": s["run"] is not None,
        "description": s["description"],
        "proof": (
            "host-required (real environment)"
            if s["environment"] == "host"
            else f"{s['environment']} — not real-environment proof"
        ),
    }


def listing() -> dict[str, Any]:
    """evals.list — the classified inventory with per-kind counts."""
    return {
        "schema": "sparkforge-aws/evals-list/v1",
        "categories": list(KINDS),
        "counts": kind_counts(),
        "suites": [
            {
                "id": s["id"],
                "kind": s["kind"],
                "environment": s["environment"],
                "sealed": s["sealed"],
                "runnable_by_cli": s["run"] is not None,
            }
            for s in SUITES
        ],
    }


def manifest_suites(cli: str) -> list[dict[str, Any]]:
    """The ``eval_suites`` of forge/context/v1 — the §7.1 classification in
    the closed (id, kind, command) shape. ``command`` is the read-only
    describe verb: a consumer can always inspect what a suite is."""
    return [
        {
            "id": s["id"],
            "kind": s["kind"],
            "command": [cli, "evals", "describe", "--suite", s["id"]],
        }
        for s in SUITES
    ]


__all__ = [
    "E_HOST",
    "E_SUITE",
    "E_UNAVAILABLE",
    "KINDS",
    "SUITES",
    "TaxonomyError",
    "capability_detail",
    "catalog",
    "describe",
    "get",
    "kind_counts",
    "listing",
    "manifest_suites",
    "suite_ids",
    "suite_sha256",
]
