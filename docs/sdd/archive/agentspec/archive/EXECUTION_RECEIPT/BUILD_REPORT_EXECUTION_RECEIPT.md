# BUILD REPORT: Execution Receipt

> Implementation report for EXECUTION_RECEIPT (§14 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | EXECUTION_RECEIPT |
| **Date** | 2026-09-12 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_EXECUTION_RECEIPT.md](./DEFINE_EXECUTION_RECEIPT.md) |
| **DESIGN** | [DESIGN_EXECUTION_RECEIPT.md](./DESIGN_EXECUTION_RECEIPT.md) |
| **Status** | ✅ Shipped |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 13/13 entradas do manifesto |
| **Files Created** | 12 (4 do modulo, 3 de teste, 3 de fixture, 1 doc, este relatorio) |
| **Lines of Code** | 614 no modulo (`__init__` 19, `_hash` 39, `build` 332, `verify` 224); +561 nos adapters (`_core` 259, `tools` 215, `cli` 87); 595 de teste |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto, como nos PRs #50 a #53: cada passo dependia de medida do anterior) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `sparkforge/receipt/__init__.py`, `_hash.py` | (direct) | ✅ Complete | `text_sha256` com CRLF normalizado; `receipt_id` sobre `findings.models._canonical` |
| 2 | `sparkforge/receipt/build.py` | (direct) | ✅ Complete | Partes case, evidence, judgment, decision, proof, tools, host, actions |
| 3 | `sparkforge/receipt/verify.py` | (direct) | ✅ Complete | Ordem fixa; caminho do recibo confinado ao repo (`outside_repo`) |
| 4 | `tests/test_receipt_build.py`, `tests/test_receipt_verify.py` | (direct) | ✅ Complete | 37 testes |
| 5 | `adapters/_core.py` | (direct) | ✅ Complete | `receipt_emit`, `receipt_write`, `receipt_emit_and_write`, `receipt_verify` |
| 6 | `adapters/cli.py` | (direct) | ✅ Complete | Grupo `receipt`, `dest="subcommand"` (sem mexer na cadeia de despacho) |
| 7 | `adapters/tools.py` | (direct) | ✅ Complete | 2 tools, 4 schemas, 2 handlers |
| 8 | `fixtures/receipt/uniao_debate/` + `tests/test_fixtures_golden_receipt.py` | (direct) | ✅ Complete | 9 testes; golden byte a byte |
| 9 | Registros de teste | (direct) | ✅ Complete | Lista literal, amostra real, formas de erro, escritoras, contagem 82 -> 84, `NOVAS_DEPOIS_DO_GOLDEN` |
| 10 | `parity.yaml`, `manifest.json`, `sf-synthesizer.md` + espelhos | (direct) | ✅ Complete | Passo 7 novo no executor |
| 11 | `docs/execution-receipt.md`, STATUS | (direct) | ✅ Complete | Tools 90; fixtures 403 em 46 dominios |
| 12 | Surface lock e claims | (direct) | ✅ Complete | +7 512 bytes; 26 claims remedidas por id |
| 13 | Este relatorio | (direct) | ✅ Complete | — |

---

## Verification Results

### Lint Check

```text
rtk ruff check .  ->  []
```

**Status:** ✅ Pass

### Type Check

N/A - o repositorio nao configura mypy.

**Status:** ⏭️ Skipped

### Tests

