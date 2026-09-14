# BUILD REPORT: Tune com timeouts e speculation (frente 2b)

> Implementation report for `tune`: `spark.speculation`, `spark.network.timeout` e `spark.sql.broadcastTimeout`, com `SF-UI-007`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_TIMEOUTS_SPECULATION |
| **Date** | 2026-09-14 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_TUNE_TIMEOUTS_SPECULATION.md](./DEFINE_TUNE_TIMEOUTS_SPECULATION.md) |
| **DESIGN** | [DESIGN_TUNE_TIMEOUTS_SPECULATION.md](./DESIGN_TUNE_TIMEOUTS_SPECULATION.md) |
| **Status** | ✅ Shipped |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 9/9 (grupos do manifesto) |
| **Files Created** | 13 casos golden (3 de event log, 9 de tuning, 1 de change) |
| **Lines of Code** | extensões em `facts/event_log.py`, `tuning/spark_conf.py`, `adapters/{tools,cli}.py` e três arquivos do catálogo (nenhum módulo novo) |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12 833 passed, 13 skipped, 0 failed (suíte em 9 lotes, cinco rodados de novo depois das correções) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `facts/event_log.py`: critério por versão, `slow_tasks`, `slow_node` | (direct) | ✅ Complete | - | Desvios 1 e 2 abaixo |
| 2 | `tuning/spark_conf.py`: três derivações, limiares do catálogo, 14 recusas | (direct) | ✅ Complete | - | `_SEM_BASE_MEDIDA` saiu: nenhuma propriedade ficou sem derivação |
| 3 | `adapters/{tools,cli}.py`: enum, descrição, `--headroom` no broadcast | (direct) | ✅ Complete | - | |
| 4 | Catálogo: `SF-UI-007`, `capacity.investigate_slow_executor`, ação da `SF-TIMEOUT-002` | (direct) | ✅ Complete | - | |
| 5 | Fixtures de event log | (direct) | ✅ Complete | - | Sintéticos, gerados por script |
| 6 | Fixtures de tuning | (direct) | ✅ Complete | - | Entradas tiradas dos extratores reais |
| 7 | `fixtures/change/do_tune_network` | (direct) | ✅ Complete | - | 30 -> 720 |
| 8 | Testes de unidade, goldens, paridade MCP | (direct) | ✅ Complete | - | 9 de extrator, 6 de timeouts |
| 9 | Regras 15/16, AGENTS, agente, manual, STATUS, README, manifesto | (direct) | ✅ Complete | - | |

**Agent Key:** `(direct)` = construído direto, pelas mesmas razões das frentes anteriores.

---

## Files Created

