# CURRENT-HARNESS-GAP — o que já existe contra o que `prompt_evo_harness.md` pediria

`prompt_evo_harness.md` (3366 linhas) propõe uma camada de "harness engineering" sobre o
Spark Forge. Sua §0 é taxativa: **não reimplemente o que já existe** — "primeiro encontre a
implementação existente, depois integre". Sua §5 pede exatamente este documento: um mapa
`EXISTING CAPABILITY → HARNESS INTEGRATION`.

Este documento responde, componente a componente, uma única pergunta: **isso já existe
aqui, possivelmente sob outro nome?**

## Como classificar

- **EXISTE, com teste** — nomeio o módulo e o arquivo de teste que exercita o comportamento.
- **EXISTE, sem teste** — nomeio o módulo; nada prova o comportamento.
- **EXISTE PARCIAL** — nomeio o que está lá e o que falta, especificamente.
- **NÃO EXISTE** — digo isso.

Nenhuma linha diz "existe" sem caminho. Nenhuma diz "testado" sem nome de arquivo de teste.

Achado central da investigação: **o repositório já tem duas implementações paralelas
de várias das mesmas ideias** — `sparkforge/economy/router.py:CapabilityModelRouter`
e `sparkforge/agents/model_policy.py:ModelSelector` são dois model routers distintos;
`sparkforge/workflows/spec.py:TaskSpec` e `sparkforge/agents/supervisor.py` cobrem
pedaços sobrepostos de execução em fases; `sparkforge/economy/budget.py:TaskBudgetGuardrail`
e `sparkforge/agents/autonomy.py:AutonomyBudget` são dois orçamentos de execução
com formas diferentes. Isso já é o risco que o §100 do harness (fase de simplificação)
existe para conter — antes de escrever harness novo, há duplicação para resolver na
base atual.

---

## 1. Componentes mínimos do v0.1 (§3)

