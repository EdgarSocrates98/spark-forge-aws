# DEFINE: Tune com timeouts e speculation (frente 2b)

> O `tune` passa a derivar `spark.network.timeout`, `spark.sql.broadcastTimeout` e `spark.speculation` da medida, com a lentidão por executor extraída do event log, uma regra nova sobre executor lento e as regras 15/16 reescritas.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_TIMEOUTS_SPECULATION |
| **Date** | 2026-09-14 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 14/15 |

---

## Problem Statement

O `tune` recusa `spark.network.timeout`, `spark.sql.broadcastTimeout` e `spark.speculation` com `no_measured_basis`, mas a relação heartbeat x network (`spark.timeout.relation`), o tempo medido do broadcast (`spark.sql.broadcast_exchange`) e a duração de cada task com o executor que a rodou (`SparkListenerTaskEnd`) já estão no artefato. O operador de job Glue fica sem número mesmo quando a medida o sustenta, e liga a speculation por palpite, sem saber se a lentidão é do nó ou da partição.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador de job Glue | Ajusta configuração depois de um run lento ou em timeout | Timeout de broadcast ou de rede sem valor sustentado; speculation ligada sem saber se o nó é o problema |
| Revisor de PR | Aprova mudança de configuração | Não sabe se o número de timeout veio de medida ou de costume |
| Agente `spark-performance-architect` | Coordena o diagnóstico | Não tem achado que separe executor lento de partição grande |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Extrator de event log emite `spark.stage.slow_tasks` por stage, com o critério de speculation do Spark da versão (multiplier sobre a mediana, piso de tempo mínimo) |
| **MUST** | Extrator emite `spark.executor.slow_node` quando o MESMO executor tem tasks lentas em dois ou mais stages com input até a mediana do stage |
| **MUST** | `tune` propõe `spark.speculation = true` só com `spark.executor.slow_node`, e recusa por nome nos outros casos |
| **MUST** | `tune` propõe `spark.network.timeout = heartbeat × 12` só com `spark.timeout.relation` quebrada |
| **MUST** | `tune` propõe `spark.sql.broadcastTimeout` pelo piso medido do broadcast que completou, com `--headroom`, só com diagnóstico `broadcast` sem `also_seen` e sem sintoma da `SF-TIMEOUT-001` |
| **MUST** | Regras 15 e 16 reescritas em `CLAUDE.md` e `AGENTS.md` |
| **SHOULD** | Regra nova `SF-UI-007` (P2) sobre `spark.executor.slow_node` |
| **SHOULD** | `SF-TIMEOUT-002` com `action.target: spark.network.timeout` e `direction: increase` |
| **COULD** | `change plan --from-tune` leva as três chaves ao `--conf` do Terraform, pelo caminho que já existe |

---

## Success Criteria

