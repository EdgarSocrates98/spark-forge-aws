"""Run the versioned deterministic token-efficient profile matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sparkforge_aws.evals.token_benchmark import load_benchmark_suite, run_benchmark_matrix

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals" / "token_efficient"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="JSON output path.")
    args = parser.parse_args()
    result = run_benchmark_matrix(load_benchmark_suite(SUITE))
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {"suite": result["suite"], "results": len(result["results"])},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
