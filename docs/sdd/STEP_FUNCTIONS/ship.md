---
sdd: 1
feature: STEP_FUNCTIONS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STEP_FUNCTIONS/build_report.md
  sha256: "9fff5aa6bf6c44d8b426fba9e6ec6fec318ae6be3e4dc65c44c8c93d732f5191"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, routing_yaml, coordinator_rule_areas, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, sync_skills, agents_parity, router_gates, status_numbers_gate, claims_gate]
deviations:
  - "Design emendado no plano: runtime_scope {} nas quatro regras em vez de {glue: '*'} (o ASL sozinho nao detecta runtime Glue), primeiro retrier que casa em vez da soma, dez fixtures em vez de seis, e os arquivos que os gates exigem acrescentados ao manifesto."
  - "A revisao final voltou ao build com sete achados importantes e doze menores, todos corrigidos em 8c5a764d: SF-SFN-004 exige .sync, SF-SFN-001 caiu para P2 e respeita polling por getJobRun e o Next do conteiner, SF-SFN-002 e SF-SFN-003 restritas as frases citadas, MaxAttempts ilegivel e JSON profundo nomeados em sfn.unresolved; mais duas fixtures (doze no corpus)."
  - "O golden fixtures/debate/retomada/expected/brief.json mudou numa linha: a allowlist de extratores de debate ganhou step-functions. Nao e golden de achado."
  - "O plan.md ficou com state_count 8; a fixture tem 7 estados, e o teste foi corrigido."
  - "A branch ficou empilhada sobre o PR #89 durante o build e foi rebaseada sobre a main depois do merge."
  - "Revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro rodou."
---

# STEP_FUNCTIONS — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de três jeitos, e nenhum aconteceu:

- **Cada regra dispara na sua fixture e fica calada nas negativas.**
  - SF-SFN-001 dispara só em `glue_sem_sync`.
  - SF-SFN-002 dispara nas cinco fixtures com retrier de falha efetivo.
  - SF-SFN-003 dispara só em `express_com_sync`.
  - SF-SFN-004 dispara só em `retry_duas_camadas`.
  - Ficam caladas `glue_limpo`, `definicao_ilegivel`, `retry_so_no_glue`,
    `retry_duas_camadas_sem_sync` e `glue_polling_com_get_job_run`.
  - `JobName` dinâmico sai `sfn.unresolved` com `job_name_dynamic`, nunca como link.
- **A área passa pelo critério de domínio:** `tests/test_criterio_de_dominio.py` dá 7
  passed.
- **Nenhum golden de achado existente mudou.**
  - `python -m pytest tests/test_fixtures_golden*.py -q` na árvore final deu 3242
    passed e 4 skipped, sem regeneração.
  - Houve 1 error de teardown, causado por um `sparkforge sdd` rodado durante a suíte. O
    arquivo, rodado sozinho, deu 34 passed.
  - Os cinco goldens de assessment mudaram só na contagem do catálogo (157 para 161).
  - O `brief.json` de debate mudou numa linha. Ele não é golden de achado.

## O que o domínio entrega

- **Extrator.** `sparkforge analyze step-functions --path` lê o `.asl.json` ou a saída de
  `describe-state-machine`, e a tool `sparkforge_analyze_step_functions` faz o mesmo. Os
  dois emitem `sfn.task` por estado Task com:
  - o padrão de integração;
  - o `JobName` literal ou dinâmico;
  - o retry efetivo do primeiro retrier que casa, 3 quando omitido;
  - o `Catch` e o `TimeoutSeconds`;
  - o `Next` efetivo, herdado do contêiner.
