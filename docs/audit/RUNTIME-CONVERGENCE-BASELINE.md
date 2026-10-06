# Runtime Convergence — Baseline Audit

**BASE_SHA:** `8f1581f7c54a4d55034afd6b4409c8ba19224070` (`origin/main`)
**BRANCH:** `devin/runtime-convergence-wave`
**DIRTY_STATE:** clean
**PYTHON_VERSION:** 3.14.6
**PACKAGE_VERSION:** 0.5.0
**Auditado em:** 2026-10-09
**Fonte do pedido:** `prompt_evo_runtime.md` (fora da árvore versionada, `.gitignore:81`)

Este documento é a matriz de convergência exigida antes de qualquer implementação:
para cada capacidade, diz qual é o dono canônico, o estado real medido no código e a
costura de integração que falta. Nenhuma feature começou antes desta tabela.

Vocabulário de estado:

| Estado | Significado |
|---|---|
| `INTEGRATED` | existe e está no caminho de execução real (verbo, tool ou executor) |
| `PARTIAL` | contrato/primitiva existe, mas não governa o caminho de execução |
| `ABSENT` | não existe |
| `DUPLICATE` | existe mais de uma implementação para a mesma capacidade |

## 1. Matriz de convergência

### Plano agentic (kernel e governança)

| Capacidade | Dono canônico | Estado | Evidência |
|---|---|---|---|
| Kernel de execução determinístico | `sparkforge/agentic/executor/run.py` (`run_executor`) | INTEGRATED | exposto via `arbitrate` em `adapters/_core.py:5673` |
| Declaração de capabilities de runtime | `sparkforge/agentic/runtime.py` | INTEGRATED | `RuntimeCapabilities`, `can_spawn_parallel`, `execution_strategy` |
| Orçamento de agente | `sparkforge/agentic/budget.py` | PARTIAL | usado no caminho do Decision Plane (`decision_plane.py:238`); fora do executor |
| Governor | `sparkforge/agentic/governor.py` | PARTIAL | só `DecisionPlaneService.active` resolve governor (`decision_plane.py:230`) |
| Recovery policy | `sparkforge/agentic/recovery.py` | PARTIAL | `RecoveryPolicy` completa (8 classes de falha); nenhuma chamada no caminho de execução |
| Segurança determinística | `sparkforge/agentic/security.py` | PARTIAL | validações existem; não são invocadas por `call_tool` |
| Trust plane | `sparkforge/agentic/trust.py` | PARTIAL | **FASE 3:** `call_tool` anexa `_trust` (`TOOL_OUTPUT`/`data_only`/`taint`) a todo resultado, recusa incluída; `taint` aterrissa em `metadata` do span; `TRUST_RANK` explícito substitui posição do enum em `RoleContextPlan.allows`. Falta: `RoleContextPlan` governando seleção de contexto (fase 4) e `AgentHandoff` no executor |
| Debate | `sparkforge/agentic/debate.py` + `executor/debate_run.py` | INTEGRATED | verbos `debate_*` em `_core.py` |
| Arbitragem | `sparkforge/agentic/arbitration.py` | INTEGRATED | chamado por `run_executor` |
| Blackboard | `sparkforge/agentic/blackboard.py` | INTEGRATED | append/read por executor |
| Checkpoint semântico | `sparkforge/agentic/checkpoint.py` | PARTIAL | `save`/`load` content-addressed; sem teste de fronteira de processo |
| Memória de decisão | `sparkforge/agentic/memory.py` | PARTIAL | `DecisionMemoryRecord` rico (freshness, invalidation, quarantine, runtime); recuperação precisa auditar se esses campos governam a seleção |
| Autonomia | `sparkforge/agentic/autonomy.py` | PARTIAL | `validate_autonomy_boundary` deliberadamente não chamado pelo executor (ver docstring `run.py:48-66`) |

### Plano de contexto

| Capacidade | Dono canônico | Estado | Evidência |
|---|---|---|---|
| Context Gateway | `sparkforge/context/gateway.py` | INTEGRATED | perfis `economy`/`balanced`/`deep` em `gateway_profiles.yaml` |
| Qualidade de contexto | `sparkforge/context/quality.py` | PARTIAL | `ContextQualityReport` computado em `_core.py:9595` para um verbo; métricas não governam promoção de política |
| Progressive disclosure | `sparkforge/context/progressive.py` | INTEGRATED | usado pelo Gateway |
| Medição de bytes de payload | `observability/context_ledger.py` | INTEGRATED | `call_tool` grava `payload_bytes` por chamada |
| Host token usage | `context/host_usage.py` | PARTIAL | consome transcript do host quando existe; ausência sai `tokens_unresolved` |

