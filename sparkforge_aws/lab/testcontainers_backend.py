"""Optional Testcontainers adapter entry point.

The module emits a plan and deliberately does not import the optional
testcontainers package at module import time. CI can install it for L1 runs;
offline analysis remains dependency-free.
"""

from __future__ import annotations

import argparse
import json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forge Lab Testcontainers plan")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            {
                "backend": "testcontainers",
                "scenario": args.scenario,
                "profile": args.profile,
                "execute": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
