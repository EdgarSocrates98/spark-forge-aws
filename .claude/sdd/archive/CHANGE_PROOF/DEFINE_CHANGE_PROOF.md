# DEFINE: Change Proof

> Para cada recomendacao que o operador aplicou, as obrigacoes de prova que os eixos da regra e a propria regra impoem, e o desfecho de cada uma -- `refuted`, `not_refuted`, `inconclusive` ou `unproven`, nunca "provado" --, compostas sobre os veredictos que `funcval` e `benchmark` ja produzem e sobre o `judge` rodado nos facts do depois.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | CHANGE_PROOF |
| **Date** | 2026-09-12 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O SparkForge recomenda mudancas com `validation` e `rollback` em prosa -- 479 itens em 155 regras --, e nenhum verbo diz, depois que o operador aplicou uma delas, se o resultado continuou o mesmo, se o que ela deveria melhorar piorou, ou se o problema que a motivou sumiu. Os comparadores que responderiam (`funcval`, `benchmark`) e as nove regras de veredito (`SF-FVAL-001..005`, `SF-BENCH-001..004`) ja existem, mas nada os liga a recomendacao que motivou a mudanca.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro que aplicou a recomendacao | Mediu antes e depois com `funcval compare` e `benchmark` | Nao tem como saber, pela recomendacao, qual obrigacao foi medida, qual refutou e qual ficou sem medida |
| Revisor do PR da mudanca | Le a saida no PR | Recebe "funcionou" sem saber se a regra que recomendou deixou de disparar |
| `sf-verifier` | Tenta refutar achados P0/P1 | Nao tem como refutar uma mudanca aplicada |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G1: modulo puro `sparkforge/proof/` que recebe findings aplicados, veredictos ja julgados, facts de comparacao e o resultado do `judge` sobre o depois, e devolve as obrigacoes e os desfechos; nao importa `adapters` nem provider |
| **MUST** | G2: `rules/catalog/proof_axes.yaml` (sem chave `rules:`), versionado, com: (a) para cada um dos 23 eixos de `action.moves`, a fonte (`funcval`, `bench` ou `none`), a medida de bench quando houver, `improves_when` (`decreases`) para eixo de bench, `proxy` quando a medida nao e o eixo, e `unlock` (a medida que destravaria) quando a fonte e `none`; (b) a chave estavel por tipo de subject |
| **MUST** | G3: obrigacao de resolucao para todo finding de `--applied`: `judge` com `return_skipped=True` sobre `--after-facts`; dispara de novo na mesma chave estavel -> `refuted`; regra em `skipped` -> `unproven` com os kinds que faltam; avaliada e nao disparou -> `not_refuted`; tipo de subject sem chave declarada -> `inconclusive` (`subject_sem_chave_estavel`) |
| **MUST** | G4: obrigacao de correcao para eixo `correctness.*`: algum `SF-FVAL-001..004` nos veredictos -> `refuted` (com os rule_ids); `SF-FVAL-005` -> `inconclusive`; sem `funcval.analyzed` na uniao -> `unproven` (`funcval compare`) |
| **MUST** | G5: obrigacao de melhoria para eixo com fonte `bench`, com precedencia fixa: `SF-BENCH-001`/`004`, `bench.unresolved` da medida ou percentual omitido -> `inconclusive`; senao `SF-BENCH-002` (eixo de tempo) ou `SF-BENCH-003` (eixo de spill) ou delta contra `improves_when` -> `refuted`; senao delta a favor -> `not_refuted`; sem `bench.analyzed` -> `unproven` (`benchmark`) |
| **MUST** | G6: com mais de um finding em `--applied`, obrigacoes de bench -> `inconclusive` (`attribution_shared`); resolucao e correcao seguem por finding |
| **MUST** | G7: desfechos so `refuted`, `not_refuted`, `inconclusive`, `unproven`; `refused` fixo com `proven` e `gain_estimate`; o delta de bench repassado como medido, com `proxy` quando o mapa declara |
| **MUST** | G8: finding de `--applied` ausente de `--findings` -> `unresolved` (`applied_nao_encontrado`); finding fora de `--applied` fica fora da prova |
| **MUST** | G9: CLI `sparkforge proof --findings F --facts U [--facts ...] --after-facts A [--after-facts ...] --applied RULE[:symbol] ...` e tool `sparkforge_proof` (`_READ_ONLY`, declara `findings_path`, `facts_path`, `after_facts_path`) |
| **SHOULD** | G10: `sf-verifier` ganha a checagem 7 ("a mudanca aplicada se sustentou?"); `parity.yaml` ganha "prove what an applied change did and did not break" |
| **SHOULD** | G11: teste do mapa: todo eixo usado em `moves` tem entrada; toda fonte e medida apontam para kind em algum `EMITTED_KINDS`; toda regra de veredito citada existe no catalogo |
| **COULD** | G12: `docs/change-proof.md` com os desfechos, a precedencia, a chave estavel e a lista dos eixos sem comparador |

