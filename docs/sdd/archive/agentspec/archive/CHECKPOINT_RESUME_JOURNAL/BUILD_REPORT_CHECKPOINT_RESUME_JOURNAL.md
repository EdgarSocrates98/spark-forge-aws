# BUILD REPORT: Checkpoint/resume/event journal (§31 P0 item 7)

> Implementation report for Checkpoint/resume/event journal (§31 P0 item 7)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHECKPOINT_RESUME_JOURNAL |
| **Date** | 2026-09-15 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_CHECKPOINT_RESUME_JOURNAL.md](./DEFINE_CHECKPOINT_RESUME_JOURNAL.md) |
| **DESIGN** | [DESIGN_CHECKPOINT_RESUME_JOURNAL.md](./DESIGN_CHECKPOINT_RESUME_JOURNAL.md) |
| **Status** | ✅ Shipped |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 12/12 (grupos do manifesto) |
| **Files Created** | `sparkforge/durable.py`, `sparkforge/journal/{__init__,record,read}.py`, `tests/test_durable.py`, `tests/test_journal.py`, `tests/test_fixtures_golden_journal.py`, 5 casos golden em `fixtures/journal/` |
| **Lines of Code** | `durable.py` ~190, `journal/` ~420; ganchos em `tools.py`, `cli.py`, `_core.py`, `case/{store,resume}.py`, `agentic/blackboard.py`, `agentic/executor/{debate_run,debate_evidence}.py` |
| **Build Time** | 1 sessão |
| **Tests Passing** | 12940 passed, 13 skipped, 0 failed (9 lotes; goldens-5 rodado de novo depois de regravar dois goldens de scan) |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Duration | Notes |
|---|------|-------|--------|----------|-------|
| 1 | `sparkforge/durable.py` | (direct) | ✅ Complete | - | `write_atomic`, `append_line`, `read_jsonl` |
| 2 | `sparkforge/journal/` | (direct) | ✅ Complete | - | Evento, raiz, `outputs`, `recording`, `estado`, `verify` |
| 3 | `case/store.py` | (direct) | ✅ Complete | - | `save_case` por `write_atomic` |
| 4 | Blackboard, `debate_run`, `debate_evidence` | (direct) | ✅ Complete | - | Appenders e leitores pelo `durable` |
| 5 | `tools.py` | (direct) | ✅ Complete | - | Gancho em `call_tool`; `_RESUME_SCHEMA` aditivo |
| 6 | `cli.py` | (direct) | ✅ Complete | - | Gancho em `_dispatch`; `journal verify` |
| 7 | `_core.py`, `case/resume.py` | (direct) | ✅ Complete | - | `resume_case` lê o journal; `journal_verify`; `handoff.md` |
| 8 | `.gitignore`, `.gitattributes` | (direct) | ✅ Complete | - | `**/.sparkforge/**/*.torn`; `fixtures/journal/** -text` |
| 9 | `tests/test_durable.py`, `tests/test_journal.py` | (direct) | ✅ Complete | - | 13 + 23 testes |
| 10 | `fixtures/journal/` + golden | (direct) | ✅ Complete | - | 5 casos, `SPARKFORGE_REGEN_JOURNAL` |
| 11 | `conftest.py`, paridade MCP, `ALLOWED_CLI_ONLY` | (direct) | ✅ Complete | - | Backstop do journal na raiz e nas fixtures |
| 12 | `CLAUDE.md`, STATUS, guia do case, referência, claims, superfície | (direct) | ✅ Complete | - | 15 alegações remedidas por id |

---

## Files Created

| File | Lines | Agent | Verified | Notes |
| ---- | ----- | ----- | -------- | ----- |
| `sparkforge/durable.py` | ~190 | (direct) | ✅ | Trava no Windows num byte além do fim do arquivo |
| `sparkforge/journal/__init__.py` | ~70 | (direct) | ✅ | `journaled()` derivado de `TOOLS`, import tardio |
| `sparkforge/journal/record.py` | ~260 | (direct) | ✅ | Regra 27: falha vira `journal: "unrecorded"` |
| `sparkforge/journal/read.py` | ~130 | (direct) | ✅ | Declara o limite da última linha |
| `tests/test_durable.py` | ~130 | (direct) | ✅ | `os.replace` sabotado em `case.yaml` e `plan.json` |
| `tests/test_journal.py` | ~260 | (direct) | ✅ | Duas portas, policy, regra 27, sem literal, resume |
| `tests/test_fixtures_golden_journal.py` | ~120 | (direct) | ✅ | `FIXTURES` literal para `test_fixtures_kind_coverage` |
| `fixtures/journal/{sem_queda,started_sem_finished,cauda_cortada,linha_removida,linha_alterada}/` | - | (direct) | ✅ | Gerados pelo próprio encadeamento do `record` |

