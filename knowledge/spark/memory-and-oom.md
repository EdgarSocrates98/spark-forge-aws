# Memória, spill, GC e as classes de OOM

"O job deu OOM" não é diagnóstico. São sete falhas distintas, com causas e correções diferentes. Classificar errado leva a aumentar worker quando o problema é plano, ou a mexer no plano quando o problema é disco.

## 1. Modelo de memória do executor

Memória de um container de executor:

```
memória do container
├─ overhead (off-heap, ~10% ou spark.executor.memoryOverhead)
│    └─ Python workers, buffers de rede, metaspace, Arrow
└─ heap JVM (spark.executor.memory)
     ├─ reserved (~300 MB)
     └─ usable = (heap - reserved)
          ├─ unified memory (spark.memory.fraction, default 0.6)
          │    ├─ execution  (shuffle, sort, hash de join, agregação)
          │    └─ storage    (cache/persist)
          │       └─ fronteira móvel: execution pode expulsar storage
          │          até spark.memory.storageFraction (default 0.5)
          └─ user memory (~0.4) — estruturas do usuário, metadados
```

Consequências práticas:

- `cache()` demais reduz memória de **execução** → mais spill em shuffle. Cache não é grátis; é troca.
- Execução pode expulsar cache, mas **não** o contrário. Um pipeline com shuffle pesado descarta o cache que você achava que estava lá.
- **Python worker vive no overhead, não no heap.** UDF Python pesado ou `pandas_udf` com batch grande estoura o *container* sem nunca encostar no heap. Aumentar `spark.executor.memory` não resolve; é `memoryOverhead` que precisa subir.

## 2. As sete classes de OOM

| Classe | Onde estoura | Assinatura no log / métrica | Causa típica | Correção que funciona |
|---|---|---|---|---|
| **Driver heap** | JVM do driver | `java.lang.OutOfMemoryError: Java heap space` no log do driver; `glue.driver.memory.heap.used.percentage` alto | `collect`/`toPandas`; broadcast de tabela grande; plano com milhares de operadores; listing de muitos arquivos | eliminar coleta ao driver; remover broadcast; reduzir plano; consertar layout de arquivos |
| **Executor heap** | JVM do executor | OOM no log do executor; executor removido; `glue.ALL.memory.heap.used.percentage` alto | partição grande demais; hash table de shuffled hash join; agregação de alta cardinalidade; skew | reduzir tamanho de partição; corrigir skew; trocar estratégia de join; worker R (2× memória) |
| **Container / overhead** | fora do heap | `Container killed by YARN for exceeding memory limits`; executor perdido **sem** OOM no log | Python worker (UDF); Arrow; buffers de rede | subir `spark.executor.memoryOverhead`; reduzir batch do `pandas_udf`; eliminar UDF Python |
| **Python worker** | processo Python | `MemoryError` no log Python; `PythonException` | `toPandas` num worker; UDF acumulando estado; biblioteca carregando tudo em memória | eliminar/reescrever UDF; `mapInPandas` com batch controlado |
| **Broadcast** | driver e executors | `Cannot broadcast the table that is larger than 8GB`; `broadcastTimeout` | hint `broadcast()` num lado que cresceu; estimativa de tamanho errada | remover hint; medir tamanho serializado; `autoBroadcastJoinThreshold = -1` para diagnosticar |
| **Metadata / plan explosion** | driver | driver lento antes de qualquer task; heap subindo no planejamento | `withColumn` em loop; centenas de milhares de partições Hive; muitos manifests Iceberg | um `select` com todas as colunas; manutenção de metadados; reduzir partições |
| **Disco (não é OOM, é confundido com um)** | disco local do worker | `No space left on device`; `DISK_NO_SPACE_ERROR`; `glue.ALL.disk.used.percentage` alto | spill massivo de shuffle; dado intermediário | reduzir shuffle; worker maior (mais disco); mais workers (mais disco somado) |

O caso mais mal diagnosticado é o terceiro. **Executor desaparecendo sem OOM no log é overhead, não heap.** Se a resposta foi "aumentei a memória e continuou", quase sempre foi `spark.executor.memory` quando devia ser `spark.executor.memoryOverhead`.

