# BUILD REPORT: Debate ROI Gate (§11)

> Implementation report for Debate ROI Gate (§11)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_ROI_GATE |
| **Date** | 2026-09-14 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_DEBATE_ROI_GATE.md](./DEFINE_DEBATE_ROI_GATE.md) |
| **DESIGN** | [DESIGN_DEBATE_ROI_GATE.md](./DESIGN_DEBATE_ROI_GATE.md) |
| **Status** | ✅ Shipped |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 10/10 (grupos do manifesto) |
| **Files Created** | `sparkforge/agentic/executor/gate.py`, `rules/catalog/debate_gate.yaml`, `tests/test_agentic_executor_gate.py`, 3 casos golden em `fixtures/debate/gate_*` |
| **Lines of Code** | módulo novo de ~300 linhas; ajustes em `run.py`, `debate_run.py` e `tools.py` |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12 894 passed, 13 skipped, 0 failed (9 lotes; goldens-4 rodado de novo depois de regravar o golden de receipt) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `action_kinds.yaml`: critério e `reversible` nos 70 `kind` | (direct) | ✅ Complete | - | 4 `false`, por script depois de cada `axis:` |
| 2 | `debate_gate.yaml` | (direct) | ✅ Complete | - | `policy_version: 1`, `[P0, P1]` |
| 3 | `executor/gate.py` | (direct) | ✅ Complete | - | Recebeu `fala_de`, movido de `run.py` |
| 4 | `run.py`: `debate_gate` na entrada, trace próprio | (direct) | ✅ Complete | - | Vizinho de `plan` |
| 5 | `debate_run.py`: três recusas antes do budget | (direct) | ✅ Complete | - | `detail` com medida, rollback ou sinal |
| 6 | `tools.py`: enum e descrições | (direct) | ✅ Complete | - | Enum compartilhado por start/next/submit |
| 7 | `tests/test_agentic_executor_gate.py` | (direct) | ✅ Complete | - | 19 testes |
| 8 | Goldens `fixtures/debate/gate_*` e harness | (direct) | ✅ Complete | - | `finding_overrides` no `meta.yaml` |
| 9 | Registros: vocabulário, `NAO_SAO_AREA`, paridade MCP | (direct) | ✅ Complete | - | 5 reescritas declaradas |
| 10 | Manual, `CLAUDE.md` (regra 29), STATUS, referência, claims | (direct) | ✅ Complete | - | |

---

## Files Created

