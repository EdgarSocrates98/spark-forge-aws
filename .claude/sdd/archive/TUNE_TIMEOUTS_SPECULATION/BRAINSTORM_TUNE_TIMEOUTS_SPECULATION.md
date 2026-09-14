# BRAINSTORM: Tune com timeouts e speculation (frente 2b)

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_TIMEOUTS_SPECULATION |
| **Date** | 2026-09-14 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Shipped |

---

## Initial Idea

**Raw Input:** Frente 2b do tune: `spark.network.timeout`, `spark.sql.broadcastTimeout` e `spark.speculation` derivados da medida, com extração de executor por task no event log e reescrita das regras 15/16 do CLAUDE.md (o operador escolheu ir contra elas).

**Context Gathered:**
- A frente 2a (PR #67, `749d44b9`) deixou as três propriedades em `_SEM_BASE_MEDIDA` de `sparkforge/tuning/spark_conf.py`, com recusa `no_measured_basis`. As recusas citam as regras 15/16 e a `SF-TIMEOUT-001` como razão para não propor número.
- `sparkforge/facts/timeout_diagnosis.py` já emite `spark.timeout.diagnosis` (categoria `heartbeat`/`network`/`broadcast`/`wall_clock`, `also_seen` e os sintomas medidos: skew, spill, GC, executores perdidos) e `spark.timeout.relation` (`heartbeat_s`, `network_timeout_s`), e roda no `fuse` quando o pool tem kind de origem.
- `spark.sql.broadcast_exchange` (entrou na 2a) traz `collect_ms`, `build_ms` e `broadcast_ms` medidos por `BroadcastExchange`.
- O `SparkListenerTaskEnd` do extrator de event log só alimenta percentis por stage (`_StageAccumulator`): executor e host da task são descartados, e nenhuma fonte separa a lentidão do NÓ da lentidão da PARTIÇÃO, que é exatamente o que a recusa atual da speculation diz faltar.
- `SF-TIMEOUT-002` tem hoje `action.target: spark.executor.heartbeatInterval`, `direction: decrease`; `SF-TIMEOUT-001` guarda os limiares de sintoma (skew 3.0, spill 0.1, GC 0.1, um executor perdido).
- Área `SF-UI` tem regras até `SF-UI-006`, rota e coordenador (`spark-performance-architect`).

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/facts/event_log.py`, `sparkforge/tuning/spark_conf.py`, `rules/catalog/{spark-ui,timeout}.yaml`, `CLAUDE.md`/`AGENTS.md` | Estender o que existe, sem módulo novo |
| Relevant KB Domains | spark (agentspec), `knowledge/spark/`, `knowledge/glue/workers-and-capacity.md` | Defaults de speculation e de timeout conferidos na fonte do Spark |
| IaC Patterns | Terraform como procedência (`tf.spark_conf`) | `change plan --from-tune` passa a levar as três chaves |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O que conta como task lenta para a speculation? | Critério do próprio Spark (duração acima de multiplier vezes a mediana do stage, com o quantile concluído) | Nenhum limiar inventado; defaults da versão conferidos na fonte no design |
| 2 | Com a relação heartbeat x network quebrada, qual chave propor? | `network.timeout = heartbeat × 12` (razão dos defaults 120s/10s) | Mantém o heartbeat pedido; a ação da `SF-TIMEOUT-002` muda junto |
| 3 | De onde sai o valor de `broadcastTimeout`? | Piso medido do broadcast que completou (collect + build + broadcast), com `--headroom` | Recusa sem broadcast medido e quando o limite atual já passa do piso |
| 4 | Há amostras além dos fixtures? | Só sintéticos | Event logs sintéticos na forma documentada do `SparkListenerTaskEnd`; nada de produção em arquivo |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/timeout/*`, `fixtures/eventlog/broadcast_timeout_stage_failure` | 4 | Frases de broadcast e de rede, timeout com sintoma, run sem evidência |
| Input files | `fixtures/sql_metrics/broadcast_exchange` | 1 | Tempos medidos do `BroadcastExchange` |
| Output examples | `fixtures/tuning/*/expected/report.json` | 14 | Forma de `properties` e `refused` do `tune` |
| Ground truth | fonte do Spark (speculation, heartbeat, network timeout, broadcast timeout) | - | Defaults conferidos por tag no design |
| Related code | `sparkforge/tuning/spark_conf.py` (`_overhead`, `_broadcast`), `timeout_diagnosis.py` | 2 | Moldes de piso medido, headroom e recusa nomeada |

**How samples will be used:**

- Event logs sintéticos novos com `Executor ID`, `Host`, `Launch Time`/`Finish Time` e input por task, um caso por proposta e por recusa.
- Os fixtures de timeout existentes viram entrada dos goldens de tuning pelo mesmo caminho do `fuse`.

---

## Approaches Explored

### Approach A: Kinds agregados no extrator de event log ⭐ Recommended

**Description:** O extrator guarda duração, executor e input por task e emite `spark.stage.slow_tasks` por stage (tasks acima do critério do Spark, por executor) e `spark.executor.slow_node` por executor quando ele é lento em dois ou mais stages sem input maior que a mediana. O `tune` e uma regra nova consomem o fact derivado.

**Pros:**
- Um fact por stage e um por executor lento, não um por task.
- Segue o precedente da 2a (estender o extrator, compor no `tune`) e a regra 33 (contagem entre stages vira fact).

**Cons:**
- O acumulador do stage passa a guardar uma lista por task durante a leitura.

**Why Recommended:** Mesma forma da 2a e do resto do extrator; o `scan` e o `fuse` enxergam a evidência sem mudança.

---

### Approach B: Um fact por task

**Description:** Emitir `spark.task` com duração, executor e host, e agregar no `tune`.

**Pros:**
- Flexível para qualquer agregação futura.

**Cons:**
- Um job com 50 mil tasks vira 50 mil facts no barramento committado, o mesmo motivo que recusou `parquet.column_chunk`.

---

### Approach C: O `tune` lê o event log

**Description:** Passar o caminho do log ao `tune` e calcular direto.

**Pros:**
- Nenhum kind novo.

**Cons:**
- Quebra a regra dos verbos de topo (não leem artefato), e `scan`/`fuse` não veriam a evidência.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-14 |
| **Reasoning** | Kind agregado por stage, derivado por executor; um fact por task seria volume sem decisão |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Task lenta = critério do Spark (multiplier sobre a mediana, quantile concluído) | O motor decide a cópia especulativa com esse critério; nenhum limiar nosso | p95 do stage; fator declarado pelo operador |
| 2 | `spark.speculation = true` só com o MESMO executor lento em dois ou mais stages e input dessas tasks até a mediana | Separa lentidão do nó da lentidão da partição, a lacuna que a recusa antiga nomeava | Speculation por skew detectado (o documento de origem recusa) |
| 3 | `network.timeout = heartbeat × 12`, só com a relação quebrada | Razão entre os defaults; mantém o heartbeat que alguém pediu | Baixar o heartbeat; propor as duas |
| 4 | `broadcastTimeout` = piso medido do broadcast que completou, com `--headroom`, só com diagnóstico `broadcast`, sem `also_seen` e sem sintoma | Piso medido como na 2a; os limiares de sintoma são LIDOS da `SF-TIMEOUT-001`, sem cópia | Dobrar o limite; só recusar |
| 5 | `spark.executor.slow_node` derivado no extrator | Regra 33: contar entre stages não cabe no `where` | Regra contando stages por `expr` |
| 6 | Regra nova `SF-UI-007` (P2) sobre o fact derivado | O executor lento é achado mesmo sem quem peça o `tune` | Só o `tune` enxergar |
| 7 | `SF-TIMEOUT-002` passa a mirar `spark.network.timeout`, direção `increase` | Alinha a ação do catálogo com o valor que o `tune` deriva | Manter a ação antiga e divergir |
| 8 | Regras 15/16 reescritas | 15: sem sintoma, o `tune` propõe `broadcastTimeout`; `wall_clock` e `heartbeat` nunca têm valor. 16: a relação quebrada tem valor derivado | Manter as regras e recusar os números |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Propor `spark.speculation.multiplier`/`quantile` | A 2b só liga a speculation; os defaults são o critério | Yes |
| Agrupar a lentidão também por host | No Glue cada worker costuma ter um executor; host e executor quase coincidem | Yes |
| Baixar `spark.executor.heartbeatInterval` | O operador escolheu subir a espera e manter o heartbeat pedido | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Kind novo e as três derivações, com recusas | ✅ | Certo, segue | No |
| Fact derivado por executor, `SF-UI-007`, ação da `SF-TIMEOUT-002`, texto das regras 15/16 | ✅ | Certo, segue | Yes (fact derivado acrescentado pela regra 33) |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O `tune` recusa `spark.network.timeout`, `spark.sql.broadcastTimeout` e `spark.speculation` por falta de base, mas a relação heartbeat x network, o tempo medido do broadcast e a lentidão por executor já existem ou podem ser extraídos; o operador fica sem número mesmo quando a medida o sustenta.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador de job Glue | Timeout de broadcast ou de rede sem valor sustentado; speculation ligada por palpite |
| Revisor de PR | Não sabe se o número de timeout veio de medida ou de costume |

### Success Criteria (Draft)
- [ ] Cada propriedade nova com um golden de proposta e um por recusa nomeada
- [ ] Speculation nunca proposta sem executor lento em dois ou mais stages com input até a mediana
- [ ] `broadcastTimeout` nunca proposto com sintoma da `SF-TIMEOUT-001` ao lado
- [ ] `SF-UI-007` dispara no golden positivo e cala no par sem executor repetido
- [ ] Regras 15/16 reescritas em CLAUDE.md e AGENTS.md, e goldens de timeout inalterados fora das recusas

### Constraints Identified
- Repo público: event logs sintéticos
- Defaults de speculation e de timeout conferidos na fonte do Spark por versão
- Os limiares de sintoma continuam só no catálogo (`SF-TIMEOUT-001`)
- Nenhum ganho estimado; toda proposta sai `REVIEW`

### Out of Scope (Confirmed)
- Chaves irmãs da speculation (`multiplier`, `quantile`)
- Agrupamento por host
- Proposta de `spark.executor.heartbeatInterval`
- L3 (frente seguinte)

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 de descoberta + 1 de abordagem + 1 de YAGNI |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_TUNE_TIMEOUTS_SPECULATION.md`
