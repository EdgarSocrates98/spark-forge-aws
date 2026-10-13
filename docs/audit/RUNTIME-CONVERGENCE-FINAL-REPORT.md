# Runtime Convergence — Final Report

**BASE_SHA:** `8f1581f7c54a4d55034afd6b4409c8ba19224070` (`origin/main`)
**FINAL_SHA:** `edf89ac` — último commit que toca código/testes; o commit
que traz este relatório é docs-only acima dele (`git log` confirma).
**BRANCH:** `devin/runtime-convergence-wave`
**Fonte do pedido:** `prompt_evo_runtime.md` (fora da árvore versionada)

Este relatório fecha a onda de convergência. Cada afirmação aponta para commit,
arquivo ou teste — o que não pôde ser provado está classificado em *Remaining
Gaps*, não arredondado para fechado.

## 1. Executive Summary

A onda convergiu as capacidades agentic existentes — que antes conviviam como
módulos sofisticados mas desconectados — em um único circuito operacional
governado: `call_tool` emite envelope de confiança, o Context Gateway seleciona
por role, o roteador adaptativo é observado pelo Decision Plane, a memória
filtra por frescor/runtime/evidência, o stop gate veta gasto sem ganho
esperado, e o AgentOps explica o run por timeline, critical path e cobertura de
medição. 20 commits atômicos por fase, cada um com teste próprio, gates do CI
relocalizáveis e documentação atualizada no mesmo commit.

Invariante preservado: **inteligência probabilística dentro de fronteiras
determinísticas de engenharia** — nenhum modelo é chamado pelo core, nenhum
número é inventado quando a medição falta (`unresolved` é resultado válido), e
nenhuma autoridade é promovida sem evidência.

## 2. Baseline

```text
Base SHA:  8f1581f7c54a4d55034afd6b4409c8ba19224070 (origin/main)
Final SHA: edf89ac (último commit com código/testes; relatório é docs-only acima)
Python:    3.14.6 (runner local), matriz CI 3.10/3.11/3.12
Tests:     14730 passed, 14 skipped, 0 failed — seção final do documento
```

## 3. Runtime Before

Leitura de `docs/audit/RUNTIME-CONVERGENCE-BASELINE.md` (FASE 0, `639a236`):

- Trust/security/memory/recovery existiam como primitivas completas mas
  **PARTIAL**: nada as invocava no caminho de execução (`call_tool` devolvia
  resultado sem envelope de confiança, o Gateway ignorava `RoleContextPlan`).
- Roteador adaptativo com inputs decorativos (`risk`, `required_reasoning`,
  `complexity` não moviam a decisão); Decision Plane existia só como shadow
  observando a rota legada.
- Memória rica em schema (freshness/quarantine/runtime) mas `retrieve` não
  filtrava por nenhum dos três; quarentena dividida entre dois arquivos.
- `unknown → 0` em tokens e custo — "não medido" e "zero" indistinguíveis;
  `cost_basis` exigido de eventos que não carregam custo invalidava reconciliação.
- AgentOps sem timeline, critical path ou cobertura de medição por provider.
- Checkpoint content-addressed sem prova de resume entre processos.
- Grafo de impacto do Knowledge Drift parava em rules/docs/goldens/evals/agents —
  "qual skill fica stale?" (§147) sem resposta.
- Sem suíte red-team; THREAT-MODEL cobria só a superfície SFCI da SPEC.

## 4. Runtime After

