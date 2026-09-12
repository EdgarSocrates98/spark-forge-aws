# DEFINE: Simulate (what-if estrutural)

> `sparkforge simulate` altera o valor de propriedades de configuracao que ja existem numa camada nomeada, passa os dois lados pelo mesmo pipeline (tira derivados, rederiva, redetecta runtime, julga) e diz quais findings somem, quais aparecem e quais regras mudam de estado -- sem prever medida nenhuma. Antes, o passo 0 liga a derivacao de timeout, que nao tinha porta de producao.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SIMULATE |
| **Date** | 2026-09-12 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

Para saber o que uma mudanca de configuracao faria com os achados, o operador hoje precisa aplica-la, extrair de novo e rejulgar. 29 regras leem configuracao diretamente e 20 leem kinds derivados dela, e nenhum verbo responde, antes de mudar, "se eu trocar esta propriedade neste arquivo, o que some e o que aparece". Alem disso, a derivacao de timeout (`extract_timeout_diagnosis`) nao tem porta de producao: `spark.timeout.*` so existe nos testes, e as 2 regras que o leem nunca disparam num case real.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Engenheiro que vai mudar um job | Edita Terraform, `spark.conf.set` ou configuracao de EMR | Descobre a consequencia estrutural so depois de aplicar e rejulgar |
| Quem usa `tune` | Recebe um valor proposto de configuracao | Nao sabe que regras aquele valor faria disparar ou calar |
| Operador de um case com timeout | Le os achados de timeout | As regras de timeout nunca aparecem, porque o fact que elas leem nao e produzido |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | G0 (passo 0): `facts/fusion.py::fuse()` passa a chamar `extract_timeout_diagnosis`, do mesmo jeito que ja chama `build_lakeformation`; `sparkforge fuse` passa a produzir `spark.timeout.*` quando ha os facts de origem |
| **MUST** | G1: modulo puro `sparkforge/simulate/` com o mapa de camadas, a alteracao dos facts, a remocao dos derivados e a comparacao pela chave estavel (`proof.keys.stable_key`); o `judge` e a rederivacao sao chamados pelo adapter |
| **MUST** | G2: `--set <camada>:<chave>=<valor>`, repetivel; camadas `tf` (`tf.spark_conf`, `tf.attribute`), `code` (`pyspark.conf_set`), `effective` (`spark.conf_effective`), `emr` (`emr.configuration`, `emrs.configuration`, `emrc.configuration`); prefixo obrigatorio; camada desconhecida ou sem prefixo -> exit 2 |
| **MUST** | G3: alteracao so em fact existente cujo `attrs.key` bate: `attrs.value` recebe o valor como texto; se o fact tinha `measures.value`, ele recebe o valor convertido em numero; valor nao numerico para medida numerica -> recusa `valor_nao_numerico_para_medida`; chave ausente na camada -> recusa `chave_ausente_na_camada`; qualquer recusa -> exit 2, sem simulacao parcial |
| **MUST** | G4: os dois lados pelo mesmo pipeline: tira os kinds de `fusion`, `lakeformation` e `timeout_diagnosis`, rederiva com `fuse`, detecta o runtime a partir dos proprios facts, julga com `return_skipped=True` |
| **MUST** | G5: saida com `changes` (por `--set`: valores antigos, novo, facts alterados), `disappeared` e `appeared` (por `(rule_id, chave estavel)`, com o subject), `persisted_count`, `skipped_delta` (regra que muda entre avaliada e pulada, com a razao), `runtime` antes e depois |
| **MUST** | G6: `refused` fixo com `performance_prediction`, `dependency_incompatibility` (-> `migration_assess`) e `execution_graph` |
| **MUST** | G7: CLI `sparkforge simulate --facts U [--facts ...] --set camada:chave=valor [--set ...]` com as flags de runtime do `judge`; tool `sparkforge_simulate` `_READ_ONLY` declarando `facts_path` |
| **SHOULD** | G8: dono = o coordenador que declara `tune`; `parity.yaml` com "show what a configuration change would structurally move" |
| **COULD** | G9: `docs/simulate.md` com as camadas, a regra de alteracao, o pipeline e as recusas |

---

## Success Criteria

