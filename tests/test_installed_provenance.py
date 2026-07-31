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
        """Falha so quando o pacote E o diretorio-fonte do repositorio, nao
        quando o pacote so esta *hospedado* dentro dele.

        "Instalado" e "dentro do repositorio" nao sao mutuamente exclusivos:
        um venv criado na raiz do checkout (`.venv/`, comum em dev e em CI que
        faz build-in-place) poe `site-packages/sparkforge` como descendente de
        ROOT sem que o import venha do source. Comparar contra o diretorio-
        fonte exato -- em vez de "esta em algum lugar sob ROOT" -- e o que
        distingue os dois casos.
        """
        package = _package_root()
        source_dir = ROOT / "sparkforge"
        assert package != source_dir, (
            f"sparkforge foi importado do diretorio-fonte {source_dir}, dentro do "
            f"repositorio {ROOT}, em vez de um pacote instalado. O gate estaria "
            f"comparando o repo consigo mesmo. Rode a partir de um cwd fora do "
            f"repo, com PYTHONSAFEPATH=1 e `-o pythonpath=`, e confirme que o "
            f"pacote foi instalado a partir do wheel (nao `pip install -e .`)."
        )

    def test_sparkforge_lives_in_site_packages(self):
        package = _package_root()
        assert "site-packages" in package.parts, (
            f"sparkforge veio de {package}, fora de site-packages. Isso indica "
            f"instalacao nao-padrao (editable install, PYTHONPATH manual ou "
            f"vendoring). Reinstale a partir do wheel com "
            f"`pip install dist/*.whl` num venv limpo e rode o teste a partir "
            f"desse venv."
        )

    def test_the_catalog_comes_from_inside_the_package(self):
        """Se o catalogo vier da raiz de um repo qualquer que exista no cwd, o
        artefato nao esta sendo exercitado."""
        from sparkforge.rules.loader import catalog_dir

        package = _package_root()
        assert package in catalog_dir().parents, (
            f"catalog_dir() retornou {catalog_dir()}, que nao esta dentro do "
            f"pacote instalado em {package}. O catalogo provavelmente veio de "
            f"`rules/catalog` na raiz de algum repositorio no cwd, nao do "
            f"pacote embarcado no wheel -- confira `MANIFEST.in`/`pyproject.toml` "
            f"e reinstale a partir do wheel."
        )

    def test_the_packaged_catalog_is_complete(self):
        # Piso literal, nao invariante dinamico: sob o gate este teste roda fora
        # do repositorio (de proposito -- e o ponto do arquivo), entao nao ha
        # disco do repo para servir de segunda fonte/oraculo sem reintroduzir o
        # mesmo acesso que o teste existe para provar que nao acontece. `48` e
        # o piso conhecido do catalogo na Fase 2; sendo piso, ele pega
        # truncamento grosseiro (build quebrado, catalogo vazio ou parcial por
        # empacotamento errado) mas nao perda parcial que ainda deixe >= 48
        # regras -- essa classe de defeito exigiria um oraculo fora do artefato.
        from sparkforge.rules.loader import load_catalog

        rules = load_catalog()
        assert len(rules) >= 48, f"catalogo embarcado com {len(rules)} regras"
        assert not [r for r in rules if r.get("blocked_on")]

    def test_knowledge_comes_from_inside_the_package(self):
        from sparkforge.knowledge_ref import knowledge_dir

        package = _package_root()
        assert package in knowledge_dir().parents, (
            f"knowledge_dir() retornou {knowledge_dir()}, que nao esta dentro do "
            f"pacote instalado em {package}. O diretorio de knowledge "
            f"provavelmente veio da raiz de algum repositorio no cwd, nao do "
            f"pacote embarcado no wheel -- confira `MANIFEST.in`/`pyproject.toml` "
            f"e reinstale a partir do wheel."
        )
