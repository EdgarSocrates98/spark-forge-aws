# BUILD REPORT: Freshness computavel das fontes

> Implementation report for KNOWLEDGE_FRESHNESS

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | KNOWLEDGE_FRESHNESS |
| **Date** | 2026-09-11 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_KNOWLEDGE_FRESHNESS.md](../features/DEFINE_KNOWLEDGE_FRESHNESS.md) |
| **DESIGN** | [DESIGN_KNOWLEDGE_FRESHNESS.md](../features/DESIGN_KNOWLEDGE_FRESHNESS.md) |
| **Status** | Complete (B1–B5); B6 no PR |

Branch `feat/knowledge-freshness`, a partir da `main` (com #50, #51 e #52).

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | B1–B5; B6 (commit e PR) em seguida |
| **Files Created** | `sparkforge/knowledge_freshness.py`, `tests/test_knowledge_freshness.py`, `tests/test_adapters_freshness.py`, `fixtures/sarif/freshness/`, `docs/knowledge-freshness.md` |
| **Files Modified** | `scripts/refresh_knowledge.py`, `adapters/{_core,cli,tools}.py`, `reporting/github.py`, `scripts/regen_fixtures.py`, `tests/{test_refresh_knowledge,test_fixtures_golden_sarif,test_fixtures_golden_mcp_parity}.py`, `sf-verifier` + espelhos, `examples/github/sparkforge.yml`, `docs/superpowers/STATUS.md`, `docs/surface.lock.json`, `docs/claims.lock.json` + `docs/harness/{CODEINTEL-GAP,CURRENT-HARNESS-GAP}.md` |
| **Tests Passing** | Suite completa, um processo por arquivo: 267 arquivos, 12 230 passed, 0 failed, 9 skipped |
| **Agents Used** | Nenhum delegado: o build foi direto |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| B1 | Modulo + unidade | (direct) | ✅ | 26 testes; o leitor de `Fontes` movido devolve o mesmo que o antigo no `knowledge/` real (219 URLs, 28 documentos) |
| B2 | `changed_at` no refresh | (direct) | ✅ | Quatro casos com `fetch` falso; `--update --offline` sobre o lock real deixa o arquivo byte a byte |
| B3 | Verbos, CLI, tools, paridade | (direct) | ✅ | Opt-in; 13 chaves aditivas por transporte no golden de paridade; CLI e tool concordam |
| B4 | Caso `fixtures/sarif/freshness`, `sf-verifier` | (direct) | ✅ | Lock sintetico por `SPARKFORGE_SOURCES_LOCK`; os 7 casos anteriores intactos |
| B5 | Docs, gates, suite, Snyk | (direct) | ✅ | Surface +4 539 bytes; 13 alegacoes remediadas por id |

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| (direct) | todos | Cada passo dependia de medida do anterior (forma do lock, golden de paridade, leitura de knowledge no parser da CLI) |

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
Suite completa, um processo por arquivo: 267 arquivos, 12 230 passed, 0 failed, 9 skipped
check_vnext_claims 0 | check_status_numbers --strict 0 | check_surface_lock 0 | check_evals 10/10
Snyk Code (knowledge_freshness.py, refresh_knowledge.py): 0
```

**Status:** ✅ Pass

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | O golden de paridade MCP compara uma chamada real de `rules_lookup` e os schemas das tres tools (A-006) | Opt-in por `source_freshness`, e `ALTERADAS_DEPOIS_DO_GOLDEN` aceita so diferenca aditiva |
| 2 | Contagem de diffs aditivos deu 14 contra 13 previstos | O `outputSchema.type` do `judge` (allowlist antiga) tambem casava como aditivo; a contagem aditiva passou a exclui-lo |
| 3 | `SPARKFORGE_KNOWLEDGE` apontando para um diretorio so com lock quebrou a CLI: o `build_parser` le a matriz do Control-M de knowledge | `SPARKFORGE_SOURCES_LOCK`, que troca so o lock |
| 4 | Snyk (Low): variavel de ambiente para `Path` sem checagem | Caminho resolvido e so `.json` existente; senao `lock_ilegivel` |
| 5 | Dois findings da mesma regra saiam como linhas iguais no resumo | Coluna "Sujeito" |
| 6 | `tests/test_facts_scan.py` recusou `rglob` em `sparkforge/`, e so no lote completo | `iter_source_files`; mesmos 52 arquivos |
| 7 | VNX-670 e razao (`contains`), e o script de remediacao so trata numero | Ajustada a mao, com nota no manifesto |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Mesma URL citada com datas diferentes | Mais recente / mais antiga | Mais antiga | Se a pagina mudou depois de qualquer validacao, alguem precisa reler |
| 2 | Descricao das tools do golden | Explicar a flag nela / na propriedade | Na propriedade nova | Mudar a descricao e alteracao de valor, e o teste de paridade so aceita chave nova |
| 3 | Lock do golden | Copia de knowledge / variavel propria | `SPARKFORGE_SOURCES_LOCK` | Issue 3 |
| 4 | `stale` sem data de validacao | `unverified` / `stale` | `stale` quando ha `changed_at` | A mudanca registrada e o sinal mais forte, e sem data nao ha revalidacao |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `SPARKFORGE_SOURCES_LOCK` e `meta.sources_lock` em vez de `SPARKFORGE_KNOWLEDGE` no golden | Issue 3 | Uma variavel de ambiente nova, documentada |
| Coluna "Sujeito" na secao do resumo | Issue 5 | — |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 a AT-007 | ✅ | `tests/test_knowledge_freshness.py` |
| AT-008, AT-009 | ✅ | `tests/test_refresh_knowledge.py::TestChangedAt` |
| AT-010, AT-011, AT-013 | ✅ | `tests/test_adapters_freshness.py` |
| AT-012 | ✅ | golden `fixtures/sarif/freshness` |

**Success Criteria:** SC1–SC8 ✅.

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass
- [x] No blocking issues
- [x] Acceptance tests verified
- [x] Ready for /ship

---

## Next Step

**If Complete:** `/ship .claude/sdd/features/DEFINE_KNOWLEDGE_FRESHNESS.md`