---

## Success Criteria

- [ ] SC1: golden em `fixtures/proof/` com um caso por desfecho e por fonte: resolucao `not_refuted`, `refuted` e `unproven`; correcao `refuted` (`count_diverged`) e `inconclusive` (`partial_coverage`); melhoria `not_refuted` (`clean_improvement`), `refuted` (`regression_slower`) e `inconclusive` (`different_input_volume`, que dispara `SF-BENCH-001` e `002` e sai `inconclusive`); `attribution_shared` com dois findings aplicados.
- [ ] SC2: nenhuma saida do corpus contem a string `proven` fora de `refused`; toda obrigacao `unproven` tem `unlock` nao vazio.
- [ ] SC3: mudar so `line`, `col`, `snippet`, `stage_id`, `job_run_id` ou `event` do subject do finding do depois nao muda o desfecho da resolucao.
- [ ] SC4: o mapa cobre os **23** eixos de `moves` medidos em 2026-09-12; a distribuicao da prova sobre o catalogo sai datada: 61 regras com eixo avaliavel, 43 so com eixo `unproven`, 51 sem eixo (todas com resolucao).
- [ ] SC5: `faster_but_spilling` sai `refuted` no eixo `shuffle.spill_bytes` e `not_refuted` no `runtime.wall_clock` (com `proxy`).
- [ ] SC6: a tool valida contra o proprio schema com amostra real; os registros de tool nova e de dominio novo de fixture atualizados; `check_surface_lock --update` com o crescimento declarado no commit; claims remedidas pela lista de ids.
- [ ] SC7: gates (`check_vnext_claims`, `check_status_numbers --strict`, `check_surface_lock`, `check_evals`, `ruff`) e suite por lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Resolucao | Antes `collect_unbounded` (SF-PY-002), depois com o `collect()` removido | `proof --applied SF-PY-002` | resolucao `not_refuted`, com a sentinela do depois em `evidence` |
| AT-002 | Nao resolveu | O depois ainda com `collect()`, em outra linha | idem | resolucao `refuted` (a chave estavel ignora a linha) |
| AT-003 | Depois sem artefato | `--after-facts` sem facts de PySpark | idem | resolucao `unproven`, com os kinds que faltam |
| AT-004 | Correcao quebrada | Uniao com os facts de `funcval/count_diverged`, regra com `correctness.write_result` | idem | correcao `refuted`, `SF-FVAL-001` citado |
| AT-005 | Validacao parcial | Uniao com `funcval/partial_coverage` | idem | correcao `inconclusive` |
| AT-006 | Sem funcval | Uniao sem `funcval.analyzed` | idem | correcao `unproven`, `unlock` = `funcval compare` |
| AT-007 | Melhoria | Uniao com `bench/clean_improvement`, regra com `runtime.wall_clock` | idem | melhoria `not_refuted`, `proxy: task_ms_nao_e_wall_clock` |
| AT-008 | Piorou | Uniao com `bench/regression_slower` | idem | melhoria `refuted` |
| AT-009 | Comparacao invalida | Uniao com `bench/different_input_volume` (SF-BENCH-001 e 002) | idem | melhoria `inconclusive`, nao `refuted` |
| AT-010 | Ganho com spill | Uniao com `bench/faster_but_spilling`, regra com os dois eixos | idem | spill `refuted`, tempo `not_refuted` |
| AT-011 | Duas mudancas | `--applied` com dois findings | idem | melhoria `inconclusive` (`attribution_shared`); resolucao por finding |
| AT-012 | Eixo sem fonte | Regra com `dependency.delivered_artifacts` | idem | eixo `unproven` com o `unlock` do mapa |
| AT-013 | Aplicado inexistente | `--applied SF-NAO-EXISTE` | idem | `unresolved` com `applied_nao_encontrado`, exit 0 |
| AT-014 | Entrada invalida | `--after-facts` ausente | idem | exit 2 com a dica |

---

## Out of Scope