| Conjunto | Resultado |
|------|--------|
| `test_receipt_build` + `test_receipt_verify` | 37 passed |
| `test_fixtures_golden_receipt` | 9 passed |
| Registros (`test_adapters_tools`, `test_harness_authorization`, `test_capability_parity`, `test_agent_coverage`, `test_fixtures_golden_mcp_parity`, `test_facts_scan`, `test_codeintel_staleness`, `test_sync_render`) | 681 passed |
| `test_docs_coverage` | 27 passed |
| `test_suite_batches` | 4 passed |
| Lote a-c | 2282 passed, 2 skipped |
| Lote d-e | 348 passed |
| Lote f-sem-golden | 1870 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 | 570 passed |
| Lote goldens-3 | 346 passed |
| Lote goldens-4 (inclui o golden do recibo) | 209 passed |
| Lote goldens-5 | 388 passed |
| Lote g-z | 4923 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 284 passed, 0 failed, 9 skipped** |

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (26 remedidas pela lista de ids) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | 0 divergencias; `total_bytes` 476 607 -> 484 119 (+7 512) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| spec-lint (DEFINE, DESIGN) | PASS |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `def _com` aninhado no `verify` (a memoria registra que def aninhado quebra o codeintel) e duas chamadas esquecidas | Funcao de modulo `_parts_in` |
| 2 | Caminho dentro do recibo e dado nao confiavel: o verify leria `../../x` fora do repo | `_item_state` confina ao repo; o adapter so rele facts declarados dentro do repo |
| 3 | AT-014 (prova fora da uniao) esperava so `proof` | Tirar um fact da uniao muda `fact_ids_sha256`: `evidence` diverge junto, e e o certo. Teste ajustado com a razao |
| 4 | Varredura V2 sobre o golden: os `measures` da uniao sao so inteiros de 0 a 33 | A varredura passou a olhar texto de `measures`, `attrs` e `subject`, contra os VALORES do recibo (substring de chave dava falso positivo com `name` e `spark`) |
| 5 | Registro manual que a lista da memoria nao tinha: o conjunto de escritoras em `test_adapters_tools.py` | `sparkforge_receipt_emit` entrou com a razao escrita |
| 6 | Dominio novo exige a linha literal `FIXTURES = ROOT / "fixtures" / "receipt"` (`test_fixtures_kind_coverage`) | O golden trocou `RAIZ`/`CASO` pela forma que o regex reconhece |
| 7 | `scripts/sync_skills.py` apagou o `.claude/agents/README.md` nao rastreado (scaffolding do agentspec) | Nao ha volta pelo git; registrado para o operador |
| 8 | 26 claims de `docs/harness/` e `docs/vnext/` movidas (tools, caminho, `.py`, bytes) | Probe que roda as provas como o gate, e aplicacao por id com nota de remediacao |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Prefixo do kind de benchmark | `benchmark.*` (DESIGN) vs `bench.*` | `bench.*` | Medido: `benchmark_runs` emite `bench.*`; nenhum kind `benchmark.` existe |
| 2 | ADR declarado na decisao mas ausente no disco | Item `missing` no emit vs lacuna | `unresolved` `adr_ausente` | Item `missing` faria o recibo nascer invalido |
| 3 | Agente e versao do host | Campo proprio no transcript vs `source`/`host_versions` | `source` e `host_versions` | O fact `host.transcript` nao tem nome de agente; varias versoes viram `versoes_multiplas` |
| 4 | Caminho relativo na emissao | Relativo ao diretorio corrente vs ao `--repo` | Ao `--repo` | O recibo guarda caminho relativo ao repo e o verify resolve do mesmo jeito |
| 5 | Nome do parametro do transcript na tool | `host_transcript` vs `host_transcript_path` | `host_transcript_path` | Mesmo nome do `telemetry_export`; o sufixo faz a cadeia de autorizacao confina-lo |
| 6 | Saida da CLI no emit | Recibo inteiro vs resumo | Resumo (`receipt_path`, `receipt_id`, `unresolved`, `refused`) | O arquivo ja tem o corpo; a tool devolve o recibo inteiro |
| 7 | Fixture do golden | Blackboard estatico commitado vs montado no teste | Montado em `tmp_path` pelas portas do produto | `arbitrate` nao le hora; o golden prova o caminho real |
| 8 | Spans ausentes no verify | `None` vs lista vazia | Lista do ledger sempre que ha run declarado | `run_ausente` com `valid: true`; `None` fica para chamada direta do modulo |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `bench.*` em vez de `benchmark.*` | Medido no extrator | Nenhum; a Decision 6 previa conferir no B1 |
| `verify` devolve tambem `missing`, `not_rechecked` e `not_evaluable` como listas | Separar apagado de adulterado na propria resposta | Schema da tool com as quatro listas |
| O verify confina o caminho do recibo ao repo | Recibo e dado nao confiavel | `outside_repo` conta como `diverged` |
| A uniao tem 63 facts, nao 60 | Medido (20 + 43) | SC5 e STATUS com o numero medido |
| O golden nao tem ADR nem decisao | Medido: o `arbitrate` sobre a uniao grava claims, contradicao, evidencias, unknowns e trace, e nenhuma `Decision` | ADR e `rollback_present` provados so pelo case sintetico dos testes de unidade |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | `test_golden_byte_a_byte` |
| AT-002 | ✅ | `test_duas_emissoes_gravam_o_mesmo_arquivo`, `test_mesma_entrada_e_mesmo_now_dao_o_mesmo_recibo` |
| AT-003 | ✅ | `test_verify_limpo_sai_0` |
| AT-004 | ✅ | `test_verify_adulterado_sai_1_e_nomeia_a_parte`, parametrizado por parte |
| AT-005 | ✅ | `test_adulterar_um_artefato_acusa_so_a_parte_dele[judgment]` |
| AT-006 | ✅ | `test_artefato_apagado_e_missing` |
| AT-007 | ✅ | `test_recibo_editado_falha_na_integridade` |
| AT-008 | ✅ | `test_sem_traces_db_nao_reconfere_e_continua_valido`, `test_transcript_fora_do_repo_nao_e_reconferido` |
| AT-009 | ✅ | `test_span_alterado_diverge` |
| AT-010 | ✅ | `test_sem_host_sem_run_e_sem_report_as_lacunas_tem_nome` |
| AT-011 | ✅ | `test_sem_run_id_a_parte_tools_e_lacuna` |
| AT-012 | ✅ | `test_versao_diferente_nao_acusa_adulteracao` |
| AT-013 | ✅ | `test_crlf_no_disco_nao_diverge`, `test_crlf_e_lf_dao_o_mesmo_sha256` |
| AT-014 | ✅ | `test_prova_citando_fact_fora_da_uniao_diverge` (com `evidence` junto; ver Issues 3) |
| AT-015 | ✅ | `test_facts_fora_do_repo_e_recusado_e_nada_e_gravado` |
| AT-016 | ✅ | `test_recibo_ilegivel_sai_2` |

**Nao provado aqui:** a verificacao cruzada Windows -> Linux (SC7) depende do CI do PR; o registro `rollback` de uma `Decision` real (a uniao nao gera decisao).

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 284 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Shipped:** ver [SHIPPED_2026-09-12.md](./SHIPPED_2026-09-12.md)
