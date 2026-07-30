# Como ler o plano físico

## 1. Modos de `explain`

| Modo | Uso |
|---|---|
| `df.explain("formatted")` | **preferido para diagnóstico.** Árvore compacta + detalhes numerados por operador |
| `df.explain(True)` | parsed, analyzed, optimized logical e physical — útil para ver o que o otimizador mudou |
| `df.explain("cost")` | inclui estatísticas estimadas — usar para checar se a estimativa de broadcast é confiável |
| `EXPLAIN` em SQL | equivalente para query SQL |

`explain("cost")` é subutilizado e resolve uma classe de dúvida direta: se o `sizeInBytes` estimado de um lado do join é absurdo (default de 8 EiB quando não há estatística), o `autoBroadcastJoinThreshold` não tem como funcionar corretamente.

## 2. Ler de baixo para cima

O plano físico executa das **folhas para a raiz**. `Scan` está embaixo; o operador final está no topo. Ler de cima para baixo inverte a ordem causal.

## 3. Campos que decidem o diagnóstico

### No nó de leitura (`FileScan` / `BatchScan`)

| Campo | O que responder |
|---|---|
| `PartitionFilters` | **o pruning de partição está acontecendo?** Vazio numa tabela particionada = lendo tudo |
| `PushedFilters` | quais predicados chegaram ao Parquet/Iceberg |
| `DataFilters` | predicados aplicados após a leitura (não empurrados) |
| `ReadSchema` | **quais colunas estão sendo lidas.** Se tem 80 colunas e a query usa 6, o pruning de coluna falhou |
| `Location` / `number of files` | contagem de arquivos — sinal de small files |

`PartitionFilters` vazio é o achado mais valioso e mais rápido de obter num plano. É onde o problema de tipo/`cast` de partição aparece.

Predicado que aparece em `DataFilters` mas não em `PushedFilters` foi rebaixado: chegou tarde, ou envolve UDF/função não suportada.

### No nó de join

| O que aparece | Leitura |
|---|---|
| `BroadcastHashJoin` | broadcast — checar se o lado pequeno realmente é pequeno |
| `SortMergeJoin` | dois shuffles + dois sorts |
| `ShuffledHashJoin` | hash table na memória do executor |
| `BroadcastNestedLoopJoin` | **alerta** — condição não-equi; custo O(n×m) |
| `CartesianProduct` | **alerta** — sem condição de join |
| `Exchange hashpartitioning(...)` | o shuffle; a chave listada é por onde foi redistribuído |

### Operadores que sinalizam custo

| Operador | Significa |
|---|---|
| `Exchange` | um shuffle. Contar os `Exchange` conta os shuffles |
| `Sort` | sort; candidato a spill |
| `HashAggregate` (dois níveis: partial + final) | agregação com shuffle no meio |
| `Window` | shuffle + sort por partição de janela |
| `Generate` | `explode` — checar fan-out de cardinalidade |
| `BatchEvalPython` / `ArrowEvalPython` | **UDF Python** — fronteira de codegen e de pushdown |
| `Coalesce` / `AQEShuffleRead` | ação do AQE em runtime |
| `ReusedExchange` | shuffle reaproveitado (bom) |
| `InMemoryTableScan` | leitura de cache |

`BatchEvalPython` no meio do plano é o achado que explica pushdown ausente acima dele. `ArrowEvalPython` é `pandas_udf` — melhor, mas ainda opaco ao otimizador.

`Exchange` em quantidade inesperada é o sinal mais confiável de trabalho não intencional. Um "job simples" com 8 `Exchange` tem 8 shuffles a justificar.

## 4. AQE: o plano do `explain` não é o plano executado

Com AQE ligado (default em Glue 4.0 e 5.x), o plano pode mudar após cada shuffle: coalescing de partições, conversão de sort-merge em broadcast, divisão de partições skewed.

Portanto:

- **Nunca concluir estratégia de join só pelo `explain()`.**
- O plano final está na **aba SQL do Spark UI**, que mostra os nós `AQEShuffleRead`, `Coalesced` e as métricas reais por operador.
- A aba SQL também liga **operador → stage**, que é o passo indispensável para correlacionar plano com métrica de task.

## 5. Correlacionar plano, stage e métrica

Sequência que fecha o diagnóstico:

1. Identificar o stage dominante no Spark UI (maior fração do runtime).
2. Na aba SQL, achar o nó de plano correspondente àquele stage.
3. Ler as métricas do nó: rows output, bytes, spill, tempo.
4. Comparar com o `explain` do código para localizar a **linha** que gerou o operador.
5. Ler p50/p95/max de task daquele stage.

O passo 4 é o que transforma "o stage 7 é lento" em "a linha 142 é o problema". Sem ele, o diagnóstico não é acionável.

## 6. Checklist rápido de plano

Percorrer sempre, na ordem:

1. `PartitionFilters` presente onde a tabela é particionada?
2. `ReadSchema` tem só as colunas necessárias?
3. Contagem de `Exchange` é justificável?
4. Alguma `BroadcastNestedLoopJoin` ou `CartesianProduct`?
5. Algum `BatchEvalPython` / `ArrowEvalPython`?
6. `Generate` com fan-out estimado?
7. Estratégia de cada join é a esperada — e confirmada no Spark UI, não só no `explain`?
8. `sizeInBytes` estimado (via `explain("cost")`) é plausível nos lados de join?

## Fontes

- Apache Spark 3.5.6 — SQL Performance Tuning (AQE, hints, comportamento de coalescing/skew/broadcast conversion). https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- Nomes de operador e campos de `FileScan` são estáveis em Spark 3.x, mas a formatação de `explain("formatted")` varia entre versões menores. Confirmar contra a saída real.
