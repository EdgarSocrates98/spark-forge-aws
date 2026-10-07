# Catálogo de anti-patterns PySpark

## Driver

- `collect()` ou `toPandas()` em dados não limitados.
- Construção de listas/dicionários gigantes no driver.
- Loops que disparam uma action por iteração.
- `count()` apenas para logging.
- Criação de planos extremamente longos por loops de `withColumn` ou `union`.

## Transformações

- Python UDF onde existe função nativa.
- `select("*")` em leituras ou antes de joins.
- Filtro tardio.
- `distinct()` para esconder erro de modelagem.
- `dropDuplicates()` sem chave e sem regra temporal.
- `orderBy()` global sem necessidade.
- `explode()` sem estimar aumento de cardinalidade.
- Joins repetidos com a mesma dimensão.
- Conversões DynamicFrame/DataFrame repetidas.

## Particionamento

- `coalesce(1)`.
- `repartition(n)` sem relação com volume e recursos.
- Particionamento por coluna de cardinalidade extrema.
- Número excessivo de partições de saída.
- Partições grandes demais que causam spill/OOM.
- Salting global em vez de seletivo.

## Persistência

- `cache()` sem reutilização.
- Persistir datasets maiores que a memória útil.
- Não executar `unpersist()`.
- Checkpoint sem necessidade de truncar lineage ou garantir recuperação.

## Escrita

- Um arquivo por chave de alta cardinalidade.
- Append frequente gerando pequenos arquivos.
- Overwrite amplo quando overwrite dinâmico/merge seria adequado.
- Compactar sem política de custo e frequência.