### Plano de economia

| Capacidade | Dono canônico | Estado | Evidência |
|---|---|---|---|
| Ledger unificado | `sparkforge/economy/ledger.py` | PARTIAL | `TokenLedger.reconcile` com defeito P0 (§3.2) |
| Router legado (tiers) | `sparkforge/economy/router.py` | INTEGRATED | `CapabilityModelRouter`, autoritativo hoje |
| Router adaptativo (scorecard) | `sparkforge/economy/model_router.py` | PARTIAL | `risk`/`required_reasoning`/`complexity` decorativos (§3.3) |
| Custo de provider | `sparkforge/economy/provider_cost.py` | PARTIAL | `None` honesto para custo incompleto; não reconciliado com ledger |
| Detector de desperdício | `sparkforge/economy/waste_detector.py` | DUPLICATE | `TokenWasteDetector.analyze_trace` duplica padrões de `agentops._waste` (duplicate_tool_call, premium_model_on_simple_task) |
| Decision Plane (shadow) | `economy/decision_plane.py` + `decision/` | INTEGRATED | `activation_ready` permanece `false` por contrato |

### Plano de observabilidade

| Capacidade | Dono canônico | Estado | Evidência |
|---|---|---|---|
| Tracer | `observability/tracer.py` | PARTIAL | `cost_basis` exigido para custo != 0; tokens sem status de medição (§3.1) |
| Store | `observability/store.py` | INTEGRATED | migração aditiva de colunas |
| AgentOps | `observability/agentops.py` | PARTIAL | `inspect`/`compare`/`baseline`; `models.tokens`/`cost` reportam 0 sem distinguir "não observado" (§3.1); sem timeline nem critical path |
| OTLP export | `observability/otlp.py` | INTEGRATED | `telemetry export`; recusa nomeada, ids determinísticos |

### Plano de protocolo e laboratório

| Capacidade | Dono canônico | Estado | Evidência |
|---|---|---|---|
| Forge Protocol (A2A) | `protocols/forge.py` | PARTIAL | contratos públicos completos; nenhum adapter produz/consome envelopes |
| Forge Lab | `sparkforge/lab/` | INTEGRATED | CLI-first, plan-only, oracle independente |
| MCP | `adapters/mcp.py`, `mcp_compact.py` | INTEGRATED | 141 tools full, 7 compact; sem matriz de conformidade |
| Doctor agentic | `_core.agentic_doctor` | PARTIAL | checa existência de arquivos, não prontidão do circuito |

## 2. Superfícies duplicadas que precisam convergir

1. **Três medições de custo/token sem reconciliação comum**: `tracer.py` (spans),
   `context_ledger.py` (tool spans em `traces.db`) e `economy/ledger.py`
   (`TokenLedger` em memória). Nenhum consome o outro.
2. **Dois detectores de desperdício**: `economy/waste_detector.py` e
   `observability/agentops._waste` cobrem padrões sobrepostos sem compartilhar
   classificação (`observed` vs `hypothesis` só existe no segundo).
3. **Dois roteadores de modelo**: `router.py` (tier, autoritativo) e
   `model_router.py` (scorecard, shadow). O prompt manda o adaptativo ser o v3;
   o legado continua rollback target — convergência é por fronteira explícita,
   não por fusão.

## 3. Defeitos P0 registrados (ordem de correção)

### 3.1 `unknown → zero` em tokens e custo de modelo

`TraceSpan.input_tokens = 0` não distingue "não observado" de "observado 0"
(`tracer.py:19-22`). `agentops.inspect_run` publica `models.tokens` =
`total_tokens` e `models.cost` = `total_cost_usd` como números crus
(`agentops.py:121-122`), enquanto `context.tokens` já sai `tokens_unresolved`.
Correção: status de medição explícito por eixo (tokens, custo), propagado do
`end_span` até `inspect_run`, com vocabulário `measured` / `unresolved` /
`not_applicable`.

