# BUILD REPORT: Autonomia L1–L2

> Implementation report for Autonomy L1–L2 (§15): `change plan` e `change sandbox`

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | AUTONOMY_L1_L2 |
| **Date** | 2026-09-13 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_AUTONOMY_L1_L2.md](../features/DEFINE_AUTONOMY_L1_L2.md) |
| **DESIGN** | [DESIGN_AUTONOMY_L1_L2.md](../features/DESIGN_AUTONOMY_L1_L2.md) |
| **Status** | Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 11/11 (entradas do manifesto) |
| **Files Created** | 5 modulos + 4 testes + 13 casos golden (54 arquivos) + manual + 3 paginas de referencia |
| **Lines of Code** | 938 em `sparkforge/change/` (5 arquivos); 479 de teste |
| **Build Time** | 1 sessao |
| **Tests Passing** | 12 704 passed, 13 skipped, 0 failed (suite em 9 lotes) |
| **Agents Used** | 0 (build direto; manifesto com Python puro, testes e registros no molde do repositorio) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `sparkforge/change/{__init__,plan}.py` | (direct) | ✅ Complete | - | L1 puro |
| 2 | `sparkforge/change/apply.py` | (direct) | ✅ Complete | - | Aplicador estrito |
| 3 | `sparkforge/change/sandbox.py` (+ `refusals.py`) | (direct) | ✅ Complete | - | `refusals.py` fora do manifesto (desvio 1) |
| 4 | `_core.change_plan/change_sandbox` | (direct) | ✅ Complete | - | Compoe `build_conf_advice`, `scan`, `simulate.diff`, `proof.load_policy` |
| 5 | CLI `change plan|sandbox` | (direct) | ✅ Complete | - | `change_action` na cadeia de `getattr` |
| 6 | Tools `sparkforge_change_plan` / `_sandbox` | (direct) | ✅ Complete | - | READ_ONLY / `_WRITE_IDEMPOTENT` |
| 7 | `fixtures/change/` (13 casos) + `.gitattributes` | (direct) | ✅ Complete | - | Facts do extrator real, gerados por script |
| 8 | Testes de unidade, sandbox e golden | (direct) | ✅ Complete | - | 4 arquivos |
| 9 | `.gitignore` (`.sparkforge/sandbox/`) | (direct) | ✅ Complete | - | |
| 10 | Registros de tool nova | (direct) | ✅ Complete | - | Lista, amostra real, FAILABLE, writers, harness 92, paridade MCP, `parity.yaml`, `manifest.json`, agentes + `sync_skills`, surface, claims |
| 11 | Docs | (direct) | ✅ Complete | - | Manual `docs/guia/usos/change.md`, indice do guia, referencia, CLAUDE.md, AGENTS.md, GUIA_DE_USO.md, `.devin/README.md`, STATUS, `agentic-evolution-report.md` |

**Agent Key:** `(direct)` = construido direto pelo build-agent. O manifesto do DESIGN atribuia @python-developer e @test-generator; o build seguiu os padroes do DESIGN direto, porque o codigo depende de registros e armadilhas do repositorio que so a sessao conhecia (ver Autonomous Decisions).

---

## Agent Contributions

| Agent | Files | Specialization Applied |
|-------|-------|------------------------|
| (direct) | todos | Padroes do DESIGN (span do no, aplicador tudo-ou-nada, duas copias) e os moldes de `policy/`, `scan/` e `simulate/` |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `sparkforge/change/__init__.py` | 36 | (direct) | ✅ | API publica |
| `sparkforge/change/refusals.py` | 89 | (direct) | ✅ | 14 nomes de recusa com `unlock` |
| `sparkforge/change/plan.py` | 269 | (direct) | ✅ | L1 |
| `sparkforge/change/apply.py` | 249 | (direct) | ✅ | Parser e aplicador |
| `sparkforge/change/sandbox.py` | 295 | (direct) | ✅ | L2 |
| `tests/test_change_plan.py` | 136 | (direct) | ✅ | Troca, recusas, nao escreve, sem subprocess/provider |
| `tests/test_change_apply.py` | 107 | (direct) | ✅ | Formas recusadas, tudo ou nada, CRLF, BOM, insercao |
| `tests/test_change_sandbox.py` | 113 | (direct) | ✅ | Arvore intacta, id estavel, limpeza, artefatos, erros de entrada |
| `tests/test_fixtures_golden_change.py` | 123 | (direct) | ✅ | 13 goldens, ida-e-volta, cobertura de recusa |
| `fixtures/change/` | 54 arquivos | (direct) | ✅ | 8 casos de plano, 5 de sandbox |
| `docs/guia/usos/change.md` | 196 | (direct) | ✅ | Manual para leigo |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge tests/test_change_*.py tests/test_fixtures_golden_change.py tests/test_adapters_tools.py
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
a-c          2355 passed, 2 skipped   (1a passada: 1 falha, modulo novo fora do git; git add e relancado)
d-e           364 passed
f-sem-golden 1886 passed, 2 skipped
goldens-1    1366 passed, 4 skipped
goldens-2     579 passed
goldens-3     358 passed
goldens-4     266 passed
goldens-5     422 passed
g-z          5108 passed, 5 skipped
total       12704 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergencias (28 remedidas por lista de ids) |
| `check_status_numbers.py --strict` | ✅ 0 divergencias |
| `check_surface_lock.py --update` | ✅ 509 717 -> 517 660 (+7 943 bytes) |
| `gen_reference_docs.py` | ✅ 253 paginas, 8 regravadas |
| spec-lint (define, design) | ✅ PASS |