```text
call_tool ── envelope _trust (TOOL_OUTPUT/data_only/taint) ──► span metadata
Gateway ── RoleContextPlan governa kinds/floor/required/tool_access ──►
    negação vira unresolved nomeado, role desconhecida = deny-all
AdaptiveModelRouter ── scorecard_maturity + route_health(8 eixos) ──►
    observe_adaptive_route ──► Decision Plane shadow ──► recibo persistido
RecoveryGovernor ── StopPolicy.evaluate(ExpectedGainState) ──►
    veta RETRY/REPLAN/ESCALATE sem ganho esperado (15 FailureClass)
Memory ── freshness_gate + RuntimeCompatibilityPolicy + quarentena única ──►
    expired sai do retrieval, incompatible excluído, unresolved reportado
SemanticCheckpoint ── content-addressed, provado cross-process ──►
    compacted() remove superseded/stale
AgentOps ── run_timeline/critical_path/provider_usage_coverage ──►
    CLI + 2 tools MCP (141→143)
KnowledgeDrift ── salto skills (RepoIndex.skill_citations) ──►
    "se a fonte X ficar stale → qual skill?" respondido
Forge Protocol ── a2a_adapter EXPERIMENTAL (stdlib, UNRESOLVED→unknown)
MCP ── matrix.yaml: 23 requisitos, evidência aponta teste real
Trust Lab ── 32 ataques determinísticos contra defesas reais
```

## 5. Convergence Matrix

| Capacidade | Antes (FASE 0) | Depois | Commit |
|---|---|---|---|
| Trust plane | PARTIAL | INTEGRATED — `_trust` em todo resultado de `call_tool` | `7e23881` |
| `RoleContextPlan` | PARTIAL | INTEGRATED — governa seleção no Gateway | `160348b` |
| Roteador adaptativo | PARTIAL | INTEGRATED — risk/reasoning/complexity operacionais, maturity reportada | `a26fcd7`+`2ea9931` |
| Decision Plane | PARTIAL (shadow da rota legada) | INTEGRATED — shadow observa a rota adaptativa; promoção exige autoridade+evidência | `37d506e` |
| Memória de decisão | PARTIAL | INTEGRATED — freshness/runtime/conflito/quarentena governam retrieval | `f33d5b0` |
| Qualidade de contexto | PARTIAL | INTEGRATED — eixos semânticos + benchmark contrafactual empírico | `ff8acaf` |
| Checkpoint | PARTIAL | INTEGRATED — resume cross-process provado, `compacted()` | `757015e` |
| AgentOps | PARTIAL | INTEGRATED — timeline/critical-path/coverage em CLI+MCP | `4fa102a` |
| Stop policy | ABSENT | INTEGRATED — gate de ganho esperado dentro do RecoveryGovernor | `53902ae` |
| Recovery taxonomy | 8 classes | INTEGRATED — 15 classes (§90 completo) | `53902ae` |
| Forge Lab agentic | ABSENT | INTEGRATED — suite `evals/agentic/recovery/` (8 cenários, derivação dupla) | `8dc91fe` |
| Conformidade MCP | PARTIAL | INTEGRATED — matrix.yaml versionada, evidência por teste | `20e9516` |
| Forge Protocol | PARTIAL | EXPERIMENTAL — adapter A2A stdlib-puro, `a2a-ready` | `1f364c9` |
| Knowledge Drift | PARTIAL | INTEGRATED — salto `skills` com honestidade por campo | `ae31c9b` |
| Red-team | ABSENT | INTEGRATED — 32 ataques determinísticos | `11cf41b` |
| Reconciliação de economia | ABSENT | INTEGRATED — `economy/reconcile.py`, conflitos nomeados | `fb19355` |
| `unknown→0` tokens/custo | defeito P0 | CORRIGIDO — `measured`/`unresolved`/`not_applicable` | `a26fcd7` |
| `cost_basis` reconciliação | defeito P0 | CORRIGIDO — exigido só de eventos com custo | `a26fcd7` |
| Waste detector duplicado | DUPLICATE | CONVERGIDO — `agentops._waste` é o dono; `TokenWasteDetector` sem preço inventado | `fb19355` |

## 6. Bugs Fixed

