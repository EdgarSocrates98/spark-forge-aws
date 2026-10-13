# Referência de configuração Spark

Defaults abaixo são os do **Apache Spark 3.5.6** (runtime do Glue 5.1). O AWS Glue sobrescreve parte deles. **Sempre confirme o valor efetivo** via `spark.conf.get("<chave>")` no job ou na aba *Environment* do Spark UI antes de recomendar mudança.

## 1. Adaptive Query Execution

AQE é ligado por default desde Spark 3.2.0. Em Glue 4.0 (Spark 3.3) e 5.x (Spark 3.5) está ativo salvo desligamento explícito.

| Propriedade | Default | Significado |
|---|---|---|
| `spark.sql.adaptive.enabled` | `true` | Chave mestra do AQE |
| `spark.sql.adaptive.advisoryPartitionSizeInBytes` | `64MB` | Tamanho-alvo de partição para coalescing e skew |
| `spark.sql.adaptive.coalescePartitions.enabled` | `true` | Junta partições pós-shuffle pequenas |
| `spark.sql.adaptive.coalescePartitions.parallelismFirst` | `true` | Prioriza paralelismo sobre tamanho-alvo |
| `spark.sql.adaptive.coalescePartitions.minPartitionSize` | `1MB` | Piso de tamanho após coalescing |
| `spark.sql.adaptive.coalescePartitions.initialPartitionNum` | (vazio) | Cai para `spark.sql.shuffle.partitions` |
| `spark.sql.adaptive.skewJoin.enabled` | `true` | Divide partições skewed em sort-merge join |
| `spark.sql.adaptive.skewJoin.skewedPartitionFactor` | `5.0` | Fator vs. mediana para considerar skew |
| `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` | `256MB` | Piso absoluto para considerar skew |
| `spark.sql.adaptive.forceOptimizeSkewedJoin` | `false` | Força a regra de skew join |
| `spark.sql.adaptive.localShuffleReader.enabled` | `true` | Evita tráfego de rede após conversão de join |
| `spark.sql.adaptive.autoBroadcastJoinThreshold` | (vazio) | Cai para `spark.sql.autoBroadcastJoinThreshold` |
| `spark.sql.adaptive.optimizeSkewsInRebalancePartitions.enabled` | `true` | Divide partições skewed em rebalance |
| `spark.sql.adaptive.rebalancePartitionsSmallPartitionFactor` | `0.2` | Fator de junção de partições pequenas |
| `spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold` | `0` | Acima de 0, prefere shuffled hash join a sort-merge |
| `spark.sql.adaptive.optimizer.excludedRules` | (vazio) | Desliga regras específicas do AQE |

**`parallelismFirst = true` é a pegadinha mais comum.** Com ele ligado, `advisoryPartitionSizeInBytes` é tratado como sugestão fraca: o AQE prioriza usar todos os cores, e as partições podem ficar bem menores que 64 MB. Se você quer de fato o tamanho-alvo respeitado, precisa `parallelismFirst = false` **junto** com o `advisory`. Mudar só o `advisory` e não observar efeito é sintoma disso, não de "AQE não funciona".

### O que AQE não resolve

Skew em `groupBy` sem join, skew causado por chave nula concentrada (a divisão não separa nulls), broadcast de lado grande forçado por hint, small files na leitura (AQE age pós-shuffle, não na leitura), e explosão de cardinalidade por `explode`.

## 2. Shuffle e join

| Propriedade | Default | Significado |
|---|---|---|
| `spark.sql.shuffle.partitions` | `200` | Partições pós-shuffle. Com AQE, é o **teto inicial**, não o final |
| `spark.sql.autoBroadcastJoinThreshold` | `10MB` | Tamanho máximo estimado para broadcast automático. `-1` desliga |
| `spark.sql.broadcastTimeout` | `300` s | Timeout de espera do broadcast |
| `spark.sql.join.preferSortMergeJoin` | `true` | Preferir sort-merge a shuffled hash join |

Com AQE ligado, `spark.sql.shuffle.partitions` deixa de ser o número tunado à mão e passa a ser o ponto de partida do coalescing. Manter alto (500–2000) e deixar o AQE reduzir é geralmente melhor que fixar 200, **desde que** o custo de criar tantas tasks vazias seja aceitável. Em job pequeno, 2000 partições iniciais é overhead puro.