| Componente do harness | Classificação | Módulo(s) existente(s) | Teste |
|---|---|---|---|
| **TaskSpec** | EXISTE, com teste | `sparkforge/workflows/spec.py:TaskSpec` — `objective`, `context`, `constraints`, `acceptance_criteria`, `risk_level: RiskLevel`, `budget: TokenBudget`, serialização `to_dict`/`to_yaml`/`from_dict` | `tests/test_workflows_dag.py::test_task_spec_serialization` |
| **CapabilityRegistry** | EXISTE PARCIAL | `sparkforge/registry/loader.py:CanonicalRegistry` registra `agents`/`skills`/`tools`/`teams`/`workflows`/`knowledge`/`policies`/`evals` por id, carregado de `config/agents.yaml`, `config/teams-expansion.yaml` e `skills/*/SKILL.md`. Falta exatamente o que o §10 pede: uma chave `capability` (ex. `aws.glue.migration`) que resolva para `{tools, skills, agents, knowledge, permissions}` num único lookup — hoje são coleções paralelas por tipo, não por capability. `AgentManifest.capabilities: list[str]` existe como campo mas nada popula/consulta por ele. | `tests/test_canonical_registry.py` (cobre carregamento e validação de manifest, não cobre resolução por capability porque essa resolução não existe) |
| **ExecutionPlanner** | EXISTE PARCIAL | `sparkforge/workflows/dag.py:ExecutionDAG.compute_waves()` faz exatamente a §14 (dependency-aware waves, detecção de ciclo). `sparkforge/agents/supervisor.py:Supervisor.run()` executa um plano de 7 fases fixas (`observe, plan, dispatch, debate, verify, synthesize, decide`) com orçamento e handlers por agente. Os dois não estão integrados: DAG genérico de um lado, plano de fases fixas do outro — nenhum monta `ExecutionPlan` combinando os dois como pede o §13/§14. | `tests/test_workflows_dag.py::test_execution_dag_waves`, `::test_execution_dag_cycle_detection`; `tests/test_agent_runtime.py::test_supervisor_stops_on_budget_and_records_decision`, `::test_supervisor_completes_the_whole_pipeline_with_the_default_budget` |
| **ContextManager** | EXISTE, com teste | `sparkforge/context/funnel.py:ContextFunnel` (dedupe + fit-in-budget), `sparkforge/context/progressive.py:ProgressiveDisclosureManager` (3 níveis A/B/C, igual à pirâmide do §19/§22/§23), `sparkforge/context/knowledge_pack.py:KnowledgePackLoader` (staleness). Cobre a pipeline do §19 quase literalmente: metadata → índice → chunks relevantes → doc completo só quando necessário. | `tests/test_context_funnel.py` (as três classes, num único arquivo) |
| **EvidencePack** | EXISTE, com teste | `sparkforge/findings/models.py:Fact`/`Finding` + o próprio fluxo `judge()` de `sparkforge/rules/engine.py` já produzem fact→finding com `severity`, `runtime_scope`, evidência citável. `MigrationAssessment` (`sparkforge/migration/assessment.py`) vai além: `findings`, `by_step`, `gates`, **`missing_evidence`** (nomeando o que falta, não escondendo) e `recommendation` — é literalmente o schema do §17 (facts, findings, confidence via severidade, unresolved via `missing_evidence`, provenance via `by_step`). | `tests/test_findings_models.py`, `tests/test_migration_assessment.py`, `tests/test_fixtures_golden_migration.py` |
| **BudgetManager** | EXISTE, com teste — **mas duplicado** | `sparkforge/economy/budget.py:TaskBudgetGuardrail` (max_input/output/total tokens, max_cost_usd, max_agent_calls, max_tool_calls, max_retries + `check_exceeded()`) cobre o §28 quase campo a campo. Em paralelo, `sparkforge/agents/autonomy.py:AutonomyBudget` (max_iterations, max_agents, max_tokens, stagnation_limit) e `sparkforge/agents/supervisor.py:Budget` (max_rounds, max_messages, max_tokens, max_context_messages) fazem orçamento de execução com *formas diferentes* para o mesmo conceito. Três dataclasses de budget, três shapes, zero conversão entre elas. | `tests/test_economy_engine.py::test_budget_guardrail_detection`; `tests/test_agent_autonomy.py::test_stop_on_stagnation_and_authorization_policy`; `tests/test_agent_runtime.py::test_supervisor_stops_on_budget_and_records_decision` |
| **ToolPolicy** | EXISTE, com teste | Fase I3: `sparkforge/agents/autonomy.py:tool_class()` deriva os 5 níveis do §40 (`READ_ONLY/LOCAL_MUTATION/CLOUD_READ/CLOUD_MUTATION/DESTRUCTIVE`) das anotações MCP que cada tool já declara em `sparkforge/adapters/tools.py` (`readOnlyHint`/`openWorldHint`/`destructiveHint`) — e não de uma segunda lista mantida à mão. Derivar a classe PEGOU UM DEFEITO antes de classificar: os sete coletores AWS declaravam `readOnlyHint: True` e escrevem em disco (artefato + manifesto de integridade, via `sparkforge.collect.aws._write_and_register`), o que fazia aprovar leitura de nuvem conceder escrita local; a anotação foi corrigida nesta fase, e dois testes que travavam a mentira junto com ela. Duas classes ficam sem membro — `CLOUD_READ` e `DESTRUCTIVE` —, e isso é o resultado, não lacuna: o valor da classificação é impedir que uma tool futura entre sem classe, e as duas vazias têm teste com catálogo sintético. `tool_class()` levanta `KeyError` para nome desconhecido, em vez de devolver `READ_ONLY`. Documentado em [`AUTHORIZATION-CHAIN.md`](AUTHORIZATION-CHAIN.md). Continua existindo, em paralelo e sem unificação, `sparkforge/registry/models.py:ToolManifest.mutation_class: RiskLevel`, que classifica tool em 4 níveis (`read_only/reversible/sensitive/destructive`) — mais grosseiro, e não consultado pela derivação. A Fase J2 fechou o limite de granularidade que a I3 declarou: `authorize()` autorizava um NOME e agora aceita `arguments` e `root`, recusando caminho que escape da raiz do case, com `AuthorizationDecision.checked_arguments` declarando se a verificação de fato rodou — medido, **60** das 65 tools declaram parâmetro de caminho (as duas sem nenhum são `sparkforge_rules_lookup` e `sparkforge_economy_report`), e a verificação reusa `sparkforge/paths.py:resolve_within`, o mesmo algoritmo de `safe_catalog_file` e `safe_knowledge_file`, em vez de uma quarta cópia do confinamento. A cadeia passou a ser **chamada**: `adapters/tools.py:call_tool` consulta `authorize()` via `sparkforge/agents/autonomy.py:CallPolicy` antes de despachar, e o handler não roda quando a decisão recusa — o despacho é único para todo o catálogo, então `adapters/mcp.py` fica coberto junto. Atenção ao nome: a classe é `CallPolicy` e **não** `ToolPolicy`, justamente porque este rótulo aqui já designa a classificação do §40 — aquilo classifica a *tool*, isto autoriza a *chamada*. O que continua fora: o enforcement do §41 fora do processo Python — não há hook `PreToolUse` barrando `terraform destroy` por `Bash` —, e a imposição só morde onde há política declarada, porque sem `policy` o comportamento é o de antes por decisão de não-regressão. | `tests/test_harness_authorization.py`, `tests/test_agent_autonomy.py` |
| **ExecutionState** | EXISTE, com teste | `sparkforge/case/store.py`: `PHASES = (intake, inventory, facts, diagnosis, hypothesis, experiment, validation, report)` + `GATES = (baseline_captured, dominant_bottleneck_identified, functional_validation_defined, flows_mapped)`, com `strict_gates` fail-closed via `rules/catalog/routing.yaml:gates`. Cobre o §36 quase por completo — falta só o mapeamento nominal para os estados do harness (`CREATED/PLANNED/RUNNING/WAITING_APPROVAL/...`), que são um relabeling do que já existe. | `tests/test_case_store.py` (729 linhas), `tests/test_case_router.py` |
| **EvaluationGate** | EXISTE PARCIAL | Dois sistemas distintos e não integrados: primeiro, `sparkforge/evals/runner.py:EvaluationRunner.run_router_eval()` mede acurácia do router contra `sparkforge/evals/datasets/router_dataset.json` — só **4 casos**, não os 5 casos de ouro que o §48 pede; segundo, `evals/fase0.xml` + `scripts/check_evals.py` é um segundo harness de avaliação, baseado em pares pergunta/resposta verificáveis contra fixtures — 10 pares. Nenhum dos dois é um "gate" que bloqueia merge/release; são scripts chamados manualmente/por teste. | `tests/test_eval_runner.py`, `tests/test_evals.py` |

