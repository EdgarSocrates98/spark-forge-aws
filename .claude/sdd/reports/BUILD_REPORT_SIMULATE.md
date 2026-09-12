# BUILD REPORT: Simulate

> Implementation report for SIMULATE (§19 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMULATE |
| **Date** | 2026-09-12 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_SIMULATE.md](../features/DEFINE_SIMULATE.md) |
| **DESIGN** | [DESIGN_SIMULATE.md](../features/DESIGN_SIMULATE.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 9/9 entradas do manifesto (B1–B6) |
| **Files Created** | 10 de codigo e teste (4 do modulo, 4 de teste, 1 doc, este relatorio) mais 9 `meta.yaml` e 6 goldens em `fixtures/simulate/` |
| **Lines of Code** | 234 no modulo (`__init__` 30, `layers` 15, `patch` 112, `diff` 77); +29 em `facts/` (`fusion` 19, `timeout_diagnosis` 10); +231 nos adapters (`_core` 73, `tools` 117, `cli` 41); 289 de teste novo |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto: cada passo dependia de medida do anterior, como nos PRs #54 e #56) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Passo 0: `fuse()` chama `extract_timeout_diagnosis` + `tests/test_fusion_timeout.py` | (direct) | ✅ Complete | Guardado por `timeout_diagnosis.SOURCE_KINDS` (ver Deviations); assercao de namespace sobre `EMITTED_KINDS` |
| 2 | `sparkforge/simulate/{__init__,layers,patch,diff}.py` | (direct) | ✅ Complete | `SimulateError.reason` nomeia cada recusa |
| 3 | `tests/test_simulate_patch.py`, `tests/test_simulate_diff.py` | (direct) | ✅ Complete | 22 testes |
| 4 | `_core.simulate_change` | (direct) | ✅ Complete | `_simulate_lado` de modulo (def aninhado quebra o codeintel) |
| 5 | `cli.py` e `tools.py` | (direct) | ✅ Complete | `simulate --facts --set`; `sparkforge_simulate` `_READ_ONLY`, schema proprio |
| 6 | `fixtures/simulate/` + `tests/test_fixtures_golden_simulate.py` | (direct) | ✅ Complete | 6 simulacoes e 3 recusas; 22 testes; `SPARKFORGE_REGEN_SIMULATE` |
| 7 | Registros | (direct) | ✅ Complete | Lista literal, amostra real, forma de erro, contagem 85 -> 86, `NOVAS_DEPOIS_DO_GOLDEN`, `manifest.json`, `parity.yaml`, `spark-performance-architect.md` + espelhos |
| 8 | `docs/simulate.md`, STATUS, contagens, surface lock, claims | (direct) | ✅ Complete | Tools 92; fixtures 422 em 48 dominios; +3 620 bytes; 26 claims remedidas por id |
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
| `test_simulate_patch` + `test_simulate_diff` | 22 passed |
| `test_fusion_timeout` + goldens de fusion e timeout + testes de `timeout_diagnosis` e `fusion` | 141 passed (antes do modulo) |
| `test_fixtures_golden_simulate` | 22 passed |
| `test_adapters_tools` + `test_harness_authorization` | 400 passed |
| Lote a-c | 2288 passed, 2 skipped |
| Lote d-e | 348 passed |
| Lote f-sem-golden | 1873 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 | 570 passed |
| Lote goldens-3 | 346 passed |
| Lote goldens-4 | 249 passed |
| Lote goldens-5 (inclui o golden do simulate) | 410 passed |
| Lote g-z | 4991 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 423 passed, 0 failed, 9 skipped** |

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (26 remedidas pela lista de ids) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | 0 divergencias; `total_bytes` 487 816 -> 491 436 (+3 620) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Ligar `extract_timeout_diagnosis` no `fuse()` sem guarda daria `spark.timeout.diagnosis` com `no_timeout_evidence` a TODO pool nao vazio: os 7 goldens de fusion mudariam sem nenhum event log | `SOURCE_KINDS` com os quatro kinds que o extrator le; `test_source_kinds_cobre_o_que_o_extrator_le` trava o conjunto contra o proprio extrator |
| 2 | `scripts/sync_skills.py` apagou de novo o `.claude/agents/README.md` nao rastreado (o agentspec o recria entre frentes) | Sem volta pelo git; memoria atualizada para copiar o arquivo antes do sync |
| 3 | 26 claims de `docs/harness/` e `docs/vnext/` movidas (tools, caminho, `.py`, bytes, e a taxa de receptor desconhecido do ADR-010, 90,9 -> 90,8) | Probe que roda as provas como o gate, e aplicacao por id com nota de remediacao |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde mora o motivo da recusa | Codigo de saida diferente por motivo vs texto | Codigo 2 sempre, motivo entre colchetes na mensagem | Toda recusa de entrada do pacote e codigo 2; o golden casa `[motivo]` no stderr |
| 2 | Recusas alem das tres do DEFINE | So as tres vs `set_malformado` e `sem_set` tambem | As cinco | `--set tf:x` e `--set tf:=1` passariam como chave vazia; `sem_set` protege a tool, que nao tem `required` do argparse |
| 3 | Chave de comparacao sem `stable_keys` declarada | Recusar vs subject inteiro | Subject inteiro | No simulate os dois lados tem o mesmo subject: o `--set` nunca o toca |
| 4 | Golden das recusas | `expected/result.json` com o erro vs so a assercao | So a assercao (codigo 2, stdout vazio, motivo) | A mensagem traz o caminho do fixture, que muda entre maquinas |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| O passo 0 roda `extract_timeout_diagnosis` so quando o pool tem kind de origem (`SOURCE_KINDS`) | A Decision 1 chamava o extrator sempre, e ele emite `no_timeout_evidence` para qualquer pool nao vazio | Goldens de fusion inalterados; `fuse()` sem event log continua igual |
| Duas recusas a mais (`set_malformado`, `sem_set`) | Ver Autonomous Decisions 2 | Documentadas em `docs/simulate.md` |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | `fixtures/simulate/concorrencia_um_some_glue003`; `test_valor_numerico_atualiza_texto_e_medida` |
| AT-002 | ✅ | `fixtures/simulate/workers_abaixo_do_minimo_fgac` (SF-LF-006 aparece) |
| AT-003 | ✅ | `fixtures/simulate/versao_muda_so_o_runtime` (runtime 5.0 -> 3.0, 10 regras em `skipped_delta`) |
| AT-004 | ✅ | `fixtures/simulate/fgac_desligado_some_lf001` (SF-LF-001 some pela rederivacao) |
| AT-005 | ✅ | `fixtures/simulate/timeout_rederivado_aparece` (SF-TIMEOUT-002 aparece) |
| AT-006 | ✅ | `fixtures/simulate/mesmo_valor_diff_vazia` |
| AT-007 | ✅ | `fixtures/simulate/recusa_chave_ausente` |
| AT-008 | ✅ | `fixtures/simulate/recusa_sem_camada` (`camada_invalida`) |
| AT-009 | ✅ | `fixtures/simulate/recusa_texto_para_medida` |

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 423 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Ready for:** `/agentspec:workflow:ship .claude/sdd/features/DEFINE_SIMULATE.md`
