"""Testes do carregador de retencao de metrica do CloudWatch."""
from __future__ import annotations

import pytest

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