## 2. Componentes adiados pelo próprio harness (§3: "somente depois avaliar")

| Componente | Classificação | Módulo(s) | Teste |
|---|---|---|---|
| **ModelRouter** | EXISTE, com teste — **duplicado** | `sparkforge/economy/router.py:CapabilityModelRouter.route_task()` (tier determinístico-primeiro, keyword-matched specialist skills, `ModelTier` de `TIER_0_DETERMINISTIC` a `TIER_6_MULTI_AGENT` — literalmente o §33/§34, incluindo "NONE é modelo válido" via `TIER_0_DETERMINISTIC` com `max_tokens=0`, `estimated_cost_usd=0.0`). Em paralelo, `sparkforge/agents/model_policy.py:ModelSelector.choose()` é um **segundo** router, orientado a inventário de contas (`ModelInfo`/`ModelDemand`), que decide por `quality`/`reasoning`/preço — não fala a língua de `ModelTier`. Os dois resolvem "qual modelo/tier usar" com esquemas incompatíveis. | `tests/test_economy_engine.py::test_capability_router_deterministic_first`, `::test_capability_router_specialist_skill`; `tests/test_model_and_observability.py::test_selector_uses_available_account_inventory_and_budget`, `::test_selector_uses_reasoning_for_high_risk_work` |
| **MemoryManager** | EXISTE PARCIAL | `sparkforge/agents/room.py:ConversationRoom` é append-only, JSONL, com `compact()` fazendo snapshot — é a separação que o §35 pede (não salva transcript completo, guarda `task/fact/hypothesis/challenge/handoff/decision/error/snapshot` tipados). Falta a camada de "known verified facts" cross-task/cross-sessão que o §35 também pede — `ConversationRoom` é por-case (`room_id`), não uma memória de projeto persistente entre cases. | `tests/test_agent_runtime.py::test_room_is_append_only_and_context_is_bounded`, `::test_context_selection_deduplicates_and_preserves_decision` |
| **RecoveryEngine** | NÃO EXISTE | `AutonomyController.should_stop()` (`sparkforge/agents/autonomy.py`) classifica quando parar (orçamento, estagnação, regressão), mas não há classificação de *tipo* de falha (`missing evidence / tool error / model error / invalid output / environment / permission / unsupported case`, §31) nem lógica de retry condicionada ao tipo (§32). | — |
| **TraceEngine** | EXISTE, com teste | `sparkforge/observability/tracer.py:AgentOpsTracker` + `sparkforge/observability/store.py:SQLiteTraceStore` (spans com tokens/custo, hierarquia via `parent_span_id`) cobre observability "real". Em paralelo, `sparkforge/agents/observability.py:TraceView` implementa exatamente o §56 ("não armazenar chain-of-thought"): `enabled=False` por padrão, sumário truncado a 160 chars a menos que `show_content=True`, e reporta explicitamente quando tokens são estimados vs reais (nunca inventa número). Dois módulos de trace, propósitos complementares (um é storage, outro é a política de exposição) mas não citados um do outro. | `tests/test_observability.py::test_agentops_tracer_and_sqlite_store`; `tests/test_model_and_observability.py::test_trace_view_is_hidden_by_default_and_warns_when_usage_is_partial` |
| **AgentFanoutGovernor** | EXISTE PARCIAL | `AutonomyBudget.max_agents` (`sparkforge/agents/autonomy.py`) e `Supervisor.Budget.max_rounds/max_messages` (`sparkforge/agents/supervisor.py`) limitam fanout numericamente. Falta a política declarativa por `ExecutionProfile` que o §25 pede (`simple task: agents=0`, `critical cross-domain: agents<=2`) — hoje o limite é um número fixo por instância de budget, não uma regra condicionada a `RiskLevel`/`ExecutionProfile`. | `tests/test_agent_autonomy.py`, `tests/test_agent_runtime.py` |
| **Cache** | EXISTE, com teste | `sparkforge/economy/cache.py:ArtifactCache` — cache de dois níveis (memória + disco), chave = sha256 de `{namespace, inputs, engine_version}`, TTL configurável. Cobre o §38 (content-addressed) quase literalmente. O §39 (separar FACT CACHE de JUDGMENT CACHE, invalidar por versão de catálogo/analyzer) não está implementado: `engine_version` é um único carimbo por chamada, não dois carimbos independentes para fato vs julgamento. | `tests/test_economy_engine.py::test_artifact_cache_set_get` |
| **Advanced planning** | NÃO EXISTE | Nada além do DAG de waves (já listado acima) e do plano de 7 fases do Supervisor. Sem replanning condicionado a resultado parcial. | — |

