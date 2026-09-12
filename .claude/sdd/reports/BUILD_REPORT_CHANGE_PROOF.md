# BUILD REPORT: Change Proof

> Implementation report for CHANGE_PROOF (§20 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHANGE_PROOF |
| **Date** | 2026-09-12 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_CHANGE_PROOF.md](../features/DEFINE_CHANGE_PROOF.md) |
| **DESIGN** | [DESIGN_CHANGE_PROOF.md](../features/DESIGN_CHANGE_PROOF.md) |
| **Status** | Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 13/13 entradas do manifesto |
| **Files Created** | 21 (6 do modulo, a politica, 3 de teste, 10 casos de fixture com 2 `job.py`, 1 doc) |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto, como nas frentes anteriores) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `rules/catalog/proof_axes.yaml` | (direct) | ✅ Complete | 23 eixos, chave estavel por tipo, convencao do sinal com a razao |
| 2 | `sparkforge/proof/{__init__,axes,keys}.py` | (direct) | ✅ Complete | Carga por `safe_catalog_file`, validacao com o campo nomeado |
| 3 | `sparkforge/proof/{resolution,axis,prove}.py` | (direct) | ✅ Complete | Desfechos na ordem do DESIGN |
| 4 | `tests/test_proof_policy.py` | (direct) | ✅ Complete | A politica contra o catalogo real |
| 5 | `tests/test_proof_outcomes.py` | (direct) | ✅ Complete | Cada ramo |
| 6 | `adapters/_core.py` | (direct) | ✅ Complete | `proof_change`: dois `judge` |
| 7 | `adapters/cli.py`, `adapters/tools.py` | (direct) | ✅ Complete | Verbo `proof`, tool `sparkforge_proof` READ_ONLY |
| 8 | `fixtures/proof/` + `tests/test_fixtures_golden_proof.py` | (direct) | ✅ Complete | 10 casos, 40 testes |
| 9 | Registros de teste | (direct) | ✅ Complete | Lista literal, amostra real, formas de erro, contagem 84 -> 85, `NOVAS_DEPOIS_DO_GOLDEN`, `NAO_SAO_AREA` |
| 10 | `parity.yaml`, `manifest.json`, `sf-verifier.md` + espelhos | (direct) | ✅ Complete | Checagem 7 |
| 11 | `docs/change-proof.md`, STATUS | (direct) | ✅ Complete | Tools 91; fixtures 413 em 47 dominios |
| 12 | Surface lock e claims | (direct) | ✅ Complete | +3 697 bytes; 23 claims remedidas por id |
| 13 | Este relatorio | (direct) | ✅ Complete | — |

---

## Verification Results

### Lint Check

```text
rtk ruff check .  ->  []
```

**Status:** ✅ Pass

### Tests