**Status:** ✅ 12704/12704 Pass

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | Na segunda execucao do sandbox, o `.sparkforge/` criado pela primeira aparecia em `copy_skipped` e o relatorio deixava de ser identico (SC8) | O estado proprio (`ESTADO_PROPRIO = ".sparkforge"`) sai do relatorio; a pasta continua podada da copia | pequeno |
| 2 | O `scan` recusa `.sparkforge/artifacts/manifest.json` que nao seja lista | Teste corrigido para escrever `[]` (o sandbox copia o manifesto como esta) | pequeno |
| 3 | Parametro de teste com 2 MB de texto virou id de teste inviavel | Caso movido para um teste proprio | pequeno |
| 4 | O script de facts trocava `particoes)` tambem na assinatura da funcao e o arquivo deixava de compilar | Troca restrita a chamada (` particoes)\n`) | pequeno |
| 5 | Lote a-c: `test_arvore_versionada` exige modulo novo no git | `git add` explicito dos arquivos novos antes dos lotes (armadilha ja registrada na memoria) | um lote |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde moram os nomes de recusa | Em `plan.py`, em cada modulo, ou num modulo proprio | `sparkforge/change/refusals.py` | Tres modulos levantam e a tool declara no schema; um lugar so evita divergir calado |
| 2 | Recusas alem do DEFINE | So as listadas, ou nomear tambem valor igual, valor que nao cabe e diff ilegivel | `valor_ja_igual`, `valor_invalido`, `diff_malformado` | Regra 20: toda saida sem diff diz por que; engolir seria silencio |
| 3 | Diff LF sobre arquivo CRLF | Recusar (estrito) ou tolerar o fim de linha | Tolerar so o fim de linha; a linha nova adota o do arquivo | `git diff` gera LF; recusar no Windows por um byte que nao muda conteudo seria atrito sem protecao |
| 4 | Artefatos coletados na copia | Deixar fora (`.sparkforge` e podado) ou copiar `.sparkforge/artifacts/` | Copiar | Sem eles o `scan` da copia julgaria menos do que o do repositorio, e a diferenca de achados mentiria |
| 5 | Delegar a @python-developer/@test-generator | Delegar ou construir direto | Direto | Registros literais, INV-007/009, armadilhas de lote e de golden: contexto da sessao que o subagente nao tem |
| 6 | Saida de `--clean` | Mesmo schema do relatorio ou forma propria | Forma propria (`cleaned`, `removed`), schema com `stage` e `main_tree_touched` obrigatorios | O schema aceita as duas sem campo falso |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| `sparkforge/change/refusals.py` alem dos tres modulos | Decisao 1 acima | Nenhum no comportamento |
| `ESTADO_PROPRIO` fora de `copy_skipped` | Issue 1 (idempotencia) | O relatorio nao lista `.sparkforge`; a copia continua sem ele |
| `.sparkforge/artifacts/` copiado | Decisao 4 | O `scan` da copia ve o que o do repositorio ve |
| `applied: false` explicito no plano | Contrato do L1 legivel na saida | Nenhum schema antigo mudou |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Terraform, uma chave | ✅ Pass | golden `tf_linha_compartilhada`: so o par muda, 3 outros intactos |
| AT-002 | Codigo | ✅ Pass | golden `codigo_conf_set` (UTF-8 antes do valor) |
| AT-003 | Do tune | ✅ Pass | golden `do_tune`: 800 -> 10, `basis` com formula e base |
| AT-004 | Sem procedencia | ✅ Pass | golden `sem_procedencia` |
| AT-005 | Linha nao confere | ✅ Pass | golden `linha_nao_confere` |
| AT-006 | Ambigua | ✅ Pass | golden `procedencia_ambigua` (lista `lib/job.py:2` e `main.tf:13`) |
| AT-007 | Nao literal | ✅ Pass | golden `valor_nao_literal` |
| AT-008 | Plano nao escreve | ✅ Pass | `test_plano_nao_escreve_nada` + hash da arvore no golden |
| AT-009 | Sandbox resolve achado | ✅ Pass | golden `resolve_achado`: SF-PY-012 em `resolved`, com validation e rollback |
| AT-010 | Diff nao aplica | ✅ Pass | golden `diff_nao_aplica`; `test_recusa_nao_cria_nada_no_disco` |
| AT-011 | Escapa da raiz | ✅ Pass | golden `escapa_da_raiz`; parse com `/etc/passwd`, `C:/`, `..` |
| AT-012 | Arquivo pulado pela copia | ✅ Pass | golden `arquivo_fora_da_copia` (SENSITIVE_NAME); `vendor/` (DIRECTORY_IGNORED) |
| AT-013 | Arvore principal intacta | ✅ Pass | hash fora de `.sparkforge/sandbox/` em todo golden e em `test_arvore_intacta_id_estavel_e_relatorio` |
| AT-014 | Idempotente | ✅ Pass | duas execucoes, mesmo `id` e mesmo relatorio |
| AT-015 | Limpeza | ✅ Pass | `test_limpeza_confinada` |

---

## Performance Notes

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| SC1 diff byte a byte | 100% dos casos de plano | 8/8 goldens | ✅ |
| SC2 ida e volta | 100% dos casos com mudanca | 4/4 (sha igual) | ✅ |
| SC4 quatro pares na linha | 1 par muda | 1 | ✅ |
| SC8 idempotencia | mesmo id e relatorio | igual | ✅ |
| SC9 sem subprocess/git/provider | 0 | 0 (teste por AST) | ✅ |
| SC10 tools | 100 | 100; com caminho 92 | ✅ |

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

**If Complete:** `/ship .claude/sdd/features/DEFINE_AUTONOMY_L1_L2.md`
