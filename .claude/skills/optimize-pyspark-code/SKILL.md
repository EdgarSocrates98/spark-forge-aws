---
name: optimize-pyspark-code
description: Use quando revisar ou refatorar código PySpark/Spark SQL para AWS Glue (script, função, módulo, PR ou trecho de DataFrame) suspeito de UDF Python evitável, collect/toPandas, join sem redução prévia, cache indevido, coalesce(1), repartition arbitrário, explode sem controle ou trabalho desnecessário no driver.
---

# Optimize PySpark Code

## Procedimento

1. Identifique inputs, outputs, volume, SLA e runtime.
2. Mapeie actions e limites de lazy evaluation.
3. Localize scans, filters, projections, joins, aggregations, windows, sorts, explode, unions e writes.
4. Consulte `knowledge/anti-patterns.md`.
5. Estime mudanças de cardinalidade.
6. Identifique shuffles e recomputação.
7. Verifique uso do driver e UDFs.
8. Produza duas versões:
   - correção mínima de baixo risco;
   - refatoração estrutural, quando justificada.
9. Mostre diff ou blocos antes/depois.
10. Defina como confirmar a melhoria no plano e nas métricas.

## Preferências

1. Spark SQL/DataFrame nativo.
2. Higher-order functions.
3. Pandas UDF apenas quando inevitável e mensurável.
4. Python UDF apenas com justificativa.
5. Nunca mover grandes dados para o driver.

## Joins

- Reduza linhas e colunas antes do join.
- Confirme estratégia física.
- Não force broadcast sem medir tamanho serializado e margem.
- Analise nulls, duplicidade e hot keys.
- Avalie pré-agregação.
- Use hints como experimentos, não dogma.

## Cache

Só recomende se:
- houver reutilização real;
- recomputação for cara;
- memória útil for suficiente;
- storage level for adequado;
- houver plano para `unpersist`.

## Saída

- Achados por severidade.
- Explicação de como Spark executa.
- Código refatorado.
- Trade-offs.
- Plano de validação e benchmark.

## Quando NÃO usar

- O gargalo já está identificado em dados/infra (skew, small files, Iceberg, workers): use a skill específica.
- Revisão formal de PR com classificação P0–P4: use `review-pyspark-pr`.
- Precisa do plano físico para decidir: passe antes por `analyze-spark-plan`.

## Referência rápida

| Anti-pattern no código | Custo típico | Alternativa nativa |
|---|---|---|
| Python UDF em transformação simples | Serialização + sem codegen/pushdown | função Spark SQL / higher-order function |
| `collect()`/`toPandas()` sem `limit` | Driver OOM, gargalo serial | agregar/escrever distribuído |
| `join` sem `select`/`filter` antes | Shuffle e bytes desnecessários | projetar e filtrar cedo, pré-agregar |
| `coalesce(1)` para "1 arquivo" | Todo o dado em 1 task | `repartition` alvo + compactação controlada |
| `explode` sem estimar fan-out | Explosão de cardinalidade | estimar N; filtrar antes; posexplode seletivo |
| `withColumn` em loop (dezenas) | Plano gigante / driver | `select` único com todas as colunas |

## Red flags

- Forçar `broadcast()` sem medir o tamanho serializado do lado pequeno.
- `cache()`/`persist()` sem reutilização real e sem `unpersist`.
- `dropDuplicates()`/`distinct()` mascarando erro de modelagem em vez de corrigir a chave.
- Refatorar sem definir como validar contagem, schema, chaves e agregados de controle.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
