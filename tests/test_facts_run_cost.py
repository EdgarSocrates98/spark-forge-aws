"""Testes do fact de custo por run."""
from __future__ import annotations

import pytest

from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact


def _run(run_id="jr_1", dpu=3600.0, dpu_source="derived"):
    measures = {"execution_time_s": 600, "number_of_workers": 10}
    if dpu is not None:
        measures["dpu_seconds"] = dpu
    return Fact(
        kind="glue.job_run",
        subject={
            "type": "job_run",
            "job_name": "etl",
            "job_run_id": run_id,
            "symbol": run_id,
        },
        measures=measures,
        attrs={
            "state": "SUCCEEDED",
            "worker_type": "G.2X",
            "glue_version": "5.0",
            "autoscaling": False,
            "dpu_source": dpu_source,
        },
    )


class TestCusto:
    def test_cost_is_dpu_hours_times_the_published_price(self):
        # 3600 DPU-s = 1 DPU-hora. Ao preco publicado de 0.44, custo 0.44.
        facts = extract_run_cost([_run(dpu=3600.0)], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert custo.measures["dpu_hours"] == 1.0
        assert custo.measures["cost"] == pytest.approx(0.44)
        assert custo.measures["dpu_seconds"] == 3600.0

    def test_the_formula_is_the_one_aws_publishes(self):
        # A propria pagina de preco traz: 6 DPU * 0.25 h * 0.44 = 0.66.
        facts = extract_run_cost([_run(dpu=6 * 0.25 * 3600)], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert custo.measures["cost"] == pytest.approx(0.66)

    def test_both_caveats_travel_inside_the_fact(self):
        facts = extract_run_cost([_run()], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        # Regiao E versao de runtime. Uma ressalva que fica so no relatorio
        # se perde no primeiro salto.
        assert custo.attrs["region"] == "UNQUALIFIED"
        assert custo.attrs["runtime_version"] == "UNQUALIFIED"
        assert custo.attrs["price_source"].startswith("http")
        assert custo.attrs["price_retrieved"]
        assert custo.attrs["currency"] == "USD"

    def test_dpu_source_is_carried_from_the_run(self):
        derivado = extract_run_cost([_run(dpu_source="derived")], "facts.json")
        observado = extract_run_cost([_run(dpu_source="observed")], "facts.json")

        # Custo sobre DPU derivado e uma derivacao sobre outra, e o leitor
        # precisa saber sem ir atras do fact de origem.
        assert [f for f in derivado if f.kind == "glue.run_cost"][0].attrs[
            "dpu_source"
        ] == "derived"
        assert [f for f in observado if f.kind == "glue.run_cost"][0].attrs[
            "dpu_source"
        ] == "observed"

    def test_the_formula_is_in_the_provenance(self):
        facts = extract_run_cost([_run()], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert "dpu_hours" in custo.provenance["formula"]


class TestRecusas:
    def test_a_run_without_dpu_produces_a_gap_never_a_zero(self):
        facts = extract_run_cost([_run(dpu=None)], "facts.json")

        assert not [f for f in facts if f.kind == "glue.run_cost"]
        lacunas = [f for f in facts if f.kind == "glue.run_cost.unresolved"]
        assert len(lacunas) == 1
        assert lacunas[0].attrs["reason"] == "dpu_seconds_unavailable"

    def test_a_price_table_that_does_not_load_is_a_gap(self, monkeypatch):
        from sparkforge.facts import run_cost

        def boom(*_args, **_kwargs):
            from sparkforge.facts.pricing import PricingError

            raise PricingError("tabela ausente")

        monkeypatch.setattr(run_cost, "prices", boom)
        facts = extract_run_cost([_run()], "facts.json")

        assert [f.attrs["reason"] for f in facts] == ["price_unavailable"]

    def test_two_prices_without_an_axis_is_ambiguous_not_a_guess(self, monkeypatch):
        from sparkforge.facts import run_cost

        entrada = {
            "value": "0.44",
            "currency": "USD",
            "region": "UNQUALIFIED",
            "runtime_version": "UNQUALIFIED",
            "source": "https://aws.amazon.com/glue/pricing/",
            "retrieved": "2026-08-23",
        }
        monkeypatch.setattr(
            run_cost, "prices", lambda *a, **k: [entrada, {**entrada, "value": "0.51"}]
        )
        facts = extract_run_cost([_run()], "facts.json")
        lacuna = [f for f in facts if f.kind == "glue.run_cost.unresolved"][0]

        # Escolher um dos dois seria escolher pelo operador.
        assert lacuna.attrs["reason"] == "price_ambiguous"
        assert "0.44" in lacuna.attrs["detail"]
        assert "0.51" in lacuna.attrs["detail"]


class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        facts = extract_run_cost([_run(), _run("jr_2", dpu=None)], "facts.json")

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())