| Bug | Natureza | Commit |
|---|---|---|
| `unknown → 0` em tokens e custo de modelo | `inspect_run` publicava 0 para "não observado"; agora `tokens_status`/`cost_status` propagam `measured`/`unresolved`/`not_applicable` do span ao relatório | `a26fcd7` |
| `cost_basis` exigido de eventos sem custo | reconciliação inteira invalidada por tool call com custo vazio; escopo corrigido para eventos que carregam custo | `a26fcd7` |
| Inputs decorativos do roteador | `risk`/`required_reasoning`/`complexity` declarados e não lidos; viraram gate de elegibilidade, casamento de capability e modulador de score | `a26fcd7`+`2ea9931` |
| Quarentena dividida em dois arquivos | `quarantine.jsonl` legado + `decisions.jsonl` competiam como autoridade; consolidado em `status` no ledger único, legado só para leitura | `f33d5b0` |
| Frescor não governava retrieval | `expired` retornava como válido; agora sai por default ou volta demotado `trust:"stale"` | `f33d5b0` |
| `zip()` sem `strict` no critical path | silenciaria divergência de tamanho de listas de spans | `4fa102a` |
| `_GATED_ACTIONS` entre imports (E402) | constante inserida no meio do bloco de imports em `control.py` | _fase 17_ |

## 7. Economy

- `sparkforge_aws/economy/reconcile.py` é a autoridade única de reconciliação:
  `ReconciliationReport` lista conflitos nomeados (`field`, `sources`,
  `resolution`) em vez de fundir em silêncio.
- `inspect_run` publica `reconciliation` — o consumidor vê de onde veio cada
  número e o que ficou `unresolved`.
- `TokenWasteDetector` não inventa preço: padrão sem custo medido sai com
  `cost_usd: null` + `unresolved`, nunca estimativa fabricada.
- `provider_tokens` continua resolvido só por transcript de host; sem ele,
  `tokens_unresolved` — o core nunca infere tokens de bytes.
- `StopPolicy` (FASE 11) é a economia de *execução*: ação que gasta budget sem
  ganho esperado de informação é vetada antes de consumir.

## 8. Model Routing

- `AdaptiveModelRouter` (v3): `risk` → gate de elegibilidade;
  `required_reasoning` → casamento contra capability do scorecard;
  `complexity` → modula score relativo (qualidade exigida cresce com a tarefa).
- `scorecard_maturity()`: `absent`/`cold`/`warming`/`mature` com
  `SCORECARD_MATURE_MIN_OBSERVATIONS = 5` declarado; scorecard sem dados sai
  `scorecard_absent` em `unresolved`, não como score zero.
- `route_health()`: 8 eixos no vocabulário `ready`/`partial`/`degraded`/
  `unresolved` — sem placar 0-100; `provider_availability` é `unresolved` de
  propósito (core offline, não finge leitura de provider).
- `agentic doctor` ganhou o eixo `scorecard_maturity`.
- Legado `CapabilityModelRouter` permanece autoritativo no dispatch; o
  adaptativo é observado pelo Decision Plane (`observe_adaptive_route`) — a
  promoção continua gated por `ACTIVE` + `active_enabled` + autoridade +
  evidência, com recibo persistido.

## 9. Memory

- `freshness_state()`: `expired` prevalece sobre campo declarado; retrieval
  exclui expirado por default ou devolve demotado para `trust:"stale"` com
  `expired:"stale"` marcado.
- `RuntimeCompatibilityPolicy` + `evaluate_runtime()` por componente:
  `exact`/`compatible`/`incompatible`/`unresolved`; prefixo numérico = mesma
  família; `incompatible` é excluído do retrieval e `unresolved` é reportado.
- `MemoryConflict` + `detect_memory_conflicts()`: `prefer`/`review` decididos
  por trust > outcome > freshness.
- Quarentena canônica: `decisions.jsonl` + `status` é a única autoridade;
  `quarantine.jsonl` legada só para leitura de histórico.
- Registry de evidência vazio ≠ registry que refuta: candidato auto-atestado
  fica `provisional`, nunca `verified` — contrato exercitado pelo red-team.
- ADR §36-38: JSONL append-only preservado (supersede/invalidate já são fatos
  append-only); event-sourcing adiado — sem consumidor de replay temporal.

## 10. Trust/Security

