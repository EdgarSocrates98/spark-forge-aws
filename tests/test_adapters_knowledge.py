"""Superficie de knowledge na CLI e no MCP.

Escape hatch barato: qualquer consumidor que precise LER um arquivo de
knowledge precisa primeiro saber onde ele esta, e num pacote instalado isso
esta dentro do site-packages.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from sparkforge.adapters import _core  # noqa: E402
from sparkforge.adapters.tools import TOOLS, call_tool  # noqa: E402


class TestCore:
    def test_without_file_returns_the_root(self):
        result = _core.knowledge_path()
        assert Path(result["root"]).is_dir()
        assert result["file"] is None

    def test_with_file_returns_the_resolved_path(self):
        result = _core.knowledge_path(file="glue/runtime-matrix.md")
        assert Path(result["file"]).is_file()
        assert result["file"].endswith("runtime-matrix.md")

    def test_lists_available_files_relative_to_the_root(self):
        """Listar e o que torna o verbo utilizavel sem adivinhacao."""
        result = _core.knowledge_path()
        assert "glue/runtime-matrix.md" in result["available"]
        assert all(not f.startswith("/") for f in result["available"])

    def test_missing_file_raises_adapter_error_not_a_traceback(self):
        with pytest.raises(_core.AdapterError) as excinfo:
            _core.knowledge_path(file="glue/nao-existe.md")
        assert "nao existe" in str(excinfo.value)

    def test_traversal_is_refused(self):
        with pytest.raises(_core.AdapterError):
            _core.knowledge_path(file="../pyproject.toml")


class TestCli:
    def test_knowledge_path_prints_json_with_the_root(self):
        result = subprocess.run(
            [sys.executable, "-m", "sparkforge.adapters.cli", "knowledge", "path"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert Path(json.loads(result.stdout)["root"]).is_dir()

    def test_knowledge_path_with_file(self):
        result = subprocess.run(
            [
                sys.executable, "-m", "sparkforge.adapters.cli",
                "knowledge", "path", "--file", "glue/runtime-matrix.md",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert Path(json.loads(result.stdout)["file"]).is_file()


class TestMcpTool:
    def test_the_tool_is_declared(self):
        assert "sparkforge_knowledge_path" in TOOLS

    def test_the_tool_answers(self):
        payload = call_tool("sparkforge_knowledge_path", {})
        assert Path(payload["root"]).is_dir()


class TestManifestsAgree:
    def test_manifest_lists_the_new_tool(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        assert "sparkforge_knowledge_path" in manifest["tools"]
