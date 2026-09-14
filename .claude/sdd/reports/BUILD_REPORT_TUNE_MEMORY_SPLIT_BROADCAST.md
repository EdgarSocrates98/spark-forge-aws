# BUILD REPORT: Tune com memória, split e broadcast (frente 2a)

> Implementation report for `tune`: `memoryOverhead`, `executor.memory`, `maxPartitionBytes` e `autoBroadcastJoinThreshold`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_MEMORY_SPLIT_BROADCAST |
| **Date** | 2026-09-14 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md](../features/DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md) |
| **DESIGN** | [DESIGN_TUNE_MEMORY_SPLIT_BROADCAST.md](../features/DESIGN_TUNE_MEMORY_SPLIT_BROADCAST.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 8/8 (entradas do manifesto) |
| **Files Created** | 10 casos golden (1 de plano, 1 de SQL metrics, 7 de tuning, 1 de change) |
| **Lines of Code** | extensões em `tuning/spark_conf.py`, `facts/{spark_plan,sql_metrics,parquet_footer}.py`, `adapters/{_core,cli,tools}.py` (nenhum módulo novo) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12 772 passed, 13 skipped, 0 failed (suíte em 9 lotes) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `knowledge/spark/sql-metrics.{yaml,md}`: rótulos do `BroadcastExchangeExec` | (direct) | ✅ Complete | - | Conferidos nas tags v3.1.1, v3.3.0, v3.5.4 e v4.1.1 |
| 2 | `facts/parquet_footer.py`: `attrs.total_compressed_bytes` | (direct) | ✅ Complete | - | Em `attrs`, fora do `Fact.id` |
| 3 | `facts/spark_plan.py` e `facts/sql_metrics.py`: `plan.join_side_stats` e `spark.sql.broadcast_exchange` | (direct) | ✅ Complete | - | |
| 4 | `tuning/spark_conf.py`: quatro derivações, recusas e `headroom` | (direct) | ✅ Complete | - | |
| 5 | `adapters/{_core,cli,tools}.py`: `--headroom` e schema da tool | (direct) | ✅ Complete | - | |
| 6 | Fixtures novos e goldens regravados | (direct) | ✅ Complete | - | |
| 7 | Docs, STATUS, agente, manual, knowledge | (direct) | ✅ Complete | - | |
| 8 | Testes de unidade e golden | (direct) | ✅ Complete | - | |

**Agent Key:** `(direct)` = construído direto, pelas mesmas razões das frentes anteriores (registros literais e armadilhas do repositório).

---

## Files Created

| File | Agent | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `fixtures/plan/explain_cost_join/` | (direct) | ✅ | Seção lógica do `EXPLAIN COST` com um join |
| `fixtures/sql_metrics/broadcast_exchange/` | (direct) | ✅ | Métricas do `BroadcastExchange` via `SparkListenerDriverAccumUpdates` |
| `fixtures/tuning/{overhead_medido,overhead_sem_process_tree,split_uma_fonte,split_duas_fontes,broadcast_um_join,broadcast_dois_joins,broadcast_sem_estatistica}/` | (direct) | ✅ | Um cenário por proposta e por recusa |
| `fixtures/change/do_tune_overhead/` | (direct) | ✅ | AT-012: `change plan --from-tune` leva o overhead para o `--conf` |

---

## Verification Results

### Lint Check

```text
ruff check (arquivos alterados)
All checks passed!
```

**Status:** ✅ Pass

### Type Check

```text
N/A - mypy nao configurado no repositorio
```

**Status:** ⏭️ Skipped

### Tests

```text
a-c          2371 passed, 2 skipped
d-e           364 passed
f-sem-golden 1893 passed, 2 skipped
goldens-1    1368 passed, 4 skipped
goldens-2     579 passed
goldens-3     358 passed
goldens-4     272 passed
goldens-5     442 passed
g-z          5125 passed, 5 skipped
total       12772 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergências (12 remedidas por lista de ids, em duas rodadas) |
| `check_status_numbers.py --strict` | ✅ 0 divergências (kinds 222 → 224, fixtures 472 → 482, fontes 247 → 248) |
| `check_surface_lock.py --update` | ✅ tools 526 807 → 527 656 (+849); knowledge 489 892 → 490 852 (+960) |
| `gen_reference_docs.py` | ✅ 255 páginas, 2 regravadas |
| `refresh_knowledge.py --offline --update` | ✅ `BroadcastExchangeExec.scala` no lock (móvel) |
| spec-lint (define, design) | ✅ PASS |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `measures_by_node` descartava acumulador de nó fora de `nodes`, e o `BroadcastExchange` não é scan nem join | `broadcasts` próprio no estado da execução | pequeno |
| 2 | Os 7 goldens de tuning e o `change/do_tune` mudaram só nos nomes de `refused` | Regravados e conferidos no diff | pequeno |
| 3 | O gate de lastro divergiu duas vezes: a primeira pelo crescimento de `tools.py`/`_core.py`, a segunda pelos testes novos e pela fonte nova | Remedido por lista de ids | pequeno |
| 4 | Arquivo solto de 0 byte na raiz (`(node_id`), fora do git | Inspecionado (vazio) e apagado | nenhum |
| 5 | `sync_skills.py` desfez a edição feita no espelho `.claude/agents/` | Edição refeita na fonte `agents/spark-performance-architect.md` e espelhos ressincronizados | pequeno |
| 6 | Paridade MCP: descrição, `explanation` e enum de recusa do `sparkforge_tune` diferem do golden congelado do SDK 1.29 | `sparkforge_tune` em `ALTERADAS_DEPOIS_DO_GOLDEN` (o `headroom` é aditivo) e `REESCRITAS_DEPOIS_DO_GOLDEN` novo, com motivo por caminho; enum só aceito crescendo com os valores antigos na frente, e contagem medida de 3 por transporte | pequeno |
| 7 | `.sparkforge/traces.db` criado por um script de diagnóstico da paridade rodado fora do isolamento de teste, e cobrado pela guarda do `conftest` | Inspecionado (ledger ignorado pelo git, criado às 12:22 pelo script) e apagado; lotes a-c e goldens-3 rodados de novo | pequeno |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde mora o tamanho comprimido do row group | `measures` ou `attrs` | `attrs` | `Fact.id` é hash de kind, subject e measures; em `measures` todo id dos goldens de footer mudaria |
| 2 | Lado sem estatística num join com o outro lado estimado | Recusar o join ou usar o lado com estatística | Usar o lado com estatística | O lado sem estatística carrega 8.0 EiB e nunca seria o menor; a recusa fica para quando nenhum lado tem |
| 3 | `effective_default_mib` sem `spark.executor.memory` pedido | Supor o default do worker ou omitir | Omitir | Supor a memória do worker seria número sem medida |
| 4 | Caso AT-012 | Reaproveitar `do_tune` ou caso novo | Caso novo, sem heap no event log | Mantém o diff com uma chave só; `executor.memory` sai recusado por `sem_pico_de_heap` |

---

## Deviations from Design

Nenhum.

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Overhead medido | ✅ Pass | golden `overhead_medido`; `test_the_overhead_is_the_worst_executor_outside_the_heap` |
| AT-002 | Sem ProcessTree | ✅ Pass | golden `overhead_sem_process_tree`; `test_without_process_tree_the_overhead_is_refused_by_name` |
| AT-003 | Folga | ✅ Pass | `test_headroom_multiplies_the_floor_and_travels_in_the_basis`; `test_a_negative_headroom_is_an_input_error` |
| AT-004 | Heap | ✅ Pass | golden `overhead_medido` (3072 MiB) |
| AT-005 | Split | ✅ Pass | golden `split_uma_fonte` (112 MiB) |
| AT-006 | Duas fontes | ✅ Pass | golden `split_duas_fontes` |
| AT-007 | Sem footer | ✅ Pass | toda recusa `sem_footer` dos goldens de tuning |
| AT-008 | Um join | ✅ Pass | goldens `plan/explain_cost_join` e `tuning/broadcast_um_join` |
| AT-009 | Dois joins | ✅ Pass | golden `broadcast_dois_joins` |
| AT-010 | Sem estatística | ✅ Pass | golden `broadcast_sem_estatistica` |
| AT-011 | Medido ao lado | ✅ Pass | goldens `sql_metrics/broadcast_exchange` e `tuning/broadcast_um_join` (`measured_broadcasts`) |
| AT-012 | Change plan | ✅ Pass | golden `change/do_tune_overhead` (512 → 1152) |

---

## Final Status

### Overall: ✅ COMPLETE

**Completion Checklist:**

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md`
