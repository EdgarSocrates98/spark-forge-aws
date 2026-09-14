# DESIGN: Tune com memória, split e broadcast

> Technical design for implementing TUNE_MEMORY_SPLIT_BROADCAST (frente 2a)

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | TUNE_MEMORY_SPLIT_BROADCAST |
| **Date** | 2026-09-14 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md](./DEFINE_TUNE_MEMORY_SPLIT_BROADCAST.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
 event log ──> event_log.py ──> spark.executor.memory_usage (ja existe: heap, offheap, python_rss)
          └──> sql_metrics.py ──> spark.sql.broadcast_exchange (NOVO: data size, tempos)
 EXPLAIN COST ──> spark_plan.py ──> plan.join_side_stats (NOVO: sizeInBytes por lado de join)
 footer ──> parquet_footer.py ──> parquet.row_group (+ attrs.total_compressed_bytes)
                                   │
                                   v
      tuning/spark_conf.py: build_conf_advice(facts, runtime, headroom=None)
        ├─ shuffle.partitions (como hoje)
        ├─ executor.memoryOverhead   piso(pior executor: offheap + python_rss) [× (1+headroom)]
        ├─ executor.memory           piso(pior executor: heap)
        ├─ files.maxPartitionBytes   mediana(row group comprimido) de UMA fonte
        └─ autoBroadcastJoinThreshold piso(lado menor) de UM join candidato  (+ medido ao lado)
                                   │
                                   v
      {properties[], refused[]}  ──> change plan --from-tune (diff quando ha procedencia em arquivo)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `facts/spark_plan.py` | Lê `== Optimized Logical Plan ==` quando traz `Statistics(`; emite `plan.join_side_stats` por join lógico (lado esquerdo e direito, bytes, `has_stats`) | Árvore por marcadores `:-`/`+-`, como o físico |
| `facts/sql_metrics.py` | Registra os nós `BroadcastExchange`; `measure_for` ganha "data size", "time to collect", "time to build" e "time to broadcast"; emite `spark.sql.broadcast_exchange` | Mapa `accumulatorId -> (nó, nome)` que já existe |
| `facts/parquet_footer.py` | `parquet.row_group.attrs.total_compressed_bytes` = soma de `total_compressed_size` das colunas | Em `attrs`, fora do `Fact.id` |
| `tuning/spark_conf.py` | Quatro derivações, sete recusas novas e `headroom` | Funções puras por propriedade |
| `adapters/{_core,cli,tools}.py` | `--headroom` na CLI e `headroom` na tool `sparkforge_tune` | Parâmetro opcional |

---

## Key Decisions

### Decision 1: Unidade do split é o row group COMPRIMIDO, em `attrs`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-09-14 |

**Context:** A-004. No Parquet, `row_group.total_byte_size` é descomprimido, e o split do Spark fatia bytes do arquivo. O coletor já grava `total_compressed_size` em cada coluna (`collect/parquet_footer.py::_do_column_chunk`).

**Choice:** O extrator soma as colunas e grava `attrs.total_compressed_bytes` no `parquet.row_group`. O `tune` usa a mediana dessa soma por fonte (`attrs.prefix`).

**Rationale:** O `Fact.id` é hash de `kind + subject + measures`, então pôr a soma em `attrs` não muda nenhum id, e nenhum `expected/findings.json` de `fixtures/parquet_footer/` que cita row group precisa ser regravado. Só os `facts.json` ganham a chave.

**Alternatives Rejected:**
1. Em `measures`: rejeitado porque mudaria todos os ids de row group e as evidências dos findings de SF-PQ.
2. `total_byte_size`: rejeitado porque é a unidade errada.

**Consequences:** A distribuição comprimida fica disponível para outras regras depois, sem migração.

### Decision 2: Join candidato definido pela estimativa, sem mapear o plano físico

**Context:** Ligar um join lógico ao `BroadcastHashJoin` físico exige casar relações, e é frágil.

**Choice:** É candidato o join lógico cujo lado menor tem estatística (não é o default do Spark, próximo de 8 EiB), fica **acima** do threshold efetivo (por isso a estimativa não o torna broadcast) e fica abaixo de 8 GB. O threshold efetivo vem de `spark.conf_effective` ou do default de 10 MB (`knowledge/spark/config-reference.md`). Exatamente um candidato gera a proposta = lado menor arredondado para cima em MiB, em bytes. Dois ou mais geram `joins_divergentes`.

**Rationale:** É a pergunta que o threshold responde: a estimativa é que decide.

### Decision 3: Overhead e heap pelo pior executor, em MiB

**Choice:**
- `overhead = ceil_MiB(max_executor(peak_jvm_offheap_bytes + peak_python_rss_bytes))`, com `headroom` opcional como multiplicador (1 + h).
- Com `spark.executor.pyspark.memory` definida, o pico do Python não soma: a documentação diz que o Python só conta no overhead quando essa chave não está configurada.
- O efetivo padrão, para comparação, é `max(minMemoryOverhead = 384 MiB, 0.10 × spark.executor.memory)` (documentação de configuração do Spark).
- `executor.memory = ceil_MiB(max_executor(peak_jvm_heap_bytes))`, proposto como `NNNm`.

**Recusas:**
- `sem_process_tree`: nenhum executor com `peak_python_rss_bytes`. Destrava com `spark.executor.processTreeMetrics.enabled=true`, cujo default é `false`.
- `sem_pico_de_heap`.

**Consequence:** No Glue a memória do worker é fixa por tipo. A `explanation` avisa que o valor é piso medido, e não pedido de worker maior.

### Decision 4: A estimativa lida do EXPLAIN COST

**Context:** A-001 conferida na fonte T2: `QueryExecution.stringWithStats` imprime `== Optimized Logical Plan ==` com `addSuffix = true`, e `Statistics.toString` é `Statistics(sizeInBytes=<Utils.bytesToString>, rowCount=…)`.

**Choice:**
- O extrator lê as linhas da seção lógica otimizada. Hoje elas são puladas e contadas em `skipped_logical_lines`; o contador passa a excluir as linhas usadas.
- Para cada `Join`, os dois filhos diretos pela indentação dão `left_bytes` e `right_bytes`.
- `bytesToString` usa B, KiB, MiB, GiB, TiB, PiB e EiB com uma casa decimal, e o parser converte em bytes.
- Estimativa de 8.0 EiB ou mais vira `has_stats: false`.

**Consequence:** Plano sem seção lógica, ou sem `Statistics(`, não emite o kind novo, e os goldens atuais de plano ficam iguais.

### Decision 5: Medido do broadcast como conferência

**Context:** A-003 conferida na fonte T2: `BroadcastExchangeExec` publica "data size", "number of output rows", "time to collect", "time to build" e "time to broadcast".

**Choice:** `spark.sql.broadcast_exchange` por nó, com `data_size_bytes`, `collect_ms`, `build_ms`, `broadcast_ms` e `output_rows`. O `tune` o traz em `basis.measured_broadcasts` quando existe, e nunca propõe sobre ele.

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `sparkforge/facts/parquet_footer.py` | Modify | `attrs.total_compressed_bytes` | @python-developer | None |
| 2 | `sparkforge/facts/spark_plan.py` | Modify | `plan.join_side_stats` | @python-developer | None |
| 3 | `sparkforge/facts/sql_metrics.py` | Modify | `spark.sql.broadcast_exchange` | @python-developer | None |
| 4 | `sparkforge/tuning/spark_conf.py` | Modify | Quatro derivações, recusas, `headroom` | @python-developer | 1-3 |
| 5 | `sparkforge/adapters/{_core,cli,tools}.py` | Modify | `--headroom` e o schema da tool `tune` | @python-developer | 4 |
| 6 | `fixtures/tuning/<casos novos>/` | Create | Goldens: overhead, sem ProcessTree, heap, split, duas fontes, sem footer, um join, dois joins, sem estatística, medido ao lado | @test-generator | 4 |
| 7 | `fixtures/plan/explain_cost_join/`, `fixtures/sql_metrics/broadcast_exchange/` | Create | Goldens dos extratores | @test-generator | 2, 3 |
| 8 | `tests/test_tuning_spark_conf.py`, `tests/test_fixtures_golden_tuning.py` (`REQUIRED_FIXTURES`), testes dos extratores | Modify | Unidade e golden | @test-generator | 1-6 |
| 9 | Listas de kinds (`test_facts_kinds`, reachability, kind coverage), surface, claims, referência, agente, CLAUDE.md, manual | Modify | Registros e docs | (general) | 2-5 |

---

## Agent Assignment Rationale

| Agent | Files Assigned | Why This Agent |
|-------|----------------|----------------|
| @python-developer | 1-5 | Extensões pontuais de extrator e de composição |
| @test-generator | 6-8 | Goldens e unidade |
| (general) | 9 | Registros do repositório |

---

## Code Patterns

### Pattern 1: bytesToString de volta para bytes

```python
_UNIDADES = {"B": 1, "KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30,
             "TiB": 1 << 40, "PiB": 1 << 50, "EiB": 1 << 60}
_STATS = re.compile(r"Statistics\(sizeInBytes=([0-9.]+)\s*(B|KiB|MiB|GiB|TiB|PiB|EiB)")


def bytes_da_estatistica(linha: str) -> float | None:
    casou = _STATS.search(linha)
    return float(casou[1]) * _UNIDADES[casou[2]] if casou else None
```

### Pattern 2: piso em MiB

```python
_MIB = 1 << 20


def piso_mib(valor_bytes: float, folga: float = 0.0) -> int:
    return math.ceil(valor_bytes * (1.0 + folga) / _MIB)
```

---

## Data Flow

```text
analyze event-log  -> memory_usage (por executor)            ┐
analyze sql-metrics -> broadcast_exchange (medido)           │
analyze plan (EXPLAIN COST) -> join_side_stats (estimado)    ├─> tune --facts ... [--headroom h] -> properties/refused
analyze parquet-footer -> row_group (+ comprimido)           ┘                                       │
                                                                        change plan --from-tune <────┘
```

---

## Integration Points

| External System | Integration Type | Authentication |
|-----------------|-----------------|----------------|
| Nenhum | Composição sobre facts já extraídos | Nenhuma |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Unit | `bytes_da_estatistica`, `piso_mib`, candidato de join, mediana por fonte, `pyspark.memory` tirando o Python | `tests/test_tuning_spark_conf.py` e testes dos extratores | pytest | AT-001 a AT-012 |
| Golden (tune) | Casos novos em `fixtures/tuning/`; os 7 atuais só perdem nomes de `refused` | `tests/test_fixtures_golden_tuning.py` | pytest | SC1 a SC3, SC6 |
| Golden (extratores) | EXPLAIN COST sintético; event log com `BroadcastExchange`; goldens atuais de plano, SQL metrics e footer só ganham `attrs` | testes golden existentes | pytest | SC4, SC5 |
| Integração | `change plan --from-tune` com overhead no `--conf` | `tests/test_fixtures_golden_change.py` ou unidade | pytest | AT-012 |

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| Medida ausente | `refused` com `reason`, `detail` e a medida que destrava | No |
| `headroom` negativo | `AdapterError` exit 2 com o comando | No |
| Linha de `Statistics` ilegível | Lado sem estimativa (`has_stats: false`) | No |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `--headroom` | float ≥ 0 | ausente (piso puro) | Folga declarada sobre o piso de overhead |

---

## Security Considerations

- Nenhuma leitura nova de artefato; tudo é composição ou extração de arquivo já apontado.

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Logging | Nenhum |
| Metrics | Nenhuma |
| Tracing | A tool `tune` passa por `call_tool` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-14 | design-agent | Versão inicial. A-001 e A-003 conferidas no código do Spark (T2), A-002 e A-005 na documentação de configuração (T1), A-004 no coletor |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_TUNE_MEMORY_SPLIT_BROADCAST.md`
