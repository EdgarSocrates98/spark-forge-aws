---
sdd: 1
feature: LF_FTA_DECLARADO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/LF_FTA_DECLARADO/build_report.md
  sha256: "8c472f7c654e8c8d8a98080d35b040abac05bc95657778ad6ef2da421f7bccd1"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, status_numbers_gate, claims_gate]
deviations:
  - "scripts/regen_fixtures.py sem argumento nao cobre fixtures/lakeformation/; conta_sem_full_table_access e grant_de_leitura_em_local_registrado foram regenerados por nome."
  - "O title de SF-LF-010 nao mudou (D3 previa); explanation, risks e rollback mudaram."
  - "Registros fora do manifesto: README, guia 06, claims.lock.json, CODEINTEL-GAP e ADR-010 (numeros), e seis meta.yaml de fixtures com o resolver."
  - "Sem subagente por tarefa nem revisao em dois estagios: o controlador executou as tres tarefas."
  - "Revisao por tarefa nao foi feita; a revisao unica depois do ship achou C1: o golden fixtures/scan/misto (after_fuse 69 -> 70) que nenhum gate do ship rodava. Regenerado por SPARKFORGE_REGEN_SCAN=1."
  - "Correcao da revisao: M1 (sem versao do Glue ou no 4.0 nem SF-LF-010 nem SF-LF-004 acusam), M2 (a razao e a secao 5, nao a 7) e M3 (spark.conf.set tardio) declarados em risks de SF-LF-010 e no STATUS, sem mudar codigo."
  - "M5: agente, skill e docs/aws/glue/6.0/lakeformation.md ganharam lakeformation.fta_declared; superficie +157 bytes. M6: fixtures/sarif/terraform/input/facts.json e copia estatica sem gerador, mantida sem o kind."
  - "scripts/regen_fixtures.py sem argumento pula fixtures/lakeformation/, iam_access e resource_link; fixtures/scan/ fica fora do script."
---

# LF_FTA_DECLARADO — entrega

## Hipótese

Confirmada, parte por parte:

- `lf_negado_fta_append_sem_all` e `lf_negado_fta_grant_all` ganham
  `lakeformation.fta_declared` e perdem `SF-LF-010`; nenhum outro finding muda (diff de
  `expected/findings.json`: só as duas entradas `SF-LF-010` saem; a segunda fixture fica sem
  finding). `tests/test_fixtures_golden_cloudwatch_logs.py::test_fta_declarado_cala_sf_lf_010_nos_goldens`.
- Localização registrada com só `spark.hadoop.fs.s3.impl`: `SF-LF-010` continua disparando
  (`tests/test_lakeformation_rules.py::TestSfLf010::test_registrado_so_com_fs_s3_impl_continua_disparando`).
- Nenhum golden sem resolver perdeu `SF-LF-010`: `grant_de_leitura_em_local_registrado`
  continua disparando, só com o texto novo.

## Gates rodados

Sobre `3b1e1e40`, pytest com `-p no:cacheprovider --basetemp=E:/sfpt_fta`:

| Registro | Comando | Exit |
|---|---|---|
| reachability_lists, fixture_kind_coverage, snippet_measure | `pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py` | 0 (731 passed) |
| rules_catalog_gates, manifest_rule_count | `pytest` lakeformation (access_graph, engine, matrix, missing_grant, rules), facts_lakeformation, rules_loader, rules_engine, docs_coverage, rules_governance, databricks_rule_audit, diagnosis_root_cause, harness_untrusted, rules_errors, rule_scope_by_nature, runtime_inferred_from_facts | 0 (1146 passed) |
| goldens | `pytest tests/test_fixtures_golden_cloudwatch_logs.py tests/test_fixtures_golden_infra_code.py tests/test_fixtures_golden_lakeformation.py tests/test_fixtures_kind_coverage.py` | 0 (439 passed, lakeformation rerodado depois do regen por nome: 28 passed) |
| status_numbers_gate | `python scripts/check_status_numbers.py --strict` | 0 (0 divergências) |
| claims_gate | `PYTHONIOENCODING=utf-8 python scripts/check_vnext_claims.py` | 0 (0 divergências) |
| — | `ruff check sparkforge scripts tests` | 0 |

`knowledge/` não mudou; `verify_offline_bundle` não se aplica.

## Comandos `kind: command` do define

- AC8: `python scripts/check_surface_lock.py && python scripts/check_vnext_claims.py && python scripts/check_status_numbers.py --strict`, exit 0.

## Números movidos

Fact kinds distintos 245 → 246; achados sem pergunta de ouro 34 em 63 → 32 em 61; VNX-674
251276 → 251707; VNX-726 89,0 → 89,1. Regras, extratores, fixtures e superfície não mudam.

## Lições

- `scripts/regen_fixtures.py` sem argumento não percorre todos os corpus (falta pelo menos
  `fixtures/lakeformation/`). Depois do regen, procure por conteúdo (`grep` do atributo que
  gera o kind novo em `expected/facts.json`) e rode os módulos de golden do domínio; não confie
  no `git status` do regen.
- Mudar o texto de uma regra move os goldens onde ela dispara, mesmo quando o disparo não muda:
  `findings.json` carrega explanation, risks e rollback.

## Rodada de correção da revisão (2026-09-25)

Revisão por tarefa não foi feita; a revisão única, depois do ship, achou **C1**: o golden de
`fixtures/scan/misto` contava 69 facts depois do `fuse` e passou a contar 70, porque o
`main.tf` dele declara o resolver. Nenhum gate da tabela acima rodava
`tests/test_fixtures_golden_scan.py`. Os 58 módulos de golden rodaram um por vez; só o de
scan falhou, e foi regenerado. Os achados menores (M1, M2, M3, M5, M6) e o que foi feito com
cada um estão no `build_report.md`, seção de mesmo nome.

| Gate | Comando | Exit |
|---|---|---|
| goldens | `pytest tests/test_fixtures_golden*.py`, um arquivo por vez, depois de todas as correções | 0 nos 58 (3319 passed, 4 skipped) |
| paridade | `pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_reference_docs.py` | 0 (149 passed) |
| área | `pytest tests/test_lakeformation*.py tests/test_facts_lakeformation.py tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py tests/test_docs_coverage.py` | 0 (977 passed) |
| — | `ruff check sparkforge scripts tests`; `python scripts/check_surface_lock.py`; `python scripts/check_status_numbers.py --strict` | 0 |
| claims_gate | `PYTHONIOENCODING=utf-8 python scripts/check_vnext_claims.py` | 0, depois de reler VNX-674 à mão (251707 → 251825, o docstring de `_fta_declarados` cresceu) |

Lição: o gate de golden de uma feature que acrescenta kind é o conjunto inteiro de goldens
que passa por `fuse`, não os módulos do domínio. `scan` roda `fuse` sobre `.tf` e não
aparece em `scripts/regen_fixtures.py`.
