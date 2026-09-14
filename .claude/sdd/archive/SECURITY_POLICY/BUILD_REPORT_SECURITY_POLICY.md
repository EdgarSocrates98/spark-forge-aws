# BUILD REPORT: Security Policy

> Implementation report for SECURITY_POLICY (§16 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SECURITY_POLICY |
| **Date** | 2026-09-13 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_SECURITY_POLICY.md](./DEFINE_SECURITY_POLICY.md) |
| **DESIGN** | [DESIGN_SECURITY_POLICY.md](./DESIGN_SECURITY_POLICY.md) |
| **Status** | ✅ Shipped |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 14/14 entradas do manifesto |
| **Files Created** | 7 modulos (`sparkforge/policy/`), 3 de teste, 10 casos de fixture, `.sparkforge/policy.yaml`, 1 manual, 2 paginas de referencia, este relatorio |
| **Lines of Code** | `policy/` ~480; `_core` +~140, `tools.py` +~50, `cli.py` +~60, `mcp.py` +~45, `autonomy.py` +3 |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `schema.py`, `load.py` | (direct) | ✅ Complete | Validacao manual (jsonschema custa 0,139 s de import); teste de concordancia com o JSON Schema formal |
| 2 | `decide.py` | (direct) | ✅ Complete | `dividir_comando` (composto, `$( )`, crase, subshell, `bash -c`, `sudo`/`env`/`timeout`/atribuicoes), casamento na sintaxe do Claude Code |
| 3 | `hook.py` | (direct) | ✅ Complete | ~125 ms por chamada; nao importa `sparkforge.adapters` (teste) |
| 4 | `settings.py` | (direct) | ✅ Complete | 22 regras `permissions.ask` geradas; `--check` no teste |
| 5 | `policy/mcp.py` | (direct) | ✅ Complete | `CallPolicy` com catalogo inteiro, aprovacoes da policy, raizes |
| 6 | `autonomy.py` | (direct) | ✅ Complete | `root` aceita sequencia; teste de nao-regressao com uma raiz |
| 7 | `adapters/mcp.py` | (direct) | ✅ Complete | `build_server(policy=, policy_error=)`; `main()` carrega de `CLAUDE_PROJECT_DIR`; `POLICY_INVALID` por chamada |
| 8 | CLI e tool | (direct) | ✅ Complete | `policy check|explain|sync-settings`; `sparkforge_policy_explain` READ_ONLY |
| 9 | `.sparkforge/policy.yaml` | (direct) | ✅ Complete | Destrutivos em `ask`, nada em `deny`, 3 classes pre-aprovadas |
| 10 | `.claude/settings.json` | (direct) | ✅ Complete | Hook `PreToolUse` e `permissions.ask` gerado |
| 11-12 | Testes e fixtures | (direct) | ✅ Complete | `test_policy_decide` (27), `test_policy_mcp` (6), golden do hook com 10 casos |
| 13 | `test_execution_surface` | (direct) | ✅ Complete | O comando do hook na lista fechada |
| 14 | Registros e docs | (direct) | ✅ Complete | Tool nova (90 com caminho), `sf-security-reviewer`, manual, referencia, THREAT-MODEL T-024, AUTHORIZATION-CHAIN, CURRENT-HARNESS-GAP (§41 EXISTE), STATUS, contagens 98, surface +2 023, 27 claims + VNX-792 |

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
| Policy, MCP, hook, registros de tool nova (18 arquivos) | 913 passed; depois da correcao Snyk, 251 passed nos afetados |
| Lote a-c | 2302 passed, 2 skipped |
| Lote d-e | 364 passed |
| Lote f-sem-golden | 1886 passed, 2 skipped |
| Lote goldens-1 | 1348 passed |
| Lote goldens-2 | 579 passed |
| Lote goldens-3 | 358 passed |
| Lote goldens-4 (inclui o golden da policy) | 266 passed |
| Lote goldens-5 | 422 passed |
| Lote g-z | 5106 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 631 passed, 0 failed, 9 skipped** |

