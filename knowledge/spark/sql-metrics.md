# Métricas SQL do Spark — o mapa de nomes que o extrator lê

`SQLMetrics` (`sql/core/.../execution/metric/SQLMetrics.scala`) é o mecanismo do Spark
para publicar um número por nó do plano físico, e não por stage. Cada operador que quer
expor um custo — bytes lidos, arquivos abertos, linhas emitidas — registra uma métrica
com três coisas: uma **chave interna** (`numFiles`), um **rótulo publicado** (`"number of
files read"`) e um **tipo** (`sum`, `size`, `timing`, `nsTiming`, `average`), que decide
como o valor é agregado e formatado. O rótulo publicado é o que chega no event log, dentro
de `sparkPlanInfo.metrics` em `SparkListenerSQLExecutionStart` e nos `Accumulables` de
`SparkListenerTaskEnd` — é esse texto, não a chave interna, que o extrator precisa
reconhecer.

`FileSourceScanExec` — o operador que lê arquivo do data lake, a v1 API — é quem declara
os quatro rótulos deste mapa. Eles chegam como métrica de **driver** (agregada uma vez
para a execução inteira: `number of files read`, `size of files read`, `number of
partitions read`) ou de **tarefa** (`number of output rows`, somada por task como qualquer
outro acumulador Spark).

## Por que é lista fechada

O rótulo publicado é texto livre escolhido pelo operador que o declara, não um enum do
Spark. Dois rótulos podem compartilhar substring por coincidência — `size of files read` e
uma futura `size of shuffle write` teriam `"size of"` em comum — e casar por substring
resolveria o primeiro certo e o segundo errado, com a mesma aparência de medição nos dois
casos. Por isso o extrator só reconhece os rótulos que este mapa lista explicitamente, com
a versão de Spark em que cada um foi conferido direto no fonte. Rótulo publicado fora do
mapa não vira `0` nem palpite: sai como `spark.sql.unresolved`, razão `unknown_metric_name`,
carregando o texto cru.

A tabela legível por máquina — rótulo, measure, tipo de métrica, versões conferidas — está
em [`sql-metrics.yaml`](sql-metrics.yaml) ao lado, e não é repetida aqui: duas cópias do
mesmo mapa divergem cedo ou tarde, e só uma delas é a que o extrator carrega em tempo de
execução (ver `docs/gates-por-mudanca.md`, sobre por que documento e dado legível por
máquina vivem em arquivos separados). Quem for verificar um rótulo lê o YAML; este texto
só explica o porquê da forma.

## Fontes

- FileSourceScanLike / DataSourceScanExec.scala — Apache Spark, tag v3.1.1. Rótulos e tipo de métrica conferidos diretamente no fonte. https://raw.githubusercontent.com/apache/spark/v3.1.1/sql/core/src/main/scala/org/apache/spark/sql/execution/DataSourceScanExec.scala (retrieved 2026-08-28)
- FileSourceScanLike / DataSourceScanExec.scala — Apache Spark, tag v3.3.0. https://raw.githubusercontent.com/apache/spark/v3.3.0/sql/core/src/main/scala/org/apache/spark/sql/execution/DataSourceScanExec.scala (retrieved 2026-08-28)
- FileSourceScanLike / DataSourceScanExec.scala — Apache Spark, tag v3.5.4. https://raw.githubusercontent.com/apache/spark/v3.5.4/sql/core/src/main/scala/org/apache/spark/sql/execution/DataSourceScanExec.scala (retrieved 2026-08-28)
- FileSourceScanLike / DataSourceScanExec.scala — Apache Spark, tag v3.5.6. https://raw.githubusercontent.com/apache/spark/v3.5.6/sql/core/src/main/scala/org/apache/spark/sql/execution/DataSourceScanExec.scala (retrieved 2026-08-28)
- FileSourceScanLike / DataSourceScanExec.scala — Apache Spark, tag v4.1.1. https://raw.githubusercontent.com/apache/spark/v4.1.1/sql/core/src/main/scala/org/apache/spark/sql/execution/DataSourceScanExec.scala (retrieved 2026-08-28)
- SQLMetrics.scala — Apache Spark, tag v3.5.4. Fábricas de métrica e os tipos (`sum`, `size`, `timing`, `nsTiming`, `average`) que cada uma produz. https://raw.githubusercontent.com/apache/spark/v3.5.4/sql/core/src/main/scala/org/apache/spark/sql/execution/metric/SQLMetrics.scala (retrieved 2026-08-28)