| Conjunto | Resultado |
|------|--------|
| `test_proof_policy` + `test_proof_outcomes` | 47 passed |
| `test_fixtures_golden_proof` | 40 passed |
| Registros (`test_adapters_tools`, `test_harness_authorization`, `test_capability_parity`, `test_agent_coverage`, `test_fixtures_golden_mcp_parity`, `test_facts_scan`, `test_codeintel_staleness`, `test_sync_render`, `test_fixtures_kind_coverage`, `test_suite_batches`) | 735 passed |
| `test_docs_coverage` | 27 passed |
| Lote a-c | 2285 passed, 2 skipped |
| Lote d-e | 348 passed |
| Lote f-sem-golden | 1870 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 | 570 passed |
| Lote goldens-3 | 346 passed |
| Lote goldens-4 (inclui os 40 do golden da prova) | 249 passed |
| Lote goldens-5 | 388 passed |
| Lote g-z | 4971 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 375 passed, 0 failed, 9 skipped** |

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (23 remedidas pela lista de ids) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | 0; `total_bytes` 484 119 -> 487 816 (+3 697) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| spec-lint (DEFINE, DESIGN) | PASS |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | **A resolucao dava `unproven` para a correcao bem-sucedida.** `SF-PY-002` declara `requires_facts: [pyspark.driver_collect]`, justamente o kind que a correcao elimina; o motor pula a regra por `requires_facts` | Medido sobre o `collect_unbounded` corrigido. A resolucao separa os dois casos pelo extrator: se o modulo que emite o kind ausente produziu algum fact no depois (aqui `pyspark.module_analyzed`), a ausencia e evidencia -> `not_refuted` (`padrao_ausente_com_extrator_rodado`); senao, `unproven`. A Decision 4 do DESIGN (passo 2) estava errada |
| 2 | `proof_axes.yaml` em `rules/catalog/` entraria na contagem de areas de regra | `NAO_SAO_AREA` de `tests/test_rules_loader.py` ganhou o quarto arquivo de vocabulario |
| 3 | O script de claims trocou `§45` por `§46` numa linha que cita secao, e deixou o numero real intacto | Linha corrigida a mao; o lookbehind passou a excluir `§` e letras; armadilha na memoria |
| 4 | Construcao torta num teste golden (`mkdir() is None`) | Parametrizado por caso |
| 5 | Exit 255 no smoke da CLI | Era o `Select-Object -First` cortando o pipe; com a saida em arquivo, exit 0 |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Correcao bem-sucedida caindo em `requires_facts` | `unproven` (DESIGN) vs distinguir pelo extrator | Distinguir pelo modulo emissor, via `_modulo_por_kind` | Sem isso a prova diria "falta artefato" exatamente quando a correcao funcionou |
| 2 | Ordem entre `SF-FVAL-005` (parcial) e `SF-FVAL-001..004` | Parcial primeiro vs divergencia primeiro | Divergencia refuta mesmo com validacao parcial | Uma divergencia medida e real, mesmo que o plano nao tenha sido todo medido |
| 3 | `bench.unresolved` com `measure: ""` | Todo furo de run invalida vs so `missing_log_analyzed` | So `missing_log_analyzed` | `missing_runtime_label` e `same_runtime_label` falam do rotulo, nao do delta |
| 4 | Evidencia do `not_refuted` normal | Todos os facts do depois vs os dos kinds que a regra le | Os dos kinds do `when` da regra | Evidencia ligada ao que a regra olharia |
| 5 | Casos do golden | Facts estaticos vs codigo extraido | Os dois: o depois de resolucao como `job.py` extraido pela porta do produto; os de eixo reusando facts de fixtures existentes | O depois corrigido precisa sair do extrator real para provar o Issue 1 |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Resolucao com `requires_facts` distingue extrator rodado de artefato faltando | Issue 1, medido | Novo ramo `not_refuted` (`padrao_ausente_com_extrator_rodado`) e dois testes |
| `after_ids_by_module` como parametro da resolucao | Necessario para o ramo acima | `prove.py` agrupa os ids do depois por modulo |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | `fixtures/proof/resolucao_corrigida` (via extrator rodado) |
| AT-002 | ✅ | `resolucao_ainda_dispara` |
| AT-003 | ✅ | `resolucao_sem_artefato` |
| AT-004 | ✅ | `correcao_refutada` |
| AT-005 | ✅ | `correcao_parcial` |
| AT-006 | ✅ | `resolucao_corrigida` (correcao `unproven` sem funcval) e unidade |
| AT-007 | ✅ | `melhoria_nao_refutada` |
| AT-008 | ✅ | `melhoria_refutada` |
| AT-009 | ✅ | `melhoria_volume_diferente` |
| AT-010 | ✅ | `ganho_com_spill` (tempo -24,5% not_refuted com proxy; spill +3100% refuted) |
| AT-011 | ✅ | `atribuicao_compartilhada` |
| AT-012 | ✅ | `test_eixo_sem_comparador_e_unproven_com_unlock` |
| AT-013 | ✅ | `test_applied_inexistente_vira_lacuna` |
| AT-014 | ✅ | forma de erro em `test_adapters_tools` |

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 375 passed, 0 failed, 9 skipped, nos nove lotes)
- [x] No blocking issues
- [x] Acceptance tests verified

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_CHANGE_PROOF.md`
