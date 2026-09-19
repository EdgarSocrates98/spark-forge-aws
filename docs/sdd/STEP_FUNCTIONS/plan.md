---
sdd: 1
feature: STEP_FUNCTIONS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/STEP_FUNCTIONS/design.md
  sha256: "aff948caeb8f42656dfd11cb1b1163ac560e34016ce3fcb53e66257bfb654cbd"
tasks:
  - id: T1
    files: [sparkforge/facts/stepfunctions.py, tests/test_stepfunctions.py, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC1, AC2]
    test: {path: tests/test_stepfunctions.py, name: test_task_glue_vira_fact_com_retry_efetivo}
  - id: T2
    files: [tests/test_stepfunctions.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_adapters_tools.py, tests/test_harness_authorization.py, tests/test_fixtures_golden_mcp_parity.py, parity.yaml, manifest.json, agents/glue-infra-reviewer.md, .codex/agents/glue-infra-reviewer.toml, docs/surface.lock.json, docs/guia/referencia/tools/README.md, docs/guia/referencia/tools/sparkforge_analyze_step_functions.md, docs/guia/06-extrair-julgar-compor.md, docs/superpowers/STATUS.md, README.md, CLAUDE.md, AGENTS.md, GUIA_DE_USO.md, .devin/README.md, docs/harness/AUTHORIZATION-CHAIN.md, docs/harness/CURRENT-HARNESS-GAP.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC7]
    test: {path: tests/test_stepfunctions.py, name: test_cli_e_tool_devolvem_os_mesmos_facts}
  - id: T3
    files: [tests/test_stepfunctions.py, sparkforge/facts/stepfunctions.py, sparkforge/facts/fusion.py, rules/catalog/stepfunctions.yaml, rules/catalog/routing.yaml, agents/glue-infra-reviewer.md, fixtures/stepfunctions, tests/test_fixtures_golden_stepfunctions.py, scripts/regen_fixtures.py, tests/test_fixtures_kind_coverage.py, tests/test_rules_catalog_reachability.py, manifest.json, knowledge/sources.lock.json, .codex/agents/glue-infra-reviewer.toml, tests/test_databricks_rule_audit.py, tests/test_sf_stubs.py, fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, fixtures/scenarios/glue_51_para_60_iceberg_ansi/expected/assessment.json, fixtures/scenarios/glue_60_fgac_com_jar/expected/assessment.json, evals/holdout/config_por_caminho_indireto/expected/assessment.json, evals/holdout/lote_misto_iceberg_parquet/expected/assessment.json, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/guia/07-conhecimento-e-catalogo.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC3, AC4, AC5, AC6, AC8]
    test: {path: tests/test_fixtures_golden_stepfunctions.py, name: test_golden}
  - id: T4
    files: [knowledge/stepfunctions/glue-integration.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, docs/guia/usos/step-functions.md, docs/gates-por-mudanca.md, parity.yaml, docs/surface.lock.json, docs/superpowers/STATUS.md, docs/claims.lock.json]
    covers: [AC9, AC10]
    test: {path: tests/test_refresh_knowledge.py, name: TestWatchlistIsDerivedFromBothOrigins::test_the_committed_lock_matches_the_watchlist}
---

# STEP_FUNCTIONS — plano

> A branch `sdd/dominio-orquestrador` está empilhada sobre `sdd/criterio-de-dominio`
> (#89): `tests/test_criterio_de_dominio.py` e a seção "Critério de domínio: artefato
> antes de nome" de `docs/gates-por-mudanca.md` existem nesta árvore, e a AC8 fecha em T3.

## Regras de execução

- Branch `sdd/dominio-orquestrador`. Pouca memória: um comando por vez, nunca a suíte
  inteira nem os lotes de `tests/test_suite_batches.py` em paralelo com edição.
- Edição por ferramenta (Edit/Write), fim de linha LF. `rules/catalog/routing.yaml` tem
  BOM: edite com Edit, nunca reescreva o arquivo inteiro.
- Arquivo `.py` novo entra no índice (`git add <arquivo>`) antes de qualquer teste:
  `tests/test_arvore_versionada.py` reprova `.py` do pacote fora do git.
- **`python scripts/sync_skills.py` e `tests/test_agents_parity.py` apagam o
  `.claude/agents/README.md` não rastreado.** Antes de cada um:
  `cp .claude/agents/README.md "$TEMP/claude_agents_README.bak.md"`; depois:
  `cp "$TEMP/claude_agents_README.bak.md" .claude/agents/README.md`. O README nunca
  entra no `git add`.
- Agente se edita na fonte `agents/<nome>.md`; `.claude/`, `.agents/` e `.github/` saem
  do sync. `.codex/agents/<nome>.toml` é espelho à mão.
- Commit por tarefa com `git commit -F <arquivo no scratchpad>`, mensagem conventional
  em inglês, terminando com as duas linhas de atribuição da sessão.
- `python scripts/check_vnext_claims.py` antes de todo commit que acrescenta `.py` ou
  move `len(TOOLS)`. Remedie **pela lista de ids da saída do gate**, nunca por varredura;
  `--seed` reescreve o lock inteiro — se precisar dele, guarde só a entrada nova e
  devolva o resto com `git checkout docs/claims.lock.json`.
- Medidas deste plano, tiradas nesta árvore (já sobre o #89) em 2026-09-19, com as
  `MEDIDAS` de `scripts/check_status_numbers.py` (`0 divergencia(s)` na hora): 157 regras
  (97 `confirmed`, 60 `structural`, 26 com `runtime_scope` não-vazio), 28 áreas, 106 tools
  (98 com caminho, 38 com `detail_level`), 38 extratores, 228 kinds, 40 rotas, 12
  coordenadores, 51 skills, 516 fixtures em 56 domínios, 254 fontes (239 móveis). Se
  alguma divergir na hora de executar, publique a medida que o gate imprimir, não o
  número escrito aqui.
- `runtime_scope: {}` nas quatro `SF-SFN` (D4): o ASL sozinho não detecta Glue, e quem
  gateia é `requires_facts`. Nenhuma lista de guarda por versão
  (`GLUE_INFRA`, `AREA_MAY_VANISH_WHEN`, `GLUE_GUARDED_RULES`) muda.

## Por que quatro tarefas, e não cinco

A proposta inicial separava a `SF-SFN-004` e a derivação numa T4 própria. Medido: a
contagem do catálogo move seis registros (`manifest.json`, `STATUS.md`, `README.md`,
`docs/guia/07`, os cinco goldens de assessment e o lastro), e separar as regras em duas
tarefas moveria os seis duas vezes. E a área
precisa entrar inteira com rota e coordenador (`test_router_agents`,
`test_agent_coverage`). Então T3 leva as quatro regras, a derivação, a área, a rota, o
corpus e o golden; e a derivação fica em T3 e não em T1 porque o teste dela (AC6) só
fecha com a `SF-SFN-004` julgando.

O `sfn.glue_job_link` entra em `EMITTED_KINDS` só em T3: declarado em T1 sem golden, ele
deixaria `test_every_kind_of_every_extractor_appears_in_some_golden[stepfunctions]`
vermelho assim que o módulo entrasse nas listas.

## T1 — o extrator de ASL

### 1. Teste que falha

`tests/test_stepfunctions.py` (arquivo novo):

```python
"""O extrator de ASL do AWS Step Functions: o que a definicao diz sobre como chama o Glue.

Definicoes sinteticas, montadas a partir dos exemplos oficiais: nenhum ASL real foi
observado (U2 de `docs/sdd/STEP_FUNCTIONS/define.md`).
"""
import json

from sparkforge.facts.stepfunctions import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_TIMEOUT_SECONDS,
    extract_stepfunctions,
    extract_stepfunctions_path,
    extract_stepfunctions_tree,
)

ASL_COM_PARALLEL_E_MAP = {
    "Comment": "Glue .sync com retry implicito, Glue sem .sync, e um Map com Lambda",
    "StartAt": "Cargas",
    "States": {
        "Cargas": {
            "Type": "Parallel",
            "Branches": [
                {
                    "StartAt": "CargaClientes",
                    "States": {
                        "CargaClientes": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::glue:startJobRun.sync",
                            "Parameters": {"JobName": "carga-clientes"},
                            "Retry": [{"ErrorEquals": ["States.ALL"]}],
                            "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ClientesFalhou"}],
                            "End": True,
                        },
                        "ClientesFalhou": {"Type": "Fail"},
                    },
                },
                {
                    "StartAt": "CargaPedidos",
                    "States": {
                        "CargaPedidos": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::glue:startJobRun",
                            "Parameters": {"JobName.$": "$.job"},
                            "TimeoutSeconds": 3600,
                            "Next": "Esperar",
                        },
                        "Esperar": {"Type": "Wait", "Seconds": 5, "End": True},
                    },
                },
            ],
            "Next": "Lotes",
        },
        "Lotes": {
            "Type": "Map",
            "ItemProcessor": {
                "ProcessorConfig": {"Mode": "INLINE"},
                "StartAt": "Validar",
                "States": {
                    "Validar": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
                        "Parameters": {
                            "FunctionName": "validar-lote",
                            "Payload": {"token.$": "$$.Task.Token"},
                        },
                        "End": True,
                    }
                },
            },
            "End": True,
        },
    },
}

CLIENTES = "States/Cargas/Branches/0/States/CargaClientes"
PEDIDOS = "States/Cargas/Branches/1/States/CargaPedidos"
VALIDAR = "States/Lotes/ItemProcessor/States/Validar"


def _tasks(facts):
    return {f.subject["symbol"]: f for f in facts if f.kind == "sfn.task"}


def test_task_glue_vira_fact_com_retry_efetivo():
    facts = extract_stepfunctions(ASL_COM_PARALLEL_E_MAP, "sm.asl.json")
    tasks = _tasks(facts)
    assert set(tasks) == {CLIENTES, PEDIDOS, VALIDAR}

    clientes = tasks[CLIENTES]
    assert clientes.attrs["service"] == "glue"
    assert clientes.attrs["api"] == "startJobRun"
    assert clientes.attrs["pattern"] == "sync"
    assert clientes.attrs["job_name"] == "carga-clientes"
    assert clientes.attrs["job_name_dynamic"] is False
    assert clientes.attrs["retriers"] == [
        {
            "error_equals": ["States.ALL"],
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
            "max_attempts_defaulted": True,
        }
    ]
    assert clientes.attrs["failure_retry_matched"] is True
    assert clientes.attrs["failure_retry_defaulted"] is True
    assert clientes.measures["failure_retry_max_attempts"] == 3
    assert clientes.attrs["has_catch"] is True
    assert clientes.attrs["timeout_declared"] is False
    assert clientes.measures["timeout_seconds"] == DEFAULT_TIMEOUT_SECONDS
    assert clientes.attrs["state_machine_type"] == "undeclared"

    pedidos = tasks[PEDIDOS]
    assert pedidos.attrs["pattern"] == "request_response"
    assert pedidos.attrs["has_next"] is True
    assert pedidos.attrs["job_name"] is None
    assert pedidos.attrs["job_name_dynamic"] is True
    assert pedidos.attrs["job_name_source"] == "jsonpath"
    assert pedidos.attrs["retriers"] == []
    assert pedidos.attrs["failure_retry_matched"] is False
    assert pedidos.measures["failure_retry_max_attempts"] == 0
    assert pedidos.attrs["has_catch"] is False
    assert pedidos.attrs["timeout_declared"] is True
    assert pedidos.measures["timeout_seconds"] == 3600

    validar = tasks[VALIDAR]
    assert (validar.attrs["service"], validar.attrs["pattern"]) == ("lambda", "callback")
    assert validar.attrs["job_name_source"] == "not_applicable"

    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "undeclared"
    assert maquina.attrs["type_declared"] is False
    assert maquina.attrs["source"] == "asl"
    assert maquina.measures == {"state_count": 8, "task_count": 3}
    [sentinela] = [f for f in facts if f.kind == "sfn.analyzed"]
    assert sentinela.measures == {"state_machine_count": 1, "task_count": 3, "unresolved_count": 0}


def test_describe_state_machine_le_definition_e_tipo(tmp_path):
    definicao = {
        "StartAt": "Rodar",
        "States": {
            "Rodar": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Parameters": {"JobName": "carga-diaria"},
                "End": True,
            }
        },
    }
    express = {"name": "carga-expressa", "type": "EXPRESS", "definition": json.dumps(definicao)}
    sem_tipo = {"name": "carga", "definition": json.dumps(definicao)}
    (tmp_path / "express.json").write_text(json.dumps(express), encoding="utf-8")
    (tmp_path / "sem_tipo.json").write_text(json.dumps(sem_tipo), encoding="utf-8")

    facts = extract_stepfunctions_path(tmp_path / "express.json", repo_root=tmp_path)
    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "EXPRESS"
    assert maquina.attrs["type_declared"] is True
    assert maquina.attrs["source"] == "describe_state_machine"
    assert maquina.attrs["name"] == "carga-expressa"
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["state_machine_type"] == "EXPRESS"
    assert task.subject["file"] == "express.json"
    assert task.subject["symbol"] == "States/Rodar"

    facts = extract_stepfunctions_path(tmp_path / "sem_tipo.json", repo_root=tmp_path)
    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "undeclared"
    assert maquina.attrs["type_declared"] is False
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["state_machine_type"] == "undeclared"

    nao_string = {"name": "x", "type": "STANDARD", "definition": definicao}
    facts = extract_stepfunctions(nao_string, "q.json")
    motivos = [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"]
    assert motivos == ["definition_not_string"]


def test_o_que_nao_le_sai_nomeado(tmp_path):
    (tmp_path / "quebrado.asl.json").write_text('{"StartAt": "A", "States": {', encoding="utf-8")
    (tmp_path / "inventario.json").write_text('{"jobs": ["carga-diaria"]}', encoding="utf-8")
    facts = extract_stepfunctions_tree(tmp_path, repo_root=tmp_path)
    motivos = sorted(
        (f.subject["file"], f.attrs["reason"]) for f in facts if f.kind == "sfn.unresolved"
    )
    assert motivos == [
        ("inventario.json", "not_a_state_machine"),
        ("quebrado.asl.json", "invalid_json"),
    ]
    assert len([f for f in facts if f.kind == "sfn.analyzed"]) == 2

    asl = {
        "QueryLanguage": "JSONata",
        "StartAt": "Dinamico",
        "States": {
            "Dinamico": {"Type": "Task", "Resource": "{% $states.input.recurso %}", "End": True},
            "Jsonata": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Arguments": {"JobName": "{% $states.input.job %}"},
                "Retry": [
                    {"ErrorEquals": ["Glue.ConcurrentRunsExceededException"], "MaxAttempts": 5},
                    {"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 0},
                ],
                "End": True,
            },
            "Texto": "nao e um estado",
        },
    }
    facts = extract_stepfunctions(asl, "sm.asl.json")
    motivos = {f.subject["symbol"]: f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"}
    assert motivos == {"States/Dinamico": "resource_dynamic", "States/Texto": "state_not_an_object"}
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["job_name_source"] == "jsonata"
    assert task.attrs["job_name_dynamic"] is True
    assert task.attrs["query_language"] == "JSONata"
    assert task.attrs["failure_retry_matched"] is True
    assert task.attrs["failure_retry_defaulted"] is False
    assert task.measures["failure_retry_max_attempts"] == 0
```

### 2. Rodar e ver falhar

```bash
git add tests/test_stepfunctions.py
python -m pytest tests/test_stepfunctions.py -q
```

Falha esperada: `ModuleNotFoundError: No module named 'sparkforge.facts.stepfunctions'` na
coleta — o módulo ausente é a unidade sob teste.

### 3. Código mínimo

`sparkforge/facts/stepfunctions.py` (arquivo novo, inteiro):

```python
"""Extrator de Facts a partir da definicao de uma state machine do AWS Step Functions.

Le a definicao em Amazon States Language (ASL) ja em disco -- o `.asl.json`
versionado no repositorio (qualquer `.json` com `StartAt` e `States`) ou a saida
salva de `aws stepfunctions describe-state-machine` (objeto com `definition` como
STRING JSON e `type`). Como `controlm_jobs.py`, NAO coleta nada e NUNCA levanta
excecao por payload malformado: o que nao consegue ler vira `sfn.unresolved` com
`attrs.reason`, e a sentinela `sfn.analyzed` sai sempre, uma por arquivo.

## Por que `sfn.`

E o nome curto que a propria AWS usa para o servico (ARN `arn:aws:states`, CLI
`aws stepfunctions`), e nenhum kind existente comeca com ele (D1 de
`docs/sdd/STEP_FUNCTIONS/design.md`).

## O que sai

- `sfn.state_machine` -- um por definicao lida. `attrs.type` e `STANDARD`,
  `EXPRESS` ou `undeclared`: um `.asl.json` nao carrega o tipo, que so vem na saida
  de `describe-state-machine`. Sem ela o tipo e `undeclared`, NUNCA `STANDARD` por
  suposicao.
- `sfn.task` -- um por estado `Task`, inclusive dentro de `Parallel.Branches[]` e de
  `Map.ItemProcessor` (e do legado `Map.Iterator`). O `subject.symbol` e o CAMINHO do
  estado na definicao (`States/Cargas/Branches/0/States/Carga`): dois estados de
  mesmo nome em ramos diferentes sao duas entidades para `same_subject`. O tipo da
  state machine viaja em `attrs.state_machine_type` porque o motor avalia um fact
  por condicao (regra 33).
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`, `invalid_json`,
  `not_a_state_machine`, `definition_not_string`, `state_not_an_object`,
  `resource_absent` e `resource_dynamic`.
- `sfn.analyzed` -- a sentinela, com as contagens.

## Os defaults publicados moram AQUI, com a fonte ao lado

A regra nao sabe o default, e `rules/expr.py` nao tem funcao. O fact grava o valor
EFETIVO e a marca de que ele foi omitido (D2):

- `MaxAttempts` "(3 by default)" -- concepts-error-handling;
- `TimeoutSeconds` "The default value is 99,999,999" -- state-task.

## Qual retrier pega a falha do job

`States.TaskFailed` "matches any known error name except for States.Timeout", e
`States.ALL` casa tudo menos `States.Runtime` (concepts-error-handling). A leitura
adotada aqui: a falha do JobRun sob `.sync` e casada pelo PRIMEIRO retrier, na ordem
declarada, cujo `ErrorEquals` contem um dos dois; retrier so de erro nomeado
(`Glue.ConcurrentRunsExceededException`) nao casa a falha do job. O efetivo dele
sai em `measures.failure_retry_max_attempts`; sem retrier que case, `0`.

## JobName

Literal quando `JobName` e string sem `{% %}`; dinamico quando a chave e `JobName.$`
(JSONPath) ou o valor e expressao JSONata. So o literal liga o estado ao
`aws_glue_job` de mesmo nome.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "stepfunctions@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sfn.state_machine",
        "sfn.task",
        "sfn.unresolved",
        "sfn.analyzed",
    }
)