- Todo resultado de `call_tool` — sucesso ou recusa — carrega `_trust`
  (`provenance=TOOL_OUTPUT`, `instruction_authority=DATA_ONLY`, `taint`); o
  `taint` aterrissa no `metadata` do span e `TRUST_RANK` é ranking explícito,
  não posição de enum.
- `as_verified_fact()` promove só o trust factual — `DATA_ONLY` sobrevive à
  promoção; autoridade SYSTEM/POLICY não entra por envelope externo
  (`__post_init__` levanta).
- `tests/test_redteam_security.py`: 32 ataques determinísticos contra as
  defesas reais — §125 Trust Lab + §45 memory poisoning; THREAT-MODEL ganhou a
  seção T-A01..A06 (5 fechadas com teste, 1 parcial declarada: o guardrail
  lexical não detecta instrução fora dos marcadores — declarado, não fingido).

## 11. Context

- `GatewayRequest.role`/`role_plan`: `ROLE_PLANS` declara os 5 executores;
  negação por kind/floor/required vira `unresolved` nomeado; `context_share`
  encolhe o teto; `tool_access` filtra capabilities; role desconhecida é
  fail-closed (`role_plan_unknown`, deny-all).
- `ContextObservation` separa `critical`/`used`/`cited`/`consumed` com
  contagens próprias; `useful_items_per_1k_tokens` (todo kind) e
  `useful_facts_per_1k_tokens` (só `kind=="fact"`) com `usefulness_basis`
  registrando a origem do julgamento.
- `CounterfactualContextBenchmark`: ablação empírica eval-only
  (`minimum_sufficient_removed`) ao lado do benchmark estático preservado.

## 12. AgentOps/Observability

- `run_timeline()`: eventos por lane (§68) — task/context/routing/agent/model/
  tool/review/debate/checkpoint; fora do vocabulário vira `other` nomeado.
- `critical_path()`: top-5 durações, retries por nome repetido, `waiting` =
  gaps medidos entre spans (não soma inventada).
- `provider_usage_coverage` em `inspect_run.models`: `measured`/`total`,
  `unresolved` sem span de modelo.
- Superfícies: `agentops timeline`/`critical-path` no CLI +
  `sparkforge_aws_agentops_timeline`/`sparkforge_aws_agentops_critical_path` MCP —
  141→143 tools declarados em `parity.yaml`, golden-allowlist, surface lock,
  STATUS e docs de referência regeneradas.

## 13. Checkpoint/Resume

- Prova cross-process real (§80-81): subprocesso A constrói estado semântico,
  checkpointa e morre; subprocesso B carrega e retoma — id content-addressed
  atravessa processos; facts/decisions/unknowns/next_actions/budget/routing/
  security conferem campo a campo; adulteração muda o id.
- `SemanticCheckpoint.compacted()` remove superseded facts e stale artifacts
  com retenção mínima declarada (§83).
- Nenhum campo transcript/messages/conversation — o checkpoint é semântico
  (§82), não replay de conversa.

## 14. MCP

- `evals/mcp-conformance/matrix.yaml`: 23 requisitos do protocolo com status
  fechado — 18 `covered` (evidência `arquivo::Classe::teste`, verificada por
  `tests/test_mcp_conformance_matrix.py`), 2 `delegated_to_sdk` (cancel, ping),
  1 `unresolved` declarado (paginação), 2 `not_applicable`.
- Superfície permanece 143 tools full / 7 compact, envelope idêntico nos dois
  adaptadores; `_trust` entra no `metadata` sem violar `outputSchema`
  (verificado: sem `additionalProperties: false` top-level).

## 15. Forge Protocol/A2A

- `protocols/a2a_adapter.py` — EXPERIMENTAL, stdlib-puro: nenhum pacote `a2a`
  no core, `protocols/__init__` não o importa, rótulo `a2a-ready` (§110-112).
- `agent_card()` publica ForgeCapability como skills A2A; `submit_task()`
  traduz message/parts → ForgeTask; `forge_to_a2a_state()` mapeia 6 estados com
  `UNRESOLVED → unknown` (nunca `completed`); `result_to_a2a_task()` devolve
  artifacts `evidence_bundle` + `unresolved`.