## 3. Preocupações transversais que o documento trata à parte

| Conceito | Classificação | Módulo(s) | Teste |
|---|---|---|---|
| **Routing L0–L4** (§11) | EXISTE PARCIAL | `sparkforge/case/router.py:next_step()` sobre `rules/catalog/routing.yaml` (51 KB) é um roteador determinístico completo: condições declarativas (`equals/absent/present/count_gt/count_eq/contains/any_where`), regras `ROUTE-*` (skill) e `AGENT-*` (coordenador) avaliadas na mesma engine, `blocked_by` por gate. Isso é o **L0 determinístico** do §11, robusto e testado. Os níveis L1–L4 (Skill route → specialist → reviewer → multi-agent) não têm um router formal equivalente — a escalada hoje é decisão do agente/coordenador em Markdown (`agents/*.md`), não código. | `tests/test_case_router.py`, mais os testes de `rules/catalog/routing.yaml` via `tests/test_rules_*` |
| **Execution waves** (§14) | EXISTE, com teste | `ExecutionDAG.compute_waves()` — ver tabela 1. | `tests/test_workflows_dag.py::test_execution_dag_waves` |
| **Harness contract** (§15) | EXISTE PARCIAL, sob outro nome | `rules/catalog/routing.yaml:gates` já é um contrato: cada gate declara `satisfied_by` (o fact que destrava), `produced_by` (o comando exato que produz esse fact) e `guards_phases` (onde ele morde) — validado na carga (`sparkforge/case/router.py:_validate_gates`, fail-closed contra gate malformado). Isso é o `success`/`failure`/`allowed_capabilities` do §15 escrito como dado versionado, não como classe Python `HarnessContract`. Falta o campo `mutation: bool` e `evaluation.golden_suite` explícitos — hoje implícitos na convenção do catálogo. | `tests/test_rules_catalog_reachability.py`, cobertura indireta via `tests/test_case_router.py` |
| **Structured handoff** (§27) | EXISTE, com teste | `sparkforge/workflows/handoff.py:StructuredHandoff` — campos quase idênticos ao pedido do §27 (`evidence_fact_ids`, `confidence`, `changed_files`→`changed_files`, `unresolved_questions`, `next_action`), com `to_compact_markdown()`. `sparkforge/case/resume.py:render_handoff()` é um segundo mecanismo de handoff, committado em `.sparkforge/handoff.md`, cobrindo cruzamento entre sessões Devin↔Claude Code (não entre agentes dentro da mesma sessão). Os dois cobrem momentos diferentes do mesmo problema e não compartilham schema. | `tests/test_workflows_dag.py::test_structured_handoff`; `tests/test_case_resume.py` |
| **Early exit** (§30) | EXISTE, com teste | `ModelTier.TIER_0_DETERMINISTIC` no router (custo 0, sem chamada de modelo) mais `AutonomyController.should_stop()` (`terminal=True` interrompe imediatamente) implementam a condição do §30 na prática, embora não exista uma função única chamada `early_exit()`. | `tests/test_economy_engine.py::test_capability_router_deterministic_first`; `tests/test_agent_autonomy.py::test_stop_on_stagnation_and_authorization_policy` |
| **Failure attribution** (§79) / **Failure spend governance** (§31) | NÃO EXISTE | `should_stop()` decide *que* parar, não classifica *por quê* nas sete categorias do §31 (`missing evidence/tool error/model error/invalid output/environment/permission/unsupported case`). Nenhum módulo produz esse enum. | — |
| **Tool allowlist** (§77) | EXISTE, com teste — **superfície diferente do harness** | `tests/test_execution_surface.py` já implementa uma allowlist fechada e testada, mas para **hooks e servidores MCP** (`.claude/settings.json`, `vendor/caveman/.claude-plugin/plugin.json`, `.mcp.json`) — não para tools MCP individuais do próprio Spark Forge. `AutonomyController.authorize_tool()` cobre allowlist por agente (`allowed_tools`), mas sem hook que a torne obrigatória em tempo de execução. | `tests/test_execution_surface.py` (allowlist de hooks/MCP), `tests/test_agent_autonomy.py` (allowlist por agente, não enforced) |
| **Authorization chain** (§76) | EXISTE PARCIAL | Fase I3: `sparkforge/agents/autonomy.py:authorize()` devolve `AuthorizationDecision` com agente, perfil, classe e a aprovação que sustentou a decisão; aprovação é por CLASSE e perfil é teto (`OFFLINE` recusa rede com aprovação ou sem). PARCIAL porque o enforcement do §41 não existe **fora do processo Python**: dentro dele a cadeia passou a ser imposta em `call_tool` (`CallPolicy`), com teste que prova que o handler não roda na recusa; `Bash` e `terraform destroy` seguem sem passar por ela. Antes desta fase: `authorize_tool()` era uma checagem de um nível (agente × tool × approval booleano), sem cadeia nem escopo. | `tests/test_harness_authorization.py` |
| **Claude Code hooks para enforcement** (§41) | NÃO EXISTE, para o propósito pedido | `.claude/settings.json` tem exatamente um hook, `SessionStart`, que só imprime o ruleset caveman quando `node` está ausente — nada de `PreToolUse` bloqueando `terraform apply`, `terraform destroy`, `aws s3 rm`, `lakeformation revoke`, expiração de snapshot etc., como o §41 pede explicitamente. A allowlist fechada existe (`test_execution_surface.py`) mas governa **hooks do projeto**, não ações destrutivas de tools de domínio. | `tests/test_execution_surface.py` prova que não há hook além do de caveman — confirma a ausência, não a cobre |
| **Prompt injection** (§42) | EXISTE PARCIAL | Fase I2: `docs/harness/UNTRUSTED-CONTENT.md` declara o invariante e `tests/test_harness_untrusted.py` o defende nas duas direções — texto de artefato não vaza para campo de catálogo, e continua visível no `snippet`, porque sanitizar a evidência seria a correção errada. PARCIAL pelo que o próprio documento declara descoberto: conteúdo que chega ao modelo por fora do `Finding` (um `Read` cru) não é alcançado por invariante nenhum daqui | `tests/test_harness_untrusted.py` |
| **Observability sem vendor lock-in** (§94) | EXISTE, com teste | `SQLiteTraceStore` é local, sem dependência de vendor (AgentOps, LangSmith etc. citados no nome da classe só como inspiração de shape, não como dependência real). | `tests/test_observability.py` |
| **Offline behaviour** (§70) | EXISTE, com teste | `tests/test_offline_expansion.py` mais o "offline-first" citado no histórico de commits do repositório (`b1241b1`, `91cada6`). `ExecutionProfile.OFFLINE` já existe em `sparkforge/registry/models.py` e é tratado em `CapabilityModelRouter.route_task()`. | `tests/test_offline_expansion.py`; `tests/test_economy_engine.py` cobre o profile indiretamente via `ExecutionProfile` |
| **Runtime harness vs evaluation harness** (§43, "crítico") | EXISTE, com teste | Fase I1: `docs/harness/RUNTIME-VS-EVALUATION.md` nomeia a fronteira e `tests/test_harness_boundary.py` a defende por AST — o runtime nunca importa `sparkforge.evals`, e a avaliação importa o runtime, que é a direção certa. O teste tranca um invariante que já valia; separação que vale por acidente deixa de valer no primeiro import distraído | `tests/test_harness_boundary.py` |
| **Grader hierarchy** (§45) | EXISTE, com teste — nunca formalizado como hierarquia | Toda a suíte de `tests/test_fixtures_golden_*.py` (32 arquivos) é grader **code-based determinístico** contra fixtures — o nível 1 do §45, e o único usado hoje. Não há grader LLM nem grader de state verification separado — o que, dado o §45 ("nunca usar LLM grader para algo que pytest pode verificar melhor"), é possivelmente já o comportamento correto, não uma lacuna. | Os 32 arquivos `tests/test_fixtures_golden_*.py` |
| **Golden cases do §48** | EXISTE PARCIAL | Caso 1/2 (Glue 4.0→5.1, Parquet e Iceberg) e caso 4 (Terraform, mudança destrutiva) têm fixtures e testes próprios (`test_fixtures_golden_migration.py`, `test_fixtures_golden_terraform.py`, `test_fixtures_golden_tfdiff.py`). Caso 3 (Lake Formation cross-account) tem `test_lakeformation_engine.py`, mas é um teste pequeno — muito mais raso que os outros golden suites, sem fixture dedicada equivalente. Caso 5 (Spark performance, event log + plano) tem fixtures separadas para plano (`test_fixtures_golden_plan.py`) e event log (`test_fixtures_golden_eventlog.py`) mas não um golden case único que combine os dois como o §48 pede. Nenhum dos 5 está reunido sob um dataset de avaliação nomeado "golden cases do harness" — cada um vive como suíte de teste de unidade/fixture, não como caso de harness. | ver arquivos citados |

