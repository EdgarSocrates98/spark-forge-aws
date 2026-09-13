# BUILD REPORT: Forge Pack

> Implementation report for FORGE_PACK (§5 de `prompt_new_evo.md`)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | FORGE_PACK |
| **Date** | 2026-09-12 |
| **Author** | build-agent |
| **DEFINE** | [DEFINE_FORGE_PACK.md](../features/DEFINE_FORGE_PACK.md) |
| **DESIGN** | [DESIGN_FORGE_PACK.md](../features/DESIGN_FORGE_PACK.md) |
| **Status** | ✅ Complete |

---

## Summary

| Metric | Value |
|--------|-------|
| **Tasks Completed** | 10/10 entradas do manifesto |
| **Files Created** | 4 do modulo, 3 de teste, 1 doc, este relatorio, e 23 arquivos em `fixtures/packs/` (1 pack valido, 7 de recusa, 1 de regra morta, o golden) |
| **Lines of Code** | `sparkforge/packs/` ~430; `loader.py` refatorado (`validate_rule`); `_core` +~180, `tools.py` +~80, `cli.py` +~35 |
| **Tests Passing** | ver Verification Results |
| **Agents Used** | 0 (build direto: cada passo dependia de medida do anterior) |

---

## Task Execution with Agent Attribution

| # | Task | Agent | Status | Notes |
|---|------|-------|--------|-------|
| 1 | `rules/loader.py` | (direct) | ✅ Complete | Corpo do laco virou `validate_rule`; `load_catalog()` sem `directory` acrescenta packs (import tardio) |
| 2 | `sparkforge/packs/{__init__,manifest,load,check}.py` | (direct) | ✅ Complete | Comparador de faixa proprio; 7 recusas; `PackSet` com mapa de prefixo |
| 3 | `tests/test_packs_manifest.py`, `tests/test_packs_load.py` | (direct) | ✅ Complete | Faixa, manifesto, cada recusa, carga, verbos, knowledge, freshness |
| 4 | Schemas de `rule_id`/`id` | (direct) | ✅ Complete | `finding.schema.json` e os 2 padroes de `tools.py` |
| 5 | `_core` | (direct) | ✅ Complete | `pack_list`, `pack_check`, `knowledge_path` com `packs`, freshness por lock do pack, `rules_lookup` sem chaves `_` |
| 6 | CLI e tool | (direct) | ✅ Complete | `pack list|check`; `sparkforge_pack_list` READ_ONLY sem parametro |
| 7 | `fixtures/packs/` + golden | (direct) | ✅ Complete | `pack list` com os 8 packs ativos de uma vez; `pack check` verde, vermelho e recusado |
| 8 | Registros | (direct) | ✅ Complete | Lista, amostra real (1 ativo + 1 recusado), `SEM_CAMINHO`, `NOVAS_DEPOIS_DO_GOLDEN`, `PADROES_ALARGADOS`, manifest, parity, `spark-performance-architect` + espelhos |
| 9 | Doc, STATUS, contagens, surface, claims | (direct) | ✅ Complete | Tools 93; fixtures 432 em 49 dominios; +2 612 bytes; 28 claims por id |
| 10 | Este relatorio | (direct) | ✅ Complete | — |

---

## Verification Results

### Lint Check

```text
ruff check .  ->  All checks passed!
```

**Status:** ✅ Pass

### Type Check

N/A - o repositorio nao configura mypy.

**Status:** ⏭️ Skipped

### Tests

| Conjunto | Resultado |
|------|--------|
| Novos + registros (`test_packs_*`, golden de packs, `test_adapters_tools`, `test_harness_authorization`, paridade MCP, `test_capability_parity`, `test_agent_coverage`, `test_rules_loader`, `test_adapters_knowledge`) | 583 passed |
| Lote a-c (2a passada) | 2289 passed, 2 skipped |
| Lote d-e (2a passada) | 348 passed |
| Lote f-sem-golden (2a passada) | 1873 passed, 2 skipped |
| Lote goldens-1 (1a passada) | 1348 passed |
| Lote goldens-2 (1a passada) | 570 passed |
| Lote goldens-3 (1a passada) | 347 passed |
| Lote goldens-4 (2a passada, inclui o golden dos packs) | 254 passed |
| Lote goldens-5 (1a passada) | 410 passed |
| Lote g-z (2a passada) | 5035 passed, 5 skipped |
| **Suite inteira, nove lotes** | **12 474 passed, 0 failed, 9 skipped** |

