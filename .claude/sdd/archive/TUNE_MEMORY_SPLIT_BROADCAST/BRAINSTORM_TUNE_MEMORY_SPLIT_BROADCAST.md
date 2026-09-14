# BRAINSTORM: Tune com memória, split e broadcast

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_MEMORY_SPLIT_BROADCAST |
| **Date** | 2026-09-14 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Shipped |

---

## Initial Idea

**Raw Input:** Segunda das três candidatas depois do §15: o `tune` deriva só `spark.sql.shuffle.partitions`, e as outras propriedades saem recusadas. A frente 2 foi quebrada em duas. Esta (2a) cobre memória, split e broadcast. A 2b cobre timeouts, speculation e a reescrita das regras 15 e 16.

**Context Gathered:**
- `sparkforge/tuning/spark_conf.py::_SEM_BASE_MEDIDA` recusa seis propriedades. A recusa de `spark.executor.memoryOverhead` diz que só existe o pico de heap, e está **desatualizada**: `facts/event_log.py::_EXECUTOR_MEMORY_METRICS` já extrai, por executor, `peak_jvm_heap_bytes`, `peak_jvm_offheap_bytes`, `peak_offheap_execution_bytes`, `peak_onheap_execution_bytes`, `peak_onheap_storage_bytes` e `peak_python_rss_bytes` em `spark.executor.memory_usage`.
- `knowledge/spark/memory-and-oom.md` §2: "Python worker vive no overhead, não no heap". Um executor perdido sem OOM no log aponta para overhead.
- A recusa de `spark.sql.files.maxPartitionBytes` pede a distribuição de tamanho por fonte, e ela existe: `s3.prefix_summary` (p50, p95, max) e `parquet.file`/`parquet.row_group` (do footer).
- `spark.sql.autoBroadcastJoinThreshold` compara contra o **tamanho estimado pelo otimizador** (`knowledge/spark/config-reference.md` §2). Sem estatística, a estimativa cai no default de 8 EiB (`plan-reading.md` §1). Hoje nenhum extrator lê `Statistics(sizeInBytes=…)`: o `spark_plan` só interpreta `== Physical Plan ==` e conta as linhas lógicas como puladas. O `plan.join` carrega estratégia e lado do build, sem tamanho. O `spark.sql.join_input` só carrega `via_joins`.
- Nenhum extrator lê as métricas do nó `BroadcastExchange` do event log.
- Fixtures: `fixtures/tfdiff/worker_upsized_*` têm event log com as métricas de memória fora do heap; `fixtures/parquet_footer/` tem 7 footers; `fixtures/plan/pruning_absent` tem `BroadcastExchange`. Nenhum plano de fixture tem `Statistics(`.

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `sparkforge/tuning/spark_conf.py`, `sparkforge/facts/spark_plan.py`, `sparkforge/facts/sql_metrics.py` | Estender, sem módulo novo |
| Relevant KB Domains | `knowledge/spark/{memory-and-oom,config-reference,plan-reading}.md`, `knowledge/storage/parquet-layout.md`; regras 11, 13, 19 e 20 do CLAUDE.md | Valor proposto mora no `tune`, fora do catálogo |
| IaC Patterns | N/A | |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Quais propriedades entram? | memoryOverhead, maxPartitionBytes (fonte única), broadcastThreshold com extrator novo; depois, na confirmação, também `--headroom`, o medido ao lado do broadcast, `executor.memory` e (na 2b) speculation e timeouts | Frente quebrada em 2a e 2b |
| 2 | De onde vem o tamanho do broadcast? | Estimativa do EXPLAIN COST | Kind novo `plan.join_side_stats` |
| 3 | Como propor o overhead? | Piso medido sem folga; `--headroom` opcional | O piso é o padrão; a folga, quando pedida, fica no `basis` |
| 4 | Que medida sustenta o split? | Row group mediano do footer | Sem footer, recusa com `collect parquet-footer` |
| 5 | Vários joins? | Só com um join candidato | `joins_divergentes` lista os pisos |
| 6 | Abordagem? | Estender o que existe | `change plan --from-tune` passa a gerar diff dessas chaves |
| 7 | Uma ou duas frentes? | Duas (2a e 2b) | Esta é a 2a |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Input files | `fixtures/tfdiff/worker_upsized_*/input/run.jsonl` | 2 | Métricas de memória por executor |
| Input files | `fixtures/parquet_footer/*/input/footer.json` | 7 | Row groups medidos |
| Input files | `fixtures/tuning/*/input/facts.json` | 7 | Goldens atuais do `tune` |
| Novos | plano `EXPLAIN COST` sintético; event log sintético com `BroadcastExchange` | 2 | Fixtures dos extratores novos |