## 4. Dois fatos citados no prompt, verificados

- **`sparkforge/providers/mock.py` e `sparkforge/cloud/worker.py` não têm teste em lugar nenhum.**
  Confirmado: nenhum arquivo em `tests/` importa `sparkforge.providers` ou `sparkforge.cloud`. `MockModelProvider.generate()` (mock.py) e `LocalFallbackWorkerBackend.dispatch()` (worker.py) são código morto do ponto de vista de prova — existem, compilam, mas nada exercita o comportamento.
- **`sparkforge/adapters` é o maior pacote e tem um gate de paridade que roda.**
  Confirmado por tamanho: `tools.py` (268,0 KB) e `_core.py` (219,7 KB) são, disparado, os dois maiores arquivos do pacote determinístico — maiores que todo `sparkforge/economy`, `sparkforge/context`, `sparkforge/registry`, `sparkforge/case`, `sparkforge/agents` e `sparkforge/workflows` somados. O gate de paridade é real e pesado: `tests/test_capability_parity.py` (819 linhas), `tests/test_agents_parity.py` (539 linhas) e `tests/test_platform_divergence.py` (227 linhas) — 1585 linhas de teste só para paridade entre adapters/plataformas. O histórico de commits confirma que esse gate já pegou regressão real (`2cc7d27 fix(ci): o gate de paridade do artefato nao alcancava scripts/, e estava vermelho desde 9474aa8`).

