from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.architecture.streaming import analyze_streaming_architecture


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "realtime_architecture"


def test_realtime_architecture_goldens():
    for directory in sorted(path for path in FIXTURES.iterdir() if path.is_dir()):
        meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
        actual = analyze_streaming_architecture(directory / meta["artifact"])
        expected = json.loads(
            (directory / "expected" / "result.json").read_text(encoding="utf-8")
        )
        assert actual == expected
        assert actual["decision"]["status"] == meta["expected_status"]
        assert actual["decision"]["selected"] == meta["expected_selected"]