---

## Approaches Explored

### Approach A: Estender o que existe ⭐ Recommended

**Description:** `tuning/spark_conf.py` ganha quatro derivações (overhead, heap, split e broadcast) e tira quatro nomes da lista de recusa. `facts/spark_plan.py` passa a ler `== Optimized Logical Plan ==` e emite `plan.join_side_stats`. `facts/sql_metrics.py` emite `spark.sql.broadcast_exchange` com o tamanho e o tempo medidos.

**Pros:** Reusa a procedência, o `runtime` e a forma `properties`/`refused` que já existem. O `change plan` ganha as chaves de graça.
**Cons:** `spark_conf.py` cresce, e dois extratores ganham kind novo.

### Approach B: Um módulo por propriedade

**Description:** `tuning/overhead.py`, `split.py`, `broadcast.py` e um verbo `analyze plan-cost`.
**Cons:** Quatro arquivos e um verbo novo para o que cabe em dois módulos.

### Approach C: Regra no catálogo

**Cons:** Rejeitada pela regra 11: valor proposto não é regra.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-09-14 |
| **Reasoning** | Mesma forma de resposta, com os extratores estendidos no lugar onde a medida nasce |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Overhead = piso do pior executor (`peak_jvm_offheap_bytes + peak_python_rss_bytes`), arredondado em MiB; `--headroom` multiplica | Um executor no limite entre dez folgados é o que morre | Média entre executores |
| 2 | Sem `ProcessTreePythonRSSMemory` no event log, o overhead sai recusado com a configuração que liga essas métricas | Pico sem o Python é metade da medida | Propor sobre o off-heap só |
| 3 | `executor.memory` = piso do pico de heap no pior executor | Mesma lógica, do outro lado | — |
| 4 | Split = row group mediano do footer, só com fonte única | Split menor que o row group faz tasks disputarem o mesmo row group | Distribuição de arquivo da listagem |
| 5 | Broadcast = piso da estimativa do lado pequeno, só com um join candidato sem broadcast, estimativa com estatística e abaixo de 8 GB | O threshold compara estimativa; 8 GB é o limite do Spark | O maior piso entre joins |
| 6 | O medido do `BroadcastExchange` sai ao lado, como conferência | Estimativa ruim aparece na comparação | Propor sobre o medido |
| 7 | Todas saem com `safety: REVIEW` | Mudam a forma do trabalho | — |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Timeouts, speculation e regras 15/16 | Vão para a frente 2b | Yes (2b) |
| `maxPartitionBytes` com várias fontes | Recusa `fontes_divergentes` | Yes |
| Broadcast com vários joins candidatos | Recusa `joins_divergentes` | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Arquitetura (tabela das propriedades e das recusas) | ✅ | "Certa, em duas frentes" | Yes (quebrada em 2a e 2b) |
| Fluxo, erros e testes | ✅ | "Sim, segue" | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
O `tune` recusa overhead, heap, split e broadcast. Para dois deles a medida já existe no motor, e a recusa estava desatualizada. Para o broadcast falta ler a estimativa que o Spark de fato compara.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Operador com executor morrendo sem OOM | Não tem o número de overhead que a medida sustenta |
| Operador de job com join | Não sabe se o broadcast não acontece por estimativa ou por threshold |

### Success Criteria (Draft)
- [ ] Overhead, heap, split e broadcast derivados nos goldens novos, com fórmula e base.
- [ ] Os 7 goldens atuais do `tune` iguais, exceto a lista de `refused`.
- [ ] `change plan --from-tune` gera diff das chaves novas quando há procedência em arquivo.

### Constraints Identified
- Regra 11 (valor proposto mora no `tune`), 13 (sem economia estimada), 20 (recusa com nome).

### Out of Scope (Confirmed)
- Timeouts, speculation e regras 15/16 (frente 2b).

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 7 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 3 |
| Validations Completed | 2 |
| Duration | 1 sessão |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_TUNE_MEMORY_SPLIT_BROADCAST.md`
