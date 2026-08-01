# Base de conhecimento — SparkForge AWS

Esta base é a fonte de verdade sobre **como Spark, Glue, Athena, Parquet e Iceberg se comportam**. Ela não contém procedimento de investigação — isso vive em `skills/`. Não contém estado de investigação — isso vive em `.sparkforge/case.yaml`.

## Regra de uso

1. **Nenhum limiar aplicado sem checar a versão.** Toda tabela aqui tem coluna ou nota de versão. Config de Spark 3.5 não vale automaticamente em Spark 3.3 (Glue 4.0).
2. **Defaults documentados aqui são os do Apache Spark.** O AWS Glue sobrescreve alguns. Sempre confirme o valor **efetivo** no runtime: `spark.conf.get("<chave>")` ou a aba Environment do Spark UI.
3. **Limiar é ponto de partida de hipótese, não veredito.** Um número fora do limiar indica onde olhar, não o que fazer.
4. **Toda entrada tem fonte com data.** Se não tem, é heurística de campo e está marcada como tal.

## Mapa

### Spark / PySpark
| Arquivo | Conteúdo |
|---|---|
| [`spark/execution-model.md`](spark/execution-model.md) | Como Spark executa: lazy eval, actions, jobs/stages/tasks, fronteiras de shuffle, codegen, o que quebra pushdown |
| [`spark/config-reference.md`](spark/config-reference.md) | Configs com nome exato, default e significado — AQE, shuffle, broadcast, leitura de arquivos |
| [`spark/shuffle-join-skew.md`](spark/shuffle-join-skew.md) | Estratégias físicas de join, custo de shuffle, diagnóstico e tratamento de skew |
| [`spark/memory-and-oom.md`](spark/memory-and-oom.md) | Modelo de memória, spill, GC, e as 7 classes distintas de OOM |
| [`spark/plan-reading.md`](spark/plan-reading.md) | Como ler `explain("formatted")` e mapear operador → stage → métrica |

### AWS Glue
| Arquivo | Conteúdo |
|---|---|
| [`glue/runtime-matrix.md`](glue/runtime-matrix.md) | Matriz Glue × Spark × Python × Iceberg/Hudi/Delta |
| [`glue/workers-and-capacity.md`](glue/workers-and-capacity.md) | Worker types G/R, DPU, disco, Auto Scaling, Flex, cálculo de capacidade |
| [`glue/job-arguments.md`](glue/job-arguments.md) | Argumentos que afetam performance, precedência código × IaC |
| [`glue/observability.md`](glue/observability.md) | Métricas CloudWatch exatas, 28 categorias de erro, o que cada uma prova |

### Amazon EMR
| Arquivo | Conteúdo |
|---|---|
| [`emr/runtime-matrix.md`](emr/runtime-matrix.md) | Matriz EMR × Spark × Hadoop × Iceberg × Python, 6.4.0 a 7.13.0, com o significado do sufixo `-amzn-N` |

### Amazon Athena
| Arquivo | Conteúdo |
|---|---|
| [`athena/performance.md`](athena/performance.md) | Engine v3, modelo de custo, partition projection, CTAS, Iceberg via Athena |

### Armazenamento
| Arquivo | Conteúdo |
|---|---|
| [`storage/parquet-layout.md`](storage/parquet-layout.md) | Row group, page, dictionary, estatísticas, small files, listing S3 |
| [`storage/iceberg-performance.md`](storage/iceberg-performance.md) | Data/delete files, manifests, snapshots, partition spec, sort order, manutenção |
| [`iceberg-diagnostics.sql`](iceberg-diagnostics.sql) | Queries de metadata tables |

### Transversal
| Arquivo | Conteúdo |
|---|---|
| [`cross-service-constraints.md`](cross-service-constraints.md) | **Armadilhas entre serviços.** Ler antes de recomendar mudança de formato ou versão |
| [`performance-principles.md`](performance-principles.md) | Hierarquia de otimização, o que nunca assumir |
| [`anti-patterns.md`](anti-patterns.md) | Anti-patterns de código |
| [`runtime-compatibility.md`](runtime-compatibility.md) | Ponteiro para `glue/runtime-matrix.md` |

## Catálogo de regras

A forma **executável** deste conhecimento vive em [`../rules/catalog/`](../rules/catalog/): YAML com `rule_id`, limiar, guarda de versão e fonte. Prosa aqui explica *por quê*; o catálogo define *quando dispara*.

Ler [`../rules/catalog/README.md`](../rules/catalog/README.md) antes de escrever regra nova.

## Fontes e frescor

Cada arquivo declara `Fontes` com URL e data de coleta no rodapé. Coleta desta rodada: **2026-07-29**.

Conhecimento aqui **não substitui** a documentação do runtime real. Quando o job em análise contradiz esta base, o runtime ganha e a base é corrigida.
