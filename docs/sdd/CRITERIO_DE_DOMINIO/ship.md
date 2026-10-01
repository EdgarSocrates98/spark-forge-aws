---
sdd: 1
feature: CRITERIO_DE_DOMINIO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/CRITERIO_DE_DOMINIO/build_report.md
  sha256: "43171280d8bb4d0912870d2d85563f0a3130e8a0a9ca7454f6348f853d27575a"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity, surface_lock, generated_reference, router_gates, status_numbers_gate, offline_manifest, sources_lock, claims_gate]
deviations:
  - "D1 emendado no build (43de7901): a primeira versao nao contava condicao case nenhuma e reprovava glue-incremental-performance-architect; o explore contou a rota AGENT-006 por outro criterio. Agora conta a rota com condicao case cujo valor nao e sentinela __nome__."
  - "O golden fixtures/knowledge_drift/filtro_por_url foi regenerado pelo proprio teste (SPARKFORGE_REGEN_DRIFT=1), porque scripts/regen_fixtures.py nao cobre knowledge_drift; sairam quatro caminhos agents/<removido>.md e totals.agents foi de 8 para 4."
  - "refresh_knowledge.py --offline --update nao atualiza knowledge/offline-manifest.json; o sha256 foi recalculado com sparkforge.tools.offline._content_sha256."
  - "Arquivos fora do manifesto: tests/test_platform_compilers.py, docs/guia/07-conhecimento-e-catalogo.md, docs/vnext/CURRENT-STATE.md, docs/harness/CODEINTEL-GAP.md, docs/harness/CURRENT-HARNESS-GAP.md, skills/aws-database e skills/aws-observability (com espelhos e referencia gerada)."
  - "A T2 reintroduziu um nome removido pelo SF_STUBS em docs/vnext/AGENT-CATALOG.md; tests/test_sf_stubs.py pegou no ship, corrigido em commit proprio."
  - "Revisao em dois estagios por tarefa nao rodou; o controlador conferiu relatos, gates e um git grep final."
  - "Corrigido depois do CI do PR #89: a secao nova de docs/gates-por-mudanca.md exige chave propria em sparkforge/sdd/change_kinds.yaml (tests/test_sdd.py::test_change_kinds_casa_com_os_titulos_do_documento), e a chave domain entrou; o design do SF_STUBS trocou o representante sf-analytics-specialist, removido aqui, por sf-security-reviewer, com a cascata recarimbada."
---

# CRITERIO_DE_DOMINIO — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de três jeitos, e nenhum aconteceu:

- **Na árvore antiga o teste falha nos três níveis.** Rodado sobre `91643841`, antes do
  SF_STUBS, `tests/test_criterio_de_dominio.py` deu 7 failed de 7.
  - Área: `SF-AGENTS-001`, `SF-AIRFLOW-001`...
  - Coordenador: `sf-agent-builder.md`.
  - Rota: `sf-agent-evaluation-specialist`, `sf-context-engineer`...
- **Hoje o teste passa**: 7 passed.
- **Nenhum golden de achado mudou.** `python -m pytest tests/test_fixtures_golden*.py -q`
  deu 3217 passed e 4 skipped, sem regeneração, com a árvore limpa.

## O critério

Domínio entra por artefato coletável, nunca por nome de agente. Ele está escrito em
`docs/gates-por-mudanca.md`, seção *Critério de domínio: artefato antes de nome*, com um
ponteiro no `CLAUDE.md` e no `AGENTS.md`. `tests/test_criterio_de_dominio.py` trava três
portas:

- **área:** tem regra executável sem `blocked_on`, e o catálogo commitado não tem regra
  `executable: false`;
- **coordenador:** declara ao menos uma área que julga;
- **rota:** ao menos uma dispara por `findings_area`, `fact` ou entrypoint real, não só
  por sentinela `__agentic_*__`.

## Medidas

| | antes (`99ae3eaf`) | depois |
|---|---|---|
| coordenadores em `agents/` | 19 | 12 |
| skills | 56 | 51 |
| rotas em `routing.yaml` | 47 | 40 |
| bytes de skills (surface lock) | 522 870 | 516 561 |

Somando as duas features, os coordenadores foram de 38 para 12, as skills de 66 para 51
e as regras de 192 para 157. Todas as 157 são executáveis.

## Gates rodados

| gate | comando | resultado |
|---|---|---|
| critério, regra e roteamento | `python -m pytest tests/test_criterio_de_dominio.py tests/test_sf_stubs.py tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_case_router.py tests/test_case_store.py tests/test_artifact_contents.py -q` | 944 passed, depois da correção em `AGENT-CATALOG.md` |
| agent, skill, referência, knowledge | `python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_skill_content.py tests/test_reference_docs.py tests/test_surface_lock.py tests/test_offline_expansion.py tests/test_refresh_knowledge.py tests/test_canonical_registry.py tests/test_platform_compilers.py tests/test_bootstrap_budget.py -q` | 750 passed |
| espelhos | `python scripts/sync_skills.py --check`, com o README não rastreado fora | exit 0 |
| referência gerada | `python scripts/gen_reference_docs.py` | 0 regravadas |
| superfície | `python scripts/check_surface_lock.py` | 0 divergências |
| bundle offline | `python scripts/verify_offline_bundle.py` | exit 0 |
| números | `python scripts/check_status_numbers.py --strict` (AC9) | exit 0 |
| lastro | `python scripts/check_vnext_claims.py` | 0 divergências |
| goldens | `python -m pytest tests/test_fixtures_golden*.py -q` | 3217 passed, 4 skipped |
| estilo | `python -m ruff check sparkforge scripts tests` | limpo |

## Pendências

- Os subagents de `config/subagents.yaml` e as tools inexistentes de
  `config/agentic-expansion.yaml` continuam como estavam (pendência do SF_STUBS).
- Correção (2026-09-19, depois do ship): a documentação não dá esses dois atalhos como
  existentes. `docs/gates-por-mudanca.md` manda recalcular o `sha256` do
  `offline-manifest.json` com `sparkforge.tools.offline._content_sha256`, e a docstring de
  `tests/test_fixtures_golden_knowledge_drift.py` manda regenerar com
  `SPARKFORGE_REGEN_DRIFT=1`. Quem citou os comandos errados foi o plano do SF_STUBS.
- `docs/agentic-evolution.md` tem mojibake anterior à feature.

## Lições

- O critério do explore e o do teste precisam ser o mesmo texto. A contagem "12 de 19"
  foi feita por uma regra diferente da que o D1 escreveu, e só o vermelho da T1 mostrou
  a diferença.
- Teste de documento vivo de uma feature pega regressão da seguinte: o
  `tests/test_sf_stubs.py` acusou o nome que a T2 desta feature reintroduziu.
- Um subagente deixou arquivo no índice, e o commit do controlador o levou junto. Antes
  de commitar, conferir `git status` e o `--stat`.
