# BUILD REPORT: Debate Executor

> Implementation report for Debate Executor

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DEBATE_EXECUTOR |
| **Date** | 2026-09-11 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_DEBATE_EXECUTOR.md](../features/DEFINE_DEBATE_EXECUTOR.md) |
| **DESIGN** | [DESIGN_DEBATE_EXECUTOR.md](../features/DESIGN_DEBATE_EXECUTOR.md) |
| **Status** | Complete (B8, COULD, deliberadamente não rodado) |

Branch `feat/debate-executor`, empilhado sobre `feat/eval-harness-agentico` (`37cf718`).

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | B1 (parcial → fechada no B5), B2–B7; B8 não rodado, com o motivo registrado |
| **Files Created** | `sparkforge/agentic/executor/{debate_run,debate_evidence}.py`; `sparkforge/evals/debate_grade.py`; `scripts/run_debate.py`; `skills/run-debate/` + espelhos; `evals/agentic/debate/` (3 casos + união); `fixtures/debate/` (13 casos); 7 arquivos de teste |
| **Tests Passing** | Suíte completa, um processo por arquivo (257 arquivos): 11 964 passaram, 0 falharam, 9 skipped (nenhum desta entrega) |
| **Agents Used** | 4 agentes general-purpose em sequência, um por bloco, sem dois escritores na árvore ao mesmo tempo |
| **Custo de host** | Smoke B1: US$ 0,02; smoke com brief real: US$ 0,0723 |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| B1 | Smoke A-004 | (direct) | ✅ parcial | Num diretório vazio o Haiku pediu contexto e não produziu JSON. Confirmou a necessidade do brief autossuficiente, de `no_json_block` e de `stdin=DEVNULL` |
| B2 | Máquina de estados, reextração, goldens | general-purpose (bloco 1) | ✅ | 112 testes |
| B3 | CLI, 3 tools MCP, 7 registros | general-purpose (bloco 2) | ✅ | `surface.lock` +15 720 bytes (83 → 86 tools); 25 alegações remediadas por lista de ids |
| B4–B6 | Grader, suíte, driver, skill | general-purpose (bloco 3) | ✅ | 68 testes; smoke real US$ 0,0723, bloco JSON lido e aceito (A-004 fechada); skills 58 → 59 (+5 096 bytes) |
| B7 | Docs + suíte completa | general-purpose (bloco 4) | ✅ | Regra 29, relatório agêntico, `evals/README`, `README`, STATUS |
| B8 | Baseline Haiku da suíte | — | ⏭️ não rodado | Ver Issue 3 |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| general-purpose × 4 | todos | DESIGN + briefing com as armadilhas conhecidas do repositório (registros manuais, fronteira runtime/avaliação, forma aceita pelo scanner de segurança, lotes por arquivo) |

---

## Files Created

