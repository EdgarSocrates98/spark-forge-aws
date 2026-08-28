"""Testes do carregador do mapa canonico de metricas SQL."""
from __future__ import annotations

import pytest

from sparkforge.facts.sql_metric_names import MetricMapError, measure_for, load_map


class TestLoad:
    def test_known_name_maps_to_a_measure(self):
        assert measure_for("size of files read") == "bytes_read"
        assert measure_for("number of files read") == "files_read"

    def test_unknown_name_returns_none_instead_of_guessing(self):
        assert measure_for("bytes of shuffle write") is None
        assert measure_for("") is None

    def test_the_map_is_not_empty(self):
        assert len(load_map()) >= 4

    def test_every_entry_declares_where_it_was_verified(self):
        for entry in load_map().values():
            assert entry["verified_in"], entry


class TestFailClosed:
    def test_missing_file_raises_instead_of_returning_empty(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", tmp_path / "nao-existe.yaml")
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError, match="nao encontrado"):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()

    def test_malformed_file_raises_instead_of_returning_empty(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        alvo = tmp_path / "sql-metrics.yaml"
        alvo.write_text("metrics: nao-e-lista\n", encoding="utf-8")
        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", alvo)
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()

    def test_duplicate_published_name_raises(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        alvo = tmp_path / "sql-metrics.yaml"
        alvo.write_text(
            "version: 1\n"
            "metrics:\n"
            "  - {published: 'x', measure: a, metric_type: sum, verified_in: ['3.5.4']}\n"
            "  - {published: 'x', measure: b, metric_type: sum, verified_in: ['3.5.4']}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", alvo)
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError, match="duplicad"):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()
