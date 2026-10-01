import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    """Le `version = "..."` de [project]. Regex em vez de tomllib porque
    tomllib so existe em 3.11 e o CI tambem roda 3.10."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml sem `version = \"...\"` em [project]"
    return match.group(1)


def test_package_version_exposed():
    import sparkforge

    assert sparkforge.__version__ == _pyproject_version()


def test_every_manifest_declares_the_same_version():
    """As quatro fontes da versao tem que concordar.

    Fixar o literal num teste so faz o bump doer; nao impede o bump pela metade,
    que e a falha real -- `pip install` entrega uma versao, o plugin do Claude
    Code anuncia outra, e `manifest.json` uma terceira. O invariante e a
    concordancia, nao o numero.
    """
    expected = _pyproject_version()
    import sparkforge

    declared = {
        "pyproject.toml": expected,
        "sparkforge/__init__.py": sparkforge.__version__,
        "manifest.json": json.loads(
            (ROOT / "manifest.json").read_text(encoding="utf-8")
        )["version"],
        ".claude-plugin/plugin.json": json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )["version"],
    }
    divergent = {k: v for k, v in declared.items() if v != expected}
    assert not divergent, f"versao divergente em {divergent} (esperado {expected})"


def test_core_imports_without_optional_extras():
    """Core must not import boto3 or the MCP SDK. Devin CLI and CI run without them."""
    code = (
        "import sys;"
        "sys.modules['boto3'] = None;"
        "sys.modules['mcp'] = None;"
        "import sparkforge, sparkforge.findings, sparkforge.rules,"
        "sparkforge.findings.models, sparkforge.rules.expr,"
        "sparkforge.facts, sparkforge.case, sparkforge.adapters;"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