- **Derivação em `fuse`.** Ela liga o Task Glue `.sync` ao `aws_glue_job` de mesmo nome.
- **Regras.** São quatro na área SF-SFN, coordenada pelo `glue-infra-reviewer` pela rota
  AGENT-086:
  - SF-SFN-001, P2: Glue sem `.sync` com estado seguinte e sem polling.
  - SF-SFN-002, P1 com `MaxAttempts` omitido, senão P2: o retry agenda o job batch
    inteiro de novo.
  - SF-SFN-003, P1: `.sync` sob `EXPRESS` declarado.
  - SF-SFN-004, P2: duas camadas de retry sobre o mesmo job. A composição das duas não é
    documentada, e a regra não afirma contagem.
- **Conhecimento.** `knowledge/stepfunctions/glue-integration.md` guarda as frases citadas
  e seis lacunas nomeadas.

## Medidas

| | antes (`0d7050c3`) | depois |
|---|---|---|
| regras | 157 | 161 |
| tools | 106 | 107 |
| extratores | 38 | 39 |
| rotas | 40 | 41 |
| fontes vigiadas | 254 | 262 |

## Gates rodados

| gate | comando | resultado |
|---|---|---|
| regra, área, roteamento, escopo | `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py tests/test_rule_scope_by_nature.py tests/test_databricks_rule_audit.py -q` | 1490 passed |
| domínio, extrator, fusão, case, snippet, cenários | `python -m pytest tests/test_criterio_de_dominio.py tests/test_sf_stubs.py tests/test_stepfunctions.py tests/test_facts_fusion.py tests/test_case_router.py tests/test_case_store.py tests/test_artifact_contents.py tests/test_facts_scan.py tests/test_harness_untrusted.py tests/test_fixtures_scenarios.py tests/test_evals_holdout.py tests/test_sdd.py -q` | 448 passed |
| agent, superfície, tool, números | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_skill_content.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_offline_expansion.py tests/test_adapters_tools.py tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_fixtures_golden_mcp_parity.py tests/test_bootstrap_budget.py tests/test_vnext_claims.py tests/test_status_numbers_gate.py tests/test_arvore_versionada.py -q` | 1465 passed |
| espelhos | `python scripts/sync_skills.py --check`, com o README não rastreado fora | exit 0 |
| referência gerada | `python scripts/gen_reference_docs.py` | 0 regravadas |
| superfície | `python scripts/check_surface_lock.py` | 0 divergências |
| bundle offline | `python scripts/verify_offline_bundle.py` (AC9) | exit 0 |
| lock de fontes | `python scripts/refresh_knowledge.py --offline --update` | árvore sem mudança |
| números | `python scripts/check_status_numbers.py --strict` (AC10) | exit 0 |
| lastro | `python scripts/check_vnext_claims.py` | 0 divergências |
| goldens | `python -m pytest tests/test_fixtures_golden*.py -q` | 3242 passed, 4 skipped, 1 error de teardown (acima) |
| estilo | `python -m ruff check sparkforge scripts tests` | limpo |

## Pendências

- **U1:** a composição do retry do Step Functions com o `MaxRetries` do Glue. Destrava um
  histórico de execução real com falha.
- **U2:** nenhum ASL real foi observado.
- **Lacuna 4:** não se sabe se a API recusa `EXPRESS` com `.sync`. Destrava
  `aws stepfunctions validate-state-machine-definition --type EXPRESS`.
- **Fora de escopo:**
  - o `definition` embutido no Terraform (`aws_sfn_state_machine`);
  - o histórico de execução;
  - Timeout do Task contra o timeout do job;
  - Distributed Map com `ExecutionType` `EXPRESS`.

## Lições

- A revisão final achou sete defeitos que os testes das tarefas não pegavam, todos de
  texto ou de padrão fora do caminho feliz: polling, `End` de ramo, Request Response com
  retry. Em domínio novo, a revisão do texto da regra contra as frases citadas precisa de
  um passo próprio.
- Rodar a CLI `sparkforge` com a suíte rodando derruba um teste por teardown. Nada de
  `sdd stamp` nem `check` enquanto os goldens rodam.
- Plano escrito por subagente trouxe números que o build corrigiu: `state_count`, as
  alegações e os links. O build publica o que o gate mede, e o plano fica como registro.
