# BUILD REPORT: Realized Gain Ledger

> Implementation report for REALIZED_GAIN (§21 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | REALIZED_GAIN |
| **Date** | 2026-09-13 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_REALIZED_GAIN.md](../features/DEFINE_REALIZED_GAIN.md) |
| **DESIGN** | [DESIGN_REALIZED_GAIN.md](../features/DESIGN_REALIZED_GAIN.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 8/8 entradas do manifesto |
| **Files Created** | 1 do modulo, 2 de teste, 1 doc, 4 casos de fixture (59 arquivos de facts recortados, 4 `meta.yaml`, 4 goldens), este relatorio |
| **Lines of Code** | `finops/realized.py` ~180; `_core` +~25, `tools.py` +~110, `cli.py` +~25 |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `sparkforge/finops/realized.py` | (direct) | ✅ Complete | `realized_gain`, `GainError`; reusa `_volume_de` e `_TOLERANCIA_PADRAO` do `capacity` |
| 2 | `tests/test_finops_realized.py` | (direct) | ✅ Complete | 13 testes: cada marca, descarte, erros, custo por `job_run_id`, moedas, tolerancia declarada, recusas |
| 3 | `_core.gain` | (direct) | ✅ Complete | Um conjunto por arquivo; lado sem arquivo ou `GainError` saem com codigo 2 |
| 4 | CLI e tool | (direct) | ✅ Complete | `sparkforge gain --baseline ... --candidate ...`; `sparkforge_gain` READ_ONLY com `baseline_paths`/`candidate_paths` |
| 5 | `fixtures/gain/` + golden | (direct) | ✅ Complete | 4 casos recortados de `capacity/cheapest_that_fits`, `capacity/volume_filter_changes_the_answer` e `finops/cheap_but_misses_sla` |
| 6 | Registros | (direct) | ✅ Complete | Lista, amostra real, FAILABLE, contagem com caminho 86 -> 87, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity, `sf-verifier` (checagem 9) + espelhos |
| 7 | Doc, STATUS, contagens, surface, claims | (direct) | ✅ Complete | `docs/realized-gain.md`; tools 95; fixtures 441 em 51 dominios; +5 425 bytes; 21 claims por id |
| 8 | Este relatorio | (direct) | ✅ Complete | — |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge tests scripts  ->  All checks passed!
```

**Status:** ✅ Pass

### Type Check

N/A - o repositorio nao configura mypy.

**Status:** ⏭️ Skipped

### Tests

| Conjunto | Resultado |
|------|--------|
| Ledger + registros (`test_finops_realized`, golden do gain, `test_adapters_tools`, `test_harness_authorization`, paridade MCP, `test_agents_parity`) | 535 passed |
| Lote a-c | 2293 passed, 2 skipped |
| Lote d-e | 348 passed |
| Lote f-sem-golden | 1886 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 (inclui o golden do gain) | 579 passed |
| Lote goldens-3 | 358 passed |
| Lote goldens-4 | 254 passed |
| Lote goldens-5 | 410 passed |
| Lote g-z | 5054 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 530 passed, 0 failed, 9 skipped** (1a passada) |

Depois da suite, o teste de tolerancia declarada foi alinhado ao AT-010 (0,5 e volume 40% maior) e rerodado sozinho: 13 passed.

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (21 remedidas pela lista de ids) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | `total_bytes` 497 576 -> 503 001 (+5 425) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Duas linhas acima de 100 colunas e um import fora de ordem | `ruff --fix` e quebra manual |
| 2 | 21 claims movidas: tools 94 -> 95, READ_ONLY 62 -> 63, com caminho 86 -> 87, contagem 54 -> 55 da cadeia de autorizacao, modulos golden 49 -> 50, dominios 50 -> 51, e as medidas do corpus de `.py` no CODEINTEL-GAP e no CURRENT-HARNESS-GAP (VNX-741 793.4 -> 795.8, VNX-431 404,2 -> 408,3, VNX-322 314,4 -> 315,5, e quatro contagens de linha e byte) | Probe e aplicacao por id, nota de remedicao em cada entrada |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Capacidade diferente entre os lados | Marca vs informacao | Informacao (`capacities` por lado) | Mudar capacidade e uma das mudancas que o ledger mede |
| 2 | Volume de arquivo com varios runs | Atribuir o scan a todos vs desconhecido | Desconhecido | Com varios runs nao ha como ligar o scan ao run |
| 3 | Custo parcial | Mediana sobre os runs com custo, sem marca vs com marca | Mediana sobre os que tem, marcada `custo_indisponivel` | O numero sai, e a marca diz que ele nao cobre todos os runs |
| 4 | Caso de custo | Inventar `glue.run_cost` vs recortar | Recortar `finops/cheap_but_misses_sla` (runs do `input`, custos do `expected`) | Fixture sintetica que ja existe, nada inventado |

---

## Deviations from Design

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | golden `ganho_por_capacidade` (-44,4% no tempo, +11,1% em DPU-s); `test_delta_das_medianas_sem_marca` |
| AT-002 | ✅ | golden `amostra_insuficiente`; `test_amostra_insuficiente` |
| AT-003 | ✅ | `test_jobs_diferentes_sao_erro`; `test_jobs_diferentes_saem_2` (CLI) |
| AT-004 | ✅ | `test_run_que_falhou_e_descartado_e_contado` |
| AT-005 | ✅ | golden `volume_diverge`; `test_volume_diverge` |
| AT-006 | ✅ | golden `custo_por_run`; `test_arquivo_com_varios_runs_tem_volume_desconhecido` |
| AT-007 | ✅ | golden `custo_por_run`; `test_custo_pelo_job_run_id` |
| AT-008 | ✅ | `test_run_sem_custo_marca_so_o_custo`, `test_moedas_diferentes_marcam_custo` |
| AT-009 | ✅ | `test_recusas_sempre` e os quatro goldens |
| AT-010 | ✅ | `test_tolerancia_declarada_no_workload` (0,5 declarado, volume 40% maior) |
| AT-011 | ✅ | `test_lado_sem_run_valido_e_erro` |

**Nao provado aqui:** ganho sobre runs reais de producao -- os fixtures sao recortes sinteticos (repositorio publico).

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 530 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_REALIZED_GAIN.md`