- [ ] 3 de 3 propriedades com pelo menos um golden de proposta, e cada recusa nomeada nova coberta por golden ou teste de unidade (mínimo 10 recusas)
- [ ] 0 proposta de speculation sem `spark.executor.slow_node` no corpus inteiro de tuning
- [ ] 0 proposta de `broadcastTimeout` com sintoma acima dos limiares da `SF-TIMEOUT-001` no corpus inteiro
- [ ] Critério de task lenta conferido para 5 versões de Glue (3.0, 4.0, 5.0, 5.1, 6.0): multiplier 1.5 e quantile 0.75 abaixo do Spark 4.0; 3 e 0.9 do Spark 4.0 em diante; tempo mínimo 100 ms em todas
- [ ] `SF-UI-007` dispara em 1 golden positivo e cala em 2 pares (lentidão espalhada e lentidão da partição)
- [ ] Goldens existentes de event log mudam só pelos kinds novos; goldens de tuning e de change mudam só nos nomes de `refused`
- [ ] Suíte em 9 lotes com 0 falha, e os gates de lastro, números e superfície sem divergência

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Tasks lentas por stage | Event log de um stage com 10 tasks, 2 acima de 1,5 × mediana, Spark 3.5.4 | `analyze event-log` | `spark.stage.slow_tasks` com 2 lentas, o limiar em ms e a contagem por executor |
| AT-002 | Versão muda o critério | O mesmo log sob Spark 4.1.1 | `analyze event-log` | Limiar de 3 × mediana; só as tasks acima dele contam |
| AT-003 | Nó lento | Executor 3 com tasks lentas em 2 stages, input dessas tasks até a mediana | `analyze event-log` + `judge` + `tune` | `spark.executor.slow_node` para o executor 3; `SF-UI-007` dispara; `spark.speculation = true` proposta |
| AT-004 | Lentidão da partição | Tasks lentas com input acima da mediana | idem | Sem `slow_node`; `SF-UI-007` cala; recusa `lentidao_da_particao` |
| AT-005 | Lentidão espalhada | Tasks lentas em executores diferentes a cada stage | idem | Sem `slow_node`; recusa `lentidao_espalhada` |
| AT-006 | Speculation já ligada | AT-003 com `spark.speculation=true` efetivo | `tune` | Recusa `speculation_ja_ligada` |
| AT-007 | Relação quebrada | `spark.timeout.relation` com heartbeat 60s e network 30s | `tune` | `spark.network.timeout` = 720 (s), com a fórmula e as duas medidas no `basis` |
| AT-008 | Relação ok ou ausente | Heartbeat 10s e network 120s; ou sem as duas chaves | `tune` | Recusa `relacao_ok`; ou `sem_relacao_observada` |
| AT-009 | Broadcast sem sintoma | Diagnóstico `broadcast` sem `also_seen` e sem sintoma, e `spark.sql.broadcast_exchange` medido de run que completou | `tune` | `broadcastTimeout` = ceil(maior collect + build + broadcast × (1 + headroom)) em s |
| AT-010 | Broadcast com sintoma | AT-009 com skew acima do limiar da `SF-TIMEOUT-001` | `tune` | Recusa `sintoma_ao_lado`, nomeando a medida |
| AT-011 | Broadcast sem medida ou que já cabe | Sem `broadcast_exchange`; ou limite atual acima do piso | `tune` | Recusa `sem_broadcast_medido`; ou `ja_cabe_no_timeout` |
| AT-012 | Ação da SF-TIMEOUT-002 | Golden `heartbeat_maior_que_network` | `judge` | O finding traz `action.target: spark.network.timeout`, `direction: increase` |
| AT-013 | Regras 15/16 | `CLAUDE.md` e `AGENTS.md` | leitura | 15 diz que sem sintoma o `tune` propõe `broadcastTimeout` e que `wall_clock`/`heartbeat` nunca têm valor; 16 diz que a relação quebrada tem valor derivado |
| AT-014 | Change plan | Terraform com `--conf spark.network.timeout=30s` e a relação quebrada | `change plan --from-tune` | Diff da chave `spark.network.timeout` |

---

## Out of Scope

