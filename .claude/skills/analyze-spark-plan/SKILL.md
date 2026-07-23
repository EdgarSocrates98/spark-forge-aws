---
name: analyze-spark-plan
description: Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, pushed filters, partition pruning, Exchange/shuffle, estratégia de join (BroadcastHashJoin, SortMergeJoin, Cartesian), Sort, Window, agregações e efeitos do AQE para localizar o caminho crítico.
---

# Analyze Spark Plan

## Entradas aceitas

- `df.explain("formatted")`
- `df.explain("extended")`
- `df.explain("cost")`
- `EXPLAIN FORMATTED`
- `EXPLAIN EXTENDED`
- Plano inicial/final do AQE

## Procedimento

1. Diferencie parsed, analyzed, optimized logical plan e physical plan.
2. Identifique cada scan e registre:
   - colunas lidas;
   - partition filters;
   - data filters;
   - pushed filters;
   - tamanho/estatísticas, quando disponíveis.
3. Marque todo `Exchange`.
4. Classifique joins:
   - BroadcastHashJoin;
   - SortMergeJoin;
   - ShuffledHashJoin;
   - BroadcastNestedLoopJoin;
   - CartesianProduct.
5. Identifique Sort, Window, HashAggregate, SortAggregate, Generate e Union.
6. Confirme se AQE alterou estratégia, coalesceu shuffle ou tratou skew.
7. Trace o caminho crítico provável.
8. Relacione hipóteses às abas/stages que devem ser verificadas no Spark UI.

## Não concluir apenas pelo plano

O plano revela operações, mas não prova distribuição dos dados, spill, GC, skew real ou saturação. Solicite métricas quando necessário.

## Saída por operador

| Operador | Função | Evidência | Risco | Hipótese | Como validar | Alternativa |
|---|---|---|---|---|---|---|

## Quando NÃO usar

- Você tem métricas de execução (Spark UI/event logs) e quer o gargalo real: use `analyze-spark-ui`.
- Suspeita confirmada de skew ou OOM: vá para `diagnose-data-skew` ou `diagnose-oom`.
- Ainda não tem o `explain`: gere-o com `df.explain("formatted")` antes.

## Referência rápida

| Operador no plano | O que observar | Sinal de alerta |
|---|---|---|
| `Scan parquet`/`BatchScan` | PushedFilters, PartitionFilters, ReadSchema | ler todas as colunas; filtro não empurrado |
| `Exchange hashpartitioning` | número e origem do shuffle | vários exchanges na mesma chave; re-shuffle |
| `SortMergeJoin` | tamanho dos dois lados | lado pequeno que caberia em broadcast |
| `BroadcastHashJoin` | lado transmitido | broadcast de tabela grande (risco de OOM) |
| `CartesianProduct` / `BroadcastNestedLoopJoin` | condição de join | join sem condição de igualdade |
| `AdaptiveSparkPlan` | `isFinalPlan=true`? coalesce/skew | comparar plano inicial × final do AQE |

## Red flags

- Afirmar causa (skew, spill) só pelo plano, sem métrica de task.
- Ignorar que o plano exibido pode ser o inicial, antes do AQE reescrever no runtime.
- Ler tamanho por `sizeInBytes` do modo `cost` como verdade quando não há estatísticas atualizadas.
