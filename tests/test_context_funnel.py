"""Tests for SparkForge Context Funnel and Progressive Disclosure (Phase 5)."""

from sparkforge.context import (
    ContextChunk,
    ContextFunnel,
    KnowledgePackLoader,
    ProgressiveDisclosureManager,
)


def test_context_funnel_deduplication():
    funnel = ContextFunnel(max_tokens_budget=1000)
    chunks = [
        ContextChunk(
            source_file="job.py", chunk_id="c1", content="df.repartition(10)", relevance_score=1.0
        ),
        ContextChunk(
            source_file="job.py", chunk_id="c2", content="df.repartition(10)", relevance_score=0.9
        ),  # Duplicate
        ContextChunk(
            source_file="util.py",
            chunk_id="c3",
            content="spark.read.parquet('s3://...')",
            relevance_score=0.8,
        ),
    ]
    minimal = funnel.build_minimal_context(chunks)
    assert minimal.deduplicated_count == 1
    assert len(minimal.chunks) == 2
    assert "df.repartition" in minimal.to_prompt_text()


def test_progressive_disclosure_levels(tmp_path):
    manager = ProgressiveDisclosureManager(root_dir=tmp_path)
    level_a = manager.get_level_a(
        skill_id="tune-glue",
        description="Optimize Glue workers and memory configuration",
        triggers=["glue OOM", "worker size"],
    )
    assert level_a.id == "tune-glue"
    assert level_a.estimated_tokens < 50

    # Level B
    skill_dir = tmp_path / "tune-glue"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "# Procedure\n1. Analyze worker type G.1X vs G.2X", encoding="utf-8"
    )
    level_b = manager.load_level_b(level_a, skill_dir)
    assert "G.1X vs G.2X" in level_b.procedure_content


def test_knowledge_pack_stale_detection(tmp_path):
    pack_dir = tmp_path / "aws-glue"
    pack_dir.mkdir()
    (pack_dir / "concise.md").write_text(
        "Glue runtime matrix and configurations.", encoding="utf-8"
    )
    (pack_dir / "metadata.json").write_text(
        '{"title": "AWS Glue", "last_verified": "2020-01-01"}', encoding="utf-8"
    )

    loader = KnowledgePackLoader(root_dir=tmp_path, max_age_days=90)
    pack = loader.load_pack(pack_dir)
    assert pack.domain == "aws-glue"
    assert pack.is_stale is True
    assert "threshold" in (pack.stale_reason or "")
