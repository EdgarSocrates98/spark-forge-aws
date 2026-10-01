---
sdd: 1
feature: SF_STUBS
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SF_STUBS/build_report.md
  sha256: "759fecd61f58b4cb18c9eb42cedd1ad1da76dfe2db91f5efcb528a6fd04b4e35"
hypothesis_outcome: confirmed
registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage, routing_yaml, coordinator_rule_areas, sync_skills, agents_parity, surface_lock, generated_reference, router_gates, status_numbers_gate, offline_manifest, sources_lock, claims_gate]
deviations:
  - "Os goldens de assessment de fixtures/scenarios (tres) e evals/holdout (dois) foram regenerados, porque carregam a contagem do catalogo (D10). O diff so move catalog_rules, unguarded_rules, reachable_rules e a frase statement; findings e recusas ficaram identicos. A previsao dizia que os goldens de cenario passavam sem regeneracao; o que ela falsificava era achado mudar, e nenhum mudou."
  - "D1 do design afirmava que scripts/sync_skills.py cuida de .codex; nao cuida. Os 19 .codex/agents/*.toml sairam por git rm na T2, e as secoes realocadas foram portadas a mao para dois .toml na revisao final (0161da5b)."
  - "Arquivos fora do manifesto do design: config/teams-expansion.yaml e config/agentic-expansion.yaml (quatro times removidos, fica governance-security), as skills aws-database, aws-messaging-and-streaming, aws-serverless, aws-storage e provision-s3-tables-table, docs/guia/usos/custo-e-capacidade.md, docs/guia/12-espelhos-e-dependencias.md, docs/vnext/CURRENT-STATE.md, docs/harness/CODEINTEL-GAP.md, docs/harness/CURRENT-HARNESS-GAP.md, .devin/README.md, sparkforge/findings/validate.py, sparkforge/finops/report.py (SF-SQL em _AREAS_DE_CODIGO), scripts/check_status_numbers.py (comentario), tests/test_rules_loader.py, tests/test_findings_validate.py e os .codex/agents/*.toml."
  - "Testes existentes ajustados: test_sync_render::test_agent_so_aparece_onde_ha_um_coordenador_so (tres skills sairam, tres ganharam coordenador unico) e test_rules_loader::test_every_committed_coordination_area_is_inert (saiu so a precondicao de existir area)."
  - "Alegacoes do gate de lastro remedidas por id: VNX-640 (752), VNX-726, VNX-503/508/510/511 (proof historical em 9c433b98), VNX-053, VNX-056, VNX-430; novas: VNX-793, 794, 795 e 796."
  - "Revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro achou 0 critico, 4 importantes e 11 menores, todos corrigidos em 0161da5b menos um fora de escopo (Pendencias)."
---

# SF_STUBS — entrega

## Hipótese

**Confirmada.** A previsão tinha três formas de falhar, e nenhuma aconteceu:

- **Contagem de executáveis:** continuou em 157. As não executáveis foram de 35 para 0
  (`tests/test_sf_stubs.py::test_catalogo_so_tem_regra_que_julga`).
- **Goldens de achados:** nenhum mudou. `python -m pytest tests/test_fixtures_golden*.py -q`
  deu 3217 passed e 4 skipped, sem regenerar nada, e a árvore ficou limpa. Nos cinco
  goldens de assessment, que carregam a contagem do catálogo, o diff moveu só os campos
  de contagem (primeiro desvio).
- **Tool órfã:** nenhuma ficou
  (`tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan`).

## Medidas

| | antes (`91643841`) | depois |
|---|---|---|
| regras no catálogo | 192 | 157 |
| regras executáveis | 157 | 157 |
| áreas de coordenação | 35 | 0 |
| coordenadores em `agents/` | 38 | 19 |
| skills | 66 | 56 |
| rotas em `routing.yaml` | 101 | 47 |
| bytes de skills (surface lock) | 533 906 | 522 870 |

## Gates rodados

| gate | comando | resultado |
|---|---|---|
| regra | `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py -q` | 934 passed |
| agent e skill | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q` | 211 passed |
| referência, roteamento, knowledge, superfície | `python scripts/gen_reference_docs.py` (0 regravadas) e `python -m pytest tests/test_reference_docs.py tests/test_router_agents.py tests/test_case_router.py tests/test_case_store.py tests/test_artifact_contents.py tests/test_offline_expansion.py tests/test_refresh_knowledge.py tests/test_surface_lock.py -q` | 212 passed |
| bundle offline | `python scripts/verify_offline_bundle.py`; `python scripts/refresh_knowledge.py --update --offline` | exit 0; nenhuma mudança |
| superfície | `python scripts/check_surface_lock.py` | 0 divergências |
| lastro | `python scripts/check_vnext_claims.py` | 0 divergências |
| goldens | `python -m pytest tests/test_fixtures_golden*.py -q` | 3217 passed, 4 skipped |
| estilo | `python -m ruff check sparkforge scripts tests` | limpo |

Comandos de `kind: command` do define:

- AC6 `python scripts/sync_skills.py --check`: exit 0, com o `.claude/agents/README.md` não
  rastreado fora da árvore, como no CI. Com ele presente, a única saída é o `ORFAO` dele.
- AC7 `python scripts/check_status_numbers.py --strict`: exit 0.

## Pendências

- **Sete `sf-*` sem rota viva.** `sf-analytics-specialist`, `sf-graph-specialist`,
  `sf-neptune-specialist`, `sf-orchestrator`, `sf-pyspark-specialist`,
  `sf-storage-specialist` e `sf-token-verifier` só são alcançáveis por rotas
  `__agentic_*__`, que nenhum código aciona. Pelo mesmo critério desta feature, isso é
  oco. Fica para a próxima.
- **Subagents sem handoff.** 13 dos 16 subagents de `config/subagents.yaml` não são mais
  citados em handoff de time nenhum.
- **Tools inexistentes.** `config/agentic-expansion.yaml` lista tools que não existem em
  `TOOLS` (por exemplo `sparkforge_context_pack`); nada as consome.

## Lições

- Os dois `config/*-expansion.yaml` e as skills `aws-*` só apareceram depois da T2, num
  `git grep` pelos nomes removidos. Um `git grep` completo pelos nomes que vão sair devia
  rodar no design, antes do manifesto.
- O D1 afirmou sem conferir que o `sync_skills.py` gera `.codex/`. Afirmação sobre o que um
  script faz se confere rodando o script.
- A ordem das tarefas foi decidida pelos testes existentes, e acertou: remover em partes
  teria deixado vermelhos atravessando commits.
