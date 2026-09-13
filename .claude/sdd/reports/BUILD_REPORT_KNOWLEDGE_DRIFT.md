# BUILD REPORT: Knowledge Drift Radar

> Implementation report for KNOWLEDGE_DRIFT (§17 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_DRIFT |
| **Date** | 2026-09-13 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_KNOWLEDGE_DRIFT.md](../features/DEFINE_KNOWLEDGE_DRIFT.md) |
| **DESIGN** | [DESIGN_KNOWLEDGE_DRIFT.md](../features/DESIGN_KNOWLEDGE_DRIFT.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 9/9 entradas do manifesto |
| **Files Created** | 1 do modulo, 2 de teste, 10 de fixture (5 locks sinteticos e 5 `meta.yaml`), 5 goldens, este relatorio |
| **Lines of Code** | `knowledge_drift.py` ~270; `_core` +~30, `tools.py` +~95, `cli.py` +~20, `refresh_knowledge.py` +~25 |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `sparkforge/knowledge_drift.py` | (direct) | ✅ Complete | `RepoIndex`, `build_index` (por `iter_source_files`), `drift` pura, `render_markdown` |
| 2 | `tests/test_knowledge_drift.py` | (direct) | ✅ Complete | 17 testes, inclusive ida e volta do indice contra os `expected/findings.json` reais |
| 3 | `_core.knowledge_drift` | (direct) | ✅ Complete | Monta lock, catalogo, `por_doc` e indice; `--url` fora do lock sai 2 |
| 4 | CLI e tool | (direct) | ✅ Complete | `knowledge drift`; `sparkforge_knowledge_drift` READ_ONLY sem caminho |
| 5 | `scripts/refresh_knowledge.py` | (direct) | ✅ Complete | `impacto()` + `render_report(..., impacto)` |
| 6 | `fixtures/knowledge_drift/` + golden | (direct) | ✅ Complete | 5 casos pela CLI com `SPARKFORGE_SOURCES_LOCK` |
| 7 | Registros | (direct) | ✅ Complete | Lista, amostra real, `SEM_CAMINHO`, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, `sf-verifier` (checagem 8) + espelhos |
| 8 | Doc, STATUS, contagens, surface, claims | (direct) | ✅ Complete | Tools 94; fixtures 437 em 50 dominios; +3 528 bytes; 30 claims por id |
| 9 | Este relatorio | (direct) | ✅ Complete | — |

---

## Verification Results

### Lint Check

```text
ruff check .  ->  All checks passed!
```

**Status:** ✅ Pass

### Type Check

N/A - o repositorio nao configura mypy.

**Status:** ⏭️ Skipped

### Tests

| Conjunto | Resultado |
|------|--------|
| Radar + registros (`test_knowledge_drift`, golden do radar, `test_refresh_knowledge`, `test_adapters_tools`, `test_harness_authorization`, paridade MCP, `test_capability_parity`, `test_agent_coverage`, `test_facts_scan`, `test_agents_parity`, `test_adapters_knowledge`) | 739 passed |
| Lote a-c (2a passada) | 2290 passed, 2 skipped |
| Lote d-e (2a passada) | 348 passed |
| Lote f-sem-golden (2a passada) | 1873 passed, 2 skipped |
| Lote goldens-1 (1a passada) | 1348 passed |
| Lote goldens-2 (1a passada) | 570 passed |
| Lote goldens-3 (2a passada, inclui o golden do radar) | 358 passed |
| Lote goldens-4 (1a passada) | 254 passed |
| Lote goldens-5 (1a passada) | 410 passed |
| Lote g-z (2a passada) | 5053 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 504 passed, 0 failed, 9 skipped** |

A 1a passada teve 1 falha (Issue 4), corrigida; a 2a refez os lotes que a correcao tocou.

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (30 remedidas pela lista de ids, em duas passadas) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | 0 divergencias; `total_bytes` 494 048 -> 497 576 (+3 528) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| spec-lint (DEFINE, DESIGN) | PASS |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | O schema da tool usava `_RECEIPT_GAP_ITEM` antes de ele ser definido no modulo: o `tools.py` quebraria no import, e nenhum teste rodado ate ali o importava | O ruff pegou (`F821`); o schema ganhou `_DRIFT_LACUNA` proprio |
| 2 | O AT-009 do DEFINE pedia o relatorio do `--offline`, que sai antes de gerar relatorio | Revisto no design: o teste chama `render_report` com o impacto |
| 4 | A suite pegou `test_adapters_code_surface::test_inv_009_nenhum_argumento_aceita_url`: o parametro `url` da tool viola o INV-009 (tool nenhuma aceita argumento com `url` no nome, porque nada acessa rede) | Renomeado para `source` na tool e na CLI (`--source`); o valor e so a chave do lock, comparada por igualdade. DEFINE e DESIGN citam `--url`: desvio registrado |
| 3 | 24 claims movidas (tools, READ_ONLY, sem caminho 7 -> 8, `.py`, bytes, receptor 90,7 -> 90,6, razao contra `grep` 10.7 -> 10.9) | Probe e aplicacao por id |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Impacto de salto sem repositorio | Lista vazia vs `null` | `null` + `unresolved` | Lista vazia pareceria "nada afetado" |
| 2 | Evals: quais arquivos | So `suite.yaml` vs todo texto de `evals/` | Todo texto (`.yaml`, `.yml`, `.json`, `.xml`, `.md`, `.txt`) | O gabarito do holdout e do debate tambem cita `rule_id` |
| 3 | Goldens: como ligar a regra | Regex no texto vs JSON | JSON do `expected/findings.json`, campo `rule_id` | O texto cita outras regras em `depends_on` e explicacao |
| 4 | Lock passado pelo refresh | Lock inteiro vs so as URLs mudadas | So as mudadas | O relatorio so fala delas; o estado so precisa da entrada da URL |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Filtro `--source`/`source` em vez de `--url`/`url` | INV-009 (Issue 4) | AT-004 roda com `--source` |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | golden `nada_mudou` |
| AT-002 | ✅ | golden `lf_consideracoes`; `test_lf_so_as_lidas_antes_da_mudanca_entram` |
| AT-003 | ✅ | `test_lida_depois_e_revalidada_e_fica_fora_do_impacto`, `test_lida_no_dia_da_mudanca_ja_e_revalidada` |
| AT-004 | ✅ | golden `filtro_por_url`; `test_url_fora_do_lock_sai_2` |
| AT-005 | ✅ | golden `fixa_por_versao`; `test_fonte_fixa_por_versao_nunca_entra` |
| AT-006 | ✅ | golden `so_documento`; `test_documento_e_citacao_e_entra_no_impacto` |
| AT-007 | ✅ | `test_sem_repositorio` (CLI) e `test_sem_repositorio_os_tres_saltos_sao_unresolved` |
| AT-008 | ✅ | `test_lock_ausente_e_unresolved`, `test_lock_ausente_nao_derruba` |
| AT-009 | ✅ | `test_relatorio_do_refresh_traz_a_mesma_secao` |
| AT-010 | ✅ | `test_recusa_sempre_presente` |

**Nao provado aqui:** o relatorio do PR semanal com impacto real -- depende de o refresh voltar a abrir PR (configuracao do operador).

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 504 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Ready for:** `/agentspec:workflow:ship .claude/sdd/features/DEFINE_KNOWLEDGE_DRIFT.md`
