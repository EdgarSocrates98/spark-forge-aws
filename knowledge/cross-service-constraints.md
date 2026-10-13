# Restrições cruzadas entre serviços

Ler **antes** de recomendar mudança de versão, formato de tabela ou layout. Estas são as armadilhas em que a mudança funciona no job e quebra em outro lugar — o modo de falha aparece no consumidor, não em quem mudou.

## 1. Iceberg format V3 × Athena

| Fato | Consequência |
|---|---|
| AWS Glue 5.1 (Iceberg 1.10.0) **pode escrever** tabelas Iceberg format version 3 | |
| Amazon Athena **não lê** Iceberg V3 | Qualquer consumidor Athena quebra |

**Ação obrigatória:** se há consumo por Athena, fixar `format-version = 2` na table property, ou permanecer em Glue 5.0.

Perigo do modo de falha: a migração Glue 5.0 → 5.1 é apresentada como upgrade de runtime. O job passa. Dias depois, dashboards e queries ad-hoc em Athena falham, e a causa está a duas semanas de distância no log de mudanças.

Verificação: `SHOW TBLPROPERTIES` / metadata da tabela, campo `format-version`.

## 2. Métricas de throughput do Glue × Iceberg

`glue.driver.recordsWritten`, `glue.driver.bytesWrittten` e `glue.driver.filesWritten` **não estão disponíveis para tabelas Iceberg**.

Consequência: não é possível medir volume de escrita por CloudWatch em pipeline Iceberg. Medir pelas metadata tables (`snapshots`, `files`) ou instrumentar no código.

`recordsRead` **é** emitido para Iceberg (quando a fonte é tabela do catálogo). A assimetria leitura/escrita é real e frequentemente descoberta tarde, no meio de um benchmark.

## 3. Observability metrics × Spark puro

`--enable-observability-metrics` só publica se `glueContext` estiver inicializado.

Job escrito como PySpark puro (`SparkSession.builder...`) sem nunca instanciar `GlueContext` não emite métrica de observabilidade alguma — e o operador conclui erradamente que o job não tem problema, quando na verdade não tem dado.

## 4. AQE × Glue 3.0

AQE é default a partir de Spark 3.2. Glue 3.0 roda Spark 3.1.1 → **AQE não é default**. Recomendações do tipo "o AQE cuida do skew" não se aplicam a Glue 3.0 sem habilitação explícita, e várias sub-configs de AQE simplesmente não existem nessa versão.

## 5. Documentação `latest` do Iceberg × versão embarcada

Propriedades, procedimentos (`rewrite_data_files`, `expire_snapshots`, `rewrite_manifests`, `remove_orphan_files`) e seus parâmetros mudam entre versões. O salto Glue 4.0 (Iceberg 1.0.0) → 5.0 (1.7.1) → 5.1 (1.10.0) é grande.

Regra: nunca citar a documentação `latest` para um job Glue 4.0. Procedimento que existe na doc e não é reconhecido no runtime é sintoma disso, não bug do Glue.

## 6. JAR próprio de Iceberg × Iceberg embarcado

Não há como desinstalar o Iceberg que o Glue embarca. Fornecer JAR próprio cria conflito de classpath resolvido por `--user-jars-first`.

Sintoma: `NoSuchMethodError` ou `ClassNotFoundException` em classe Iceberg, intermitente entre operações.

Revisar em conjunto: versão Spark/Scala do JAR (Scala 2.12), precedência de classpath, registro de extensão e catálogo, e `--datalake-formats`.

## 7. Config no código × default arguments do Terraform

`spark.conf.set(...)` em runtime sobrescreve default argument do IaC, silenciosamente.

Causa mais comum de "mudei no Terraform e nada aconteceu". Ver `spark/config-reference.md` §6 para a ordem completa de precedência, e quais configs não podem mudar após a sessão iniciar.

## 8. Auto Scaling × NumberOfWorkers

Com `--enable-auto-scaling = true`, configurar `MinCapacity` e `MaxCapacity`. Configurar `NumberOfWorkers` junto é contraditório e é o erro de IaC mais comum na área.

## 9. Job bookmarks × concorrência

`GLUE_JOB_BOOKMARK_VERSION_MISMATCH_ERROR` ocorre quando o mesmo job roda concorrentemente sobre a mesma origem. `max concurrent runs > 1` com bookmarks é combinação perigosa.

Além disso: bookmark **não é** mecanismo de incremental universal. Usar bookmark como se fosse CDC leva a reprocessamento ou a perda de dados. Incremental sobre Iceberg deve usar snapshot/incremental read, não bookmark.

## 10. Partition projection × layout esparso

Partition projection assume que toda partição do padrão existe. Layout esparso gera trabalho inútil; range mal definido (data final fixa que não avança) faz partições novas desaparecerem das queries — falha por dado faltante, silenciosa.

## Como usar esta lista

Antes de qualquer recomendação que envolva mudança de versão de Glue, versão de Iceberg, formato de tabela, particionamento ou configuração de capacidade: percorrer esta lista e declarar no relatório quais itens foram verificados e qual foi o resultado.

Item não verificado é risco não declarado.

## Fontes

- Introducing AWS Glue 5.1 for Apache Spark (V3 × Athena, matriz de versões). https://aws.amazon.com/blogs/big-data/introducing-aws-glue-5-1-for-apache-spark (retrieved 2026-07-29)
- Monitoring with AWS Glue Observability metrics (limitações Iceberg/JDBC, requisito de `glueContext`, categorias de erro). https://docs.aws.amazon.com/glue/latest/dg/monitor-observability.html (retrieved 2026-07-29)
- Using auto scaling for AWS Glue (`MinCapacity`/`MaxCapacity` vs `NumberOfWorkers`). https://docs.aws.amazon.com/glue/latest/dg/auto-scaling.html (retrieved 2026-07-29)
- Apache Spark 3.5.6 SQL Performance Tuning (AQE default desde 3.2). https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- Partition your data — Amazon Athena. https://docs.aws.amazon.com/athena/latest/ug/partitions.html (retrieved 2026-07-29)
- Itens 6, 7 e 9 (segunda parte) são conhecimento operacional; verificar no runtime real.
