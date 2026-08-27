"""Testes do carregador de retencao de metrica do CloudWatch."""
from __future__ import annotations

import pytest
import yaml

from sparkforge.facts import cloudwatch_retention as cwr


class TestTable:
    def test_loads_entries_sorted_by_period(self):
        table = cwr.retention_table()
        assert table, "tabela de retencao vazia"
        periods = [entry["period_seconds"] for entry in table]
        assert periods == sorted(periods)

    def test_every_entry_declares_evidence(self):
        for entry in cwr.retention_table():
            for field in ("source", "source_type", "retrieved"):
                assert entry.get(field), f"entrada sem {field}: {entry}"


class TestPeriodForAge:
    def test_recent_run_gets_the_finest_period(self):
        assert cwr.period_for_age_days(0.0) == 60

    def test_run_older_than_the_finest_retention_escalates(self):
        assert cwr.period_for_age_days(20.0) == 300

    def test_run_older_than_every_retention_returns_none(self):
        assert cwr.period_for_age_days(100_000.0) is None

    def test_negative_age_is_rejected(self):
        with pytest.raises(ValueError, match="idade negativa"):
            cwr.period_for_age_days(-1.0)


class TestFailClosed:
    """Espelha tests/test_glue_pricing.py:76-110 -- a refusa e provada por
    teste comitado, nao por script descartavel. Uma branch de validacao
    apagada por engano precisa quebrar o CI, nao passar em silencio.
    """

    @pytest.mark.parametrize(
        "mutacao",
        [
            {"source": ""},
            {"source_type": ""},
            {"retrieved": ""},
            {"source_type": "BLOG_QUALQUER"},
        ],
    )
    def test_entrada_sem_evidencia_estoura_na_carga(self, mutacao, tmp_path, monkeypatch):
        base = dict(cwr.retention_table()[0])
        base.update(mutacao)
        arquivo = tmp_path / "observability.yaml"
        arquivo.write_text(yaml.safe_dump({"retention": [base]}), encoding="utf-8")
        monkeypatch.setattr(cwr, "safe_knowledge_file", lambda *_: arquivo)
        cwr.retention_table.cache_clear()
        try:
            with pytest.raises(cwr.RetentionError):
                cwr.retention_table()
        finally:
            cwr.retention_table.cache_clear()

    @pytest.mark.parametrize(
        "mutacao",
        [
            {"period_seconds": 0},
            {"period_seconds": -60},
            {"period_seconds": "60"},
            {"retention_days": 0},
            {"retention_days": -15},
            {"retention_days": "15"},
        ],
    )
    def test_campo_de_retencao_invalido_estoura_na_carga(self, mutacao, tmp_path, monkeypatch):
        base = dict(cwr.retention_table()[0])
        base.update(mutacao)
        arquivo = tmp_path / "observability.yaml"
        arquivo.write_text(yaml.safe_dump({"retention": [base]}), encoding="utf-8")
        monkeypatch.setattr(cwr, "safe_knowledge_file", lambda *_: arquivo)
        cwr.retention_table.cache_clear()
        try:
            with pytest.raises(cwr.RetentionError):
                cwr.retention_table()
        finally:
            cwr.retention_table.cache_clear()

    def test_entrada_que_nao_e_mapa_estoura_na_carga(self, tmp_path, monkeypatch):
        arquivo = tmp_path / "observability.yaml"
        arquivo.write_text(
            yaml.safe_dump({"retention": ["nao sou um mapa"]}), encoding="utf-8"
        )
        monkeypatch.setattr(cwr, "safe_knowledge_file", lambda *_: arquivo)
        cwr.retention_table.cache_clear()
        try:
            with pytest.raises(cwr.RetentionError):
                cwr.retention_table()
        finally:
            cwr.retention_table.cache_clear()

    @pytest.mark.parametrize(
        "conteudo",
        [
            {},
            {"retention": []},
        ],
    )
    def test_tabela_vazia_estoura_em_vez_de_responder_zero(self, conteudo, tmp_path, monkeypatch):
        arquivo = tmp_path / "observability.yaml"
        arquivo.write_text(yaml.safe_dump(conteudo), encoding="utf-8")
        monkeypatch.setattr(cwr, "safe_knowledge_file", lambda *_: arquivo)
        cwr.retention_table.cache_clear()
        try:
            with pytest.raises(cwr.RetentionError):
                cwr.retention_table()
        finally:
            cwr.retention_table.cache_clear()
