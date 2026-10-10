#!/usr/bin/env python3
"""Validate propose-change-pr recommendation envelope offline."""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "_shared" / "scripts"
sys.path.insert(0, str(_SHARED))
from validate_skill_context import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(default_skill="propose-change-pr"))