| File | Agent | Verified | Notes |
| ---- | ----- | -------- | ----- |
| `sparkforge/agentic/executor/gate.py` | (direct) | ✅ | Puro; política inválida vira `unresolved` |
| `rules/catalog/debate_gate.yaml` | (direct) | ✅ | Fora das áreas de regra |
| `tests/test_agentic_executor_gate.py` | (direct) | ✅ | Quatro vereditos, ordem, política, trace, varredura de texto |
| `fixtures/debate/gate_{experimentar_antes,nao_debater,unresolved}/` | (direct) | ✅ | Recusa sem gravar; `nao_debater` sem budget prova a ordem |

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
a-c            2410 passed, 2 skipped   (246s)
d-e             364 passed              (85s)
f-sem-golden   1902 passed, 2 skipped   (121s)
goldens-1      1399 passed, 4 skipped   (1046s)
goldens-2       579 passed              (387s)
goldens-3       359 passed              (255s)
goldens-4       272 passed              (199s; 1a passada: 1 falha no golden de receipt, regravado)
goldens-5       460 passed              (216s)
g-z (2 metades) 1983 + 3166 passed, 5 skipped (318s + 306s)
total         12894 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergências (6 remedidas por lista de ids: VNX-726, 640, 663, 666, 741, 431) |
| `check_status_numbers.py --strict` | ✅ 0 divergências (fixtures 497 -> 500) |
| `check_surface_lock.py --update` | ✅ tools +769 bytes (532 181 -> 532 950); nenhuma tool nova |
| `gen_reference_docs.py` | ✅ 257 páginas, 2 regravadas |
| spec-lint (define, design) | ✅ PASS |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | `Experiment` não tem `unknown_question` nem `evidence_needed` (o DESIGN ligava lacuna e experimento por esse campo) | `experiments_from([lacuna])` por lacuna; `evidence_needed` lido da própria lacuna | pequeno |
| 2 | `_DEBATE_REFUSAL_REASONS` é um enum só para `start`, `next` e `submit` | Cinco reescritas declaradas na paridade MCP, e o contador medido de 3 para 8 por transporte | pequeno |
| 3 | `run.py` importaria o gate e o gate precisaria de `_fala_de` de `run.py` (import circular) | `fala_de` mudou para `gate.py`; `run.py` o importa com o nome antigo | nenhum |
| 4 | Dois arquivos vazios (`lista`, `nome`) apareceram na raiz durante a sessão | Conferidos (0 bytes) e apagados | nenhum |
| 5 | `test_fixtures_golden_receipt` caiu no lote goldens-4: o recibo de `fixtures/receipt/uniao_debate` conta os traces do blackboard, e o `arbitrate` agora grava dois (`arbitration` e `debate_gate`) | Golden regravado com `SPARKFORGE_REGEN_RECEIPT=1`; o diff tem só a contagem (1 -> 2), o sha256 de `traces.jsonl` e o `receipt_id` | um lote a mais |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Arbitragem sem claim vencedora | Só `escalate` como sem lastro, ou `escalate` e `sem_vencedor` | Os dois | Sem vencedora a arbitragem também não tem lastro; na dúvida, o gate mantém o comportamento de hoje (debater) |
| 2 | Variações dos goldens do gate | Copiar os facts da união para cada caso, ou `finding_overrides` no `meta.yaml` | `finding_overrides` | O domínio proíbe `expected/findings.json`, e copiar 60 facts para mudar uma severidade duplicaria medida |
| 3 | Onde mora `fala_de` | Duplicar em `gate.py`, ou mover | Mover, com alias em `run.py` | Uma implementação só da mesma pergunta |
| 4 | Entrada sem `debate_gate` no `start` | Deixar passar, ou `gate_unresolved` | `gate_unresolved` | Abrir debate sem o veredito pularia o gate calado |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Ligação lacuna -> experimento por chamada individual, e não pelo campo `unknown_question` | Issue 1 | Mesmo resultado; `evidence_needed` vem da lacuna |
| Paridade MCP com 5 reescritas, não 3 | Issue 2 | `debate_next` e `debate_submit` também publicam o enum |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Par real | ✅ Pass | `test_par_real_sai_debater_pela_severidade`; 13 goldens de debate sem regravação |
| AT-002 | Medida antes | ✅ Pass | `test_lacuna_citando_o_par_sai_experimentar_antes`; golden `gate_experimentar_antes` |
| AT-003 | Barato para debater | ✅ Pass | `test_par_barato_e_reversivel_sai_nao_debater`; golden `gate_nao_debater` (sem budget) |
| AT-004 | Irreversível | ✅ Pass | `test_irreversivel_decide_mesmo_com_severidade_ausente` |
| AT-005 | Sem lastro | ✅ Pass | `test_escalate_sai_debater`, `test_sem_claim_vencedora_conta_como_sem_lastro` |
| AT-006 | Sinal faltando | ✅ Pass | `test_kind_fora_do_vocabulario_sai_unresolved`; golden `gate_unresolved` |
| AT-007 | Política inválida | ✅ Pass | `test_politica_invalida_sai_unresolved_e_nao_derruba_o_plano` |
| AT-008 | Sinais | ✅ Pass | `test_sinais_informativos_e_ganho_de_informacao_recusado` |
| AT-009 | Vocabulário | ✅ Pass | `test_todo_kind_declara_reversible`, `test_irreversiveis_sao_os_declarados` |
| AT-010 | Trace | ✅ Pass | `test_arbitrate_grava_trace_proprio_do_gate` |
| AT-011 | Sem afirmação de ganho | ✅ Pass | `test_nenhuma_frase_de_ganho_ou_economia` |
| AT-012 | Enum de recusa | ✅ Pass | `test_o_enum_de_recusas_e_o_conjunto_das_constantes`; paridade MCP |

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

**Ready for:** `/ship .claude/sdd/features/DEFINE_DEBATE_ROI_GATE.md`
