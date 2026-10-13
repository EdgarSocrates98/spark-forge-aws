"""Guards da matriz de versões streaming.

A matriz é conhecimento versionado: o teste impede que ela volte a afirmar
uma release sem separar upstream/managed, sem fonte oficial ou sem explicitar
o limite de evidência local.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "knowledge" / "streaming" / "runtime-matrix.md"
LOCK = ROOT / "knowledge" / "sources.lock.json"


def _sources() -> list[str]:
    text = MATRIX.read_text(encoding="utf-8")
    return [line[2:].strip() for line in text.splitlines() if line.startswith("- http")]


def test_streaming_runtime_matrix_has_explicit_states_and_boundaries() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    assert "Data da revalidação: 2026-10-02." in text
    assert "`VERIFIED`" in text
    assert "`UNRESOLVED`" in text
    assert "`N/A + motivo`" in text
    assert "runtime efetivo" in text
    assert "Divergência" in text


def test_every_streaming_matrix_source_is_in_the_offline_source_lock() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    watched = set(lock["sources"])
    assert _sources()
    assert set(_sources()) <= watched


def test_streaming_runtime_matrix_is_in_the_offline_bundle() -> None:
    manifest = json.loads(
        (ROOT / "knowledge" / "offline-manifest.json").read_text(encoding="utf-8")
    )
    paths = {item["path"] for item in manifest["documents"]}
    assert "knowledge/streaming/runtime-matrix.md" in paths
