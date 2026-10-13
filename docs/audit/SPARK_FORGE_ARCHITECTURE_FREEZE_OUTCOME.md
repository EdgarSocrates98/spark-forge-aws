# SPARK FORGE — ARCHITECTURE FREEZE OUTCOME

Brief final da onda de final-hardening. Cada afirmacao aponta para commit,
arquivo ou teste; o que nao foi provado esta classificado, nao arredondado.

## STATUS

**Spark Forge — Architecture Freeze Candidate.** Sem P0 architectural gap
ou core runtime inconsistency conhecido. Restantes sao `BACKLOG`,
`EXPERIMENTAL`, `DEFERRED`/`DEFERRED_EXTERNAL` — todos nomeados abaixo.

- **BASE_SHA:** `a1bf2ada47e182f52b1253910b92e45ef3508ecc` (`origin/main`, merge do PR #125)
- **FINAL_SHA:** `5865b05` — ultimo commit que toca codigo/testes; os
  commits acima dele sao docs-only (re-medicoes de claims e este
  relatorio).
- **BRANCH:** `devin/final-hardening-freeze`
- **Fonte do pedido:** `prompt_evo_final_hardening.md` (fora da arvore versionada)

## OBJECTIVE

Fechar os seams de convergencia restantes e colocar o projeto em
architecture freeze temporario, passando o modo para
**Evaluation-Driven Engineering**. CLOSURE > EXPANSION foi mantida:
um modulo novo (`handoff.py`), um arquivo de teste, o resto e
documentacao, flags e re-ancoragem de evidencia.

## HANDOFF_CONVERGENCE

**DONE.** `RoleContextPlan → AgentHandoff` tinha o contrato mas nenhuma
admissao — nada consultava o plano do receptor. `sparkforge/agentic/handoff.py`
agora admite cada handoff contra o `RoleContextPlan` do receiver com
`ALLOW`/`DENY`/`REVIEW`, preservando `DATA_ONLY` e carregando
sender/recipient/trust/taint/unresolved/evidence_refs. Confused-deputy
travado: quem nao tem autoridade nao a ganha mandando handoff para outra
role (o plano do receiver filtra; a autoridade nunca atravessa).
`tests/test_agentic_handoff.py` — 26 testes.

## TRUST_FLOORS

**DEFERRED — correto.** Inventario de producers: nenhum producer de
contexto emite `trust` em items (o novo `admit_handoff` e o unico que
rotula). Subir `trust_floor` acima de `UNKNOWN` tornaria as roles
inutilizaveis sem ganho — §15/§20 do prompt: `UNKNOWN` e o correto, nao
zero-evidencia. Documentado no docstring de `role_plans.py`. Floor por
kind (§18) fica como opcao futura atras de um producer que sustente.

## MODEL_ROUTER

**SHADOW mantido — correto.** `AdaptiveModelRouter` segue
`ModelRouteMode.SHADOW`, `activation_ready=False`,
`provider_availability=unresolved` (offline por desenho). Nada ativado;
requisitos de `ACTIVE` (corpus rotulado, scorecards persistentes,
comparacao shadow, evidencia de economia, rollback, provider
availability) documentados em `ADR-013`.

## DECISION_PLANE

Sem mudanca — observa a rota atual em shadow; receipts
content-addressed preservam status/route/unresolved. Nao promovido.

## MEMORY

Sem mudanca — `MEMORY` rank = evidencia, nao autoridade; recall cap
`limit=5` auditado em `MCP-PAGINATION-AUDIT.md`.

## CONTEXT

Sem mudanca estrutural — o gateway continua fail-closed para plano
desconhecido/malformado, e agora e o filtro que o handoff consulta.

## AGENTOPS

**Clarificado.** `agentops_critical_path` documentado como perfil de
duracao medido (top spans por `duration_seconds`, retries por nome
repetido, waiting entre `end_time` consecutivos) — nao o caminho
critico causal do metodo CPM, que exigiria o DAG de dependencias que o
ledger nao guarda. Nome mantido (nao quebrar CLI por nomenclatura);
docstring + `description` do tool declaram a semantica.

## MCP

**BACKLOG com gatilho.** Auditoria em `MCP-PAGINATION-AUDIT.md`: todos
os `analyze_*` paginam via `paginate_items`/`next_cursor`; code-intel
tem cap estrutural; memory tem `limit=5`. Unica superficie sem teto:
`agentops_timeline` (todos os spans de um run). Classificada BACKLOG —
gatilho = consumidor real paginar um timeline (offset/limit +
`next_cursor` sobre a convencao existente). Superficie continua 143
tools / 7 compact; `surface.lock.json` atualizado pela mudanca de
descricao legitima e declarada.

## A2A

**EXPERIMENTAL mantido — spec revista.** `A2A_EXPERIMENTAL.spec_reviewed`
-> `True` apos revisao doc-only contra a spec **v1.0.x**; divergencias
medidas e nomeadas no proprio flag e em `docs/audit/A2A-SPEC-REVIEW.md`
(metodo `tasks/send`->`message/send`, forma do AgentCard, serializacao
de enum ProtoJSON vs binding JSON). Nenhuma mudanca de comportamento;
adapter segue `a2a-ready`, nunca implementacao da spec.

## FORGE_PROTOCOL

**v1 preservado, sem quebra.** `ForgeTask`/`ForgeResult` intactos;
`unresolved` -> `unknown` (nunca `completed`); evidence_bundle separado.
Forger readiness verificado: discovery, submission, result, evidence e
unresolved continuam possiveis — ver `FORGE-KERNEL-READINESS.md`.

## DOMAIN_CORE

**Freeze de especializacao respeitado (§67).** Nada em Spark/Glue/EMR/
Lake Formation/Iceberg/Kafka/Kinesis/Flink/Streaming/CDC/Parquet/Athena/
DQ/FinOps foi tocado — nenhuma regressao real exigiu a excecao do §68.

## EVAL_READINESS

`docs/audit/EVALUATION-PHASE-READINESS.md`: context bytes, utilizacao,
recall, tool calls, latencia, custo-observado e unresolved sao medidos
hoje; `provider_tokens` exige transcript do host; cloud-only e lab-only
nomeados; comparacao `economy`/`balanced`/`deep` executavel sobre o
mesmo cenario (Pareto, sem winner global inventado). Nenhum subsistema
novo criado.

## SUPPLY_CHAIN

Locks py3.10/3.11/3.12 atualizados (boto3/botocore/cryptography) —
commit proprio `a84fddc`. `gen_requirements --check`: OK (requirements
reflete pyproject). `gen_lock --check`: OK (3 locks, 160 entradas
pinadas com hash). `test_supply_chain` + `test_requirements_mirror` +
`test_ci_workflow`: 103 passed.

## TESTS

- **Focused suites (§70)** — handoff/trust, context, agentic, memory,
  router, decision, MCP, AgentOps, red-team:
  `python -m pytest tests/test_agentic_*.py tests/test_runtime_convergence_*.py
  tests/test_context_*.py tests/test_decision_*.py tests/test_router_agents.py
  tests/test_case_router.py tests/test_adapters_mcp*.py tests/test_adapters_tools.py
  tests/test_adapters_context_gateway.py tests/test_redteam_security.py
  tests/test_harness_untrusted.py -q -p no:randomly`
  → **1392 passed em 15min26s**.
- **Novo** `tests/test_agentic_handoff.py`: 26 testes — ALLOW/DENY/REVIEW,
  wrong-recipient, unknown-role, filtering por plano, floor, DATA_ONLY,
  taint monotonico (sem downgrade envelope->item), confused-deputy,
  round-trip, ids deterministicos.
- `check_status_numbers --strict`: **0 divergencias** (modulos agentic
  22->23 e testes agentic 540->597 remedidos e publicados).
- `ruff check` nos arquivos tocados: limpo; mypy em `handoff.py`: 0
  erros (baseline do repo permanece suja — pre-existente, nao desta onda).
- **Full suite** — `python -m pytest -q -p no:randomly`
  (14770 coletados): a execucao foi **interrompida em ~79%** para a
  tarefa de renomeacao do pacote pedida na mesma sessao. Ate o ponto de
  interrupcao: 1 falha observada na faixa de 66%; todos os arquivos de
  teste dessa faixa (`test_proof_*`, `test_provider_economy`,
  `test_receipt_*`, `test_recovery_*`, `test_redteam_security`,
  `test_refresh_knowledge`, `test_release_*`, `test_reporting_github`,
  `test_requirements_mirror` — 283 testes) **re-rodaram verdes em
  isolamento** — falha nao reproduzivel isolada, classificada como
  flake de ordenacao/estado, nao como bug de codigo. Fica registrado
  como UNRESOLVED, nao zero: a suite completa roda de novo sobre a
  arvore renomeada, que e a execucao que vale para o merge seguinte.

## CI

`CI_REMOTE = NOT_OBSERVED` — cota do GitHub Actions esgotada pelo
usuario; nao classificado como code failure (§71). Quando CI voltar:
full remote verification, sem nova wave (§72).

## BACKLOG

| gap | gatilho |
|---|---|
| `agentops_timeline` sem paginacao | consumidor real paginar um timeline |
| agent necessity eval (with/without) | corpus de tarefas reais rotulado |
| `RouteHealth` como primitivo | consumidor externo declarar os campos |
| alinhar adapter A2A a forma v1.0.x | driver/SDK A2A real consumir o adapter |

## DEFERRED / DEFERRED_EXTERNAL

| gap | classe | razao |
|---|---|---|
| trust_floor acima de UNKNOWN | DEFERRED | nenhum producer emite trust em items |
| scorecard persistence | DEFERRED (ADR-013) | sem consumidor real do arquivo |
| `provider_availability` | DEFERRED_EXTERNAL | core offline por desenho |
| `provider_tokens` | DEFERRED_EXTERNAL | so via transcript do host |
| Forge Kernel extraido | DEFERRED | sem segundo consumidor real |

## ARCHITECTURE_FREEZE

Declarado em `docs/audit/ARCHITECTURE-FREEZE.md`: planos congelados,
mudancas permitidas durante freeze, criterios de saida (gap medido +
ADR + evidencia de avaliacao) e o que NAO e blocker.

## Final gap table (§86)

| Gap | Status | Freeze blocker? |
|---|---|---|
| RoleContextPlan→AgentHandoff | DONE | nao — fechado |
| trust floors | DEFERRED | nao |
| provider availability | DEFERRED_EXTERNAL | nao |
| scorecard persistence | DEFERRED | nao |
| MCP pagination | BACKLOG | nao |
| A2A full server | EXPERIMENTAL | nao |
| lexical injection semantics | residual risk | nao |
| kernel extraction | DEFERRED | nao |

## NEXT

> **Evaluation-Driven Engineering.**

A proxima fase mede o que a plataforma entrega — os eixos ja sao
coletaveis (`EVALUATION-PHASE-READINESS.md`). Mudanca arquitetural a
partir daqui exige gap medido + ADR + evidencia de avaliacao.

*Este documento nao declara "100% complete" (§83). Classificacao por
eixo acima e o relato honesto do que esta fechado, deferido ou em
backlog.*
