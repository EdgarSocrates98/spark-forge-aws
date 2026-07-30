# Matriz de runtime AWS Glue

Confirme sempre contra o runtime **efetivo** do job. Esta tabela orienta; não substitui a aba *Environment* do Spark UI nem as release notes.

## 1. Matriz principal

| AWS Glue | Apache Spark | Python | Scala | Iceberg | Hudi | Delta Lake |
|---|---|---|---|---|---|---|
| 5.1 | 3.5.6 | 3.11 | 2.12.18 | 1.10.0 | 1.0.2 | 3.3.2 |
| 5.0 | 3.5.4 | 3.11 | 2.12 | 1.7.1 | 0.15.0 | 3.3.0 |
| 4.0 | 3.3.0 | 3.10 | 2.12 | 1.0.0 | 0.12.1 | 2.1.0 |
| 3.0 | 3.1.1 | 3.7 | 2.12 | 0.13.1 | 0.10.1 | 1.0.0 |

Colunas Hudi/Delta para 4.0 e 3.0 são de release notes históricas — confirmar antes de citar.

## 2. Consequências que mudam recomendação

### AQE
Ligado por default desde Spark 3.2. Portanto: **default em Glue 4.0 e 5.x; não em Glue 3.0** (Spark 3.1.1). Recomendar "confie no AQE" para um job Glue 3.0 é erro de versão.

### Iceberg
O salto 1.0.0 (Glue 4.0) → 1.7.1 (5.0) → 1.10.0 (5.1) é grande. Procedimentos, propriedades de tabela e capacidades diferem muito. Nunca cite a documentação `latest` do Iceberg para um job Glue 4.0.

Capacidades novas em Iceberg 1.10.0 / Glue 5.1: Materialized View, **format version 3**, valores default de coluna, deletion vectors para tabelas merge-on-read, transforms multi-argumento, row lineage tracking.

### Python
3.7 (Glue 3.0) → 3.10 (4.0) → 3.11 (5.x). Biblioteca própria que usa sintaxe de 3.11 não roda em Glue 4.0. `match` statement (3.10+) não roda em Glue 3.0.

## 3. Armadilha de versão mais séria: Iceberg V3 e Athena

**Glue 5.1 pode escrever tabelas Iceberg format V3. Amazon Athena não lê V3.**

Se qualquer consumidor downstream consulta a tabela via Athena, é obrigatório fixar `format-version = 2` na tabela, ou permanecer em Glue 5.0. Migrar para Glue 5.1 e deixar a tabela virar V3 quebra o consumo por Athena — e o modo de falha aparece no consumidor, não no job que fez a mudança.

Ver [`../cross-service-constraints.md`](../cross-service-constraints.md) para o conjunto completo dessas restrições cruzadas.

## 4. JARs próprios de Iceberg

Fornecer JAR próprio em vez de usar o embarcado exige revisar, em conjunto:

1. Compatibilidade Spark/Scala do JAR (Scala 2.12 nas versões acima).
2. Precedência de classpath — `--user-jars-first` muda quem ganha.
3. Conflito com o Iceberg já embarcado pelo Glue (não há como "desinstalar" o embarcado).
4. Registro de extensão e catálogo compatível com a versão fornecida.

Sintoma de conflito: `NoSuchMethodError` / `ClassNotFoundException` em classe Iceberg, ou procedimento que existe na doc e não é reconhecido.

Registrar no relatório a matriz detectada **e** qualquer divergência entre runtime embarcado e biblioteca customizada. No SparkForge isso é o finding `SF-ENV-001`.

## 5. Como detectar a versão efetiva

Em ordem de confiabilidade:

1. Spark UI → aba *Environment* → `spark.version`, e classpath para versão de Iceberg.
2. Event log do run (contém `spark.version` e as configs).
3. `glue_version` no Terraform / job definition.
4. `--datalake-formats` nos default arguments (indica qual formato o Glue carrega).
5. `requirements.txt` / `pyproject.toml` do projeto (indica intenção, não runtime).

Divergência entre fontes **não** é resolvida escolhendo uma. É registrada como divergência.

## Fontes

- Migrating AWS Glue for Spark jobs to AWS Glue version 5.0. https://docs.aws.amazon.com/glue/latest/dg/migrating-version-50.html (retrieved 2026-07-29)
- Introducing AWS Glue 5.1 for Apache Spark — AWS Big Data Blog. https://aws.amazon.com/blogs/big-data/introducing-aws-glue-5-1-for-apache-spark (retrieved 2026-07-29)
- Introducing AWS Glue 5.1 — What's New. https://aws.amazon.com/about-aws/whats-new/2025/11/aws-glue-5-1 (retrieved 2026-07-29)
- Breaking Changes Checklist: Migrating AWS Glue Jobs to Version 5.0/5.1 — AWS re:Post. https://repost.aws/articles/ARjELjm9_jRxejMb1havX8xg/breaking-changes-checklist-migrating-aws-glue-jobs-to-version-5-0-5-1 (retrieved 2026-07-29)
- AWS Glue Release Notes. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-release-notes.rss (retrieved 2026-07-29)
- Linhas de Glue 3.0/4.0 para Hudi e Delta não foram reconfirmadas nesta coleta. Marcar como a verificar.