# https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
# MaxAttempts: "(3 by default)".
DEFAULT_MAX_ATTEMPTS = 3
# https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
# TimeoutSeconds: "The default value is 99,999,999".
DEFAULT_TIMEOUT_SECONDS = 99_999_999

_FAILURE_ERRORS = frozenset({"States.ALL", "States.TaskFailed"})
_DECLARED_TYPES = frozenset({"STANDARD", "EXPRESS"})
_UNDECLARED = "undeclared"


@dataclass
class _Leitura:
    """O estado de UMA definicao sendo lida: onde, com que tipo, e o que ja saiu."""

    path: str
    machine_type: str
    query_language: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)
    state_count: int = 0


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _state_subject(path: str, state_path: str) -> dict[str, Any]:
    subject = _file_subject(path)
    subject["symbol"] = state_path
    return subject


def _provenance(path: str, sha: str) -> dict[str, Any]:
    return {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="sfn.unresolved",
        subject=subject,
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _is_jsonata(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    texto = value.strip()
    return texto.startswith("{%") and texto.endswith("%}")


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _target(service: str, api: str, pattern: str, integration: str) -> dict[str, str]:
    return {"service": service, "api": api, "pattern": pattern, "integration": integration}


def _parse_resource(resource: str) -> dict[str, str]:
    """Servico, API, padrao e forma de integracao, lidos do ARN do `Resource`.

    `arn:aws:states:::glue:startJobRun.sync` -> glue, startJobRun, sync, optimized. O
    sufixo decide o padrao: `.sync` (inclusive `.sync:2`) e `sync`,
    `.waitForTaskToken` e `callback`, sem sufixo e `request_response`.
    """
    partes = resource.split(":")
    if len(partes) < 6 or partes[0] != "arn":
        return _target("", "", "request_response", "other")
    if partes[2] == "lambda":
        return _target("lambda", "invoke", "request_response", "function_arn")
    if partes[2] != "states":
        return _target(partes[2], "", "request_response", "other")
    cauda = partes[5:]
    integracao = "optimized"
    if cauda and cauda[0] == "aws-sdk":
        integracao = "sdk"
        cauda = cauda[1:]
    if cauda and cauda[0] == "activity":
        return _target("activity", "", "activity", "activity")
    if len(cauda) < 2:
        return _target(cauda[0] if cauda else "", "", "request_response", "other")
    chamada = ":".join(cauda[1:])
    if ".waitForTaskToken" in chamada:
        padrao = "callback"
    elif ".sync" in chamada:
        padrao = "sync"
    else:
        padrao = "request_response"
    return _target(cauda[0], chamada.split(".", 1)[0], padrao, integracao)


def _job_name(state: dict[str, Any]) -> tuple[str | None, str]:
    """(nome literal, origem): `literal`, `jsonpath`, `jsonata`, `unreadable` ou `absent`."""
    for bloco in ("Arguments", "Parameters"):
        argumentos = state.get(bloco)
        if _is_jsonata(argumentos):
            return None, "jsonata"
        if not isinstance(argumentos, dict):
            continue
        if "JobName.$" in argumentos:
            return None, "jsonpath"
        if "JobName" not in argumentos:
            continue
        valor = argumentos["JobName"]
        if _is_jsonata(valor):
            return None, "jsonata"
        if isinstance(valor, str) and valor.strip():
            return valor, "literal"
        return None, "unreadable"
    return None, "absent"


def _job_attrs(state: dict[str, Any], service: str) -> dict[str, Any]:
    if service != "glue":
        return {"job_name": None, "job_name_dynamic": False, "job_name_source": "not_applicable"}
    nome, origem = _job_name(state)
    return {"job_name": nome, "job_name_dynamic": origem != "literal", "job_name_source": origem}


def _retriers(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Cada retrier com o `MaxAttempts` EFETIVO e a marca de omitido (D2)."""
    bruto = state.get("Retry")
    saida: list[dict[str, Any]] = []
    for retrier in bruto if isinstance(bruto, list) else []:
        if not isinstance(retrier, dict):
            continue
        erros = retrier.get("ErrorEquals")
        nomes = [e for e in erros if isinstance(e, str)] if isinstance(erros, list) else []
        if "MaxAttempts" not in retrier:
            efetivo, omitido = DEFAULT_MAX_ATTEMPTS, True
        else:
            valor = retrier["MaxAttempts"]
            efetivo, omitido = (valor if _is_count(valor) else None), False
        saida.append(
            {"error_equals": nomes, "max_attempts": efetivo, "max_attempts_defaulted": omitido}
        )
    return saida


def _failure_retrier(retriers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """O PRIMEIRO retrier, na ordem declarada, que casa a falha do job."""
    for retrier in retriers:
        if _FAILURE_ERRORS & set(retrier["error_equals"]):
            return retrier
    return None


def _timeout(state: dict[str, Any]) -> tuple[bool, bool, int | None]:
    """(declarado, dinamico, segundos efetivos). `TimeoutSecondsPath` e dinamico."""
    if "TimeoutSecondsPath" in state:
        return True, True, None
    if "TimeoutSeconds" not in state:
        return False, False, DEFAULT_TIMEOUT_SECONDS
    valor = state["TimeoutSeconds"]
    if _is_count(valor) and valor > 0:
        return True, False, valor
    return True, True, None


def _task_fact(state: dict[str, Any], name: str, state_path: str, leitura: _Leitura) -> Fact:
    recurso = state["Resource"]
    alvo = _parse_resource(recurso)
    retriers = _retriers(state)
    falha = _failure_retrier(retriers)
    declarado, dinamico, segundos = _timeout(state)
    linguagem = state.get("QueryLanguage")
    attrs: dict[str, Any] = {
        "state_name": name,
        "resource": recurso,
        **alvo,
        **_job_attrs(state, alvo["service"]),
        "retriers": retriers,
        "failure_retry_matched": falha is not None,
        "failure_retry_defaulted": falha is not None and falha["max_attempts_defaulted"],
        "has_catch": bool(state.get("Catch")),
        "has_next": isinstance(state.get("Next"), str),
        "end": state.get("End") is True,
        "timeout_declared": declarado,
        "timeout_dynamic": dinamico,
        "state_machine_type": leitura.machine_type,
        "query_language": linguagem if isinstance(linguagem, str) else leitura.query_language,
    }
    measures: dict[str, Any] = {"retrier_count": len(retriers)}
    if falha is None:
        measures["failure_retry_max_attempts"] = 0
    elif falha["max_attempts"] is not None:
        measures["failure_retry_max_attempts"] = falha["max_attempts"]
    if segundos is not None:
        measures["timeout_seconds"] = segundos
    return Fact(
        kind="sfn.task",
        subject=_state_subject(leitura.path, state_path),
        measures=measures,
        attrs=attrs,
        provenance=leitura.provenance,
    )


def _walk(states: dict[str, Any], base: str, leitura: _Leitura) -> None:
    """Percorre `States`, descendo em `Parallel.Branches[]` e `Map.ItemProcessor`/`Iterator`."""
    for nome, corpo in states.items():
        state_path = f"{base}/States/{nome}" if base else f"States/{nome}"
        leitura.state_count += 1
        subject = _state_subject(leitura.path, state_path)
        if not isinstance(corpo, dict):
            leitura.facts.append(_unresolved(subject, "state_not_an_object", leitura.provenance))
            continue
        tipo = corpo.get("Type")
        if tipo == "Task":
            recurso = corpo.get("Resource")
            if recurso is None:
                leitura.facts.append(_unresolved(subject, "resource_absent", leitura.provenance))
            elif not isinstance(recurso, str) or not recurso.strip() or _is_jsonata(recurso):
                leitura.facts.append(_unresolved(subject, "resource_dynamic", leitura.provenance))
            else:
                leitura.facts.append(_task_fact(corpo, str(nome), state_path, leitura))
        elif tipo == "Parallel":
            ramos = corpo.get("Branches")
            for indice, ramo in enumerate(ramos if isinstance(ramos, list) else []):
                if isinstance(ramo, dict) and isinstance(ramo.get("States"), dict):
                    _walk(ramo["States"], f"{state_path}/Branches/{indice}", leitura)
        elif tipo == "Map":
            for chave in ("ItemProcessor", "Iterator"):
                processador = corpo.get(chave)
                if isinstance(processador, dict) and isinstance(processador.get("States"), dict):
                    _walk(processador["States"], f"{state_path}/{chave}", leitura)


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="sfn.analyzed",
            subject=_file_subject(path),
            measures={
                "state_machine_count": sum(1 for f in facts if f.kind == "sfn.state_machine"),
                "task_count": sum(1 for f in facts if f.kind == "sfn.task"),
                "unresolved_count": sum(1 for f in facts if f.kind == "sfn.unresolved"),
            },
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def extract_stepfunctions(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado: ASL, ou a saida de `describe-state-machine`."""
    provenance = _provenance(path, artifact_sha256)
    if not isinstance(payload, dict):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([falha], path, provenance)
    origem, tipo, nome, definicao = "asl", _UNDECLARED, None, payload
    if "definition" in payload:
        origem = "describe_state_machine"
        bruto = payload["definition"]
        if not isinstance(bruto, str):
            falha = _unresolved(_file_subject(path), "definition_not_string", provenance)
            return _finish([falha], path, provenance)
        try:
            definicao = json.loads(bruto)
        except json.JSONDecodeError:
            falha = _unresolved(_file_subject(path), "invalid_json", provenance, at="definition")
            return _finish([falha], path, provenance)
        declarado = payload.get("type")
        if isinstance(declarado, str) and declarado in _DECLARED_TYPES:
            tipo = declarado
        if isinstance(payload.get("name"), str):
            nome = payload["name"]
    if not (
        isinstance(definicao, dict)
        and isinstance(definicao.get("StartAt"), str)
        and isinstance(definicao.get("States"), dict)
    ):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([falha], path, provenance)
    linguagem = definicao.get("QueryLanguage")
    leitura = _Leitura(
        path=path,
        machine_type=tipo,
        query_language=linguagem if isinstance(linguagem, str) else "JSONPath",
        provenance=provenance,
    )
    _walk(definicao["States"], "", leitura)
    attrs: dict[str, Any] = {
        "type": tipo,
        "type_declared": tipo != _UNDECLARED,
        "query_language": leitura.query_language,
        "source": origem,
    }
    if nome is not None:
        attrs["name"] = nome
    leitura.facts.append(
        Fact(
            kind="sfn.state_machine",
            subject=_file_subject(path),
            measures={
                "state_count": leitura.state_count,
                "task_count": sum(1 for f in leitura.facts if f.kind == "sfn.task"),
            },
            attrs=attrs,
            provenance=provenance,
        )
    )
    return _finish(leitura.facts, path, provenance)


def extract_stepfunctions_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `sfn.unresolved` com `read_error`; JSON invalido,
    `invalid_json`. Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = _provenance(anchor, sha)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        falha = _unresolved(_file_subject(anchor), "invalid_json", provenance)
        return _finish([falha], anchor, provenance)
    return extract_stepfunctions(parsed, anchor, artifact_sha256=sha)


def extract_stepfunctions_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: vira `sfn.unresolved` daquele arquivo e a
    travessia continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.json"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_stepfunctions_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_TIMEOUT_SECONDS",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_stepfunctions",
    "extract_stepfunctions_path",
    "extract_stepfunctions_tree",
]
```

Sem função aninhada (duas `def` de mesmo nome no mesmo escopo quebram
`tests/test_codeintel_security.py::TestInv001`), sem `Path.glob`/`rglob` (é
`tests/test_facts_scan.py`), sem API de Python 3.11+ (o CI roda 3.10).

### 4. Rodar e ver passar

```bash
git add sparkforge/facts/stepfunctions.py
python -m pytest tests/test_stepfunctions.py -q
```

Três testes verdes.

### 5. Gates vizinhos

Extrator (`docs/gates-por-mudanca.md`, "Acrescentar ou alterar um EXTRATOR de facts") —
o módulo ainda NÃO entra nas duas listas manuais: entra em T3, no mesmo commit do golden.

```bash
python -m ruff check sparkforge/facts/stepfunctions.py tests/test_stepfunctions.py
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_facts_scan.py tests/test_harness_untrusted.py tests/test_databricks_rule_audit.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py -q
```

`test_harness_untrusted.py` roda `extract_stepfunctions_tree` sobre todo domínio de
`fixtures/` (a medida de snippet): o módulo tem `*_tree`, então é exercitado sem entrada
em `_derivados_de_facts`, e nenhum fact dele carrega `snippet`.

Números (tabela *Números correntes* e prosa auditada):

- `docs/superpowers/STATUS.md`, duas trocas de prefixo de linha (o resto de cada linha
  fica como está). Antes → depois:

```text
| Extratores de facts | **38** —
| Extratores de facts | **39** — `stepfunctions.py` é o trigésimo nono (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`): o primeiro que lê quem DISPARA o job Glue, a definição ASL do AWS Step Functions. Leitura anterior de **38** —
```

```text
| Fact kinds distintos emitidos | **228** —
| Fact kinds distintos emitidos | **232** — os quatro `sfn.*` do extrator de ASL (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`): `sfn.state_machine`, `sfn.task`, `sfn.unresolved` e `sfn.analyzed`. Leitura anterior de **228** —
```

- `README.md` linha 45: `Os 38 extratores emitem 228 kinds distintos` →
  `Os 39 extratores emitem 232 kinds distintos`.
- `docs/guia/06-extrair-julgar-compor.md`: linha 86,
  `Os 38 extratores emitem 228 kinds distintos de fact (recontado em 2026-09-18),` →
  `Os 39 extratores emitem 232 kinds distintos de fact (recontado em 2026-09-19),`; linha
  231, `nenhum dos 228 kinds a nomeia` → `nenhum dos 232 kinds a nomeia`.

```bash
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

O gate de lastro reprova as alegações de corpus de `.py` (dois arquivos novos; medido em
entregas anteriores: `VNX-640`, `VNX-644`, `VNX-667`, `VNX-670`, `VNX-674` em
`docs/harness/CODEINTEL-GAP.md`). Remedie pelos ids que a saída listar, número no
documento e em `docs/claims.lock.json`, e rode o gate de novo até `exit 0`.

### 6. Commit

`feat(facts): read AWS Step Functions ASL definitions into sfn.* facts`

Arquivos: `sparkforge/facts/stepfunctions.py`, `tests/test_stepfunctions.py`,
`docs/superpowers/STATUS.md`, `README.md`, `docs/guia/06-extrair-julgar-compor.md`,
`docs/harness/CODEINTEL-GAP.md`, `docs/claims.lock.json`.

## T2 — verbo `analyze step-functions` e tool `sparkforge_analyze_step_functions`

### 1. Teste que falha

Acrescente ao fim de `tests/test_stepfunctions.py`:

```python
def test_cli_e_tool_devolvem_os_mesmos_facts(tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    entrada = tmp_path / "entrada"
    entrada.mkdir()
    (entrada / "sm.asl.json").write_text(json.dumps(ASL_COM_PARALLEL_E_MAP), encoding="utf-8")
    saida = tmp_path / "facts.json"

    codigo = main(["analyze", "step-functions", "--path", str(entrada), "--out", str(saida)])
    capsys.readouterr()
    assert codigo == 0
    pela_cli = json.loads(saida.read_text(encoding="utf-8"))

    pela_tool = call_tool(
        "sparkforge_analyze_step_functions", {"path": str(entrada), "limit": 1000}
    )
    assert "error" not in pela_tool, pela_tool
    assert pela_tool["total_count"] == len(pela_cli)
    assert pela_tool["items"] == pela_cli
    assert pela_tool["by_kind"]["sfn.task"] == 3
    assert pela_tool["unresolved"] == 0

    erro = call_tool("sparkforge_analyze_step_functions", {"path": str(tmp_path / "nao-existe")})
    assert "sparkforge analyze step-functions" in erro["error"]
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_stepfunctions.py::test_cli_e_tool_devolvem_os_mesmos_facts -q
```

Falha esperada: `SystemExit: 2` do argparse (`invalid choice: 'step-functions'`).

### 3. Código mínimo

**`sparkforge/adapters/_core.py`** — import. Troque

```python
from sparkforge.facts.sql_metrics import extract_sql_metrics_path
from sparkforge.facts.terraform import (
```

por

```python
from sparkforge.facts.sql_metrics import extract_sql_metrics_path
from sparkforge.facts.stepfunctions import (
    extract_stepfunctions_path,
    extract_stepfunctions_tree,
)
from sparkforge.facts.terraform import (
```

E a função pública, logo antes da seção de benchmark. Troque

```python
    facts = _extract_controlm_jobs_facts(path, version)
    return _facts_page(facts, "ctm.unresolved", kind, limit, cursor, detail_level)
```

por

```python
    facts = _extract_controlm_jobs_facts(path, version)
    return _facts_page(facts, "ctm.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze step-functions
# --------------------------------------------------------------------------- #
#
# Le a DEFINICAO da state machine -- o `.asl.json` do repositorio ou a saida salva
# de `aws stepfunctions describe-state-machine` -- e nunca o historico de execucao.
# Nao ha `collect` par (D3 de `docs/sdd/STEP_FUNCTIONS/design.md`): o
# `describe-state-machine` exige credencial, e o operador cola a saida em arquivo.


def _extract_step_functions_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o .asl.json da state machine, para a saida salva de\n"
            f"  `aws stepfunctions describe-state-machine`, ou para o diretorio com eles:\n"
            f"    sparkforge analyze step-functions --path statemachines/ "
            f"--out .sparkforge/facts_sfn.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_stepfunctions_tree(target, repo_root=target)
    return extract_stepfunctions_path(target, repo_root=target.parent)


def analyze_step_functions(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_step_functions_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)
```

**`sparkforge/adapters/cli.py`** — subcomando. Troque

```python
    _add_detail_level(ctm_analyze_p)

    dq_p = analyze_sub.add_parser(
```

por

```python
    _add_detail_level(ctm_analyze_p)

    sfn_analyze_p = analyze_sub.add_parser(
        "step-functions",
        help="Extrai facts da definicao ASL de uma state machine do AWS Step Functions "
        "(`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um "
        "fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e "
        "TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao.",
    )
    sfn_analyze_p.add_argument(
        "--path",
        required=True,
        help="Arquivo .json (ASL ou describe-state-machine) ou diretorio com eles.",
    )
    sfn_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    sfn_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sfn_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sfn_analyze_p.add_argument("--cursor")
    _add_detail_level(sfn_analyze_p)

    dq_p = analyze_sub.add_parser(
```

Handler: troque

```python
def _cmd_analyze_controlm_jobs(args: argparse.Namespace) -> int:
```

por

```python
def _cmd_analyze_step_functions(args: argparse.Namespace) -> int:
    full = _core.analyze_step_functions(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_controlm_jobs(args: argparse.Namespace) -> int:
```

Despacho: troque

```python
    ("analyze", "controlm-jobs"): _cmd_analyze_controlm_jobs,
```

por

```python
    ("analyze", "controlm-jobs"): _cmd_analyze_controlm_jobs,
    ("analyze", "step-functions"): _cmd_analyze_step_functions,
```

**`sparkforge/adapters/tools.py`** — declaração. Troque

```python
    "sparkforge_analyze_data_quality": {
        "description": (
```

por

```python
    "sparkforge_analyze_step_functions": {
        "description": (
            "Extrai facts da definicao de uma state machine do AWS Step Functions em "
            "Amazon States Language (ASL): o `.asl.json` versionado no repositorio, ou a "
            "saida salva de `aws stepfunctions describe-state-machine` (objeto com "
            "`definition` como string JSON e `type`). Emite `sfn.state_machine` (tipo "
            "STANDARD, EXPRESS ou `undeclared` -- um `.asl.json` nao carrega o tipo, e ele "
            "NUNCA e suposto STANDARD), um `sfn.task` por estado Task, inclusive dentro de "
            "Parallel e Map (servico, API, padrao `request_response`/`sync`/`callback`, "
            "JobName literal ou a marca de dinamico, retriers com o `MaxAttempts` EFETIVO -- "
            "3 quando omitido, com a marca de omitido --, `Catch` e `TimeoutSeconds`), "
            "`sfn.unresolved` com a razao do que nao deu para ler, e a sentinela "
            "`sfn.analyzed`. NAO chama a API do Step Functions e NAO le historico de "
            "execucao: le a DEFINICAO."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Arquivo .json (ASL ou describe-state-machine) ou diretorio com eles."
                    ),
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {
                    "type": "string",
                    "enum": list(_core.NIVEIS_DE_DETALHE),
                    "description": _DETAIL_LEVEL_DESC,
                },
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_data_quality": {
        "description": (
```

Handler: troque

```python
def _h_analyze_data_quality(args: dict[str, Any]) -> dict[str, Any]:
```

por

```python
def _h_analyze_step_functions(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_step_functions(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )


def _h_analyze_data_quality(args: dict[str, Any]) -> dict[str, Any]:
```

Despacho: troque

```python
    "sparkforge_analyze_controlm_jobs": _h_analyze_controlm_jobs,
```

por

```python
    "sparkforge_analyze_controlm_jobs": _h_analyze_controlm_jobs,
    "sparkforge_analyze_step_functions": _h_analyze_step_functions,
```

**Registros da superfície, no mesmo commit:**

`tests/test_adapters_tools.py`:

- lista literal de `TestToolSurface`: troque

```python
            "sparkforge_analyze_controlm_jobs",
            "sparkforge_analyze_data_quality",
```

por

```python
            "sparkforge_analyze_controlm_jobs",
            "sparkforge_analyze_step_functions",
            "sparkforge_analyze_data_quality",
```

- amostra real: troque `_CONSUMER_INVENTORY = """consumers:` por

```python
# Definicao ASL com um Glue `.sync` e retry implicito: rende `sfn.task` com os campos
# que as regras SF-SFN leem, e nao so a sentinela que sai de qualquer `.json`.
_STEP_FUNCTIONS_ASL = json.dumps(
    {
        "StartAt": "RodarCarga",
        "States": {
            "RodarCarga": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Parameters": {"JobName": "carga-diaria"},
                "Retry": [{"ErrorEquals": ["States.ALL"]}],
                "End": True,
            }
        },
    }
)

_CONSUMER_INVENTORY = """consumers:
```

- construtor de `_real_output_for`: troque `    if name == "sparkforge_analyze_data_quality":` por

```python
    if name == "sparkforge_analyze_step_functions":
        sfn_path = tmp_path / "carga.asl.json"
        sfn_path.write_text(_STEP_FUNCTIONS_ASL, encoding="utf-8")
        resultado = call_tool("sparkforge_analyze_step_functions", {"path": str(sfn_path)})
        assert resultado["by_kind"].get("sfn.task") == 1, resultado["by_kind"]
        return resultado

    if name == "sparkforge_analyze_data_quality":
```

- `FAILABLE`: troque

```python
        ("sparkforge_analyze_controlm_jobs", {"path": "<tmp>/inexistente"}),
```

por

```python
        ("sparkforge_analyze_controlm_jobs", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_step_functions", {"path": "<tmp>/inexistente"}),
```

`tests/test_harness_authorization.py`: troque

```python
        # `_WRITE_IDEMPOTENT`. O conjunto de excecao nao se move.
        assert len(TOOLS) - len(sem_caminho) == 98
```

por

```python
        # `_WRITE_IDEMPOTENT`. O conjunto de excecao nao se move.
        # 98 -> 99 com `analyze_step_functions` (2026-09-19, `docs/sdd/STEP_FUNCTIONS/`):
        # `_READ_ONLY`, le a definicao ASL em disco e declara `path`.
        assert len(TOOLS) - len(sem_caminho) == 99
```

`parity.yaml`: logo depois do bloco `- name: extract facts from a Control-M Jobs-as-Code
definition` (termina em `copilot_ci: [cli, files]`, antes de `- name: diff component
versions between two runtime releases`), acrescente:

```yaml
  # A definicao ASL do AWS Step Functions e codigo-fonte, como o `Jobs-as-Code` da
  # capacidade acima: o `.asl.json` do repositorio, ou a saida salva de
  # `describe-state-machine`. NAO HA `collect` PAR neste incremento, e a ausencia e
  # decidida (D3 de `docs/sdd/STEP_FUNCTIONS/design.md`): a chamada exige credencial.
  - name: extract facts from an AWS Step Functions state machine definition
    tools: [sparkforge_analyze_step_functions]
    cli: [analyze step-functions]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]

```

`manifest.json`: troque

```json
    "sparkforge_analyze_sql_metrics",
```

por

```json
    "sparkforge_analyze_sql_metrics",
    "sparkforge_analyze_step_functions",
```

`agents/glue-infra-reviewer.md` (senão `test_no_tool_is_orphan` reprova): troque

```markdown
## Três armadilhas que a infraestrutura esconde
```

por

```markdown
## Quem dispara o job: Step Functions

A definição do job não diz quem o chama nem quantas vezes. Quando o job roda sob uma
state machine do AWS Step Functions, `sparkforge_analyze_step_functions` lê a definição
ASL — o `.asl.json` do repositório, ou a saída salva de `aws stepfunctions
describe-state-machine` — e devolve um `sfn.task` por estado `Task`: o padrão de
integração (`request_response`, `sync`, `callback`), o `JobName` literal ou a marca de
dinâmico, os retriers com o `MaxAttempts` efetivo (3 quando omitido, e a marca de
omitido), o `Catch` e o `TimeoutSeconds`. Um `.asl.json` não carrega o tipo do workflow:
sem a saída de `describe-state-machine`, o tipo sai `undeclared`, nunca `STANDARD`.

## Três armadilhas que a infraestrutura esconde
```

Espelhos: backup do README, `python scripts/sync_skills.py`, devolva o README. E à mão,
`.codex/agents/glue-infra-reviewer.toml`: a mesma seção, no mesmo lugar do
`developer_instructions` (antes da linha `## Três armadilhas que a infraestrutura
esconde`).

`docs/guia/06-extrair-julgar-compor.md`, tabela de verbos: troque a linha que começa
com `| **Definição `Jobs-as-Code` do Control-M** | `analyze controlm-jobs` |` por ela
mesma seguida desta linha nova:

```markdown
| **Definição ASL do AWS Step Functions** | `analyze step-functions` | o `.asl.json` versionado no repositório, ou a saída salva de `aws stepfunctions describe-state-machine`: um fact por estado Task, com padrão de integração, `JobName` e retry efetivo. Com o Terraform do job no mesmo pool, `fuse` liga o Task ao `aws_glue_job` |
```

`tests/test_fixtures_golden_mcp_parity.py`: o SDK `mcp`
2.2.0 está instalado nesta máquina, então `test_toda_tool_nova_esta_declarada` roda. Troque

```python
    "sparkforge_sdd_stamp": "2026-09-16: hash do upstream de um artefato SDD",
}
```

por

```python
    "sparkforge_sdd_stamp": "2026-09-16: hash do upstream de um artefato SDD",
    "sparkforge_analyze_step_functions": "2026-09-19: definicao ASL do AWS Step Functions",
}
```

Referência e superfície:

```bash
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
```

O primeiro reescreve `docs/guia/referencia/tools/README.md`, cria
`docs/guia/referencia/tools/sparkforge_analyze_step_functions.md`, e reescreve também
`docs/guia/referencia/cli/analyze.md` e `docs/guia/referencia/agents/glue-infra-reviewer.md`
(estes dois não estão no manifesto: ver "Dúvidas" no fim).
O segundo imprime o crescimento em bytes: copie-o para o corpo do commit (regra 26).

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_stepfunctions.py -q
python -m pytest tests/test_adapters_tools.py -q
```

### 5. Gates vizinhos

"Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada" e
"Alterar agent, skill ou seus espelhos":

```bash
python -m pytest tests/test_reference_docs.py tests/test_surface_lock.py -q
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q
python -m pytest tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_adapters_code_surface.py tests/test_mcp_modern_era.py -q
python -m pytest tests/test_fixtures_golden_mcp_parity.py -q
python -m ruff check sparkforge/adapters tests/test_stepfunctions.py tests/test_adapters_tools.py tests/test_harness_authorization.py
```

(backup e devolução do `.claude/agents/README.md` em volta de `test_agents_parity.py`.)

Números. `docs/superpowers/STATUS.md`, antes → depois:

```text
| Tools MCP | **106** —
| Tools MCP | **107** — a **107ª** é `sparkforge_analyze_step_functions` (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`): lê a definição ASL do AWS Step Functions, é `_READ_ONLY` e declara `path`. Leitura anterior de **106** —
```

`README.md` linha 111: `**106 tools MCP**` → `**107 tools MCP**`.

Prosa que `check_status_numbers.py` audita:

- `GUIA_DE_USO.md` linha 237: `as 106 tools fazem (recontado em 2026-09-16)` →
  `as 107 tools fazem (recontado em 2026-09-19)`;
- `.devin/README.md` linha 31: `**106 tools** por stdio (recontado em 2026-09-16)` →
  `**107 tools** por stdio (recontado em 2026-09-19)`;
- `AGENTS.md` linha 143: `**106 tools, 38 with `detail_level`** (recounted 2026-09-16)`
  → `**107 tools, 39 with `detail_level`** (recounted 2026-09-19)`;
- `CLAUDE.md` linha 144: `**106 tools, 38 com `detail_level`** (recontado em 2026-09-16)`
  → `**107 tools, 39 com `detail_level`** (recontado em 2026-09-19)`. A tool nova aceita
  `detail_level`, e a medida é por assinatura (`_tools_com_detail_level`).

```bash
python scripts/check_status_numbers.py --strict
python -m pytest tests/test_status_numbers_gate.py tests/test_bootstrap_budget.py -q
python scripts/check_vnext_claims.py
```

`len(TOOLS)` move alegações de `docs/harness/`: lidas nesta
branch, `AUTHORIZATION-CHAIN.md` (linhas 80, 196, 278, 324: 106 tools, 98 de 106),
`CURRENT-HARNESS-GAP.md` (linhas 42 e 107) e `CODEINTEL-GAP.md` (linha 305, `detail_level`
em 40 das 106). Remedie pelos ids da saída do gate — número no documento e no
`docs/claims.lock.json` — até `exit 0`.

### 6. Commit

`feat(cli,mcp): add the analyze step-functions verb and its MCP tool`, com o crescimento
da superfície em bytes no corpo.

## T3 — a área `SF-SFN`: quatro regras, a derivação em `fuse`, a rota, o corpus e o golden

### 1. Testes que falham, e o corpus

**1a.** Acrescente ao fim de `tests/test_stepfunctions.py`:

```python
TF_CARGA_DIARIA = """resource "aws_glue_job" "carga_diaria" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = 2
}
"""

RUNTIME_GLUE = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def _glue_sync(nome_do_job: dict, retry: list, proximo: dict) -> dict:
    return {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": nome_do_job,
        "Retry": retry,
        **proximo,
    }


def test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga(tmp_path):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.terraform import extract_terraform_tree
    from sparkforge.rules.engine import judge
    from sparkforge.rules.loader import load_catalog

    asl = {
        "StartAt": "Ligada",
        "States": {
            "Ligada": _glue_sync(
                {"JobName": "carga-diaria"},
                [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}],
                {"Next": "Dinamica"},
            ),
            "Dinamica": _glue_sync(
                {"JobName.$": "$.job"},
                [{"ErrorEquals": ["States.ALL"]}],
                {"Next": "SemDefinicao"},
            ),
            "SemDefinicao": _glue_sync(
                {"JobName": "job-que-nao-esta-no-terraform"},
                [{"ErrorEquals": ["States.ALL"]}],
                {"End": True},
            ),
        },
    }
    (tmp_path / "sm.asl.json").write_text(json.dumps(asl), encoding="utf-8")
    (tmp_path / "main.tf").write_text(TF_CARGA_DIARIA, encoding="utf-8")
    so_asl = extract_stepfunctions_tree(tmp_path, repo_root=tmp_path)
    so_tf = extract_terraform_tree(tmp_path, repo_root=tmp_path)

    fundidos = fuse(so_asl + so_tf)

    [link] = [f for f in fundidos if f.kind == "sfn.glue_job_link"]
    assert link.subject["symbol"] == "States/Ligada"
    assert link.attrs["resource"] == "aws_glue_job.carga_diaria"
    assert link.attrs["job_name"] == "carga-diaria"
    assert link.attrs["glue_max_retries_source"] == "literal"
    assert link.measures == {"sfn_retry_effective": 2, "glue_max_retries": 2}
    motivos = {
        f.subject["symbol"]: f.attrs["reason"] for f in fundidos if f.kind == "sfn.unresolved"
    }
    assert motivos == {
        "States/Dinamica": "job_name_dynamic",
        "States/SemDefinicao": "job_definition_absent",
    }

    achados = judge(fundidos, load_catalog(), RUNTIME_GLUE)
    quatro = [a.subject["symbol"] for a in achados if a.rule_id == "SF-SFN-004"]
    assert quatro == ["States/Ligada"]

    # fuse sem Terraform no pool nao inventa vinculo
    assert not [f for f in fuse(so_asl) if f.kind == "sfn.glue_job_link"]
    # e pool sem Step Functions sai do fuse sem nenhum sfn.*
    assert not [f for f in fuse(so_tf) if f.kind.startswith("sfn.")]
```

**1b.** `tests/test_fixtures_golden_stepfunctions.py` (arquivo novo, com a linha LITERAL
que `test_fixtures_kind_coverage.py` casa por regex):

```python
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
```

**1c.** O corpus `fixtures/stepfunctions/<caso>/{meta.yaml,input/}`. Todas as fixtures
usam o mesmo `runtime`. Ele é inerte para as `SF-SFN` (`runtime_scope: {}`), e existe
porque o `judge` exige um e porque o `aws_glue_job` das fixtures pareadas declara
`glue_version = "5.0"`:

```yaml
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
```

`fixtures/stepfunctions/glue_sem_sync/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: Glue disparado sem .sync e seguido de um estado que depende dele.",
  "QueryLanguage": "JSONata",
  "StartAt": "IniciarCarga",
  "States": {
    "IniciarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun",
      "Arguments": {"JobName": "carga-diaria"},
      "Next": "PublicarResultado"
    },
    "PublicarResultado": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Arguments": {"FunctionName": "publicar-resultado"},
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/glue_sem_sync/meta.yaml`:

```yaml
name: glue_sem_sync
proves: >
  O POSITIVO de SF-SFN-001. `glue:startJobRun` sem `.sync` e com `Next`: o estado
  termina quando o Glue aceita o pedido, e `PublicarResultado` roda com o job ainda em
  execucao. O Task do Lambda e registrado e nao julgado -- as regras julgam so o Glue.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.state_machine, sfn.task]
expects_rules: [SF-SFN-001]
```

`fixtures/stepfunctions/glue_retry_implicito/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: .sync com retrier em States.ALL e MaxAttempts omitido.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 60, "BackoffRate": 2.0}],
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/glue_retry_implicito/meta.yaml`:

```yaml
name: glue_retry_implicito
proves: >
  O ramo P1 de SF-SFN-002. O retrier casa a falha do job (`States.ALL`) e nao declara
  `MaxAttempts`: o efetivo e o default publicado, 3, e ninguem escolheu as tres
  execucoes a mais do job inteiro.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.state_machine, sfn.task]
