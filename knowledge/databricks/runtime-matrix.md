# Matriz de runtime do Databricks

Esta página responde uma pergunta: dado o número do Databricks Runtime de um
cluster ou job, qual Apache Spark ele roda? O espelho executável é
[`runtime-matrix.yaml`](runtime-matrix.yaml), com a coluna `spark` e nada mais.

## 1. O que a fonte publica

A página de versões suportadas lista, por versão, a versão do Apache Spark, a
data de lançamento e o fim de suporte. Lida em 2026-09-17, atualizada pela
Databricks em 2026-09-11:

| Databricks Runtime | LTS | Apache Spark | Lançamento | Fim de suporte |
|---|---|---|---|---|
| 19 | não | 4.2.0 | 2026-06-15 | definido na transição para LTS |
| 18 | sim | 4.1.0 | 2026-06-10 | 2029-06-10 |
| 17.3 | sim | 4.0.0 | 2025-10-22 | 2028-10-22 |
| 16.4 | sim | 3.5.2 | 2025-05-09 | 2028-05-09 |
| 15.4 | sim | 3.5.0 | 2024-08-19 | 2027-08-19 |
| 14.3 | sim | 3.5.0 | 2024-02-01 | 2027-02-01 |

A página escreve `18 LTS`, `17.3 LTS`...; aqui o sufixo vira a coluna LTS para
que a chave seja a mesma do YAML e do guard de drift.

A página não publica Python, Scala nem Delta por versão. Esses eixos ficam
fora da matriz.

## 2. A chave e o rótulo

A matriz é indexada pelo número como a página o escreve. O rótulo que a
Clusters API e a Jobs API carregam em `spark_version` tem outra forma
(`15.4.x-scala2.12`): a referência de `clusters/create` documenta o campo como
"The Spark version of the cluster, e.g. `3.3.x-scala2.11`" (lida em
2026-09-18), o número do runtime seguido de `.x-scala` e da versão do Scala. A
normalização guarda os segmentos numéricos iniciais (`15.4`). Quando o rótulo termina em `.0` e a matriz tem só o número maior
(`18.0` contra `18`), a busca tenta o número maior. Versão fora da matriz
deixa `spark` vazio: a derivação não inventa.

## 3. O que ainda não se sabe

- **U1.** A chave `spark.databricks.clusterUsageTags.sparkVersion` é
  documentada como propriedade local de TaskContext, com valor como `16.3`, no
  Databricks Runtime 16.3 ou mais novo. Não há fonte oficial dizendo que ela
  aparece nas `Spark Properties` do event log entregue por cluster log
  delivery. O SparkForge lê a chave quando ela está lá; a presença em log real
  continua a confirmar. No serverless a pergunta não se aplica (não há event
  log entregue); a observação da seção 4 mostra só que a chave não é legível
  por `spark.conf` ali: `spark.conf.get` dela levanta
  `CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION`. Para cluster clássico — onde a
  chave é documentada — a pergunta continua aberta.
- **U2.** A página do Photon documenta a cor dos operadores na interface e o
  `runtime_engine = PHOTON` nas APIs, não como Photon aparece no event log.
  Photon é declarado (`--photon on|off`) OU detectado pelo TEXTO DO PLANO —
  prefixo `Photon` nos nomes de operador (`PhotonRange`, `PhotonGroupingAgg`,
  ...) e a seção `== Photon Explanation ==` de `explain(mode="formatted")`,
  que o SparkForge lê como o fact `plan.photon` (seção 4) e cuja observação
  vence a declaração quando as duas divergem. Isso não é o event log: como
  Photon aparece no event log entregue continua não observado, porque
  compute serverless não entrega event log.
- `spark.sql.shuffle.partitions = auto` liga o auto-optimized shuffle, que
  escolhe o número de partições pelo plano e pelo volume. A página "Adaptive
  query execution" (https://docs.databricks.com/aws/en/optimizations/aqe,
  lida em 2026-09-17) diz que é opt-in e que o default é `200` para o caso
  que ela documenta. Na observação da seção 4, sob compute serverless e sem
  nenhuma configuração do operador, o valor presente já é `auto` — os dois
  fatos (default documentado `200`; valor observado `auto`) ficam lado a
  lado, sem que um resolva o outro. O `tune` recusa derivar número fixo por
  cima de `auto`.

