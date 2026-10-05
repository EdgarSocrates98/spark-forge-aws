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
| Trust plane | `sparkforge/agentic/trust.py` | PARTIAL | `TrustEnvelope`, `RoleContextPlan`, `AgentHandoff`, `sanitize_tool_output` referenciados apenas no próprio módulo e em `__init__` |
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
| `RoleContextPlan` na seleção de contexto | `trust.py` → `gateway.py` | 4 |
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