expects_rules: [SF-SFN-002]
```

`fixtures/stepfunctions/glue_retry_explicito/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: .sync com retrier em States.TaskFailed e MaxAttempts declarado.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 120, "MaxAttempts": 1}],
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "NotificarFalha"}],
      "End": true
    },
    "NotificarFalha": {"Type": "Fail", "Error": "CargaFalhou", "Cause": "O job Glue falhou."}
  }
}
```

`fixtures/stepfunctions/glue_retry_explicito/meta.yaml`:

```yaml
name: glue_retry_explicito
proves: >
  O ramo P2 de SF-SFN-002: `MaxAttempts` declarado (1) em `States.TaskFailed`. Alguem
  escolheu o numero, e o achado continua dizendo que cada tentativa e um JobRun inteiro.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.state_machine, sfn.task]
expects_rules: [SF-SFN-002]
```

`fixtures/stepfunctions/express_com_sync/input/describe-state-machine.json`:

```json
{
  "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:carga-expressa",
  "name": "carga-expressa",
  "status": "ACTIVE",
  "definition": "{\"Comment\":\"Fixture sintetica: Glue .sync sob workflow EXPRESS.\",\"StartAt\":\"RodarCarga\",\"States\":{\"RodarCarga\":{\"Type\":\"Task\",\"Resource\":\"arn:aws:states:::glue:startJobRun.sync\",\"Parameters\":{\"JobName\":\"carga-diaria\"},\"End\":true}}}",
  "roleArn": "arn:aws:iam::123456789012:role/sfn-carga",
  "type": "EXPRESS",
  "creationDate": "2026-09-19T10:00:00.000000-03:00"
}
```

`fixtures/stepfunctions/express_com_sync/meta.yaml`:

```yaml
name: express_com_sync
proves: >
  O POSITIVO de SF-SFN-003, lido da saida de `describe-state-machine` (definition como
  string JSON). `type: EXPRESS` declarado e `.sync` no Task do Glue: "Express Workflows
  only support Request Response integrations." O NEGATIVO ja esta no corpus: todo
  `.asl.json` sai com tipo `undeclared` e nenhum dispara a regra.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.state_machine, sfn.task]
