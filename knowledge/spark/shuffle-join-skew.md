# Shuffle, joins e skew

## 1. Estratégias físicas de join

| Estratégia | Como aparece no plano | Shuffle | Quando o Spark escolhe | Modo de falha |
|---|---|---|---|---|
| Broadcast Hash Join | `BroadcastHashJoin` | não (broadcast) | lado pequeno estimado < `autoBroadcastJoinThreshold` (10 MB) ou hint | driver OOM; `broadcastTimeout`; executor OOM se a hash table não cabe |
| Sort Merge Join | `SortMergeJoin` | ambos os lados | default para joins grandes com chave ordenável | spill de sort; skew concentra em poucas tasks |
| Shuffled Hash Join | `ShuffledHashJoin` | ambos os lados | `preferSortMergeJoin=false` ou `maxShuffledHashJoinLocalMapThreshold` > 0 | executor OOM (hash table na memória) |
| Broadcast Nested Loop | `BroadcastNestedLoopJoin` | não | condição não-equi (`<`, `between`, `like`) | explosão quadrática; é o sinal de alerta mais forte do plano |
| Cartesian | `CartesianProduct` | sim | sem condição de join | quase sempre bug |

`BroadcastNestedLoopJoin` ou `CartesianProduct` num plano de job grande deve ser tratado como P0 até prova em contrário. Custo é O(n×m).

## 2. Custo do shuffle

Um shuffle move dados entre executors. Por partição de saída, o custo é: serialização → escrita em disco local do mapper → transferência de rede → leitura pelo reducer → possivelmente sort/spill.

O que reduz shuffle, em ordem de eficácia:

1. **Filtrar antes.** Predicado que chega ao pushdown remove bytes que nunca entram no shuffle.
2. **Projetar antes.** `select` das colunas usadas antes do join. Uma tabela de 80 colunas onde o join usa 6 desperdiça ~92% da banda de shuffle.
3. **Pré-agregar.** Se o join é seguido de `groupBy`, agregar o lado grande antes reduz cardinalidade na origem do shuffle.
4. **Broadcast do lado pequeno** — quando ele *é* pequeno e medido.
5. **Bucketing** na tabela de origem (elimina shuffle em joins recorrentes pela mesma chave). Alto custo de escrita; só vale para tabela lida muitas vezes pela mesma chave.
6. **Reordenar joins** para que os mais seletivos aconteçam primeiro.

Aumentar workers **não reduz** shuffle — distribui o mesmo volume por mais nós, com mais conexões de rede.

## 3. Diagnóstico de skew

Skew é distribuição desigual de dados por partição. Sintoma canônico: o stage termina quando a última task termina, e uma task leva 20× a mediana.

### Métricas e limiares

| Métrica | Limiar de alerta | Interpretação |
|---|---|---|
| `max task duration / median` | ≥ 3, crescente | candidato a skew |
| `max task duration / median` | ≥ 10 | skew dominante |
| `max task input bytes / median` | ≥ 3 | skew de **dados** (não de computação) |
| coeficiente de variação da duração | > 1 | distribuição muito dispersa |
| `spill (memory + disk) / input` | > 1 | partição não cabe na memória de execução |
| `glue.driver.skewness.stage` | > 0 | Glue já detectou; > 1 = razão ≥ 2× o fator |
| `glue.driver.skewness.job` | > 0 | skew ponderado pela duração do stage |

Distinção que muda a ação: `max/median` alto **com** `input` uniforme indica skew de *computação* (UDF caro em certas linhas, `explode` desigual), não de dados. Repartition não resolve isso.

### Causas, na ordem em que aparecem na prática

1. **Chave nula.** `NULL` em join agrupa tudo numa partição. AQE **não** divide isso.
2. **Hot key natural.** Cliente/loja/tenant que concentra 30% do volume.
3. **Valor sentinela.** `-1`, `0`, `"UNKNOWN"`, `"N/A"` usados como "sem valor".
4. **Cardinalidade baixa de partição.** `partitionBy` numa coluna com 3 valores distintos.
5. **`explode` desigual.** Array com 2 elementos na maioria das linhas e 50.000 em algumas.
6. **Data de carga.** Todo o histórico gravado com `dt = data_do_backfill`.

### Tratamentos, do mais barato ao mais invasivo

| Tratamento | Aplicável quando | Custo / risco |
|---|---|---|
| Filtrar nulls antes do join | null não é semanticamente necessário | **verificar semântica** — pode alterar resultado |
| Separar nulls: join só nos não-nulos + `union` dos nulos | null precisa aparecer no resultado | duas passagens; preserva semântica |
| Confiar no AQE skewJoin | sort-merge join, skew por hot key não-nula | já é default; ajustar `skewedPartitionFactor` |
| Broadcast do lado pequeno | lado pequeno mesmo | elimina o shuffle e o skew juntos |
| Salting (chave + sufixo aleatório) | hot key conhecida, poucas | replica o lado pequeno N×; complexidade real no código |
| Isolar a hot key: processar separado e unir | 1–3 chaves dominam | dois DAGs; mais código |
| `REBALANCE` hint | skew na **escrita** (arquivos desiguais) | barato; primeira tentativa para saída |
| Repartition por chave composta de maior cardinalidade | skew por baixa cardinalidade | adiciona shuffle |

Salting é a resposta mais citada e raramente a melhor primeira tentativa: adiciona complexidade permanente ao código, e AQE já cobre boa parte dos casos de sort-merge join. Chegar em salting sem antes provar que o AQE não resolveu é tuning por intuição.

## 4. Sequência de investigação

1. Identificar o stage dominante (maior fração do runtime), não o mais lento em absoluto.
2. Ler p50 / p95 / max de duração e de input desse stage.
3. Calcular `max/median` de duração **e** de input. Comparar — separa skew de dados de skew de computação.
4. Ler spill e GC do stage.
5. Mapear o stage ao operador no plano SQL (aba SQL do Spark UI liga stage a nó).
6. Se for join: obter tamanho e cardinalidade de cada lado, contagem de nulls e distribuição das top-N chaves.
7. Só então escolher tratamento.

Passo 6 exige medir, não estimar: `df.groupBy(chave).count().orderBy(desc("count")).limit(20)` sobre uma amostra, e `df.filter(col(chave).isNull()).count()`.

## 5. Validação obrigatória após tratar skew

Qualquer tratamento de skew que toque a chave de join pode alterar o resultado. Validar sempre: contagem total antes/depois, contagem de linhas com chave nula, agregados de controle por dimensão de negócio, e ausência de duplicação (contagem distinta da chave primária do resultado).

Salting mal implementado duplica linhas silenciosamente. Separação de nulls mal implementada as descarta.

## Fontes

- Apache Spark 3.5.6 — SQL Performance Tuning (estratégias de join, hints, configs de AQE skew). https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- AWS Glue Observability metrics — `glue.driver.skewness.stage` / `.job`, fator default 5, override via `spark.metrics.conf.driver.source.glue.jobPerformance.skewnessFactor`. https://docs.aws.amazon.com/glue/latest/dg/monitor-observability.html (retrieved 2026-07-29)
- Limiares de `max/median`, coeficiente de variação e `spill/input` são heurísticas de campo. Ponto de partida de hipótese, não veredito.