### 3.2 `cost_basis` reconciliado sobre eventos errados

`TokenLedger.reconcile` (`ledger.py:123-128`) exige `cost_basis` de **todos** os
eventos quando `observed` de custo existe. Um evento de tool sem custo (campo
legitimamente vazio) invalida o run inteiro. Correção: a exigência vale só para
eventos que carregam custo (`estimated_cost_usd` ou `observed_cost_usd` não
nulo) — invariante já garantida por `LedgerEvent.__post_init__`.

### 3.3 Inputs decorativos do roteador adaptativo

`ModelRoutingInput.risk` e `required_reasoning` são declarados e nunca lidos;
`complexity` entra no tuple de score (`model_router.py:192`) subtraído
identicamente para todo candidato — não move ranking. Correção: `risk` vira
gate de elegibilidade; `required_reasoning` casa com capability/scorecard;
`complexity` passa a modular score relativo (qualidade exigida cresce com
complexidade), tudo com `unresolved` quando a evidência não existe.

## 4. Costuras de integração abertas (mapa para as fases)

| Seam | De → para | Fase |
|---|---|---|
| Trust no caminho de execução | `trust.py` → `call_tool`/executor | 3 |
| `RoleContextPlan` na seleção de contexto | `trust.py` → `gateway.py` | 4 ✅ |
| Inputs do router | `model_router.py` interno | 5 |
| Promotion real do Decision Plane | `decision_plane.py` | 6 |
| Memória governando recuperação | `memory.py` retrieve | 7 |
| Métricas de contexto na promoção | `quality.py` → policy | 8 |
| Resume entre processos | `checkpoint.py` | 9 |
| Timeline/critical path/coverage | `agentops.py` | 10 |
| Stop policy por ganho de informação | novo ponto de decisão | 11 |
| Cenários agentic no Lab | `lab/scenario.py` | 12 |
| Conformance MCP | `adapters/mcp*.py` | 13 |
| Adapter A2A experimental | `protocols/forge.py` | 14 |
| Freshness knowledge/graph | `codeintel`, `knowledge/` | 15 |
| SBOM | `scripts/`, supply chain | 16 |

## 5. Limites desta auditoria

- A classificação `PARTIAL`/`INTEGRATED` é por análise estática do grafo de
  chamadas dentro de `sparkforge/`; ferramentas externas podem compor os módulos
  de outra forma. Não é claim exaustivo sobre todos os 141 tools.
- Números citados são os medidos nesta leitura; a tabela *Números correntes* do
  `docs/superpowers/STATUS.md` continua a fonte de verdade operacional.

## 6. Estado das fases (atualização incremental)