---

## Verification Results

### Lint Check

```text
ruff check (arquivos alterados e novos)
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
a-c            2410 passed, 2 skipped   (259s)
d-e             377 passed              (89s)
f-sem-golden   1902 passed, 2 skipped   (123s)
goldens-1      1399 passed, 4 skipped   (3 fatias: 311s + 453s + 314s)
goldens-2       579 passed              (398s)
goldens-3       371 passed              (264s)
goldens-4       272 passed              (205s)
goldens-5       460 passed              (224s; 1a passada: 2 falhas em test_fixtures_golden_scan, regravadas)
g-z (2 metades) 3062 + 2108 passed, 5 skipped (253s + 361s)
total           12940 passed, 13 skipped, 0 failed
```

| Gate | Result |
|------|--------|
| `check_vnext_claims.py` | ✅ 0 divergências (15 remedidas por lista de ids: VNX-726, 640, 653, 658, 663, 666, 741, 674, 357, 358, 431, 322, 324, 327, 469) |
| `check_status_numbers.py --strict` | ✅ 0 divergências (fixtures 500 -> 505, domínios 54 -> 55) |
| `check_surface_lock.py --update` | ✅ tools +642 bytes (532 950 -> 533 592); nenhuma tool nova (103) |
| `gen_reference_docs.py` | ✅ 258 páginas, 3 regravadas e `cli/journal.md` nova |
| spec-lint (define, design) | ✅ PASS |
| `git status` depois da suíte | ✅ nenhum `journal.jsonl` novo na árvore (backstop do `conftest.py`) |

---

## Issues Encountered

| # | Issue | Resolution | Time Impact |
|---|-------|------------|-------------|
| 1 | O golden `linha_alterada` saiu `intact`: o gerador editou a ÚLTIMA linha, e nenhuma linha posterior guarda o hash dela | O caso passou a editar a linha do meio (quebra no seq 3); o limite virou teste (`test_editar_a_ultima_linha_nao_e_detectavel_pela_cadeia`), docstring do `read.py`, linha do `CLAUDE.md` e seção do guia | pequeno |
| 2 | `test_fixtures_golden_scan` (`json_solto`, `workload_na_raiz`) passou a listar `.sparkforge` em `skipped`: o `started` cria `.sparkforge/journal.jsonl` antes do scan montar o plano | Goldens regravados (`SPARKFORGE_REGEN_SCAN=1`); o diff é só a entrada `{"path": ".sparkforge", "reason": "DIRECTORY_IGNORED"}`, a mesma que qualquer segundo `scan` já mostrava | um lote a mais |
| 3 | A contagem medida de diferenças aditivas da paridade MCP subiu de 14 para 16 por transporte (`journal` e `in_flight_source` no `resume`) | Constante atualizada junto com `ALTERADAS_DEPOIS_DO_GOLDEN["sparkforge_resume"]` | nenhum |
| 4 | A prova da VNX-726 é um `python -c` de várias linhas: via `shell=True` no Windows a saída vinha vazia | O script de remediação passou a executar como o gate: `shlex.split`, sem shell | nenhum |
| 5 | `test_arvore_versionada::test_espelho_gerado_esta_em_dia_no_disco` acusa `.claude/agents/README.md` como ÓRFÃO (só local) | README tirado da árvore durante a suíte e devolvido depois do backup | nenhum |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Quebra de linha do JSONL | Manter o modo texto (`\r\n` no Windows) ou gravar `\n` binário | `\n` binário | Determinístico entre sistemas; os leitores aceitam os dois e o recibo usa `text_sha256` |
| 2 | Onde travar no Windows | Byte 0 ou byte além do fim | Byte `2**31 - 2` | `msvcrt.locking` é obrigatória: travar o byte 0 faria quem só lê receber `PermissionError` |
| 3 | Cauda sem `\n` que é JSON válido | Quarentena ou só completar | Só completar com `\n` | É um registro inteiro sem a quebra; mandá-lo para `.torn` perderia dado bom |
| 4 | `repo` apontando para diretório inexistente | Criar, ou não gravar | `unrecorded` com `raiz_inexistente` | O verbo decide se cria; o journal não cria raiz nova |
| 5 | `outputs` do `change_propose` | Ler `files` do resultado ou `outputs_unresolved` | `outputs_unresolved` | `files` não é propriedade do topo do `outputSchema`; ler forma incerta seria inventar lista |
| 6 | Resultado do verbo na porta CLI (os handlers imprimem e devolvem `int`) | Mudar 27 handlers ou capturar o último `_print` | Capturar em `_ULTIMA_SAIDA` | Um ponto só; o handler não muda |
| 7 | Journal ilegível no `resume` | Levantar ou devolver estado | `chain: "unreadable"` | `resume` nunca cai por causa do journal (regra 27) |
| 8 | `case_yaml_intacto_apos_falha` como golden | Golden ou unidade | Unidade (`test_durable.py`) | Golden não consegue sabotar `os.replace`; a prova é o monkeypatch |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| 5 goldens em vez de 6 | O cenário de `case.yaml` intacto é prova de unidade (Decisão 8) | Mesma cobertura |
| `change_propose` sem `outputs` | Decisão 5 | 7 tools com `outputs` resolvido pela tabela: `case_open`, `case_update`, 14 `collect_*`, `scan`, `receipt_emit`, `debate_start` |
| `chain` ganha `unreadable` | Decisão 7 | Enum do schema aditivo com 4 valores |
| "Qualquer edição de linha quebra a cadeia" (Decision 2 do DESIGN) | Issue 1: editar a ÚLTIMA linha não é detectável | Limite declarado e travado por teste; a última linha é protegida pelo commit |
| Goldens de scan regravados | Issue 2 | Diff só em `skipped` |

