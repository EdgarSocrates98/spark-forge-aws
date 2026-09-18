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
(`15.4.x-scala2.12`). A normalização guarda os segmentos numéricos iniciais
(`15.4`). Quando o rótulo termina em `.0` e a matriz tem só o número maior
(`18.0` contra `18`), a busca tenta o número maior. Versão fora da matriz
deixa `spark` vazio: a derivação não inventa.

## 3. O que ainda não se sabe

- **U1.** A chave `spark.databricks.clusterUsageTags.sparkVersion` é
  documentada como propriedade local de TaskContext, com valor como `16.3`, no
  Databricks Runtime 16.3 ou mais novo. Não há fonte oficial dizendo que ela
  aparece nas `Spark Properties` do event log entregue por cluster log
  delivery. O SparkForge lê a chave quando ela está lá; a presença em log real
  continua a confirmar.
- **U2.** A página do Photon documenta a cor dos operadores na interface e o
  `runtime_engine = PHOTON` nas APIs, não como Photon aparece no event log. Por
  isso Photon é declarado (`--photon on|off`), não detectado.
- `spark.sql.shuffle.partitions = auto` liga o auto-optimized shuffle, que
  escolhe o número de partições pelo plano e pelo volume. A página "Adaptive
  query execution" (https://docs.databricks.com/aws/en/optimizations/aqe,
  lida em 2026-09-17) diz que é opt-in e que o default é `200`. O `tune`
  recusa derivar número fixo por cima de `auto`.

## Fontes

- Databricks Runtime release notes versions and compatibility. https://docs.databricks.com/aws/en/release-notes/runtime/ (retrieved 2026-09-17)
- Get task context in a UDF. https://docs.databricks.com/aws/en/udf/udf-task-context (retrieved 2026-09-17)
- What is Photon? https://docs.databricks.com/aws/en/compute/photon (retrieved 2026-09-17)
- Adaptive query execution. https://docs.databricks.com/aws/en/optimizations/aqe (retrieved 2026-09-17)