---

## Conclusão

### 1. O que o harness realmente acrescentaria, excluídas as duplicatas

Muito pouco em termos de **capacidade nova**, e um trabalho real em **unificação**:

- **RecoveryEngine com classificação de falha por tipo** (§31) e **authorization chain** (§76)
  são as duas únicas peças do harness sem *nenhum* equivalente no repositório hoje. São
  também as mais baratas de justificar: nenhuma delas duplica algo existente.
- **Um `CapabilityRegistry` de verdade** — hoje `CanonicalRegistry` guarda coleções por
  tipo (`agents`, `skills`, `tools`...), não por capability. Resolver `aws.glue.migration
  → {tools, skills, agents}` num único lookup é trabalho real, não relabeling.
- **Unificar os três budgets** (`TaskBudgetGuardrail`, `AutonomyBudget`, `Supervisor.Budget`)
  e os **dois model routers** (`CapabilityModelRouter`, `ModelSelector`) num shape só. Isso
  não é "harness novo": é dívida técnica que o harness, se escrito sobre a base atual sem
  essa fusão, herdaria e pioraria — passaria a haver *quatro* formas de orçamento em vez
  de três.
- **Enforcement de tool policy FORA do processo Python, via hook `PreToolUse`** (§41):
  dentro do processo a política deixou de ser só decisão — `adapters/tools.py:call_tool`
  chama `authorize()` por `CallPolicy` e o handler não executa quando a cadeia recusa,
  o que cobre as 65 tools num ponto só. O que resta é o que nunca passa por `call_tool`:
  um agente que rode `terraform destroy` por `Bash` não é interceptado por nada. Duas
  ressalvas honestas sobre o que já existe — a imposição só morde onde há política
  declarada (sem `policy`, o comportamento é o de antes, por não-regressão deliberada),
  e `adapters/cli.py` e `agents/supervisor.py` seguem sem chamá-la.
