"""A matriz Databricks Runtime -> Spark e dado com fonte, nao constante."""
from pathlib import Path

import pytest
import yaml

from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]
PAGINA = "https://docs.databricks.com/aws/en/release-notes/runtime/"


def test_matriz_tem_fonte_data_e_vocabulario_fechado(tmp_path):
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

    invalida = tmp_path / "runtime-matrix.yaml"
    invalida.write_text(
        "schema_version: 1\nsources: []\nretrieved: '2026-09-17'\n"
        "versions:\n  '15.4':\n    spark: '3.5.0'\n    python: '3.11'\n",
        encoding="utf-8",
    )
    with pytest.raises(runtime_matrix.RuntimeMatrixError, match="python"):
        runtime_matrix._carrega_matriz_fechada(
            invalida, runtime_matrix.DATABRICKS_COMPONENTS, "Databricks"
        )
