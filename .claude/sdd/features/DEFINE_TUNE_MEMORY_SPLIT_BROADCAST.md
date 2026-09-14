# DEFINE: Tune com memória, split e broadcast

> O `tune` passa a derivar `spark.executor.memoryOverhead`, `spark.executor.memory`, `spark.sql.files.maxPartitionBytes` e `spark.sql.autoBroadcastJoinThreshold`, cada uma com fórmula, base medida e recusa nomeada. Para o broadcast entram duas extrações novas.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_MEMORY_SPLIT_BROADCAST |
| **Date** | 2026-09-14 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 13/15 |

---

## Problem Statement

O `tune` deriva só `spark.sql.shuffle.partitions` e recusa as outras propriedades como "sem base medida". Duas dessas recusas estão desatualizadas:
- o event log já extrai, por executor, os picos de heap, de memória fora do heap e do Python (`spark.executor.memory_usage`);
- o footer Parquet já dá o tamanho de row group por fonte.

A terceira recusa, a do broadcast, é real: o número que o Spark compara com o threshold é a estimativa do otimizador, e nenhum extrator lê essa estimativa.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Operador com executor morrendo sem OOM | Ajusta memória de executor | Não tem o overhead que a medida sustenta, e a resposta do `tune` diz que a medida não existe |
| Operador de job com join | Ajusta o broadcast | Não sabe se o join não vira broadcast por causa da estimativa ou do threshold |
| Quem lê Parquet no S3 | Ajusta o split de leitura | Não tem o split alinhado ao row group medido |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | `spark.executor.memoryOverhead` = piso, em MiB arredondado para cima, do maior `peak_jvm_offheap_bytes + peak_python_rss_bytes` entre os executores. Com `--headroom f` (CLI) ou `headroom` (tool), a proposta vira piso × (1 + f), e a folga fica registrada no `basis` como decisão |
| **MUST** | Sem `peak_python_rss_bytes` no event log, o overhead sai em `refused`, com a configuração que liga as métricas de ProcessTree |
| **MUST** | `spark.executor.memory` = piso, em MiB arredondado para cima, do maior `peak_jvm_heap_bytes` entre os executores; sem o pico de heap, recusa |
| **MUST** | `spark.sql.files.maxPartitionBytes` = tamanho mediano de row group, em bytes comprimidos, de uma fonte Parquet medida. Com várias fontes medidas sai `fontes_divergentes`, com o valor de cada fonte; sem footer sai `sem_footer`, citando `collect parquet-footer` |
| **MUST** | O extrator de plano lê `Statistics(sizeInBytes=…)` do `== Optimized Logical Plan ==` do EXPLAIN COST e emite `plan.join_side_stats` com a estimativa de cada lado de cada join; a estimativa sem estatística (o default do Spark, próximo de 8 EiB) sai marcada |
| **MUST** | `spark.sql.autoBroadcastJoinThreshold` = piso da estimativa do lado menor, só com exatamente um join candidato: sem broadcast hoje, estimativa com estatística e abaixo de 8 GB. Com dois ou mais sai `joins_divergentes`, com o piso de cada join; estimativa sem estatística sai recusada com `ANALYZE TABLE` |
| **MUST** | O extrator de SQL metrics emite `spark.sql.broadcast_exchange` com o tamanho e o tempo medidos do nó `BroadcastExchange`; o `tune` o mostra ao lado da estimativa, como conferência |
| **MUST** | Todas as propriedades novas saem com `safety: REVIEW`, o valor efetivo e a procedência (`_procedencia`); os 4 nomes deixam `_SEM_BASE_MEDIDA` |
| **SHOULD** | `change plan --from-tune` gera diff das chaves novas quando elas têm procedência em arquivo, sem mudar o `change` |
| **SHOULD** | Agente `spark-performance-architect`, a linha do `tune` no CLAUDE.md, o manual `custo-e-capacidade.md` ou `job-lento.md`, e a referência |
| **COULD** | O `doctor` avisa quando o event log não tem as métricas de ProcessTree |

---

## Success Criteria