A 1a passada foi parada para a correcao do Snyk; a 2a rodou os nove lotes depois dela, com o `.claude/agents/README.md` (orfao local) fora da arvore.

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (27 remedidas por id + VNX-792 com prova `artifact`) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | `total_bytes` 507 694 -> 509 717 (+2 023) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| `gen_reference_docs.py --check` | em dia |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | O `PreToolUse` so decide `allow`/`deny` (documentacao oficial; busca literal por `"ask"`: NOT FOUND) | `ask` realizado por `permissions.ask` gerado; decisao do operador no brainstorm |
| 2 | `authorize()` exige aprovacao para LOCAL_MUTATION, CLOUD_READ, CLOUD_MUTATION e DESTRUCTIVE; uma policy sem aprovacoes recusaria tudo que o MCP faz | Policy padrao pre-aprova as tres classes em uso |
| 3 | Carregar a policy dentro do `call_tool` mudaria todos os testes de tools | Carga na fronteira do servidor (`main()`) |
| 4 | `jsonschema` custa 0,139 s de import; o hook passaria de 0,2 s | Validacao manual e teste de concordancia |
| 5 | INV-007 recusa parametro de tool chamado `command` | Parametro `bash_text` (so comparado como texto) |
| 6 | Gate de lastro: o "2" de "exit 2" em texto novo de `docs/harness/` virou alegacao, e a linha da tabela §41 que passou a dizer EXISTE virou alegacao de capacidade | Texto por extenso; VNX-792 com prova `artifact` (hook + golden). O `--seed` reescrevia o manifesto inteiro: entrada copiada a mao |
| 7 | 27 claims movidas; tres saltos grandes (VNX-658 28 525 -> 365 052, VNX-666, VNX-741) porque `_core.py` passou a citar `tool_class` e entrou no denominador de "ler os arquivos" | Medidas reais, remedidas por id |
| 8 | `sha2116` em `AUTHORIZATION-CHAIN.md` (defeito antigo, ja na `main`) | Corrigido para `sha256` |
| 9 | Snyk (python/PT, baixa, 2x): `CLAUDE_PROJECT_DIR` fluindo para a leitura do `policy.yaml` no hook e no servidor MCP | `raiz_do_projeto()` resolve a raiz e exige diretorio existente; o arquivo e confinado por `resolve_within` (symlink que escape vira `PolicyError`); teste novo `test_raiz_que_nao_e_diretorio_e_recusada`. A suite da 1a passada foi parada para a correcao nao mudar a arvore no meio. `snyk_send_feedback` nao foi enviado: o servidor Snyk nao conectou nesta sessao |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Matcher do hook | `Bash\|Edit\|Write` vs incluir `MultiEdit`/`NotebookEdit` | Incluir | Escrita por outra tool nao pode escapar da regra de caminho |
| 2 | stdin ilegivel | Passar vs bloquear | Bloquear | Sem entrada nao ha decisao |
| 3 | `permissions.ask` | Mesclar com regras a mao vs a lista inteira ser da policy | Da policy | Uma fonte; `--check` pega edicao a mao |
| 4 | Tools negadas em `ask` | Manter vs tirar | Tirar | Tool negada nao pede confirmacao, e recusada |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Parametro da tool `bash_text`, nao `command` | INV-007 | Nenhum no contrato |
| Matcher com `MultiEdit` e `NotebookEdit` | Decisao 1 acima | Mais cobertura |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001, AT-002, AT-003 | ✅ | `test_policy_do_repositorio_e_valida_e_pede_ask_nos_destrutivos`, `test_bash_mais_estrita_vence`, `test_dividir_comando` |
| AT-004 | ✅ | golden `deny_com_involucro`, `deny_composto`, `deny_em_substituicao` |
| AT-005 | ✅ | golden `comum_passa`, `ask_nao_bloqueia` |
| AT-006 | ✅ | golden `deny_escrita_catalogo` |
| AT-007 | ✅ | golden `policy_invalida`; `test_servidor_sem_policy_e_com_policy_invalida` |
| AT-008 | ✅ | golden `sem_policy`; `test_sem_arquivo_e_none` |
| AT-009 | ✅ | `test_settings_do_repositorio_em_dia_com_a_policy`, `test_regras_ask` |
| AT-010 | ✅ | `test_tool_negada_nao_roda_o_handler` |
| AT-011 | ✅ | `test_caminho_fora_da_raiz_e_recusado_e_extra_root_libera` |
| AT-012 | ✅ | `test_policy_padrao_pre_aprova_as_classes_de_hoje`, `test_policy_padrao_nao_recusa_leitura_dentro_do_repo` |
| AT-013 | ✅ | `test_hook_e_rapido`, `test_hook_nao_importa_o_catalogo_de_tools` (medido ~125 ms) |

**Nao provado aqui:** o hook e as regras `ask` numa sessao real do Claude Code (o golden roda o hook por subprocess com o stdin documentado).

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 631 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [x] Ready for /ship (CI do PR #64: 5 jobs verdes, `test (3.10)` pendente no ship, liberado pelo operador)

---

## Next Step

**Shipped:** ver [SHIPPED_2026-09-13.md](./SHIPPED_2026-09-13.md)
