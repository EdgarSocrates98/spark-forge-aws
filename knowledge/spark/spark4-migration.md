# Migração Apache Spark 3.5 → 4.0 → 4.1

Glue 6.0 roda Spark 4.1.1; Glue 5.1 roda 3.5.6; Glue 4.0 roda 3.3.0. Um salto de Glue 4.0
para 6.0 atravessa as duas fronteiras de uma vez. Ver
[`../glue/runtime-matrix.md`](../glue/runtime-matrix.md).

## 1. ANSI mode

Ligado por padrão a partir de 4.0 (`spark.sql.ansi.enabled`). No SparkForge isso é
`SF-MIG-003`, guardado por Glue 6.0 — não é repetido aqui como regra.

## 2. Configurações que mudaram de nome em 4.0

As configs de rebase de data/hora perderam o prefixo `legacy`. O nome antigo **não** é lido:

| nome em 3.5 | nome em 4.0+ |
|---|---|
| `spark.sql.legacy.parquet.int96RebaseModeInWrite` | `spark.sql.parquet.int96RebaseModeInWrite` |
| `spark.sql.legacy.parquet.datetimeRebaseModeInWrite` | `spark.sql.parquet.datetimeRebaseModeInWrite` |
| `spark.sql.legacy.parquet.int96RebaseModeInRead` | `spark.sql.parquet.int96RebaseModeInRead` |
| `spark.sql.legacy.avro.datetimeRebaseModeInWrite` | `spark.sql.avro.datetimeRebaseModeInWrite` |
| `spark.sql.legacy.avro.datetimeRebaseModeInRead` | `spark.sql.avro.datetimeRebaseModeInRead` |

O codec Parquet `lz4raw` deixou de ser aceito; o nome passou a ser `lz4_raw`.

O risco é o mesmo de `fs.s3.consistent` no Glue 5 (ver `SF-MIG-002`): **silêncio**. A chave
antiga não causa erro, e quem lê o job vê uma configuração que parece ativa e não está.

## 3. APIs de pandas-on-Spark removidas em 4.0

Removidas sem substituto compatível por assinatura:

| removida | substituta |
|---|---|
| `DataFrame.append`, `Series.append` | `ps.concat` |
| `DataFrame.iteritems`, `Series.iteritems` | `.items` |
| `DataFrame.to_koalas` | `DataFrame.pandas_api` |
| `DataFrame.koalas` | `DataFrame.pandas_on_spark` |
| `DataFrame.get_dtype_counts` | `DataFrame.dtypes.value_counts()` |
| `Series.is_monotonic`, `Index.is_monotonic` | `.is_monotonic_increasing` |
| `DataFrameGroupBy.backfill` | `DataFrameGroupBy.bfill` |
| `DataFrameGroupBy.pad` | `DataFrameGroupBy.ffill` |
| `DataFrame.mad`, `Series.mad` | sem substituto |
| `Int64Index`, `Float64Index` | `Index` |

`from pyspark.sql.functions import *` deixou de exportar `DataFrame`, `Column` e
`StructType`; eles vêm de `pyspark.sql` e `pyspark.sql.types`.

## 4. Piso de dependência Python em 4.0 e 4.1

| pacote | piso em 4.0 | piso em 4.1 |
|---|---|---|
| PyArrow | 11.0.0 | 15.0.0 |
| pandas | 2.0.0 | 2.2.0 |
| NumPy | 1.21 | 1.21 |

Python 3.8 deixou de ser suportado em 4.0, e 3.9 em 4.1. Glue 6.0 roda Python 3.13, então a
fronteira do interpretador não morde ali — o que morde é o **pin** de um pacote no
`requirements.txt` do job, que continua valendo o que estava escrito.

## 5. Mudanças de comportamento sem sinal no código

Estas não são detectáveis por análise estática do job; entram aqui como conhecimento para
quem desenha o plano de regressão:

- `spark.sql.legacy.timeParserPolicy` e `spark.sql.legacy.ctePrecedencePolicy` passam de
  `EXCEPTION` para `CORRECTED` por padrão.
- Codec padrão do ORC passa de `snappy` para `zstd` (`spark.sql.orc.compression.codec`).
- `spark.sql.maxSinglePartitionBytes` passa de `Long.MaxValue` para `128m`.
- Cast de timestamp com overflow fora do ANSI passa a devolver `null` em vez do valor
  circular.
- Storage-Partitioned Join passa a ligado por padrão.

## Fontes

- Migration Guide: SQL, Datasets and DataFrame — Apache Spark 4.1.1. https://spark.apache.org/docs/4.1.1/sql-migration-guide.html (retrieved 2026-08-22)
- Upgrading PySpark — Apache Spark 4.1.1. https://spark.apache.org/docs/4.1.1/api/python/migration_guide/pyspark_upgrade.html (retrieved 2026-08-22)
