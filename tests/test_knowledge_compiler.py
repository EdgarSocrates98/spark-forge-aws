from __future__ import annotations

from pathlib import Path

from sparkforge.codeintel.query_expansion import expand_query
from sparkforge.knowledge_engine.compiler import compile_knowledge
from sparkforge.knowledge_engine.packs import PackRegistry


def test_query_expansion_is_versioned_and_deterministic() -> None:
    first = expand_query("skew no join")
    second = expand_query("skew no join")
    assert first == second
    assert first.vocabulary_version
    assert "aqe" in first.terms
    assert "join" in first.clusters


def test_knowledge_compiler_emits_source_hashes_and_lazy_pack_metadata(tmp_path: Path) -> None:
    pack = tmp_path / "glue"
    pack.mkdir()
    (pack / "runtime.md").write_text("# Runtime\nGlue 5.1 supports feature X.\n", encoding="utf-8")
    index = compile_knowledge(pack)
    assert index.claims[0].source_hash
    assert index.search(("feature",))[0].domain == "runtime"

    registry = PackRegistry(tmp_path)
    assert registry.descriptors()[0].domain == "glue"
    assert registry.select("glue", limit=1)[0]["source"] == "runtime.md"


def test_knowledge_pack_selection_uses_expanded_terms(tmp_path: Path) -> None:
    pack = tmp_path / "spark"
    pack.mkdir()
    (pack / "routing.md").write_text(
        "# Routing\nAdaptive Query Execution (AQE) is available.\n",
        encoding="utf-8",
    )

    matches = PackRegistry(tmp_path).select("skew no join", limit=1)

    assert matches[0]["source"] == "routing.md"
