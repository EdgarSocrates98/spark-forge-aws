---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/DATABRICKS_PHOTON_PLAN/build_report.md
  sha256: "b78b28fd8929f3f6d1dce11afc8028a3d6d0c4ddaed1f1ed692d8253b4ffb10d"
hypothesis_outcome: confirmed
registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage, runtime_scope_gates, reachability_lists, snippet_measure, offline_manifest, sources_lock, fixture_corpus_gates, claims_gate, surface_lock, generated_reference, status_numbers_gate]
deviations:
  - "Tarefa nova TX (T6 no frontmatter do build_report), aprovada pelo coordenador: textos publicos que diziam Photon so declarado e so plan.python_udf fora da recusa (cli.py _PHOTON_FLAG_HELP, tools.py _PHOTON_INPUT e a descricao de runtime.photon e do motivo de pulo do judge, comentario de RuntimeContext.photon, comentarios do engine, explanation e proposed_change[1] de SF-ENV-006, README.md); photon saiu de AXES_DECLARED_ONLY em tests/test_capability_parity.py."
  - "Arquivos fora do manifesto do design: tests/test_capability_parity.py, tests/test_fixtures_golden_mcp_parity.py (texto do motivo ja declarado), tests/test_fixtures_golden_plan.py (literal ArrowEvalPython pandas -> arrow, mesmo veredito), os goldens de fixtures/runtime/databricks_divergent_spark, databricks_event_log_runtime e databricks_flag_runtime (so texto de SF-ENV-006), 17 paginas de docs/guia/referencia, docs/surface.lock.json, knowledge/databricks/runtime-matrix.md secao 3 U2, knowledge/spark/plan-reading.md, knowledge/INDEX.md, knowledge/offline-manifest.json, docs/claims.lock.json e docs/harness/."
  - "T3 passo 4: test_declared_only_axes_are_real_axes_without_producer nao falhou porque nao sabia derivar a chave de photon; o ajuste condicionado a essa falha foi feito na TX."
  - "T3: _photon_declarado removida; o caso dela entrou em _photon(sources, databricks), que devolve valor, fonte e divergencia numa leitura so."
  - "Os commits f1a91e76 e b18ff242 (160c890f e 14083311 antes do rebase) sairam com a linha Co-Authored-By de Claude Sonnet 5; sem amend, por regra."
  - "A branch foi rebaseada sobre origin/main depois do build: os hashes citados no build_report sao os de antes do rebase; os hashes de conteudo das fases nao mudaram (sdd check ok antes do ship)."
  - "No ship: tests/test_databricks_photon_plan.py teve uma linha quebrada em duas para passar no ruff (E501, 102 > 100), sem mudar o que o teste confere."
  - "No ship: docs/superpowers/STATUS.md ganhou a secao DATABRICKS_PHOTON_PLAN, que registra o que mudou no texto de epoca da secao DATABRICKS_SPARK sem reescreve-lo, e a linha Regras de diagnostico ganhou a frase de que SF-ENV-006 nao dispara com plano Photon."
  - "surface_lock, generated_reference e status_numbers_gate rodados alem dos registros de change_kinds, porque a TX moveu a superficie e a referencia gerada, e o STATUS foi editado no ship."
---

# DATABRICKS_PHOTON_PLAN — entrega

## Hipótese

Confirmada. A afirmação do define era que Photon é detectável no texto do plano pelo
prefixo dos operadores, e que uma recusa movida por esse artefato substitui a
dependência de `--photon` sem mudar nenhum veredito de plano sem Photon.

As duas partes da previsão foram medidas no ship:

- **Os dois planos Photon, sem declaração.** Extrator e `judge` sobre
  `fixtures/plan/photon_join` e `fixtures/plan/photon_udf` com contexto vazio (sem
  `--photon` e sem `--databricks`). Os dois emitem `plan.photon`. Os dois recusam
  `SF-PLAN-003`, `SF-PQ-002` e `SF-PQ-004` com `databricks.photon.unresolved`.
  `photon_join` ainda dispara `SF-PLAN-004` (`plan.aqe`) e `photon_udf` dispara
  `SF-PLAN-002` (`plan.python_udf`): são as duas exceções do design.
- **Nenhum veredito de plano sem Photon mudou.** Comparamos as 8 fixtures de
  `fixtures/plan` sem Photon, com o `findings.json` na base (`12d106fa`, merge-base
  com `origin/main`) contra o de HEAD. A chave foi (rule_id, severidade, subject), e
  deu 0 diferenças (SC1 = 0). O único golden de plano antigo que mudou foi
  `python_udf_in_plan`, e só no `udf_type` e no texto de SF-PLAN-002 (AC6). Esse é o
  "antes" que o teste de AC3 não segura sozinho.

A generalidade fica limitada pelos unknowns do define, e o ship diz isso em vez de
prometer mais. U1: a forma dos operadores veio de um ambiente só (Databricks Free
Edition, serverless, Spark 4.2.0, 2026-09-18). U2: o texto de suporte parcial de
`== Photon Explanation ==` não foi visto. A previsão fala dos dois planos
observados, e foi sobre eles que medimos.

## Comandos de aceite (`kind: command`)

