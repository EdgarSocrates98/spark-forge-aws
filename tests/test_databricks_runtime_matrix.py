"""A matriz Databricks Runtime -> Spark e dado com fonte, nao constante."""
from pathlib import Path

import pytest
import yaml

import sparkforge.knowledge_ref as kr
from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]
PAGINA = "https://docs.databricks.com/aws/en/release-notes/runtime/"


def test_matriz_tem_fonte_data_e_vocabulario_fechado():
    documento = yaml.safe_load(
        (ROOT / "knowledge" / "databricks" / "runtime-matrix.yaml").read_text(encoding="utf-8")
    )
    assert documento["sources"] == [PAGINA]
    assert documento["retrieved"] == "2026-09-17"
    assert runtime_matrix.DATABRICKS_COMPONENTS == frozenset({"spark"})
    assert runtime_matrix.databricks_sources() == (PAGINA,)
    assert runtime_matrix.load_databricks() == {
        "19": {"spark": "4.2.0"},
        "18": {"spark": "4.1.0"},
        "17.3": {"spark": "4.0.0"},
        "16.4": {"spark": "3.5.2"},
        "15.4": {"spark": "3.5.0"},
        "14.3": {"spark": "3.5.0"},
    }


def test_componente_fora_do_vocabulario_estoura(tmp_path, monkeypatch):
    """`load_databricks()` PUBLICO, nao `_carrega_matriz_fechada` privado --
    mesmo mecanismo de `tests/test_runtime_matrix.py::_matriz_sintetica`:
    `knowledge_dir()` resolve a partir do `__file__` de `knowledge_ref`, entao
    trocar esse atributo e a unica forma de isolar o corpo real do repositorio.

    O cache do `lru_cache` precisa ser limpo ANTES (senao o resultado real ja
    cacheado pelo teste acima venceria a matriz sintetica em silencio) E DEPOIS
    (senao os testes seguintes do modulo herdariam a matriz invalida deste
    `tmp_path`, que ja nem existe mais em disco) -- por isso o `finally`.
    """
    pacote = tmp_path / "site-packages" / "sparkforge"
    conhecimento = pacote / "knowledge"
    (conhecimento / "databricks").mkdir(parents=True)
    (conhecimento / "databricks" / "runtime-matrix.yaml").write_text(
        "schema_version: 1\nsources: []\nretrieved: '2026-09-17'\n"
        "versions:\n  '15.4':\n    spark: '3.5.0'\n    python: '3.11'\n",
        encoding="utf-8",
    )
    (conhecimento / "sources.lock.json").write_text('{"sources": {}}', encoding="utf-8")
    modulo = pacote / "knowledge_ref.py"
    modulo.touch()
    monkeypatch.delenv("SPARKFORGE_KNOWLEDGE", raising=False)
    monkeypatch.setattr(kr, "__file__", str(modulo))
    runtime_matrix.load_databricks.cache_clear()
    try:
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="python"):
            runtime_matrix.load_databricks()
    finally:
        runtime_matrix.load_databricks.cache_clear()