A 1a passada teve 2 falhas (Issue 6), corrigidas; a 2a refez os lotes que as correcoes tocaram. Os goldens 1, 2, 3 e 5 nao dependem de nada editado depois deles.

### Gates

| Gate | Resultado |
|------|-----------|
| `check_vnext_claims.py` | 0 divergencias (28 remedidas pela lista de ids, em tres passadas) |
| `check_status_numbers.py --strict` | 0 divergencias |
| `check_surface_lock.py` | 0 divergencias; `total_bytes` 491 436 -> 494 048 (+2 612) |
| `check_evals.py` | 10 respostas verificadas, todas reproduzem |
| spec-lint (DEFINE, DESIGN) | PASS |

---

## Issues Encountered

| # | Issue | Resolution |
|---|-------|------------|
| 1 | `importlib.metadata` respondeu **0.4.0** com o codigo do repositorio carregado: uma dist-info velha em site-packages vencia a `egg-info` 0.5.0, que so e achada com o diretorio corrente no repo. Todo pack saia `core_incompativel` | `installed_version()` le primeiro o `version` do `pyproject.toml` ao lado do pacote (mesma precedencia de `catalog_dir()`), com regex porque o CI roda Python 3.10 sem `tomllib`; metadata e o fallback |
| 2 | A-002 do DEFINE caiu no design: tres schemas travavam `^SF-` e o golden MCP so aceita diferenca aditiva | Padrao alargado + `PADROES_ALARGADOS` exato e contado (6 por transporte) |
| 3 | A-003 caiu no design: `absent` so confere kind | Regras sinteticas por `where`/`expr` (`worker_type = G.4X`, `timeout > 1440`) |
| 4 | Arquivo vazio `fallback` apareceu na raiz durante a sessao | 0 bytes, nao rastreado, criado nesta sessao: removido |
| 5 | 21 claims movidas (tools, READ_ONLY, sem caminho 6 -> 7, `.py`, bytes, receptor 90,8 -> 90,7) | Probe e aplicacao por id; a linha do VNX-631 (`\| READ_ONLY \| 53 \| 6 \|`) conferida antes |
| 6 | Primeira passada da suite: 2 falhas. `test_agents_parity::TestNoPlatformKnowledge` pegou as chaves de escopo de runtime e de data de leitura de fonte no exemplo YAML do DESIGN (`.claude/` e diretorio de plataforma, e o gate recusa metadado de regra ali -- inclusive citado em prosa, o que derrubou o CI deste PR na primeira vez porque este relatorio o citava literalmente); `test_facts_scan::test_nenhum_modulo_varre_com_glob_cru` pegou `glob` cru em `packs/load.py` | O DESIGN aponta o arquivo de regras em vez de copia-lo; `_rule_files` passou a `iter_source_files` (denylist e teto) + `resolve_within`. Trocar por `iterdir` para escapar do gate seria a evasao que ele existe para pegar |
| 7 | A troca por `iter_source_files` moveu mais 4 claims (VNX-644, 667, 670, 674): a medida de `grep` pelo nome cresceu | Remedidas por id; 10.6 -> 10.7 na razao contra `grep` pelo nome |
| 8 | Snyk (SAST `python/PT`, low, 2 ocorrencias): o diretorio vindo de `SPARKFORGE_PACKS` chegava a `os.walk` sem que `rules/` fosse confinado -- um `rules` symlink para fora faria a varredura andar fora do pack | `_rule_files` resolve `rules/` e exige `is_relative_to(raiz do pack)` ANTES de varrer; senao, `regra_invalida`. Teste `test_rules_que_aponta_para_fora_do_pack_e_recusado` (symlink real). A suite em andamento foi parada e refeita. `snyk_send_feedback` nao foi enviado: o servidor MCP do Snyk nao conectou nesta sessao. Mais 3 claims andaram poucos bytes (VNX-644, 667, 674), remedidas por id. O Snyk continuou apontando o fluxo variavel -> `os.walk` depois do confinamento: e o proprio desenho (o operador escolhe o diretorio; nao ha base confiavel), o mesmo fluxo de `SPARKFORGE_CATALOG`. O operador decidiu ACEITAR o risco em vez de restringir os packs a uma raiz fixa; registrado em `docs/forge-pack.md`, secao "Confianca" |