expects_rules: [SF-SFN-003]
```

`fixtures/stepfunctions/glue_limpo/input/cargas.asl.json`:

```json
{
  "Comment": "Fixture sintetica: .sync em paralelo, retry so de erro nomeado, Catch e um Map com Lambda.",
  "StartAt": "CargasParalelas",
  "States": {
    "CargasParalelas": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "CargaClientes",
          "States": {
            "CargaClientes": {
              "Type": "Task",
              "Resource": "arn:aws:states:::glue:startJobRun.sync",
              "Parameters": {"JobName": "carga-clientes"},
              "Retry": [{"ErrorEquals": ["Glue.ConcurrentRunsExceededException"], "IntervalSeconds": 30, "MaxAttempts": 2, "BackoffRate": 2.0}],
              "End": true
            }
          }
        },
        {
          "StartAt": "CargaPedidos",
          "States": {
            "CargaPedidos": {
              "Type": "Task",
              "Resource": "arn:aws:states:::glue:startJobRun.sync",
              "Parameters": {"JobName": "carga-pedidos"},
              "Retry": [
                {"ErrorEquals": ["Glue.ConcurrentRunsExceededException"], "IntervalSeconds": 30, "MaxAttempts": 2, "BackoffRate": 2.0},
                {"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 0}
              ],
              "End": true
            }
          }
        }
      ],
      "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "NotificarFalha"}],
      "Next": "ValidarLotes"
    },
    "ValidarLotes": {
      "Type": "Map",
      "ItemsPath": "$.lotes",
      "ItemProcessor": {
        "ProcessorConfig": {"Mode": "INLINE"},
        "StartAt": "ValidarLote",
        "States": {
          "ValidarLote": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {"FunctionName": "validar-lote", "Payload.$": "$"},
            "End": true
          }
        }
      },
      "End": true
    },
    "NotificarFalha": {"Type": "Fail", "Error": "CargaFalhou", "Cause": "Uma das cargas Glue falhou."}
  }
}
```

`fixtures/stepfunctions/glue_limpo/meta.yaml`:

```yaml
name: glue_limpo
proves: >
  O NEGATIVO da area. Dois Glue `.sync` dentro de um Parallel, cada um com retry so em
  erro nomeado (`Glue.ConcurrentRunsExceededException`), e o segundo com
  `States.TaskFailed` em `MaxAttempts: 0` -- a falha do job NAO e reexecutada. Esse
  zero e a fronteira que faz a troca `>` por `>=` na SF-SFN-002 mudar este golden.
  Sem achado nenhum; o Lambda dentro do Map e registrado e nao julgado.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.state_machine, sfn.task]