- §114 readiness: The Forger descobre, submete e recebe evidence bundle +
  unresolved. Classificação EXPERIMENTAL (§251): existe só como adapter, não
  como servidor A2A completo.

## 16. Forge Lab

- `evals/agentic/recovery/`: 8 cenários determinísticos do circuito de
  recuperação (security_refusal, loop_fingerprint, budget_exhausted_gate,
  continue_on_gaps, debate_sem_contradicao, provider_bounded_retry,
  context_insufficient_replan, missing_evidence_abstain), cada um
  `case.yaml` + `expected.yaml` no molde da suite de debate.
- `tests/test_evals_recovery_suite.py` replaya por `RecoveryGovernor.resolve`
  E re-deriva o gabarito pela composição `RecoveryPolicy`×`StopPolicy` sem o
  governador — driver e derivação divergindo invalida o cenário (anti-fixture
  por construção).

## 17. Evals

- `scripts/check_evals.py`: 10 respostas re-derivadas do corpus — todas
  reproduzem.
- `evals/agentic/recovery/` (FASE 12): 8 cenários determinísticos replayados
  por `RecoveryGovernor.resolve` com derivação independente do gabarito.
- `evals/mcp-conformance/matrix.yaml` (FASE 13): 23 requisitos fechados com
  evidência por teste, verificada por `test_mcp_conformance_matrix.py`.
- Suíte completa: ver *Resultado da suíte completa* ao fim — 14730 testes,
  0 falhas, na árvore congelada do commit `edf89ac`.

## 18. CI/Supply Chain

- `verify_wheel.py`: 2 builds → artefatos bit-idênticos + instalação em venv
  limpo + suíte golden sobre o pacote instalado.
- `vendor_caveman.py --check`: 127 arquivos conferem com `MANIFEST.sha256`.
- `gen_lock.py --check`: 3 locks, 160 entradas pinadas com hash.
- `gen_requirements.py --check`: requirements espelha pyproject.
- `check_evals.py`: 10 respostas re-derivadas do corpus, todas reproduzem.
- `check_vnext_claims.py`: 811 alegações com prova; divergências de corpus
  remediadas por medição (número novo + nota datada), nunca por edição de prosa.
- `check_status_numbers.py --strict`: 0 divergências.
- `check_recall_economy.py`: piso de recall 100%; razão `unresolved` declarada
  (envelope > corpus do gold set — mede o piso, não economia).
- `check_surface_lock.py`: 0 divergências.
- `load_catalog(validate_exprs=True)`: 221 regras validadas.
- `pip-audit --require-hashes --disable-pip -r locks/py3.11.txt` +
  `audit_policy.py audit.json --lock locks/py3.11.txt`: executado localmente,
  base consultada, 52 pacotes auditados, nenhuma vulnerabilidade conhecida.
- OTLP Collector (job `otel-collector`) é DEFERRED_EXTERNAL: exige daemon
  Docker, indisponível neste ambiente; a política é exercitada offline por
  `tests/test_supply_chain.py` e os goldens OTLP por
  `tests/test_fixtures_golden_otel.py`.

## 19. Performance

- Suite completa: ver *Resultado da suíte completa* — 6565s (1h49m) na
  máquina local Windows sob carga, `--basetemp` fora da árvore (defeito
  ambiental do tempdir do usuário documentado na seção seguinte).
- Índice codeintel sobre o repo: ~63s na máquina local carregada — acima do
  teto de 60s das provas `fast` do gate de alegações; os valores das provas
  foram verificados com índice compartilhado (uma construção, N consultas) —
  timeout ambiental, não divergência.
- Custo adicional introduzido pela onda: `_trust` por `call_tool` = bloco
  constante por resultado (3 chaves serializadas); `provider_usage_coverage` e
  `critical_path` são O(n) sobre spans já carregados; o gate de stop é uma
  avaliação de política por decisão de recuperação, não por token.