---

## Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde o `id_duplicado` pode acontecer | Contra core, entre packs, dentro do pack | So dentro do pack | `SF` recusado e prefixo unico entre packs tornam as outras duas impossiveis |
| 2 | Fixture do pack | Apontar facts do core vs copiar | Copiar para dentro do pack | Pack e unidade portatil; `pack check` roda sem o repositorio do core |
| 3 | Golden do `pack list` | Caminho absoluto vs relativo | Relativo a raiz, versao do core como `<core>` | O golden nao pode depender da maquina nem da versao |
| 4 | `validate_exprs` em regra de pack | Igual ao core (opcional) vs sempre | Sempre | Regra de terceiro com `expr` quebrado morre na carga, nao no primeiro `judge` |
| 5 | Mesma URL citada por core e pack | Uma linha por origem vs primeira vence | Primeira vence (core) | `source_freshness` e chaveado por URL; o estado do core e o mais vigiado |

---

## Deviations from Design

| Deviation | Reason | Impact |
|-----------|--------|--------|
| Versao do core lida do `pyproject.toml` antes da metadata | Medido: metadata divergia do codigo carregado (Issue 1) | `docs/forge-pack.md` registra; `test_versao_e_a_do_codigo_carregado` trava |
| `pack check` de pack recusado sai 1 com a recusa, sem julgar | O design so previa pack valido | AT a mais no golden |
| Golden em `fixtures/packs/_expected/` | O golden precisa morar no dominio; o diretorio conta como fixture | STATUS com 432 |
| `rules/` do pack confinado antes da varredura | Achado do Snyk (Issue 8); o design so confinava cada arquivo | Recusa `regra_invalida` para `rules` fora do pack |

---

## Acceptance Test Verification

| ID | Status | Evidence |
|----|--------|----------|
| AT-001 | ✅ | `test_sem_variavel_o_catalogo_e_o_do_core`; suite sem a variavel |
| AT-002 | ✅ | `test_pack_acrescenta_as_regras_dele` (core + 2) |
| AT-003 | ✅ | `test_judge_ve_o_pack_e_nao_mexe_no_core` (`ACME-GOV-002` em `max_capacity_conflict`) |
| AT-004 | ✅ | `test_root_cause_ve_o_pack` |
| AT-005..AT-010 | ✅ | `test_cada_recusa`, `test_prefixo_repetido_e_pack_duplicado`, golden `pack list` com as 7 |
| AT-011, AT-012 | ✅ | `test_pack_check_verde`, `test_pack_check_vermelho_nomeia_a_regra` |
| AT-013 | ✅ | `test_knowledge_do_pack_em_chave_propria`, `test_knowledge_do_pack_confinado` |
| AT-014 | ✅ | `test_fonte_de_pack_sem_lock`; com lock, `test_fonte_de_pack_com_lock_do_pack` (`fresh`) |
| AT-015 | ✅ | `test_diretorio_inexistente_levanta` (CatalogError; exit 2 pela tool) |

---

## Final Status

### Overall: ✅ COMPLETE

- [x] All tasks from manifest completed
- [x] All verification checks pass
- [x] All tests pass (12 474 passed, 0 failed, 9 skipped, nos nove lotes de `tests/test_suite_batches.py`)
- [x] No blocking issues
- [x] Acceptance tests verified
- [ ] Ready for /ship (depois do CI do PR)

---

## Next Step

**Ready for:** `/agentspec:workflow:ship .claude/sdd/features/DEFINE_FORGE_PACK.md`