## 3. OOM que aparece "depois de horas"

Padrão específico e frequente em jobs full/bootstrap. Causas, em ordem de probabilidade:

1. **Acúmulo no driver ao longo de um loop.** Cada iteração adiciona plano, listeners de evento, ou resultado de action que não é liberado. Heap do driver sobe monotonicamente. Sinal: `glue.driver.memory.heap.used.percentage` com tendência crescente, não picos.
2. **Lineage/plano crescendo por iteração.** Sem `checkpoint()`, o plano de `df` acumula operadores em cada volta do loop. Após N iterações o planejamento em si estoura.
3. **Cache nunca liberado.** `cache()` dentro de loop sem `unpersist()` → storage cresce, execução sufoca, e o spill vira OOM.
4. **Commits Iceberg acumulando metadados.** Muitos appends → muitos snapshots e manifests → o planejamento de cada leitura seguinte carrega mais metadado no driver.
5. **Skew que só aparece no último lote.** O lote que contém a hot key falha; os anteriores passaram.

Diagnóstico decisivo: plotar heap do driver e do executor **ao longo do tempo** do run. Crescimento monotônico → acúmulo (1, 2, 3, 4). Pico isolado no fim → dado (5).

## 4. Spill

Spill é dado de execução escrito em disco porque não cabe na memória de execução. Não é erro; é degradação.

| Métrica | Limiar | Leitura |
|---|---|---|
| `spill(disk) / input` do stage | > 0 | há pressão de memória |
| `spill(disk) / input` | > 1 | está escrevendo mais do que leu — algoritmo ou partição inadequados |
| `spill(memory)` alto, `spill(disk)` = 0 | — | ainda cabe; margem apertada |

Spill não se corrige com mais memória primeiro. Ordem correta: reduzir o volume que entra no shuffle (filtro, projeção, pré-agregação) → aumentar número de partições (partições menores) → corrigir skew → só então mais memória por executor.

## 5. GC

| Métrica | Limiar | Ação |
|---|---|---|
| `GC time / executor run time` | > 10% | investigar |
| `GC time / executor run time` | > 20% | memory-bound; é o gargalo |

GC alto com heap **não** cheio indica muitos objetos de vida curta — típico de UDF Python, ou de conversão linha-a-linha. GC alto com heap cheio indica dado demais por executor.

## 6. O que medir antes de pedir mais memória

Nenhuma recomendação de aumentar worker ou memória sem estes seis números:

1. `glue.driver.memory.heap.used.percentage` — série temporal, não pico.
2. `glue.ALL.memory.heap.used.percentage` — série temporal.
3. `glue.ALL.disk.used.percentage` — descarta a classe "disco".
4. Spill (memory e disk) do stage dominante.
5. `GC time / run time` do stage dominante.
6. `max/median` de input das tasks do stage dominante — descarta skew.

Se 6 mostra skew, o problema não é memória. Se 3 está alto, o problema não é memória. Se 5 está alto com heap baixo, o problema é alocação de objetos, não capacidade.

## Fontes

- AWS Glue Observability metrics — nomes exatos de métrica (`glue.driver.memory.heap.used.percentage`, `glue.ALL.memory.*`, `glue.driver.disk.*`, `glue.ALL.disk.used.percentage`) e categorias de erro (`OUT_OF_MEMORY_ERROR`, `DISK_NO_SPACE_ERROR`). https://docs.aws.amazon.com/glue/latest/dg/monitor-observability.html (retrieved 2026-07-29)
- Apache Spark 3.5.6 — SQL Performance Tuning. https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- Defaults `spark.memory.fraction = 0.6` e `spark.memory.storageFraction = 0.5` são do Apache Spark; confirmar valor efetivo no Glue via aba Environment.
- Seções 3 e 6 são heurística de campo. A taxonomia das sete classes é organizadora, não uma classificação oficial da AWS — as categorias de erro do Glue Observability agrupam de forma mais grossa (`OUT_OF_MEMORY_ERROR` cobre driver e executor).