## 20. Remaining Gaps

| Item | Classificação | Razão |
|---|---|---|
| `RoleContextPlan` governando `AgentHandoff` no executor | PARTIAL | plano governa contexto; handoff ainda não consulta |
| `provider_availability` no route_health | UNRESOLVED | core é offline por desenho; precisa de leitura de provider — não finge |
| Paginação MCP | UNRESOLVED | declarado na matrix como lacuna |
| Adapter A2A | EXPERIMENTAL | §251: shape translation only, não é servidor A2A |
| Champion/challenger, benchmark contrafactual | EXPERIMENTAL | existem em Lab/eval-only, não no dispatch |
| OTLP collector live | DEFERRED_EXTERNAL | exige daemon Docker — ausente no ambiente local; CI roda o job no runner |
| Scorecard store persistido | DEFERRED | scorecards são in-memory; doctor reporta o eixo como `unresolved` em vez de fingir leitura |
| Guardrail lexical vs. instrução sem marcador | GAP declarado | T-A01 parcial: fora dos marcadores exige modelo — fora do escopo determinístico |
| `activation_ready` do Decision Plane | DEFERRED | permanece `false` por contrato: exige corpus rotulado mínimo + gates de qualidade/economia |
| Event-sourcing do ledger de memória | DEFERRED | ADR §36-38: sem consumidor de replay temporal hoje |

## Resultado da suíte completa

```text
command:     python -m pytest -q -p no:cacheprovider --basetemp=E:/projetos/.tmp_pytest_sf/final2
environment: Windows 11, Python 3.14.6 (C:\Python314), worktree no commit
             edf89ac (árvore congelada — nenhuma edição durante a execução);
             basetemp fora do repo por PermissionError no tempdir padrão do
             usuário (C:\Users\edgar\AppData\Local\Temp\pytest-of-edgar —
             diretório residual sem permissão de escrita/remoção)
result:      14730 passed, 14 skipped, 0 failed in 6565.47s (1:49:25)
```

Nota de transparência: uma execução anterior sobre a mesma árvore de código
terminou `14728 passed, 14 skipped, 2 failed` — as duas falhas vieram de
edições desta fase feitas *durante* a coleta/execução (a seção nova de
`gates-por-mudanca.md` sem registro em `change_kinds.yaml`, e a página de
referência gerada velha após a citação das tools novas no coordenador). As
duas foram corrigidas (`change_kinds.yaml` + `gen_reference_docs.py`) e a
execução acima, sobre árvore já commitada e congelada, é o resultado
definitivo.

Gates do CI executados localmente (equivalentes do job `test` + `wheel` +
`audit`):

| Gate | Resultado |
|---|---|
| `ruff check sparkforge_aws scripts tests` | All checks passed |
| `sync_skills.py --check` | OK — mirrors em dia |
| `gen_requirements.py --check` | OK |
| `gen_lock.py --check` | OK — 3 locks, 160 entradas pinadas |
| `vendor_caveman.py --check` | OK — 127 arquivos conferem |
| `verify_offline_bundle.py --check` | ok: true |
| `check_evals.py` | 10 respostas reproduzem |
| `check_vnext_claims.py` | 0 divergências |
| `check_status_numbers.py --strict` | 0 divergências |
| `check_recall_economy.py` | 0 problemas |
| `check_surface_lock.py` | 0 divergências |
| `load_catalog(validate_exprs=True)` | 221 regras validadas |
| `verify_wheel.py` | OK — 2 builds bit-idênticas, wheel instala em venv limpo, 3514 goldens passam no pacote instalado, twine check PASSED, bundle 60 skills/14 agents |
| `pip-audit` + `audit_policy.py` | base consultada, 52 pacotes, nenhuma vulnerabilidade |
| `otel-collector` (job CI) | **DEFERRED_EXTERNAL** — exige Docker daemon, ausente no ambiente local |
| `sarif-upload` (job CI) | workflow_dispatch, exige GitHub — não executável localmente |
| sem artefato cru rastreado | git ls-files limpo |
