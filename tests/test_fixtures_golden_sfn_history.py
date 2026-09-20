"""Golden do corpus de historico de execucao do AWS Step Functions (`fixtures/sfn_history/`).

Cada fixture e sintetica, montada a partir da forma de evento publicada em
`API_GetExecutionHistory` (`previousEventId`, `stateEnteredEventDetails.name`,
`taskScheduledEventDetails.resource`/`resourceType`, `taskSubmittedEventDetails.output`):
nenhum historico real foi observado (U2 de `docs/sdd/SFN_HISTORY/define.md`).

A EXTRACAO SEGUE O CAMINHO DO PRODUTO, e o corpus separa os dois artefatos em
subdiretorios porque a PRODUCAO os separa: `analyze sfn-history --path <historico>` e
`analyze step-functions --path <definicao>` sao dois verbos com dois `--path`. Juntos
no mesmo diretorio, cada extrator leria o arquivo do outro e sairia um `sfn.unresolved`
cruzado por fixture -- ruido que nao e medida.

`scripts/regen_fixtures.py::regen_sfn_history` e o par deste `_extract`: se um deriva e
o outro nao, o golden nunca fecha.

Este modulo NAO e opcional: `test_fixtures_kind_coverage.py` casa o dominio pela linha
literal `FIXTURES = ...` abaixo, e `scripts/verify_wheel.py` roda os modulos
`test_fixtures_*.py` contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.sfn_history import (
    EXTRACTOR_ID,
    build_sfn_retry_observado,
    extract_sfn_history_tree,
)
from sparkforge.facts.stepfunctions import extract_stepfunctions_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sfn_history"

# Lista escrita a mao de proposito: fixture removida em silencio some do `parametrize`
# sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # SF-SFNX-001: tres tentativas contra um teto declarado de duas.
    "retry_acima_do_declarado",
    # O NEGATIVO dela, na FRONTEIRA: duas tentativas contra teto dois. E esta fixture
    # que mata a troca `>` por `>=` na `expr` da SF-SFNX-001.
    "retry_dentro_do_declarado",
    # SF-SFNX-002: TaskTimedOut num Task `.sync`.
    "task_timed_out_sync",
    # O NEGATIVO dela: um `.sync` que expira ANTES do `TaskSubmitted`. Nao ha
    # `sfn.job_run`, e a regra que manda ler o `JobRunId` tem de ficar calada.
    "task_timed_out_sem_submissao",
    # SF-SFNX-003: ExecutionAborted com o Task `.sync` agendado e sem terminal proprio.
    "execucao_abortada_com_task_em_voo",
    # O negativo das tres: uma execucao que correu e terminou.
    "execucao_limpa",
    # `includeExecutionData` desligado, e output de forma nao reconhecida (U1).
    "sem_execution_data",
    # `nextToken` na saida salva: o que foi lido continua valendo.
    "historico_truncado",
    # Tipo de evento que a lista conhecida nao tem.
    "evento_desconhecido",
    # JSON invalido, e JSON que nao e historico.
    "json_invalido",
    # Historico com tentativa demais e SEM ASL: o confronto nao acontece, a lacuna sai
    # nomeada, e a SF-SFNX-001 fica em `skipped` -- "nao perguntei", nunca "esta tudo bem".
    "historico_sem_asl",
    # Execucao RETOMADA: `ExecutionRedriven` no historico, e o ASL com `MaxAttempts` ao
    # lado. O confronto com o teto declarado e RECUSADO (`redrive_in_execution`), e a
    # SF-SFNX-001 fica calada sobre uma contagem que soma as tentativas de antes e as
    # de depois do redrive. As tentativas continuam publicadas.
    "execucao_com_redrive",
    # Dois ramos de um `Parallel` com um estado de mesmo nome: o nome nao identifica um
    # estado, nenhum `sfn.attempt` dele sai, e o de nome unico do mesmo historico
    # continua virando tentativa com indice.
    "parallel_estado_homonimo",
    # O alcance da recusa de nome nao para no `Parallel`: duas iteracoes de um `Map`
    # INLINE caem nela pelo mesmo criterio, e e por isso que esta fixture existe -- o
    # define so falava de `Parallel`. E e ela que prova a outra metade: o `sfn.job_run`
    # de cada iteracao SOBREVIVE a recusa, sem `#<n>` no simbolo e sem `attempt_index`.
    "map_inline_iteracoes",
    # A NEGATIVA das duas acima, e a que impede a correcao de virar regressao: o mesmo
    # estado reentrado TRES vezes em sequencia continua numerado 1..3. E ela que mata a
    # troca do teste de ancestralidade por um teste so de contagem de entradas.
    "retry_em_ramo_unico",
}


def fixture_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _extract(directory: Path):
    input_dir = directory / "input"
    historico = input_dir / "historico"
    definicao = input_dir / "definicao"
    alvo = historico if historico.is_dir() else input_dir
    facts = list(extract_sfn_history_tree(alvo, repo_root=input_dir))
    if definicao.is_dir():
        facts.extend(extract_stepfunctions_tree(definicao, repo_root=input_dir))
    # A MESMA guarda de `fusion.fuse`: sem `sfn.attempt` no pool, nada deriva.
    if any(f.kind == "sfn.attempt" for f in facts):
        facts.extend(build_sfn_retry_observado(facts))
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
def test_uma_sentinela_por_arquivo_de_historico(directory):
    """A sentinela e por ARQUIVO, e o prefixo `sfn.` e compartilhado com o ASL.

    `stepfunctions.py` tambem emite `sfn.analyzed` (D1: o prefixo e o mesmo de
    proposito), entao contar por kind misturaria os dois extratores. O filtro e
    `provenance.extractor`, que e o unico campo que os separa.
    """
    _, facts, _ = run_fixture(directory)
    input_dir = directory / "input"
    historico = input_dir / "historico"
    alvo = historico if historico.is_dir() else input_dir
    sentinelas = [
        f
        for f in facts
        if f.kind == "sfn.analyzed" and f.provenance["extractor"] == EXTRACTOR_ID
    ]
    assert len(sentinelas) == len(sorted(alvo.rglob("*.json")))
    for campo, kind in (
        ("attempt_count", "sfn.attempt"),
        ("job_run_count", "sfn.job_run"),
    ):
        esperado = sum(1 for f in facts if f.kind == kind)
        assert sum(s.measures[campo] for s in sentinelas) == esperado, campo
