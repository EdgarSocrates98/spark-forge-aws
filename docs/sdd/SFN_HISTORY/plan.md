---
sdd: 1
feature: SFN_HISTORY
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_HISTORY/design.md
  sha256: "8db52096b630ed396b87a19016cb3b7fbe88e6fe0c800a3001c48aeb8f439485"
tasks:
  - id: T1
    files: [sparkforge/facts/sfn_history.py, tests/test_sfn_history.py, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3]
    test: {path: tests/test_sfn_history.py, name: test_historico_vira_execucao_e_tentativas}
  - id: T2
    files: [tests/test_sfn_history.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_adapters_tools.py, tests/test_harness_authorization.py, tests/test_fixtures_golden_mcp_parity.py, parity.yaml, manifest.json, agents/glue-infra-reviewer.md, .claude/agents/glue-infra-reviewer.md, .agents/agents/glue-infra-reviewer.md, .github/agents/glue-infra-reviewer.agent.md, .codex/agents/glue-infra-reviewer.toml, docs/surface.lock.json, docs/guia/referencia/tools/README.md, docs/guia/referencia/tools/sparkforge_analyze_sfn_history.md, docs/guia/referencia/cli/analyze.md, docs/guia/referencia/agents/glue-infra-reviewer.md, docs/guia/06-extrair-julgar-compor.md, docs/superpowers/STATUS.md, README.md, CLAUDE.md, AGENTS.md, GUIA_DE_USO.md, .devin/README.md, docs/harness/AUTHORIZATION-CHAIN.md, docs/harness/CURRENT-HARNESS-GAP.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC7]
    test: {path: tests/test_sfn_history.py, name: test_cli_e_tool_devolvem_os_mesmos_facts}
  - id: T3
    files: [tests/test_sfn_history.py, sparkforge/facts/sfn_history.py, sparkforge/facts/fusion.py, rules/catalog/sfn-history.yaml, rules/catalog/routing.yaml, agents/glue-infra-reviewer.md, .claude/agents/glue-infra-reviewer.md, .agents/agents/glue-infra-reviewer.md, .github/agents/glue-infra-reviewer.agent.md, .codex/agents/glue-infra-reviewer.toml, fixtures/sfn_history, tests/test_fixtures_golden_sfn_history.py, scripts/regen_fixtures.py, tests/test_fixtures_kind_coverage.py, tests/test_rules_catalog_reachability.py, tests/test_databricks_rule_audit.py, sparkforge/agentic/executor/debate_evidence.py, docs/agentic-evolution-report.md, fixtures/debate/retomada/expected/brief.json, manifest.json, knowledge/sources.lock.json, docs/guia/referencia/agents/glue-infra-reviewer.md, fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, fixtures/scenarios/glue_51_para_60_iceberg_ansi/expected/assessment.json, fixtures/scenarios/glue_60_fgac_com_jar/expected/assessment.json, evals/holdout/config_por_caminho_indireto/expected/assessment.json, evals/holdout/lote_misto_iceberg_parquet/expected/assessment.json, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/guia/07-conhecimento-e-catalogo.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC4, AC5, AC6, AC8]
    test: {path: tests/test_fixtures_golden_sfn_history.py, name: test_golden}
  - id: T4
    files: [knowledge/stepfunctions/execution-history.md, knowledge/stepfunctions/glue-integration.md, knowledge/INDEX.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, docs/guia/usos/step-functions.md, docs/gates-por-mudanca.md, parity.yaml, docs/surface.lock.json, docs/superpowers/STATUS.md, docs/claims.lock.json]
    covers: [AC9, AC10]
    test: {path: tests/test_surface_lock.py, name: "TestOLockBateComAMedida::test_the_knowledge_matches"}
---

# SFN_HISTORY — plano