- Qualquer desfecho `proven`; estimativa de ganho.
- Comparador novo para os 43 eixos sem fonte (custo, layout de storage, versao de engine, artefato entregue).
- Aplicar a mudanca em sandbox (autonomia L2, §15).
- Security Validation e Cost Validation como etapas proprias do §20.
- Acoplar a prova ao Execution Receipt.
- Mudar `Finding`, as regras do catalogo ou os comparadores existentes.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regras 13 e 30 | Nenhum ganho estimado, nenhum "provado" |
| Technical | Regra 12 | Melhoria so entre as execucoes que o operador mediu |
| Technical | Regra 20 | `unproven` e `unresolved` sempre com nome |
| Technical | Regra 26 | Uma tool nova move a superficie |
| Technical | `action.direction` e o sentido da ACAO, nao do eixo | A direcao de melhoria mora no mapa (`improves_when`), nao na regra |
| Technical | Caso real nunca entra em arquivo | Fixtures sinteticas derivadas das existentes |
| Technical | Dominio novo de fixture | `FIXTURES = ROOT / "fixtures" / "proof"` literal no modulo golden |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/proof/`; `rules/catalog/proof_axes.yaml`; `adapters/_core.py`, `cli.py`, `tools.py`; `agents/executors/sf-verifier.md` e espelhos; `parity.yaml`; `manifest.json`; `fixtures/proof/`; `tests/test_proof_*.py`, `tests/test_fixtures_golden_proof.py` | Nenhum recurso de nuvem |
| **KB Domains** | Validacao funcional (`funcval`), benchmark (`bench.*`), motor de regras (`judge`, `skipped`) | Veredictos reusados, nunca reimplementados |
| **IaC Impact** | None | — |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | `action.direction` diz para que lado o eixo deve andar | A decisao 8 do brainstorm estaria certa | [x] Errada: nas 26 regras com eixo de bench, a direcao e 13 `replace`, 8 `add`, 4 `decrease`, 1 `remove`; a direcao de melhoria vai para o mapa (G2) |
| A-002 | As fixtures de `bench/` e `funcval/` disparam os veredictos esperados | Os casos do golden precisariam de outras fixtures | [x] `regression_slower` -> SF-BENCH-002; `different_input_volume` -> 001 e 002; `faster_but_spilling` -> 003; `most_stages_renamed` -> 004; `count_diverged` -> SF-FVAL-001; `schema_diverged` -> 002; `duplicate_key_appeared` -> 003; `aggregate_*_diverged`/`outside_tolerance` -> 004; `partial_coverage` -> 005 |
| A-003 | `run_judge(..., return_skipped=True)` devolve `skipped` com os kinds que faltam | A resolucao nao distinguiria muda de resolvida | [x] `adapters/_core.py:3363` e `diagnosis/root_cause.py:297-307` (`missing`) |
| A-004 | `collect_unbounded` dispara SF-PY-002 com subject `source_location` e `symbol` estavel | O caso de resolucao precisaria de outra regra | [x] SF-PY-002 no golden; o `symbol` e a funcao que contem a chamada |
| A-005 | `bench.unresolved` e o percentual omitido sao distinguiveis por medida | O `inconclusive` da melhoria seria so por regra | [x] `bench.unresolved` carrega `measure` e `reason`; o percentual some quando a medida nao e `usable` (`facts/benchmark.py:_compare`) |
| A-006 | Os facts de comparacao (`funcval.*`, `bench.*`) entram na uniao `--facts` e o `judge` sobre ela produz os veredictos | Os veredictos precisariam de outra entrada | [x] A prova julga a uniao e o depois ela mesma (DESIGN Decision 1) |
| A-007 | `one_side_missing` e `migracao_entre_runtimes` nao disparam regra | Precisam de desfecho proprio | [x] Nenhuma regra dispara; o DESIGN decide se viram `inconclusive` pelo `bench.unresolved` |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | 479 itens em prosa, 9 regras de veredito sem ligacao, medido |
| Users | 3 | Tres papeis, cada um com uma saida |
| Goals | 3 | 12 metas MoSCoW, cada uma ligada a SC ou AT |
| Success | 3 | Contagens exatas (23 eixos, 61/43/51 regras, casos por desfecho) |
| Scope | 2 | A-005 e A-006 ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-005 e A-006 sao de implementacao.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | define-agent | Versao inicial, a partir de `BRAINSTORM_CHANGE_PROOF.md`; A-001 corrige a decisao 8 do brainstorm (direcao de melhoria no mapa, nao na `action`) e fixa a precedencia `inconclusive` > `refuted` do bench |
| 1.1 | 2026-09-12 | design-agent | A-005 e A-006 fechadas; `SF-BENCH-001` confunde o eixo `scan.bytes_read` (DESIGN Decision 3) |
| 1.2 | 2026-09-12 | ship-agent | Shipped and archived (PR #56) |

---

## Next Step

**Shipped:** ver [SHIPPED_2026-09-12.md](./SHIPPED_2026-09-12.md)
