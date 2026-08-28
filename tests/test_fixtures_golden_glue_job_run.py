"""Golden do corpus sintetico de historico de runs Glue.

Modulo dedicado, e nao mais uma classe dentro de `test_facts_glue_job_run.py`,
porque `test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module`
cobra um `test_fixtures_*.py` que declare o dominio: dominio sem modulo proprio
existe, parece cobertura, e o gate de wheel nunca o executa contra o pacote
instalado. `GOLDEN_MODULES` em `scripts/verify_wheel.py` e derivado do glob
`test_fixtures_*.py`, entao este arquivo entra la sozinho.

Os cenarios nao tem `expected/facts.json` byte-exato como os goldens de Athena
e EMR: nenhuma regra do catalogo consome `glue.job_run.*` ou `glue.metric*`
ainda, entao nao ha `expects_rules` para escrever. O que estes testes travam e
a semantica de cada cenario -- capacidade que nao funde, grupo marcado como
`mixed`, recusa sob Auto Scaling, correlacao completa -- e a ausencia de
classificacao de tamanho de workload, que e a fase seguinte.
"""
import json
from pathlib import Path

from sparkforge.facts.glue_job_run import extract_glue_job_runs_path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "glue_job_run"


class TestGoldenScenarios:
    def test_capacity_change_never_merges_groups(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "capacity_changed_midway" / "runs", "synthetic-job"
        )
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]

        capacidades = {
            (f.subject["worker_type"], f.subject["number_of_workers"]) for f in dists
        }
        assert len(capacidades) > 1
        for fact in dists:
            assert fact.measures["n"] >= 1

    def test_mixed_group_is_marked(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "mixed_dpu_source" / "runs", "synthetic-job"
        )
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]
        assert any(f.attrs["dpu_source"] == "mixed" for f in dists)

    def test_all_failed_produces_no_succeeded_distribution(self):
        facts = extract_glue_job_runs_path(FIXTURES / "all_failed" / "runs", "synthetic-job")
        dists = [f for f in facts if f.kind == "glue.job_run.distribution"]

        assert dists
        assert all(f.subject["state"] == "FAILED" for f in dists)
        outcome = [f for f in facts if f.kind == "glue.job_run.outcome"][0]
        assert outcome.measures["n_succeeded"] == 0

    def test_small_primary_input_never_implies_small_workload(self):
        """O teste que o documento de origem chama de mais importante.

        Um batch de entrada pequeno nao autoriza concluir que o job e pequeno.
        Este extrator nao ve entrada nenhuma -- ve duracao, capacidade e
        desfecho -- e o teste trava isso: nenhum fact emitido aqui carrega
        classificacao de tamanho, porque classificar workload e a fase seguinte.
        """
        facts = extract_glue_job_runs_path(FIXTURES / "single_run" / "runs", "synthetic-job")
        blob = json.dumps([f.to_dict() for f in facts])
        for palavra in ("micro", "small", "medium", "large", "workload_class"):
            assert palavra not in blob

    def test_autoscaling_without_dpu_scenario_refuses(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "autoscaling_without_dpu" / "runs", "synthetic-job"
        )
        run = [f for f in facts if f.kind == "glue.job_run"][0]
        unresolved = [f for f in facts if f.kind == "glue.job_run.unresolved"]

        assert "dpu_seconds" not in run.measures
        assert any(
            f.attrs["reason"] == "dpu_unobservable_under_autoscaling" for f in unresolved
        )

    def test_correlated_scenario_emits_metrics_for_every_run(self):
        facts = extract_glue_job_runs_path(
            FIXTURES / "correlated" / "runs",
            "synthetic-job",
            cloudwatch_dir=FIXTURES / "correlated" / "cloudwatch",
        )
        metrics = [f for f in facts if f.kind == "glue.metric"]
        run_ids_with_metrics = {f.subject["job_run_id"] for f in metrics}

        assert run_ids_with_metrics == {"jr_0001", "jr_0002"}
        assert not [
            f
            for f in facts
            if f.kind == "glue.job_run.unresolved"
            and f.attrs["reason"] in ("cloudwatch_not_requested", "cloudwatch_artifact_missing")
        ]
