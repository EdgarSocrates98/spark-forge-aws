# Modelo de execução do Spark

Base para raciocinar linha a linha. Sem este modelo, revisão de código PySpark é adivinhação.

## 1. Lazy evaluation e a fronteira da action

Transformações (`select`, `filter`, `join`, `withColumn`, `groupBy`) **não executam nada**. Elas constroem um plano lógico. Nada roda até uma **action**.

Consequência prática: o custo não está na linha da transformação, está na linha da action. Um `filter` na linha 40 e um `count()` na linha 200 formam **um único** job — e é a linha 200 que aparece no Spark UI.

### Actions (a lista completa que importa)

| Action | Traz dados ao driver? | Nota |
|---|---|---|
| `collect()` | **sim, tudo** | risco de driver OOM proporcional ao resultado |
| `toPandas()` | **sim, tudo** | pior que `collect`: cópia + conversão |
| `toLocalIterator()` | sim, por partição | menos pico de memória, mais round-trips |
| `head(n)` / `take(n)` / `first()` | sim, n linhas | limitado; costuma ser seguro |
| `show()` | sim, 20 linhas default | seguro, mas dispara job completo se houver sort/agregação |
| `count()` | não (só o número) | **dispara o DAG inteiro** |
| `isEmpty()` | não | mais barato que `count() == 0` |
| `foreach` / `foreachPartition` | não | executa nos executors |
| `write.*` / `save` / `saveAsTable` / `insertInto` | não | action de escrita |
| `writeTo(...).append()/.overwritePartitions()` | não | Iceberg (DataFrameWriterV2) |

`spark.sql("...")` **não** é action — devolve DataFrame. `spark.sql("INSERT ...")` ou `spark.sql("CALL ...")` executam de imediato.

### Por que isso importa em revisão

`count()` usado para log é o anti-pattern mais barato de encontrar e mais caro de manter: cada `logger.info(f"{df.count()} registros")` é um DAG completo a mais. Dois `count()` no mesmo `df` sem cache = dois DAGs.

## 2. Job → Stage → Task

- **Job**: um por action.
- **Stage**: fronteira de shuffle. Cada shuffle divide o job em mais um stage.
- **Task**: uma por partição, dentro de um stage. É a unidade de paralelismo e a unidade que aparece com métrica de duração, input, spill e GC.

Operações que **criam fronteira de shuffle** (wide transformations): `groupBy`/`agg`, `join` (exceto broadcast), `distinct`, `dropDuplicates`, `repartition`, `orderBy`/`sort` global, `Window` com `partitionBy`, `intersect`, `except`, `cube`/`rollup`.

Operações **sem shuffle** (narrow): `select`, `filter`, `withColumn`, `map`, `flatMap`, `union`, `coalesce` (reduz sem shuffle), `mapPartitions`, `explode`.

Regra de leitura: **número de stages ≈ número de shuffles + 1**. Se um job "simples" tem 14 stages, há shuffles não intencionais.

## 3. Onde o pushdown morre

Spark empurra filtro e projeção para a camada de leitura (Parquet/Iceberg). Isso é o maior ganho disponível e é fácil de destruir.

| Padrão | Pushdown de predicado | Pruning de coluna | Pruning de partição |
|---|---|---|---|
| `spark.read.parquet(p).filter(col("d") == "2026-01-01")` | sim | sim | sim, se `d` é coluna de partição |
| `filter` **depois** de `join` | não chega na leitura do lado grande | parcial | não |
| `filter` com **Python UDF** | **não** — UDF é caixa preta | sim | não |
| `filter` com `rand()` ou função não-determinística | não | sim | não |
| `filter` sobre coluna resultado de UDF/expressão complexa | não | sim | não |
| leitura via `DynamicFrame` sem `push_down_predicate` | não | limitado | só com `push_down_predicate`/`catalogPartitionPredicate` |
| `cast` implícito incompatível na comparação de partição | pode falhar silenciosamente | sim | frequentemente **não** |

O item do `cast` é a armadilha silenciosa: partição `dt` gravada como `string` e filtrada como `date` (ou vice-versa) pode ler tudo. Verificar sempre no plano físico, em `PartitionFilters`, não no código.

## 4. UDF Python: o custo real

Um `pyspark.sql.functions.udf` custa, por linha:

1. Serialização da linha JVM → formato pickle.
2. Cópia para o processo Python worker (pipe).
3. Execução do bytecode Python (sem vetorização).
4. Serialização de volta.
5. Desserialização na JVM.

Além disso, perde-se **whole-stage codegen** para todo o segmento do plano, e o operador vira opaco para o otimizador (sem pushdown, sem reordenação de predicado).

| Tipo | Serialização | Vetorizado | Codegen | Pushdown |
|---|---|---|---|---|
| Função Spark SQL nativa | nenhuma | sim | sim | sim |
| Higher-order function (`transform`, `filter`, `aggregate` sobre array) | nenhuma | sim | sim | parcial |
| `pandas_udf` (Arrow) | Arrow em lote | sim (por batch) | não | não |
| `udf` Python | por linha, pickle | não | não | não |

Ordem de preferência: nativa → higher-order → `pandas_udf` → `udf`. Um `udf` só se justifica com medição mostrando que a alternativa não existe.

## 5. Cache: quando ajuda e quando piora

`cache()` / `persist()` materializa o resultado para reuso. Só compensa se **todas** forem verdadeiras:

1. O DataFrame é usado em **duas ou mais** actions distintas.
2. Recomputá-lo é caro (envolve shuffle ou leitura ampla).
3. Há memória de executor sobrando para ele.
4. Existe `unpersist()` quando deixa de ser necessário.

Quando piora: ocupa memória de execução → mais spill em shuffle; `MEMORY_AND_DISK` com dado grande vira I/O extra; cache antes de um `filter` seletivo materializa dado que seria descartado.

`StorageLevel` relevante em Glue: `MEMORY_AND_DISK` (default de `cache()` em DataFrame) e `MEMORY_AND_DISK_SER` (menos memória, mais CPU).

Sinal de cache inútil no Spark UI: aba Storage mostrando fração baixa de cache e stages repetindo a mesma leitura.

## 6. Recomputação de DAG em loop

Padrão que domina jobs "de batch":

```python
for lote in lotes:                      # 50 iterações
    df_lote = df_caro.filter(col("lote") == lote)   # df_caro NÃO está materializado
    df_lote.write.format("iceberg").mode("append").save(tabela)
```

Cada iteração executa `df_caro` **inteiro** de novo — 50 vezes o custo de leitura, joins e shuffles, e o filtro descarta 98% do resultado. O batching reduziu o tamanho da escrita, não o trabalho.

Alternativas, em ordem de preferência: escrever tudo numa action com `partitionBy` da coluna de lote; materializar `df_caro` uma vez (checkpoint ou tabela intermediária) antes do loop; ou reduzir na origem (filtro que chega ao pushdown), não depois do DAG caro.

Diagnóstico: `pyspark.loop` contendo `pyspark.write`/`pyspark.action`, e no Spark UI N jobs quase idênticos com o mesmo primeiro stage.

## 7. Trabalho no driver

O driver executa: construção do plano, planejamento (inclusive listing de arquivos e resolução de partições), coleta de resultados de action, e o loop Python do script.

Fontes de gargalo de driver: listing de dezenas de milhares de arquivos S3; plano com milhares de operadores (loop de `withColumn`); broadcast de tabela grande (o driver materializa antes de distribuir); `collect`/`toPandas`; laço Python serial disparando actions.

## 8. AQE muda o plano em tempo de execução

Com AQE ligado (default desde Spark 3.2), o plano que você vê em `explain()` **não é** o plano executado. AQE pode, após cada shuffle: coalescer partições, converter sort-merge join em broadcast, e dividir partições skewed.

Consequência para diagnóstico: nunca conclua estratégia de join só pelo `explain()`. Confirme no Spark UI (aba SQL mostra o plano final, com nós `AQEShuffleRead` e `Coalesced`), ou use `df.explain("formatted")` mais as métricas reais do stage.

## Fontes

- Apache Spark 3.5.6 — SQL Performance Tuning. https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- AWS Prescriptive Guidance — Best practices for performance tuning AWS Glue for Apache Spark jobs. https://docs.aws.amazon.com/prescriptive-guidance/latest/tuning-aws-glue-for-apache-spark/introduction (retrieved 2026-07-29)
- Heurísticas das seções 6 e 7 são de campo, não de documentação oficial. Tratar como hipótese até medir.