---

## Blockers (if any)

Nenhum.

---

## Acceptance Test Verification

| ID | Scenario | Status | Evidence |
|----|----------|--------|----------|
| AT-001 | Par pela CLI | ✅ Pass | `test_case_open_pela_cli_grava_o_par` |
| AT-002 | Par pelo MCP | ✅ Pass | `test_case_update_pelo_mcp_encadeia` |
| AT-003 | Verbo de leitura | ✅ Pass | `test_verbo_de_leitura_nao_grava` |
| AT-004 | Conjunto travado | ✅ Pass | `test_e_o_das_anotacoes` (27), `test_todo_verbo_do_journal_tem_porta_de_cli_pela_convencao` |
| AT-005 | Em voo | ✅ Pass | `test_em_voo_vem_do_journal`, golden `started_sem_finished` |
| AT-006 | Texto do chamador vence | ✅ Pass | `test_texto_de_quem_chama_vence` |
| AT-007 | Cadeia íntegra | ✅ Pass | golden `sem_queda` |
| AT-008 | Linha removida | ✅ Pass | golden `linha_removida` (broken_at 2), exit 1 |
| AT-009 | Linha alterada | ✅ Pass | golden `linha_alterada` (broken_at 3), `test_editar_uma_linha_do_meio_quebra_no_seq_seguinte` |
| AT-010 | Cauda cortada | ✅ Pass | golden `cauda_cortada`, `test_append_depois_da_cauda_cortada_continua_a_cadeia`, `TestAppendLine` |
| AT-011 | Linha ruim no meio | ✅ Pass | `test_linha_ruim_no_meio_levanta_com_o_numero` |
| AT-012 | Escrita atômica | ✅ Pass | `test_case_yaml_intacto_apos_falha`, `test_plan_json_intacto_apos_falha` |
| AT-013 | Journal indisponível | ✅ Pass | `test_journal_indisponivel_nao_derruba_o_verbo`, `test_cli_avisa_em_stderr` |
| AT-014 | Sem valor literal | ✅ Pass | `test_valor_sensivel_vira_hash`, `test_caminho_da_raiz_nao_aparece_no_journal` |
| AT-015 | Recusa da policy | ✅ Pass | `test_recusa_da_policy_nao_grava` |
| AT-016 | Goldens intactos | ✅ Pass | 13 goldens de debate e `receipt/uniao_debate` sem regravação |

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

**Ready for:** `/ship .claude/sdd/features/DEFINE_CHECKPOINT_RESUME_JOURNAL.md`
