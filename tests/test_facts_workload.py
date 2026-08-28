"""Testes do extrator do inventario declarado de workload."""
from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.facts.workload import extract_workload_path


def _inventario(tmp_path: Path, payload) -> Path:
    alvo = tmp_path / "workload.yaml"
    alvo.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return alvo


class TestDeclared:
    def test_declares_sla_and_primary_source(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {
                "jobs": [
                    {"name": "etl-clientes", "sla_minutes": 45, "primary_source": "db.clientes"}
                ]
            },
        )

        facts = extract_workload_path(alvo)
        declarado = [f for f in facts if f.kind == "workload.declared"][0]

        assert declarado.subject["symbol"] == "etl-clientes"
        assert declarado.measures["sla_minutes"] == 45
        assert declarado.attrs["primary_source"] == "db.clientes"

    def test_partial_entry_declares_only_what_it_has(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": [{"name": "etl-parcial", "sla_minutes": 30}]})

        declarado = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared"
        ][0]

        assert declarado.measures["sla_minutes"] == 30
        assert "primary_source" not in declarado.attrs

    def test_sentinel_counts_the_jobs(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "a", "sla_minutes": 1}, {"name": "b", "sla_minutes": 2}]},
        )

        sentinela = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared_analyzed"
        ][0]

        assert sentinela.measures["jobs_declared"] == 2


class TestMalformed:
    def test_entry_without_name_is_unresolved_not_silence(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": [{"sla_minutes": 10}]})

        lacunas = [f for f in extract_workload_path(alvo) if f.kind == "workload.unresolved"]

        assert len(lacunas) == 1
        assert lacunas[0].attrs["reason"] == "entry_without_name"

    def test_entry_that_is_not_an_object_is_unresolved(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": ["isto-nao-e-um-objeto"]})

        lacunas = [f for f in extract_workload_path(alvo) if f.kind == "workload.unresolved"]

        assert [f.attrs["reason"] for f in lacunas] == ["entry_not_an_object"]

    def test_same_job_declared_twice_is_unresolved(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "dup", "sla_minutes": 1}, {"name": "dup", "sla_minutes": 2}]},
        )
        facts = extract_workload_path(alvo)

        declarados = [f for f in facts if f.kind == "workload.declared"]
        lacunas = [
            f
            for f in facts
            if f.kind == "workload.unresolved" and f.attrs["reason"] == "job_declared_twice"
        ]

        # A primeira declaracao vale; a segunda vira lacuna. Aceitar as duas
        # faria o fingerprint depender da ordem do arquivo.
        assert len(declarados) == 1
        assert len(lacunas) == 1

    def test_valid_entries_survive_a_malformed_neighbour(self, tmp_path):
        alvo = _inventario(
            tmp_path, {"jobs": [{"sla_minutes": 10}, {"name": "bom", "sla_minutes": 20}]}
        )

        declarados = [f for f in extract_workload_path(alvo) if f.kind == "workload.declared"]

        assert [f.subject["symbol"] for f in declarados] == ["bom"]


class TestAbsent:
    def test_missing_file_is_not_an_error(self, tmp_path):
        facts = extract_workload_path(tmp_path / "nao-existe.yaml")
        sentinela = [f for f in facts if f.kind == "workload.declared_analyzed"][0]

        assert sentinela.measures["jobs_declared"] == 0
        assert not [f for f in facts if f.kind == "workload.declared"]


class TestSchema:
    def test_every_emitted_fact_validates(self, tmp_path):
        from sparkforge.findings.validate import validate_fact

        alvo = _inventario(
            tmp_path,
            {
                "jobs": [
                    {"name": "bom", "sla_minutes": 10, "primary_source": "db.clientes"},
                    {"sla_minutes": 5},
                    "isto-nao-e-um-objeto",
                ]
            },
        )
        facts = extract_workload_path(alvo)

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())
