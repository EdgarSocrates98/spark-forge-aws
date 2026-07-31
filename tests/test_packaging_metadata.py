"""Metadata que o PyPI e o marketplace leem.

Sem `readme`, o pacote publicado aparece sem descricao. Sem `license`
declarado, o LICENSE do disco nao e legivel por ferramenta. Sem `urls`
correto, o link do pacote leva a lugar nenhum -- que e o estado de hoje no
plugin.json.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/EdgarSocrates98/spark-forge-aws"


def _pyproject() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


class TestPyprojectMetadata:
    def test_declares_readme(self):
        assert re.search(r'^readme\s*=\s*"README\.md"', _pyproject(), re.MULTILINE)

    def test_declares_license(self):
        assert re.search(r"^license\s*=", _pyproject(), re.MULTILINE)
        assert (ROOT / "LICENSE").is_file()

    def test_declares_authors(self):
        assert re.search(r"^authors\s*=", _pyproject(), re.MULTILINE)

    def test_declares_the_supported_pythons_as_classifiers(self):
        text = _pyproject()
        assert "Programming Language :: Python :: 3.10" in text
        assert "Programming Language :: Python :: 3.11" in text

    def test_urls_point_at_the_real_repository(self):
        assert REPO_URL in _pyproject()


class TestPluginManifest:
    def test_homepage_points_at_the_real_repository(self):
        data = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        assert data["homepage"] == REPO_URL

    def test_no_manifest_mentions_the_nonexistent_org(self):
        """`sparkforge-aws/spark-forge-aws` nao existe no GitHub. Instalar o
        plugin por esse link da 404, em silencio."""
        for name in ("pyproject.toml", ".claude-plugin/plugin.json", "manifest.json"):
            text = (ROOT / name).read_text(encoding="utf-8")
            assert "github.com/sparkforge-aws/" not in text, name
