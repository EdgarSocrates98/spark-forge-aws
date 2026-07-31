# tests/test_installed_provenance.py
"""Afirma que `sparkforge` veio do pacote instalado, nao do repositorio.

Opt-in por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem isto o gate de paridade e
teatro: se o repositorio estiver no sys.path, `import sparkforge` pega o
codigo-fonte, os goldens batem com eles mesmos, e o teste passa sem provar que
o ARTEFATO funciona.

Nao basta configurar `cwd` e `PYTHONSAFEPATH`. Configuracao se perde num
refactor de workflow; assercao nao.
"""
import os
from pathlib import Path

import pytest

import sparkforge

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("SPARKFORGE_VERIFY_INSTALLED") != "1",
    reason="so roda sob o gate do artefato (scripts/verify_wheel.py)",
)


def _package_root() -> Path:
    assert sparkforge.__file__, "sparkforge sem __file__: import de namespace package?"
    return Path(sparkforge.__file__).resolve().parent


class TestProvenance:
    def test_sparkforge_is_not_imported_from_the_repository(self):
        package = _package_root()
        assert ROOT not in package.parents and package != ROOT / "sparkforge", (
            f"sparkforge foi importado de {package}, que esta dentro do repositorio "
            f"{ROOT}. O gate estaria comparando o repo consigo mesmo. "
            f"Rode a partir de um cwd fora do repo e com PYTHONSAFEPATH=1."
        )

    def test_sparkforge_lives_in_site_packages(self):
        package = _package_root()
        assert "site-packages" in package.parts, (
            f"sparkforge veio de {package}, fora de site-packages"
        )

    def test_the_catalog_comes_from_inside_the_package(self):
        """Se o catalogo vier da raiz de um repo qualquer que exista no cwd, o
        artefato nao esta sendo exercitado."""
        from sparkforge.rules.loader import catalog_dir

        assert _package_root() in catalog_dir().parents

    def test_the_packaged_catalog_is_complete(self):
        from sparkforge.rules.loader import load_catalog

        rules = load_catalog()
        assert len(rules) >= 48, f"catalogo embarcado com {len(rules)} regras"
        assert not [r for r in rules if r.get("blocked_on")]

    def test_knowledge_comes_from_inside_the_package(self):
        from sparkforge.knowledge_ref import knowledge_dir

        assert _package_root() in knowledge_dir().parents
