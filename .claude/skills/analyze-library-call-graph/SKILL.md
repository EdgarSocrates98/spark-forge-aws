---
name: analyze-library-call-graph
description: Use quando o job Glue chama uma biblioteca Python com múltiplos módulos e você precisa mapear, além do entrypoint, onde estão leituras, actions, caches, loops, UDFs, mudanças de Spark config e writes escondidos (ex.: count() em logger, persist sem unpersist, action dentro de helper).
---

# Analyze Library Call Graph

## Objetivo

Não revisar apenas o entrypoint. Seguir imports e chamadas até as funções que executam trabalho Spark.

## Mapear

- entrypoint;
- módulos internos;
- factories;
- decorators;
- helpers;
- classes;
- callbacks;
- plugins;
- funções de leitura;
- transformações;
- actions;
- writes;
- logging;
- configuração Spark;
- UDFs;
- conversões DynamicFrame/DataFrame.

## Marcação obrigatória

Para cada função:

```yaml
function:
  module:
  name:
  callers:
  reads:
  transformations:
  actions:
  writes:
  cache:
  loops:
  spark_conf_changes:
  udf_usage:
  side_effects:
```

## Sinais críticos

- `count()` escondido em logger;
- leitura duplicada;
- write dentro de helper;
- persist sem unpersist;
- Spark config alterada no meio do pipeline;
- UDF registrada globalmente;
- funções que retornam DataFrame mas também executam action;
- loops indiretos;
- reconversão DynamicFrame/DataFrame;
- plano gerado por dezenas/centenas de `withColumn`.

## Saída

- grafo textual/Mermaid;
- mapa de actions;
- mapa de leituras/escritas;
- caminhos críticos;
- funções prioritárias para profiling/refatoração.

## Quando NÃO usar

- O código é um único script curto sem biblioteca: vá direto a `optimize-pyspark-code`.
- Você já tem o mapa e quer atacar o batching ou o incremental: use `analyze-batch-loop` / `design-incremental-processing`.
- Precisa do plano físico de uma query específica: use `analyze-spark-plan`.

## Referência rápida

| O que procurar | Onde costuma se esconder | Por que importa |
|---|---|---|
| actions | logger, validações, `assert`, helpers | disparam jobs/recomputação não óbvios |
| writes | funções utilitárias, callbacks | commits e small files fora do fluxo principal |
| leituras duplicadas | factories, imports repetidos | mesma fonte lida N vezes |
| `persist` sem `unpersist` | classes com estado | memória retida por todo o job |
| mudança de Spark conf | setup no meio do pipeline | comportamento diferente entre etapas |

## Red flags

- Concluir a análise só pelo entrypoint, sem seguir imports até as funções que executam trabalho Spark.
- Ignorar actions embutidas em logging/validação como fonte de jobs extras.
- Não marcar funções que retornam DataFrame mas também disparam action (efeito colateral).
