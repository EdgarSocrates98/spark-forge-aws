# BUILD REPORT: Doctor e Scan

> Implementation report for DOCTOR_SCAN (§22 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | DOCTOR_SCAN |
| **Date** | 2026-09-13 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_DOCTOR_SCAN.md](../features/DEFINE_DOCTOR_SCAN.md) |
| **DESIGN** | [DESIGN_DOCTOR_SCAN.md](../features/DESIGN_DOCTOR_SCAN.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 15/15 entradas do manifesto |
| **Files Created** | 4 modulos (`sparkforge/scan/{__init__,plan,summary}.py`, `sparkforge/doctor.py`), 3 de teste, 7 casos de fixture, 1 manual, este relatorio |
| **Lines of Code** | `scan/plan.py` ~200, `scan/summary.py` ~55, `doctor.py` ~160; `_core` +~200, `tools.py` +~130, `cli.py` +~60 |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1-3 | `sparkforge/scan/` | (direct) | ✅ Complete | Plano puro, `KIND_PARA_ANALYZE` fechado, seis recusas, resumo |
| 4 | `sparkforge/doctor.py` | (direct) | ✅ Complete | `Checagem`, nove `avaliar_*` puros, `resumo` |
| 5 | `_core.scan`, `_core.doctor` | (direct) | ✅ Complete | Um analyze por arquivo, `fuse` + `judge`, escrita em `.sparkforge/scan/`, SARIF pelo `report_github_write`; doctor sonda as portas |
| 6-7 | CLI e tools | (direct) | ✅ Complete | `scan [raiz] --dry-run --format --fail-on --glue...`, `doctor --repo --online`; `sparkforge_scan` `_WRITE_IDEMPOTENT`, `sparkforge_doctor` `_READ_ONLY` |
| 8-11 | Testes e fixtures | (direct) | ✅ Complete | `test_scan_plan` (12), `test_doctor` (17), golden com 7 casos + SC1, SC4, dry-run |
| 12 | `sf-inventory` | (direct) | ✅ Complete | Passo 0 (doctor) e passo 5 (plano do scan) + espelhos |
| 13 | Registros | (direct) | ✅ Complete | Lista, amostras reais, FAILABLE, writers, contagem com caminho 87 -> 89, `NOVAS_DEPOIS_DO_GOLDEN`, manifest, parity |
| 14 | Manual e referencia | (direct) | ✅ Complete | `docs/guia/usos/scan-e-doctor.md`; referencia regerada |
| 15 | STATUS, contagens, surface, claims | (direct) | ✅ Complete | Tools 97; fixtures 448 em 52 dominios; +4 693 bytes; 28 claims por id |

---

## Verification Results

### Lint Check

```text
ruff check sparkforge tests scripts  ->  All checks passed!
```

### Type Check

N/A - o repositorio nao configura mypy.

### Tests

| Conjunto | Resultado |
|------|--------|
| Scan, doctor e registros de tool nova (14 arquivos) | 797 passed antes das duas correcoes de mensagem; 287 passed depois, nos afetados |
| Lote a-c (2a passada) | 2299 passed, 2 skipped |
| Lote d-e | 364 passed |
| Lote f-sem-golden | 1886 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 (2a passada) | 579 passed |
| Lote goldens-3 | 358 passed |
| Lote goldens-4 | 254 passed |
| Lote goldens-5 (inclui o golden do scan) | 422 passed |
| Lote g-z | 5073 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 583 passed, 0 failed, 9 skipped** |

A 1a passada foi morta por falta de memoria no lote goldens-2; antes disso, o a-c teve 1 falha LOCAL (`test_espelho_gerado_esta_em_dia_no_disco` acusando `.claude/agents/README.md`, arquivo nao rastreado do scaffolding do agentspec, como orfao do espelho; nao existe no CI). A 2a passada rodou os lotes restantes com o README fora da arvore.

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (28 remedidas pela lista de ids) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | `total_bytes` 503 001 -> 507 694 (+4 693) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| `gen_reference_docs.py --check` | em dia (248 paginas) |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `code_status` passa por `garantir_frescor`, que grava a conferencia no indice quando ele existe (por isso `sparkforge_code_status` esta entre as tools que escrevem). O doctor chamando-o seria `_READ_ONLY` mentiroso | O doctor so confere a EXISTENCIA do indice e aponta `sparkforge code status --root .` para o frescor; teste mede o `mtime_ns` do banco antes e depois |
| 2 | O caso `analyze_falhou` montado com dump Iceberg malformado nao falhava | Medido: Iceberg, Athena e EMR aceitam dump malformado como `*.unresolved`; CloudWatch, parquet-footer, IAM, grants e resource link levantam. O fixture passou a usar grants de Lake Formation |
| 3 | `pack_list` devolve `env` com o NOME da variavel, sempre; o doctor dava `ok` com 0 packs | `skip` quando nao ha pack ativo nem recusado |
| 4 | `unlock` do indice ensinava `code init --repo .`; a flag e `--root` | Corrigido nos tres `unlock` |
| 5 | Mensagem de raiz inexistente sem comando que resolve (`test_error_message_is_actionable`) | Mensagem com `sparkforge scan <raiz> --dry-run` / `sparkforge doctor --repo <raiz>` |
| 6 | `_REPORT_DIR` inexistente no `_core` (pego antes de rodar) | Usa o retorno de `report_github_write` |
| 7 | 28 claims movidas (tools 95 -> 97, READ_ONLY, com caminho 87 -> 89, contagens de `.py` e bytes, receptor 90,6 -> 90,5) | Probe e aplicacao por id |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Runs do Glue no plano | Um analyze por arquivo vs por pasta+job | Pasta+job | `analyze glue-job-runs` exige diretorio e `--job-name` |
| 2 | Frescor do indice no doctor | `code_status` vs so existencia | So existencia | Manter a tool honestamente `_READ_ONLY` |
| 3 | `--fail-on` sem `--format sarif` | Exigir SARIF vs valer nos dois modos | Vale nos dois | Gate calculado dos findings, mesma semantica do `report github` (P1 inclui P0) |
| 4 | Runtime no golden | Manter `detected_from` vs tirar | Tirar so no golden | Depende do caminho da copia em `tmp_path` |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Checagem `indice_de_codigo` nao confere frescor | Issue 1 | `ok` com `unlock` para `code status` quando o indice existe |
| Fixture `analyze_falhou` com grants, nao Iceberg | Issue 2 | Nenhum no contrato |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | golden `misto` (7 entradas, 9 findings com `SF-LF-005`); `test_scan_igual_ao_fluxo_a_mao` |
| AT-002 | ✅ | `test_dry_run_nao_grava` |
| AT-003 | ✅ | golden `json_solto`; `test_json_solto_e_recusado_sem_farejar` |
| AT-004 | ✅ | golden `sha256_divergente`; `test_sha256_divergente_e_ausente` |
| AT-005 | ✅ | golden `kind_sem_analyze`; `test_kind_sem_analyze` |
| AT-006 | ✅ | golden `analyze_falhou`; `test_analyze_que_falha_nao_derruba_os_outros` |
| AT-007 | ✅ | `test_glue_job_run_tira_o_job_do_source_e_agrupa_por_pasta`; golden `misto`, `exige_job_name` |
| AT-008 | ✅ | `test_sarif_igual_ao_report_github` (exit 1 com P0) |
| AT-009 | ✅ | `test_cli_sai_0_sem_fail`, `test_doctor_de_verdade_tem_as_nove_checagens` |
| AT-010 | ✅ | `test_cli_sai_1_com_catalogo_invalido` |
| AT-011 | ✅ | `test_extras`, `test_mcp`, `test_credencial_aws` |
| AT-012 | ✅ | `test_credencial_aws` (sem credencial -> warn, sem rede) |
| AT-013 | ✅ | `test_tool_nunca_recebe_online`; amostra real em `test_adapters_tools` |

**Nao provado aqui:** `doctor --online` contra a AWS (sem boto3 nem credencial neste ambiente).

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 583 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Ready for:** `/ship .claude/sdd/features/DEFINE_DOCTOR_SCAN.md`