expects_rules: []
```

`fixtures/stepfunctions/definicao_ilegivel/input/quebrado.asl.json` (JSON invalido de
proposito, o arquivo inteiro):

```text
{"StartAt": "RodarCarga", "States": {"RodarCarga": {"Type": "Task",
```

`fixtures/stepfunctions/definicao_ilegivel/input/inventario.json`:

```json
{"jobs": ["carga-diaria", "carga-clientes"]}
```

`fixtures/stepfunctions/definicao_ilegivel/meta.yaml`:

```yaml
name: definicao_ilegivel
proves: >
  O ponto cego contado. Um arquivo que nao abre como JSON (`invalid_json`) e um JSON
  que nao e state machine (`not_a_state_machine`): os dois viram `sfn.unresolved`
  nomeado, com uma sentinela por arquivo, e nenhum achado.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.unresolved]
expects_rules: []
```

As quatro fixtures pareadas (ASL + `main.tf`) usam o mesmo Terraform, com o
`max_retries` que cada uma declara. `fixtures/stepfunctions/retry_duas_camadas/input/main.tf`:

```hcl
resource "aws_glue_job" "carga_diaria" {
  name              = "carga-diaria"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 2
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://bucket-exemplo/scripts/carga_diaria.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://bucket-exemplo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://bucket-exemplo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
```

(Medido nesta branch: esse `aws_glue_job` sozinho, julgado com o `runtime` acima, não
dispara regra nenhuma — o golden só pode mudar por causa do ASL.)

`fixtures/stepfunctions/retry_duas_camadas/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: o mesmo job com retry nas duas camadas.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 300, "MaxAttempts": 2, "BackoffRate": 1.0}],
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/retry_duas_camadas/meta.yaml`:

```yaml
name: retry_duas_camadas
proves: >
  O POSITIVO de SF-SFN-004. O Task liga ao `aws_glue_job.carga_diaria` pelo `JobName`
  literal igual ao `name`; o retrier do Step Functions tem efetivo 2 e o job declara
  `max_retries = 2`. As duas camadas existem sobre o mesmo job, e a composicao delas
  nao e documentada. SF-SFN-002 dispara junto, e deve: o retrier reexecuta o job.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.glue_job_link
  - sfn.state_machine
  - sfn.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: [SF-SFN-002, SF-SFN-004]
```

`fixtures/stepfunctions/job_name_dinamico/input/main.tf`:

```hcl
resource "aws_glue_job" "carga_diaria" {
  name              = "carga-diaria"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 2
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://bucket-exemplo/scripts/carga_diaria.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://bucket-exemplo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://bucket-exemplo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
```

`fixtures/stepfunctions/job_name_dinamico/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: JobName vem da entrada da execucao.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName.$": "$.job_name"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}],
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/job_name_dinamico/meta.yaml`:

```yaml
name: job_name_dinamico
proves: >
  O NEGATIVO de SF-SFN-004 por nome dinamico. O retrier tem efetivo 1 e o Terraform tem
  `max_retries = 2`, mas `JobName.$` nao e literal: nao ha vinculo, sai
  `sfn.unresolved` com `reason: job_name_dynamic`, e SF-SFN-004 fica calada em vez de
  adivinhar o job. SF-SFN-002 dispara, porque ela so le o ASL.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.state_machine
  - sfn.task
  - sfn.unresolved
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: [SF-SFN-002]
```

`fixtures/stepfunctions/retry_so_no_step_functions/input/main.tf`:

```hcl
resource "aws_glue_job" "carga_diaria" {
  name              = "carga-diaria"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://bucket-exemplo/scripts/carga_diaria.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://bucket-exemplo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://bucket-exemplo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
```

`fixtures/stepfunctions/retry_so_no_step_functions/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: retry so no Step Functions, o job declara max_retries 0.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 300, "MaxAttempts": 2, "BackoffRate": 1.0}],
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/retry_so_no_step_functions/meta.yaml`:

```yaml
name: retry_so_no_step_functions
proves: >
  Uma fronteira de SF-SFN-004: o vinculo existe, o retrier tem efetivo 2 e o job
  declara `max_retries = 0`. Uma camada so, e a regra calada. E o golden que muda se
  alguem trocar `glue_max_retries > 0` por `>= 0`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.glue_job_link
  - sfn.state_machine
  - sfn.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: [SF-SFN-002]
```

`fixtures/stepfunctions/retry_so_no_glue/input/main.tf`:

```hcl
resource "aws_glue_job" "carga_diaria" {
  name              = "carga-diaria"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 2
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://bucket-exemplo/scripts/carga_diaria.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://bucket-exemplo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://bucket-exemplo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
```

`fixtures/stepfunctions/retry_so_no_glue/input/carga.asl.json`:

```json
{
  "Comment": "Fixture sintetica: o Step Functions nao reexecuta a falha do job.",
  "StartAt": "RodarCarga",
  "States": {
    "RodarCarga": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 0}],
      "End": true
    }
  }
}
```

`fixtures/stepfunctions/retry_so_no_glue/meta.yaml`:

```yaml
name: retry_so_no_glue
proves: >
  A outra fronteira de SF-SFN-004: o vinculo existe, o job declara `max_retries = 2` e
  o retrier do Step Functions tem `MaxAttempts: 0`. Uma camada so, e nenhuma regra
  dispara. E o golden que muda se alguem trocar `sfn_retry_effective > 0` por `>= 0`
  -- e tambem `failure_retry_max_attempts > 0` da SF-SFN-002.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.glue_job_link
  - sfn.state_machine
  - sfn.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: []
```

### 2. Rodar e ver falhar

```bash
git add tests/test_fixtures_golden_stepfunctions.py
python -m pytest tests/test_stepfunctions.py::test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga tests/test_fixtures_golden_stepfunctions.py -q
```

Falhas esperadas: `ImportError: cannot import name 'build_sfn_glue_link'` na coleta do
golden (a derivação é a unidade sob teste), e `ValueError: not enough values to unpack`
em `[link] = ...` no teste do `fuse`.

### 3. Código mínimo

**3a. A derivação, em `sparkforge/facts/stepfunctions.py`** (D5).

No docstring do módulo, troque

```text
- `sfn.analyzed` -- a sentinela, com as contagens.
```

por

```text
- `sfn.analyzed` -- a sentinela, com as contagens.
- `sfn.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_sfn_glue_link` liga
  o Task do Glue ao `aws_glue_job` de mesmo `name` quando os dois estao no pool, e
  `fusion.fuse` a chama. As razoes de `sfn.unresolved` que so ela emite:
  `job_name_dynamic`, `job_definition_absent`, `job_definition_ambiguous` e
  `glue_max_retries_not_literal`.
```

Imports: troque

```python
import hashlib
import json
from dataclasses import dataclass, field
```

por

```python
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
```

`EMITTED_KINDS`: troque

```python
EMITTED_KINDS = frozenset(
    {
        "sfn.state_machine",
        "sfn.task",
        "sfn.unresolved",
        "sfn.analyzed",
    }
)
```

por

```python
EMITTED_KINDS = frozenset(
    {
        "sfn.state_machine",
        "sfn.task",
        "sfn.unresolved",
        "sfn.analyzed",
        "sfn.glue_job_link",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `sfn.task` no pool, o `fuse` sai byte a
# byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"sfn.task"})
```

E acrescente, logo antes de `__all__`:

```python
def _glue_jobs_por_nome(facts: Sequence[Fact]) -> dict[str, list[tuple[str, str]]]:
    """Nome literal do job -> [(arquivo, endereco do recurso)], de `tf.attribute` `name`."""
    nomes: dict[str, list[tuple[str, str]]] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        subject = fact.subject or {}
        attrs = fact.attrs or {}
        simbolo = str(subject.get("symbol") or "")
        if not simbolo.startswith("aws_glue_job."):
            continue
        if attrs.get("key") != "name" or attrs.get("block") != "root" or not attrs.get("literal"):
            continue
        arquivo = str(subject.get("file") or "")
        nomes.setdefault(str(attrs.get("value")), []).append((arquivo, simbolo))
    return nomes


def _max_retries(facts: Sequence[Fact], arquivo: str, simbolo: str) -> tuple[str, int | None]:
    """(`literal`, n), (`absent`, 0) ou (`not_literal`, None) para UM `aws_glue_job`.

    `absent` vale 0 porque o atributo nao declarado nao pede retry. Valor interpolado
    vira `tf.unresolved` sem o endereco do recurso (`terraform.py`); por isso qualquer
    `tf.unresolved` de `max_retries` no MESMO arquivo torna a resposta `not_literal` --
    conservador de proposito: nunca um zero que ninguem leu.
    """
    for fact in facts:
        subject = fact.subject or {}
        if fact.kind != "tf.attribute" or subject.get("symbol") != simbolo:
            continue
        if subject.get("file") != arquivo:
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != "max_retries" or attrs.get("block") != "root":
            continue
        valor = (fact.measures or {}).get("value")
        if attrs.get("literal") and isinstance(valor, int | float) and not isinstance(valor, bool):
            return "literal", int(valor)
        return "not_literal", None
    interpolado = any(
        f.kind == "tf.unresolved"
        and (f.attrs or {}).get("key") == "max_retries"
        and (f.subject or {}).get("file") == arquivo
        for f in facts
    )
    return ("not_literal", None) if interpolado else ("absent", 0)


def build_sfn_glue_link(facts: Sequence[Fact]) -> list[Fact]:
    """Liga cada `sfn.task` do Glue ao `aws_glue_job` de mesmo `name` literal (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `lakeformation.build_lakeformation`:
    o motor avalia um fact por condicao, e os dois lados tem `subject` diferente -- o
    estado da state machine e o recurso do Terraform --, entao `same_subject` nao os
    junta. Nao liga por substring: nome de job e chave exata na API do Glue.

    `sfn_retry_effective` e o `failure_retry_max_attempts` do Task: o efetivo do
    PRIMEIRO retrier que casa a falha do job (ver o docstring do modulo). O que nao liga
    sai nomeado em `sfn.unresolved`, nunca como vinculo.
    """
    nomes = _glue_jobs_por_nome(facts)
    saida: list[Fact] = []
    for task in facts:
        attrs = task.attrs or {}
        if task.kind != "sfn.task" or attrs.get("service") != "glue":
            continue
        if attrs.get("api") != "startJobRun":
            continue
        proveniencia = {
            "artifact": str((task.provenance or {}).get("artifact", "")),
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": [task.id],
        }
        nome = attrs.get("job_name")
        if attrs.get("job_name_dynamic") or not isinstance(nome, str):
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "job_name_dynamic",
                    proveniencia,
                    job_name_source=attrs.get("job_name_source", ""),
                    unblocked_by="JobName literal no estado Task",
                )
            )
            continue
        candidatos = nomes.get(nome, [])
        if len(candidatos) != 1:
            razao = "job_definition_absent" if not candidatos else "job_definition_ambiguous"
            saida.append(
                _unresolved(
                    dict(task.subject),
                    razao,
                    proveniencia,
                    job_name=nome,
                    resources=[simbolo for _, simbolo in candidatos],
                    unblocked_by="sparkforge analyze terraform no aws_glue_job, e fuse",
                )
            )
            continue
        arquivo, simbolo = candidatos[0]
        origem, retries = _max_retries(facts, arquivo, simbolo)
        measures: dict[str, Any] = {}
        efetivo = (task.measures or {}).get("failure_retry_max_attempts")
        if efetivo is not None:
            measures["sfn_retry_effective"] = efetivo
        if retries is not None:
            measures["glue_max_retries"] = retries
        saida.append(
            Fact(
                kind="sfn.glue_job_link",
                subject=dict(task.subject),
                measures=measures,
                attrs={
                    "job_name": nome,
                    "resource": simbolo,
                    "resource_file": arquivo,
                    "glue_max_retries_source": origem,
                    "sfn_retry_defaulted": bool(attrs.get("failure_retry_defaulted")),
                },
                provenance=proveniencia,
            )
        )
        if origem == "not_literal":
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "glue_max_retries_not_literal",
                    proveniencia,
                    job_name=nome,
                    resource=simbolo,
                )
            )
    return sort_facts(saida)
```

E no `__all__`, troque `    "EXTRACTOR_ID",` por

```python
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_sfn_glue_link",
```

**3b. `sparkforge/facts/fusion.py`.** Imports: troque

```python
from sparkforge.facts.timeout_diagnosis import EMITTED_KINDS as TIMEOUT_EMITTED_KINDS
```

por

```python
from sparkforge.facts.stepfunctions import EMITTED_KINDS as SFN_EMITTED_KINDS
from sparkforge.facts.stepfunctions import SOURCE_KINDS as SFN_SOURCE_KINDS
from sparkforge.facts.stepfunctions import build_sfn_glue_link
from sparkforge.facts.timeout_diagnosis import EMITTED_KINDS as TIMEOUT_EMITTED_KINDS
```

E no fim de `fuse`, troque

```python
    return sort_facts(combined.values())
```

por

```python
    # `sfn.glue_job_link` deriva AQUI pela mesma razao de `lakeformation.*`: o
    # `sfn.task` e o `aws_glue_job` tem `subject` diferente, e o motor nao junta dois
    # facts numa condicao. Guardado por `SOURCE_KINDS`: pool sem Step Functions sai
    # byte a byte igual.
    if any(f.kind in SFN_SOURCE_KINDS for f in facts):
        derivados_sfn = build_sfn_glue_link(facts)
        desconhecidos_sfn = {f.kind for f in derivados_sfn} - SFN_EMITTED_KINDS
        if desconhecidos_sfn:
            raise AssertionError(
                f"kind fora do namespace de stepfunctions: {sorted(desconhecidos_sfn)}"
            )
        for fact in derivados_sfn:
            combined[fact.id] = fact

    return sort_facts(combined.values())
```

(Confira antes que `    return sort_facts(combined.values())` aparece uma vez só em
`fusion.py`; é a última linha de `fuse`.)

**3c. `rules/catalog/stepfunctions.yaml`** (arquivo novo, inteiro):

```yaml
# Catálogo de regras — como o AWS Step Functions dispara o job Glue
#
# Depende de `sparkforge/facts/stepfunctions.py`, que lê a definição ASL (o
# `.asl.json` do repositório, ou a saída salva de `aws stepfunctions
# describe-state-machine`) e, em `fuse`, liga o estado Task ao `aws_glue_job` de mesmo
# `name` (`sfn.glue_job_link`). As frases citadas estão em
# `knowledge/stepfunctions/glue-integration.md`; o desenho, em
# `docs/sdd/STEP_FUNCTIONS/design.md`.
#
# O QUE A ÁREA NÃO JULGA, e por quê (D4):
# - `TimeoutSeconds` do Task contra o `Timeout` do job: o que acontece com o JobRun
#   quando o estado expira por `States.Timeout` não é documentado;
# - ausência de `Catch`: é política, não defeito, e a documentação só diz que o
#   default é falhar a execução;
# - serviços além do Glue: o extrator os registra, e nenhuma regra os julga.
#
# `runtime_scope: {}` nas quatro (D4), e a escolha é medida: não há fronteira de
# versão publicada para nenhuma delas, e o ASL sozinho não detecta runtime Glue --
# `{glue: "*"}` faria as quatro saírem em `skipped` até alguém declarar `--glue`, o
# defeito que `docs/gates-por-mudanca.md` descreve. Quem gateia é `requires_facts`:
# sem `sfn.task` (ou sem o `sfn.glue_job_link` que só o `fuse` deriva), a regra é
# pulada com a razão. A auditoria de texto AWS de `tests/test_databricks_rule_audit.py`
# fica satisfeita porque `stepfunctions` está em `SO_AWS`: o extrator só lê artefato
# da AWS.
#
# A ÂNCORA de cada regra é o fact que ela julga, com `same_subject: true`: um achado
# por estado Task, nunca um por arquivo. O `subject.symbol` é o caminho do estado na
# definição, então dois estados de mesmo nome em ramos de um Parallel são dois achados.

catalog_version: 1
schema_version: 1
area: SF-SFN
retrieved: 2026-09-19