| File | Verified | Notes |
| ---- | -------- | ----- |
| `sparkforge/agentic/executor/debate_run.py` | ✅ | `start`/`next_step`/`submit`; fechamento pelo `referee_over_blackboard` numa cópia temporária, gravando só a decisão final (blackboard append-only) |
| `sparkforge/agentic/executor/debate_evidence.py` | ✅ | Allowlist de 22 extratores, caminho confinado ao case, `.sparkforge/` fora do alcance, sha1 do artefato gravado |
| `sparkforge/evals/debate_grade.py` + subcomando `debate` | ✅ | `correct_winner`, `wrong_winner`, `correct_unresolved`, `false_resolution`, `missed_resolution` + `decisive_fact` |
| `scripts/run_debate.py` | ✅ | Workspace de prova, nomes neutros de caso, `stdin=DEVNULL`, `no_json_block` |
| `skills/run-debate/SKILL.md` | ✅ | Não despachável; espelhos via `sync_skills.py` |
| `evals/agentic/debate/{lf_vence,graph_vence,sem_fato}` | ✅ | Decididos por `lakeformation.grant` reextraído via `lakeformation-grants` |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge scripts tests -> limpo
```

**Status:** ✅ Pass

### Type Check

```text
N/A — o repositório não configura mypy
```

**Status:** ⏭️ Skipped

### Tests

```text
Suíte completa (LOTES, um processo por arquivo): 11964 passed, 0 failed, 9 skipped
check_vnext_claims 0 | check_status_numbers --strict 0 | check_surface_lock 0 | check_evals 10/10
Snyk Code (executor/, evals/, scripts/run_debate.py): 0 achados
```

**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | O `budget:` recusava `max_rounds`, e o plano sairia sempre `unresolved` | `debate_rounds_from_budget` aceita a chave na faixa 1–10 do `DebateBudget`; sem ela, `budget_undeclared` |
| 2 | "Claim sem objeção pendente" nunca geraria vencedor, porque o referee recusa objeção sem réplica | O vencedor existe só quando exatamente um lado declara `concede: true`; nenhum ou os dois dão `unresolved` |
| 3 | O único par de conflito direto do catálogo (`SF-GRAPH-005` × `SF-LF-001`) só nasce da UNIÃO de facts de dois jobs diferentes; no smoke real o Haiku argumentou que o conflito não existe para nenhum dos dois sozinho | A suíte mede a mecânica e a decidibilidade com roteiros gravados. O baseline com modelo (B8) não foi rodado, porque mediria um tópico mal posto. Declarado em `evals/README.md` e no STATUS |
| 4 | `lakeformation.access_model` vem de derivação, e a reextração não o produz | O fact decisivo passou a ser `lakeformation.grant`, que o extrator `lakeformation-grants` da allowlist produz |
| 5 | Arquivos vazios apareceram na raiz por erro de redirecionamento (`77`, `dict[str`) | Removidos depois de conferir tamanho zero e horário dentro da sessão |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Como executar um build grande com o contexto em 85% | Inline / agentes em sequência | 4 agentes em sequência | O contexto de cada bloco fica fora da conversa principal; um escritor por vez |
| 2 | Regra do vencedor | Sem objeção pendente / `concede` | `concede` | Compatível com o referee; nunca maioria |
| 3 | Rodar o B8 | Rodar / não rodar | Não rodar | Issue 3: mediria um tópico mal posto |
| 4 | O driver chama `_core` em processo | subprocess da CLI / em processo | Em processo | Mesmas funções da CLI; menos superfície de comando |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `concede: bool` na submissão | Issue 2 | Schema da submissão cresce um campo |
| `hypothesis_cannot_close` é recusa de fechamento, não de submit | AT-007 | — |
| Recusas nomeadas a mais (`invalid_rules`, `debate_not_found`, `dangling_target_ref`, `duplicate_entity`, `artifact_not_found`, `extractor_failed`) | Casos que o DESIGN não listou | — |
| Fact decisivo `lakeformation.grant` | Issue 4 | — |
| Grader lê o `result.json` do driver | Mantém a avaliação sem ler o workspace do runtime | — |
| B8 não rodado | Issue 3 | Sem baseline de debate com modelo |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001…AT-011 | ✅ | `fixtures/debate/` (13 casos) + `test_agentic_debate_run.py` + `test_cli_debate.py` |
| AT-012 | ✅ parcial | Smoke real de um turno, com bloco JSON aceito; o driver ponta a ponta não rodou com modelo (Issue 3) |
| AT-013 | ✅ | `test_evals_debate_grade.py` |
| AT-014 | ✅ | `test_evals_invariants.py` com os módulos novos |

**Success Criteria:**
- SC1–SC8 ✅.
- A verificação manual da skill (A-006) fica pendente para uma sessão de host.

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed (B8/COULD não rodado, com o motivo)
- [x] All verification checks pass
- [x] All tests pass (suíte completa)
- [x] No blocking issues
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_DEBATE_EXECUTOR.md`