- Propor `spark.speculation.multiplier`, `spark.speculation.quantile` ou `spark.speculation.minTaskRuntime`
- Agrupar a lentidão por host (só por executor)
- Propor `spark.executor.heartbeatInterval`
- Valor proposto para timeout de `wall_clock` (relógio do Glue) ou `heartbeat`
- Um fact por task no barramento
- L3 (pacote de PR), que é a frente seguinte

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Limiares de sintoma só no catálogo (`SF-TIMEOUT-001`) | O `tune` lê a regra do catálogo; nenhuma cópia de limiar no módulo |
| Technical | Regra 33: contar entre stages não cabe no `where` | `spark.executor.slow_node` é derivado no extrator |
| Technical | Kind novo entra nas listas manuais (`test_rules_catalog_reachability`, `test_fixtures_kind_coverage`) e a regra nova precisa de golden que a dispare | Registros no build |
| Technical | Repo público | Event logs sintéticos na forma do `SparkListenerTaskEnd` (`Executor ID`, `Host`, `Launch Time`, `Finish Time`, `Speculative`, `Killed`) |
| Technical | Nenhum ganho estimado; toda proposta `REVIEW` | Mesmo contrato da 2a |
| Resource | Suíte em lotes, memória baixa | Nove lotes, um processo por lote |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/facts/event_log.py`, `sparkforge/tuning/spark_conf.py`, `sparkforge/adapters/{_core,cli,tools}.py`, `rules/catalog/{spark-ui,timeout}.yaml`, `CLAUDE.md`, `AGENTS.md` | Extensão do que existe, sem módulo novo |
| **KB Domains** | spark (agentspec); `knowledge/spark/`, `knowledge/glue/runtime-matrix.md` | Tabela de versão do critério ao lado da do AQE |
| **IaC Impact** | None | Terraform só como procedência de `tf.spark_conf` |

---

## Data Contract (if applicable)

### Source Inventory
| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| Event log do Spark (`SparkListenerTaskEnd`, `StageCompleted`) | JSON lines | uma linha por task | por run | Glue / Spark |
| Facts derivados (`spark.timeout.diagnosis`, `spark.timeout.relation`, `spark.sql.broadcast_exchange`) | facts JSON | um por run, relação ou exchange | por `fuse` | SparkForge |

### Schema Contract
| Column | Type | Constraints | PII? |
|--------|------|-------------|------|
| `spark.stage.slow_tasks.measures` (`slow_count`, `task_count`, `threshold_ms`, `median_ms`) | número | `slow_count <= task_count` | No |
| `spark.stage.slow_tasks.attrs.by_executor` | mapa executor para contagem e input | chaves são `Executor ID` | No |
| `spark.executor.slow_node` (`stages_slow`, `slow_tasks`) | número | `stages_slow >= 2` | No |

### Freshness SLAs
| Layer | Target | Measurement |
|-------|--------|-------------|
| Facts | Na leitura do event log | Extração determinística |

### Completeness Metrics
- Stage sem task bem-sucedida não emite `slow_tasks`
- Task falha, morta ou especulativa fora da mediana e da contagem

### Lineage Requirements
- Toda proposta cita os fact ids no `basis`/`current.evidence`

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Com o stage concluído, a condição de `quantile` do Spark já foi satisfeita, e o critério pós-execução é `duração > max(multiplier × mediana, tempo mínimo)` | O critério pós-execução divergiria do que o scheduler faria; precisaria simular a ordem de término | [x] fórmula conferida em TaskSetManager v3.1.1, v3.5.4 e v4.1.1 |
| A-002 | Defaults: multiplier 1.5 e quantile 0.75 abaixo do Spark 4.0; 3 e 0.9 desde o 4.0.0; tempo mínimo 100 ms (constante no scheduler na 3.1.1, `spark.speculation.minTaskRuntime` desde 3.2.0) | Critério errado por versão | [x] fonte v3.1.1, v3.3.0, v3.5.4 e docs 4.0.0 e 4.1.1 |
| A-003 | `SparkListenerTaskEnd.Task Info` traz `Executor ID`, `Host`, `Speculative`, `Killed` | Sem executor por task, sem `slow_node` | [x] `JsonProtocol.taskInfoToJson` v3.5.4 |
| A-004 | Valor configurado de `spark.speculation.multiplier`/`quantile` em `spark.conf_effective` vence o default | O critério ignoraria o que o run usou | [ ] conferir no design |
| A-005 | Ler o catálogo no `tune` (para os limiares da `SF-TIMEOUT-001`) custa um carregamento por chamada (~810 ms medidos no Forge Pack) | Latência do `tune`; carregar só o arquivo da área | [ ] medir no design |
| A-006 | O pool fundido traz o diagnóstico do run que falhou e o `broadcast_exchange` de run que completou | Sem mistura, `broadcastTimeout` sempre recusa `sem_broadcast_medido` | [ ] conferir no design |
| A-007 | Mudar a ação da `SF-TIMEOUT-002` só move o golden dela e os de `arbitrate`/`simulate` que a leem | Diff maior que o esperado | [ ] medir no build |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Três recusas atuais e as medidas que já existem, nomeadas |
| Users | 3 | Operador, revisor e o agente coordenador, com a dor de cada um |
| Goals | 3 | MoSCoW com seis MUST |
| Success | 3 | Contagens e versões conferidas |
| Scope | 2 | Fora do escopo explícito; A-004 a A-007 abertos para o design |
| **Total** | **14/15** | |

---

## Open Questions

None - ready for Design. A-004 a A-007 são conferências do design e do build, não decisões do operador.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | define-agent | Initial version, a partir de BRAINSTORM_TUNE_TIMEOUTS_SPECULATION.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_TUNE_TIMEOUTS_SPECULATION.md`
