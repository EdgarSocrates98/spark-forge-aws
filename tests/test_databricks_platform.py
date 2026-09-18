"""Databricks como plataforma declarada, com fronteira onde o significado muda."""
from pathlib import Path

from sparkforge.adapters._core import build_runtime
from sparkforge.facts.runtime_detect import detect_runtime

ROOT = Path(__file__).resolve().parents[1]


def test_flag_declara_plataforma_e_deriva_spark():
    context, facts = build_runtime(databricks="15.4.x-scala2.12")
    assert context.databricks == "15.4"
    assert context.spark == "3.5.0"
    assert context.detected_from == ["cli"]
    assert context.to_dict()["databricks"] == "15.4"
    plataforma = next(f for f in facts if f.kind == "env.platform")
    assert plataforma.attrs["resolved"] == "databricks"
    divergente, _ = detect_runtime(
        {"cli": {"databricks_runtime": "15.4.x-scala2.12"}, "event_log": {"spark_version": "3.5.2"}}
    )
    assert "cli:matrix=3.5.0" in " ".join(divergente.divergences)
    maior, _ = build_runtime(databricks="18.0.x-scala2.13")
    assert (maior.databricks, maior.spark) == ("18.0", "4.1.0")
    fora, _ = build_runtime(databricks="9.1.x-scala2.12")
    assert (fora.databricks, fora.spark) == ("9.1", "")