| Fase | Commit | Evidência |
|---|---|---|
| 0 — auditoria | `639a236` | este documento |
| 1 — P0 | `a26fcd7` | `tokens_status` no span/trace/store; `models.tokens`/`cost` estruturados em `inspect_run`; `cost_basis` escopado a eventos com custo; `risk`/`required_reasoning`/`complexity` operacionais no router |
| 2 — economia | `fb19355` | `economy/reconcile.py` (autoridades canônicas, conflitos nomeados); `inspect_run` ganha `reconciliation`; `TokenWasteDetector` sem preço inventado |
| 3 — trust no despacho | `7e23881` | `_trust` em todo resultado de `call_tool` (inclui recusa); `taint` no metadata do span; `TRUST_RANK` explícito; `tool_result_envelope()` em `trust.py` |
| 4 — `RoleContextPlan` na seleção | `160348b` | `GatewayRequest.role`/`role_plan`; `ROLE_PLANS` com os 5 executores; negação por kind/floor/required vira `unresolved` nomeado; `context_share` encolhe o teto; `tool_access` filtra capabilities; role desconhecida é fail-closed (`role_plan_unknown`, deny-all); `_trust` do item via `item["trust"]`; campos declarados em `context_start` (MCP+CLI) |
| 5 — Model Router v3 | `2ea9931` | `scorecard_maturity()` (absent/cold/warming/mature, `SCORECARD_MATURE_MIN_OBSERVATIONS=5` declarado); `ModelRouteDecision` reporta `scorecard_observations`/`scorecard_maturity` e `scorecard_absent` em `unresolved`; `route_health()` com 8 eixos no vocabulário ready/partial/degraded/unresolved (sem placar 0-100); `provider_availability` é `unresolved` de propósito (core offline); `doctor agentic` ganha o eixo `scorecard_maturity`; promoção continua exigindo modo ACTIVE + `active_enabled` + autoridade + evidência |
| 6 — Decision Plane | `37d506e` | `observe_adaptive_route()` em `agentic/shadow.py`: a decisão do `AdaptiveModelRouter` entra como `current` (`provider/model` canônico) na avaliação shadow do contrato, com recibo persistido e `route_health` acompanhando a observação; `route_with_mode`/`AgenticDecisionController` seguem como o único caminho de promoção (autoridade + evidência + governador + recibo) |
| 7 — Memory v3 | `f33d5b0` | `freshness_state()` (`expired` prevalece sobre campo); `expired` sai do retrieval por default ou volta demotado para `trust:"stale"` com `expired="stale"`; `RuntimeCompatibilityPolicy`/`evaluate_runtime()` por componente (exact/compatible/incompatible/unresolved, prefixo numérico = mesma família — §41-42); `incompatible` excluído, `unresolved` reportado; `MemoryConflict`+`detect_memory_conflicts()` (prefer/review por trust>outcome>freshness); quarentena consolidada: `decisions.jsonl`+`status` é a única autoridade, `quarantine.jsonl` legada só para leitura de histórico. ADR §36-38: JSONL append-only preservado — supersede/invalidate já são fatos append-only; event-sourcing adiado por não haver consumidor de replay temporal |
| 8 — Context Quality v3 | `ff8acaf` | Vocabulário de eixos separado (§58): `critical`/`used`/`cited`/`consumed` no `ContextObservation` com contagens próprias; `useful_items_per_1k_tokens` (todo kind) + `useful_facts_per_1k_tokens` (só `kind=="fact"`, facts reais — §59-60); `usefulness_basis` registra a origem do julgamento (§62); `CounterfactualContextBenchmark` com ablação empírica eval-only (`minimum_sufficient_removed`) ao lado do benchmark estático preservado (§63-64) |
| 9 — Checkpoint/resume real | `757015e` | Teste cross-process de verdade: subprocesso A constrói estado semântico, checkpointa e morre; subprocesso B carrega e retoma — id content-addressed atravessa processos e facts/decisions/unknowns/next_actions/budget/routing/security conferem campo a campo (§80-81); adulteração muda o id (content-addressed detecta); nenhum campo transcript/messages/conversation existe (§82); `SemanticCheckpoint.compacted()` remove superseded facts e stale artifacts com retenção mínima declarada (§83) |
| 10 — AgentOps v2 | `4fa102a` | `run_timeline()` (eventos por lane §68 — task/context/routing/agent/model/tool/review/debate/checkpoint, fora do vocabulário vira `other` nomeado); `critical_path()` (top-5 durações, retries por nome repetido, waiting = gaps medidos entre spans — §69); `provider_usage_coverage` em `inspect_run.models` (measured/total, `unresolved` sem span de modelo — §12); superfícies `agentops timeline`/`critical-path` no CLI + `sparkforge_agentops_timeline`/`critical_path` MCP (141→143 tools, declarado em parity.yaml, golden-allowlist, STATUS e docs de referência) |

