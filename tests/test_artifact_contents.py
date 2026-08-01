"""O artefato tem que carregar catalogo e knowledge.

Sem isto, `pip install` entrega `analyze` sem `judge` -- a camada `facts/`
embarca e a camada `rules/` nao. O teste constroi o wheel de verdade porque
inspecionar `pyproject.toml` provaria a intencao, nao o resultado: e o backend
que decide o que entra no zip.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> zipfile.ZipFile:
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"`python -m build` indisponivel ou falhou: {result.stderr[-400:]}")
    built = sorted(out.glob("*.whl"))
    assert built, "build terminou com sucesso e nao produziu wheel"
    return zipfile.ZipFile(built[0])


def _names(wheel: zipfile.ZipFile, prefix: str) -> list[str]:
    return [n for n in wheel.namelist() if n.startswith(prefix)]


class TestWheelCarriesTheKnowledgeLayer:
    def test_catalog_yaml_is_inside_the_package(self, wheel):
        found = _names(wheel, "sparkforge/rules/catalog/")
        assert [n for n in found if n.endswith(".yaml")], sorted(wheel.namelist())[:20]

    def test_routing_is_included_too(self, wheel):
        """`next_step` fica inerte sem routing.yaml, e o sintoma seria um
        roteamento vazio em vez de um erro."""
        assert "sparkforge/rules/catalog/routing.yaml" in wheel.namelist()

    def test_knowledge_is_inside_the_package(self, wheel):
        assert _names(wheel, "sparkforge/knowledge/")

    def test_schemas_survived_the_backend_swap(self, wheel):
        """`package-data` do setuptools embarcava os JSON Schemas. Se a troca de
        backend os perder, `validate_output` quebra no pacote instalado -- e a
        secao 5.2 da Fase 0 diz que finding sem schema nao e recusado."""
        assert _names(wheel, "sparkforge/findings/schemas/")

    def test_the_counts_are_not_zero(self, wheel):
        """Asserção de contagem: `force-include` sumindo num upgrade do
        hatchling nao quebraria import nenhum -- so devolveria catalogo
        vazio."""
        assert len(_names(wheel, "sparkforge/rules/catalog/")) >= 8
        assert len(_names(wheel, "sparkforge/knowledge/")) >= 15