- **Um dataset de golden cases nomeado e completo para os 5 casos do §48** — os dados
  existem espalhados em fixtures de teste de unidade; reuni-los sob um harness de avaliação
  citável é trabalho de integração, não de invenção.

### 2. O que já está construído e deveria ser integrado, não escrito

A lista longa: `TaskSpec`, `ExecutionDAG.compute_waves` (dependency-aware waves),
`StructuredHandoff`, `TaskBudgetGuardrail`, `ArtifactCache` (content-addressed cache),
`CapabilityModelRouter` (incluindo "NONE é modelo válido" via `TIER_0_DETERMINISTIC`),
`ContextFunnel` + `ProgressiveDisclosureManager` + `KnowledgePackLoader` (a pirâmide
completa de context engineering do §19–§23), `ConversationRoom` (memória por-case,
append-only, tipada), `TraceView` (a política exata do §56 — não guarda
chain-of-thought por padrão), `AgentOpsTracker` + `SQLiteTraceStore` (observability
local, sem vendor lock-in), `AutonomyController` (early exit, stop-on-stagnation,
authorize_tool), `Supervisor` (execução em fases com orçamento), `case/store.py`
(state machine com gates fail-closed) + `case/router.py` (routing L0 determinístico,
explicável, com `reason`/`evidence`/`blocked_by`/`alternatives` — o próprio §12 já
implementado), `case/resume.py` (resume entre sessões), e o par
`sparkforge/migration/assessment.py` + `rules/catalog/routing.yaml:gates` que juntos
já são o "Harness Contract" (§15) do primeiro caso do §49 — `MigrationAssessment` tem
`gates`, `missing_evidence` e `recommendation` (`NO_GO`/`CONDITIONAL_GO`/`GO`), que é
exatamente o schema pedido pela §50.