Nenhum. Todos os `verified_by` do define são `kind: test`, em
`tests/test_databricks_photon_plan.py`. Rodados de novo no ship:
`python -m pytest tests/test_databricks_photon_plan.py -q` deu 14 passed (exit 0).

## Gates rodados

Um comando por vez, em primeiro plano, depois da correção de ruff e da edição do STATUS.

| registro | comando | resultado |
|---|---|---|
| pré-requisito | `sparkforge sdd check --repo . --feature DATABRICKS_PHOTON_PLAN` | `ok: true`, 0 recusas, 0 lacunas |
| pré-requisito (CI) | `python -m ruff check sparkforge scripts tests` | 1 E501 em `tests/test_databricks_photon_plan.py:157`, corrigido; depois, `All checks passed!` |
| `rules_catalog_gates`, `manifest_rule_count`, `fixture_kind_coverage`, `reachability_lists` | `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py -q` | 1144 passed |
| `runtime_scope_gates` | `python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q` | 715 passed |
| `snippet_measure` | `python -m pytest tests/test_harness_untrusted.py -q` | 4 passed |
| `fixture_corpus_gates` | `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q` | 89 passed |
| `offline_manifest` | `python -m pytest tests/test_offline_expansion.py -q` e `python scripts/verify_offline_bundle.py` | 4 passed; `ok: true`, `failed: []` |
| `sources_lock` | `python scripts/refresh_knowledge.py --update --offline` | sem diferença no lock |
| `surface_lock` | `python scripts/check_surface_lock.py` | 0 divergências |
| `generated_reference` | `python scripts/gen_reference_docs.py` e `python -m pytest tests/test_reference_docs.py -q` | 268 páginas, 0 regravadas; 5 passed |
| `claims_gate` | `python scripts/check_vnext_claims.py` e `python -m pytest tests/test_vnext_claims.py tests/test_docs_coverage.py tests/test_installed_provenance.py -q` | 0 divergências; 174 passed, 5 skipped |
| `status_numbers_gate` | `python scripts/check_status_numbers.py --strict` | 0 divergências (exit 0) |
| testes da entrega | `python -m pytest tests/test_databricks_photon_plan.py -q` e `python -m pytest tests/test_capability_parity.py tests/test_fixtures_golden_plan.py -q` | 14 passed; 112 passed |

**A suíte inteira não rodou**, nem em lotes. A máquina tem pouca memória, e o operador
vetou os lotes neste ship. Quem roda a suíte é o CI. Pelo mesmo motivo não rodaram
`tests/test_agents_parity.py` nem `scripts/sync_skills.py` sem `--check`: os dois
apagam o `.claude/agents/README.md`, que não é rastreado. Esta entrega não tem
`change_kind` `agent_or_skill`.

## Pendências

- **Skill `analyze-spark-plan` e espelhos.** Ainda rotulam `ArrowEvalPython` como "UDF
  vetorizada" e não citam `plan.photon`. Não foram editados porque editar passa pela
  sincronização de espelhos, que apaga `.claude/agents/README.md`. Fica para uma
  frente própria, com o `change_kind` `agent_or_skill` (`sync_skills`, `agents_parity`).
- **U1 e U2 do define continuam abertos.** Falta um plano Photon de outro Databricks
  Runtime (ou documentação oficial dos nomes de operador) e um plano com operação não
  suportada.
- **Limitações que o build aceitou** (ver `build_report.md`):
  - a linha `== Photon Explanation ==` entra em `plan.analyzed.measures.skipped_logical_lines`;
  - o subject de `plan.photon` depende do modo do explain;
  - a fonte `plan` não entra em `RuntimeContext.detected_from`;
  - uma seção de explicação sem nó Photon não emite o fact;
  - a recusa vale por case;
  - `AXES_DECLARED_ONLY` ficou vazio;
  - `risks` e `proposed_change[0]` de SF-ENV-006 estão incompletos, não falsos;
  - `.venv/Lib/site-packages` tem uma cópia velha do catálogo.
- **`docs/gates-por-mudanca.md`** não cita `check_status_numbers.py` nas seções de
  extrator e de corpus de fixture. Sugestão do build, não aplicada aqui.
- **Achado fora da feature.** O arquivo rastreado `tuple[dict[str` na raiz vem de
  `749d44b9` (PR #67) e ficou intocado.

## Lições

- O gate que o CI roda primeiro, o ruff, não estava na receita de verificação do
  build. Uma linha de 102 colunas no teste da própria feature passou pelas revisões
  por tarefa e pela revisão final. O build deve rodar
  `python -m ruff check sparkforge scripts tests` antes do relatório `done`.
- O teste de AC3 compara com o golden que a própria feature regenera, e por isso não
  segura o "antes". Quem mediu o "antes" foi a comparação contra a merge-base, feita
  no ship. Critério "nada mudou" deve nascer com o comando de comparação contra a base
  como `kind: command` no define.
- A contagem de fact kinds e de fixtures só apareceu na revisão final, pelo
  `check_status_numbers.py --strict`. Extrator e fixture nova movem o STATUS, e o
  mapa de gates dessas duas seções ainda não diz isso.
