import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_exposed():
    import sparkforge

    assert sparkforge.__version__ == "0.4.0"


def test_core_imports_without_optional_extras():
    """Core must not import boto3 or the MCP SDK. Devin CLI and CI run without them.

    NOTE: Task 3 will extend this to import sparkforge.findings.models, and
    Task 2 will extend it to import sparkforge.rules.expr, once those modules exist.
    """
    code = (
        "import sys;"
        "sys.modules['boto3'] = None;"
        "sys.modules['mcp'] = None;"
        "import sparkforge, sparkforge.findings, sparkforge.rules,"
        "sparkforge.facts, sparkforge.case, sparkforge.adapters;"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
