"""SDD_MIGRATION: o processo trocado sem apagar a historia.

Cada teste cobre um criterio de `docs/sdd/SDD_MIGRATION/define.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agentspec_desligado_no_projeto():
    config = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert config["enabledPlugins"]["agentspec@agentspec"] is False