`autoBroadcastJoinThreshold` compara contra o **tamanho estimado pelo otimizador**, não o tamanho serializado real. Estatística ausente ou ruim (tabela sem `ANALYZE`, fonte sem estatística) faz a estimativa errar em ordens de magnitude — nos dois sentidos.

## 3. Leitura de arquivos

| Propriedade | Default | Significado |
|---|---|---|
| `spark.sql.files.maxPartitionBytes` | `128MB` | Máximo de bytes por partição de leitura |
| `spark.sql.files.openCostInBytes` | `4MB` | Custo estimado de abrir um arquivo |
| `spark.sql.files.minPartitionNum` | default parallelism | Piso sugerido de partições de leitura |
| `spark.sql.files.maxPartitionNum` | (vazio) | Teto sugerido de partições de leitura |
| `spark.sql.sources.parallelPartitionDiscovery.threshold` | `32` | A partir de N paths, listing paralelo |
| `spark.sql.sources.parallelPartitionDiscovery.parallelism` | `10000` | Paralelismo máximo de listing |

`openCostInBytes = 4MB` é a chave para entender small files: **um arquivo de 10 KB é contabilizado como 4 MB** no cálculo de empacotamento. Com 100.000 arquivos pequenos, o planejamento raciocina sobre ~400 GB "virtuais" e o job gasta o tempo abrindo arquivos, não lendo dados. Aumentar workers não corrige isso — o gargalo é contagem de arquivos e round-trips S3.

## 4. Cache colunar

| Propriedade | Default | Significado |
|---|---|---|
| `spark.sql.inMemoryColumnarStorage.compressed` | `true` | Comprime colunas em cache |
| `spark.sql.inMemoryColumnarStorage.batchSize` | `10000` | Linhas por batch no cache colunar |

## 5. Hints de SQL (Spark 3.5)

```sql
-- join
SELECT /*+ BROADCAST(r) */      * FROM records r JOIN src s ON r.key = s.key
SELECT /*+ MERGE(r) */          ...   -- força sort-merge
SELECT /*+ SHUFFLE_HASH(r) */   ...
SELECT /*+ SHUFFLE_REPLICATE_NL(r) */ ...

-- particionamento
SELECT /*+ COALESCE(3) */               * FROM t;
SELECT /*+ REPARTITION(3, c) */         * FROM t;
SELECT /*+ REPARTITION_BY_RANGE(3, c) */ * FROM t;
SELECT /*+ REBALANCE(3, c) */           * FROM t;
```

`REBALANCE` é o hint mais subutilizado: produz partições de tamanho parecido **e** coopera com AQE para dividir as skewed. É a ferramenta correta para "quero arquivos de saída equilibrados", em vez de `repartition(n)` chutado.

Hint é **experimento**, não solução permanente. Um `BROADCAST` fixo no código vira bomba-relógio quando o lado "pequeno" cresce: o driver materializa a tabela antes de distribuir, e o modo de falha é OOM de driver ou `broadcastTimeout`, não degradação gradual.

## 6. Ordem de precedência de configuração no Glue

Do menos para o mais forte:

1. Default do Apache Spark
2. Default do AWS Glue para a versão
3. `--conf` em *default arguments* (Terraform / job definition)
4. `SparkConf` na criação da sessão no script
5. `spark.conf.set(...)` em runtime, antes da action relevante

Item 5 sobrescreve silenciosamente o Terraform. É a causa mais comum de "mudei no IaC e nada aconteceu". Diagnóstico: procurar `pyspark.conf_set` no código e comparar com os default arguments.

Configs que **não** podem mudar após a sessão iniciar (precisam ir em 3 ou 4): `spark.executor.memory`, `spark.executor.cores`, `spark.driver.memory`, `spark.serializer`, `spark.sql.warehouse.dir`, registro de extensão/catálogo Iceberg.

## Fontes

- Apache Spark 3.5.6 — SQL Performance Tuning (todos os defaults das seções 1–4). https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- Seção 6 é conhecimento operacional de Glue, verificado contra o comportamento documentado de default arguments; tratar a ordem exata como hipótese verificável via aba Environment do Spark UI.
