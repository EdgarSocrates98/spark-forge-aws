# BUILD REPORT: Stage → linha de codigo

> Implementation report for STAGE_CALLSITE_LOCATION

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | STAGE_CALLSITE_LOCATION |
| **Date** | 2026-09-11 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_STAGE_CALLSITE_LOCATION.md](../features/DEFINE_STAGE_CALLSITE_LOCATION.md) |
| **DESIGN** | [DESIGN_STAGE_CALLSITE_LOCATION.md](../features/DESIGN_STAGE_CALLSITE_LOCATION.md) |
| **Status** | Complete (B1–B4, B6); B5 no PR |

Branch `feat/stage-callsite-location`, empilhado sobre `feat/sarif-github-check` (PR #50).

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | B1–B4 e B6; B5 (commit, PR, upload real) em seguida |
| **Files Created** | `fixtures/sarif/{stage_python,stage_scala,stage_negativos}/` |
| **Files Modified** | `sparkforge/reporting/{locate,github}.py`, `sparkforge/adapters/tools.py`, `tests/test_reporting_github.py`, `tests/test_fixtures_golden_sarif.py`, `.github/workflows/ci.yml`, `docs/github-code-scanning.md`, `docs/superpowers/STATUS.md`, `docs/surface.lock.json`, `docs/claims.lock.json` + docs remediados |
| **Tests Passing** | Suite completa, um processo por arquivo: 262 arquivos, 12 100 passed, 0 failed, 9 skipped |
| **Agents Used** | Nenhum delegado: o build foi direto |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| B1 | `locate.py`, `github.py` + unidade | (direct) | ✅ | Indice `(stage_id, artifact)`, maior sufixo unico, Scala pelo nome do stage, 4 motivos novos, nota na mensagem |
| B2 | Enum da tool; invariante do corpus | (direct) | ✅ | Nenhum finding de stage do corpus sai `runtime`; os 28 saem `callsite_*` (0/28 localizados) |
| B3 | 3 fixtures + golden | (direct) | ✅ | `stage_python` 3 localizados (`jobs/lib/carga.py:7`, `jobs/lib/job.py:42`, `jobs/lib/job.py:58`); `stage_scala` em `src/Etl.scala:120`; `stage_negativos` 5 recusas, uma de cada |
| B4 | CI, docs, gates, suite, Snyk | (direct) | ✅ | Surface +315 bytes (tools 468 492 → 468 807) |
| B6 | Este relatorio e statuses | (direct) | ✅ | — |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| (direct) | todos | O DESIGN atribuia python-developer e test-generator a `locate.py`, `github.py` e a unidade. O escopo e um modulo, e cada teste depende da forma exata do fact `spark.stage.callsite`, medida no extrator |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge scripts tests -> All checks passed!
```

**Status:** ✅ Pass

### Type Check

```text
N/A — o repositorio nao configura mypy
```

**Status:** ⏭️ Skipped

### Tests

```text
Suite completa, um processo por arquivo: 262 arquivos, 12 100 passed, 0 failed, 9 skipped
check_vnext_claims 0 | check_status_numbers --strict 0 | check_surface_lock 0 | check_evals 10/10
Snyk Code (sparkforge/reporting): 0
```

**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Os `.py` gerados para as fixtures tinham a linha da acao indentada (`    resultado = df.collect()`), e `test_codeintel_staleness` acusou 6 arquivos que nao compilam | Linha da acao sem indentacao, mesmas linhas (7, 42, 58, 5, 1, 2); goldens regenerados; todo `.py` de `fixtures/sarif/` passa em `ast.parse` |
| 2 | O teste de `runtime` usava um finding de `stage`, que agora tem caminho proprio | Dividido: `job_run` sem stage continua `runtime`; stage sem callsite vira `callsite_ausente` |
| 3 | `.py` novos movem alegacoes de lastro (bytes e linhas da arvore) | Gate rodado de novo depois das fixtures: 0 divergencias |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Finding de stage sem fact de stage na evidencia | Primeiro callsite / recusa quando ha mais de um artefato | Recusa `callsite_ambiguo` com mais de um; usa o unico quando so ha um | O `stage_id` recomeca a cada aplicacao; escolher um artefato seria adivinhar |
| 2 | Onde a nota aparece | So SARIF / SARIF, anotacao e resumo | Os tres, pela mesma `_mensagem` | SC4 pede 100% nos tres |
| 3 | Modelo dos findings das fixtures | Escrever a mao / derivar do corpus | Derivar (`SF-UI-001` de `cloudwatch_logs/fetch_failed_com_executor_perdido`, `SF-WASTE-002` de `waste/ocioso_por_skew`) com ids por `Fact(...).id` | Fixture sintetica com forma real (decisao do brainstorm) |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `_candidatos` do Pattern 1 virou `_candidato(raiz, sufixo)` | Previsto no proprio DESIGN | Nenhum |
| `stage_python` tem 3 findings (dois stage 0 em event logs diferentes + um `job_run`) | Cobre AT-001, AT-002 e AT-003 no mesmo caso que vai ao upload real | `results_count` esperado = 3 |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001, 002, 003 | ✅ | golden `stage_python` + `TestCallsite` |
| AT-004, 005, 006, 008, 009 | ✅ | golden `stage_negativos` + `TestCallsite` |
| AT-007 | ✅ | golden `stage_scala` + `TestCallsite::test_scala_no_repo` |
| AT-010 | ✅ | `test_nenhum_finding_com_stage_sai_como_runtime` + `test_nenhum_finding_some_no_corpus_inteiro` |
| AT-011 | ✅ | `TestCaso` nos 4 casos anteriores, byte a byte |
| AT-012 | ⏳ | `workflow_dispatch` depois do push |

**Success Criteria:** SC1–SC6 e SC8 ✅; SC7 depende do upload real.

---

## Final Status

### Overall: ✅ COMPLETE (upload real pendente)

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Acceptance tests verified (AT-012 no PR)
- [x] Ready for /ship depois do AT-012

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_STAGE_CALLSITE_LOCATION.md`