- [ ] SC0: `sparkforge fuse` sobre os facts de `eventlog/broadcast_timeout_stage_failure` produz `spark.timeout.*`; os **7** goldens de `fixtures/fusion/` ficam byte a byte (medido: nenhum tem fact de event log).
- [ ] SC1: `fixtures/simulate/` com um caso por consequencia -- regra some, regra aparece, runtime muda, derivado de Lake Formation, timeout -- mais as recusas e o caso de simetria (sem `--set`, `disappeared` e `appeared` vazios).
- [ ] SC2: nenhuma saida do corpus traz medida prevista; `refused` sempre com os tres itens.
- [ ] SC3: mudar so `line`/`snippet` do subject nao cria diferenca (chave estavel).
- [ ] SC4: a tool valida contra o schema com amostra real; registros de tool nova e dominio novo; surface lock com o crescimento declarado; claims por lista de ids.
- [ ] SC5: gates e suite por lotes com 0 falhas.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Regra some | `terraform/bookmarks_with_concurrency` (SF-GLUE-003 le `max_concurrent_runs` por `measures.value > 1`) | `--set tf:max_concurrent_runs=1` | SF-GLUE-003 em `disappeared`; `measures.value` alterado para 1 |
| AT-002 | Regra aparece | Um caso em que o valor novo faz uma regra disparar (o DESIGN escolhe) | `--set` correspondente | a regra em `appeared` |
| AT-003 | Runtime muda | `--set tf:glue_version=<outra>` | simulate | `runtime` antes e depois diferentes; regras com `runtime_scope` em `appeared`/`disappeared` ou `skipped_delta` |
| AT-004 | Derivado de Lake Formation | Uma fixture de `infra_code` com FGAC e SF-LF | `--set tf:--enable-lakeformation-fine-grained-access=<outro>` | `lakeformation.*` rederivado; a SF-LF correspondente muda |
| AT-005 | Timeout | `eventlog/broadcast_timeout_stage_failure` | `--set effective:spark.network.timeout=<abaixo do heartbeat>` | SF-TIMEOUT-002 em `appeared` (depende de G0) |
| AT-006 | Simetria | Qualquer uniao | simulate sem mudanca efetiva (valor igual ao atual) | `disappeared` e `appeared` vazios |
| AT-007 | Chave ausente | `--set tf:nao_existe=1` | simulate | exit 2, `chave_ausente_na_camada` |
| AT-008 | Sem prefixo | `--set max_concurrent_runs=1` | simulate | exit 2 |
| AT-009 | Nao numerico | `--set tf:max_concurrent_runs=muitos` | simulate | exit 2, `valor_nao_numerico_para_medida` |

---

## Out of Scope

- Mudar versao de runtime como eixo proprio (`migration_assess` ja faz); aplicar recomendacao (`--apply`); dependencias incompativeis; grafo de execucao; qualquer medida prevista; criar chave nova numa camada.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regras 12, 13 e 30 | Nenhuma medida prevista |
| Technical | Regra 19 | Camada nomeada, nunca "todas" |
| Technical | Regra 26 | Tool nova move a superficie |
| Technical | `Fact.id` inclui `measures` | Alterar `measures.value` muda o id; a comparacao e pela chave estavel |
| Technical | Caso real nunca entra em arquivo | Casos sobre fixtures sinteticas existentes |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/facts/fusion.py` (G0); `sparkforge/simulate/`; `adapters/_core.py`, `cli.py`, `tools.py`; executor/coordenador do `tune`; `parity.yaml`; `manifest.json`; `fixtures/simulate/`; `tests/test_simulate_*.py`, `tests/test_fixtures_golden_simulate.py` | Nenhum recurso de nuvem |
| **KB Domains** | Motor de regras (`judge`, `skipped`), derivacao (`fuse`, Lake Formation, timeout), configuracao Glue/Spark/EMR | — |
| **IaC Impact** | None | — |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Todo kind de configuracao guarda a propriedade em `attrs.key`/`attrs.value` | O `--set` precisaria de um adaptador por kind | [x] Parcial: em `tf.attribute`, `attrs.value` e texto e `measures.value` existe quando o valor e numero; SF-GLUE-003 le `measures.value` (G3 cobre) |
| A-002 | O passo 0 nao muda nenhum golden de `fusion` | Regenerar goldens com a razao | [x] 0 de 7 goldens de `fixtures/fusion/` tem fact de event log |
| A-003 | So `eventlog/broadcast_timeout_stage_failure` tem `spark.network.timeout` e `spark.executor.heartbeatInterval` em `spark.conf_effective` | O caso de timeout precisaria de outra fixture | [x] medido |
| A-004 | Ha fixture com FGAC declarado e SF-LF disparada | O caso de Lake Formation precisaria de fixture nova | [x] 6 de `infra_code` + 1 de `lakeformation` |
| A-005 | `extract_timeout_diagnosis(facts, path)` roda so sobre facts | Chama-la no `fuse` exigiria outra entrada | [x] assinatura; o significado de `path` fica para o DESIGN |
| A-006 | Qual coordenador declara `tune` | O dono muda | [ ] DESIGN |
| A-007 | Qual `--set` faz uma regra aparecer (AT-002) e qual valor de FGAC muda a SF-LF (AT-004) | Os casos precisam de outras fixtures | [ ] DESIGN (medido rodando o simulate) |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | 29 + 20 regras e o timeout sem porta, medidos |
| Users | 3 | Tres papeis |
| Goals | 3 | G0 a G9 com MoSCoW |
| Success | 3 | 7 goldens de fusion intactos, casos por consequencia |
| Scope | 2 | A-006 e A-007 ficam para o DESIGN |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-006 e A-007 sao de implementacao.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-12 | define-agent | Versao inicial, a partir de `BRAINSTORM_SIMULATE.md`; A-001 corrige a premissa do brainstorm (`measures.value` numerico em `tf.attribute`) |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_SIMULATE.md`