rules:

  - id: SF-SFN-001
    category: stepfunctions
    title: "Job Glue disparado sem .sync: o próximo estado roda com o job ainda em execução"
    requires_facts: [sfn.task]
    when:
      same_subject: true
      all:
        - fact: sfn.task
          where:
            attrs.service: glue
            attrs.api: startJobRun
            attrs.pattern: request_response
            attrs.has_next: true
    status: structural
    severity_default: P1
    runtime_scope: {}
    explanation: >
      O estado chama `glue:startJobRun` no padrão Request Response — o `Resource` não
      termina em `.sync` —, e a documentação do Step Functions diz o que isso significa:
      "Step Functions will not wait for a job to complete." O estado termina quando o
      Glue aceita o pedido, e o `Next` roda com o job ainda em execução. Um estado
      seguinte que leia a saída do job lê dado parcial ou antigo, e o desfecho do
      JobRun não chega à execução da state machine. O padrão que espera o job terminar
      é o Run a Job (`.sync`), com o recurso `arn:aws:states:::glue:startJobRun.sync`.
      A regra exige `Next`: um `startJobRun` terminal (`End`) é disparo deliberado sem
      espera, e não há estado seguinte a proteger. Ver
      knowledge/stepfunctions/glue-integration.md.
    proposed_change:
      - "Trocar o `Resource` para `arn:aws:states:::glue:startJobRun.sync`, para que o estado espere o JobRun terminar e falhe junto com ele."
      - "Se o disparo sem espera é deliberado (o job segue sozinho e ninguém depende do resultado), tirar a dependência: nenhum estado seguinte pode ler a saída do job. Registrar a decisão no `Comment` do estado."
      - "Ao trocar para `.sync`, conferir a policy da role da state machine: a política que a AWS gera para o `.sync` do Glue inclui `glue:BatchStopJobRun`, além de `glue:StartJobRun`."
    # `orchestration.change_job_definition` porque a troca e de forma da definicao (o
    # padrao de integracao), nao de politica de execucao. `moves` evita
    # `runtime.wall_clock` de proposito: o grupo desse eixo esta no teto de 12 que
    # `tests/test_agentic_executor_ordering.py` e `tests/test_rules_action_field.py`
    # travam, e o que a troca muda de verdade e o que o estado seguinte le.
    action:
      kind: orchestration.change_job_definition
      target: sfn.task.resource
      direction: replace
      requires_absent: []
      moves:
        - correctness.write_result
      depends_on: []
    risks:
      - "Com `.sync`, a execução da state machine passa a durar o job inteiro. Em workflow EXPRESS o `.sync` não é suportado (SF-SFN-003)."
      - "Um job que hoje falha sem a state machine saber passa a falhar a execução: alarmes e Catch que nunca dispararam passam a disparar."
    tradeoffs:
      - "Esperar o job custa tempo de execução do workflow; disparar sem esperar custa a garantia de ordem entre o job e o resto do fluxo."
    validation:
      - "`sparkforge analyze step-functions --path <definição corrigida>` mostra o `sfn.task` com `pattern: sync`, e `sparkforge judge` não produz mais SF-SFN-001 para o estado."
      - "EIXO DE RESULTADO — numa execução de teste, o estado seguinte lê a saída completa do job: a contagem de linhas que ele lê é igual à que o JobRun escreveu, conferida no destino depois do `SUCCEEDED` do JobRun."
      - "Uma execução de teste em que o job falha termina a state machine em falha (ou no Catch declarado), e não segue para o estado seguinte."
    rollback:
      - "Reverter o commit da definição ASL e republicar a state machine pelo mesmo caminho que a publica (IaC ou `update-state-machine`). Execuções já iniciadas seguem com a definição com que começaram."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html", retrieved: 2026-09-19}

  - id: SF-SFN-002
    category: stepfunctions
    title: "Retry do Step Functions reexecuta o job Glue inteiro a cada tentativa"
    requires_facts: [sfn.task]
    when:
      same_subject: true
      all:
        - fact: sfn.task
          where:
            attrs.service: glue
            attrs.api: startJobRun
            attrs.pattern: sync
            attrs.failure_retry_matched: true
          expr: "measures.failure_retry_max_attempts > 0"
    status: structural
    severity_by:
      # O numero veio do default publicado: ninguem escolheu as tres execucoes a mais.
      - {when: "attrs.failure_retry_defaulted == True", severity: P1}
    severity_default: P2
    runtime_scope: {}
    explanation: >
      O estado espera o job (`.sync`) e tem um retrier cujo `ErrorEquals` contém
      `States.ALL` ou `States.TaskFailed` — os dois nomes que casam a falha do JobRun
      (`States.TaskFailed` "matches any known error name except for `States.Timeout`").
      Cada tentativa chama `StartJobRun` de novo: é um JobRun novo, que relê a entrada e
      reescreve a saída do começo, não uma retomada. Com `MaxAttempts` omitido o efetivo
      é o default publicado — "(`3` by default)" —, e um job batch que falha roda até
      quatro vezes antes de a execução desistir. A severidade sobe para P1 quando o
      número veio do default. O retrier que casa é o primeiro, na ordem declarada, cujo
      `ErrorEquals` contém um dos dois nomes; o efetivo dele está em
      `measures.failure_retry_max_attempts` do fact de evidência, e a marca de omitido em
      `attrs.failure_retry_defaulted`.
    proposed_change:
      - "Declarar `MaxAttempts` explícito no retrier que casa a falha do job, com o número de tentativas que o custo de um JobRun inteiro justifica — inclusive `0`, que desliga o retry para aquele erro."
      - "Restringir o `ErrorEquals` aos erros transitórios que valem nova tentativa (por exemplo `Glue.ConcurrentRunsExceededException`), em vez de `States.ALL` ou `States.TaskFailed`, que casam também a falha do próprio job."
      - "Se o job escreve em modo append, tornar a escrita idempotente antes de manter qualquer retry: cada tentativa é um JobRun que escreve de novo."
    action:
      kind: orchestration.restrict_run_policy
      target: sfn.task.retry
      direction: decrease
      requires_absent: []
      moves:
        - cost.dpu_seconds
        - correctness.write_result
      depends_on: []
    risks:
      - "Tirar o retry expõe a execução a falhas transitórias que hoje são absorvidas."
      - "Trocar `States.ALL` por erros nomeados exige o nome exato do erro transitório na integração: um nome errado desliga o retry sem aviso."
    tradeoffs:
      - "Retry sobre o job inteiro compra resiliência com o custo de um JobRun completo por tentativa; retry no próprio Glue compra a mesma resiliência com outro custo — e as duas camadas juntas são a SF-SFN-004."
    validation:
      - "`sparkforge analyze step-functions` mostra o retrier com `max_attempts_defaulted: false` e o `MaxAttempts` escolhido, e `sparkforge judge` não produz mais SF-SFN-002 para o estado, ou a produz em P2 quando o retry foi mantido de propósito."
      - "EIXO DE RESULTADO — numa execução de teste em que o job falha na primeira tentativa, o destino tem a mesma contagem total e a mesma contagem por chave de negócio que uma execução sem falha: a tentativa extra não duplicou nem perdeu linha."
      - "O histórico da execução (`aws stepfunctions get-execution-history`) mostra, para o estado, no máximo 1 + `MaxAttempts` agendamentos do Task."
    rollback:
      - "Reverter o commit da definição ASL e republicar a state machine."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html", retrieved: 2026-09-19}

  # O tipo mora em `sfn.state_machine`, e o motor avalia um fact por condicao: por isso
  # o extrator copia o tipo para `attrs.state_machine_type` de cada Task (regra 33), e a
  # regra le um fact so. `sfn.state_machine` fica em `requires_facts` para que o tipo
  # tenha sido LIDO, e `undeclared` nunca casa `EXPRESS`.
  - id: SF-SFN-003
    category: stepfunctions
    title: "Integração .sync numa state machine EXPRESS, que só suporta Request Response"
    requires_facts: [sfn.state_machine, sfn.task]
    when:
      same_subject: true
      all:
        - fact: sfn.task
          where:
            attrs.service: glue
            attrs.pattern: sync
            attrs.state_machine_type: EXPRESS
    status: confirmed
    severity_default: P1
    runtime_scope: {}
    explanation: >
      A saída de `describe-state-machine` declara `type: EXPRESS`, e a definição chama o
      Glue com `.sync`. A documentação do Step Functions é direta: "Express Workflows
      only support Request Response integrations." A combinação não é suportada, e o
      fluxo não espera o job como a definição foi escrita para esperar. O tipo só é lido
      quando vem declarado: um `.asl.json` sem a saída de `describe-state-machine` sai
      com `type: undeclared`, e a regra não dispara sobre suposição.
    proposed_change:
      - "Mover a chamada do Glue para uma state machine STANDARD, que suporta `.sync`, e chamá-la a partir da EXPRESS se o restante do fluxo precisa continuar EXPRESS."
      - "Ou manter a EXPRESS e trocar para Request Response (`arn:aws:states:::glue:startJobRun`), assumindo que o fluxo não espera o job — e então nenhum estado seguinte pode depender do resultado (SF-SFN-001)."
    # `moves: []`: a troca decide se a definicao e suportada, e nao mexe em grandeza que
    # algum fact meca antes e depois, nem no dado que o job escreve.
    action:
      kind: orchestration.change_job_definition
      target: sfn.state_machine.type
      direction: replace
      requires_absent: []
      moves: []
      depends_on: []
    risks:
      - "STANDARD e EXPRESS têm modelos de cobrança e de histórico de execução diferentes; mover o fluxo inteiro muda os dois."
    tradeoffs:
      - "Separar só a chamada do Glue numa STANDARD aninhada preserva a EXPRESS para o resto, ao custo de uma state machine a mais para manter."
    validation:
      - "`sparkforge analyze step-functions` sobre a saída nova de `describe-state-machine` mostra o `sfn.task` do Glue com `state_machine_type: STANDARD`, ou com `pattern: request_response`, e `sparkforge judge` não produz mais SF-SFN-003."
      - "EIXO DE RESULTADO — uma execução de teste termina com o JobRun em `SUCCEEDED` antes do estado seguinte, e o destino tem a contagem que o job escreveu."
    rollback:
      - "Reverter o commit da definição e do tipo no IaC que publica a state machine, e republicá-la."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html", retrieved: 2026-09-19}

  # A ancora e o fact DERIVADO: sem `fuse` com o ASL e o Terraform no mesmo pool, a
  # regra sai em `skipped` com `reason: requires_facts` -- "nao perguntei", nunca "esta
  # tudo bem". JobName dinamico e job ausente saem em `sfn.unresolved` na derivacao.
  - id: SF-SFN-004
    category: stepfunctions
    title: "Retry nas duas camadas: a state machine e o job Glue reexecutam a mesma falha"
    requires_facts: [sfn.glue_job_link]
    when:
      same_subject: true
      all:
        - fact: sfn.glue_job_link
          expr: "measures.sfn_retry_effective > 0 and measures.glue_max_retries > 0"
    status: structural
    severity_default: P2
    runtime_scope: {}
    explanation: >
      O estado Task do Glue tem retrier efetivo sobre a falha do job, e o `aws_glue_job`
      de mesmo `name` declara `max_retries` maior que zero: as duas camadas de retry
      existem sobre o mesmo job. Na API do Glue, `MaxRetries` é "The maximum number of
      times to retry this job after a JobRun fails.", e os parâmetros de `StartJobRun`
      não o incluem — o Step Functions não o sobrescreve. O que nenhuma das duas
      documentações descreve é a COMPOSIÇÃO: o `.sync` acompanha o JobRunId que o
      `StartJobRun` devolveu, e o retry do Glue é outro JobRun. Esta regra afirma só que
      as duas camadas existem; não afirma quantas vezes o job roda numa falha, porque
      esse número não é publicado. O vínculo entre o estado e o recurso é por `JobName`
      literal igual ao `name` do recurso — nome dinâmico ou recurso ausente saem em
      `sfn.unresolved`, nunca como vínculo. Ver
      knowledge/stepfunctions/glue-integration.md, lacuna 1.
    proposed_change:
      - "Escolher UMA camada de retry para a falha do job: `max_retries = 0` no `aws_glue_job` e o retry no Step Functions (onde `MaxAttempts` e `ErrorEquals` são explícitos e aparecem no histórico da execução), ou o retrier do Step Functions restrito a erros de chamada e o retry do job no Glue."
      - "Antes de escolher, medir: um histórico de execução real com falha (`aws stepfunctions get-execution-history`) e os JobRuns do job no mesmo intervalo (`sparkforge collect glue-job-runs`) mostram quantos JobRuns uma falha produziu de fato."
    action:
      kind: orchestration.restrict_run_policy
      target: glue.max_retries
      direction: decrease
      requires_absent: []
      moves:
        - cost.dpu_seconds
        - correctness.write_result
      depends_on: []
    risks:
      - "Zerar `max_retries` tira a retentativa que hoje cobre falhas transitórias quando o job roda fora da state machine (disparo manual ou outro gatilho)."
      - "A regra não mede quantas vezes o job rodou: o número depende da composição que a documentação não descreve."
    tradeoffs:
      - "Retry no Step Functions é visível no histórico da execução e configurável por erro; retry no Glue vale para qualquer gatilho do job. Manter as duas é escolha possível, desde que alguém tenha medido o que ela custa."
    validation:
      - "`sparkforge fuse` sobre os facts de `analyze step-functions` e `analyze terraform` mostra o `sfn.glue_job_link` com `glue_max_retries: 0` ou `sfn_retry_effective: 0`, e `sparkforge judge` não produz mais SF-SFN-004."
      - "EIXO DE RESULTADO — numa execução de teste com falha induzida, o destino tem a mesma contagem total e por chave de negócio que uma execução sem falha, e o número de JobRuns do intervalo é o que a camada escolhida declara."
    rollback:
      - "Restaurar o `max_retries` anterior no Terraform e o retrier anterior na definição ASL, e reaplicar os dois."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html", retrieved: 2026-09-19}
```

`rules/catalog/action_kinds.yaml` NÃO muda: os dois `kind` e os três eixos usados já
estão no vocabulário fechado (medido nesta branch; o grupo de `cost.dpu_seconds` tem 1
regra e vai a 3, longe do teto).

**3d. Rota — `rules/catalog/routing.yaml`** (tem BOM: edite com Edit). Troque

```yaml
fallback:
  recommended_skill: sparkforge-diagnose
```

por

```yaml
  # SF-SFN entrou com `docs/sdd/STEP_FUNCTIONS/` (2026-09-19) e ganha ENTRADA PROPRIA
  # pelo motivo de sempre: `rule_areas` do agente NAO roteia, e `findings_area` conta
  # por prefixo exato do `rule_id` ate o ultimo hifen.
  #
  # `glue-infra-reviewer` e o dono porque as quatro regras julgam COMO o job Glue e
  # disparado e quantas vezes ele roda -- padrao de integracao, retry do Step
  # Functions, retry do proprio job --, a mesma conversa de `max_retries` que ele ja
  # tem em SF-GLUE-004. PRECEDENCIA: depois de AGENT-002; um case com SF-GLUE junto vai
  # pela rota de cima, e o destino e o mesmo.
  - id: AGENT-086
    phase_in: [diagnosis, hypothesis, design, verification, documentation]
    title: Achado dominante em como o Step Functions dispara o job Glue
    when:
      all:
        - {findings_area: SF-SFN, count_gt: 0}
    recommended_agent: glue-infra-reviewer
    reason: >
      A state machine que dispara o job decide se o fluxo espera o job terminar e
      quantas vezes uma falha reexecuta o job inteiro. O conserto mora na definicao ASL
      e no `max_retries` do `aws_glue_job` -- os dois artefatos de infraestrutura que
      este coordenador ja le --, e nao no codigo do job.

fallback:
  recommended_skill: sparkforge-diagnose
