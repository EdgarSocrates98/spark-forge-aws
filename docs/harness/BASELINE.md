# BASELINE — engine antes do Harness

Este documento existe porque `prompt_evo_harness.md` §4 ("BASELINE ANTES DO
HARNESS") exige um baseline medido antes de qualquer mudança de harness: "Sem
baseline não existe prova de melhoria." Sem ele, uma mudança futura no harness
não tem contra o que ser comparada.

Regra seguida na sua construção: **todo número aqui veio de um comando
executado nesta sessão e registrado ao lado dele.** Nenhum número foi copiado
de outro documento do repositório. Onde isso não foi possível — porque a
medição exigiria infraestrutura que o repositório ainda não tem — a seção
final diz isso explicitamente, em vez de estimar.

- **Commit medido**: `6a76b7a` (`git rev-parse --short HEAD`)
- **Branch**: `feat/fase6b-sf-cfg`
- **Data**: 2026-08-22

Precedente direto: o commit `6c3c396` publicou `docs/vnext/FINAL-REPORT.md`
com números como "-81,8% custo por 1k tasks" e "94,5% cache hit rate" sem
nenhum artefato de medição por trás. Uma auditoria de onze tarefas provou isso
e removeu os números; `docs/claims.lock.json` e
`scripts/check_vnext_claims.py` agora impedem que voltem. Este documento é do
mesmo gênero — uma tabela de números que alguém vai comparar depois — então
segue a mesma disciplina desde o primeiro rascunho.

## Testes e gates

| O quê | Valor | Comando |
|---|---|---|
| Testes coletados | 5791 | `python -m pytest --collect-only -q` |
| Suíte completa (medida pelo coordenador, não por este agente) | 5786 passed, 5 skipped em 989.21s | `python -m pytest -q -p no:randomly` |
| Gate de claims do vNext | `0 divergencia(s).` (exit 0) | `python scripts/check_vnext_claims.py` |
| Paridade de skills entre plataformas | `OK: .claude, .agents e .github em dia com skills/ e agents/` (exit 0) | `python scripts/sync_skills.py --check` |
| Gate de evals | `10 respostas verificadas contra o corpus, todas reproduzem.` (exit 0) | `python scripts/check_evals.py` |
| Bundle offline | `{"offline": true, "checked": 43, "failed": [], "ok": true}` (exit 0) | `python scripts/verify_offline_bundle.py` |

A diferença entre "testes coletados" (5791) e "testes na suíte completa"
(5786 passed + 5 skipped = 5791) bate — não há descarte silencioso de teste
entre coleta e execução neste commit.

## Superfície do motor

| O quê | Valor | Comando |
|---|---|---|
| Regras no catálogo | 119 | `python -c "from sparkforge.rules.loader import load_catalog; c=load_catalog(); print(len(c))"` |
| Regras bloqueadas (`blocked_on` presente) | 0 | mesmo catálogo, contando `r.get('blocked_on')` truthy |
| Áreas de regra (`category`, derivado do catálogo) | 17 | contagem de `r.get('category')` distintos no catálogo carregado |
| Arquivos em `sparkforge/facts/` (exceto `__init__.py`) | 22 | `ls sparkforge/facts/` |
| **Extratores de fatos** (modulo com `EMITTED_KINDS`) | **20** | import de cada modulo, contagem dos que declaram `EMITTED_KINDS` |
| Arquivos que NAO sao extratores | 2 (`runtime_matrix.py` e `secrets.py`, que nao emitem kind) | import de cada módulo em `sparkforge/facts/`, leitura do atributo `EMITTED_KINDS` |
| Kinds de fato únicos (união de todo `EMITTED_KINDS`) | 129 | mesmo script, união dos conjuntos |
| Ferramentas MCP | 41 | `python -c "from sparkforge.adapters.tools import TOOLS; print(len(TOOLS))"` |
| Rotas no catálogo de roteamento | 92 | `yaml.safe_load(open('rules/catalog/routing.yaml'))['rules']`, contagem da lista |
| Coordenadores (`agents/*.md`, fora de `executors/`) | 38 | `ls agents/*.md \| wc -l` |
| Executores (`agents/executors/*.md`) | 5 | `ls agents/executors/*.md \| wc -l` |
| Skills (`skills/*/SKILL.md`) | 40 | `ls skills/*/SKILL.md \| wc -l` |
| Diretórios de fixture dourada (total) | 181 | `find fixtures -mindepth 2 -maxdepth 2 -type d \| wc -l` |

Regras por área (contagem derivada do catálogo carregado, não de lista
manual): `agentic-platform` 35, `pyspark-code` 12, `emr-infra` 9,
`emr-serverless` 6, `glue-infra` 6, `spark-ui` 6, `athena` 5, `environment` 5,
`functional-validation` 5, `iceberg` 5, `parquet-layout` 5, `benchmark` 4,
`data-quality` 4, `graph` 4, `spark-plan` 4, `glue-migration` 3, `call-graph`
1.

Fixtures douradas por domínio (contagem de subdiretórios em cada
`fixtures/<domínio>/`, comando `find fixtures/<domínio> -mindepth 1 -maxdepth 1 -type d | wc -l`
repetido por domínio):

| Domínio | Fixtures |
|---|---|
| graph | 25 |
| emr_serverless | 19 |
| pyspark | 17 |
| dq | 13 |
| emr | 14 |
| funcval | 10 |
| migration | 10 |
| iceberg | 9 |
| terraform | 8 |
| plan | 7 |
| runtime | 7 |
| s3 | 7 |
| fusion | 5 |
| eventlog | 4 |
| sql | 4 |
| athena | 3 |
| callgraph | 3 |
| catalog | 3 |
| consumers | 3 |
| infra_code | 2 |
| tfdiff | 2 |
| bench | 6 |

Soma dos 22 domínios: 181 — bate com a contagem total acima; não há
diretório fora dos 22 domínios listados.

## Pacotes que o Harness vai governar

Para cada pacote-alvo do harness (`sparkforge/{workflows,economy,context,
registry,evals,observability,providers,cloud,adapters}`): arquivos `.py`
(excluindo `__init__.py`), linhas totais somando **todos** os `.py` do
diretório (`__init__.py` incluso), e se existe teste — nomeado, não apenas
afirmado.

| Pacote | Arquivos .py (sem `__init__`) | Linhas totais | Teste que exercita |
|---|---|---|---|
| `workflows` | 3 | 190 | `tests/test_workflows_dag.py` (`test_task_spec_serialization`, `test_execution_dag_waves`, `test_execution_dag_cycle_detection`, `test_structured_handoff`) |
| `economy` | 4 | 405 | `tests/test_economy_engine.py` (`test_token_usage_cost_estimation`, `test_budget_guardrail_detection`, `test_artifact_cache_set_get`, `test_capability_router_deterministic_first`, `test_capability_router_specialist_skill`, `test_token_waste_detector`) |
| `context` | 3 | 269 | `tests/test_context_funnel.py` (`test_context_funnel_deduplication`, `test_progressive_disclosure_levels`, `test_knowledge_pack_stale_detection`) |
| `registry` | 3 | 604 | `tests/test_canonical_registry.py`, mais uso em `tests/test_platform_compilers.py` e `tests/test_workflows_dag.py` |
| `evals` | 1 | 82 | `tests/test_eval_runner.py` (`test_router_golden_eval_dataset`) |
| `observability` | 2 | 240 | `tests/test_observability.py` (`test_agentops_tracer_and_sqlite_store`) |
| `providers` | 1 | 22 | **nenhum** |
| `cloud` | 1 | 58 | **nenhum** |
| `adapters` | 10 | 7813 | 16 arquivos de teste, entre eles `tests/test_adapters_cli.py`, `tests/test_adapters_mcp.py`, `tests/test_adapters_tools.py`, `tests/test_capability_parity.py` |

Comandos usados: contagem de arquivo com
`find sparkforge/<pacote> -name "*.py" ! -name "__init__.py" | wc -l`;
contagem de linhas com `find sparkforge/<pacote> -name "*.py" -exec cat {} + | wc -l`;
teste localizado com
`grep -rl "sparkforge\.<pacote>\b" tests/*.py` e confirmado lendo o arquivo
listado.

**`providers` e `cloud` não têm nenhum teste.** Busca por `providers` e por
`cloud` em `tests/*.py` (`grep -rln "providers" tests/*.py` e
`grep -rln "\bcloud\b" tests/*.py`) não retornou nenhum arquivo. O conteúdo
desses dois pacotes é pequeno (`sparkforge/providers/mock.py`, 22 linhas;
`sparkforge/cloud/worker.py` + `__init__.py`, 58 linhas) mas está,
hoje, sem cobertura — se o harness vier a depender deles, isso é dívida a
resolver antes, não depois.

## Token e custo

`prompt_evo_harness.md` §4 pede baseline de "tokens estimados/reais quando
disponíveis". A resposta honesta, depois de ler
`sparkforge/economy/` e `sparkforge/observability/`, é que **este
repositório não produz nenhum número real de token ou custo hoje** — só
infraestrutura para um dia produzir, ainda não conectada a uma execução real.

Evidência lida diretamente do código (não de docstring, do corpo das
funções):

- `sparkforge/economy/budget.py` define `TIER_PRICING`, uma tabela de preço
  por milhão de tokens digitada à mão (`tier_3_cheap_local`: US$0,10/US$0,40;
  `tier_5_premium`: US$3,00/US$15,00; etc.) e `TokenUsage.estimate_cost_usd()`,
  que multiplica essa tabela por contagens de token que **alguém precisa
  fornecer** — a classe não mede nada sozinha.
- `sparkforge/economy/router.py` (`CapabilityModelRouter.route_task`) devolve
  `estimated_cost_usd` como constante fixa por branch de decisão (`0.0`,
  `0.001`, `0.005`, `0.05`) — não é uma leitura de custo real, é um palpite
  embutido no código-fonte.
- `sparkforge/economy/waste_detector.py` (`TokenWasteDetector.analyze_trace`)
  opera sobre uma lista de `trace_events` que precisa ser passada por quem
  chama — nada no repositório hoje produz essa lista a partir de uma execução
  real. `grep -rln "AgentOpsTracker\|SQLiteTraceStore\|TokenUsage(" sparkforge/ agents/ skills/ scripts/`
  só encontrou o próprio pacote `sparkforge/observability/` como usuário
  dessas classes — nenhum outro lugar do código as invoca com dados de um
  agente de verdade.
- `sparkforge/observability/tracer.py` (`AgentOpsTracker`, `TraceSpan`,
  `ExecutionTrace`) e `sparkforge/observability/store.py`
  (`SQLiteTraceStore`) são um esquema de tracing completo, com uma tabela
  SQLite pronta para `input_tokens`, `output_tokens`, `estimated_cost_usd`
  por span — mas `end_span()` recebe esses valores como argumento; nada os
  preenche a partir de uma chamada real de modelo. O único teste,
  `tests/test_observability.py::test_agentops_tracer_and_sqlite_store`,
  grava e lê valores fabricados pelo próprio teste.

**Conclusão**: o baseline de economia de token está **ausente**, não
estimado-mal. Para existir, precisaria de: primeiro, um ponto de instrumentação
real no caminho de execução de um agente — algo que capture
`input_tokens`/`output_tokens`/`cached_tokens` de uma resposta de modelo de
verdade e chame `AgentOpsTracker.end_span()` com esses números; segundo, pelo
menos uma execução de referência gravada em `SQLiteTraceStore` para servir de
ponto de comparação; terceiro, a mesma disciplina de proveniência que este
documento segue — cada número futuro citando o `run_id` que o produziu, não
uma tabela de preço.

## O que este baseline NÃO mede

`prompt_evo_harness.md` §4 pede: testes, golden fixtures, comportamento de
CLI, comportamento offline, comportamento de MCP, latência, resolução
determinística, chamadas de ferramenta, agents usados, tokens
estimados/reais, tamanho de contexto, taxa de erro. Deste conjunto, este
documento cobriu testes, golden fixtures, comportamento offline (via
`verify_offline_bundle.py`) e a superfície de MCP/agents em contagem
estrutural. O resto, e por quê:

- **Comportamento de CLI em execução real**: não executei nenhum comando
  `sparkforge <verbo>` fim a fim nesta sessão — só contei ferramentas e rotas
  estaticamente. Não há, portanto, medição de "a CLI roda X caminhos e
  produz Y saída" — só de "a CLI declara X caminhos".
- **Latência**: nenhum comando medido aqui reporta tempo de execução exceto
  a suíte de testes (989.21s, e essa medição não é minha — é do
  coordenador). Não há baseline de latência por operação (por regra, por
  tool call, por rota).
- **Resolução determinística**: não medi que fração das tarefas reais o
  motor resolve via regra/fato determinístico (tier 0/1 do roteador) contra
  quantas precisariam de um modelo. `CapabilityModelRouter.route_task`
  existe e tem regra para isso, mas sem um corpus de tarefas reais rodando
  contra ele, não há taxa a reportar — só a lógica de decisão.
- **Chamadas de ferramenta em execução real**: contei quantas ferramentas
  MCP existem (41) e quantas rotas o catálogo declara (92), não quantas
  chamadas uma tarefa real dispara nem em que ordem.
- **Tamanho de contexto**: `sparkforge/context/` tem teste
  (`test_context_funnel_deduplication`, `test_progressive_disclosure_levels`,
  `test_knowledge_pack_stale_detection`), mas nenhum desses testes reporta um
  número de tokens ou bytes de contexto que sirva de baseline comparável —
  são testes de comportamento (dedupe acontece, nível progressivo existe),
  não de tamanho.
- **Taxa de erro em produção**: a única taxa de erro medida aqui é a de
  testes (0 falhas, 5 skips na medição do coordenador). Não há execução real
  do harness ou dos agents fora de teste, logo não há taxa de erro
  operacional a reportar.
- **Token e custo real**: coberto na seção anterior — ausente, com o motivo
  escrito por extenso ali, não repetido aqui.

Cada um desses pontos exige o mesmo tipo de instrumentação que falta para
token/custo: uma execução real do sistema, capturada, antes que exista
número honesto para citar. Até lá, qualquer harness que se compare contra
este baseline só pode reivindicar melhoria nas dimensões que esta tabela
efetivamente mede.
