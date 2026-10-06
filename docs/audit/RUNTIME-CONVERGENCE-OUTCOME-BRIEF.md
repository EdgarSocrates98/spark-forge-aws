# Runtime Convergence — Outcome Brief

Formato exigido por `prompt_evo_runtime.md` (FASE 17). Cada campo aponta para
evidência; o que não foi provado está em `DEFERRED`/`UNRESOLVED`, não em
`STATUS`. Detalhe por seção: `RUNTIME-CONVERGENCE-FINAL-REPORT.md`.

```text
STATUS: CONVERGED — 18 fases (0-17) commitadas atomicamente; cada capacidade
  chegou a contract+implementation+runtime integration+policy+tests+eval+
  observability+docs onde aplicável. Gaps residuais classificados, não
  arredondados.

BASE_SHA: 8f1581f7c54a4d55034afd6b4409c8ba19224070

FINAL_SHA: edf89ac — último commit com código/testes; o commit que traz
  este brief é docs-only acima dele.

OBJECTIVE: Convergir as capacidades existentes em um único circuito
  operacional governado — evidence-first, determinístico primeiro, econômico,
  seguro, auditável, provider-neutral, local-first.

RUNTIME_CONVERGENCE: INTEGRATED — `call_tool` emite `_trust`; Gateway seleciona
  por `RoleContextPlan`; roteador adaptativo observado pelo Decision Plane;
  memória filtra por freshness/runtime/evidência; StopPolicy veta gasto sem
  ganho esperado; AgentOps explica timeline/critical-path/cobertura.
  Evidência: `tests/test_runtime_convergence_*.py`, commits `7e23881`,
  `160348b`, `37d506e`, `f33d5b0`, `53902ae`, `4fa102a`.

OBSERVABILITY: INTEGRATED — `run_timeline()` por lane, `critical_path()` top-5
  + retries + waiting medido, `provider_usage_coverage` (measured/total) em
  `inspect_run.models`; CLI + 2 tools MCP (141→143). `4fa102a`.

ECONOMY: INTEGRATED — `economy/reconcile.py` autoridade única com conflitos
  nomeados; `unknown→0` corrigido (measured/unresolved/not_applicable);
  `cost_basis` só de eventos com custo; waste sem preço inventado
  (`cost_usd: null` + `unresolved`). `fb19355`, `a26fcd7`.

MODEL_ROUTING: INTEGRATED — `AdaptiveModelRouter` v3: risk=elegibilidade,
  reasoning=capability match, complexity=modulador; `scorecard_maturity()`
  4 estados declarados; `route_health()` 8 eixos sem placar inventado;
  promoção gated por ACTIVE+autoridade+evidência. `a26fcd7`, `2ea9931`.

MEMORY: INTEGRATED — `freshness_state()` governa retrieval (expired excluído
  ou demotado `trust:"stale"`); `RuntimeCompatibilityPolicy` por componente;
  `detect_memory_conflicts()` prefer/review; quarentena canônica em
  `decisions.jsonl`; registry ausente ⇒ `provisional`, nunca `verified`.
  `f33d5b0`.

TRUST: INTEGRATED — envelope `_trust` (TOOL_OUTPUT/data_only/taint) em todo
  `call_tool`; `as_verified_fact()` não promove autoridade; Trust Lab =
  32 ataques determinísticos contra defesas reais; THREAT-MODEL §T-A01..A06
  (5 fechadas, 1 parcial declarada). `7e23881`, `11cf41b`.

CONTEXT: INTEGRATED — `ROLE_PLANS` (5 executores) no Gateway; negação =
  `unresolved` nomeado; role desconhecida = deny-all; `ContextObservation`
  critical/used/cited/consumed; `CounterfactualContextBenchmark` eval-only.
  `160348b`, `ff8acaf`.

AGENTOPS: INTEGRATED — ver OBSERVABILITY. `4fa102a`.

CHECKPOINT: INTEGRATED — resume cross-process provado (subprocesso A morre,
  subprocesso B retoma, id content-addressed atravessa); `compacted()` remove
  superseded/stale; semântico, sem transcript. `757015e`.

MCP: INTEGRATED — `evals/mcp-conformance/matrix.yaml`: 23 requisitos —
  18 covered (evidência arquivo::Classe::teste verificada por teste),
  2 delegated_to_sdk, 1 unresolved (paginação), 2 not_applicable. `20e9516`.

FORGE_PROTOCOL: INTEGRATED — contratos Forge estáveis; Knowledge Drift ganhou
  o salto `skills` (stale → qual skill) com honestidade por campo
  (`sem_diretorio_skills` ≠ `[]`). `ae31c9b`.

A2A: EXPERIMENTAL — `protocols/a2a_adapter.py` stdlib-puro, `a2a-ready`;
  UNRESOLVED→unknown; não é servidor A2A (classificação §251). `1f364c9`.

FORGE_LAB: INTEGRATED — `evals/agentic/recovery/` 8 cenários determinísticos;
  teste replaya por RecoveryGovernor E re-deriva gabarito por
  RecoveryPolicy×StopPolicy (anti-fixture). `8dc91fe`.

EVALS: INTEGRATED — `check_evals.py` 10/10 respostas re-derivadas reproduzem;
  suite agentic nova exercita o circuito de recuperação. `8dc91fe`.

SECURITY: INTEGRATED — red-team §125+§45: injection lexical, taint, autoridade
  de instrução, identidade de agente, tool allow/deny, secret-shape,
  memory poisoning (7 classes). `_trust` aditivo preservado — parity tests
  normalizam só no lado do teste. `11cf41b`, FASE 17.

SUPPLY_CHAIN: INTEGRATED — vendor 127 arquivos OK; locks 3×160 pinados;
  requirements espelha pyproject; skills mirrors OK; offline bundle OK;
  wheel bit-reprodutível + instalação verificada; pip-audit executado: 52
  pacotes, 0 vulnerabilidades; surface lock e status numbers 0 divergências.

TESTS: 14730 passed, 14 skipped, 0 failed em 6565s — suíte completa sobre a
  árvore congelada de edf89ac (python -m pytest -q -p no:cacheprovider
  --basetemp=E:/projetos/.tmp_pytest_sf/final2, Windows, Python 3.14.6).

CI: equivalentes locais do job `test` todos verdes — ruff, sync_skills,
  requirements, locks (3×160), vendor (127), offline bundle, evals (10),
  vnext claims (0 divergências), status numbers, recall/economy, surface
  lock, catálogo com expressões (221 regras), sem artefato cru rastreado.
  Job `wheel`: 2 builds bit-idênticas + 3514 goldens no pacote instalado +
  twine PASSED + bundle OK. Job `audit`: pip-audit consultou a base — 52
  pacotes, 0 vulnerabilidades. `otel-collector` e `sarif-upload` são
  DEFERRED_EXTERNAL (Docker daemon / workflow_dispatch, indisponíveis
  localmente).

REGRESSIONS: FASE 3 (`_trust` aditivo) invalidou ~55 asserts de paridade
  legada que comparavam payload cru com `call_tool`; corrigidos no teste
  (pop de `_trust` antes da comparação), formato travado em
  `test_runtime_convergence_trust.py`. Contagens pinadas de tools/legendas
  atualizadas (131→133, módulos agentic 21→22) com nota datada.

DEFERRED: scorecard store persistido (in-memory; doctor reporta o eixo
  `unresolved`); `activation_ready` do Decision Plane permanece `false` por
  contrato (exige corpus rotulado + gates); event-sourcing do ledger de
  memória (ADR §36-38: sem consumidor de replay); `RoleContextPlan` no
  `AgentHandoff` (governa contexto, não handoff — PARTIAL).

UNRESOLVED: `provider_availability` (core offline por desenho); paginação MCP
  (declarado na matrix); OTLP collector live (DEFERRED_EXTERNAL — sem Docker
  local); guardrail lexical vs. instrução sem marcador lexical (GAP
  declarado, T-A01 parcial — fora do escopo determinístico).

NEXT: push da branch `devin/runtime-convergence-wave`; em ambiente com
  Docker, rodar o job `otel-collector`; corpus rotulado para avaliar
  `activation_ready`; considerar `RoleContextPlan` em `AgentHandoff` quando
  houver caso de uso medido.
```
