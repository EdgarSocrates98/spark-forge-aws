"""Golden do corpus de definicao ASL do AWS Step Functions (`fixtures/stepfunctions/`).

Cada fixture e sintetica, montada a partir dos exemplos oficiais
(`arn:aws:states:::glue:startJobRun.sync`, `JobName` em `Parameters`/`Arguments`):
nenhum ASL real foi observado (U2 de `docs/sdd/STEP_FUNCTIONS/define.md`).

A EXTRACAO SEGUE O CAMINHO DO PRODUTO. Fixture so com `.json` e o que
`analyze step-functions` seguido de `judge` ve. Fixture com `main.tf` ao lado e o que
`fuse` ve com os dois lados no pool: extrai o Terraform e deriva `sfn.glue_job_link`
com `build_sfn_glue_link`, a mesma funcao que `fusion.fuse` chama.
`scripts/regen_fixtures.py::regen_stepfunctions` e o par deste `_extract`: se um
deriva e o outro nao, o golden nunca fecha.

Este modulo NAO e opcional: `test_fixtures_kind_coverage.py` casa o dominio pela linha
literal `FIXTURES = ...` abaixo, e `scripts/verify_wheel.py` roda os modulos
`test_fixtures_*.py` contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.stepfunctions import build_sfn_glue_link, extract_stepfunctions_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "stepfunctions"

# Lista escrita a mao de proposito: fixture removida em silencio some do `parametrize`
# sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # SF-SFN-001: startJobRun sem .sync, com Next.
    "glue_sem_sync",
    # SF-SFN-002 nos dois ramos de severidade: MaxAttempts omitido (P1) e declarado (P2).
    "glue_retry_implicito",
    "glue_retry_explicito",
    # SF-SFN-003: describe-state-machine com type EXPRESS e .sync.
    "express_com_sync",
    # O negativo: .sync, retry so de erro nomeado, TaskFailed com MaxAttempts 0 -- esta
    # ultima e a fronteira que mata a troca `>` -> `>=` da SF-SFN-002.
    "glue_limpo",
    # sfn.unresolved do extrator: JSON invalido e JSON que nao e state machine.
    "definicao_ilegivel",
    # SF-SFN-004 (e SF-SFN-002): o ASL e o aws_glue_job com max_retries 2.
    "retry_duas_camadas",
    # JobName.$ nao liga: sfn.unresolved job_name_dynamic, SF-SFN-004 calada.
    "job_name_dinamico",
    # As duas fronteiras da SF-SFN-004: liga, mas uma das camadas e zero.
    "retry_so_no_step_functions",
    "retry_so_no_glue",
}


def fixture_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = list(extract_stepfunctions_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        facts.extend(build_sfn_glue_link(facts))
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
    sentinelas = [f for f in facts if f.kind == "sfn.analyzed"]
    assert len(sentinelas) == len(list((directory / "input").glob("*.json")))
    for campo, kind in (("state_machine_count", "sfn.state_machine"), ("task_count", "sfn.task")):
        esperado = sum(1 for f in facts if f.kind == kind)
        assert sum(s.measures[campo] for s in sentinelas) == esperado, campo
