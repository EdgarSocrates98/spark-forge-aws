---
name: review-pyspark-pr
description: Use quando revisar um Pull Request PySpark/AWS Glue e precisar detectar regressões de performance, custo e escala — novas actions, shuffles, joins com cardinalidade, UDFs, collect, loops de DataFrame, mudança de write mode, particionamento e operações Iceberg/Parquet.
---

# Review PySpark PR

## Escopo

Analise somente impactos introduzidos ou alterados pelo PR, mas considere contexto suficiente para entender a execução.

## Classificação

- P0: corrupção, perda de dados, explosão de custo ou indisponibilidade provável.
- P1: regressão crítica comprovável.
- P2: problema relevante de escala/performance.
- P3: melhoria incremental.
- P4: sugestão experimental.

## Verificações

- Novas actions.
- Novos shuffles/exchanges.
- Join e cardinalidade.
- UDFs.
- Driver collection.
- Loops de DataFrame.
- Cache/persist.
- Repartition/coalesce.
- Mudanças de write mode.
- Particionamento físico.
- Iceberg merge/delete/snapshots.
- Arquivos e compactação.
- Logging que dispara jobs.
- Testes de correção e performance.

## Comentário de review

Cada comentário deve conter:
1. Problema.
2. Evidência no diff/plano.
3. Impacto.
4. Correção concreta.
5. Como testar.

Evite comentários genéricos sem ação.

## Quando NÃO usar

- Não é um diff/PR e sim refatoração exploratória: use `optimize-pyspark-code`.
- A mudança é de infraestrutura/IaC do job: use `review-glue-terraform`.
- Precisa comprovar o impacto com números: encadeie `benchmark-pyspark-job`.

## Referência rápida

| Mudança no diff | Risco de regressão | O que exigir do autor |
|---|---|---|
| novo `join` sem filtro/projeção antes | shuffle e custo | evidência de redução prévia; estratégia física |
| nova UDF Python | perda de codegen/pushdown | justificativa vs função nativa |
| `collect`/`toPandas`/`.rdd` novo | driver OOM | por que não distribuído |
| `withColumn` em loop / novos `union` | plano gigante | consolidar em `select` único |
| troca de write mode (overwrite/append/merge) | perda de dados / small files | escopo, idempotência, contagem |
| nova action em logging (`count`/`show`) | job extra oculto | remover ou medir custo |

## Red flags

- Aprovar sem plano de teste de correção (contagem, schema, chaves) para mudanças de escrita.
- Comentário genérico ("otimize isso") sem correção concreta e como validar.
- Ignorar operações Iceberg (merge/delete) que multiplicam commits/snapshots.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