> Branch `sdd/sfn-history`, empilhada sobre `main` depois do #90 (STEP_FUNCTIONS).
> **A branch `sdd/airflow-dag` (#91) NÃO está nesta árvore** — ela existe em
> `git log sdd/airflow-dag` e ainda não foi mergeada. Todos os números deste plano
> foram medidos aqui, em `caf829a3`, e por isso são os de **depois do #90 e antes do
> #91**. Se o #91 entrar antes desta feature, **meça de novo**: o gate é que vale.
>
> O precedente inteiro — extrator, verbo, tool, área com regras, derivação em `fuse`,
> corpus, golden e os registros — existe duas vezes: `docs/sdd/STEP_FUNCTIONS/plan.md`
> (nesta árvore) e `docs/sdd/AIRFLOW_DAG/plan.md` (em `sdd/airflow-dag`). Este plano os
> espelha tarefa a tarefa. Onde ele se afasta do precedente, a razão está escrita no
> lugar.

## Regras de execução

- Pouca memória: **um comando por vez**, nunca a suíte inteira nem os lotes de
  `tests/test_suite_batches.py` em paralelo com edição.
- Edição por ferramenta (Edit/Write), fim de linha LF. `rules/catalog/routing.yaml` tem
  BOM: edite com Edit, nunca reescreva o arquivo inteiro.
- Arquivo `.py` novo do pacote entra no índice (`git add <arquivo>`) **antes** de
  qualquer teste: `tests/test_arvore_versionada.py` reprova `.py` de `sparkforge/**`
  fora do git.
- **`python scripts/sync_skills.py` e `tests/test_agents_parity.py` apagam o
  `.claude/agents/README.md` não rastreado.** Antes de cada um:
  `cp .claude/agents/README.md "$TEMP/claude_agents_README.bak.md"`; depois:
  `cp "$TEMP/claude_agents_README.bak.md" .claude/agents/README.md`. O README nunca
  entra no `git add`.
- Agente se edita na fonte `agents/<nome>.md`; `.claude/`, `.agents/` e `.github/` saem
  do `sync_skills.py`. **`.codex/agents/<nome>.toml` o sync NÃO gera**: é espelho à mão,
  e a seção nova vai nele no mesmo commit.
- **`description` de agente não pode conter `: `** — quebra o frontmatter YAML e derruba
  29 parametrizações de `tests/test_router_agents.py`. Armadilha paga na revisão final do
  AIRFLOW_DAG; a `description` do `glue-infra-reviewer` muda em T2 e usa ` - `, nunca `: `.
- Commit por tarefa com `git commit -F <arquivo no scratchpad>`, mensagem conventional
  em inglês, terminando com as duas linhas de atribuição da sessão.
- `python scripts/check_vnext_claims.py` antes de todo commit que acrescenta `.py` ou
  move `len(TOOLS)`. Remedie **pela lista de ids da saída do gate**, nunca por varredura;
  `--seed` reescreve o lock inteiro — se precisar dele, guarde só a entrada nova e
  devolva o resto com `git checkout docs/claims.lock.json`. Em `docs/claims.lock.json`,
  **`expect.value` é `int` em `kind: number` e `kind: pattern`, e string em
  `kind: contains`** — trocar o tipo faz o gate reprovar com uma mensagem que não diz isso.

## Medidas desta árvore, tiradas antes de começar

Com os produtores de `scripts/check_status_numbers.py` (`0 divergencia(s)` na hora,
2026-09-20, em `caf829a3`):

| medida | antes | depois desta feature |
|---|---|---|
| Regras de diagnóstico | **161** (98 `confirmed`, 63 `structural`, 26 com `runtime_scope` não-vazio) | **164** (**101** `confirmed`, 63 `structural`, 26 com `runtime_scope` não-vazio) |
| Áreas (`area_of`) | **29** | **30** |
| Tools MCP | **107** (99 declaram caminho, 39 com `detail_level`) | **108** (**100** com caminho, **40** com `detail_level`) |
| Extratores de facts | **39** | **40** |
| Fact kinds distintos | **233** | **237** |
| Rotas determinísticas | **41** | **42** |
| Coordenadores | **12** | **12** (nenhum novo) |
| Fixtures golden | **528** em **57** domínios | **538** em **58** domínios |
| Fontes oficiais vigiadas | **262** (247 móveis, 15 fixas) | **263** (248 móveis, 15 fixas) |
| Documentos de `knowledge/` no `surface.lock` | **54** | **55** |
| Bytes de `knowledge/` no `surface.lock` | **510162** | **meça** (`check_surface_lock.py --update` imprime) |
| `manifest.json` `rule_count` | **161** | **164** |
| Goldens de assessment: `catalog_rules` / `unguarded_rules` | **161** / **135** | **164** / **138** |
| Allowlist de extratores de evidência do debate | **23** | **24** |
| Arquivos `.py` que `iter_source_files` entrega | **756** | **759** (3 módulos novos; nenhuma fixture é `.py`) |
| `len(TOOLS) - len(sem_caminho)` em `test_harness_authorization` | **99** | **100** |

**Publique o que o gate medir na hora, não o número escrito aqui.** Se alguma linha
divergir ao executar, a medida do gate é que vale — este plano é a previsão, e a
previsão pode estar errada.

Quatro medidas que decidem desenho e ficam registradas aqui:

- **Os kinds sobem 4 e não 6.** `sfn.unresolved` e `sfn.analyzed` **já existem** —
  `stepfunctions.py` os declara. O prefixo compartilhado é D1, e a consequência é
  aritmética: entram `sfn.execution`, `sfn.attempt`, `sfn.job_run` (T1) e
  `sfn.retry_observado` (T3). 233 → 236 em T1, 236 → 237 em T3.
- **`runtime.wall_clock` é o maior grupo de eixo de `action.moves`, com 12**, e
  `tests/test_agentic_executor_ordering.py::test_os_maiores_grupos_de_restricao_tem_dez_regras_cada`
  afirma `maior == 12` e `no_topo == {"runtime.wall_clock"}`. **Nenhuma regra `SF-SFNX`
  pode declarar `runtime.wall_clock`.** Os eixos escolhidos são `cost.dpu_seconds`
  (3 → 4), `correctness.write_result` (`nature: risk`, fora da restrição) e `moves: []`
  nas duas que só mandam medir.
- **Só a `SF-SFNX-001` tem `expr` com comparação.** `tests/test_rules_threshold_mutation.py`
  compara `FRONTEIRA_SEM_GOLDEN` por igualdade exata: a fixture
  `retry_dentro_do_declarado` tem `tentativas_observadas == teto_declarado`, e é ela que
  mata a troca `>` → `>=`. **Sem entrada nova em `FRONTEIRA_SEM_GOLDEN`.**
- **Custo não entra em lugar nenhum.** Regras 13 e 25 do `CLAUDE.md`: nenhuma regra, nenhum
  fact e nenhum texto deste plano atribui custo a uma tentativa, estima economia ou fala em
  dólar. O que existe é contagem de tentativa, duração medida entre timestamps, e o
  `JobRunId` — que é o que permite ao operador perguntar o custo pelo verbo `finops`, com
  `dpu_seconds` de verdade.

## Por que quatro tarefas, e não cinco

Pelo mesmo motivo medido no STEP_FUNCTIONS e repetido no AIRFLOW_DAG: a contagem do
catálogo move seis registros (`manifest.json`, `STATUS.md`, `README.md`,
`docs/guia/07`, os cinco goldens de assessment e o lastro), e separar as regras em duas
tarefas moveria os seis duas vezes. A área precisa entrar inteira com rota e coordenador
(`test_router_agents`, `test_agent_coverage`, `test_criterio_de_dominio`). Então T3 leva
as três regras, a derivação, a área, a rota, o corpus e o golden; e a derivação fica em
T3 e não em T1 porque o teste dela (AC4) só fecha com a `SF-SFNX-001` julgando.

`sfn.retry_observado` entra em `EMITTED_KINDS` só em T3: declarado em T1 sem golden, ele
deixaria `test_every_kind_of_every_extractor_appears_in_some_golden[sfn_history]`
vermelho assim que o módulo entrasse nas listas manuais.

## O que este plano refina do desenho (e por quê)

Cinco pontos, todos repetidos na seção **Dúvidas** no fim:

1. **A tentativa é pareada pelo ENCADEAMENTO, não pela ordem.** D1 diz "o estado vem do
   `TaskStateEntered` mais recente". Aplicado como "o último `TaskStateEntered` visto até
   aqui", ele erra dentro de `Parallel` e `Map`, onde os estados se intercalam. A
   refinação: subir a cadeia de `previousEventId` a partir do próprio evento até o
   primeiro ancestral do tipo procurado — que é exatamente o que a API garante, porque o
   encadeamento é por ramo. Quando a cadeia quebra (evento referenciado ausente, raiz
   antes de achar o ancestral, ou ciclo), **nada é chutado**: sai `sfn.unresolved` com
   `chain_broken`, `state_unresolved` ou `attempt_unanchored`.
2. **Três atributos DERIVADOS pelo extrator (regra 33).** `rules/expr.py` tem seis
   comparadores e nenhuma função: `attrs.execution_outcome_class` (`stopped` para
   `ExecutionAborted`/`ExecutionTimedOut`, `finished` para as outras duas, `unresolved`
   sem evento terminal), `attrs.job_run_outcome_observed` e `attrs.terminal_present`. Sem
   eles, AC5 e AC6 exigiriam `in` e negação, que o motor não tem.
3. **O corpus separa `input/definicao/` de `input/historico/`.** D8 fala em "o par ASL +
   histórico". Postos no mesmo diretório, cada extrator leria o arquivo do outro e sairia
   um `sfn.unresolved` cruzado por fixture — ruído que não é medida. Em subdiretórios, o
   golden chama cada extrator no seu, que é o que a produção faz: dois verbos, dois
   `--path`.
4. **Uma razão a mais que a lista de D1: `state_name_absent_in_asl`.** O ASL está no case,
   mas não declara um estado com aquele nome (renomeado, ou de outra state machine). É
   diferente de `asl_absent` — ali ninguém perguntou; aqui perguntou-se e não bateu — e
   confundir os dois esconderia um erro de pareamento atrás de uma lacuna.
5. **`sfn.job_run` lê o `output` defensivamente, e nomeia o que não reconhece (U1).** A
   forma exata do `output` do `TaskSubmitted` do Glue não está na página da API. O
   extrator aceita `output` como objeto ou como string JSON, procura `JobRunId`, depois
   `Id`, depois `JobRun.Id`, e, quando nada casa, emite `sfn.unresolved`
   `job_run_id_unrecognized` **com as chaves de topo que viu** — que é o fact que um
   histórico real fecha U1 com.

## Cobertura dos critérios, por id exato

Os nomes de teste são os que o `define` fixou, e nenhum deles é inventado aqui.

| AC | tarefa | o que o fecha |
|---|---|---|
| AC1 | T1 | `tests/test_sfn_history.py::test_historico_vira_execucao_e_tentativas` |
| AC2 | T1 | `tests/test_sfn_history.py::test_job_run_vem_do_output_e_a_ausencia_sai_nomeada` |
| AC3 | T1 | `tests/test_sfn_history.py::test_historico_incompleto_sai_nomeado_sem_perder_o_que_leu` |
| AC4 | T3 | `tests/test_fixtures_golden_sfn_history.py::test_golden` (`retry_acima_do_declarado` e `historico_sem_asl`), apoiado por `tests/test_sfn_history.py::test_fuse_confronta_o_retry_declarado_com_o_observado` |
| AC5 | T3 | `tests/test_fixtures_golden_sfn_history.py::test_golden` (`task_timed_out_sync`) |
| AC6 | T3 | `tests/test_fixtures_golden_sfn_history.py::test_golden` (`execucao_abortada_com_task_em_voo`) |
| AC7 | T2 | `tests/test_sfn_history.py::test_cli_e_tool_devolvem_os_mesmos_facts` |
| AC8 | T3 | `tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato` (ver a ressalva no §4 de T3) |
| AC9 | T4 | `python scripts/verify_offline_bundle.py` |
| AC10 | T4 | `python scripts/check_status_numbers.py --strict` |

## T1 — o extrator do histórico

### 1. Teste que falha

`tests/test_sfn_history.py` (arquivo novo):

```python
"""O extrator do historico de execucao do AWS Step Functions: o que ACONTECEU.

Historicos sinteticos, montados a partir da forma de evento publicada em
`API_GetExecutionHistory`: nenhum historico real foi observado (U2 de
`docs/sdd/SFN_HISTORY/define.md`). A forma exata do `output` do `TaskSubmitted` do
Glue e a lacuna U1, e por isso o extrator le tres formas e nomeia o que nao reconhece.
"""
import json

from sparkforge.facts.sfn_history import (
    extract_sfn_history,
    extract_sfn_history_path,
    extract_sfn_history_tree,
)


def _evento(id_, anterior, tipo, segundo, **detalhes):
    evento = {
        "id": id_,
        "previousEventId": anterior,
        "timestamp": f"2026-09-18T03:00:{segundo:02d}.000000+00:00",
        "type": tipo,
    }
    evento.update(detalhes)
    return evento


def _agendado(**extra):
    detalhes = {"resource": "startJobRun.sync", "resourceType": "glue"}
    detalhes.update(extra)
    return {"taskScheduledEventDetails": detalhes}


def _submetido(saida):
    detalhes = {"resource": "startJobRun.sync", "resourceType": "glue"}
    if saida is not None:
        detalhes["output"] = saida
    return {"taskSubmittedEventDetails": detalhes}


# Tres tentativas do MESMO estado, cada uma com um JobRun proprio, e a execucao
# terminando em falha. E o formato de resposta da API: objeto com `events`.
HISTORICO_COM_TRES_TENTATIVAS = {
    "events": [
        _evento(1, 0, "ExecutionStarted", 0),
        _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "CargaDiaria"}),
        _evento(3, 2, "TaskScheduled", 2, **_agendado(timeoutInSeconds=3600)),
        _evento(4, 3, "TaskStarted", 3, taskStartedEventDetails={"resourceType": "glue"}),
        _evento(5, 4, "TaskSubmitted", 4, **_submetido('{"JobRunId": "jr_a", "JobName": "carga-diaria"}')),
        _evento(
            6,
            5,
            "TaskFailed",
            30,
            taskFailedEventDetails={
                "resource": "startJobRun.sync",
                "resourceType": "glue",
                "error": "Glue.AWSGlueException",
                "cause": "JobRun jr_a FAILED",
            },
        ),
        _evento(7, 6, "TaskScheduled", 31, **_agendado()),
        _evento(8, 7, "TaskStarted", 32),
        _evento(9, 8, "TaskSubmitted", 33, **_submetido({"JobRunId": "jr_b"})),
        _evento(
            10,
            9,
            "TaskFailed",
            60,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "JobRun jr_b FAILED"},
        ),
        _evento(11, 10, "TaskScheduled", 61, **_agendado()),
        _evento(12, 11, "TaskStarted", 62),
        _evento(13, 12, "TaskSubmitted", 63, **_submetido({"JobRun": {"Id": "jr_c"}})),
        _evento(
            14,
            13,
            "TaskFailed",
            90,
            taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "JobRun jr_c FAILED"},
        ),
        _evento(
            15,
            14,
            "ExecutionFailed",
            91,
            executionFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "esgotou"},
        ),
    ]
}


def _de(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_historico_vira_execucao_e_tentativas():
    facts = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")

    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["status"] == "failed"
    assert execucao.attrs["arn_declared"] is False
    assert execucao.attrs["source"] == "get_execution_history"
    assert execucao.attrs["truncated"] is False
    assert execucao.measures == {
        "event_count": 15,
        "attempt_count": 3,
        "job_run_count": 3,
        "duration_seconds": 91.0,
    }

    tentativas = sorted(_de(facts, "sfn.attempt"), key=lambda f: f.measures["attempt_index"])
    assert [t.measures["attempt_index"] for t in tentativas] == [1, 2, 3]
    assert {t.subject["symbol"] for t in tentativas} == {
        "CargaDiaria#1",
        "CargaDiaria#2",
        "CargaDiaria#3",
    }
    primeira = tentativas[0]
    assert primeira.attrs["state_name"] == "CargaDiaria"
    assert (primeira.attrs["service"], primeira.attrs["api"]) == ("glue", "startJobRun")
    assert primeira.attrs["pattern"] == "sync"
    assert primeira.attrs["resource"] == "startJobRun.sync"
    assert primeira.attrs["result"] == "failed"
    assert primeira.attrs["terminal_present"] is True
    assert primeira.attrs["submitted"] is True
    assert primeira.attrs["error"] == "Glue.AWSGlueException"
    assert primeira.attrs["cause"] == "JobRun jr_a FAILED"
    assert primeira.attrs["job_run_outcome_observed"] is True
    assert primeira.attrs["execution_outcome"] == "failed"
    assert primeira.attrs["execution_outcome_class"] == "finished"
    assert primeira.measures["duration_seconds"] == 28.0
    assert primeira.measures["timeout_seconds"] == 3600

    [sentinela] = _de(facts, "sfn.analyzed")
    assert sentinela.measures == {
        "execution_count": 1,
        "attempt_count": 3,
        "job_run_count": 3,
        "unresolved_count": 0,
    }


def test_job_run_vem_do_output_e_a_ausencia_sai_nomeada():
    facts = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    corridas = sorted(_de(facts, "sfn.job_run"), key=lambda f: f.subject["symbol"])
    assert [c.attrs["job_run_id"] for c in corridas] == ["jr_a", "jr_b", "jr_c"]
    # As TRES formas que o extrator aceita, e de qual chave cada uma veio (U1).
    assert [c.attrs["read_from"] for c in corridas] == ["JobRunId", "JobRunId", "JobRun.Id"]
    assert corridas[0].attrs["job_name"] == "carga-diaria"
    assert corridas[1].attrs["job_name"] is None
    assert [c.subject["symbol"] for c in corridas] == [
        "CargaDiaria#1",
        "CargaDiaria#2",
        "CargaDiaria#3",
    ]

    # `includeExecutionData` desligado: o `TaskSubmitted` vem sem `output`. Nenhum
    # `sfn.job_run` e afirmado, e a lacuna sai nomeada.
    sem_dado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSubmitted", 3, **_submetido(None)),
            _evento(5, 4, "TaskSucceeded", 9),
            _evento(6, 5, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(sem_dado, "sem-dado.json")
    assert _de(facts, "sfn.job_run") == []
    motivos = {f.attrs["reason"] for f in _de(facts, "sfn.unresolved")}
    assert motivos == {"execution_data_absent"}

    # `output` presente e com forma que o extrator NAO reconhece: as chaves de topo
    # saem no fact, porque e delas que sai a resposta da lacuna U1.
    desconhecido = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSubmitted", 3, **_submetido({"SomethingElse": 1, "Outra": 2})),
            _evento(5, 4, "TaskSucceeded", 9),
            _evento(6, 5, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(desconhecido, "desconhecido.json")
    assert _de(facts, "sfn.job_run") == []
    [falha] = _de(facts, "sfn.unresolved")
    assert falha.attrs["reason"] == "job_run_id_unrecognized"
    assert falha.attrs["output_keys"] == ["Outra", "SomethingElse"]


def test_historico_incompleto_sai_nomeado_sem_perder_o_que_leu(tmp_path):
    # Truncado: `nextToken` na saida salva. O que foi lido continua valendo, e a
    # execucao sai `unresolved` porque o evento terminal pode estar na pagina que
    # ninguem salvou.
    truncado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskStarted", 3),
        ],
        "nextToken": "AAAAKgAAAAIAAAAAAAAAAg==",
    }
    facts = extract_sfn_history(truncado, "truncado.json")
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["status"] == "unresolved"
    assert execucao.attrs["truncated"] is True
    [tentativa] = _de(facts, "sfn.attempt")
    assert tentativa.attrs["result"] == "none"
    assert tentativa.attrs["terminal_present"] is False
    assert tentativa.attrs["execution_outcome_class"] == "unresolved"
    assert "duration_seconds" not in tentativa.measures
    motivos = sorted(f.attrs["reason"] for f in _de(facts, "sfn.unresolved"))
    assert motivos == ["execution_terminal_absent", "truncated"]

    # Cadeia quebrada (o evento 7 aponta para um id que nao esta no arquivo), tipo
    # desconhecido, e evento que nao e objeto.
    esburacado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSucceeded", 9),
            _evento(5, 4, "ExecutionSucceeded", 10),
            _evento(6, 4, "EventoDoFuturo", 10),
            _evento(7, 99, "TaskScheduled", 11, **_agendado()),
            "nao e um evento",
        ]
    }
    facts = extract_sfn_history(esburacado, "esburacado.json")
    motivos = sorted(f.attrs["reason"] for f in _de(facts, "sfn.unresolved"))
    assert motivos == ["event_not_an_object", "event_type_unknown", "state_unresolved"]
    desconhecido = [f for f in facts if f.attrs.get("reason") == "event_type_unknown"]
    assert desconhecido[0].attrs["type"] == "EventoDoFuturo"
    # O que foi lido continua valendo: a tentativa completa saiu.
    [tentativa] = _de(facts, "sfn.attempt")
    assert (tentativa.attrs["state_name"], tentativa.attrs["result"]) == ("Carga", "succeeded")

    # JSON invalido e JSON que nao e historico: um `sfn.unresolved` por arquivo, e a
    # sentinela sai dos dois.
    (tmp_path / "quebrado.json").write_text('{"events": [', encoding="utf-8")
    (tmp_path / "inventario.json").write_text('{"jobs": ["carga-diaria"]}', encoding="utf-8")
    facts = extract_sfn_history_tree(tmp_path, repo_root=tmp_path)
    assert sorted(
        (f.subject["file"], f.attrs["reason"]) for f in _de(facts, "sfn.unresolved")
    ) == [
        ("inventario.json", "not_an_execution_history"),
        ("quebrado.json", "invalid_json"),
    ]
    assert len(_de(facts, "sfn.analyzed")) == 2

    # A lista crua de eventos, sem o envelope da resposta, tambem e lida.
    (tmp_path / "lista.json").write_text(
        json.dumps(HISTORICO_COM_TRES_TENTATIVAS["events"]), encoding="utf-8"
    )
    facts = extract_sfn_history_path(tmp_path / "lista.json", repo_root=tmp_path)
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["source"] == "event_list"
    assert len(_de(facts, "sfn.attempt")) == 3
```

### 2. Rodar e ver falhar

```bash
git add tests/test_sfn_history.py
python -m pytest tests/test_sfn_history.py -q
```

Falha esperada: `ModuleNotFoundError: No module named 'sparkforge.facts.sfn_history'` na
coleta — o módulo ausente é a unidade sob teste.

### 3. Código mínimo

`sparkforge/facts/sfn_history.py` (arquivo novo, inteiro):

```python
"""Extrator de Facts a partir do HISTORICO de execucao do AWS Step Functions.

Le a saida salva de `aws stepfunctions get-execution-history` ja em disco: o objeto
de resposta da API (`{"events": [...]}`, com `nextToken` opcional) ou a lista crua de
eventos. Como `stepfunctions.py` e `controlm_jobs.py`, NAO coleta nada e NUNCA levanta
excecao por payload malformado: o que nao consegue ler vira `sfn.unresolved` com
`attrs.reason`, e a sentinela `sfn.analyzed` sai sempre, uma por arquivo.

## Por que o MESMO prefixo `sfn.` do ASL

E o mesmo dominio, e o kind diz a natureza: `sfn.task` e DECLARACAO (o que o ASL diz
que deve acontecer) e `sfn.attempt` e MEDIDA (o que o historico registra que
aconteceu). Um prefixo proprio separaria em dois dominios o que o operador ve como um
(D1 de `docs/sdd/SFN_HISTORY/design.md`). A consequencia e aritmetica e esta declarada
no plano: `sfn.unresolved` e `sfn.analyzed` JA existem, e este modulo acrescenta tres
kinds, nao cinco.

## O que sai

- `sfn.execution` -- um por arquivo lido. `attrs.status` vem do evento terminal da
  execucao (`succeeded`, `failed`, `aborted`, `timed_out`) e e `unresolved` quando
  nenhum deles esta no arquivo -- NUNCA `succeeded` por suposicao. `attrs.arn` so
  existe quando a saida salva traz `executionArn`: a resposta de
  `get-execution-history` nao o traz, e inventa-lo seria afirmar leitura que nao houve.
- `sfn.attempt` -- um por TENTATIVA de Task: o par entre um `TaskScheduled` e o
  primeiro evento terminal do MESMO agendamento. O `subject.symbol` e
  `<nome do estado>#<ordem>`.
- `sfn.job_run` -- um por `JobRunId` lido do `output` do `TaskSubmitted`, ligado a
  tentativa pelo mesmo `subject.symbol`.
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`,
  `size_above_limit`, `invalid_json`, `json_too_deep`, `not_an_execution_history`,
  `truncated`, `event_not_an_object`, `event_type_unknown`, `state_unresolved`,
  `attempt_unanchored`, `chain_broken`, `execution_terminal_absent`,
  `execution_data_absent` e `job_run_id_unrecognized`.
- `sfn.analyzed` -- a sentinela, com as contagens.

## Como uma tentativa e PAREADA, e por que pela cadeia

A API publica `previousEventId` em todo evento, e o encadeamento e por RAMO: dentro de
`Parallel` e de `Map` os eventos de ramos diferentes se intercalam na ordem de `id`,
mas cada um aponta para o anterior DO SEU ramo. Por isso o pareamento sobe a cadeia a
partir do proprio evento ate o primeiro ancestral do tipo procurado, e nunca usa "o
ultimo visto ate aqui", que erraria exatamente nesses dois casos.

- de um `TaskScheduled` sobe-se ate o `TaskStateEntered` -> o NOME do estado;
- de um terminal (`TaskSucceeded`, `TaskFailed`, `TaskTimedOut`, `TaskStartFailed`,
  `TaskSubmitFailed`) sobe-se ate o `TaskScheduled` -> a TENTATIVA que ele fecha;
- de um `TaskSubmitted` sobe-se ate o `TaskScheduled` -> a tentativa que submeteu.

Cadeia que chega a raiz sem achar, evento referenciado ausente do arquivo, ou ciclo:
`sfn.unresolved` nomeado. NUNCA um chute -- atribuir a tentativa ao estado errado num
`Parallel` seria pior do que nao atribuir.

## Tres atributos DERIVADOS aqui (regra 33)

`sparkforge/rules/expr.py` tem seis comparadores e nenhuma funcao, e `where` so compara
por igualdade. Os tres predicados que as regras precisam sao derivados no extrator:

- `execution_outcome_class`: `stopped` para `ExecutionAborted` e `ExecutionTimedOut`,
  `finished` para `ExecutionSucceeded` e `ExecutionFailed`, `unresolved` sem terminal;
- `terminal_present`: a tentativa tem evento terminal proprio;
- `job_run_outcome_observed`: o desfecho do JobRun foi observado pelo Task. So e
  verdadeiro num `.sync` que terminou em `TaskSucceeded` ou `TaskFailed` -- num
  `TaskTimedOut` o Task expirou ANTES, e num Request Response o Task nunca acompanhou.

## O que este modulo NAO faz

- Nao chama a API. O operador salva a saida e aponta o `--path`.
- Nao le historico de EXPRESS: `get-execution-history` "is not supported by EXPRESS
  state machines", e o historico dele vai para o CloudWatch Logs.
- Nao atribui custo a tentativa nem estima economia (regras 13 e 25 do `CLAUDE.md`). O
  que ele entrega e o `JobRunId`, que e por onde o operador pergunta custo com
  `dpu_seconds` medido.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sparkforge.facts import scan
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "sfn_history@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sfn.execution",
        "sfn.attempt",
        "sfn.job_run",
        "sfn.unresolved",
        "sfn.analyzed",
    }
)

# https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html
# Os tipos de `HistoryEventType` que a pagina publica. Tipo fora desta lista nao e
# erro do artefato -- e a API que cresceu --, e por isso sai em `sfn.unresolved`
# `event_type_unknown` com o nome, em vez de ser ignorado em silencio.
_TIPOS_CONHECIDOS = frozenset(
    {
        "ActivityFailed",
        "ActivityScheduleFailed",
        "ActivityScheduled",
        "ActivityStarted",
        "ActivitySucceeded",
        "ActivityTimedOut",
        "ChoiceStateEntered",
        "ChoiceStateExited",
        "ExecutionAborted",
        "ExecutionFailed",
        "ExecutionStarted",
        "ExecutionSucceeded",
        "ExecutionTimedOut",
        "FailStateEntered",
        "LambdaFunctionFailed",
        "LambdaFunctionScheduleFailed",
        "LambdaFunctionScheduled",
        "LambdaFunctionStartFailed",
        "LambdaFunctionStarted",
        "LambdaFunctionSucceeded",
        "LambdaFunctionTimedOut",
        "MapIterationAborted",
        "MapIterationFailed",
        "MapIterationStarted",
        "MapIterationSucceeded",
        "MapRunAborted",
        "MapRunFailed",
        "MapRunStarted",
        "MapRunSucceeded",
        "MapStateAborted",
        "MapStateEntered",
        "MapStateExited",
        "MapStateFailed",
        "MapStateStarted",
        "MapStateSucceeded",
        "ParallelStateAborted",
        "ParallelStateEntered",
        "ParallelStateExited",
        "ParallelStateFailed",
        "ParallelStateStarted",
        "ParallelStateSucceeded",
        "PassStateEntered",
        "PassStateExited",
        "SucceedStateEntered",
        "SucceedStateExited",
        "TaskFailed",
        "TaskScheduled",
        "TaskStartFailed",
        "TaskStarted",
        "TaskStateAborted",
        "TaskStateEntered",
        "TaskStateExited",
        "TaskSubmitFailed",
        "TaskSubmitted",
        "TaskSucceeded",
        "TaskTimedOut",
        "WaitStateAborted",
        "WaitStateEntered",
        "WaitStateExited",
    }
)

# Evento terminal de UMA tentativa -> o `result` que sai no fact.
_RESULTADO_POR_TIPO = {
    "TaskSucceeded": "succeeded",
    "TaskFailed": "failed",
    "TaskTimedOut": "timed_out",
    "TaskStartFailed": "start_failed",
    "TaskSubmitFailed": "submit_failed",
}

# Evento terminal da EXECUCAO -> o `status` que sai no fact.
_STATUS_POR_TIPO = {
    "ExecutionSucceeded": "succeeded",
    "ExecutionFailed": "failed",
    "ExecutionAborted": "aborted",
    "ExecutionTimedOut": "timed_out",
}

# A execucao PAROU (alguem abortou, ou o relogio dela estourou) contra ela TERMINOU
# por conta propria. A distincao decide a SF-SFNX-003 e e derivada aqui (regra 33).
_PARADA = frozenset({"aborted", "timed_out"})

# O desfecho do JobRun so e observado pelo Task nestes dois terminais, e so sob `.sync`.
_OBSERVA_O_JOB_RUN = frozenset({"succeeded", "failed"})

_DETALHES_POR_TIPO = {
    "TaskScheduled": "taskScheduledEventDetails",
    "TaskStarted": "taskStartedEventDetails",
    "TaskSubmitted": "taskSubmittedEventDetails",
    "TaskSucceeded": "taskSucceededEventDetails",
    "TaskFailed": "taskFailedEventDetails",
    "TaskTimedOut": "taskTimedOutEventDetails",
    "TaskStartFailed": "taskStartFailedEventDetails",
    "TaskSubmitFailed": "taskSubmitFailedEventDetails",
    "ExecutionAborted": "executionAbortedEventDetails",
    "ExecutionFailed": "executionFailedEventDetails",
    "ExecutionTimedOut": "executionTimedOutEventDetails",
    "ExecutionSucceeded": "executionSucceededEventDetails",
    "ExecutionStarted": "executionStartedEventDetails",
}


@dataclass
class _Leitura:
    """O estado de UM arquivo sendo lido: onde, e o que ja saiu."""

    path: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _attempt_subject(path: str, simbolo: str) -> dict[str, Any]:
    subject = _file_subject(path)
    subject["symbol"] = simbolo
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


def _loads(texto: str) -> tuple[Any, str | None]:
    """(valor, None) ou (None, razao). Nunca levanta.

    Historico de execucao longa chega a megabytes, e o decodificador de JSON levanta
    `RecursionError` com aninhamento profundo e `MemoryError` com payload hostil. As
    tres formas de falha saem nomeadas, e nenhuma derruba quem chamou.
    """
    try:
        return json.loads(texto), None
    except RecursionError:
        return None, "json_too_deep"
    except MemoryError:
        return None, "json_too_large"
    except ValueError:  # inclui json.JSONDecodeError
        return None, "invalid_json"


def _instante(valor: Any) -> float | None:
    """Segundos desde a epoca, ou `None`. ISO 8601 e epoch, e nada mais.

    A CLI serializa `timestamp` como ISO 8601 com deslocamento; alguns dumps de SDK o
    gravam como numero. Milissegundo vira segundo pelo limiar de 1e11 -- qualquer
    epoch em SEGUNDOS ate o ano 5138 fica abaixo dele.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor) / 1000.0 if abs(valor) > 1e11 else float(valor)
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto).timestamp()
    except ValueError:
        return None


def _detalhes(evento: dict[str, Any]) -> dict[str, Any]:
    bloco = evento.get(_DETALHES_POR_TIPO.get(str(evento.get("type")), ""))
    return bloco if isinstance(bloco, dict) else {}


def _padrao(recurso: str) -> str:
    """`startJobRun.sync` -> sync; `.waitForTaskToken` -> callback; resto -> request_response.

    O historico publica `resourceType` (o servico) e `resource` (a API mais o sufixo)
    em campos SEPARADOS, e por isso aqui nao se parseia ARN nenhum -- diferente de
    `stepfunctions._parse_resource`, que le o `Resource` do ASL inteiro.
    """
    if ".waitForTaskToken" in recurso:
        return "callback"
    if ".sync" in recurso:
        return "sync"
    return "request_response"


def _ancestral(
    evento: dict[str, Any], por_id: dict[int, dict[str, Any]], tipos: frozenset[str]
) -> tuple[dict[str, Any] | None, str | None]:
    """O ancestral mais proximo, pela cadeia de `previousEventId`, cujo tipo esta em `tipos`.

    (evento, None), ou (None, razao). As razoes sao tres e diferentes de proposito:
    `chain_root` (a cadeia acabou sem achar), `chain_broken` (o id referenciado nao
    esta no arquivo -- historico truncado, ou pagina faltando) e `chain_cycle` (um
    arquivo montado a mao que se referencia). Confundi-las esconderia truncamento
    atras de "nao achei".
    """
    visitados: set[int] = set()
    atual = evento
    while True:
        anterior = atual.get("previousEventId")
        if isinstance(anterior, bool) or not isinstance(anterior, int) or anterior <= 0:
            return None, "chain_root"
        if anterior in visitados:
            return None, "chain_cycle"
        visitados.add(anterior)
        pai = por_id.get(anterior)
        if pai is None:
            return None, "chain_broken"
        if str(pai.get("type")) in tipos:
            return pai, None
        atual = pai


def _job_run(saida: Any) -> tuple[str | None, str | None, str | None, list[str]]:
    """(job_run_id, job_name, chave lida, chaves de topo). U1 mora aqui.

    A forma exata do `output` do `TaskSubmitted` do Glue NAO esta na pagina da API: a
    pagina de integracao so diz que o `JobName` e inserido na resposta. Por isso o
    extrator le defensivamente -- objeto, ou string com JSON dentro -- e tenta tres
    chaves, na ordem. O que nao casa sai nomeado COM as chaves de topo, porque e delas
    que um historico real fecha a lacuna.
    """
    if isinstance(saida, str):
        saida, _ = _loads(saida)
    if not isinstance(saida, dict):
        return None, None, None, []
    chaves = sorted(str(k) for k in saida)
    nome = saida.get("JobName")
    nome = nome if isinstance(nome, str) and nome.strip() else None
    for chave in ("JobRunId", "Id"):
        valor = saida.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor, nome, chave, chaves
    aninhado = saida.get("JobRun")
    if isinstance(aninhado, dict):
        valor = aninhado.get("Id")
        if isinstance(valor, str) and valor.strip():
            if nome is None and isinstance(aninhado.get("JobName"), str):
                nome = aninhado["JobName"]
            return valor, nome, "JobRun.Id", chaves
    return None, nome, None, chaves


def _eventos(payload: Any) -> tuple[list[Any] | None, bool, str | None, str]:
    """(eventos, truncado, arn, origem) ou (None, ...) quando nao e historico."""
    if isinstance(payload, list):
        return payload, False, None, "event_list"
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        return None, False, None, ""
    token = payload.get("nextToken")
    arn = payload.get("executionArn")
    return (
        payload["events"],
        bool(isinstance(token, str) and token.strip()),
        arn if isinstance(arn, str) and arn.strip() else None,
        "get_execution_history",
    )


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="sfn.analyzed",
            subject=_file_subject(path),
            measures={
                "execution_count": sum(1 for f in facts if f.kind == "sfn.execution"),
                "attempt_count": sum(1 for f in facts if f.kind == "sfn.attempt"),
                "job_run_count": sum(1 for f in facts if f.kind == "sfn.job_run"),
                "unresolved_count": sum(1 for f in facts if f.kind == "sfn.unresolved"),
            },
            attrs={"extractor": EXTRACTOR_ID},
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def _valida_eventos(brutos: list[Any], leitura: _Leitura) -> list[dict[str, Any]]:
    """Os eventos que sao objeto com `id` inteiro. O resto sai nomeado."""
    limpos: list[dict[str, Any]] = []
    for indice, bruto in enumerate(brutos):
        if not isinstance(bruto, dict):
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_not_an_object",
                    leitura.provenance,
                    index=indice,
                )
            )
            continue
        identificador = bruto.get("id")
        if isinstance(identificador, bool) or not isinstance(identificador, int):
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_not_an_object",
                    leitura.provenance,
                    index=indice,
                )
            )
            continue
        if str(bruto.get("type")) not in _TIPOS_CONHECIDOS:
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_type_unknown",
                    leitura.provenance,
                    type=str(bruto.get("type")),
                    event_id=identificador,
                )
            )
            continue
        limpos.append(bruto)
    return limpos


def _desfecho_da_execucao(eventos: list[dict[str, Any]]) -> tuple[str, str]:
    """(status, classe). `unresolved`/`unresolved` quando nao ha evento terminal."""
    for evento in reversed(eventos):
        status = _STATUS_POR_TIPO.get(str(evento.get("type")))
        if status is not None:
            return status, ("stopped" if status in _PARADA else "finished")
    return "unresolved", "unresolved"


def extract_sfn_history(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado: resposta da API, ou lista de eventos."""
    provenance = _provenance(path, artifact_sha256)
    brutos, truncado, arn, origem = _eventos(payload)
    if brutos is None:
        falha = _unresolved(_file_subject(path), "not_an_execution_history", provenance)
        return _finish([falha], path, provenance)

    leitura = _Leitura(path=path, provenance=provenance)
    eventos = _valida_eventos(brutos, leitura)
    por_id = {int(e["id"]): e for e in eventos}
    ordenados = sorted(eventos, key=lambda e: int(e["id"]))
    status, classe = _desfecho_da_execucao(ordenados)

    if truncado:
        leitura.facts.append(
            _unresolved(_file_subject(path), "truncated", provenance, read_events=len(ordenados))
        )
    if status == "unresolved" and ordenados:
        leitura.facts.append(
            _unresolved(_file_subject(path), "execution_terminal_absent", provenance)
        )

    # 1. Um agendamento -> uma tentativa. O estado vem da cadeia, nunca da ordem.
    tentativas: dict[int, dict[str, Any]] = {}
    ordem_por_estado: dict[str, int] = {}
    for evento in ordenados:
        if str(evento.get("type")) != "TaskScheduled":
            continue
        entrada, razao = _ancestral(evento, por_id, frozenset({"TaskStateEntered"}))
        nome = None
        if entrada is not None:
            detalhes = entrada.get("stateEnteredEventDetails")
            if isinstance(detalhes, dict) and isinstance(detalhes.get("name"), str):
                nome = detalhes["name"]
        if nome is None:
            leitura.facts.append(
                _unresolved(
                    _file_subject(path),
                    "state_unresolved",
                    provenance,
                    event_id=int(evento["id"]),
                    detail=razao or "state_name_absent",
                )
            )
            continue
        ordem_por_estado[nome] = ordem_por_estado.get(nome, 0) + 1
        tentativas[int(evento["id"])] = {
            "state_name": nome,
            "index": ordem_por_estado[nome],
            "scheduled": evento,
            "terminal": None,
            "submitted": None,
        }

    # 2. Terminal e submissao sobem ate o agendamento DELES.
    for evento in ordenados:
        tipo = str(evento.get("type"))
        if tipo not in _RESULTADO_POR_TIPO and tipo != "TaskSubmitted":
            continue
        agendamento, razao = _ancestral(evento, por_id, frozenset({"TaskScheduled"}))
        alvo = tentativas.get(int(agendamento["id"])) if agendamento is not None else None
        if alvo is None:
            leitura.facts.append(
                _unresolved(
                    _file_subject(path),
                    "attempt_unanchored",
                    provenance,
                    event_id=int(evento["id"]),
                    type=tipo,
                    detail=razao or "scheduled_not_an_attempt",
                )
            )
            continue
        if tipo == "TaskSubmitted":
            alvo["submitted"] = evento
        elif alvo["terminal"] is None:
            alvo["terminal"] = evento

    # 3. Os facts, em ordem de agendamento.
    for identificador in sorted(tentativas):
        estado = tentativas[identificador]
        leitura.facts.extend(_fatos_da_tentativa(estado, status, classe, leitura))

    inicio = _instante(ordenados[0].get("timestamp")) if ordenados else None
    fim = _instante(ordenados[-1].get("timestamp")) if ordenados else None
    medidas: dict[str, Any] = {
        "event_count": len(ordenados),
        "attempt_count": sum(1 for f in leitura.facts if f.kind == "sfn.attempt"),
        "job_run_count": sum(1 for f in leitura.facts if f.kind == "sfn.job_run"),
    }
    if inicio is not None and fim is not None:
        medidas["duration_seconds"] = round(fim - inicio, 3)
    atributos: dict[str, Any] = {
        "status": status,
        "status_class": classe,
        "source": origem,
        "truncated": truncado,
        "arn_declared": arn is not None,
    }
    if arn is not None:
        atributos["arn"] = arn
    leitura.facts.append(
        Fact(
            kind="sfn.execution",
            subject=_file_subject(path),
            measures=medidas,
            attrs=atributos,
            provenance=provenance,
        )
    )
    return _finish(leitura.facts, path, provenance)


def _fatos_da_tentativa(
    estado: dict[str, Any], status: str, classe: str, leitura: _Leitura
) -> list[Fact]:
    """O `sfn.attempt` e, quando o `output` o sustenta, o `sfn.job_run` dele."""
    agendamento = estado["scheduled"]
    detalhes = _detalhes(agendamento)
    recurso = detalhes.get("resource")
    recurso = recurso if isinstance(recurso, str) else ""
    servico = detalhes.get("resourceType")
    servico = servico if isinstance(servico, str) else ""
    padrao = _padrao(recurso)
    simbolo = f"{estado['state_name']}#{estado['index']}"
    subject = _attempt_subject(leitura.path, simbolo)

    terminal = estado["terminal"]
    resultado = _RESULTADO_POR_TIPO.get(str(terminal.get("type"))) if terminal else None
    detalhes_terminais = _detalhes(terminal) if terminal else {}
    submetido = estado["submitted"]

    atributos: dict[str, Any] = {
        "state_name": estado["state_name"],
        "service": servico,
        "api": recurso.split(".", 1)[0],
        "resource": recurso,
        "pattern": padrao,
        "result": resultado or "none",
        "terminal_present": terminal is not None,
        "submitted": submetido is not None,
        "execution_outcome": status,
        "execution_outcome_class": classe,
        "job_run_outcome_observed": bool(
            padrao == "sync" and resultado in _OBSERVA_O_JOB_RUN
        ),
    }
    for campo in ("error", "cause"):
        valor = detalhes_terminais.get(campo)
        if isinstance(valor, str) and valor:
            atributos[campo] = valor

    medidas: dict[str, Any] = {"attempt_index": estado["index"]}
    inicio = _instante(agendamento.get("timestamp"))
    fim = _instante(terminal.get("timestamp")) if terminal else None
    if inicio is not None and fim is not None:
        medidas["duration_seconds"] = round(fim - inicio, 3)
    limite = detalhes.get("timeoutInSeconds")
    if isinstance(limite, int) and not isinstance(limite, bool):
        medidas["timeout_seconds"] = limite

    saida: list[Fact] = [
        Fact(
            kind="sfn.attempt",
            subject=subject,
            measures=medidas,
            attrs=atributos,
            provenance=leitura.provenance,
        )
    ]
    if submetido is None:
        return saida
    bruto = _detalhes(submetido)
    if "output" not in bruto:
        saida.append(
            _unresolved(
                dict(subject),
                "execution_data_absent",
                leitura.provenance,
                state_name=estado["state_name"],
            )
        )
        return saida
    corrida, nome, chave, chaves = _job_run(bruto["output"])
    if corrida is None:
        saida.append(
            _unresolved(
                dict(subject),
                "job_run_id_unrecognized",
                leitura.provenance,
                state_name=estado["state_name"],
                output_keys=chaves,
            )
        )
        return saida
    saida.append(
        Fact(
            kind="sfn.job_run",
            subject=dict(subject),
            measures={"attempt_index": estado["index"]},
            attrs={
                "job_run_id": corrida,
                "job_name": nome,
                "state_name": estado["state_name"],
                "read_from": chave,
                "source": "task_submitted_output",
            },
            provenance=leitura.provenance,
        )
    )
    return saida


def extract_sfn_history_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `sfn.unresolved` com `read_error`; arquivo acima do teto de
    `scan._teto_para` (o mesmo que a varredura aplica), `size_above_limit` -- e ele
    importa mais aqui do que no ASL, porque historico de execucao longa chega a
    megabytes. Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        tamanho, teto = path.stat().st_size, scan._teto_para(path)
        if tamanho > teto:
            falha = _unresolved(
                _file_subject(anchor), "size_above_limit", vazio, size=tamanho, limit=teto
            )
            return _finish([falha], anchor, vazio)
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = _provenance(anchor, sha)
    parsed, razao = _loads(text)
    if razao is not None:
        falha = _unresolved(_file_subject(anchor), razao, provenance)
        return _finish([falha], anchor, provenance)
    return extract_sfn_history(parsed, anchor, artifact_sha256=sha)


def extract_sfn_history_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: vira `sfn.unresolved` daquele arquivo e a travessia
    continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.json"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_sfn_history_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_sfn_history",
    "extract_sfn_history_path",
    "extract_sfn_history_tree",
]
```

Nota de implementação, e o motivo de `_loads` ter quatro saídas: o `json_too_large` de
`MemoryError` **não** está na lista de razões do docstring do módulo por engano — ele
está; se o `ruff` ou uma releitura apontar divergência entre a lista do docstring e as
razões que o código emite, a lista do docstring é que se corrige, nunca o contrário.

### 4. Rodar e ver passar

```bash
git add sparkforge/facts/sfn_history.py
python -m pytest tests/test_sfn_history.py -q
```

Três testes verdes — AC1, AC2 e AC3.

### 5. Gates vizinhos

Extrator (`docs/gates-por-mudanca.md`, "Acrescentar ou alterar um EXTRATOR de facts") —
o módulo ainda **NÃO** entra nas duas listas manuais: entra em T3, no mesmo commit do
golden.

```bash
python -m ruff check sparkforge/facts/sfn_history.py tests/test_sfn_history.py
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_facts_scan.py tests/test_harness_untrusted.py tests/test_databricks_rule_audit.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py -q
```

`test_harness_untrusted.py` roda `extract_sfn_history_tree` sobre todo domínio de
`fixtures/` (a medida de snippet): o módulo tem `*_tree`, então é exercitado sem entrada
em `_derivados_de_facts`, e nenhum fact dele carrega `snippet` — o `subject` é sempre
`_file_subject`, com `snippet` vazio.

Números (tabela *Números correntes* e prosa auditada). `docs/superpowers/STATUS.md`,
duas trocas de prefixo de linha (o resto de cada linha fica como está). Antes → depois:

```text
| Extratores de facts | **39** —
| Extratores de facts | **40** — `sfn_history.py` é o quadragésimo (2026-09-20, feature `docs/sdd/SFN_HISTORY/`): o primeiro que lê o que ACONTECEU numa state machine, o histórico de execução do AWS Step Functions. Leitura anterior de **39** —
```

```text
| Fact kinds distintos emitidos | **233** —
| Fact kinds distintos emitidos | **236** — os TRÊS do extrator de histórico (2026-09-20, feature `docs/sdd/SFN_HISTORY/`): `sfn.execution`, `sfn.attempt` e `sfn.job_run`. São três e não cinco porque `sfn.unresolved` e `sfn.analyzed` já existiam — o extrator do histórico compartilha o prefixo `sfn.` com o do ASL de propósito (D1), e o kind é que diz a natureza: `sfn.task` é declaração, `sfn.attempt` é medida. Leitura anterior de **233** —
```

- `README.md` linha 44: `Os 39 extratores emitem 233 kinds distintos` →
  `Os 40 extratores emitem 236 kinds distintos`.
- `docs/guia/06-extrair-julgar-compor.md`: linha 86,
  `Os 39 extratores emitem 233 kinds distintos de fact (recontado em 2026-09-19),` →
  `Os 40 extratores emitem 236 kinds distintos de fact (recontado em 2026-09-20),`;
  linha 232, `nenhum dos 233 kinds a nomeia` → `nenhum dos 236 kinds a nomeia`.

```bash
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

O gate de lastro reprova as alegações de corpus de `.py` (dois arquivos novos: 756 →
758). Medido em entregas anteriores, os ids que costumam cair são `VNX-640`, `VNX-644`,
`VNX-667`, `VNX-670` e `VNX-674` em `docs/harness/CODEINTEL-GAP.md` — **mas a lista da
saída do gate é que manda**: no AIRFLOW_DAG o gate acusou oito, e dois dos citados no
plano não estavam entre eles. Remedie pelos ids que a saída listar, número no documento
e em `docs/claims.lock.json` (`expect.value` **int** em `kind: number`), e rode o gate de
novo até `exit 0`.

### 6. Commit

`feat(facts): read AWS Step Functions execution history into sfn.* facts`

Arquivos: `sparkforge/facts/sfn_history.py`, `tests/test_sfn_history.py`,
`docs/superpowers/STATUS.md`, `README.md`, `docs/guia/06-extrair-julgar-compor.md`,
`docs/harness/CODEINTEL-GAP.md`, `docs/claims.lock.json`.

## T2 — verbo `analyze sfn-history` e tool `sparkforge_analyze_sfn_history`

### 1. Teste que falha

Acrescente ao fim de `tests/test_sfn_history.py`:

```python
def test_cli_e_tool_devolvem_os_mesmos_facts(tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    entrada = tmp_path / "entrada"
    entrada.mkdir()
    (entrada / "execucao.json").write_text(
        json.dumps(HISTORICO_COM_TRES_TENTATIVAS), encoding="utf-8"
    )
    saida = tmp_path / "facts.json"

    codigo = main(["analyze", "sfn-history", "--path", str(entrada), "--out", str(saida)])
    capsys.readouterr()
    assert codigo == 0
    pela_cli = json.loads(saida.read_text(encoding="utf-8"))

    pela_tool = call_tool("sparkforge_analyze_sfn_history", {"path": str(entrada), "limit": 1000})
    assert "error" not in pela_tool, pela_tool
    assert pela_tool["total_count"] == len(pela_cli)
    assert pela_tool["items"] == pela_cli
    assert pela_tool["by_kind"]["sfn.attempt"] == 3
    assert pela_tool["by_kind"]["sfn.job_run"] == 3
    assert pela_tool["unresolved"] == 0

    erro = call_tool("sparkforge_analyze_sfn_history", {"path": str(tmp_path / "nao-existe")})
    assert "sparkforge analyze sfn-history" in erro["error"]
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_sfn_history.py::test_cli_e_tool_devolvem_os_mesmos_facts -q
```

Falha esperada: `SystemExit: 2` do argparse (`invalid choice: 'sfn-history'`).

### 3. Código mínimo

**`sparkforge/adapters/_core.py`** — import. Troque

```python
from sparkforge.facts.s3_listing import extract_s3_listing_path, extract_s3_listing_tree
from sparkforge.facts.spark_plan import extract_plan_path
```

por

```python
from sparkforge.facts.s3_listing import extract_s3_listing_path, extract_s3_listing_tree
from sparkforge.facts.sfn_history import (
    extract_sfn_history_path,
    extract_sfn_history_tree,
)
from sparkforge.facts.spark_plan import extract_plan_path
```

E a função pública, logo depois da de Step Functions. Troque

```python
    facts = _extract_step_functions_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)
```

por

```python
    facts = _extract_step_functions_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze sfn-history
# --------------------------------------------------------------------------- #
#
# Le o HISTORICO de execucao -- a saida salva de `aws stepfunctions
# get-execution-history` -- e nunca a definicao. O par dele e
# `analyze step-functions`, que le a definicao: um diz o que DEVIA acontecer, o
# outro o que ACONTECEU, e o `fuse` confronta os dois.
#
# Nao ha `collect` par (D3 de `docs/sdd/SFN_HISTORY/design.md`): a chamada exige
# credencial, e o operador salva a saida em arquivo. A API nao suporta EXPRESS.


def _extract_sfn_history_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o JSON salvo de `aws stepfunctions get-execution-history`,\n"
            f"  ou para o diretorio com eles:\n"
            f"    sparkforge analyze sfn-history --path historicos/ "
            f"--out .sparkforge/facts_sfn_history.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_sfn_history_tree(target, repo_root=target)
    return extract_sfn_history_path(target, repo_root=target.parent)


def analyze_sfn_history(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_sfn_history_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)
```

**`sparkforge/adapters/cli.py`** — subcomando. Troque

```python
    _add_detail_level(sfn_analyze_p)

    dq_p = analyze_sub.add_parser(
```

por

```python
    _add_detail_level(sfn_analyze_p)

    sfnh_analyze_p = analyze_sub.add_parser(
        "sfn-history",
        help="Extrai facts do HISTORICO de execucao de uma state machine do AWS Step "
        "Functions (a saida salva de `aws stepfunctions get-execution-history`): uma "
        "tentativa por par TaskScheduled/terminal, com ordem, resultado, duracao, erro "
        "e o JobRunId do Glue lido do output do TaskSubmitted. Le o que ACONTECEU, "
        "nunca a definicao.",
    )
    sfnh_analyze_p.add_argument(
        "--path",
        required=True,
        help="Arquivo .json salvo de get-execution-history, ou diretorio com eles.",
    )
    sfnh_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    sfnh_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sfnh_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sfnh_analyze_p.add_argument("--cursor")
    _add_detail_level(sfnh_analyze_p)

    dq_p = analyze_sub.add_parser(
```

Handler: troque

```python
def _cmd_analyze_step_functions(args: argparse.Namespace) -> int:
    full = _core.analyze_step_functions(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)
```

por

```python
def _cmd_analyze_step_functions(args: argparse.Namespace) -> int:
    full = _core.analyze_step_functions(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_sfn_history(args: argparse.Namespace) -> int:
    full = _core.analyze_sfn_history(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)
```

Despacho: troque

```python
    ("analyze", "step-functions"): _cmd_analyze_step_functions,
```

por

```python
    ("analyze", "step-functions"): _cmd_analyze_step_functions,
    ("analyze", "sfn-history"): _cmd_analyze_sfn_history,
```

**`sparkforge/adapters/tools.py`** — declaração. O bloco novo entra **imediatamente
antes** da linha `    "sparkforge_analyze_step_functions": {` do dicionário `TOOLS` (é a
única ocorrência dela ali). Troque

```python
    "sparkforge_analyze_step_functions": {
        "description": (
```

por

```python
    "sparkforge_analyze_sfn_history": {
        "description": (
            "Extrai facts do HISTORICO de execucao de uma state machine do AWS Step "
            "Functions: a saida salva de `aws stepfunctions get-execution-history` (o "
            "objeto de resposta com `events`, ou a lista crua de eventos). Emite "
            "`sfn.execution` (status pelo evento terminal -- `unresolved` quando ele nao "
            "esta no arquivo, NUNCA sucesso por suposicao --, duracao e contagem de "
            "eventos), um `sfn.attempt` por TENTATIVA de Task (nome do estado pela cadeia "
            "de `previousEventId`, ordem, padrao de integracao, resultado, duracao, erro e "
            "cause), `sfn.job_run` com o JobRunId do Glue lido do `output` do "
            "TaskSubmitted, `sfn.unresolved` com a razao do que nao deu para ler ou parear "
            "(historico truncado, cadeia quebrada, evento de tipo desconhecido, "
            "`includeExecutionData` desligado, output de forma nao reconhecida), e a "
            "sentinela `sfn.analyzed`. NAO chama a API e NAO le a definicao: para a "
            "definicao ASL, use `sparkforge_analyze_step_functions`. A API nao suporta "
            "state machine EXPRESS. Nao atribui custo a tentativa nenhuma."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Arquivo .json salvo de get-execution-history, ou diretorio com eles."
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
    "sparkforge_analyze_step_functions": {
        "description": (
```

Handler: troque

```python
def _h_analyze_step_functions(args: dict[str, Any]) -> dict[str, Any]:
```

por

```python
def _h_analyze_sfn_history(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_sfn_history(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )


def _h_analyze_step_functions(args: dict[str, Any]) -> dict[str, Any]:
```

Despacho: troque

```python
    "sparkforge_analyze_step_functions": _h_analyze_step_functions,
```

por

```python
    "sparkforge_analyze_step_functions": _h_analyze_step_functions,
    "sparkforge_analyze_sfn_history": _h_analyze_sfn_history,
```

**Registros da superfície, no mesmo commit:**

`tests/test_adapters_tools.py`:

- lista literal de `TestToolSurface`: troque

```python
            "sparkforge_analyze_step_functions",
            "sparkforge_analyze_data_quality",
```

por

```python
            "sparkforge_analyze_step_functions",
            "sparkforge_analyze_sfn_history",
            "sparkforge_analyze_data_quality",
```

- amostra real: troque `_CONSUMER_INVENTORY = """consumers:` por

```python
# Historico com UMA tentativa de Glue `.sync` que falhou, com o JobRunId no output do
# TaskSubmitted: rende `sfn.attempt` e `sfn.job_run` com os campos que as regras
# SF-SFNX leem, e nao so a sentinela que sai de qualquer `.json`.
_SFN_HISTORY_EVENTS = [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T03:00:00+00:00", "type": "ExecutionStarted"},
    {
        "id": 2,
        "previousEventId": 1,
        "timestamp": "2026-09-18T03:00:01+00:00",
        "type": "TaskStateEntered",
        "stateEnteredEventDetails": {"name": "CargaDiaria"},
    },
    {
        "id": 3,
        "previousEventId": 2,
        "timestamp": "2026-09-18T03:00:02+00:00",
        "type": "TaskScheduled",
        "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"},
    },
    {
        "id": 4,
        "previousEventId": 3,
        "timestamp": "2026-09-18T03:00:03+00:00",
        "type": "TaskSubmitted",
        "taskSubmittedEventDetails": {
            "resource": "startJobRun.sync",
            "resourceType": "glue",
            "output": json.dumps({"JobRunId": "jr_amostra"}),
        },
    },
    {
        "id": 5,
        "previousEventId": 4,
        "timestamp": "2026-09-18T03:00:30+00:00",
        "type": "TaskFailed",
        "taskFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "FAILED"},
    },
    {
        "id": 6,
        "previousEventId": 5,
        "timestamp": "2026-09-18T03:00:31+00:00",
        "type": "ExecutionFailed",
        "executionFailedEventDetails": {"error": "Glue.AWSGlueException"},
    },
]
_SFN_EXECUTION_HISTORY = json.dumps({"events": _SFN_HISTORY_EVENTS})

_CONSUMER_INVENTORY = """consumers:
```

- construtor de `_real_output_for`: troque `    if name == "sparkforge_analyze_step_functions":` por

```python
    if name == "sparkforge_analyze_sfn_history":
        sfnh_path = tmp_path / "execucao.json"
        sfnh_path.write_text(_SFN_EXECUTION_HISTORY, encoding="utf-8")
        resultado = call_tool("sparkforge_analyze_sfn_history", {"path": str(sfnh_path)})
        assert resultado["by_kind"].get("sfn.attempt") == 1, resultado["by_kind"]
        assert resultado["by_kind"].get("sfn.job_run") == 1, resultado["by_kind"]
        return resultado

    if name == "sparkforge_analyze_step_functions":
```

- `FAILABLE`: troque

```python
        ("sparkforge_analyze_step_functions", {"path": "<tmp>/inexistente"}),
```

por

```python
        ("sparkforge_analyze_step_functions", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_sfn_history", {"path": "<tmp>/inexistente"}),
```

`tests/test_harness_authorization.py`: troque

```python
        # 98 -> 99 com `analyze_step_functions` (2026-09-19, `docs/sdd/STEP_FUNCTIONS/`):
        # `_READ_ONLY`, le a definicao ASL em disco e declara `path`.
        assert len(TOOLS) - len(sem_caminho) == 99
```

por

```python
        # 98 -> 99 com `analyze_step_functions` (2026-09-19, `docs/sdd/STEP_FUNCTIONS/`):
        # `_READ_ONLY`, le a definicao ASL em disco e declara `path`.
        # 99 -> 100 com `analyze_sfn_history` (2026-09-20, `docs/sdd/SFN_HISTORY/`):
        # `_READ_ONLY`, le o historico de execucao salvo em disco e declara `path`.
        assert len(TOOLS) - len(sem_caminho) == 100
```

`parity.yaml`: logo depois do bloco `- name: extract facts from an AWS Step Functions
state machine definition` (termina em `copilot_ci: [cli, files]`, antes de
`- name: diff component versions between two runtime releases`), acrescente:

```yaml
  # O HISTORICO de execucao e o par da capacidade acima, e a diferenca e de natureza: a
  # definicao diz o que DEVIA acontecer, o historico diz o que ACONTECEU. NAO HA
  # `collect` PAR neste incremento, e a ausencia e decidida (D3 de
  # `docs/sdd/SFN_HISTORY/design.md`): a chamada exige credencial, e a API nao suporta
  # state machine EXPRESS.
  - name: extract facts from an AWS Step Functions execution history
    tools: [sparkforge_analyze_sfn_history]
    cli: [analyze sfn-history]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]

```

(O bloco `knowledge:` desta capacidade entra em T4, quando o documento existir.)

`manifest.json`: troque

```json
    "sparkforge_analyze_s3_listing",
```

por

```json
    "sparkforge_analyze_s3_listing",
    "sparkforge_analyze_sfn_history",
```

(A lista é alfabética: `s3_listing` < `sfn_history` < `sql`.)

`agents/glue-infra-reviewer.md` (senão `test_no_tool_is_orphan` reprova). Troque

```markdown
## Três armadilhas que a infraestrutura esconde
```

por

```markdown
### E o que aconteceu de verdade: o histórico de execução

A definição diz quantas vezes o job **pode** ser reagendado; só o histórico diz quantas
vezes ele **foi**. `sparkforge_analyze_sfn_history` lê a saída salva de `aws
stepfunctions get-execution-history` e devolve um `sfn.attempt` por tentativa de Task —
nome do estado, ordem, resultado, duração, erro e `cause` — e um `sfn.job_run` com o
`JobRunId` que cada tentativa produziu. Com a definição ASL no mesmo case, `fuse`
confronta os dois e emite `sfn.retry_observado`: tentativas observadas contra o teto
declarado. O histórico não traz custo, e nenhum achado o atribui — o que ele traz é o
`JobRunId`, que é por onde `sparkforge_finops` responde custo com `dpu_seconds` medido.

A API **não** suporta state machine EXPRESS, e o histórico dela vai para o CloudWatch
Logs: nesse caso, `sparkforge_analyze_cloudwatch_logs`.

## Três armadilhas que a infraestrutura esconde
```

E a `description` do frontmatter — **sem `: `, que quebra o YAML** (armadilha paga na
revisão final do AIRFLOW_DAG). Troque

```yaml
description: Gargalo ou risco na definicao do job Glue e nao no codigo - worker type e numero, auto scaling, bookmark, retries, argumentos de job, observabilidade, Terraform, e como a state machine do Step Functions dispara o job.
```

por

```yaml
description: Gargalo ou risco na definicao do job Glue e nao no codigo - worker type e numero, auto scaling, bookmark, retries, argumentos de job, observabilidade, Terraform, e como a state machine do Step Functions dispara o job - a definicao ASL e o historico de execucao, que diz quantas vezes o job rodou de verdade.
```

Espelhos: backup do `.claude/agents/README.md`, `python scripts/sync_skills.py`, devolva o
README. E à mão, `.codex/agents/glue-infra-reviewer.toml`: a mesma seção, no mesmo lugar
do `developer_instructions` (antes da linha `## Três armadilhas que a infraestrutura
esconde`), e a mesma `description`.

`docs/guia/06-extrair-julgar-compor.md`, tabela de verbos: troque a linha 115 (a que começa
com `| **Definição ASL do AWS Step Functions** |`) por ela mesma seguida desta linha nova:

```markdown
| **Histórico de execução do AWS Step Functions** | `analyze sfn-history` | a saída salva de `aws stepfunctions get-execution-history`: uma tentativa por par `TaskScheduled`/terminal, com ordem, resultado, duração e o `JobRunId` do Glue. Com o ASL do mesmo state machine no pool, `fuse` confronta o retry declarado com o observado |
```

`tests/test_fixtures_golden_mcp_parity.py`: o SDK `mcp` 2.2.0 está instalado nesta
máquina, então `test_toda_tool_nova_esta_declarada` roda. Troque

```python
    "sparkforge_analyze_step_functions": "2026-09-19: definicao ASL do AWS Step Functions",
}
```

por

```python
    "sparkforge_analyze_step_functions": "2026-09-19: definicao ASL do AWS Step Functions",
    "sparkforge_analyze_sfn_history": "2026-09-20: historico de execucao do AWS Step Functions",
}
```

Referência e superfície:

```bash
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
```

O primeiro reescreve `docs/guia/referencia/tools/README.md`, cria
`docs/guia/referencia/tools/sparkforge_analyze_sfn_history.md`, e reescreve também
`docs/guia/referencia/cli/analyze.md` e
`docs/guia/referencia/agents/glue-infra-reviewer.md`. O segundo imprime o crescimento em
bytes: copie-o para o corpo do commit (regra 26).

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_sfn_history.py -q
python -m pytest tests/test_adapters_tools.py -q
```

### 5. Gates vizinhos

"Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada" e
"Alterar agent, skill ou seus espelhos", **um comando por vez**:

```bash
python -m pytest tests/test_reference_docs.py tests/test_surface_lock.py -q
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q
python -m pytest tests/test_router_agents.py -q
python -m pytest tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_adapters_code_surface.py tests/test_mcp_modern_era.py -q
python -m pytest tests/test_fixtures_golden_mcp_parity.py -q
python -m ruff check sparkforge/adapters tests/test_sfn_history.py tests/test_adapters_tools.py tests/test_harness_authorization.py
```

(backup e devolução do `.claude/agents/README.md` em volta do sync e de
`test_agents_parity.py`.)

`test_router_agents.py` está nesta lista **por causa da `description`**: ela é parseada
como frontmatter YAML, e um `: ` dentro dela derruba 29 parametrizações de uma vez. Se o
teste ficar vermelho com erro de YAML, é a `description` — não a rota.

Números. `docs/superpowers/STATUS.md`, antes → depois:

```text
| Tools MCP | **107** —
| Tools MCP | **108** — a **108ª** é `sparkforge_analyze_sfn_history` (2026-09-20, feature `docs/sdd/SFN_HISTORY/`): lê o histórico de execução do AWS Step Functions, é `_READ_ONLY` e declara `path`. Leitura anterior de **107** —
```

`README.md` linha 111: `**107 tools MCP**` → `**108 tools MCP**`.

Prosa que `check_status_numbers.py` audita:

- `GUIA_DE_USO.md`: `as 107 tools fazem (recontado em 2026-09-19)` →
  `as 108 tools fazem (recontado em 2026-09-20)`;
- `.devin/README.md`: `**107 tools** por stdio (recontado em 2026-09-19)` →
  `**108 tools** por stdio (recontado em 2026-09-20)`;
- `AGENTS.md`: ``**107 tools, 39 with `detail_level`** (recounted 2026-09-19)`` →
  ``**108 tools, 40 with `detail_level`** (recounted 2026-09-20)``;
- `CLAUDE.md`: ``**107 tools, 39 com `detail_level`** (recontado em 2026-09-19)`` →
  ``**108 tools, 40 com `detail_level`** (recontado em 2026-09-20)``. A tool nova aceita
  `detail_level`, e a medida é por assinatura (`_tools_com_detail_level`).

```bash
python scripts/check_status_numbers.py --strict
python -m pytest tests/test_status_numbers_gate.py tests/test_bootstrap_budget.py -q
python scripts/check_vnext_claims.py
```

`len(TOOLS)` move alegações de `docs/harness/`: nesta árvore, `AUTHORIZATION-CHAIN.md`
(107 tools, 99 de 107), `CURRENT-HARNESS-GAP.md` e `CODEINTEL-GAP.md` (`detail_level` em
N das 107). **Duas alegações podem estar na mesma linha** (medido no AIRFLOW_DAG, em
`CURRENT-HARNESS-GAP.md`): remedie pelos ids da saída do gate — número no documento e no
`docs/claims.lock.json` — até `exit 0`, e nunca por varredura do texto `107`.

### 6. Commit

`feat(cli,mcp): add the analyze sfn-history verb and its MCP tool`, com o crescimento
da superfície em bytes no corpo.

## T3 — a área `SF-SFNX`: três regras, a derivação em `fuse`, a rota, o corpus e o golden

### 1. Testes que falham, e o corpus

**1a.** Acrescente ao fim de `tests/test_sfn_history.py`:

```python
ASL_COM_RETRY_DE_UMA = {
    "StartAt": "CargaDiaria",
    "States": {
        "CargaDiaria": {
            "Type": "Task",
            "Resource": "arn:aws:states:::glue:startJobRun.sync",
            "Parameters": {"JobName": "carga-diaria"},
            "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}],
            "End": True,
        }
    },
}


def test_fuse_confronta_o_retry_declarado_com_o_observado(tmp_path):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.stepfunctions import extract_stepfunctions

    historico = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_UMA, "carga.asl.json")

    fundidos = fuse([definicao, historico])
    [confronto] = [f for f in fundidos if f.kind == "sfn.retry_observado"]
    assert confronto.subject["symbol"] == "CargaDiaria"
    assert confronto.measures == {"tentativas_observadas": 3, "teto_declarado": 2}
    assert confronto.attrs["state_name"] == "CargaDiaria"
    assert confronto.attrs["job_name"] == "carga-diaria"
    assert confronto.attrs["pattern"] == "sync"
    assert confronto.attrs["declared_retry_defaulted"] is False
    # A proveniencia liga o confronto as tres tentativas E ao `sfn.task`: sem isso, o
    # achado citaria um fact que ninguem consegue reencontrar.
    derivados = set(confronto.provenance["derived_from"])
    assert derivados == {f.id for f in historico if f.kind == "sfn.attempt"} | {
        f.id for f in definicao if f.kind == "sfn.task"
    }

    # Sem o ASL no pool, nenhum confronto e a lacuna sai nomeada.
    so_historico = fuse([historico])
    assert not [f for f in so_historico if f.kind == "sfn.retry_observado"]
    motivos = {
        f.attrs["reason"] for f in so_historico if f.kind == "sfn.unresolved"
    }
    assert "asl_absent" in motivos

    # ASL presente, estado com OUTRO nome: perguntou-se e nao bateu, que e diferente
    # de nao ter perguntado.
    outro = extract_stepfunctions(
        {
            "StartAt": "CargaMensal",
            "States": {
                "CargaMensal": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {"JobName": "carga-mensal"},
                    "End": True,
                }
            },
        },
        "mensal.asl.json",
    )
    fundidos = fuse([outro, historico])
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    motivos = {f.attrs["reason"] for f in fundidos if f.kind == "sfn.unresolved"}
    assert "state_name_absent_in_asl" in motivos

    # Dois estados de MESMO nome em ramos de um Parallel: o historico so sabe o nome,
    # e escolher um seria chutar.
    ambiguo = extract_stepfunctions(
        {
            "StartAt": "Cargas",
            "States": {
                "Cargas": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "CargaDiaria",
                            "States": {
                                "CargaDiaria": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                                    "Parameters": {"JobName": "carga-diaria"},
                                    "End": True,
                                }
                            },
                        },
                        {
                            "StartAt": "CargaDiaria",
                            "States": {
                                "CargaDiaria": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                                    "Parameters": {"JobName": "carga-diaria-bis"},
                                    "End": True,
                                }
                            },
                        },
                    ],
                    "End": True,
                }
            },
        },
        "ambiguo.asl.json",
    )
    fundidos = fuse([ambiguo, historico])
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    [falha] = [
        f
        for f in fundidos
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "state_name_ambiguous"
    ]
    assert falha.attrs["declared_count"] == 2
```

**1b.** `tests/test_fixtures_golden_sfn_history.py` (arquivo novo, inteiro):

```python
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
```

**1c. O corpus.** Dez fixtures em `fixtures/sfn_history/<caso>/`, cada uma com
`meta.yaml` e `input/`. O `expected/` de cada uma sai do `regen`, nunca da mão.

O `runtime` das dez é o mesmo, e é o do corpus de `fixtures/stepfunctions/`:

```yaml
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
```

Abaixo, o conteúdo de cada arquivo. Os `timestamp` são ISO 8601 com deslocamento, que é
como a CLI da AWS os serializa.

---

**`fixtures/sfn_history/retry_acima_do_declarado/input/definicao/carga.asl.json`**

```json
{
  "Comment": "Carga diaria com UMA tentativa extra declarada: teto efetivo de duas.",
  "StartAt": "CargaDiaria",
  "States": {
    "CargaDiaria": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {"JobName": "carga-diaria"},
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}],
      "End": true
    }
  }
}
```

**`fixtures/sfn_history/retry_acima_do_declarado/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T03:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T03:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T03:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T03:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T03:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_aaaaaaaa1\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T03:12:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_aaaaaaaa1 FAILED"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T03:12:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T03:12:02.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T03:12:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_aaaaaaaa2\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T03:24:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_aaaaaaaa2 FAILED"}},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T03:24:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T03:24:02.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 13, "previousEventId": 12, "timestamp": "2026-09-18T03:24:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_aaaaaaaa3\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 14, "previousEventId": 13, "timestamp": "2026-09-18T03:36:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_aaaaaaaa3 FAILED"}},
    {"id": 15, "previousEventId": 14, "timestamp": "2026-09-18T03:36:01.000000+00:00", "type": "ExecutionFailed", "executionFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_aaaaaaaa3 FAILED"}}
  ]
}
```

**`fixtures/sfn_history/retry_acima_do_declarado/meta.yaml`**

```yaml
name: retry_acima_do_declarado
proves: >
  O POSITIVO de SF-SFNX-001. O ASL declara um retrier com `MaxAttempts: 1` sobre
  `States.TaskFailed` -- teto efetivo de DUAS execucoes do Task --, e o historico
  registra TRES agendamentos do mesmo estado, cada um com um JobRun proprio. O
  confronto e derivado em `fuse`, como `bridge.py` faz entre codigo e execucao.
  SF-SFN-002 dispara junto, pelo lado da definicao, e deve: o retrier reexecuta o job
  inteiro. Nenhum achado atribui custo (regra 13) -- o que fica no fact e o JobRunId.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.retry_observado
  - sfn.state_machine
  - sfn.task
expects_rules: [SF-SFN-002, SF-SFNX-001]
```

---

**`fixtures/sfn_history/retry_dentro_do_declarado/input/definicao/carga.asl.json`**

Idêntico ao de `retry_acima_do_declarado` (o mesmo teto declarado de duas).

**`fixtures/sfn_history/retry_dentro_do_declarado/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T03:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T03:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T03:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T03:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T03:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_bbbbbbbb1\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T03:12:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "Glue.AWSGlueException", "cause": "JobRun jr_bbbbbbbb1 FAILED"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T03:12:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T03:12:02.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T03:12:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_bbbbbbbb2\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T03:23:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T03:23:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaDiaria"}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T03:23:02.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

**`fixtures/sfn_history/retry_dentro_do_declarado/meta.yaml`**

```yaml
name: retry_dentro_do_declarado
proves: >
  A FRONTEIRA de SF-SFNX-001, e o negativo dela. Duas tentativas observadas contra um
  teto declarado de duas: o retry fez exatamente o que a definicao permite, e a regra
  fica calada. E esta igualdade que faz a troca de `>` por `>=` na `expr` mudar este
  golden -- por isso a area NAO precisa de entrada em `FRONTEIRA_SEM_GOLDEN`.
  SF-SFN-002 dispara pelo lado da definicao, que e o mesmo ASL da fixture anterior.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.retry_observado
  - sfn.state_machine
  - sfn.task
expects_rules: [SF-SFN-002]
```

---

**`fixtures/sfn_history/task_timed_out_sync/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T04:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T04:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaHoraria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T04:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 900}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T04:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T04:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_cccccccc1\", \"JobName\": \"carga-horaria\"}"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T04:15:02.000000+00:00", "type": "TaskTimedOut", "taskTimedOutEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "error": "States.Timeout", "cause": "Task timed out after 900 seconds"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T04:15:03.000000+00:00", "type": "ExecutionFailed", "executionFailedEventDetails": {"error": "States.Timeout", "cause": "Task timed out"}}
  ]
}
```

**`fixtures/sfn_history/task_timed_out_sync/meta.yaml`**

```yaml
name: task_timed_out_sync
proves: >
  O POSITIVO de SF-SFNX-002. O Task `.sync` expirou pelo proprio `TimeoutSeconds` (900
  medidos no `taskScheduledEventDetails`), e o historico NAO registra o fim do JobRun
  `jr_cccccccc1` que ele acompanhava: `job_run_outcome_observed` e falso. A execucao
  terminou em `ExecutionFailed`, entao `execution_outcome_class` e `finished` e a
  SF-SFNX-003 fica calada -- as duas nao se sobrepoem. Sem ASL no case: o confronto de
  retry nao acontece, e a lacuna sai nomeada em `asl_absent`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: [SF-SFNX-002]
```

---

**`fixtures/sfn_history/execucao_abortada_com_task_em_voo/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T05:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T05:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaNoturna"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T05:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 7200}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T05:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T05:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_dddddddd1\", \"JobName\": \"carga-noturna\"}"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T05:40:00.000000+00:00", "type": "ExecutionAborted", "executionAbortedEventDetails": {"error": "OperadorParou", "cause": "stop-execution pelo plantao"}}
  ]
}
```

**`fixtures/sfn_history/execucao_abortada_com_task_em_voo/meta.yaml`**

```yaml
name: execucao_abortada_com_task_em_voo
proves: >
  O POSITIVO de SF-SFNX-003. A execucao terminou em `ExecutionAborted` --
  `execution_outcome_class: stopped` -- com o Task `.sync` agendado e submetido e SEM
  evento terminal proprio: `terminal_present` e falso. O JobRun `jr_dddddddd1` pode
  estar em voo, e o historico nao diz. A regra nomeia o sintoma e NAO afirma custo
  (regra 13): quem responde custo e `finops`, com o JobRunId e `dpu_seconds` medido.
  SF-SFNX-002 fica calada porque nao houve `TaskTimedOut`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: [SF-SFNX-003]
```

---

**`fixtures/sfn_history/execucao_limpa/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T06:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T06:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T06:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 3600}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T06:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T06:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_eeeeeeee1\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T06:18:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T06:18:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaDiaria"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T06:18:02.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

**`fixtures/sfn_history/execucao_limpa/meta.yaml`**

```yaml
name: execucao_limpa
proves: >
  O NEGATIVO da area inteira. Uma tentativa, `.sync`, `TaskSucceeded`, execucao
  `ExecutionSucceeded`: `job_run_outcome_observed` verdadeiro, `terminal_present`
  verdadeiro, `execution_outcome_class: finished`. Nenhuma das tres regras dispara.
  Sem ASL no case: a lacuna do confronto sai nomeada, e nao vira achado.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

---

**`fixtures/sfn_history/sem_execution_data/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T07:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T07:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaSemDado"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T07:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T07:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T07:10:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T07:10:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaSemDado"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T07:10:02.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaComOutroOutput"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T07:10:03.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T07:10:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"SdkResponseMetadata\": {\"RequestId\": \"abc\"}, \"SdkHttpMetadata\": {\"HttpStatusCode\": 200}}"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T07:20:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T07:20:01.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaComOutroOutput"}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T07:20:02.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

**`fixtures/sfn_history/sem_execution_data/meta.yaml`**

```yaml
name: sem_execution_data
proves: >
  As DUAS metades da AC2, e a lacuna U1 ao lado. O primeiro Task foi submetido sem
  `output` -- `includeExecutionData` desligado --, e nenhum `sfn.job_run` e afirmado:
  sai `execution_data_absent`. O segundo TEM `output`, e a forma dele nao e nenhuma
  das tres que o extrator reconhece: sai `job_run_id_unrecognized` COM as chaves de
  topo (`SdkHttpMetadata`, `SdkResponseMetadata`), que e o dado que um historico real
  usa para fechar U1. Nenhuma regra dispara: as duas tentativas terminaram bem.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.unresolved
expects_rules: []
```

---

**`fixtures/sfn_history/historico_truncado/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T08:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T08:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaLonga"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T08:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1", "timeoutInSeconds": 7200}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T08:00:03.000000+00:00", "type": "TaskStarted", "taskStartedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T08:00:04.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_ffffffff1\", \"JobName\": \"carga-longa\"}"}}
  ],
  "nextToken": "AAAAKgAAAAIAAAAAAAAAAg=="
}
```

**`fixtures/sfn_history/historico_truncado/meta.yaml`**

```yaml
name: historico_truncado
proves: >
  AC3 no caso que mais engana. `nextToken` na saida salva: a pagina seguinte existe e
  ninguem a salvou. O que foi lido continua valendo -- a tentativa e o JobRun saem --,
  e as duas lacunas saem nomeadas: `truncated` e `execution_terminal_absent`. O
  `status` da execucao e `unresolved`, NUNCA sucesso por suposicao, e por isso a
  SF-SFNX-003 fica calada: `execution_outcome_class` e `unresolved`, nao `stopped`.
  Um extrator que chutasse "abortada" aqui inventaria um achado P1.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

---

**`fixtures/sfn_history/evento_desconhecido/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T09:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T09:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaDiaria"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T09:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T09:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_99999999\", \"JobName\": \"carga-diaria\"}"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T09:09:00.000000+00:00", "type": "TaskSucceeded", "taskSucceededEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T09:09:01.000000+00:00", "type": "VariableSetEventDetailsEntered"},
    {"id": 7, "previousEventId": 5, "timestamp": "2026-09-18T09:09:02.000000+00:00", "type": "TaskStateExited", "stateExitedEventDetails": {"name": "CargaDiaria"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T09:09:03.000000+00:00", "type": "ExecutionSucceeded"}
  ]
}
```

**`fixtures/sfn_history/evento_desconhecido/meta.yaml`**

```yaml
name: evento_desconhecido
proves: >
  AC3 na metade que a API move sozinha. O tipo `VariableSetEventDetailsEntered` nao
  esta na lista publicada que o extrator carrega: nao e defeito do artefato, e a API
  que cresceu. Ele sai em `event_type_unknown` COM o nome, e o resto do arquivo
  continua valendo -- a tentativa completa sai, com o JobRun. Ignorar em silencio
  seria a unica saida pior do que falhar.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

---

**`fixtures/sfn_history/json_invalido/input/quebrado.json`** (sem subdiretório: esta
fixture não tem histórico legível nem definição)

```text
{"events": [
```

**`fixtures/sfn_history/json_invalido/input/inventario.json`**

```json
{"jobs": ["carga-diaria", "carga-horaria"]}
```

**`fixtures/sfn_history/json_invalido/meta.yaml`**

```yaml
name: json_invalido
proves: >
  AC3 nas duas formas de "nao da para ler": JSON que nao fecha (`invalid_json`) e JSON
  valido que nao e historico de execucao (`not_an_execution_history`). Um
  `sfn.unresolved` por arquivo, uma sentinela por arquivo, e NENHUMA excecao que
  derrube quem chamou. Sem `sfn.attempt` no pool, a derivacao nem roda -- a mesma
  guarda que `fusion.fuse` aplica.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [sfn.analyzed, sfn.unresolved]
expects_rules: []
```

---

**`fixtures/sfn_history/historico_sem_asl/input/historico/execucao.json`**

```json
{
  "events": [
    {"id": 1, "previousEventId": 0, "timestamp": "2026-09-18T10:00:00.000000+00:00", "type": "ExecutionStarted"},
    {"id": 2, "previousEventId": 1, "timestamp": "2026-09-18T10:00:01.000000+00:00", "type": "TaskStateEntered", "stateEnteredEventDetails": {"name": "CargaSemDefinicao"}},
    {"id": 3, "previousEventId": 2, "timestamp": "2026-09-18T10:00:02.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 4, "previousEventId": 3, "timestamp": "2026-09-18T10:00:03.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_11111111\"}"}},
    {"id": 5, "previousEventId": 4, "timestamp": "2026-09-18T10:10:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_11111111 FAILED"}},
    {"id": 6, "previousEventId": 5, "timestamp": "2026-09-18T10:10:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 7, "previousEventId": 6, "timestamp": "2026-09-18T10:10:02.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_22222222\"}"}},
    {"id": 8, "previousEventId": 7, "timestamp": "2026-09-18T10:20:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_22222222 FAILED"}},
    {"id": 9, "previousEventId": 8, "timestamp": "2026-09-18T10:20:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 10, "previousEventId": 9, "timestamp": "2026-09-18T10:20:02.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_33333333\"}"}},
    {"id": 11, "previousEventId": 10, "timestamp": "2026-09-18T10:30:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_33333333 FAILED"}},
    {"id": 12, "previousEventId": 11, "timestamp": "2026-09-18T10:30:01.000000+00:00", "type": "TaskScheduled", "taskScheduledEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "region": "us-east-1"}},
    {"id": 13, "previousEventId": 12, "timestamp": "2026-09-18T10:30:02.000000+00:00", "type": "TaskSubmitted", "taskSubmittedEventDetails": {"resource": "startJobRun.sync", "resourceType": "glue", "output": "{\"JobRunId\": \"jr_44444444\"}"}},
    {"id": 14, "previousEventId": 13, "timestamp": "2026-09-18T10:40:00.000000+00:00", "type": "TaskFailed", "taskFailedEventDetails": {"error": "Glue.AWSGlueException", "cause": "JobRun jr_44444444 FAILED"}},
    {"id": 15, "previousEventId": 14, "timestamp": "2026-09-18T10:40:01.000000+00:00", "type": "ExecutionFailed", "executionFailedEventDetails": {"error": "Glue.AWSGlueException"}}
  ]
}
```

**`fixtures/sfn_history/historico_sem_asl/meta.yaml`**

```yaml
name: historico_sem_asl
proves: >
  A SEGUNDA metade da AC4, e o unico jeito de prova-la. Quatro tentativas do mesmo
  estado e quatro JobRuns distintos -- numero que dispararia a SF-SFNX-001 com
  qualquer teto declarado plausivel --, e nenhuma definicao ASL no case. O confronto
  NAO acontece, a regra sai em `skipped` com `reason: requires_facts`, e a lacuna sai
  nomeada em `asl_absent`. "Nao perguntei" e o achado; "esta tudo bem" seria mentira.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - sfn.analyzed
  - sfn.attempt
  - sfn.execution
  - sfn.job_run
  - sfn.unresolved
expects_rules: []
```

### 2. Rodar e ver falhar

```bash
git add tests/test_fixtures_golden_sfn_history.py
python -m pytest tests/test_sfn_history.py::test_fuse_confronta_o_retry_declarado_com_o_observado tests/test_fixtures_golden_sfn_history.py -q
```

Falhas esperadas: `ImportError: cannot import name 'build_sfn_retry_observado'` na coleta
do golden (a derivação é a unidade sob teste), e `ValueError: not enough values to
unpack` em `[confronto] = ...` no teste do `fuse`.

### 3. Código mínimo

**3a. A derivação, em `sparkforge/facts/sfn_history.py`** (D5).

No docstring do módulo, troque

```text
- `sfn.analyzed` -- a sentinela, com as contagens.
```

por

```text
- `sfn.analyzed` -- a sentinela, com as contagens.
- `sfn.retry_observado` -- DERIVADO, nunca lido de arquivo: `build_sfn_retry_observado`
  casa as tentativas de um estado com o `sfn.task` de MESMO NOME que o ASL declara, e
  `fusion.fuse` a chama. As razoes de `sfn.unresolved` que so ela emite: `asl_absent`,
  `state_name_absent_in_asl`, `state_name_ambiguous` e `declared_ceiling_unreadable`.
```

Imports: o módulo de T1 não usa `Sequence`, e a derivação usa. Troque

```python
from dataclasses import dataclass, field
from datetime import datetime
```

por

```python
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
```

`EMITTED_KINDS`: troque

```python
EMITTED_KINDS = frozenset(
    {
        "sfn.execution",
        "sfn.attempt",
        "sfn.job_run",
        "sfn.unresolved",
        "sfn.analyzed",
    }
)
```

por

```python
EMITTED_KINDS = frozenset(
    {
        "sfn.execution",
        "sfn.attempt",
        "sfn.job_run",
        "sfn.unresolved",
        "sfn.analyzed",
        "sfn.retry_observado",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `sfn.attempt` no pool, o `fuse` sai byte
# a byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS` e do
# `stepfunctions.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"sfn.attempt"})
```

E acrescente, logo antes de `__all__`:

```python
def _glue_por_estado(facts: Sequence[Fact], kind: str) -> dict[str, list[Fact]]:
    """Nome do estado -> facts daquele kind que chamam `glue:startJobRun`.

    Serve para os dois lados do confronto: `sfn.attempt` (medido) e `sfn.task`
    (declarado). O `subject` dos dois e diferente -- o do ASL e o CAMINHO do estado na
    definicao, o do historico e `<nome>#<ordem>` --, e por isso `same_subject` nao os
    junta e a derivacao existe (o mesmo motivo de `bridge.py` e de
    `build_sfn_glue_link`).
    """
    por_nome: dict[str, list[Fact]] = {}
    for fact in facts:
        if fact.kind != kind:
            continue
        attrs = fact.attrs or {}
        if attrs.get("service") != "glue" or attrs.get("api") != "startJobRun":
            continue
        nome = attrs.get("state_name")
        if not isinstance(nome, str) or not nome:
            continue
        por_nome.setdefault(nome, []).append(fact)
    return por_nome


def build_sfn_retry_observado(facts: Sequence[Fact]) -> list[Fact]:
    """Confronta o retry DECLARADO no ASL com o OBSERVADO no historico (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `bridge.py`: o motor avalia um
    fact por condicao, e o que ele precisa comparar -- quantas vezes o Task foi
    agendado contra quantas vezes ele PODIA ser -- mora em dois facts de `subject`
    diferente.

    O pareamento e pelo NOME do estado, porque o historico so publica o nome: o
    `stateEnteredEventDetails.name`. Nao ha caminho de estado no historico, e por isso
    dois estados de mesmo nome em ramos de um `Parallel` sao AMBIGUIDADE, nao escolha.

    O `teto_declarado` e `1 + failure_retry_max_attempts` do `sfn.task`: o Step
    Functions agenda o Task uma vez, mais `MaxAttempts` reagendamentos. O efetivo, a
    marca de `MaxAttempts` omitido e a regra de qual retrier casa a falha do job moram
    em `stepfunctions.py`, com a frase citada ao lado -- aqui so se LE o que ele mediu.

    Nada aqui atribui custo (regras 13 e 25): o fact diz quantas vezes, e o `JobRunId`
    de cada tentativa esta em `sfn.job_run`, que e por onde `finops` responde custo com
    `dpu_seconds` medido.
    """
    tentativas = _glue_por_estado(facts, "sfn.attempt")
    if not tentativas:
        return []
    declaradas = _glue_por_estado(facts, "sfn.task")
    ha_asl = any(f.kind == "sfn.task" for f in facts)
    saida: list[Fact] = []
    for nome in sorted(tentativas):
        grupo = sorted(tentativas[nome], key=lambda f: f.id)
        arquivo = str((grupo[0].subject or {}).get("file") or "")
        subject = _attempt_subject(arquivo, nome)
        proveniencia = {
            "artifact": str((grupo[0].provenance or {}).get("artifact", "")),
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": sorted(f.id for f in grupo),
        }
        if not ha_asl:
            saida.append(
                _unresolved(dict(subject), "asl_absent", proveniencia, state_name=nome)
            )
            continue
        candidatas = declaradas.get(nome) or []
        if not candidatas:
            saida.append(
                _unresolved(
                    dict(subject), "state_name_absent_in_asl", proveniencia, state_name=nome
                )
            )
            continue
        if len(candidatas) > 1:
            saida.append(
                _unresolved(
                    dict(subject),
                    "state_name_ambiguous",
                    proveniencia,
                    state_name=nome,
                    declared_count=len(candidatas),
                )
            )
            continue
        tarefa = candidatas[0]
        teto = (tarefa.measures or {}).get("failure_retry_max_attempts")
        if isinstance(teto, bool) or not isinstance(teto, int):
            saida.append(
                _unresolved(
                    dict(subject),
                    "declared_ceiling_unreadable",
                    proveniencia,
                    state_name=nome,
                )
            )
            continue
        attrs_da_tarefa = tarefa.attrs or {}
        saida.append(
            Fact(
                kind="sfn.retry_observado",
                subject=dict(subject),
                measures={"tentativas_observadas": len(grupo), "teto_declarado": 1 + teto},
                attrs={
                    "state_name": nome,
                    "job_name": attrs_da_tarefa.get("job_name"),
                    "pattern": attrs_da_tarefa.get("pattern"),
                    "declared_retry_matched": bool(
                        attrs_da_tarefa.get("failure_retry_matched")
                    ),
                    "declared_retry_defaulted": bool(
                        attrs_da_tarefa.get("failure_retry_defaulted")
                    ),
                    "execution_outcome": (grupo[-1].attrs or {}).get("execution_outcome"),
                },
                provenance={
                    **proveniencia,
                    "derived_from": sorted({*proveniencia["derived_from"], tarefa.id}),
                },
            )
        )
    return sort_facts(saida)
```

E `__all__`: troque

```python
__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_sfn_history",
```

por

```python
__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_sfn_retry_observado",
    "extract_sfn_history",
```

**3b. `sparkforge/facts/fusion.py`** — a chamada. Troque

```python
from sparkforge.facts.stepfunctions import SOURCE_KINDS as SFN_SOURCE_KINDS
from sparkforge.facts.stepfunctions import build_sfn_glue_link
```

por

```python
from sparkforge.facts.sfn_history import EMITTED_KINDS as SFN_HISTORY_EMITTED_KINDS
from sparkforge.facts.sfn_history import SOURCE_KINDS as SFN_HISTORY_SOURCE_KINDS
from sparkforge.facts.sfn_history import build_sfn_retry_observado
from sparkforge.facts.stepfunctions import SOURCE_KINDS as SFN_SOURCE_KINDS
from sparkforge.facts.stepfunctions import build_sfn_glue_link
```

(Se o `ruff`/isort quiser o bloco de `sfn_history` noutra posição da lista de imports de
`sparkforge.facts.*`, aceite o que ele escrever — `sfn_history` < `spark_plan` <
`stepfunctions` na ordem alfabética.)

E o bloco de derivação, no fim de `fuse`. Troque

```python
        for fact in derivados_sfn:
            combined[fact.id] = fact

    return sort_facts(combined.values())
```

por

```python
        for fact in derivados_sfn:
            combined[fact.id] = fact

    # `sfn.retry_observado` deriva AQUI pela mesma razao do `sfn.glue_job_link` logo
    # acima, e com o mesmo molde: o `sfn.attempt` (medido) e o `sfn.task` (declarado)
    # tem `subject` diferente, e o motor nao junta dois facts numa condicao. Guardado
    # por `SOURCE_KINDS`: pool sem historico de execucao sai byte a byte igual.
    if any(f.kind in SFN_HISTORY_SOURCE_KINDS for f in facts):
        derivados_historico = build_sfn_retry_observado(facts)
        desconhecidos_historico = {
            f.kind for f in derivados_historico
        } - SFN_HISTORY_EMITTED_KINDS
        if desconhecidos_historico:
            raise AssertionError(
                f"kind fora do namespace de sfn_history: {sorted(desconhecidos_historico)}"
            )
        for fact in derivados_historico:
            combined[fact.id] = fact

    return sort_facts(combined.values())
```

**3c. `rules/catalog/sfn-history.yaml`** (arquivo novo, inteiro):

```yaml
# Catálogo de regras — o que ACONTECEU numa execução do AWS Step Functions
#
# Depende de `sparkforge/facts/sfn_history.py`, que lê a saída salva de
# `aws stepfunctions get-execution-history` e, em `fuse`, confronta as tentativas
# observadas com o retry que o ASL declara (`sfn.retry_observado`). As frases citadas
# estão em `knowledge/stepfunctions/execution-history.md`; o desenho, em
# `docs/sdd/SFN_HISTORY/design.md`.
#
# POR QUE UMA ÁREA PRÓPRIA, e não mais quatro regras em `SF-SFN` (D4): `SF-SFN` julga o
# que a definição DECLARA; esta julga o que a execução REGISTROU. Misturar as duas na
# mesma área tiraria do operador exatamente a distinção que esta feature existe para
# fazer — e é ela que decide o conserto, porque retry declarado se corrige na definição
# e tentativa observada demais pode ser sintoma de outra coisa inteira.
#
# O QUE A ÁREA NÃO JULGA, e por quê (D4):
# - duração de tentativa acima de um limiar: limiar de duração de job não tem fonte
#   publicada, e seria número inventado;
# - custo de uma tentativa, e economia de tirá-la: regras 13 e 25 do `CLAUDE.md`. O
#   fact traz o `JobRunId`, e quem responde custo é `finops`, com `dpu_seconds` medido;
# - quantas vezes o job Glue rodou por tentativa: a composição entre o retry do Step
#   Functions e o `MaxRetries` do Glue continua sem documentação (lacuna 1 de
#   `knowledge/stepfunctions/glue-integration.md`). O que esta área mede é o número de
#   AGENDAMENTOS do Task, que é o que o histórico registra;
# - histórico de state machine EXPRESS: a API não o suporta, e ele vai para o
#   CloudWatch Logs;
# - serviços além do Glue: o extrator os registra, e nenhuma regra os julga.
#
# `runtime_scope: {}` nas três (D4), e a escolha é medida: não há fronteira de versão
# publicada para nenhuma delas, e o histórico sozinho não detecta runtime Glue --
# `{glue: "*"}` faria as três saírem em `skipped` até alguém declarar `--glue`, o
# defeito que `docs/gates-por-mudanca.md` descreve. Quem gateia é `requires_facts`: sem
# `sfn.attempt` (ou sem o `sfn.retry_observado` que só o `fuse` deriva), a regra é
# pulada com a razão. A auditoria de texto AWS de `tests/test_databricks_rule_audit.py`
# fica satisfeita porque `sfn_history` está em `SO_AWS`: o extrator só lê artefato da
# AWS.
#
# AS TRÊS SÃO `confirmed`, e é a diferença de natureza com `SF-SFN`: elas afirmam que
# algo ACONTECEU, lido do artefato de execução, não que a configuração tem uma
# propriedade. `SF-SFN-002` e `structural` sobre o mesmo retry; esta área é o lado
# medido dele.
#
# A ÂNCORA de cada regra é o fact que ela julga, com `same_subject: true`: um achado por
# tentativa (`<estado>#<ordem>`) nas duas últimas, e um por estado na primeira.
#
# TRÊS PREDICADOS DERIVADOS no extrator (regra 33), porque `sparkforge/rules/expr.py`
# tem seis comparadores e nenhuma função: `execution_outcome_class` (que junta
# `ExecutionAborted` e `ExecutionTimedOut` num valor só, porque `in` não existe),
# `terminal_present` e `job_run_outcome_observed`.

catalog_version: 1
schema_version: 1
area: SF-SFNX
retrieved: 2026-09-20

rules:

  # A ancora e o fact DERIVADO: sem `fuse` com o historico e o ASL no mesmo pool, a
  # regra sai em `skipped` com `reason: requires_facts` -- "nao perguntei", nunca "esta
  # tudo bem". ASL ausente, estado com outro nome e nome ambiguo saem em
  # `sfn.unresolved` na derivacao.
  - id: SF-SFNX-001
    category: stepfunctions-execution
    title: "Tentativas observadas acima do que o retry declarado permite"
    requires_facts: [sfn.retry_observado]
    when:
      same_subject: true
      all:
        - fact: sfn.retry_observado
          expr: "measures.tentativas_observadas > measures.teto_declarado"
    status: confirmed
    severity_default: P2
    runtime_scope: {}
    explanation: >
      O histórico da execução registra mais agendamentos do Task do que o retry
      declarado no ASL permite. O Step Functions agenda o Task uma vez e o reagenda até
      `MaxAttempts` vezes — teto efetivo de `1 + MaxAttempts` —, e cada agendamento de
      um `glue:startJobRun` é um `StartJobRun` novo, não uma retomada. O número
      observado está em `measures.tentativas_observadas`, lido dos eventos
      `TaskScheduled` do estado; o teto, em `measures.teto_declarado`. A diferença tem
      três leituras possíveis, e o achado **não escolhe entre elas**: o ASL lido não é o
      que estava publicado quando a execução rodou; existe outro retrier casando a
      falha antes do que o extrator mediu; ou o estado foi reentrado pelo fluxo (um
      `Choice` que volta), e aí cada entrada traz o seu próprio orçamento de retry. As
      três se decidem pela mesma evidência: a versão da definição no instante da
      execução. Esta regra **não** afirma quantos JobRuns do Glue a falha produziu — o
      `MaxRetries` do próprio job é outra camada, e a composição delas não é
      documentada (`SF-SFN-004`, e a lacuna 1 de
      knowledge/stepfunctions/glue-integration.md). E não afirma custo nenhum: o
      `JobRunId` de cada tentativa está em `sfn.job_run`, e é por ele que
      `sparkforge finops` responde custo com `dpu_seconds` medido.
    proposed_change:
      - "Conferir qual versão da definição estava publicada no instante da execução (`aws stepfunctions describe-state-machine --state-machine-arn <arn>` traz a definição corrente; o histórico de versões, se houver, traz a da época) antes de mudar qualquer coisa: o achado compara um ASL do repositório com uma execução que pode ter rodado outro."
      - "Se a definição confere, procurar o segundo caminho de reagendamento: um `Choice` que volta ao mesmo estado, ou um retrier anterior na ordem declarada cujo `ErrorEquals` também casa a falha do job."
      - "Se o retry é o esperado e o número é o desejado, declarar `MaxAttempts` explícito no retrier que casa a falha, com o número que um JobRun inteiro por tentativa justifica — inclusive `0`."
    # `orchestration.restrict_run_policy` com o mesmo alvo e a mesma direcao da
    # `SF-SFN-002` (`sfn.task.retry`, `decrease`): mesma direcao nao e contradicao para
    # `tests/test_rules_action_field.py`, e as duas propoem a mesma familia de conserto
    # -- uma pela definicao, esta pela medida. `runtime.wall_clock` esta FORA de
    # proposito: ele e o maior grupo de restricao (12) e
    # `tests/test_agentic_executor_ordering.py` trava esse teto.
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
      - "O ASL lido pode não ser o que executou. O achado compara artefato do repositório com execução da conta, e nada no histórico traz a definição."
      - "Reduzir o retry expõe a execução a falhas transitórias que hoje são absorvidas."
      - "Se o job não escreve de forma idempotente, cada tentativa a mais já deixou efeito no destino — e reduzir o retry agora não desfaz o que as anteriores escreveram."
    tradeoffs:
      - "Retry sobre o job inteiro compra resiliência ao custo de um JobRun completo por tentativa. Descobrir que o observado passa do declarado não diz qual dos dois está errado — diz que eles não batem."
    validation:
      - "`sparkforge analyze sfn-history` sobre um histórico novo, depois da correção, mostra `tentativas_observadas` menor ou igual a `teto_declarado`, e `sparkforge judge` não produz mais SF-SFNX-001 para o estado."
      - "EIXO DE RESULTADO — numa execução de teste com falha induzida, o destino tem a mesma contagem total e a mesma contagem por chave de negócio que uma execução sem falha: as tentativas extras não duplicaram nem perderam linha."
      - "Os `JobRunId` de `sfn.job_run` do intervalo, conferidos em `sparkforge collect glue-job-runs`, são exatamente os que a camada de retry escolhida declara — nem mais, nem menos."
    rollback:
      - "Reverter o commit da definição ASL e republicar a state machine pelo mesmo caminho que a publica (IaC ou `update-state-machine`)."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html", retrieved: 2026-09-19}

  # A ancora e a TENTATIVA, e os tres predicados de igualdade que ela le sao os que
  # `expr.py` consegue avaliar. `job_run_outcome_observed` e derivado no extrator
  # (regra 33): ele e verdadeiro so num `.sync` que terminou em sucesso ou falha.
  - id: SF-SFNX-002
    category: stepfunctions-execution
    title: "Task .sync expirou: o histórico não registra o fim do JobRun que ele acompanhava"
    requires_facts: [sfn.attempt]
    when:
      same_subject: true
      all:
        - fact: sfn.attempt
          where:
            attrs.service: glue
            attrs.api: startJobRun
            attrs.pattern: sync
            attrs.result: timed_out
            attrs.job_run_outcome_observed: false
    status: confirmed
    severity_default: P1
    runtime_scope: {}
    explanation: >
      A tentativa terminou em `TaskTimedOut`: o estado expirou pelo próprio
      `TimeoutSeconds` antes que o JobRun terminasse. Num Task `.sync` é o Step
      Functions que acompanha o JobRun, e quando ele para de acompanhar o histórico
      deixa de registrar o desfecho — o último evento sobre aquele JobRun é o
      `TaskSubmitted`. O `JobRunId` está em `sfn.job_run`; o que aconteceu com ele
      depois, não. A regra afirma que o desfecho **não foi observado**, e nada além
      disso: ela não afirma que o job continuou rodando, nem que ele foi interrompido —
      a documentação do abort do `.sync` não descreve o caso de timeout (lacuna 2 de
      knowledge/stepfunctions/glue-integration.md). E não afirma custo: dizer "você
      pagou por um job órfão" exigiria o `dpu_seconds` de um run que ninguém leu
      (regra 13 do CLAUDE.md).
      **O timeout é consequência antes de ser causa** (regra 15): antes de aumentar
      `TimeoutSeconds`, leia por que o JobRun passou do prazo — skew, spill, GC ou
      executor perdido ao lado trocam uma falha rápida por uma falha cara.
    proposed_change:
      - "Ler o desfecho real daquele JobRun antes de tocar em qualquer limite: `aws glue get-job-run --job-name <nome> --run-id <JobRunId>` sobre o `JobRunId` que está em `sfn.job_run` diz se ele terminou, falhou, ou continuou depois do Task expirar."
      - "Com o desfecho em mãos, classificar: JobRun que terminou DEPOIS do prazo é dimensionamento do prazo; JobRun que travou é diagnóstico do job (event log, `sparkforge analyze event-log`), e aumentar o limite só adia a mesma falha."
      - "Declarar o que acontece com o JobRun quando o Task expira: um estado de limpeza no `Catch` do timeout chamando `glue:batchStopJobRun` torna a resposta determinística, em vez de depender de comportamento não documentado."
    # `timeout.investigate_symptom_first` com `direction: investigate` e `moves: []` e a
    # regra 15 escrita em vocabulario fechado: ler a causa antes de mexer no limite. A
    # acao nao move grandeza nenhuma porque ela nao muda nada -- ela mede.
    action:
      kind: timeout.investigate_symptom_first
      target: sfn.task.timeout
      direction: investigate
      requires_absent: []
      moves: []
      depends_on: []
    risks:
      - "Aumentar `TimeoutSeconds` sem saber por que o job passou do prazo troca uma falha rápida por uma falha cara (`SF-TIMEOUT-001`)."
      - "Parar o JobRun no `Catch` sem que a escrita do job seja idempotente pode deixar o destino em estado parcial — a interrupção acontece no meio de uma escrita."
      - "Alcance: o que a AWS faz com o JobRun quando o `.sync` expira não está publicado. O conserto determinístico é declarar a limpeza, não confiar no default."
    tradeoffs:
      - "Prazo curto falha rápido e deixa dúvida sobre o job; prazo longo resolve a dúvida e segura a execução da state machine pelo tempo inteiro do job."
    validation:
      - "`aws glue get-job-run` sobre o `JobRunId` da tentativa devolve o estado terminal dele: é a medida que falta, e ela existe."
      - "Depois da correção, `sparkforge analyze sfn-history` sobre um histórico novo mostra a tentativa com `result: succeeded` ou `failed` — `job_run_outcome_observed` verdadeiro —, e `sparkforge judge` não produz mais SF-SFNX-002."
      - "EIXO DE RESULTADO — o destino tem a mesma contagem total e por chave de negócio que uma execução de referência: um JobRun órfão que terminou sozinho pode ter escrito depois do Task expirar, e essa contagem é a única prova de que não houve duplicação."
    rollback:
      - "Reverter o commit da definição (o `TimeoutSeconds` anterior, ou o estado de limpeza acrescentado) e republicar a state machine."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html", retrieved: 2026-09-19}

  - id: SF-SFNX-003
    category: stepfunctions-execution
    title: "Execução parou com um Task .sync agendado e sem evento terminal próprio"
    requires_facts: [sfn.attempt]
    when:
      same_subject: true
      all:
        - fact: sfn.attempt
          where:
            attrs.service: glue
            attrs.api: startJobRun
            attrs.pattern: sync
            attrs.terminal_present: false
            attrs.execution_outcome_class: stopped
    status: confirmed
    severity_default: P1
    runtime_scope: {}
    explanation: >
      A execução terminou em `ExecutionAborted` ou `ExecutionTimedOut` —
      `execution_outcome_class: stopped`, o valor que o extrator deriva justamente
      porque o motor de regras não tem `in` (regra 33) — e o Task `.sync` do Glue foi
      agendado sem nunca ganhar evento terminal próprio. A execução parou por fora, e o
      último que o histórico sabe daquele Task é que ele foi agendado (e, quando há
      `TaskSubmitted`, submetido, com o `JobRunId` em `sfn.job_run`). A regra afirma o
      que está no artefato: **a execução parou com o Task em voo**. Ela não afirma que
      o job continuou rodando — isso depende do que a AWS faz com o JobRun no abort do
      `.sync`, e a lacuna está nomeada em
      knowledge/stepfunctions/execution-history.md. E não afirma custo nem economia
      (regras 13 e 25). A diferença para a `SF-SFNX-002` é qual dos dois relógios
      parou: lá o do Task, aqui o da execução.
    proposed_change:
      - "Ler o desfecho do `JobRunId` daquela tentativa (`aws glue get-job-run`): é a única fonte que diz se o job parou junto com a execução ou seguiu sozinho."
      - "Declarar a limpeza em vez de depender do default: um `Catch` de `States.ALL` no estado, ou um passo de encerramento que chame `glue:batchStopJobRun` sobre o `JobRunId` — e a role da state machine precisa da permissão correspondente, que a política que a AWS gera para o `.sync` do Glue já inclui."
      - "Se abortar a execução é operação rotineira (plantão parando carga), escrever o procedimento com o passo de conferir o JobRun: o operador que aborta precisa saber que o job pode não ter parado."
    # `orchestration.change_job_definition` com alvo PROPRIO
    # (`sfn.state_machine.abort_handling`) e `direction: add`: a mudanca acrescenta o
    # tratamento que hoje nao existe. `moves` traz so `correctness.write_result`
    # (`nature: risk`, fora da restricao de grupo): o que a limpeza muda e o que fica
    # escrito no destino quando alguem para a execucao.
    action:
      kind: orchestration.change_job_definition
      target: sfn.state_machine.abort_handling
      direction: add
      requires_absent: []
      moves:
        - correctness.write_result
      depends_on: []
    risks:
      - "Parar o JobRun no abort sem escrita idempotente deixa o destino em estado parcial: a interrupção cai no meio de uma escrita."
      - "Alcance: o que acontece com o JobRun quando a execução é abortada não está descrito para o caso de timeout da execução, e a leitura registrada aqui é essa lacuna, não uma resposta."
      - "Acrescentar `Catch` muda o caminho de falha da state machine: estados que nunca rodaram passam a rodar, e alarmes que nunca dispararam passam a disparar."
    tradeoffs:
      - "Parar o job junto com a execução torna o abort determinístico ao custo de perder trabalho que talvez terminasse sozinho; deixar o job seguir preserva o trabalho ao custo de ninguém saber que ele existe."
    validation:
      - "`aws glue get-job-run` sobre o `JobRunId` da tentativa devolve o estado terminal dele — é a medida que o histórico não tem."
      - "Depois da correção, um abort de teste produz um histórico em que o Task tem evento terminal próprio (`TaskFailed` pelo `Catch`, ou `TaskStateAborted`), e `sparkforge judge` não produz mais SF-SFNX-003."
      - "EIXO DE RESULTADO — depois de um abort de teste, o destino tem a contagem por chave de negócio de antes do abort, ou a de uma execução completa: nunca uma terceira, que é o que escrita parcial produz."
    rollback:
      - "Reverter o commit da definição (o `Catch` ou o passo de encerramento acrescentado) e republicar a state machine."
    sources:
      - {url: "https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html", retrieved: 2026-09-19}
```

**3d. `rules/catalog/routing.yaml`** — a rota `AGENT-088`. Arquivo **com BOM**: edite com
Edit, nunca reescreva. Troque

```yaml
fallback:
  recommended_skill: sparkforge-diagnose
```

por

```yaml
  # SF-SFNX entrou com `docs/sdd/SFN_HISTORY/` (2026-09-20) e ganha ENTRADA PROPRIA pelo
  # motivo de sempre: `rule_areas` do agente NAO roteia, e `findings_area` conta por
  # prefixo exato do `rule_id` ate o ultimo hifen (`SF-SFNX-001` -> `SF-SFNX`). Sem esta
  # entrada, um case cujo unico achado e uma tentativa observada voltaria de `next_step`
  # com `recommended_agent: None`.
  #
  # O MESMO dono de SF-SFN (`glue-infra-reviewer`), e nao um coordenador novo: as tres
  # regras julgam COMO o job Glue foi disparado e quantas vezes ele rodou, a mesma
  # conversa de `max_retries` que ele ja tem em SF-GLUE-004 e em SF-SFN. Uma area so nao
  # justifica coordenador novo, e o criterio de dominio exige area que julga.
  #
  # PRECEDENCIA: depois de AGENT-002 (`glue-infra-reviewer`) e de AGENT-086 (SF-SFN); um
  # case com SF-GLUE ou SF-SFN junto vai pelas rotas de cima, e o destino e o mesmo.
  - id: AGENT-088
    phase_in: [diagnosis, hypothesis, design, verification, documentation]
    title: Achado dominante no que a execucao do Step Functions registrou
    when:
      all:
        - {findings_area: SF-SFNX, count_gt: 0}
    recommended_agent: glue-infra-reviewer
    reason: >
      O historico da execucao diz quantas vezes o Task foi agendado de verdade, e o que
      ficou sem desfecho quando o relogio do Task ou o da execucao parou. O conserto
      mora na definicao ASL, no prazo declarado e no tratamento de abort -- os
      artefatos de infraestrutura que este coordenador ja le --, e nao no codigo do job.

fallback:
  recommended_skill: sparkforge-diagnose
```

**3e. `agents/glue-infra-reviewer.md`** — `rule_areas`. Troque

```yaml
rule_areas: [SF-GLUE, SF-ENV, SF-SFN]
```

por

```yaml
rule_areas: [SF-GLUE, SF-ENV, SF-SFN, SF-SFNX]
```

(A seção de prosa e a `description` já entraram em T2. Espelhos: backup do
`.claude/agents/README.md`, `python scripts/sync_skills.py`, devolva o README; e
`.codex/agents/glue-infra-reviewer.toml` à mão, se ele carregar `rule_areas`.)

**3f. `tests/test_fixtures_kind_coverage.py`** — as duas listas manuais. No bloco de
imports, troque

```python
    s3_listing,
    spark_plan,
```

por

```python
    s3_listing,
    sfn_history,
    spark_plan,
```

E no mapa de domínios, troque

```python
    # `stepfunctions` entra nas DUAS listas no MESMO commit de `fixtures/stepfunctions/`:
    # sem ele aqui, os cinco kinds `sfn.*` nao sao verificados por ninguem.
    "stepfunctions": stepfunctions,
```

por

```python
    # `sfn_history` entra nas DUAS listas no MESMO commit de `fixtures/sfn_history/`:
    # sem ele aqui, os kinds `sfn.execution`, `sfn.attempt`, `sfn.job_run` e
    # `sfn.retry_observado` nao sao verificados por ninguem. `sfn.unresolved` e
    # `sfn.analyzed` ele COMPARTILHA com `stepfunctions` de proposito (D1 de
    # `docs/sdd/SFN_HISTORY/design.md`): o prefixo e o mesmo porque o dominio e o
    # mesmo, e o kind e que diz a natureza -- `sfn.task` e declaracao, `sfn.attempt`
    # e medida.
    "sfn_history": sfn_history,
    # `stepfunctions` entra nas DUAS listas no MESMO commit de `fixtures/stepfunctions/`:
    # sem ele aqui, os cinco kinds `sfn.*` nao sao verificados por ninguem.
    "stepfunctions": stepfunctions,
```

**3g. `tests/test_rules_catalog_reachability.py`** — as duas listas de `EXTRACTORS`
(linhas ~85 e ~215). Nas duas, troque

```python
    s3_listing,
    spark_plan,
```

por

```python
    s3_listing,
    # `sfn_history` entra nas DUAS listas manuais no MESMO commit da area SF-SFNX: sem
    # ele aqui, `sfn.attempt` e `sfn.retry_observado` contam como orfaos e as tres
    # regras seriam forcadas a `blocked_on` sobre um extrator que esta no repositorio.
    sfn_history,
    spark_plan,
```

(Se o import de `sfn_history` ainda não estiver no bloco `from sparkforge.facts import
(...)` do arquivo, acrescente-o na mesma posição alfabética.)

**3h. `tests/test_databricks_rule_audit.py`**, em `SO_AWS`: troque

```python
    "stepfunctions": (
        "le a definicao ASL do AWS Step Functions (`arn:aws:states`) e deriva "
        "`sfn.glue_job_link` do `aws_glue_job` do Terraform"
    ),
```

por

```python
    "stepfunctions": (
        "le a definicao ASL do AWS Step Functions (`arn:aws:states`) e deriva "
        "`sfn.glue_job_link` do `aws_glue_job` do Terraform"
    ),
    # Sem esta entrada, as tres regras SF-SFNX (sem eixo de plataforma no
    # `runtime_scope`) contariam como alcancaveis num job Databricks -- e o artefato
    # que elas leem so existe na AWS.
    "sfn_history": (
        "le o historico de execucao do AWS Step Functions (`get-execution-history`) e "
        "deriva `sfn.retry_observado` contra o `sfn.task` do ASL"
    ),
```

**3i. `sparkforge/agentic/executor/debate_evidence.py`**, em `EVIDENCE_EXTRACTORS`:
troque

```python
    "s3-listing": ("s3_listing", "extract_s3_listing_path"),
```

por

```python
    "s3-listing": ("s3_listing", "extract_s3_listing_path"),
    "sfn-history": ("sfn_history", "extract_sfn_history_path"),
```

`extract_sfn_history_path(path, repo_root)` tem a assinatura que
`tests/test_agentic_debate_evidence.py::test_todo_extrator_da_lista_recebe_path_e_repo_root`
exige, e o módulo não é de transcript. No comentário acima do dicionário, troque
`carregar os 23 extratores para` por `carregar os 24 extratores para`.

(Confira a chave vizinha antes de editar: a lista é ordenada alfabeticamente e
`s3-listing` < `sfn-history` < `sql`. Se `sql` vier logo depois de `s3-listing` nesta
árvore, a âncora acima é a certa.)

**3j. `docs/agentic-evolution-report.md`**: troque `allowlist de 23` por
`allowlist de 24` (uma ocorrência, por volta da linha 205).

**3k. O golden do debate, na MESMA tarefa.** `fixtures/debate/retomada/expected/brief.json`
lista a allowlist de extratores no bloco `evidence_extractors`, e ela acabou de mudar.
**Regenere pelo caminho do próprio teste**, nunca editando o JSON à mão:

```bash
python -c "import json, sys, tempfile; sys.path.insert(0, '.'); sys.path.insert(0, 'tests'); from pathlib import Path; from test_fixtures_golden_debate import FIXTURES, run_fixture; from sparkforge.agentic.executor.debate_run import next_step; raiz = Path(tempfile.mkdtemp()) / 'case'; resultado = run_fixture(FIXTURES / 'retomada', raiz); alvo = FIXTURES / 'retomada' / 'expected' / 'brief.json'; alvo.write_bytes((json.dumps(next_step(raiz, resultado['debate_id']), sort_keys=True, indent=2) + '\n').encode('utf-8'))"
python -m pytest tests/test_fixtures_golden_debate.py -q
```

Confira com `git diff -- fixtures/debate/retomada/expected/brief.json`: **só** a linha
`"sfn-history",` entra na lista `evidence_extractors`. Qualquer outra linha é achado que
mudou — pare e relate. (Esta armadilha foi paga duas vezes: no STEP_FUNCTIONS e no
AIRFLOW_DAG, onde a T3 não a regenerou e a rodada de goldens acusou depois.)

**3l. `scripts/regen_fixtures.py`** — o par do `_extract` do golden.

Imports: troque

```python
from sparkforge.facts.s3_listing import extract_s3_listing_path  # noqa: E402
from sparkforge.facts.spark_plan import extract_plan_path  # noqa: E402
```

por

```python
from sparkforge.facts.s3_listing import extract_s3_listing_path  # noqa: E402
from sparkforge.facts.sfn_history import (  # noqa: E402
    build_sfn_retry_observado,
    extract_sfn_history_tree,
)
from sparkforge.facts.spark_plan import extract_plan_path  # noqa: E402
```

Constante: troque

```python
FIXTURES_STEPFUNCTIONS = ROOT / "fixtures" / "stepfunctions"
```

por

```python
FIXTURES_STEPFUNCTIONS = ROOT / "fixtures" / "stepfunctions"
FIXTURES_SFN_HISTORY = ROOT / "fixtures" / "sfn_history"
```

Função: troque

```python
def regen_dq(directory: Path) -> None:
```

por

```python
def regen_sfn_history(directory: Path) -> None:
    """Historico de execucao do Step Functions: `*.json` sob input/historico/ (ou
    input/), e a definicao ASL sob input/definicao/ quando houver.

    O PAR de `tests/test_fixtures_golden_sfn_history.py::_extract`, e a mesma porta do
    produto: dois verbos, dois `--path`. Os dois artefatos ficam em subdiretorios
    porque a producao os separa -- juntos, cada extrator leria o arquivo do outro e
    sairia um `sfn.unresolved` cruzado por fixture, ruido que nao e medida. A
    derivacao roda sob a MESMA guarda de `fusion.fuse`: sem `sfn.attempt` no pool,
    nada deriva.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    historico = input_dir / "historico"
    definicao = input_dir / "definicao"
    alvo = historico if historico.is_dir() else input_dir
    facts = list(extract_sfn_history_tree(alvo, repo_root=input_dir))
    if definicao.is_dir():
        facts.extend(extract_stepfunctions_tree(definicao, repo_root=input_dir))
    if any(f.kind == "sfn.attempt" for f in facts):
        facts.extend(build_sfn_retry_observado(facts))
    facts = sort_facts(facts)
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_dq(directory: Path) -> None:
```

Despacho por nome: troque

```python
                (FIXTURES_STEPFUNCTIONS / name, regen_stepfunctions),
```

por

```python
                (FIXTURES_STEPFUNCTIONS / name, regen_stepfunctions),
                (FIXTURES_SFN_HISTORY / name, regen_sfn_history),
```

Laço completo: troque

```python
    # Mesma guarda de existencia: `fixtures/stepfunctions/` nasce nesta entrega.
    if FIXTURES_STEPFUNCTIONS.is_dir():
        for directory in sorted(p for p in FIXTURES_STEPFUNCTIONS.iterdir() if p.is_dir()):
            regen_stepfunctions(directory)
```

por

```python
    # Mesma guarda de existencia: `fixtures/stepfunctions/` nasce nesta entrega.
    if FIXTURES_STEPFUNCTIONS.is_dir():
        for directory in sorted(p for p in FIXTURES_STEPFUNCTIONS.iterdir() if p.is_dir()):
            regen_stepfunctions(directory)
    # Mesma guarda de existencia: `fixtures/sfn_history/` nasce nesta entrega.
    if FIXTURES_SFN_HISTORY.is_dir():
        for directory in sorted(p for p in FIXTURES_SFN_HISTORY.iterdir() if p.is_dir()):
            regen_sfn_history(directory)
```

**3m. Regenerar e LER o golden.**

```bash
git add sparkforge/facts/sfn_history.py tests/test_fixtures_golden_sfn_history.py
python scripts/regen_fixtures.py retry_acima_do_declarado retry_dentro_do_declarado task_timed_out_sync execucao_abortada_com_task_em_voo execucao_limpa sem_execution_data historico_truncado evento_desconhecido json_invalido historico_sem_asl
```

Confira a saída linha a linha contra o `expects_rules` de cada `meta.yaml`:
SF-SFNX-001 só em `retry_acima_do_declarado`; SF-SFNX-002 só em `task_timed_out_sync`;
SF-SFNX-003 só em `execucao_abortada_com_task_em_voo`; SF-SFN-002 (da área do ASL, pelo
lado da definição) só nas duas fixtures que têm `input/definicao/`; nada em
`execucao_limpa`, `sem_execution_data`, `historico_truncado`, `evento_desconhecido`,
`json_invalido` e `historico_sem_asl`.

- **Regra que apareça fora dessa lista é achado que ninguém pediu: pare e relate.**
- Se um `expects_kinds` divergir do conjunto medido, o `meta.yaml` é que está errado:
  corrija-o para o medido e diga no relatório qual mudou. `expects_rules` é contrato, e
  divergência nele é motivo de parar.

**3n. Registros que a regra e o extrator movem.**

- `manifest.json`: `"rule_count": 161,` → `"rule_count": 164,`.
- Fontes: `python scripts/refresh_knowledge.py --offline --update`. **Uma** URL nova
  entra em `knowledge/sources.lock.json` — `API_GetExecutionHistory` —; as outras três
  citadas pelas regras (`concepts-error-handling`, `connect-to-resource`, `connect-glue`)
  já estão no lock por `rules/catalog/stepfunctions.yaml`, e ganham o vínculo com as
  `SF-SFNX`. 262 → 263 (247 → 248 móveis, 15 fixas inalteradas).
- Goldens de assessment (carregam a contagem do catálogo):
  `python scripts/regen_fixtures.py glue_40_para_60_salto_longo glue_51_para_60_iceberg_ansi glue_60_fgac_com_jar config_por_caminho_indireto lote_misto_iceberg_parquet`.
  Confira com `git diff --stat -- fixtures/scenarios evals/holdout` e
  `git diff -- fixtures/scenarios evals/holdout | grep '^[-+] '`: só `catalog_rules`
  (161 → 164), `unguarded_rules` (135 → 138: as três têm `runtime_scope: {}`) e a frase
  `statement` que repete os dois ("Catalogo: 164 regras, ... e 138 sem guarda").
  **Qualquer outra linha é achado que mudou: pare e relate.**
- Referência: `python scripts/gen_reference_docs.py` (a página do agente muda com
  `rule_areas`).

**3o. Números.** `docs/superpowers/STATUS.md`, trocas de prefixo de linha (o resto de cada
linha fica como está), antes → depois:

```text
| Regras de diagnóstico | **161**, sendo **98 `confirmed`** e **63 com `status: structural`**, todas executáveis —
| Regras de diagnóstico | **164**, sendo **101 `confirmed`** e **63 com `status: structural`**, todas executáveis — as três `SF-SFNX` (o que a execução do AWS Step Functions REGISTROU) entraram em 2026-09-20 (feature `docs/sdd/SFN_HISTORY/`), as três `confirmed`: elas afirmam que algo ACONTECEU, lido do artefato de execução, e é essa a diferença de natureza com as quatro `SF-SFN`, que julgam o que a definição declara. Leitura anterior de **161**, sendo **98 `confirmed`** e **63 com `status: structural`**, todas executáveis —
```

```text
| Regras com eixo de resultado no `validation` | **161 de 161 têm `validation`** —
| Regras com eixo de resultado no `validation` | **164 de 164 têm `validation`** — as três `SF-SFNX` (2026-09-20) entram com eixo de resultado, e a `SF-SFNX-002` publica um eixo que quase nenhuma outra publica: **o desfecho do JobRun que o histórico não registrou**, lido por `aws glue get-job-run` sobre o `JobRunId` da tentativa. Sem ele, "o job parou" e "o job seguiu sozinho" são indistinguíveis. Leitura anterior de **161 de 161 têm `validation`** —
```

```text
| Fact kinds distintos emitidos | **236** —
| Fact kinds distintos emitidos | **237** — `sfn.retry_observado` (2026-09-20), derivado em `fuse` quando o histórico de execução e o ASL do mesmo state machine estão no mesmo pool. Leitura anterior de **236** —
```

```text
| Rotas determinísticas | **41** —
| Rotas determinísticas | **42** — a acrescida é `AGENT-088` (2026-09-20, feature `docs/sdd/SFN_HISTORY/`), que leva achado `SF-SFNX` a `glue-infra-reviewer`, o mesmo dono de `SF-SFN`. Leitura anterior de **41** —
```

```text
| Fixtures golden | **528** em 57 domínios —
| Fixtures golden | **538** em 58 domínios — as **10** acrescidas formam o domínio novo `fixtures/sfn_history/` (2026-09-20, feature `docs/sdd/SFN_HISTORY/`), sintéticas a partir da forma de evento publicada em `API_GetExecutionHistory`; duas trazem a definição ASL ao lado do histórico, em subdiretórios separados, porque a produção os separa em dois verbos. Leitura anterior de **528** em 57 domínios —
```

```text
| Fontes oficiais vigiadas | **262** (247 móveis, 15 fixas) —
| Fontes oficiais vigiadas | **263** (248 móveis, 15 fixas) — a acrescida é `API_GetExecutionHistory`, citada pelas três regras `SF-SFNX` (2026-09-20, feature `docs/sdd/SFN_HISTORY/`). As outras três URLs que elas citam já estavam no lock, por `rules/catalog/stepfunctions.yaml`. Leitura anterior de **262** (247 móveis, 15 fixas) —
```

A linha "Regras com `runtime_scope` não-vazio" **não muda** (continua 26): as três
declaram `{}`. A linha "Coordenadores" **não muda** (continua 12): nenhum agente novo.
A linha "Perguntas do gold set de recuperação" é **derivada das regras e cresce
sozinha** — o AIRFLOW_DAG foi surpreendido por ela; leia o que
`check_status_numbers.py` medir e publique esse número.

`README.md`: linha 44, `Os 40 extratores emitem 236 kinds distintos` →
`Os 40 extratores emitem 237 kinds distintos`; e
`**161** regras de diagnóstico em YAML, **161 delas executáveis**` →
`**164** regras de diagnóstico em YAML, **164 delas executáveis**`.

E a prosa auditada:

- `docs/guia/06-extrair-julgar-compor.md`: linha 86, `emitem 236 kinds` →
  `emitem 237 kinds`; linha 232, `nenhum dos 236 kinds` → `nenhum dos 237 kinds`.
- `docs/guia/07-conhecimento-e-catalogo.md`:
  - `desse conhecimento: **161** regras de` → `desse conhecimento: **164** regras de`;
  - `**161 delas executáveis**, ou seja, todas` → `**164 delas executáveis**, ou seja, todas`;
  - `mais **41** rotas determinísticas` → `mais **42** rotas determinísticas`;
  - ``As 161 executáveis se distribuem em 29 áreas (medido em 2026-09-19 com `area_of`):``
    → ``As 164 executáveis se distribuem em 30 áreas (medido em 2026-09-20 com `area_of`):``;
  - ``(fronteira do Spark 4), `SF-SFN` 4 (como o AWS`` →
    ``(fronteira do Spark 4), `SF-SFNX` 3 (o que a execução do Step Functions registrou), `SF-SFN` 4 (como o AWS``;
  - `Cada uma das 161 carrega` → `Cada uma das 164 carrega`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_sfn_history.py tests/test_fixtures_golden_sfn_history.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_criterio_de_dominio.py -q
```

O primeiro comando fecha AC4, AC5 e AC6: o golden prova as duas regras que o histórico
sozinho sustenta (`SF-SFNX-002` e `SF-SFNX-003`) e a que exige o confronto
(`SF-SFNX-001`), mais as duas metades da AC4 — `retry_acima_do_declarado` com o ASL, e
`historico_sem_asl` sem ele. O último é o `verified_by` da AC8
(`test_todo_coordenador_tem_rota_por_artefato`).

**Sobre a AC8, e uma ressalva honesta:** o teste que o `define` fixa
(`test_todo_coordenador_tem_rota_por_artefato`) passa **antes e depois** desta feature,
porque o `glue-infra-reviewer` já tem rota por artefato (`AGENT-002` e `AGENT-086`). O
que de fato ficaria **vermelho** sem a área completa é, no mesmo arquivo,
`test_todo_coordenador_declara_area_que_julga` — `SF-SFNX` em `rule_areas` sem regra no
catálogo reprova na asserção `areas <= todas`. Rode o arquivo inteiro, não só o teste
nomeado, e cite os dois no relatório do build.

### 5. Gates vizinhos

Regra, `runtime_scope`, área, extrator, corpus, routing, agent, fontes (seções de
`docs/gates-por-mudanca.md`), **um comando por vez**:

```bash
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py -q
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py tests/test_rules_action_field.py tests/test_rules_campos_de_lista.py -q
python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q
python -m pytest tests/test_databricks_rule_audit.py tests/test_agentic_executor_ordering.py tests/test_harness_untrusted.py tests/test_sf_stubs.py -q
python -m pytest tests/test_agentic_debate_evidence.py tests/test_debate_suite.py tests/test_fixtures_golden_debate.py -q
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
`test_agents_parity.py`.)

`test_rules_threshold_mutation.py` tem de passar **SEM entrada nova** em
`FRONTEIRA_SEM_GOLDEN`: `retry_dentro_do_declarado` existe para matar a troca `>`→`>=`
da `expr` da `SF-SFNX-001`, e as outras duas regras não têm `expr`. Se o teste pedir
exceção, a fixture correspondente é que está errada — confira que ela tem
`tentativas_observadas == teto_declarado` de verdade.

`test_agentic_executor_ordering.py` está na lista por causa do teto de 12 de
`runtime.wall_clock`: se ele ficar vermelho, alguma regra `SF-SFNX` declarou esse eixo
em `action.moves`, e a correção é tirar o eixo, não mexer no teste.

O gate de lastro reprova de novo pelo corpus de `.py`: agora é **um** arquivo novo (o
módulo de golden; as dez fixtures são `.json`), 758 → 759. Remedie pelos ids que a saída
listar, como em T1.

### 6. Commit

`feat(rules): add the SF-SFNX area judging what a Step Functions execution recorded`,
com no corpo: 3 regras (161 → 164), a área `SF-SFNX`, a rota `AGENT-088`, o kind
derivado `sfn.retry_observado` em `fuse`, 10 fixtures no domínio novo, 1 fonte nova, e a
allowlist de evidência do debate de 23 para 24.

## T4 — o documento de conhecimento, o manual de uso e os registros finais

### 1. O teste que falha

Esta tarefa não tem teste próprio: o vermelho é o do **lock de superfície**, que acusa o
documento de `knowledge/` novo no disco enquanto o lock ainda diz 54 (regra 26). O lock
de **fontes** não fica vermelho aqui: a URL da API já entrou em T3, citada pelas regras
— o que o `refresh_knowledge` acrescenta em T4 é só o vínculo `docs` dela.

Escreva `knowledge/stepfunctions/execution-history.md` (arquivo novo, inteiro):

~~~~markdown
# Histórico de execução do Step Functions: o que ele prova, e o que ele não prova

> **Lido em 2026-09-19.** A página de referência da API `GetExecutionHistory`, mais as
> três páginas do guia já citadas em
> [`glue-integration.md`](glue-integration.md). Quem consome: o extrator
> `sparkforge/facts/sfn_history.py` e as três regras de
> `rules/catalog/sfn-history.yaml`. Frase entre aspas é citação literal; o resto é
> leitura nossa, e diz de qual frase veio.

## 1. O que a API entrega, e o que ela recusa

- "Returns the history of the specified execution as a list of events." A resposta é
  uma **lista de eventos**, não um resumo: quem quiser tentativa, duração ou desfecho
  tem que derivá-los dos eventos.
- "This API action is not supported by `EXPRESS` state machines." O histórico de uma
  EXPRESS vai para o CloudWatch Logs, e o extrator daqui não o lê. Por isso a área
  `SF-SFNX` não tem nenhuma regra de EXPRESS: o artefato não existe.
- `includeExecutionData`: "You can select whether execution data (input or output of a
  history event) is returned. The default is `true`." **Sem ele não há `output`**, e
  sem `output` não há `JobRunId` para ler. O extrator emite
  `sfn.unresolved: execution_data_absent` e nenhum `sfn.job_run` — nunca um id
  inventado.
- Paginação: "If `nextToken` is returned, there are more results available". `maxResults`
  tem default 100 e máximo 1000. Uma saída salva **com** `nextToken` é uma página, não o
  histórico: sai `sfn.unresolved: truncated`, e o `status` da execução fica
  `unresolved` em vez de ser adivinhado.

## 2. A forma de cada evento, e o que ela sustenta

Todo evento tem `id`, `previousEventId`, `timestamp` e `type`.

| evento | campos que importam | o que sustenta |
|---|---|---|
| `ExecutionStarted` | — | o instante inicial da execução |
| `TaskStateEntered` | `stateEnteredEventDetails.name` | **o nome do estado** — a única fonte dele no histórico |
| `TaskScheduled` | `taskScheduledEventDetails` com `resource`, `resourceType`, `parameters`, `region`, `timeoutInSeconds` | **uma tentativa** começou; o serviço, o padrão de integração e o prazo declarado |
| `TaskStarted` | `taskStartedEventDetails` | a chamada saiu |
| `TaskSubmitted` | `taskSubmittedEventDetails.output` | o `JobRunId` do Glue (§3) |
| `TaskSucceeded`, `TaskFailed`, `TaskTimedOut`, `TaskStartFailed`, `TaskSubmitFailed` | `error` e `cause` nos que os têm | **a tentativa terminou**, e como |
| `TaskStateExited` | `stateExitedEventDetails.name` | o estado saiu |
| `ExecutionSucceeded`, `ExecutionFailed`, `ExecutionAborted`, `ExecutionTimedOut` | `error` e `cause` | **o desfecho da execução** |

**O encadeamento é por ramo, e é ele que pareia.** `previousEventId` aponta para o
evento anterior *daquele ramo*: dentro de `Parallel` e de `Map`, eventos de ramos
diferentes se intercalam na ordem de `id`, mas cada cadeia continua correta. Por isso o
extrator sobe a cadeia a partir do próprio evento — de um `TaskScheduled` até o
`TaskStateEntered`, de um terminal até o `TaskScheduled` — em vez de usar "o último
visto". Cadeia quebrada, raiz alcançada sem achar, ou ciclo: `sfn.unresolved` nomeado,
nunca um chute.

## 3. O `JobRunId` do Glue, e por que ele é uma lacuna

A página da API **não** descreve a forma do `output` do `TaskSubmitted` de uma
integração com o Glue. A página de integração diz que o `JobName` é inserido na
resposta, e nada mais. O extrator então lê defensivamente: `output` como objeto **ou**
como string com JSON dentro, e três chaves na ordem — `JobRunId`, `Id`, e `JobRun.Id`.
O que não casa sai em `sfn.unresolved: job_run_id_unrecognized` **com as chaves de topo
que ele viu**, que é exatamente o dado de que um histórico real precisa para fechar a
lacuna 1 abaixo.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-SFNX-001 | os agendamentos do Task no histórico passam do teto `1 + MaxAttempts` que o ASL declara | qual dos dois está errado; quantos JobRuns a falha produziu (lacuna 1 de `glue-integration.md`); custo |
| SF-SFNX-002 | a tentativa `.sync` terminou em `TaskTimedOut`, e o desfecho do JobRun **não foi observado** | que o job continuou rodando, nem que ele parou (lacuna 2); custo do run órfão (regra 13) |
| SF-SFNX-003 | a execução parou (`Aborted`/`TimedOut`) com o Task `.sync` agendado e sem terminal próprio | o que a AWS faz com o JobRun nesse caso (lacuna 2); custo |

**Nenhuma das três atribui custo, e a recusa é de desenho.** Dizer "você pagou por um
JobRun órfão" exige o `dpu_seconds` de um run que ninguém leu, e é o que a regra 13 do
`CLAUDE.md` proíbe; dizer o valor em dólar exige `cost_basis` (regra 25). O que o
histórico entrega é o `JobRunId` — e é por ele que `sparkforge finops` responde custo
com `dpu_seconds` medido.

## 5. Lacunas nomeadas

1. **A forma do `output` do `TaskSubmitted` do Glue.** Não publicada (§3). O extrator lê
   três formas e nomeia o resto. O que destrava: **um histórico real** com
   `includeExecutionData` ligado, lido na conversa e nunca commitado — o
   `job_run_id_unrecognized` que ele produzir traz as chaves de topo, e elas fecham a
   lacuna numa linha.
2. **O JobRun quando o Task expira ou a execução é abortada.** A descrição do abort do
   `.sync` não cobre o timeout do Task, e nada diz o que acontece com o JobRun quando a
   execução termina em `ExecutionAborted`. Por isso `SF-SFNX-002` e `SF-SFNX-003`
   afirmam **não observação**, e o conserto que elas propõem é declarar a limpeza em vez
   de confiar no default. O que destrava: frase oficial, ou um par
   (histórico, `get-job-run`) real.
3. **A composição dos retries continua aberta.** Esta feature mede quantas vezes o
   **Task** foi agendado; ela não mede quantos **JobRuns** uma falha produziu, porque o
   `MaxRetries` do próprio job é outra camada. Ver a lacuna 1 de
   [`glue-integration.md`](glue-integration.md). O que destrava: o par entre um
   histórico real com falha e os JobRuns do mesmo intervalo
   (`sparkforge collect glue-job-runs`) — e o `sfn.job_run` desta feature é metade dele.
4. **Histórico real não observado.** O corpus `fixtures/sfn_history/` é sintético,
   montado a partir da forma de evento publicada. Ele prova o **mecanismo**, não a
   resposta (U2 de `docs/sdd/SFN_HISTORY/define.md`).
5. **EXPRESS fora de alcance.** A API não o suporta (§1), e o CloudWatch Logs tem outro
   formato. Nada aqui vale para EXPRESS.
6. **Map distribuído (`mapRunArn`) não é lido.** Os eventos `MapRun*` entram na lista de
   tipos conhecidos e não produzem fact: o extrator não segue as execuções filhas de um
   Distributed Map, e o que roda dentro delas fica fora do histórico da mãe.
7. **`sfn.*` do histórico sai com `line: 0`.** O extrator lê JSON sem posição de linha, e
   o `subject.symbol` é `<estado>#<ordem>`. `sparkforge report github` não ancora esses
   achados numa linha do arquivo.

## Fontes

- Referência da API do AWS Step Functions — `GetExecutionHistory`: a lista de eventos, o veto a EXPRESS, `includeExecutionData`, `nextToken`/`maxResults` e a forma de cada `*EventDetails`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — integração com o AWS Glue: o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
~~~~

### 2. Rodar e ver falhar

```bash
python -m pytest "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches" -q
```

Falha esperada: `AssertionError` com `document_count` 55 medido contra 54 no lock (e o
`by_name_sha256` divergindo junto).

### 3. Código mínimo

**`knowledge/stepfunctions/glue-integration.md`** — a lacuna 1 passa a apontar o artefato
que a destrava (D7). Troque

```markdown
1. **Composição dos retries.** Nenhuma das duas documentações descreve como o retry do
   Step Functions compõe com o `MaxRetries` do Glue. O `.sync` acompanha o `JobRunId`
   que o `StartJobRun` devolveu, e o retry do Glue é outro JobRun. O que destrava
   afirmar a contagem de tentativas: um histórico de execução real com falha
   (`get-execution-history`) junto dos JobRuns do mesmo intervalo, ou documentação
   oficial que a descreva.
```

por

```markdown
1. **Composição dos retries.** Nenhuma das duas documentações descreve como o retry do
   Step Functions compõe com o `MaxRetries` do Glue. O `.sync` acompanha o `JobRunId`
   que o `StartJobRun` devolveu, e o retry do Glue é outro JobRun. O que destrava
   afirmar a contagem de tentativas: um histórico de execução real com falha
   (`get-execution-history`) junto dos JobRuns do mesmo intervalo, ou documentação
   oficial que a descreva.

   **Metade disso já é mecanismo, desde 2026-09-20.**
   [`execution-history.md`](execution-history.md) e o verbo `analyze sfn-history` leem o
   histórico salvo e entregam o número de agendamentos do Task e o `JobRunId` de cada
   um; `SF-SFNX-001` confronta esse número com o teto declarado aqui. O que continua
   faltando é o **outro lado**: os JobRuns do mesmo intervalo, que dizem quantas vezes
   o job rodou de fato. A lacuna é de artefato real, não de mecanismo.
```

E a tabela do §4 do mesmo documento, na linha da `SF-SFN-004`: troque

```markdown
| SF-SFN-004 | as duas camadas de retry existem sobre o mesmo job `.sync` | quantas vezes o job roda numa falha (lacuna 1) |
```

por

```markdown
| SF-SFN-004 | as duas camadas de retry existem sobre o mesmo job `.sync` | quantas vezes o job roda numa falha (lacuna 1); o lado medido disso é `SF-SFNX-001`, que conta os agendamentos do Task no histórico |
```

**`knowledge/INDEX.md`** — o documento novo. A seção de orquestração **não existe** nesta
árvore (`glue-integration.md` também está fora do índice), então ela nasce aqui, com os
dois. Troque

```markdown
### Transversal
```

por

```markdown
### Orquestração

| Arquivo | Conteúdo |
|---|---|
| [`stepfunctions/glue-integration.md`](stepfunctions/glue-integration.md) | Como uma state machine do AWS Step Functions dispara o job Glue: padrões de integração, `.sync`, retry declarado, os defaults publicados e as seis lacunas |
| [`stepfunctions/execution-history.md`](stepfunctions/execution-history.md) | O que o **histórico de execução** prova: a forma de cada evento, como uma tentativa é pareada pelo encadeamento, o `JobRunId` do Glue, e o que as regras `SF-SFNX` afirmam — e o que elas recusam afirmar |

### Transversal
```

**Lock de fontes** (o vínculo `docs` da URL da API passa a citar o documento novo):

```bash
python scripts/refresh_knowledge.py --offline --update
```

**Manifesto offline** — o `sha256` pela função que o gate confere, nunca por outro hash.
Dois documentos mudam: o novo, e o `glue-integration.md`, porque a lacuna 1 e a tabela
foram editadas.

```bash
python -c "import json; from pathlib import Path; from sparkforge.tools.offline import _content_sha256; p = Path('knowledge/offline-manifest.json'); m = json.loads(p.read_text(encoding='utf-8')); alvos = {'knowledge/stepfunctions/execution-history.md': 'execution-history', 'knowledge/stepfunctions/glue-integration.md': 'glue-integration'}; m['documents'] = [d for d in m['documents'] if d['path'] not in alvos] + [{'path': k, 'title': v, 'sha256': _content_sha256(Path(k))} for k, v in alvos.items()]; m['documents'].sort(key=lambda d: d['path']); p.write_bytes((json.dumps(m, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))"
```

(O manifesto está ordenado por `path` e gravado como `json.dumps(indent=2)` mais `\n` —
medido nesta árvore; `write_bytes` evita o CRLF do Windows.)

**`parity.yaml`**, na capacidade que T2 acrescentou: troque

```yaml
    cli: [analyze sfn-history]
    platforms:
```

por

```yaml
    cli: [analyze sfn-history]
    knowledge:
      - knowledge/stepfunctions/execution-history.md
    platforms:
```

**Manual de uso** — `docs/guia/usos/step-functions.md` ganha a seção do histórico (D7 do
manifesto). A página já existe, e os links relativos dela são `../../../` — três níveis,
porque ela mora em `docs/guia/usos/`.

Troque o parágrafo de abertura

```markdown
O SparkForge **não** chama a API do Step Functions e não lê histórico de execução. Ele
lê a definição. Todos os exemplos usam arquivos sintéticos de `fixtures/stepfunctions/`.
```

por

```markdown
O SparkForge **não** chama a API do Step Functions: ele lê **artefato salvo**. São dois,
e a diferença entre eles é a razão desta página ter duas metades — a **definição** diz o
que devia acontecer, e o **histórico de execução** diz o que aconteceu. Todos os exemplos
usam arquivos sintéticos de `fixtures/stepfunctions/` e `fixtures/sfn_history/`.
```

E acrescente, logo antes da seção `## O que ele não faz`:

~~~~markdown
## A outra metade: o histórico de execução

A definição diz quantas vezes o Task **pode** ser reagendado. Só o histórico diz quantas
vezes ele **foi** — e é ele que separa retry declarado de retry observado.

```bash
# 1. Salvar o historico (o operador roda isto na conta; o SparkForge nao chama a API)
aws stepfunctions get-execution-history \
  --execution-arn <arn> --include-execution-data --max-results 1000 \
  > /tmp/sf/execucao.json

# 2. Extrair os facts do historico
sparkforge analyze sfn-history \
  --path fixtures/sfn_history/task_timed_out_sync/input/historico \
  --out /tmp/sf/facts_hist.json

# 3. Julgar: SF-SFNX-002 e 003 leem so o historico
sparkforge judge --facts /tmp/sf/facts_hist.json

# 4. Com a definicao do MESMO state machine: fundir, e o confronto aparece
sparkforge analyze sfn-history \
  --path fixtures/sfn_history/retry_acima_do_declarado/input/historico \
  --out /tmp/sf/hist.json
sparkforge analyze step-functions \
  --path fixtures/sfn_history/retry_acima_do_declarado/input/definicao \
  --out /tmp/sf/asl.json
sparkforge fuse --facts /tmp/sf/hist.json --facts /tmp/sf/asl.json --out /tmp/sf/juntos.json
sparkforge judge --facts /tmp/sf/juntos.json
```

**`--include-execution-data` não é opcional na prática**: sem ele não há `output` no
`TaskSubmitted`, e sem `output` não há `JobRunId`. O SparkForge não inventa um: sai
`sfn.unresolved` com `execution_data_absent`.

**Se a saída tiver `nextToken`, ela é uma página, não o histórico.** O SparkForge lê o
que está lá, marca `truncated`, e deixa o `status` da execução em `unresolved` — nunca
sucesso por suposição.

| kind | um por | o que diz |
|---|---|---|
| `sfn.execution` | arquivo | `status` pelo evento terminal (`unresolved` quando ele não está no arquivo), duração, contagem de eventos, `truncated` |
| `sfn.attempt` | tentativa de Task (`<estado>#<ordem>`) | nome do estado, ordem, padrão de integração, resultado, duração, `error`, `cause`, e o prazo declarado do Task |
| `sfn.job_run` | `JobRunId` lido do `output` do `TaskSubmitted` | o id, o `JobName` quando vem junto, e de qual chave ele foi lido |
| `sfn.retry_observado` | estado, só em `fuse` com o ASL | tentativas observadas contra o teto declarado |
| `sfn.unresolved` | o que não deu para ler ou parear | truncamento, cadeia quebrada, tipo de evento desconhecido, `execution_data_absent`, `job_run_id_unrecognized`, ASL ausente ou ambíguo |
| `sfn.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

### As três regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-SFNX-001` | os agendamentos do Task passam do teto `1 + MaxAttempts` que o ASL declara (exige os dois artefatos no `fuse`) | P2 |
| `SF-SFNX-002` | a tentativa `.sync` terminou em `TaskTimedOut`: o desfecho do JobRun que ela acompanhava não foi observado | P1 |
| `SF-SFNX-003` | a execução terminou em `Aborted` ou `TimedOut` com o Task `.sync` agendado e sem evento terminal próprio | P1 |

**Nenhuma delas fala em custo.** Atribuir custo a uma tentativa exigiria o `dpu_seconds`
de um run que ninguém leu. O que o histórico entrega é o `JobRunId` — e é com ele que
`sparkforge finops` responde custo com medida de verdade.

**EXPRESS não passa por aqui**: a API não suporta `get-execution-history` para ela, e o
histórico dela vai para o CloudWatch Logs.
~~~~

E na seção `## O que ele não faz`, troque

```markdown
- Não lê histórico de execução (`get-execution-history`) nem coleta da conta: o
  operador salva a saída do `describe-state-machine` em arquivo.
```

por

```markdown
- Não coleta da conta: o operador salva a saída do `describe-state-machine` e a do
  `get-execution-history` em arquivo, e aponta cada verbo para o seu.
- Não lê histórico de state machine EXPRESS: a API não o suporta.
- Não segue as execuções filhas de um Distributed Map (`mapRunArn`).
```

E na seção `## Referência`, troque

```markdown
- As frases citadas e as lacunas: [`knowledge/stepfunctions/glue-integration.md`](../../../knowledge/stepfunctions/glue-integration.md).
```

por

```markdown
- As frases citadas e as lacunas da definição: [`knowledge/stepfunctions/glue-integration.md`](../../../knowledge/stepfunctions/glue-integration.md).
- As frases citadas e as lacunas do histórico: [`knowledge/stepfunctions/execution-history.md`](../../../knowledge/stepfunctions/execution-history.md).
- As regras do histórico: [`rules/catalog/sfn-history.yaml`](../../../rules/catalog/sfn-history.yaml).
- O corpus do histórico: [`fixtures/sfn_history/`](../../../fixtures/sfn_history/).
```

**`docs/gates-por-mudanca.md`** — nada de novo entra, mas a seção "Acrescentar um CORPUS
de fixture novo" ganha o exemplo do par de artefatos. Troque

```markdown
## Acrescentar ou alterar um cenário de `evals/holdout/`
```

por

```markdown
> **Corpus com DOIS artefatos do mesmo domínio** (2026-09-20, `fixtures/sfn_history/`):
> quando a fixture precisa de dois artefatos que a produção lê por **verbos diferentes**
> — ali, a definição ASL e o histórico de execução —, eles ficam em **subdiretórios**
> de `input/`, e o `_extract` do golden chama cada extrator no seu. Juntos no mesmo
> diretório, cada extrator leria o arquivo do outro e sairia um `unresolved` cruzado por
> fixture: ruído que não é medida, e que muda todo golden quando o outro extrator muda.

## Acrescentar ou alterar um cenário de `evals/holdout/`
```

**Superfície** (regra 26):

```bash
python scripts/check_surface_lock.py --update
```

O crescimento em bytes vai no corpo do commit.

Nenhuma linha da tabela *Números correntes* de `docs/superpowers/STATUS.md` se move nesta
tarefa: a URL entrou em T3, e não há medida publicada de documento de `knowledge/` — o
que trava esse crescimento é `docs/surface.lock.json`.

### 4. Rodar e ver passar

```bash
python -m pytest "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches" -q
python scripts/verify_offline_bundle.py
python scripts/check_status_numbers.py --strict
```

Os dois últimos são os `verified_by` da AC9 e da AC10: `"ok": true` e
`0 divergencia(s)`.

### 5. Gates vizinhos

"Editar um documento em `knowledge/`", a referência gerada e os números:

```bash
python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q
python -m pytest tests/test_capability_parity.py tests/test_surface_lock.py tests/test_reference_docs.py -q
python -m pytest tests/test_status_numbers_gate.py tests/test_criterio_de_dominio.py tests/test_sdd.py -q
python -m pytest tests/test_docs_coverage.py tests/test_knowledge_freshness.py -q
python -m pytest tests/test_bootstrap_budget.py -q
python scripts/check_vnext_claims.py
```

`test_reference_docs.py` confere que todo comando que o manual ensina existe
(`analyze sfn-history`, `analyze step-functions`, `fuse`, `judge`) e que os links
relativos resolvem — é ele que pega o erro de profundidade (`../../` em vez de
`../../../`).

### 6. Commit

`docs(knowledge): cite the Step Functions execution history sources and extend the usage guide`,
com o crescimento da superfície em bytes no corpo.

## Antes de fechar a feature

```bash
sparkforge sdd stamp --repo . docs/sdd/SFN_HISTORY/plan.md
sparkforge sdd check --repo . --feature SFN_HISTORY
```

(A sintaxe do `stamp` é `sdd stamp --repo . <artefato>` — o `--feature`/`--phase` que o
plano do AIRFLOW_DAG escreveu não existe na CLI.)

E, quando os quatro commits estiverem de pé, a suíte **em lotes, um por vez**, pela
receita de `tests/test_suite_batches.py::LOTES` — nunca a suíte inteira num processo só,
e nunca com edição na árvore ao mesmo tempo. Os dois arquivos de teste novos caem sozinhos
nos lotes existentes, porque `LOTES` é por glob: `test_sfn_history.py` no lote `g-z`, e
`test_fixtures_golden_sfn_history.py` no lote `goldens-5`. Nenhuma edição em
`test_suite_batches.py`.

Por fim, `python -m pytest tests/test_fixtures_golden*.py -q` **sem regenerar**: é o SC2
do `define`, e nenhum golden de achado existente pode ter mudado. O único de outro
domínio que esta feature toca é `fixtures/debate/retomada/expected/brief.json`, e ele foi
regenerado em T3, na mesma tarefa que mudou a allowlist.

## Dúvidas

O manifesto do design foi seguido; estes são os pontos em que ele ficou curto, sobrou, ou
em que o plano precisou decidir. Todos estão repetidos no corpo, onde importam.

1. **O `#91` (AIRFLOW_DAG) não está nesta árvore, e todos os números deste plano são de
   antes dele.** A branch `sdd/airflow-dag` existe e não foi mergeada; `origin/main`
   ainda é `b324aa3b`. Se ela entrar antes desta feature, **todas** as linhas da tabela
   *Medidas desta árvore* mudam (regras 161→165, áreas 29→30, tools 107→108, extratores
   39→40, kinds 233→239, rotas 41→42, fixtures 528→540, fontes 262→265, allowlist do
   debate 23→24) e o plano precisa ser remedido antes de executar. O plano manda publicar
   o que o gate medir; esta é a razão.
2. **A AC8 aponta um teste que já passa.** `test_todo_coordenador_tem_rota_por_artefato`
   é verde antes e depois, porque o `glue-infra-reviewer` já tem `AGENT-002` e
   `AGENT-086`. O teste que de fato fica vermelho sem a área completa é
   `test_todo_coordenador_declara_area_que_julga`, no mesmo arquivo. O plano mantém o
   nome que o `define` fixou e manda rodar o arquivo inteiro. **Confirme** se quer o
   `define` recarimbado com o segundo nome ao lado.
3. **Kinds compartilhados: +3 em T1, não +5.** D1 escolheu o prefixo `sfn.` e listou
   cinco kinds, mas dois deles (`sfn.unresolved`, `sfn.analyzed`) já são de
   `stepfunctions.py`. Três consequências que o desenho não menciona e o plano trata: a
   contagem de kinds sobe 4 no total (3 + o derivado); o teste de sentinela do golden
   precisa filtrar por `provenance.extractor`, porque contar por kind misturaria os dois
   extratores; e `test_every_kind_of_every_extractor_appears_in_some_golden[sfn_history]`
   passa para esses dois kinds mesmo que o corpus novo não os produza. **Se o operador
   preferir kinds próprios** (`sfn.history_unresolved`, `sfn.history_analyzed`), o D1
   muda e o plano com ele.
4. **Uma razão de `sfn.unresolved` a mais que D1: `state_name_absent_in_asl`.** "O ASL
   está no case e não declara esse estado" é diferente de "não há ASL" — uma é erro de
   pareamento, a outra é lacuna — e juntá-las esconderia a primeira atrás da segunda.
5. **Uma decisão de corpus que D8 não previu: subdiretórios.** D8 fala em "o par ASL +
   histórico" sem dizer onde. O plano os separa em `input/definicao/` e
   `input/historico/`, e a razão está no §3 de *O que este plano refina do desenho*. Isso
   também muda o `regen_sfn_history` e o `_extract` do golden, que precisam ser o par um
   do outro.
6. **Páginas geradas e espelhos que o manifesto lista pela metade.** O manifesto lista os
   três espelhos do `sync_skills.py` e o `.codex/*.toml`, e lista quatro páginas de
   `docs/guia/referencia/`. Ele **não** lista `docs/gates-por-mudanca.md` como alvo de T4
   (o plano acrescenta lá a nota sobre corpus com dois artefatos) nem
   `knowledge/INDEX.md` como criação de seção. O `files` de T4 inclui os dois; confirme
   ou reduza.
7. **`category: stepfunctions-execution` é vocabulário novo.** O campo é livre
   (`tests/test_rules_loader.py` só exige presença), e o design não o fixou. A alternativa
   era reusar `stepfunctions`, que economizaria uma categoria e borraria a distinção que
   a área existe para fazer. Escolhido o primeiro; é reversível numa linha.
8. **Os cinco goldens de assessment.** O manifesto lista um só
   (`glue_40_para_60_salto_longo`) e diz que ele representa "três cenários e dois
   holdout". O `files` de T3 lista os cinco por extenso; confirme ou reduza.
9. **O golden do debate entrou no manifesto, e ainda assim merece o aviso.** D-manifesto
   lista `fixtures/debate/retomada/expected/brief.json`, o que é um avanço sobre as duas
   features anteriores — nas duas ele foi esquecido e a rodada de goldens acusou depois.
   O plano dá o comando de regeneração pelo caminho do próprio teste, em T3. Se o comando
   de uma linha ficar ilegível na prática, escrever um script de três linhas no
   scratchpad é equivalente — **o que não é equivalente é editar o JSON à mão.**
10. **O que continua fora, e é bom que esteja.** Coletor com credencial, EXPRESS,
    Distributed Map, custo por tentativa, e **fechar a lacuna U1 com número**: a feature
    entrega o mecanismo que a destrava (o `job_run_id_unrecognized` com as chaves de
    topo), e a resposta exige um histórico real, que nunca entra no repositório.