O documento §0 do harness pede para "primeiro encontrar, depois integrar" — a lista
acima é a prova de que a maior parte do trabalho de "encontrar" já estava certa: os
conceitos do harness majoritariamente **já foram implementados**, só que em três
pacotes que não se conhecem (`sparkforge/economy`, `sparkforge/agents`,
`sparkforge/case` + `sparkforge/workflows`).

### 3. O que precisaria de um segundo consumidor antes de ser desenhado com honestidade

A fase que acabou de ser entregue produziu **uma** vertical concreta: o motor de
compatibilidade de migração Glue (`sparkforge/migration/`, área de regra `SF-MIG`),
com `MigrationAssessment` como único consumidor real de gates de execução
(`dados/performance/custo/canary`) e do padrão `steps` → `by_step` → `findings`.

Extrair um `HarnessContract` genérico — classe Python, não o dado em
`rules/catalog/routing.yaml` — a partir dessa única instância é exatamente a
"arquitetura prematura" que o próprio §100 do harness avisa contra ("pode resultar em
remover código recém-criado; isso é permitido e desejável"). Os componentes que estão
nessa posição, e que este documento recomenda **não** generalizar ainda:

- **`HarnessContract` como classe** (§15) — hoje só tem um consumidor real
  (`SF-MIG`/`MigrationAssessment`). Os outros golden cases do §48 (Lake Formation,
  Iceberg, Terraform, Spark performance) não têm um `*Assessment` equivalente; sem um
  segundo caso implementado no mesmo molde, qualquer abstração de contrato genérico
  estaria generalizando a partir de uma única instância.
- **`AgentFanoutGovernor` como política declarativa por `ExecutionProfile`** (§25) —
  hoje os limites de fanout são números fixos em duas classes de budget diferentes
  (`AutonomyBudget.max_agents`, `Supervisor.Budget.max_rounds`). Não há segundo cenário
  de multi-agent além do `Supervisor` de 7 fases para provar que a política precisa
  variar por perfil em vez de por instância.
- **`ModelRouter` unificado** — antes de desenhar a interface final, os dois
  consumidores atuais (`CapabilityModelRouter` orientado a tier/custo determinístico,
  `ModelSelector` orientado a inventário de contas Devin/Claude) precisam continuar
  vivos e observados por mais um ciclo para que a unificação não escolha o shape errado
  a partir de um único caso de uso dominante.
- **`RecoveryEngine`** — como não existe nenhuma implementação hoje (nem parcial), um
  desenho direto do zero corre o risco clássico do §100: nenhum caso real ainda gerou
  os sete tipos de falha do §31 em produção dentro deste repositório para validar que a
  taxonomia proposta é a certa.

---

*Fontes: `prompt_evo_harness.md` (linhas 1–3365, seções 0, 3, 5, 8–50, 66–79, 94, 100);
`sparkforge/workflows/`, `sparkforge/economy/`, `sparkforge/context/`, `sparkforge/registry/`,
`sparkforge/evals/`, `sparkforge/observability/`, `sparkforge/providers/`, `sparkforge/cloud/`,
`sparkforge/agents/`, `sparkforge/case/`, `sparkforge/rules/`, `sparkforge/migration/`,
`rules/catalog/routing.yaml`, `.claude/settings.json`, `tests/*.py`.*
