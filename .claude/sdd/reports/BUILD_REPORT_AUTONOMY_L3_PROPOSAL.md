# BUILD REPORT: Autonomia L3 — pacote de proposta de PR

> Implementation report for `sparkforge change propose` e a skill `propose-change-pr`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L3_PROPOSAL |
| **Date** | 2026-09-14 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_AUTONOMY_L3_PROPOSAL.md](../features/DEFINE_AUTONOMY_L3_PROPOSAL.md) |
| **DESIGN** | [DESIGN_AUTONOMY_L3_PROPOSAL.md](../features/DESIGN_AUTONOMY_L3_PROPOSAL.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 10/10 (grupos do manifesto) |
| **Files Created** | `sparkforge/change/proposal.py`, `skills/propose-change-pr/SKILL.md`, `tests/test_change_proposal.py`, 2 casos golden em `fixtures/change/` |
| **Lines of Code** | módulo novo de ~400 linhas; portas em `_core`, `cli`, `tools` |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12 864 passed, 13 skipped, 0 failed (9 lotes, 1a passada) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `change/refusals.py`: 4 recusas com `unlock` | (direct) | ✅ Complete | - | `RECUSAS_DA_PROPOSTA` |
| 2 | `change/proposal.py`: montagem pura | (direct) | ✅ Complete | - | Assinatura e recibo injetados |
| 3 | `change/__init__.py` | (direct) | ✅ Complete | - | |
| 4 | `_core.change_propose`, CLI e tool | (direct) | ✅ Complete | - | Schema de recusa próprio |
| 5 | Skill `propose-change-pr` | (direct) | ✅ Complete | - | Não despachável |
| 6 | Policy, `settings.json`, `.gitignore` | (direct) | ✅ Complete | - | `sync-settings` |
| 7 | Goldens `proposta_completa` e `proposta_resolve` | (direct) | ✅ Complete | - | Os dois caminhos da assinatura |
| 8 | `tests/test_change_proposal.py` e golden de change | (direct) | ✅ Complete | - | 19 testes |
| 9 | Registros de tool e skill | (direct) | ✅ Complete | - | |
| 10 | Manual, STATUS, contagens | (direct) | ✅ Complete | - | |

---

## Files Created

| File | Agent | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `sparkforge/change/proposal.py` | (direct) | ✅ | Sem `subprocess`, `os` nem chamada de sistema (teste por AST) |
| `skills/propose-change-pr/SKILL.md` | (direct) | ✅ | Seções padrão e `## Não faz` |
| `tests/test_change_proposal.py` | (direct) | ✅ | Pacote, recusas, severidade, AST |
| `fixtures/change/proposta_{completa,resolve}/` | (direct) | ✅ | Com e sem assinatura; com benchmark anexado |

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
a-c           2391 passed, 2 skipped   (285s)
d-e            364 passed              (87s)
f-sem-golden  1902 passed, 2 skipped   (125s)
goldens-1     1390 passed, 4 skipped   (1244s)
goldens-2      579 passed              (444s)
goldens-3      359 passed              (250s)
goldens-4      272 passed              (197s)
goldens-5      460 passed              (216s)
g-z           5147 passed, 5 skipped   (574s)
total        12864 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergências (22 remedidas por lista de ids) |
| `check_status_numbers.py --strict` | ✅ 0 divergências (tools 102 -> 103, skills 59 -> 60, fixtures 495 -> 497) |
| `check_surface_lock.py --update` | ✅ tools +3 749 bytes; skills +1 documento, +4 111 bytes |
| `gen_reference_docs.py` | ✅ 257 páginas (2 novas) |
| `sync_skills.py` | ✅ skill e `sf-verifier` nos espelhos |
| `policy sync-settings` | ✅ `Bash(git push *)` e `Bash(gh pr create *)` em `permissions.ask` |
| spec-lint (define, design) | ✅ PASS |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `_signature_parts` não trata lista vazia (`pop` de conjunto vazio): com `after/` sem achado, assinatura e recibo cairiam | O `_core` confere os findings antes; sem achado, o pacote sai sem assinatura e sem recibo, e o corpo diz por quê | pequeno |
| 2 | O `report.json` do sandbox não guarda a base do `tune` | O corpo mostra o diff inteiro e os achados; a base do valor fica fora (desvio) | nenhum |
| 3 | `_CHANGE_REFUSAL` é compartilhado entre `change plan` e `change sandbox` | Schema de recusa próprio para a tool nova, sem mexer no enum das outras duas | nenhum |
| 4 | `sync_skills.py` apagou de novo o `.claude/agents/README.md` | Backup da sessão antes do sync e restaurado depois | nenhum |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Achado novo sem finding correspondente em `after/` | Atenção ou bloqueio | Bloqueio | Não saber a gravidade não é o mesmo que ela ser baixa |
| 2 | Assinatura e recibo dentro do `proposal.py` | Importar `adapters` ou injetar | Injetar | O mesmo molde do `varrer` do sandbox; o módulo não depende de `adapters` |
| 3 | Anexos de funcval | Resultado do `funcval compare` ou facts `funcval.*` | Facts `funcval.*` | O recibo e o `proof` já tratam funcval e bench como facts |
| 4 | `report verify` devolve `status: signed` | O DEFINE dizia `verified` | O valor real | É o contrato do `report verify` |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Sem base do `tune` no corpo | Issue 2 | O revisor lê o diff; a origem do valor fica no plano |
| Sem achado em `after/`: pacote de 8 arquivos, sem `evidence/receipt.json` | Issue 1 | `signed: false`, `receipt_id: null` |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Pacote completo | ✅ Pass | `test_grava_os_nove_arquivos_sem_rodar_git`; golden `proposta_completa` |
| AT-002 | Idempotência | ✅ Pass | `test_o_mesmo_now_grava_os_mesmos_bytes` |
| AT-003 | Sandbox inexistente | ✅ Pass | `test_sandbox_inexistente_nao_grava_nada` |
| AT-004 | Sandbox recusado | ✅ Pass | `test_sandbox_que_nao_aplicou` |
| AT-005 | Árvore mudou | ✅ Pass | `test_arvore_mudada_depois_do_sandbox` |
| AT-006 | Achado novo P0/P1 | ✅ Pass | `test_achado_novo_p1_bloqueia_e_nao_grava` |
| AT-007 | P2/P3 novo | ✅ Pass | `test_p2_e_p3_vao_para_atencao_e_p0_p1_bloqueiam` |
| AT-008 | Sem medida | ✅ Pass | `test_o_corpo_lista_a_medida_pendente_e_nao_afirma_ganho` |
| AT-009 | Com medida | ✅ Pass | `test_a_medida_anexada_entra_no_corpo`; golden `proposta_resolve` |
| AT-010 | Assinatura | ✅ Pass | `test_a_assinatura_do_corpo_confere` |
| AT-011 | Recibo | ✅ Pass | `test_o_recibo_tem_raiz_no_after_e_nao_carrega_spans` |
| AT-012 | Patch aplica | ✅ Pass | `test_o_patch_e_o_rollback_reproduzem_as_duas_copias`; `test_git_apply_check_aceita_o_patch` |
| AT-013 | Sem git no pacote | ✅ Pass | `test_o_modulo_nao_importa_subprocess_nem_chama_o_sistema` |
| AT-014 | Policy | ✅ Pass | `policy sync-settings` e os testes de policy |

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

**Ready for:** `/ship .claude/sdd/features/DEFINE_AUTONOMY_L3_PROPOSAL.md`