```

**3e. Coordenador — `agents/glue-infra-reviewer.md`.** Troque
`rule_areas: [SF-GLUE, SF-ENV]` por `rule_areas: [SF-GLUE, SF-ENV, SF-SFN]`, e troque

```markdown
sem a saída de `describe-state-machine`, o tipo sai `undeclared`, nunca `STANDARD`.
```

por

```markdown
sem a saída de `describe-state-machine`, o tipo sai `undeclared`, nunca `STANDARD`.

A área `SF-SFN` julga esses facts. Com o Terraform do mesmo job no case,
`sparkforge_fuse` liga o `Task` ao `aws_glue_job` de mesmo `name` (`sfn.glue_job_link`),
e é aí que as duas camadas de retry aparecem juntas: o `max_retries` do job e o retrier
do Step Functions. A composição das duas não é documentada — afirme que as duas existem,
nunca quantas vezes o job roda numa falha.
```

Espelhos: backup do README, `python scripts/sync_skills.py`, devolva o README; e o mesmo
parágrafo em `.codex/agents/glue-infra-reviewer.toml`, logo depois da linha equivalente
do `developer_instructions`.

**3f. As duas listas manuais do extrator, no mesmo commit do golden.**

`tests/test_rules_catalog_reachability.py` — as DUAS ocorrências (o import e a tupla
`EXTRACTORS`); em cada uma troque

```python
    sql_metrics,
    terraform,
```

por

```python
    sql_metrics,
    # `stepfunctions` entra nas DUAS listas manuais no MESMO commit da area SF-SFN:
    # sem ele aqui, os cinco kinds `sfn.*` contam como orfaos e as quatro regras
    # seriam forcadas a `blocked_on` sobre um extrator que esta no repositorio.
    stepfunctions,
    terraform,
```

`tests/test_fixtures_kind_coverage.py` — import: troque

```python
    sql_metrics,
    terraform,
```

por

```python
    sql_metrics,
    stepfunctions,
    terraform,
```

e no dicionário `EXTRACTORS`, troque

```python
    "terraform": terraform,
```

por

```python
    # `stepfunctions` entra nas DUAS listas no MESMO commit de `fixtures/stepfunctions/`:
    # sem ele aqui, os cinco kinds `sfn.*` nao sao verificados por ninguem.
    "stepfunctions": stepfunctions,
    "terraform": terraform,