- [ ] SC1: cada propriedade nova tem golden em `fixtures/tuning/` com o valor derivado, a fórmula e a base, conferidos à mão.
- [ ] SC2: cada recusa nova (`sem_process_tree`, `sem_pico_de_heap`, `sem_footer`, `fontes_divergentes`, `joins_divergentes`, `estimativa_sem_estatistica`, `lado_acima_de_8gb`) aparece em pelo menos um golden.
- [ ] SC3: os 7 goldens atuais do `tune` mantêm a propriedade de shuffle byte a byte; só a lista de `refused` muda, perdendo os 4 nomes que passam a ser derivados ou recusados por outra razão.
- [ ] SC4: `plan.join_side_stats` sai num golden de `fixtures/plan/` a partir de um EXPLAIN COST sintético; os goldens de plano atuais ficam iguais.
- [ ] SC5: `spark.sql.broadcast_exchange` sai num golden de SQL metrics a partir de um event log sintético; os goldens atuais ficam iguais.
- [ ] SC6: `--headroom 0.2` sobre o golden de overhead devolve exatamente piso × 1,2 arredondado, e a folga aparece no `basis`.
- [ ] SC7: registros, surface, claims e referência em dia; suíte nos 9 lotes com 0 falha.

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Overhead medido | event log com os picos de ProcessTree | `tune` | `memoryOverhead` = piso do pior executor, `basis` com o executor e as parcelas |
| AT-002 | Sem ProcessTree | event log sem `peak_python_rss_bytes` | `tune` | `refused`, com a configuração que liga as métricas |
| AT-003 | Folga | AT-001 | `tune --headroom 0.2` | piso × 1,2, com a folga no `basis` |
| AT-004 | Heap | event log com `peak_jvm_heap_bytes` | `tune` | `executor.memory` = piso do pior executor |
| AT-005 | Split | footer de uma fonte | `tune` | `maxPartitionBytes` = row group mediano, em bytes comprimidos |
| AT-006 | Duas fontes | footers de duas fontes com medianas diferentes | `tune` | `fontes_divergentes`, com o valor de cada fonte |
| AT-007 | Sem footer | nenhum `parquet.row_group` | `tune` | `sem_footer`, com `collect parquet-footer` |
| AT-008 | Um join | EXPLAIN COST com um join sem broadcast e estatística | `analyze plan` + `tune` | threshold = piso da estimativa do lado menor |
| AT-009 | Dois joins | dois joins candidatos | `tune` | `joins_divergentes`, com os dois pisos |
| AT-010 | Sem estatística | estimativa default do Spark | `tune` | `estimativa_sem_estatistica`, com `ANALYZE TABLE` |
| AT-011 | Medido ao lado | event log com `BroadcastExchange` | `analyze sql-metrics` + `tune` | tamanho e tempo medidos ao lado da estimativa |
| AT-012 | Change plan | golden com overhead no `--conf` do Terraform | `change plan --from-tune` | diff da chave de overhead |

---

## Out of Scope

- `network.timeout`, `broadcastTimeout`, speculation e as regras 15 e 16 (frente 2b).
- `maxPartitionBytes` com várias fontes e broadcast com vários joins candidatos, que saem recusados.
- Qualquer estimativa de ganho.

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Regra 11: valor proposto mora no `tune` | Nada vai para o catálogo |
| Technical | Regra 13: nada de ganho estimado | `explanation` sem economia |
| Technical | Regra 20: recusa tem nome e diz o que destrava | Sete recusas novas nomeadas |
| Technical | Goldens de plano e de SQL metrics existentes | As extrações novas só acrescentam kind quando há dado |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `sparkforge/tuning/spark_conf.py`, `sparkforge/facts/spark_plan.py`, `sparkforge/facts/sql_metrics.py`, `adapters/{_core,cli,tools}.py` (`--headroom`), `fixtures/{tuning,plan,sql_metrics}/` | Nenhum módulo novo |
| **KB Domains** | `knowledge/spark/{memory-and-oom,config-reference,plan-reading}.md`, `knowledge/storage/parquet-layout.md` | |
| **IaC Impact** | None | |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | O EXPLAIN COST imprime `Statistics(sizeInBytes=<n> <unidade>, …)` nas linhas do plano lógico otimizado, inclusive nos filhos do `Join` | A extração não teria de onde ler | [ ] conferir na fonte T1/T2 no design |
| A-002 | `ProcessTreePythonRSSMemory` só sai no event log com `spark.executor.processTreeMetrics.enabled=true` | A recusa citaria a configuração errada | [ ] conferir na documentação do Spark |
| A-003 | O nó `BroadcastExchange` expõe no event log métricas de tamanho e de tempo ("data size", "time to broadcast" e afins) | Não haveria o medido ao lado | [ ] conferir na fonte do Spark |
| A-004 | `parquet.row_group.total_byte_size` é descomprimido, e o split do Spark fatia bytes do arquivo (comprimidos); é preciso o tamanho comprimido do row group | Proposta com a unidade errada | [ ] conferir se o coletor grava o comprimido por coluna, e somá-lo |
| A-005 | Overhead efetivo sem configuração explícita = `max(384 MiB, 0.10 × spark.executor.memory)` | Comparação errada com o efetivo | [ ] conferir na documentação do Spark |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Recusas desatualizadas medidas |
| Users | 3 | Três personas |
| Goals | 3 | MoSCoW por propriedade e extrator |
| Success | 2 | Os valores exatos dependem dos goldens do design |
| Scope | 2 | A-001 a A-005 abertos |
| **Total** | **13/15** | |

---

## Open Questions

- A-001 a A-005: conferir no design, na fonte oficial e no código.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | define-agent | Versão inicial a partir de BRAINSTORM_TUNE_MEMORY_SPLIT_BROADCAST.md; A-004 (unidade do row group) levantada ao ler o extrator |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md`
