#!/usr/bin/env python3
"""Validate analyze-functional-rules recommendation envelope offline."""
from pathlib import Path
import sys

_SHARED = Path(__file__).resolve().parents[2] / "_shared" / "scripts"
sys.path.insert(0, str(_SHARED))
from validate_skill_context import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(default_skill="analyze-functional-rules"))