| File | Agent | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `fixtures/eventlog/{no_lento_em_dois_stages,lentidao_espalhada,criterio_spark4}/` | (direct) | ✅ | `SF-UI-007` dispara no primeiro e cala no par; o terceiro prova o multiplier 3 do Spark 4 |
| `fixtures/tuning/{speculation_*,network_*,broadcast_timeout_*}/` | (direct) | ✅ | 9 casos, um por proposta e por recusa principal |
| `fixtures/change/do_tune_network/` | (direct) | ✅ | AT-014 |

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
d-e           364 passed            (rodado de novo)
f-sem-golden 1902 passed, 2 skipped (rodado de novo)
goldens-1    1388 passed, 4 skipped (rodado de novo)
goldens-2     579 passed
goldens-3     359 passed            (rodado de novo)
goldens-4     272 passed
goldens-5     460 passed            (rodado de novo)
g-z          5138 passed, 5 skipped
total       12833 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergências (6 remedidas por lista de ids; sem divergência nova depois das correções da suíte) |
| `check_status_numbers.py --strict` | ✅ 0 divergências (kinds 224 -> 226, regras 190 -> 191, executáveis 155 -> 156, fixtures 482 -> 495, fontes 248 -> 249) |
| `check_surface_lock.py --update` | ✅ tools 527 656 -> 528 432 (+776) |
| `gen_reference_docs.py` | ✅ 255 páginas, 3 regravadas |
| `sync_skills.py` | ✅ 3 espelhos do agente |
| `refresh_knowledge.py --offline --update` | ✅ fontes da `SF-UI-007` no lock |
| spec-lint (define, design) | ✅ PASS |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `SF-UI-007` disparou no golden `duration_skew_at_threshold`: a task lenta dele lê 3x mais shuffle remoto com o mesmo input | O tamanho da partição passou a ser input MAIS shuffle lido (remoto e local); o golden virou o caso natural de `lentidao_da_particao` | pequeno |
| 2 | O golden congelado da paridade MCP grava `sucesso_verbo_lookup`, que devolve a `SF-TIMEOUT-002` inteira | Exceção declarada por chamada, com motivo; só os três campos reescritos são neutralizados, e o teste exige que a troca exista | pequeno |
| 3 | O `.claude/agents/README.md` (scaffolding do agentspec, fora do git) sumiu antes do `sync_skills` | Restaurado do backup da sessão (`claude_agents_README.bak.md`) | nenhum |
| 4 | Primeira passada da suíte: 11 falhas em 5 lotes, fora do conjunto rápido. `spark.stage.slow_tasks` entrou em goldens de outros domínios que passam pelo event log (2 de CloudWatch Logs, o `scan` misto), a regra nova moveu a contagem do catálogo nos cenários e no holdout de migração (190 -> 191), e o teste de paridade `test_so_o_type_do_output_schema_difere` também compara as chamadas gravadas | Goldens regravados e conferidos no diff (só o fact novo e a contagem); `expects_kinds` dos dois de CloudWatch; `_chamada_declarada` no filtro da paridade, restrita aos campos da chamada declarada, com a contagem travada em 5 | pequeno |
| 5 | O script de diagnóstico da paridade gravou de novo `.sparkforge/traces.db` | Inspecionado (criado pelo script às 16:34) e apagado antes de rodar os lotes | nenhum |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `spark.stage.slow_tasks` para todo stage ou só com task lenta | Um por stage (DESIGN) ou só quando há lenta | Só quando há lenta | Um fact por stage uniforme era volume sem decisão, e mexeria em dezenas de goldens de event log sem mudar resposta nenhuma |
| 2 | Log sem versão do Spark | `spark.unresolved` (DESIGN) ou recusa no `tune` | Recusa `criterio_de_especulacao_desconhecido` no `tune` | Muitos logs sintéticos não têm `SparkListenerLogStart`; a lacuna mudaria o `unresolved_count` do `spark.log_analyzed` em todos |
| 3 | `no_measured_basis` no enum | Tirar ou manter | Manter | Nenhuma propriedade o emite mais, mas tirar valor do enum quebra a paridade MCP (só crescimento é aceito) |
| 4 | `spark.speculation` como valor | booleano ou string | `"true"` | O `change plan` escreve o literal |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `slow_tasks` só em stage com task lenta | Decisão 1 | `sem_tasks_lentas` é decidido pela presença de `spark.stage.task_duration` sem `slow_tasks` |
| Lacuna de versão no `tune`, não no extrator | Decisão 2 | Recusa nomeada em vez de fact de lacuna |
| Partição = input + shuffle lido | Issue 1 | Campos `median_read_bytes`/`max_slow_read_bytes` em vez de `input` |
| 14 recusas novas, não 13 | `criterio_de_especulacao_desconhecido` | Enum com 14 valores novos |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Tasks lentas por stage | ✅ Pass | `test_spark_3_uses_one_and_a_half_times_the_median`; goldens de event log |
| AT-002 | Versão muda o critério | ✅ Pass | `test_spark_4_raised_the_multiplier_to_three`; golden `criterio_spark4` |
| AT-003 | Nó lento | ✅ Pass | golden `no_lento_em_dois_stages` (`SF-UI-007`) e `tuning/speculation_no_lento` |
| AT-004 | Lentidão da partição | ✅ Pass | `tuning/speculation_particao` (de `duration_skew_at_threshold`) |
| AT-005 | Lentidão espalhada | ✅ Pass | golden `lentidao_espalhada` e `tuning/speculation_espalhada` |
| AT-006 | Speculation já ligada | ✅ Pass | `tuning/speculation_ja_ligada` |
| AT-007 | Relação quebrada | ✅ Pass | `tuning/network_relacao_quebrada` (1560 s); `test_a_broken_relation_gives_twelve_heartbeats` |
| AT-008 | Relação ok ou ausente | ✅ Pass | `tuning/network_relacao_ok`; `sem_relacao_observada` nos demais |
| AT-009 | Broadcast sem sintoma | ✅ Pass | `tuning/broadcast_timeout_medido` (370 s); `test_the_broadcast_timeout_is_the_measured_floor_with_headroom` |
| AT-010 | Broadcast com sintoma | ✅ Pass | `tuning/broadcast_timeout_com_sintoma`; `test_a_symptom_at_the_catalog_threshold_refuses` |
| AT-011 | Sem medida ou já cabe | ✅ Pass | `network_relacao_ok` (`sem_broadcast_medido`) e `broadcast_timeout_ja_cabe` |
| AT-012 | Ação da SF-TIMEOUT-002 | ✅ Pass | golden `timeout/heartbeat_maior_que_network` |
| AT-013 | Regras 15/16 | ✅ Pass | `CLAUDE.md` e `AGENTS.md` |
| AT-014 | Change plan | ✅ Pass | `change/do_tune_network` |

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

**Shipped:** `.claude/sdd/archive/TUNE_TIMEOUTS_SPECULATION/SHIPPED_2026-09-14.md` (PR #68)
