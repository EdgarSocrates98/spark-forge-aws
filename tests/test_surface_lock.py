"""O gate da superficie: lock, e nao limiar.

Nao existe "20% e demais" que fonte nenhuma publique. O que existe e o numero
medido de hoje: crescer a superficie passa a exigir DECLARAR o crescimento,
igual a `docs/claims.lock.json` ja faz com alegacao publicada.
"""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.observability.surface import measure_surface

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "surface.lock.json"


def _lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


class TestOLockBateComAMedida:
    def test_the_lock_exists_and_declares_its_basis(self):
        lock = _lock()

        assert lock["schema_version"] == 1
        assert "json.dumps" in lock["basis"]

    def test_the_tool_catalogue_matches(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["tools"]["tool_count"] == lock["tools"]["tool_count"]
        assert medida["tools"]["total_bytes"] == lock["tools"]["total_bytes"]

    def test_the_skills_match(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["skills"]["document_count"] == lock["skills"]["document_count"]
        assert medida["skills"]["total_bytes"] == lock["skills"]["total_bytes"]

    def test_the_knowledge_matches(self):
        lock = _lock()
        medida = measure_surface()

        assert medida["knowledge"]["document_count"] == lock["knowledge"]["document_count"]
        assert medida["knowledge"]["total_bytes"] == lock["knowledge"]["total_bytes"]

    def test_nothing_is_unresolved(self):
        """Arquivo ilegivel na superficie e defeito, nao ruido."""
        medida = measure_surface()

        assert medida["skills"]["unresolved"] == []
        assert medida["knowledge"]["unresolved"] == []