## 4. Observado em Databricks Free Edition (serverless), 2026-09-18

Observação de operador, um único ambiente: conta Databricks Free Edition
própria, compute serverless, notebook com dados sintéticos (`spark.range`).
Tier de autoridade: observação de campo, não documentação oficial — uma
versão, um tipo de compute, fora do escopo da matriz de runtime clássico das
seções 1–3 (que documenta cluster, não serverless). Não generalize para
cluster clássico nem para outra versão sem nova observação.

- `spark.version` = `4.2.0`.
- `spark.conf.get` de `spark.databricks.clusterUsageTags.sparkVersion`,
  `spark.databricks.photon.enabled` e `spark.sql.adaptive.enabled` levanta
  `AnalysisException [CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION]`: no
  serverless observado, essas três chaves não são legíveis por `spark.conf`.
- `spark.sql.shuffle.partitions` = `auto`, sem nenhuma configuração do
  operador; o shuffle do plano saiu como `hashpartitioning(k, 16)`.
- `explain(mode="formatted")` de um groupBy + join mostrou os operadores
  `PhotonRange`, `PhotonProject`, `PhotonGroupingAgg`,
  `PhotonShuffleExchangeSink`, `PhotonShuffleMapStage`,
  `PhotonShuffleExchangeSource`, `PhotonBroadcastHashJoin`,
  `PhotonColumnarToRow`, `PhotonResultStage`, sob `AdaptiveSparkPlan`, com
  uma seção `== Photon Explanation ==` dizendo "The query is fully supported
  by Photon.".
- `explain` de um `@F.udf` Python comum mostrou `ArrowEvalPython` entre
  `PhotonArrowResultStage`/`PhotonArrowBatchSink` e
  `PhotonArrowBatchSource`; a seção `== Photon Explanation ==` disse "fully
  supported" também para essa UDF.
- Medido pelo controlador com `sparkforge analyze plan` sobre os dois
  planos, fora deste repositório, em 2026-09-18: o extrator ainda não
  reconhecia o vocabulário `Photon*` — no plano com join emitiu só
  `plan.analyzed` e `plan.aqe`, nenhum `plan.join`/`plan.exchange`; no plano
  da UDF emitiu `plan.python_udf` com `udf_type: "pandas"` para um
  `ArrowEvalPython` que vinha de `@F.udf` comum, não pandas. As duas lacunas
  foram corrigidas pela feature descrita a seguir.

**O que o SparkForge faz com um plano Photon, desde esta feature.** O
extrator reconhece os operadores de prefixo `Photon` e emite um fact
`plan.photon` por plano (`measures.photon_operators`, `measures.operators`,
`attrs.operators` com os nomes distintos ordenados, `attrs.explanation` com
a primeira linha de `== Photon Explanation ==`). Com `plan.photon` entre os
facts, o engine recusa toda regra que exige kind de plano — em `skipped`
com motivo `databricks.photon.unresolved` — sem precisar de `--photon`,
exceto as que exigem só `plan.python_udf` ou `plan.aqe`. Uma declaração
`--photon off` diante desse fact vira divergência, não silêncio (seção 3,
U2). E `ArrowEvalPython` sai com `udf_type: arrow`, porque o plano não
distingue `pandas_udf` de UDF Python otimizada para Arrow. Limites: a forma
é a observada num único ambiente (Free Edition, serverless, Spark 4.2.0,
2026-09-18); o texto de suporte parcial da seção de explicação (fallback
para Spark comum) não foi visto, só "fully supported"; e Photon pelo event
log continua não observado (U2).

## Fontes

- Databricks Runtime release notes versions and compatibility. https://docs.databricks.com/aws/en/release-notes/runtime/ (retrieved 2026-09-17)
- Get task context in a UDF. https://docs.databricks.com/aws/en/udf/udf-task-context (retrieved 2026-09-17)
- What is Photon? https://docs.databricks.com/aws/en/compute/photon (retrieved 2026-09-17)
- Adaptive query execution. https://docs.databricks.com/aws/en/optimizations/aqe (retrieved 2026-09-17)
- Clusters API, create. https://docs.databricks.com/api/workspace/clusters/create (retrieved 2026-09-18)