| 11 — Information gain / stop | `53902ae` | `agentic/stop.py`: `StopPolicy.evaluate(ExpectedGainState)` — gate determinístico de ganho esperado (§85-86, política + estado observado, sem pseudo-ML) sobre os sinais do §87 (evidence_gaps, uncertainty, contradictions, role_coverage, agent_disagreement, novel_evidence_potential, remaining_budget, task_risk, security_flag, unresolved_required); vocabulário §88 completo em `StopAction` (STOP_SUFFICIENT/STOP_BUDGET/STOP_NO_GAIN/STOP_SECURITY/STOP_UNRESOLVED/CONTINUE/REVIEW/DEBATE/HUMAN); `FailureClass` cobre as 11 classes do §90 (provider_unavailable, tool_failure, policy_conflict, security_refusal, context_insufficient, loop, dependency_failure entram; security_refusal→refuse e loop→stop por §92); gate plugado em `RecoveryGovernor.resolve(gain_state=...)` — stop veta a ação antes de gastar budget, reason `stop_gate:<ação>` |
| 12 — Forge Lab agentic evals | `8dc91fe` | `evals/agentic/recovery/` — 8 cenarios deterministicos do circuito de recuperacao (security_refusal, loop_fingerprint, budget_exhausted_gate, continue_on_gaps, debate_sem_contradicao, provider_bounded_retry, context_insufficient_replan, missing_evidence_abstain), cada um `case.yaml` + `expected.yaml` no molde da suite de debate; `tests/test_evals_recovery_suite.py` replaya por `RecoveryGovernor.resolve` E re-deriva o gabarito pela composicao `RecoveryPolicy`×`StopPolicy` sem o governador — driver e derivacao divergindo invalida o cenario |
| 13 — MCP conformance | `20e9516` | `evals/mcp-conformance/matrix.yaml` — 23 requisitos do protocolo com status fechado (covered/delegated_to_sdk/unresolved/not_applicable): 18 covered com evidencia `arquivo::Classe::teste`, 2 delegados ao SDK (cancel, ping), 1 lacuna declarada (paginacao), 2 nao-aplicaveis (resources/prompts, roots/elicitation); `tests/test_mcp_conformance_matrix.py` verifica que toda evidencia aponta um teste real (classe + def) e que covered sempre tem evidencia |
| 14 — Forge Protocol / A2A | `1f364c9` | `protocols/a2a_adapter.py` — adapter EXPERIMENTAL stdlib-puro (§111-112: nenhum pacote `a2a` no core, `protocols/__init__` nao o importa); rótulo `a2a-ready` (§110); `agent_card()` publica ForgeCapability como skills A2A, `submit_task()` traduz message/parts→ForgeTask, `forge_to_a2a_state()` mapeia os 6 estados com UNRESOLVED→`unknown` (nunca completed), `result_to_a2a_task()` devolve artifacts `evidence_bundle`+`unresolved` — §114 readiness: The Forger descobre, submete e recebe evidence bundle + unresolved |
| 15 — grafo de impacto com skills | `ae31c9b` | `SALTOS_DO_REPOSITORIO` ganha `skills` (§147 — "qual skill?" respondido): `RepoIndex.skill_citations` indexa `skills/*/SKILL.md` por `rule_id` citado no corpo; `skills_of()` propaga como agentes; `drift()` devolve `impact.skills`/`totals.skills` e o refresh renderiza o rótulo; honestidade por campo: `skill_citations=None` quando o checkout não tem `skills/` → `impact.skills=null` + `unresolved` com `sem_diretorio_skills` (vazio seria falso-negativo; `repo_root()` segue nos 3 diretórios da assinatura); goldens regenerados por `SPARKFORGE_REGEN_DRIFT=1` — saída real no repo: 13 skills impactadas; `test_lf_impacto_conferivel_por_arquivo` agora confere cada skill listada contra o texto do arquivo |
| 16 — supply chain / Trust Lab | `11cf41b` | Supply chain já era coberta (SBOM CycloneDX determinístico, locks pinados+sha256, pip-audit no CI + `audit_policy` pura, vendor manifest, wheel bit-reproduzível) — a lacuna era a suíte red-team determinística (§158). `tests/test_redteam_security.py`: 32 ataques contra as defesas REAIS — §125 Trust Lab (prompt_injection, malicious_tool_output, cross_agent_injection, instruction_laundering, confused_deputy) e §45 memory poisoning (proposta maliciosa, injection persistida, outcome falso, ref forjada, stale, contaminação cross-case/cross-repo, laundering, runtime errado); limites honestos declarados (guardrail lexical não detecta instrução sem marcador; registry vazio = evidência auto-atestada `provisional`, nunca `verified`). THREAT-MODEL ganha seção T-A01..A06 sem violar o escopo SPEC da tabela principal |

Nota de ambiente registrada na fase 3: a suíte com `--basetemp` dentro do
repositório faz `_ancestral_com_case` (`journal/record.py`) escalar até a raiz
do projeto e gravar em `.sparkforge/journal.jsonl` — o backstop do
`conftest.py` reprova por desenho. A suíte roda com `--basetemp` fora da árvore
(`E:\projetos\.tmp_pytest_sf`) até que o tempdir do Windows volte a aceitar
escrita.
