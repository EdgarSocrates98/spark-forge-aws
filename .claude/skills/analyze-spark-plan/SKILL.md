---
name: analyze-spark-plan
description: Use quando tiver a saída de df.explain (formatted/extended/cost) ou EXPLAIN e precisar interpretar scans, PartitionFilters/PushedFilters, Exchange/shuffle, estratégia de join (BroadcastHashJoin, SortMergeJoin, ShuffledHashJoin, BroadcastNestedLoopJoin, CartesianProduct), Sort, Window, HashAggregate, Generate/explode, UDF Python no plano (BatchEvalPython/ArrowEvalPython) e o antes/depois do AQE. Use também quando a pergunta for "por que não usa broadcast", "por que lê a tabela inteira", "o filtro não desceu pro scan" ou "quantos shuffles esse job tem", mesmo sem citar explain. Não existe parser de plano no toolkit — sparkforge não lê explain(). Se você está prestes a concluir causa (skew, spill, OOM) só pelo plano, rode `sparkforge analyze pyspark` e, se houver execução, `sparkforge analyze event-log` em vez disso — eles não leem o plano, mas cruzam o que o código pede e o que de fato rodou com as regras SF-PY-*, e é isso que confirma a causa, não o plano sozinho.
---

# Analyze Spark Plan

Este é o caso honesto do toolkit: não há `sparkforge analyze plan`. Nenhum extrator lê a saída de `explain()`. O plano revela operações declaradas, não distribuição real de dados, spill, GC ou a estratégia de join que o AQE efetivamente escolheu em runtime. Ler plano é trabalho de domínio, feito à mão, com o checklist de `knowledge/spark/plan-reading.md` — e depois cruzado com os facts que o toolkit computa de verdade.

## Procedimento

1. **Obtenha o plano físico.** `df.explain("formatted")` é o preferido para diagnóstico. `df.explain(True)` mostra parsed/analyzed/optimized logical e physical — útil pra ver o que o otimizador mudou. `df.explain("cost")` inclui estatística estimada. Nada disso passa pelo `sparkforge`; é PySpark puro.
2. **Leia de baixo para cima.** O plano executa das folhas (`Scan`) para a raiz. Percorra o checklist de `knowledge/spark/plan-reading.md` seção 6: `PartitionFilters` presente onde a tabela é particionada, `ReadSchema` só com as colunas usadas, contagem de `Exchange` justificável, ausência de `CartesianProduct`/`BroadcastNestedLoopJoin`, presença de `BatchEvalPython`/`ArrowEvalPython`, fan-out de `Generate`, estratégia de cada join confirmada (não só assumida).
3. **Nunca conclua estratégia de join só pelo `explain()`.** Com AQE ligado (default em Glue 4.0/5.x), o plano pode ser reescrito depois de cada shuffle. O plano final está na aba SQL do Spark UI, ou no event log real — não no `explain()` do código.
4. **Correlacione com o que o código pede.** `sparkforge analyze pyspark --path <arquivo ou diretório> --out .sparkforge/facts.json` extrai os facts estáticos por AST (`pyspark.join`, `pyspark.udf`, `pyspark.explode`, `pyspark.partitioning`, `pyspark.chain`, `pyspark.withcolumn_run`) que dão nome de arquivo e linha a cada operador suspeito do plano.
5. **Julgue esses facts.** `sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped` aplica o catálogo `SF-PY-*` (`rules/catalog/pyspark.yaml`). Cada regra que dispara aponta um operador do plano e a linha exata de origem — é o passo que transforma "o Exchange 3 é caro" em "a linha 142 é o problema".
6. **Se há execução real, feche o ciclo.** `sparkforge analyze event-log --path <log> --out .sparkforge/facts.json` (procedimento completo em `analyze-spark-ui`) confirma se o operador suspeito do plano realmente custou — duração, spill, GC do stage correspondente àquele nó do plano.

## Do operador do plano à regra que o correlaciona

Esta é a correlação central desta skill: nenhuma dessas linhas tem limiar numérico porque não é uma regra de execução — é uma correlação estrutural entre o que aparece no plano e o fact estático que a justifica.

## Referência rápida

| Operador no plano | Regra `SF-PY` correlacionada | Fact que a regra consome |
|---|---|---|
| `BatchEvalPython` / `ArrowEvalPython` | `SF-PY-001` | `pyspark.udf` |
| `Exchange` antes de `Filter`/`Project` tardio | `SF-PY-003` | `pyspark.chain`, `pyspark.join` |
| `Generate` (explode) | `SF-PY-006` | `pyspark.explode` |
| Redução para uma única partição de saída | `SF-PY-005` | `pyspark.partitioning` |
| `BroadcastHashJoin` por hint fixo no código | `SF-PY-009` | `pyspark.join` |
| `Exchange` de repartition com argumento literal | `SF-PY-010` | `pyspark.partitioning` |
| Sequência longa de projeções antes do plano final | `SF-PY-007` | `pyspark.withcolumn_run` |

Limiares e severidade de cada regra vêm de `sparkforge rules lookup --id <ID>`, nunca de memória — o catálogo muda, e um número decorado vira mentira silenciosa.

## Quando NÃO usar

- Você já tem métricas de execução (Spark UI/event log) e quer o gargalo real: use `analyze-spark-ui`.
- Skew ou OOM já confirmados: aprofunde em `diagnose-data-skew` ou `diagnose-oom`.
- Ainda não tem o `explain`: gere com `df.explain("formatted")` antes de abrir esta skill.

## Red flags

- Afirmar causa (skew, spill, OOM) só pelo plano, sem métrica de task real.
- Tratar o plano exibido como o plano executado — ele pode ser o inicial, antes do AQE reescrever em runtime.
- Ler `sizeInBytes` do modo `cost` como verdade quando não há estatística atualizada na tabela.
- Esperar que `sparkforge` tenha um verbo para ler o plano. Não tem; inventar um comando aqui falha de forma confusa em vez de simplesmente não ajudar.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
