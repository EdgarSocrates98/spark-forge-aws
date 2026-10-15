#!/usr/bin/env python3
"""Forge Lab emitter — spark-forge-aws.

Two real deterministic scenarios, stdlib-only:
  1. lab-doctor          — sparkforge_*.lab.doctor.run_doctor readiness
     profile (host capabilities actually available, honestly counted).
  2. holdout-corpus      — every evals/holdout case must carry expected/
     ground truth + meta.yaml; integrity is measured, not assumed.
"""

from __future__ import annotations

import argparse
import json
import re as _re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FORGE = "spark-forge-aws"
SUITE = "spark-forge-aws-lab"


def _slug(s: object) -> str:
    return _re.sub(r"[^a-z0-9-]+", "-", str(s).lower()).strip("-") or "scenario"


def m(state: str, value: object = None, unit: str = "") -> dict:
    return {"state": state, "unit": unit, "value": value}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkout", required=True)
    ap.add_argument("--mode", default="A", choices=["A", "B", "C"])
    ap.add_argument("--result-out", required=True)
    a = ap.parse_args()
    checkout = Path(a.checkout).resolve()
    sys.path.insert(0, str(checkout))
    results = []

    # --- scenario 1: lab doctor readiness --------------------------------
    started = time.monotonic()
    try:
        from sparkforge_aws.lab.doctor import run_doctor

        d = run_doctor(checkout).to_dict()
        checks = d.get("checks", [])
        avail = sum(1 for c in checks if c.get("status") == "available")
        ready = bool(d.get("ready"))
        results.append(
            {
                "scenario_id": "lab-doctor",
                "verdict": "pass" if ready else "fail",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "detail": "; ".join(str(u) for u in (d.get("unresolved") or [])[:3]),
                "evidence_ref": "sparkforge/lab/doctor",
                "judge": None,
                "metrics": {
                    "success": m("measured", 1.0 if ready else 0.0, "ratio"),
                    "components_matched": m("measured", avail),
                    "components_total": m("measured", len(checks)),
                    "cost_usd": m("not_applicable"),
                    "tokens": m("not_applicable"),
                },
            }
        )
    except Exception as exc:  # honest failure, never silent
        results.append(
            {
                "scenario_id": "lab-doctor",
                "verdict": "fail",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "detail": f"{type(exc).__name__}: {exc}"[:300],
                "evidence_ref": "",
                "judge": None,
                "metrics": {
                    "success": m("measured", 0.0, "ratio"),
                    "cost_usd": m("not_applicable"),
                },
            }
        )

    # --- scenario 2: holdout corpus integrity -----------------------------
    started = time.monotonic()
    holdout = checkout / "evals" / "holdout"
    cases = sorted(p for p in holdout.iterdir() if p.is_dir()) if holdout.is_dir() else []
    complete = 0
    missing: list[str] = []
    for case in cases:
        ok = (
            (case / "meta.yaml").is_file() and any((case / "expected").iterdir())
            if (case / "expected").is_dir()
            else False
        )
        if ok:
            complete += 1
        else:
            missing.append(case.name)
    verdict = "pass" if cases and not missing else ("skipped" if not cases else "fail")
    results.append(
        {
            "scenario_id": "holdout-corpus",
            "verdict": verdict,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "detail": ("missing ground truth: " + ", ".join(missing[:5]))
            if missing
            else ("" if cases else "no cases under evals/holdout"),
            "evidence_ref": "evals/holdout",
            "judge": None,
            "metrics": {
                "success": m("measured", 1.0 if verdict == "pass" else 0.0, "ratio"),
                "components_matched": m("measured", complete),
                "components_total": m("measured", len(cases)),
                "reproducibility_rate": m("not_available"),
                "cost_usd": m("not_applicable"),
            },
        }
    )

    receipt = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "external": False,
        "suite": SUITE,
        "forge": FORGE,
        "mode": a.mode,
        "notes": [
            "domain benchmark scenarios pending case-runner wiring "
            "(cyc9-04/05 scope: declaration + integrity gates)"
        ],
        "producer": {"id": FORGE, "version": "lab-script"},
        "results": results,
    }
    out = Path(a.result_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
