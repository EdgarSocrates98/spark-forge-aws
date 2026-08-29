"""Tests for SparkForge Platform Compilers and Exporters (Phase 6)."""
import pytest

from sparkforge.adapters.platforms import (
    PlatformCompiler,
)
from sparkforge.registry.loader import get_default_registry


def test_platform_compiler_all_targets(tmp_path):
    registry = get_default_registry()
    compiler = PlatformCompiler(registry=registry, root_dir=tmp_path)

    results = compiler.export_all(output_dir=tmp_path)
    assert "antigravity" in results
    assert "cursor" in results
    assert "claude" in results
    assert "devin" in results
    assert "windsurf" in results
    assert "copilot" in results
    assert "generic" in results

    # Verify Antigravity generated files
    ag_files = results["antigravity"]
    assert len(ag_files) > 0
    ag_agent_md = tmp_path / ".agents" / "agents" / "sf-orchestrator.md"
    assert ag_agent_md.is_file()
    content = ag_agent_md.read_text(encoding="utf-8")
    assert "GENERATED FROM CANONICAL SOURCE" in content
    assert "sf-orchestrator" in content

    # Verify Cursor MDC rules
    cursor_files = results["cursor"]
    assert len(cursor_files) > 0
    cursor_rule = tmp_path / ".cursor" / "rules" / "optimize-pyspark-code.mdc"
    assert cursor_rule.is_file()
    rule_content = cursor_rule.read_text(encoding="utf-8")
    assert "globs:" in rule_content
    assert "GENERATED FROM CANONICAL SOURCE" in rule_content


def test_invalid_target_raises(tmp_path):
    compiler = PlatformCompiler(root_dir=tmp_path)
    with pytest.raises(ValueError, match="Unknown platform target"):
        compiler.export_target("unknown_target", output_dir=tmp_path)
