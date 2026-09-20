"""Golden do corpus de DAG do Apache Airflow (`fixtures/airflow/`).

Cada fixture e sintetica, montada a partir dos exemplos da documentacao do provider
Amazon: nenhum DAG real foi observado (U2 de `docs/sdd/AIRFLOW_DAG/define.md`).

A EXTRACAO SEGUE O CAMINHO DO PRODUTO. Fixture so com `.py` e o que
`analyze airflow-dag` seguido de `judge` ve. Fixture com `main.tf` ao lado e o que
`fuse` ve com os dois lados no pool: extrai o Terraform e deriva `af.glue_job_link`
com `build_af_glue_link`, a mesma funcao que `fusion.fuse` chama.
`scripts/regen_fixtures.py::regen_airflow` e o par deste `_extract`: se um deriva e o
outro nao, o golden nunca fecha.

Este modulo NAO e opcional: `test_fixtures_kind_coverage.py` casa o dominio pela linha
literal `FIXTURES = ...` abaixo, e `scripts/verify_wheel.py` roda os modulos
`test_fixtures_*.py` contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.airflow_dag import build_af_glue_link, extract_airflow_dag_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "airflow"

# Lista escrita a mao de proposito: fixture removida em silencio some do `parametrize`
# sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # SF-AIRFLOW-001: wait_for_completion=False com tarefa a jusante.
    "sem_espera",
    # SF-AIRFLOW-002: execution_timeout declarado e stop_job_run_on_kill ausente.
    "timeout_sem_stop",
    # O negativo da espera na SF-AIRFLOW-002: os dois sinais, sem esperar o job.
    "timeout_sem_espera",
    # SF-AIRFLOW-003: espera o job sem deferrable.
    "espera_sincrona",
    # SF-AIRFLOW-004: DAG + o aws_glue_job com max_retries 2.
    "retry_duas_camadas",
    # O negativo da area: espera com deferrable, sem timeout, retries 0.
    "dag_limpo",
    # As duas fronteiras da SF-AIRFLOW-004: liga, mas uma das camadas e zero.
    "retry_so_no_glue",
    "retry_so_no_airflow",
    # `job_name` em Jinja nao liga: af.unresolved, SF-AIRFLOW-004 calada.
    "job_name_nao_literal",
    # O que a leitura estatica nao alcanca, contado em vez de adivinhado.
    "dag_dinamico",
    "python_invalido",
    "taskflow_decorador",
}


def fixture_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = list(extract_airflow_dag_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        facts.extend(build_af_glue_link(facts))
    return sort_facts(facts)


def run_fixture(directory: Path):
    meta = _meta(directory)
    facts = _extract(directory)
    return meta, facts, judge(facts, load_catalog(), meta["runtime"])


def _esperado(directory: Path, nome: str):
    return json.loads((directory / "expected" / nome).read_text(encoding="utf-8"))


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio vazio o pytest 8.x
# chama o callable sobre o sentinela NOTSET e aborta a sessao inteira.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
def test_golden(directory):
    meta, facts, findings = run_fixture(directory)
    assert [f.to_dict() for f in facts] == _esperado(directory, "facts.json")
    assert [f.to_dict() for f in findings] == _esperado(directory, "findings.json")
    assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))
    assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))
    for fact in facts:
        validate_fact(fact.to_dict())
    for finding in findings:
        validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
def test_uma_sentinela_por_arquivo_e_ela_conta_o_que_diz(directory):
    _, facts, _ = run_fixture(directory)
    sentinelas = [f for f in facts if f.kind == "af.analyzed"]
    assert len(sentinelas) == len(list((directory / "input").glob("*.py")))
    for campo, kind in (("dag_count", "af.dag"), ("task_count", "af.task")):
        esperado = sum(1 for f in facts if f.kind == kind)
        assert sum(s.measures[campo] for s in sentinelas) == esperado, campo


def test_nenhum_fact_do_dominio_carrega_snippet():
    """O DAG e codigo de terceiro: `subject.snippet` sairia com texto nao confiavel.

    `tests/test_harness_untrusted.py` mede o conjunto de extratores que produzem
    snippet, e `airflow_dag` nao entra nele -- este teste trava a decisao no dominio.
    """
    for directory in fixture_dirs():
        _, facts, _ = run_fixture(directory)
        for fact in facts:
            if fact.kind.startswith("af."):
                assert not fact.subject.get("snippet"), (directory.name, fact.kind)