```

**3g. `scripts/regen_fixtures.py`** — o par do `_extract` do golden.

Imports: troque

```python
from sparkforge.facts.sql_literal import extract_sql_path  # noqa: E402
```

por

```python
from sparkforge.facts.sql_literal import extract_sql_path  # noqa: E402
from sparkforge.facts.stepfunctions import (  # noqa: E402
    build_sfn_glue_link,
    extract_stepfunctions_tree,
)
```

e troque

```python
from sparkforge.migration.assessment import assess  # noqa: E402
```

por

```python
from sparkforge.findings.models import sort_facts  # noqa: E402
from sparkforge.migration.assessment import assess  # noqa: E402
```

Constante: troque

```python
FIXTURES_CONTROLM = ROOT / "fixtures" / "controlm"
```

por

```python
FIXTURES_CONTROLM = ROOT / "fixtures" / "controlm"
FIXTURES_STEPFUNCTIONS = ROOT / "fixtures" / "stepfunctions"
```

Função: troque

```python
def regen_dq(directory: Path) -> None:
```

por

```python
def regen_stepfunctions(directory: Path) -> None:
    """Definicoes ASL do AWS Step Functions: `*.json` sob input/, e `main.tf` ao lado.

    O PAR de `tests/test_fixtures_golden_stepfunctions.py::_extract`, e a mesma porta do
    produto: fixture so com `.json` e o que `analyze step-functions` ve; com `.tf` ao
    lado, extrai o Terraform e deriva `sfn.glue_job_link` como `fusion.fuse` faz.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = list(extract_stepfunctions_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        facts.extend(build_sfn_glue_link(facts))
    facts = sort_facts(facts)
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_dq(directory: Path) -> None:
```

Despacho por nome: troque

```python
                (FIXTURES_CONTROLM / name, regen_controlm),
```

por

```python
                (FIXTURES_CONTROLM / name, regen_controlm),
                (FIXTURES_STEPFUNCTIONS / name, regen_stepfunctions),
```

Laço completo: troque

```python
            regen_controlm(directory)
```

por

```python
            regen_controlm(directory)
    # Mesma guarda de existencia: `fixtures/stepfunctions/` nasce nesta entrega.
    if FIXTURES_STEPFUNCTIONS.is_dir():
        for directory in sorted(p for p in FIXTURES_STEPFUNCTIONS.iterdir() if p.is_dir()):
            regen_stepfunctions(directory)
```

**3h. Regenerar e LER o golden.**

```bash
git add sparkforge/facts/stepfunctions.py tests/test_fixtures_golden_stepfunctions.py
python scripts/regen_fixtures.py glue_sem_sync glue_retry_implicito glue_retry_explicito express_com_sync glue_limpo definicao_ilegivel retry_duas_camadas job_name_dinamico retry_so_no_step_functions retry_so_no_glue
```

Confira a saída linha a linha contra o `expects_rules` de cada `meta.yaml`: SF-SFN-001 em
`glue_sem_sync`; SF-SFN-002 em `glue_retry_implicito` (severidade **P1** no
`findings.json`), em `glue_retry_explicito` (**P2**), em `retry_duas_camadas`,
`job_name_dinamico` e `retry_so_no_step_functions`; SF-SFN-003 só em `express_com_sync`;
SF-SFN-004 só em `retry_duas_camadas`; nada em `glue_limpo`, `definicao_ilegivel` e
`retry_so_no_glue`. Qualquer outra regra no golden é achado que ninguém pediu: pare e
relate.

**3i. Registros que a regra move.**

- `manifest.json`: `"rule_count": 157,` → `"rule_count": 161,`.
- Fontes: `python scripts/refresh_knowledge.py --offline --update` (quatro URLs novas das
  regras entram em `knowledge/sources.lock.json`; `aws-glue-api-jobs-runs` já estava, por
  `rules/catalog/timeout.yaml`, e ganha o vínculo com `SF-SFN-004`).
- Goldens de assessment (carregam a contagem do catálogo):
  `python scripts/regen_fixtures.py glue_40_para_60_salto_longo glue_51_para_60_iceberg_ansi glue_60_fgac_com_jar config_por_caminho_indireto lote_misto_iceberg_parquet`.
  Confira com `git diff --stat -- fixtures/scenarios evals/holdout` e
  `git diff -- fixtures/scenarios evals/holdout | grep '^[-+] '`: só `catalog_rules`
  (157 → 161), `unguarded_rules` (131 → 135: as quatro têm `runtime_scope: {}`) e a
  frase `statement` que repete os dois ("Catalogo: 161 regras, ... e 135 sem guarda").
  Qualquer outra linha é achado que mudou: pare e relate.
- `tests/test_sf_stubs.py`, em `test_catalogo_so_tem_regra_que_julga`: a contagem era a
  foto do SF_STUBS e deixa de ser afirmada; as outras duas asserções ficam. Troque

  ```python
      assert [r["id"] for r in catalogo if r.get("executable", True) is False] == []
      assert len(catalogo) == 157
  ```

  por

  ```python
      assert [r["id"] for r in catalogo if r.get("executable", True) is False] == []
      # A contagem (157) era a foto do SF_STUBS, e cada area nova a derrubava sem medir
      # nada do que este teste guarda. Quem publica a contagem e o STATUS, pelo gate.
  ```

- `tests/test_databricks_rule_audit.py`, em `SO_AWS`: troque

  ```python
      "cloudwatch_logs": "le `filter_log_events` do CloudWatch Logs",
  ```

  por

  ```python
      "cloudwatch_logs": "le `filter_log_events` do CloudWatch Logs",
      "stepfunctions": (
          "le a definicao ASL do AWS Step Functions (`arn:aws:states`) e deriva "
          "`sfn.glue_job_link` do `aws_glue_job` do Terraform"
      ),
  ```

  Sem esta entrada, as quatro `SF-SFN` (sem eixo de plataforma AWS no `runtime_scope`)
  contam como alcançáveis num job Databricks, e o texto delas cita Glue.
- Referência: `python scripts/gen_reference_docs.py` (a página do agente muda com
  `rule_areas`).

**3j. Números.** `docs/superpowers/STATUS.md`, trocas de prefixo de linha, antes → depois:

```text
| Regras de diagnóstico | **157**, sendo **97 `confirmed`** e **60 com `status: structural`**, todas executáveis —
| Regras de diagnóstico | **161**, sendo **98 `confirmed`** e **63 com `status: structural`**, todas executáveis — as quatro `SF-SFN` (como o AWS Step Functions dispara o job Glue) entraram em 2026-09-19 (feature `docs/sdd/STEP_FUNCTIONS/`), `SF-SFN-003` `confirmed` e as outras três `structural`. Leitura anterior de **157**, sendo **97 `confirmed`** e **60 com `status: structural`**, todas executáveis —
```

```text
| Regras com eixo de resultado no `validation` | **157 de 157 têm `validation`**, todas as que ficam —
| Regras com eixo de resultado no `validation` | **161 de 161 têm `validation`** — as quatro `SF-SFN` (2026-09-19) entram com eixo de resultado. Leitura anterior de **157 de 157 têm `validation`**, todas as que ficam —
```

```text
| Fact kinds distintos emitidos | **232** —
| Fact kinds distintos emitidos | **233** — `sfn.glue_job_link` (2026-09-19), derivado em `fuse` quando o ASL e o Terraform do job estão no mesmo pool. Leitura anterior de **232** —
```

```text
| Rotas determinísticas | **40** —
| Rotas determinísticas | **41** — a acrescida é `AGENT-086` (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`), que leva achado `SF-SFN` a `glue-infra-reviewer`. Leitura anterior de **40** —
```

```text
| Fixtures golden | **516** em 56 domínios —
| Fixtures golden | **526** em 57 domínios — as **10** acrescidas formam o domínio novo `fixtures/stepfunctions/` (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`), sintéticas a partir dos exemplos oficiais; quatro trazem o `main.tf` do job ao lado do ASL. Leitura anterior de **516** em 56 domínios —
```

```text
| Fontes oficiais vigiadas | **254** (239 móveis, 15 fixas) —
| Fontes oficiais vigiadas | **258** (243 móveis, 15 fixas) — as **quatro** acrescidas são citadas pelas regras `SF-SFN` (2026-09-19, feature `docs/sdd/STEP_FUNCTIONS/`): `connect-glue`, `connect-to-resource` e `concepts-error-handling` do guia do Step Functions, e `aws-glue-api-jobs-job` da API do Glue; `aws-glue-api-jobs-runs` já estava no lock. Leitura anterior de **254** (239 móveis, 15 fixas) —
```

A linha "Regras com `runtime_scope` não-vazio" não muda (continua 26): as quatro
declaram `{}`.

`README.md`: linha 45, `Os 39 extratores emitem 232 kinds distintos` →
`Os 39 extratores emitem 233 kinds distintos`; linha 46, `**157** regras de diagnóstico
em YAML, **157 delas executáveis**` → `**161** regras de diagnóstico em YAML, **161 delas
executáveis**`.

E a prosa auditada:

- `docs/guia/06-extrair-julgar-compor.md`: linha 86, `emitem 232 kinds` →
  `emitem 233 kinds`; linha 231, `nenhum dos 232 kinds` → `nenhum dos 233 kinds`.
- `docs/guia/07-conhecimento-e-catalogo.md`:
  - `desse conhecimento: **157** regras de` → `desse conhecimento: **161** regras de`;
  - `**157 delas executáveis**, ou seja, todas` → `**161 delas executáveis**, ou seja, todas`;
  - `mais **40** rotas determinísticas` → `mais **41** rotas determinísticas`;
  - `As 157 executáveis se distribuem em 28 áreas (medido em 2026-09-17 com `area_of`):`
    → `As 161 executáveis se distribuem em 29 áreas (medido em 2026-09-19 com `area_of`):`;
  - `(fronteira do Spark 4), `SF-KMS` 2,` → `(fronteira do Spark 4), `SF-SFN` 4 (como o AWS
    Step Functions dispara o job Glue), `SF-KMS` 2,`;
  - `Cada uma das 157 carrega` → `Cada uma das 161 carrega`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_stepfunctions.py tests/test_fixtures_golden_stepfunctions.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_criterio_de_dominio.py -q
```

O último é o `verified_by` da AC8: a área `SF-SFN` tem regra executável que julga, o
`glue-infra-reviewer` a declara, e a rota `AGENT-086` dispara por `findings_area`.

### 5. Gates vizinhos

Regra, `runtime_scope`, área, extrator, corpus, routing, agent, fontes (seções de
`docs/gates-por-mudanca.md`), um comando por vez:

```bash
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py -q
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py tests/test_rules_action_field.py tests/test_rules_campos_de_lista.py -q
python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q
python -m pytest tests/test_databricks_rule_audit.py tests/test_agentic_executor_ordering.py tests/test_harness_untrusted.py tests/test_sf_stubs.py -q
python -m pytest tests/test_verify_wheel.py tests/test_case_router.py tests/test_case_store.py tests/test_artifact_contents.py -q
python -m pytest tests/test_fixtures_scenarios.py tests/test_evals_holdout.py -q
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_reference_docs.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py tests/test_facts_scan.py -q
python -m ruff check sparkforge scripts tests
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

(backup e devolução do `.claude/agents/README.md` em volta do sync e de
`test_agents_parity.py`.) `test_rules_threshold_mutation.py` tem de passar SEM entrada nova
em `FRONTEIRA_SEM_GOLDEN`: `glue_limpo`, `retry_so_no_glue` e `retry_so_no_step_functions`
existem para matar as trocas `>`→`>=` das duas `expr`. O gate de lastro reprova de novo
pelo `.py` novo do golden: remedie pelos ids, como em T1.

### 6. Commit

`feat(rules): add the SF-SFN area judging how Step Functions triggers Glue jobs`, com no
corpo: 4 regras (157 → 161), a rota `AGENT-086`, o kind derivado `sfn.glue_job_link` em
`fuse`, 10 fixtures no domínio novo, 4 fontes novas.

## T4 — o documento de conhecimento, o manual de uso e os registros finais

### 1. O teste que falha

Esta tarefa não tem teste próprio: o vermelho é o do lock de fontes, que acusa a URL nova
da seção `## Fontes` do documento antes de ela entrar no lock. Escreva
`knowledge/stepfunctions/glue-integration.md` (arquivo novo, inteiro):

```markdown
# Step Functions disparando job Glue: integração, retry e tipo de workflow

> **Lido em 2026-09-19.** Seis páginas oficiais da AWS: quatro do guia do AWS Step
> Functions e duas da API do AWS Glue. Quem consome: o extrator
> `sparkforge/facts/stepfunctions.py` (os dois defaults publicados moram lá, com a URL
> ao lado) e as quatro regras de `rules/catalog/stepfunctions.yaml`. Frase entre aspas é
> citação literal; o resto é leitura nossa, e diz de qual frase veio.

## 1. O recurso e os padrões de integração

O Glue tem o padrão *Run a Job* (`.sync`), com o recurso
`arn:aws:states:::glue:startJobRun.sync` (connect-glue). A mesma página publica a
política IAM gerada para o `.sync`, e ela inclui `glue:BatchStopJobRun`.

| padrão | `Resource` | o que a documentação diz |
|---|---|---|
| Request Response | `arn:aws:states:::glue:startJobRun` | "Step Functions will not wait for a job to complete." |
| Run a Job (`.sync`) | `arn:aws:states:::glue:startJobRun.sync` | "If a task using this (`.sync`) service integration pattern is aborted, and Step Functions is unable to cancel the task, you might incur additional charges from the integrated service." |
| callback (`.waitForTaskToken`) | — | o extrator registra o padrão; nenhuma regra o julga para o Glue |

Sobre o tipo de workflow, a mesma página (connect-to-resource): "Express Workflows only
support Request Response integrations."

## 2. Retry, erros reservados e os defaults

- `MaxAttempts` "(`3` by default)" — concepts-error-handling. O extrator grava o efetivo
  (`max_attempts`) e a marca de omitido (`max_attempts_defaulted`).
- `States.TaskFailed` "matches any known error name except for `States.Timeout`", e
  `States.ALL` não pega `States.Runtime` — concepts-error-handling.
- `TimeoutSeconds`: "The default value is 99,999,999", e `TimeoutSeconds` e
  `TimeoutSecondsPath` não coexistem no mesmo estado — state-task.

Leitura nossa, a partir das duas primeiras: a falha de um JobRun sob `.sync` chega ao
estado como erro, e o primeiro retrier, na ordem declarada, cujo `ErrorEquals` contém
`States.TaskFailed` ou `States.ALL` a casa. Cada tentativa desse retrier chama
`StartJobRun` de novo — um JobRun novo, não uma retomada.

## 3. O lado do Glue

- `MaxRetries`: "The maximum number of times to retry this job after a JobRun fails."
  (aws-glue-api-jobs-job).
- `Timeout`: "defaulted to 2,880 minutes for Glue version 4.0 and earlier, or 480
  minutes for Glue version 5.0 and later" (aws-glue-api-jobs-job).
- Os parâmetros de `StartJobRun` não incluem `MaxRetries` (aws-glue-api-jobs-runs): o
  Step Functions não o sobrescreve.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-SFN-001 | Request Response com `Next`: o estado seguinte roda com o job em execução | que o job vai falhar |
| SF-SFN-002 | retrier efetivo sobre a falha do job `.sync`; P1 quando o número é o default | que retry é errado — só que cada tentativa é um JobRun inteiro |
| SF-SFN-003 | `.sync` sob `type: EXPRESS` declarado | nada quando o tipo é `undeclared` |
| SF-SFN-004 | as duas camadas de retry existem sobre o mesmo job | quantas vezes o job roda numa falha (lacuna 1) |

O vínculo da SF-SFN-004 é por `JobName` literal igual ao `name` do `aws_glue_job`, feito
em `fuse`. `JobName.$`, expressão JSONata e job ausente do Terraform saem em
`sfn.unresolved` com a razão, nunca como vínculo.

## 5. Lacunas nomeadas

1. **Composição dos retries.** Nenhuma das duas documentações descreve como o retry do
   Step Functions compõe com o `MaxRetries` do Glue. O `.sync` acompanha o `JobRunId`
   que o `StartJobRun` devolveu, e o retry do Glue é outro JobRun. O que destrava
   afirmar a contagem de tentativas: um histórico de execução real com falha
   (`get-execution-history`) junto dos JobRuns do mesmo intervalo, ou documentação
   oficial que a descreva.
2. **JobRun quando o Task expira.** A leitura registrada em
   `docs/sdd/STEP_FUNCTIONS/define.md` não achou o que acontece com o JobRun quando o
   estado expira por `States.Timeout`: a descrição do abort do `.sync` não inclui
   timeout. Por isso não há regra de `TimeoutSeconds` contra o `Timeout` do job.
3. **ASL real não observado.** O corpus `fixtures/stepfunctions/` é sintético, montado a
   partir dos exemplos oficiais. Um `.asl.json` ou `describe-state-machine` real do
   operador, lido na conversa e nunca commitado, é o que o testaria contra produção.

## Fontes

- Guia do AWS Step Functions — integração com o AWS Glue: o padrão `.sync`, o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort, e o limite dos Express Workflows. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — estado Task: `TimeoutSeconds` e `TimeoutSecondsPath`. https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html (retrieved 2026-09-19)
- API do AWS Glue — Jobs: `MaxRetries` e `Timeout`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html (retrieved 2026-09-19)
- API do AWS Glue — Job runs: os parâmetros de `StartJobRun`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html (retrieved 2026-09-19)
```

### 2. Rodar e ver falhar

```bash
python -m pytest "tests/test_refresh_knowledge.py::TestWatchlistIsDerivedFromBothOrigins::test_the_committed_lock_matches_the_watchlist" -q
```

Falha esperada: `AssertionError` com a URL de `state-task` na watchlist e fora do lock (as
outras cinco já entraram em T3 pelas regras).

### 3. Código mínimo

Lock de fontes:

```bash
python scripts/refresh_knowledge.py --offline --update
```

Manifesto offline — o `sha256` pela função que o gate confere, nunca por outro hash:

```bash
python -c "import json; from pathlib import Path; from sparkforge.tools.offline import _content_sha256; p = Path('knowledge/offline-manifest.json'); m = json.loads(p.read_text(encoding='utf-8')); doc = 'knowledge/stepfunctions/glue-integration.md'; m['documents'] = [d for d in m['documents'] if d['path'] != doc] + [{'path': doc, 'title': 'glue-integration', 'sha256': _content_sha256(Path(doc))}]; m['documents'].sort(key=lambda d: d['path']); p.write_bytes((json.dumps(m, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))"
```

(O manifesto está ordenado por `path` e gravado como `json.dumps(indent=2)` mais `\n` —
medido nesta branch; `write_bytes` evita o CRLF do Windows.)

`parity.yaml`, na capacidade de T2: troque

```yaml
    cli: [analyze step-functions]
    platforms:
```

por

```yaml
    cli: [analyze step-functions]
    knowledge:
      - knowledge/stepfunctions/glue-integration.md
    platforms:
```

Manual de uso — `docs/guia/usos/step-functions.md` (arquivo novo, inteiro; o bloco externo
usa `~~~~` porque o manual tem blocos de código dentro):

~~~~markdown
# Step Functions: como a state machine dispara o job Glue

O **AWS Step Functions** orquestra jobs Glue por uma *state machine*, escrita em Amazon
States Language (ASL). Este manual mostra como o SparkForge lê essa definição e confere
três coisas sobre o job Glue que ela dispara: se o fluxo **espera** o job terminar,
quantas vezes o **retry** reexecuta o job inteiro, e se o **tipo** do workflow suporta o
padrão que a definição pede. Com o Terraform do job ao lado, ele mostra também quando o
retry existe nas **duas camadas** — na state machine e no próprio job.

O SparkForge **não** chama a API do Step Functions e não lê histórico de execução. Ele
lê a definição. Todos os exemplos usam arquivos sintéticos de `fixtures/stepfunctions/`.

## Receita rápida

```bash
mkdir -p /tmp/sf

# 1. Extrair os facts da definicao (.asl.json, saida de describe-state-machine, ou diretorio)
sparkforge analyze step-functions \
  --path fixtures/stepfunctions/glue_sem_sync/input --out /tmp/sf/facts_sfn.json

# 2. Julgar: SF-SFN-001 a 003 leem so o ASL
sparkforge judge --facts /tmp/sf/facts_sfn.json

# 3. Com o Terraform do job: extrair os dois lados, fundir e julgar
sparkforge analyze step-functions \
  --path fixtures/stepfunctions/retry_duas_camadas/input --out /tmp/sf/sfn.json
sparkforge analyze terraform \
  --path fixtures/stepfunctions/retry_duas_camadas/input --out /tmp/sf/tf.json
sparkforge fuse --facts /tmp/sf/sfn.json --facts /tmp/sf/tf.json --out /tmp/sf/fundidos.json
sparkforge judge --facts /tmp/sf/fundidos.json
```

A definição vem do repositório (o `.asl.json` que o IaC publica) ou da conta: a saída de
`aws stepfunctions describe-state-machine --state-machine-arn <arn>`, salva em arquivo,
é lida do mesmo jeito — e é a única das duas que traz o `type` (STANDARD ou EXPRESS).

## O que sai

| kind | um por | o que diz |
|---|---|---|
| `sfn.state_machine` | definição | `type` (`STANDARD`, `EXPRESS` ou `undeclared`), linguagem de consulta, origem |
| `sfn.task` | estado `Task`, inclusive em `Parallel` e `Map` | serviço, API, padrão (`request_response`, `sync`, `callback`), `JobName` literal ou dinâmico, retriers com o `MaxAttempts` efetivo, `Catch`, `TimeoutSeconds` |
| `sfn.glue_job_link` | Task ligado a um `aws_glue_job` (só em `fuse`) | o retry efetivo do Step Functions e o `max_retries` do job |
| `sfn.unresolved` | o que não deu para ler ou ligar | a razão: JSON inválido, recurso dinâmico, `JobName` dinâmico, job ausente do Terraform |
| `sfn.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

Um `.asl.json` não traz o tipo do workflow: sem a saída de `describe-state-machine`, ele
sai `undeclared`, nunca `STANDARD` por suposição.

## As quatro regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-SFN-001` | `glue:startJobRun` sem `.sync` e com `Next`: o próximo estado roda com o job em execução | P1 |
| `SF-SFN-002` | Task `.sync` com retrier em `States.ALL` ou `States.TaskFailed` e `MaxAttempts` efetivo maior que zero: cada tentativa é um JobRun inteiro | P1 com `MaxAttempts` omitido (3 por default), P2 declarado |
| `SF-SFN-003` | `.sync` numa state machine com `type: EXPRESS` declarado | P1 |
| `SF-SFN-004` | o Task ligado ao job tem retry efetivo e o job tem `max_retries` maior que zero | P2 |

A `SF-SFN-004` afirma só que as duas camadas existem. **Quantas vezes o job roda numa
falha não é documentado** — o retry do Glue é outro JobRun, e o `.sync` acompanha o
primeiro. Medir exige um histórico de execução real com falha e os JobRuns do mesmo
intervalo (`sparkforge collect glue-job-runs`).

## O que ele não faz

- Não lê histórico de execução (`get-execution-history`) nem coleta da conta: o
  operador salva a saída do `describe-state-machine` em arquivo.
- Não lê a definição dentro de `aws_sfn_state_machine` do Terraform (`templatefile`,
  `jsonencode`): só o ASL em arquivo ou a saída do `describe-state-machine`.
- Não julga outros serviços (Lambda, Batch, EMR): o extrator os registra, e nenhuma regra
  os julga.
- Não compara o `TimeoutSeconds` do Task com o `Timeout` do job: o que acontece com o
  JobRun quando o estado expira não é documentado.

## Referência

- As frases citadas e as lacunas: [`knowledge/stepfunctions/glue-integration.md`](../../knowledge/stepfunctions/glue-integration.md).
- As regras: [`rules/catalog/stepfunctions.yaml`](../../rules/catalog/stepfunctions.yaml).
- O corpus: [`fixtures/stepfunctions/`](../../fixtures/stepfunctions/).
~~~~

Superfície (documento de `knowledge/` novo move o lock — regra 26):

```bash
python scripts/check_surface_lock.py --update
```

Critério de domínio — `docs/gates-por-mudanca.md`, seção "Critério de domínio: artefato
antes de nome": Step Functions deixa de estar entre os domínios sem artefato. Troque

```markdown
depois o coordenador que sabe quando investigá-la. Domínio que ainda não tem artefato
(Airflow, DynamoDB, Kinesis, Lambda, Step Functions) não ganha agente nem área: ganha
`unresolved` nomeando o artefato que falta. Foi por essa porta que 35 áreas e 26
```

por

```markdown
depois o coordenador que sabe quando investigá-la. Domínio que ainda não tem artefato
(Airflow, DynamoDB, Kinesis, Lambda) não ganha agente nem área: ganha `unresolved`
nomeando o artefato que falta. Step Functions saiu desta lista em 2026-09-19 pela porta
certa (`docs/sdd/STEP_FUNCTIONS/`): o extrator da definição ASL veio primeiro, a área
`SF-SFN` julga os facts dele, e `glue-infra-reviewer` a declara com rota por
`findings_area`. Foi por essa porta que 35 áreas e 26
```

Número: `docs/superpowers/STATUS.md`, antes → depois:

```text
| Fontes oficiais vigiadas | **258** (243 móveis, 15 fixas) —
| Fontes oficiais vigiadas | **259** (244 móveis, 15 fixas) — a acrescida é a página `state-task` do guia do Step Functions (2026-09-19), citada só por `knowledge/stepfunctions/glue-integration.md` (o default de `TimeoutSeconds`). Leitura anterior de **258** (243 móveis, 15 fixas) —
```

### 4. Rodar e ver passar

```bash
python -m pytest "tests/test_refresh_knowledge.py::TestWatchlistIsDerivedFromBothOrigins::test_the_committed_lock_matches_the_watchlist" -q
python scripts/verify_offline_bundle.py
python scripts/check_status_numbers.py --strict
```

Os dois últimos são os `verified_by` da AC9 e da AC10: `"ok": true` e `0 divergencia(s)`.

### 5. Gates vizinhos

"Editar um documento em `knowledge/`", a referência gerada e os números:

```bash
python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q
python -m pytest tests/test_capability_parity.py tests/test_surface_lock.py tests/test_reference_docs.py -q
python -m pytest tests/test_status_numbers_gate.py tests/test_criterio_de_dominio.py tests/test_sdd.py -q
python scripts/check_vnext_claims.py
```

`test_reference_docs.py` confere que todo comando que o manual ensina existe
(`analyze step-functions`, `analyze terraform`, `fuse`, `judge`) e que os links
relativos resolvem.

### 6. Commit

`docs(knowledge): cite the Step Functions and Glue integration sources and add the usage guide`,
com o crescimento da superfície em bytes no corpo.

---

## Dúvidas

As perguntas da primeira versão foram decididas e estão gravadas no design (D1, D4, D5,
D8 e o manifesto). Ficam três pontos pequenos, todos de manifesto:

1. **Páginas geradas e espelhos que o manifesto não lista.** `gen_reference_docs.py`
   reescreve também `docs/guia/referencia/cli/analyze.md` (T2) e
   `docs/guia/referencia/agents/glue-infra-reviewer.md` (T2 e T3), e
   `sync_skills.py` reescreve `.claude/agents/glue-infra-reviewer.md`,
   `.agents/agents/glue-infra-reviewer.md` e `.github/agents/glue-infra-reviewer.agent.md`
   (T2 e T3). O plano os produz pelos scripts, mas eles não estão no `files` de nenhuma
   tarefa porque não estão no manifesto.
2. **Os cinco goldens de assessment.** O manifesto lista um só
   (`glue_40_para_60_salto_longo`) e diz que ele representa "três cenários e dois
   holdout". O `files` de T3 lista os cinco por extenso; confirme ou reduza.
3. **`tests/test_sf_stubs.py`.** A troca tira a asserção de contagem e deixa um
   comentário no lugar, com a razão. Se preferir sem comentário, basta apagar a linha.
