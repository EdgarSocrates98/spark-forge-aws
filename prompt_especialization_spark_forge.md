Perfeito. Essa observação muda bastante o nível do prompt.

O que você está pedindo não é apenas “suporte a Spark 3.x/4.x”. É transformar o Spark Forge em uma espécie de **enciclopédia operacional + motor de diagnóstico + motor de migração + especialista de arquitetura + especialista de performance/custo**, com conhecimento **version-aware até o nível de patch/runtime**, principalmente para AWS.

Isso é particularmente importante porque as mudanças entre runtimes são profundas. Por exemplo, Glue 4.0 usa Spark 3.3.0/Python 3.10, Glue 5.0 usa Spark 3.5.4/Python 3.11, Glue 5.1 usa Spark 3.5.6/Python 3.11 e Glue 6.0 usa Spark 4.1.1/Python 3.13, além de mudanças importantes em Java, Scala, Hadoop, Arrow, Parquet e comportamento do Spark. ([Documentação AWS][1])

E há um ponto especialmente importante: **Lake Formation também possui versões de cross-account sharing**, hoje chegando à versão 5, com mudanças significativas de comportamento e sem downgrade a partir da v5. ([Documentação AWS][2])

Então eu acrescentaria o seguinte como **nova versão do prompt mestre**, substituindo o anterior:

# SPARK FORGE — EXTREME VERSION-AWARE DATA ENGINEERING INTELLIGENCE

## MISSÃO

Evolua o projeto:

[https://github.com/EdgarSocrates98/spark-forge-aws](https://github.com/EdgarSocrates98/spark-forge-aws)

para uma plataforma de inteligência especializada em Data Engineering capaz de atuar profundamente em:

* Apache Spark
* PySpark
* Python
* AWS Glue
* Amazon EMR
* Apache Iceberg
* Apache Parquet
* AWS Lake Formation
* AWS Glue Data Catalog
* Amazon Athena
* Amazon S3
* AWS KMS
* Apache Arrow
* Pandas
* Avro
* JSON
* Data Quality
* observabilidade
* segurança
* governança
* performance
* custo
* arquitetura
* migração
* troubleshooting
* otimização
* capacity planning

O objetivo NÃO é simplesmente adicionar suporte nominal a essas tecnologias.

O objetivo é construir um:

# VERSION-AWARE DATA ENGINEERING EXPERT SYSTEM

capaz de entender diferenças entre versões, identificar incompatibilidades, explicar regressões, diagnosticar problemas, propor migrações, comparar arquiteturas, otimizar performance e custo e validar as mudanças através de evidências e experimentos.

---

# 1. VISÃO FINAL

O Spark Forge deve conseguir receber algo como:

> "Tenho um job Glue 4.0 com Spark 3.3, Iceberg X, Python 3.10, Parquet Y, Lake Formation cross-account e quero migrar para Glue 5.1."

E responder:

```text
CURRENT ENVIRONMENT
        ↓
DEPENDENCY GRAPH
        ↓
VERSION MATRIX
        ↓
KNOWN BREAKING CHANGES
        ↓
CODE COMPATIBILITY
        ↓
CONFIG COMPATIBILITY
        ↓
DATA FORMAT COMPATIBILITY
        ↓
SECURITY COMPATIBILITY
        ↓
PERFORMANCE IMPACT
        ↓
COST IMPACT
        ↓
MIGRATION RISKS
        ↓
MIGRATION PLAN
        ↓
TEST PLAN
        ↓
VALIDATION
        ↓
BENCHMARK
        ↓
GO / NO-GO
```

---

# 2. PRINCÍPIO ABSOLUTO: VERSION-AWARE EVERYTHING

Nenhuma regra importante deve ser avaliada sem conhecer o máximo possível de:

```yaml
environment:
  cloud:
  region:
  account:
  service:

runtime:
  glue:
  emr:
  emr_release:
  spark:
  scala:
  java:
  python:
  hadoop:
  hive:

libraries:
  iceberg:
  parquet:
  arrow:
  pyarrow:
  pandas:
  numpy:
  boto3:
  aws_sdk:

catalog:
  type:
  version:
  account:
  region:

security:
  lakeformation:
  cross_account_version:
  kms:
  iam:

storage:
  s3:
  table_format:
```

Se alguma informação não estiver disponível:

```text
UNKNOWN
```

Nunca inferir silenciosamente.

---

# 3. MATRIZ COMPLETA DE SPARK

O Spark Forge deve possuir conhecimento especializado, separado por versão, para:

```text
Spark 3.0
Spark 3.1
Spark 3.2
Spark 3.3
Spark 3.4
Spark 3.5
Spark 4.0
Spark 4.1
Spark 4.2
```

Não criar apenas:

```text
spark >= 3
```

Criar conhecimento granular:

```text
3.0.x
3.1.x
3.2.x
3.3.x
3.4.x
3.5.x
4.0.x
4.1.x
4.2.x
```

Quando a documentação permitir, distinguir inclusive:

```text
major
minor
patch
vendor distribution
AWS distribution
```

---

# 4. SPARK VERSION KNOWLEDGE

Para cada versão do Spark documentar:

## Core

* APIs adicionadas
* APIs removidas
* APIs deprecated
* mudanças semânticas
* mudanças de defaults
* mudanças de comportamento
* mudanças de serialização
* mudanças de scheduler
* mudanças de execução

## SQL

* SQL syntax
* ANSI
* casting
* timestamp
* date
* decimal
* null semantics
* joins
* aggregation
* window
* subquery
* CTE
* functions

## DataFrame

* API changes
* behavior changes
* schema inference
* type coercion
* nullability
* column resolution

## PySpark

* Python compatibility
* UDF
* Pandas UDF
* Arrow
* serialization
* Python worker
* cloudpickle
* API changes

## Spark SQL

* optimizer
* Catalyst
* physical planner
* AQE
* CBO
* statistics
* joins
* partitioning

## Performance

* AQE
* skew
* shuffle
* memory
* caching
* file scanning
* partitioning
* parallelism

## Structured Streaming

* checkpoint compatibility
* state store
* watermark
* trigger
* sink/source compatibility
* state schema
* recovery behavior

## Runtime changes

Document:

```text
default changed
feature added
feature removed
behavior changed
configuration changed
performance changed
compatibility changed
```

---

# 5. SPARK MIGRATION MATRIX

Criar uma matriz explícita para:

```text
3.0 → 3.1
3.1 → 3.2
3.2 → 3.3
3.3 → 3.4
3.4 → 3.5
3.5 → 4.0
4.0 → 4.1
4.1 → 4.2
```

E também saltos:

```text
3.0 → 3.5
3.0 → 4.0
3.0 → 4.2
3.3 → 4.0
3.5 → 4.0
3.5 → 4.2
```

Para cada migração:

```yaml
migration:
  source:
  target:

breaking_changes:
behavior_changes:
removed_apis:
deprecated_apis:
default_changes:
config_changes:
python_changes:
java_changes:
scala_changes:
parquet_changes:
iceberg_changes:
arrow_changes:
streaming_changes:
performance_risks:
security_risks:
known_troubles:
rollback_strategy:
```

---

# 6. SPARK MIGRATION TROUBLESHOOTING DATABASE

Criar uma base especializada de problemas reais.

Cada problema:

```yaml
id:
title:
source_version:
target_version:

symptoms:
errors:
stacktrace_patterns:

root_causes:

affected:
  spark:
  pyspark:
  python:
  scala:
  java:
  iceberg:
  parquet:
  arrow:

diagnostic_steps:

fix:

workaround:

permanent_solution:

regression_risk:

references:
```

---

# 7. STACKTRACE INTELLIGENCE

O Spark Forge deve reconhecer padrões de erro como:

```text
ClassNotFoundException
NoSuchMethodError
NoClassDefFoundError
AbstractMethodError
MethodNotFound
Py4JJavaError
AnalysisException
SparkUpgradeException
UnsupportedOperationException
IllegalArgumentException
ClassCastException
OutOfMemoryError
GC overhead limit exceeded
ExecutorLostFailure
FetchFailed
FetchFailedException
MetadataFetchFailedException
Task not serializable
Python worker exited unexpectedly
ArrowInvalid
ArrowMemoryError
ConcurrentModificationException
CommitFailedException
FileNotFoundException
AccessDeniedException
```

E relacioná-los com:

```text
runtime
version
dependency
configuration
code
data
security
```

---

# 8. GLUE VERSION MATRIX

Especialização máxima para:

```text
Glue 4.0
Glue 5.0
Glue 5.1
Glue 6.0
```

Também manter conhecimento histórico para:

```text
Glue 0.9
Glue 1.0
Glue 2.0
Glue 3.0
```

porque migrações reais podem partir dessas versões.

---

# 9. GLUE 4.0

Conhecimento detalhado de:

```text
Spark 3.3.0
Python 3.10
Java
Scala
Hadoop
EMRFS
Iceberg
Parquet
Arrow
Glue Catalog
GlueContext
DynamicFrame
```

Especializar em:

* Spark 3.3 migration
* Python 3.10 migration
* Log4j2 migration
* Encryption SDK
* JDBC drivers
* connectors
* dependency conflicts
* extra jars
* GlueContext
* DynamicFrame
* Spark native APIs
* job parameters
* worker types
* autoscaling
* bookmarks
* pushdown predicates
* S3 optimized committer

AWS documenta, por exemplo, mudanças de Python 3.7 para 3.10 e Spark 3.1.1 para 3.3.0 na migração para Glue 4.0, além de mudanças de Log4j, EMRFS e Encryption SDK. ([Documentação AWS][3])

---

# 10. GLUE 5.0

Especializar em:

```text
Spark 3.5.4
Python 3.11
Java 17
Scala 2.12
```

Conhecer profundamente:

* Spark 3.5 migration
* Python 3.11
* Java 17
* dependency changes
* FGAC
* Lake Formation
* Iceberg
* Delta
* Hudi
* connectors
* JDBC
* logging
* runtime configuration

Particular atenção:

```text
--enable-lakeformation-fine-grained-access
```

e limitações do FGAC.

Por exemplo, a documentação do Glue 5.0 registra FGAC nativo do Spark via Lake Formation, incluindo Iceberg, Delta e Hudi, mas também documenta limitações para escrita. ([Documentação AWS][4])

---

# 11. GLUE 5.1

Criar conhecimento próprio, não tratar como sinônimo de Glue 5.0.

Registrar:

```text
Spark 3.5.6
Python 3.11
Scala 2.12.18
Java 17
```

e todas as diferenças em relação ao 5.0.

Criar:

```text
Glue 5.0 → 5.1 migration analyzer
```

---

# 12. GLUE 6.0

Especialização máxima.

Conhecer:

```text
Spark 4.1.1
Python 3.13
Java 17
Scala 2.13.17
Hadoop 3.4.2
Iceberg 1.11.0
Arrow 18.3.0
Parquet 1.16.0
Pandas 2.3.3
NumPy 2.4.4
```

A matriz deve vir da documentação oficial e ser versionada, não hard-coded em regras. ([Documentação AWS][5])

---

# 13. GLUE 5.1 → 6.0 MIGRATION DOCTOR

Especialização extrema para:

```text
Glue 5.1
      ↓
Glue 6.0
```

Detectar:

## S3

EMRFS → S3A.

## Scala

2.12 → 2.13.

Detectar automaticamente JARs compilados para Scala 2.12.

## Spark

3.5.6 → 4.1.1.

## Python

3.11 → 3.13.

## ANSI

Detectar possíveis falhas por mudança de comportamento.

## Date/time

Detectar impacto de mudanças em parsing.

## Java

17 permanece.

## Dependencies

Comparar toda a árvore.

A documentação oficial do Glue 6.0 destaca exatamente essas mudanças, incluindo a remoção do EMRFS, Scala 2.13, ANSI mode ON por padrão e Python 3.13. ([Documentação AWS][5])

---

# 14. GLUE MIGRATION MATRIX COMPLETA

Implementar:

```text
Glue 3 → 4
Glue 3 → 5
Glue 3 → 5.1
Glue 3 → 6

Glue 4 → 5
Glue 4 → 5.1
Glue 4 → 6

Glue 5 → 5.1
Glue 5 → 6

Glue 5.1 → 6
```

E rotas reversas somente como:

```text
rollback analysis
```

não como downgrade automático.

---

# 15. GLUE → EMR MIGRATION ENGINE

Isso é obrigatório.

Permitir:

```text
Glue 4.0 → EMR X
Glue 5.0 → EMR X
Glue 5.1 → EMR X
Glue 6.0 → EMR X
```

e também:

```text
EMR → Glue
EMR release → EMR release
```

---

# 16. EMR VERSION INTELLIGENCE

Para cada EMR release:

```text
EMR release
Spark
Hadoop
Hive
Iceberg
Python
Java
Scala
AWS SDK
EMRFS/S3A
Lake Formation
```

Detectar:

```text
Spark mismatch
Scala mismatch
Java mismatch
Iceberg mismatch
Hadoop mismatch
AWS SDK mismatch
```

---

# 17. CROSS-RUNTIME MIGRATION

Criar:

```text
Runtime Translation Engine
```

Exemplo:

```text
Glue 4
Spark 3.3
Python 3.10
Iceberg A

        ↓

EMR 7.x
Spark 3.5
Python 3.11
Iceberg B
```

Produzir:

```text
compatibility matrix
migration risks
code changes
configuration changes
dependency changes
data format risks
security changes
performance changes
cost changes
```

---

# 18. ICEBERG VERSION INTELLIGENCE

Especialização por:

```text
Iceberg 0.x
Iceberg 1.x
```

com máxima granularidade possível.

Para cada versão:

```text
Spark compatibility
Java compatibility
Scala compatibility
catalog compatibility
format version
feature availability
schema evolution
partition evolution
row-level deletes
equality deletes
position deletes
branches
tags
WAP
REST catalog
Glue catalog
S3 Tables
maintenance
statistics
metadata
```

A matriz deve refletir a compatibilidade oficial do Iceberg com cada linha do Spark. O próprio projeto mantém integrações específicas por versão do Spark — por exemplo `spark/v3.5` e `spark/v4.0` — e publica artefatos específicos para essas linhas. ([Apache Iceberg][6])

---

# 19. ICEBERG MIGRATION ENGINE

Detectar:

```text
Iceberg upgrade
Iceberg downgrade
Spark upgrade + Iceberg upgrade
Glue upgrade + Iceberg upgrade
EMR upgrade + Iceberg upgrade
```

Nunca analisar Iceberg isoladamente.

Sempre calcular:

```text
Spark × Iceberg × Catalog × Runtime × Engine
```

---

# 20. ICEBERG TROUBLESHOOTING

Criar banco especializado para:

```text
CommitFailedException
ValidationException
NoSuchTableException
NoSuchNamespaceException
NoSuchMethodError
ClassNotFoundException
schema mismatch
partition mismatch
snapshot conflict
manifest conflict
metadata conflict
delete file problems
catalog problems
S3 authorization
KMS authorization
Lake Formation authorization
```

---

# 21. ICEBERG PERFORMANCE ENGINE

Diagnosticar:

```text
small files
large files
manifest explosion
metadata explosion
snapshot accumulation
delete files
partition skew
bad distribution
bad sorting
poor pruning
poor statistics
```

Produzir:

```text
read amplification
write amplification
metadata amplification
delete amplification
```

---

# 22. ICEBERG COST ENGINE

Estimar:

```text
storage
S3 requests
metadata operations
manifest operations
compute
compaction
snapshot maintenance
Athena scan
Glue compute
EMR compute
```

Comparar:

```text
current
optimized
projected
```

---

# 23. PARQUET VERSION INTELLIGENCE

Criar conhecimento por versão:

```text
Parquet 1.x
```

com:

```text
encoding
compression
statistics
page index
bloom filters
encryption
logical types
nested types
decimal
timestamp
INT96
```

Relacionar com:

```text
Spark
Glue
EMR
Iceberg
Athena
Arrow
PyArrow
Pandas
```

---

# 24. PARQUET MIGRATION DOCTOR

Detectar:

```text
old writer
new reader
new writer
old reader
mixed files
mixed encodings
mixed schemas
```

E responder:

> "Posso ler esses arquivos depois de migrar o Spark?"

---

# 25. PARQUET PERFORMANCE ENGINE

Calcular:

```text
file size distribution
row group distribution
compression ratio
column pruning
predicate pushdown
statistics effectiveness
page skipping opportunity
bloom filter opportunity
scan amplification
```

---

# 26. PYTHON VERSION INTELLIGENCE

Especializar:

```text
Python 3.8
3.9
3.10
3.11
3.12
3.13
```

e relacionar com:

```text
PySpark
PyArrow
Pandas
NumPy
cloudpickle
boto3
```

Detectar:

```text
ABI incompatibility
wheel incompatibility
binary dependency
C-extension
Python syntax
deprecated API
dependency resolver conflict
```

---

# 27. PYTHON MIGRATION DOCTOR

Exemplo:

```text
Python 3.10
       ↓
Python 3.11
       ↓
Python 3.13
```

Detectar:

```text
removed APIs
deprecated APIs
package incompatibilities
native extensions
serialization changes
typing issues
timezone behavior
dependency constraints
```

---

# 28. PYSPARK MIGRATION DOCTOR

Especializar:

```text
Python API
JVM bridge
Py4J
Arrow
Pandas UDF
Python UDF
RDD
DataFrame
SQL
Streaming
```

---

# 29. LAKE FORMATION VERSION INTELLIGENCE

Não tratar Lake Formation como uma única versão.

Criar conhecimento para:

```text
cross-account version 1
cross-account version 2
cross-account version 3
cross-account version 4
cross-account version 5
```

e para diferentes modos:

```text
Lake Formation mode
Hybrid access mode
IAM access control
LF-TBAC
named resource
federated catalog
```

---

# 30. LAKE FORMATION CROSS-ACCOUNT VERSION DOCTOR

Criar:

```text
LF Cross Account Migration Engine
```

para:

```text
v1 → v2
v2 → v3
v3 → v4
v4 → v5
```

e cenários mistos:

```text
producer v1
consumer v3
```

---

# 31. LAKE FORMATION VERSION 5

Tratar como mudança de alto impacto.

O conhecimento deve registrar:

```text
wildcard resource patterns
RAM
resource associations
large-scale sharing
migration behavior
downgrade limitations
```

A documentação atual indica que Cross Account Version 5 permite compartilhar quantidades muito maiores de tabelas usando padrões wildcard e que, após atualização para v5, downgrade não é suportado. ([Documentação AWS][2])

---

# 32. LAKE FORMATION TROUBLESHOOTING DATABASE

Cobrir obrigatoriamente:

```text
AccessDeniedException
Insufficient Lake Formation permissions
Illegal combination
IAMAllowedPrincipals
DATA_LOCATION_ACCESS
SELECT missing
DESCRIBE missing
CREATE_TABLE missing
ALTER missing
DROP missing
RAM invitation
RAM share
resource link
LF-Tags
data filters
cross-account
KMS
S3
Glue Catalog
EMR
Athena
Glue ETL
```

A própria documentação oficial possui uma seção específica de troubleshooting cross-account com problemas de permissões, RAM, EMR e combinações ilegais de permissões; esses casos devem virar fixtures e regras do Spark Forge. ([Documentação AWS][7])

---

# 33. LAKE FORMATION AUTHORIZATION GRAPH

Modelar:

```text
Account
 ↓
Organization
 ↓
RAM
 ↓
Lake Formation
 ↓
Catalog
 ↓
Database
 ↓
Table
 ↓
Resource Link
 ↓
S3
 ↓
KMS
```

Cada edge:

```yaml
permission:
expected:
actual:
evidence:
status:
```

---

# 34. CENÁRIO ESPECIAL: EMR + LAKE FORMATION

Criar troubleshooting especializado.

Exemplo:

```text
EMR
 ↓
Spark
 ↓
Glue Catalog
 ↓
Lake Formation
 ↓
cross-account
```

O engine deve reconhecer problemas específicos do EMR, inclusive APIs Glue adicionais exigidas por algumas bibliotecas.

A documentação atual de troubleshooting da AWS registra, por exemplo, um cenário cross-account em EMR no qual bibliotecas Spark tentam chamar `glue:GetUserDefinedFunctions`, podendo resultar em AccessDenied dependendo das permissões/RAM managed permissions. ([Documentação AWS][7])

---

# 35. CENÁRIO ESPECIAL: GLUE + LAKE FORMATION

Especializar em:

```text
GlueContext
DynamicFrame
Spark DataFrame
FGAC
IAM
Lake Formation
Iceberg
```

Distinguir:

```text
catalog access
metadata access
data access
write access
```

---

# 36. CENÁRIO ESPECIAL: ATHENA + LAKE FORMATION + ICEBERG

Diagnosticar:

```text
Athena
 ↓
Lake Formation
 ↓
Glue Catalog
 ↓
Iceberg
 ↓
S3
 ↓
KMS
```

---

# 37. ARQUITETURA DOCTOR

O Spark Forge também deve atuar ANTES de existir código.

Entrada:

```text
"Quero construir um lakehouse"
```

Saída:

```text
recommended architecture
runtime
Spark
Glue/EMR
Iceberg
Parquet
Catalog
Lake Formation
S3
security
partition strategy
file sizing
cost model
```

---

# 38. MIGRATION ARCHITECT

Entrada:

```text
current architecture
target architecture
```

Saída:

```text
gap analysis
dependencies
risks
breaking changes
migration phases
rollback
validation
benchmark
cost delta
```

---

# 39. PERFORMANCE ARCHITECT

Analisar arquitetura antes da implementação.

Perguntas:

```text
Where is the bottleneck likely to be?
How much data?
How many files?
How many partitions?
What query patterns?
What joins?
What retention?
What concurrency?
What SLA?
What budget?
```

---

# 40. COST ARCHITECT

O sistema deve conseguir comparar:

```text
Glue
vs
EMR
vs
EMR Serverless
```

considerando:

```text
runtime
DPU/instance
duration
autoscaling
storage
S3
Athena
network
KMS
maintenance
```

Não escolher simplesmente o menor preço por hora.

O objetivo é:

```text
lowest total cost for required SLA
```

---

# 41. COST × PERFORMANCE OPTIMIZER

Criar fronteira:

```text
           PERFORMANCE
               ↑
               │       ● A
               │
               │   ● B
               │
               │ ● C
               │
               └────────────────→ COST
```

Encontrar:

```text
Pareto frontier
```

---

# 42. WORKLOAD DNA

Classificar automaticamente:

```text
IO_BOUND
CPU_BOUND
MEMORY_BOUND
SHUFFLE_BOUND
NETWORK_BOUND
SKEW_BOUND
PYTHON_BOUND
METADATA_BOUND
CATALOG_BOUND
AUTHORIZATION_BOUND
SMALL_FILES_BOUND
JOIN_BOUND
WINDOW_BOUND
WRITE_BOUND
READ_BOUND
```

E permitir múltiplos scores:

```yaml
workload_dna:
  shuffle: 0.92
  skew: 0.81
  io: 0.44
  python: 0.22
```

---

# 43. INTELLIGENT TUNING

Não criar:

```text
if files > X:
    use Y
```

Criar:

```text
facts
+
runtime
+
workload
+
historical evidence
+
benchmark
+
constraints
```

→ recommendation.

---

# 44. AUTO-TUNING

Criar solver para:

```text
executor count
executor cores
executor memory
memory overhead
shuffle partitions
AQE
broadcast threshold
file partition size
parallelism
worker type
worker count
autoscaling
Iceberg target file size
write distribution
```

---

# 45. TUNING POR OBJETIVO

Permitir:

```text
optimize_for:
  latency
  cost
  reliability
  throughput
  memory
  stability
  balanced
```

---

# 46. MIGRATION SIMULATOR

Criar:

```text
Current Runtime
       ↓
Migration Simulator
       ↓
Target Runtime
```

Simular:

```text
API changes
config changes
dependency changes
behavior changes
security changes
performance changes
cost changes
```

---

# 47. MIGRATION SCORE

Gerar:

```yaml
migration:
  compatibility_score:
  code_risk:
  runtime_risk:
  dependency_risk:
  data_risk:
  security_risk:
  performance_risk:
  cost_risk:
  rollback_difficulty:
  overall_risk:
```

---

# 48. MIGRATION READINESS

Resultado:

```text
READY
READY_WITH_CHANGES
HIGH_RISK
BLOCKED
UNKNOWN
```

---

# 49. TROUBLESHOOTING ENGINE

Entrada:

```text
error
stacktrace
runtime
version
configuration
architecture
```

Saída:

```text
top root causes
confidence
evidence
diagnostic steps
fix
workaround
migration impact
```

---

# 50. ERROR SIGNATURE DATABASE

Cada erro deve possuir:

```yaml
signature:
  regex:
  exception:
  message_pattern:

versions:
  affected:
  fixed:
  introduced:

runtime:
  glue:
  emr:
  spark:

causes:
solutions:
workarounds:
references:
```

---

# 51. VERSION DIFF ENGINE

Criar:

```bash
sparkforge version diff spark 3.5 4.0
sparkforge version diff glue 4.0 5.1
sparkforge version diff glue 5.1 6.0
sparkforge version diff iceberg 1.x 1.y
sparkforge version diff lakeformation 4 5
```

Output:

```text
NEW
REMOVED
CHANGED
DEPRECATED
DEFAULT_CHANGED
INCOMPATIBLE
RISK
```

---

# 52. ARCHITECTURE DIFF

Permitir:

```bash
sparkforge architecture diff architecture-v1.yaml architecture-v2.yaml
```

Comparar:

```text
runtime
Spark
Glue
EMR
Iceberg
Parquet
catalog
security
network
cost
performance
```

---

# 53. MIGRATION PLAN GENERATOR

Gerar plano:

```text
Phase 0
Inventory

Phase 1
Compatibility

Phase 2
Code remediation

Phase 3
Infrastructure

Phase 4
Data validation

Phase 5
Performance benchmark

Phase 6
Cost validation

Phase 7
Canary

Phase 8
Production rollout

Phase 9
Post-migration validation
```

---

# 54. ROLLBACK ENGINE

Toda migração deve responder:

```text
Can we rollback?
How?
How long?
What data changed?
What snapshots exist?
What schema changed?
What catalog changed?
What permissions changed?
```

---

# 55. CANARY ENGINE

Permitir:

```text
old runtime
vs
new runtime
```

no mesmo workload.

Comparar:

```text
correctness
runtime
cost
shuffle
spill
memory
files
records
schema
```

---

# 56. REGRESSION DETECTION

Detectar automaticamente:

```text
runtime increased
cost increased
shuffle increased
spill increased
memory increased
failures increased
output changed
schema changed
```

---

# 57. KNOWLEDGE SOURCES

Priorizar:

1. Apache Spark official docs
2. AWS Glue official docs
3. AWS EMR official docs
4. Apache Iceberg official docs
5. Apache Parquet official docs
6. AWS Lake Formation official docs
7. AWS Glue Catalog docs
8. AWS Athena docs
9. AWS S3 docs
10. AWS KMS docs
11. Apache Arrow docs
12. Pandas docs
13. PyArrow docs

Community sources podem complementar troubleshooting, mas nunca substituir documentação oficial para determinar compatibilidade.

---

# 58. KNOWLEDGE VERSIONING

Toda entrada deve conter:

```yaml
technology:
version:
vendor:
runtime:
feature:
status:
source:
retrieved_at:
confidence:
```

---

# 59. CONFLICT RESOLUTION

Se duas fontes discordarem:

```text
official documentation
        >
official release notes
        >
official issue tracker
        >
official source code
        >
community
        >
heuristic
```

Mas registrar o conflito.

---

# 60. EVIDENCE MODEL

Toda conclusão precisa ter:

```text
fact
evidence
source
runtime
confidence
```

---

# 61. NÃO FAZER OVERGENERALIZATION

É proibido transformar:

```text
Spark 3.5 behavior
```

em:

```text
Spark behavior
```

ou:

```text
Glue 5.1 behavior
```

em:

```text
Glue behavior
```

ou:

```text
Iceberg 1.x behavior
```

em:

```text
Iceberg behavior
```

---

# 62. RUNTIME-SPECIFIC RULES

Uma regra deve poder declarar:

```yaml
runtime_scope:
  spark:
    min:
    max:

  glue:
    versions:

  emr:
    releases:

  iceberg:
    versions:
```

---

# 63. PATCH-SPECIFIC KNOWLEDGE

Quando uma correção depender de patch:

```text
Spark 3.5.4
Spark 3.5.5
Spark 3.5.6
```

não generalizar para:

```text
Spark 3.5
```

---

# 64. VENDOR PATCHES

Diferenciar:

```text
Apache Spark
Amazon EMR Spark
AWS Glue Spark
```

Mesmo quando o número de versão parece equivalente.

---

# 65. DEPENDENCY GRAPH

Criar grafo:

```text
Glue
 ↓
Spark
 ↓
Scala
 ↓
Java
 ↓
Hadoop
 ↓
Parquet
 ↓
Iceberg
 ↓
Arrow
 ↓
Python
 ↓
PyArrow
 ↓
Pandas
```

E:

```text
Spark
 ↓
Glue Catalog
 ↓
Lake Formation
 ↓
RAM
 ↓
IAM
 ↓
S3
 ↓
KMS
```

---

# 66. DEPENDENCY CONFLICT DETECTOR

Detectar:

```text
multiple Iceberg jars
multiple Parquet jars
multiple Hadoop jars
multiple Jackson jars
multiple Arrow versions
Scala 2.12 + Scala 2.13
Spark 3.x jar + Spark 4.x jar
```

---

# 67. JAR ANALYZER

Analisar:

```text
jar
manifest
pom
scala binary version
artifact
groupId
artifactId
version
transitive dependencies
```

Detectar:

```text
binary incompatibility
class shadowing
classpath conflict
NoSuchMethodError
ClassNotFoundException
```

---

# 68. PYTHON ENVIRONMENT ANALYZER

Analisar:

```text
requirements
constraints
wheel
python version
ABI
native libs
```

Detectar incompatibilidades antes da execução.

---

# 69. PRE-FLIGHT CHECK

Criar:

```bash
sparkforge preflight
```

Antes de executar workload.

Verificar:

```text
runtime
dependencies
Spark
Python
Iceberg
Parquet
Lake Formation
IAM
S3
KMS
catalog
configuration
```

---

# 70. MIGRATION PREFLIGHT

Criar:

```bash
sparkforge migration preflight \
  --source glue:4.0 \
  --target glue:6.0
```

Resultado:

```text
BLOCKERS
WARNINGS
CHANGES
RECOMMENDATIONS
TESTS_REQUIRED
```

---

# 71. PERFORMANCE PREFLIGHT

Criar:

```bash
sparkforge performance preflight
```

---

# 72. COST PREFLIGHT

Criar:

```bash
sparkforge cost preflight
```

---

# 73. SECURITY PREFLIGHT

Criar:

```bash
sparkforge security preflight
```

---

# 74. ARCHITECTURE PREFLIGHT

Criar:

```bash
sparkforge architecture preflight
```

---

# 75. FINAL UNIFIED ENGINE

Integrar tudo:

```text
                    SPARK FORGE
                         │
        ┌────────────────┼────────────────┐
        │                │                │
     Runtime          Workload         Architecture
     Intelligence     Intelligence     Intelligence
        │                │                │
        └────────────────┼────────────────┘
                         │
                 Diagnosis Engine
                         │
                 Root Cause Engine
                         │
                  Debate Engine
                         │
                Recommendation Engine
                         │
                 Experiment Engine
                         │
                 Benchmark Engine
                         │
                  Cost Optimizer
                         │
                 Migration Engine
                         │
                 Learning Engine
```

---

# 76. RESULTADO ESPERADO

O Spark Forge deve conseguir atuar em pelo menos quatro grandes modos.

## MODE 1 — BUILD

Construção de nova arquitetura.

```text
"Projete um lakehouse para X."
```

## MODE 2 — MIGRATE

Migração.

```text
"Tenho Glue 4.0 e quero Glue 5.1."
```

ou:

```text
"Tenho Glue 5.1 e quero EMR 7.x."
```

## MODE 3 — OPTIMIZE

Performance/custo.

```text
"Esse job demora 3 horas e custa X."
```

## MODE 4 — TROUBLESHOOT

Produção.

```text
"Depois da migração apareceu NoSuchMethodError."
```

---

# 77. EXEMPLO DE RESPOSTA ESPERADA

Diante de:

> "Migrar Glue 4.0 para Glue 6.0"

o Spark Forge deve produzir:

```text
CURRENT
Glue 4.0
Spark 3.3
Python 3.10
Java 8
Scala 2.12
Iceberg X

TARGET
Glue 6.0
Spark 4.1.1
Python 3.13
Java 17
Scala 2.13
Iceberg 1.11

CRITICAL CHANGES

1. Spark 3.3 → 4.1
2. Python 3.10 → 3.13
3. Java 8 → 17
4. Scala 2.12 → 2.13
5. EMRFS → S3A
6. ANSI behavior changes
7. Iceberg compatibility
8. custom JAR compatibility
9. PyArrow compatibility
10. Pandas compatibility

CODE IMPACT

...

DEPENDENCY IMPACT

...

DATA IMPACT

...

SECURITY IMPACT

...

PERFORMANCE IMPACT

...

COST IMPACT

...

BLOCKERS

...

MIGRATION PLAN

...

ROLLBACK PLAN

...

VALIDATION PLAN

...

BENCHMARK PLAN

...

GO/NO-GO
```

---

# 78. REGRA FINAL

O Spark Forge NÃO deve responder:

> "Use configuração X porque é uma boa prática."

Deve responder:

> "Para Spark X + Glue Y + Python Z + Iceberg A + workload B, encontrei os fatos C/D/E. A documentação indica F. O risco é G. A recomendação H é compatível com esse runtime. A alternativa I possui menor risco, porém menor benefício. Recomendo executar o experimento J antes da promoção."

---

# 79. DEFINIÇÃO DE EXCELÊNCIA

O objetivo final é que o Spark Forge seja capaz de responder com profundidade equivalente a um time formado por:

```text
Senior Spark Engineer
+
Senior Python Engineer
+
Senior AWS Glue Engineer
+
Senior EMR Engineer
+
Senior Iceberg Engineer
+
Senior Parquet Engineer
+
Senior Lake Formation Engineer
+
Cloud Architect
+
Performance Engineer
+
FinOps Engineer
+
Security Engineer
+
Migration Specialist
+
SRE
```

mas com uma diferença fundamental:

o conhecimento precisa ser:

```text
version-aware
runtime-aware
evidence-aware
architecture-aware
performance-aware
cost-aware
security-aware
migration-aware
experiment-aware
```

---

# 80. REGRA DE OURO

Não criar simplesmente:

```text
mais agents
mais rules
mais MCPs
```

Criar:

```text
MAIS CONHECIMENTO
+
MAIS GRANULARIDADE
+
MAIS CONTEXTO
+
MAIS EVIDÊNCIA
+
MAIS VERSIONAMENTO
+
MAIS TROUBLESHOOTING
+
MAIS EXPERIMENTAÇÃO
+
MAIS VALIDAÇÃO
```

O resultado esperado é:

```text
VERSION
    ↓
RUNTIME
    ↓
DEPENDENCIES
    ↓
ARCHITECTURE
    ↓
WORKLOAD
    ↓
FACTS
    ↓
EVIDENCE
    ↓
DIAGNOSIS
    ↓
ROOT CAUSE
    ↓
DEBATE
    ↓
RECOMMENDATION
    ↓
MIGRATION / OPTIMIZATION / FIX
    ↓
EXPERIMENT
    ↓
BENCHMARK
    ↓
COST
    ↓
SECURITY
    ↓
VALIDATION
    ↓
PROMOTION
    ↓
LEARNING
```

Esse fluxo deve ser considerado a arquitetura-alvo do Spark Forge.

### O ponto que eu considero mais importante

Eu faria uma mudança conceitual grande no projeto: **o eixo principal do Spark Forge deveria deixar de ser “technology → rules” e passar a ser “technology × version × runtime × scenario”.**

Por exemplo:

```text
Spark 3.5
×
Glue 5.1
×
Iceberg 1.x
×
Python 3.11
×
Lake Formation Cross Account
×
MERGE
×
200M records
×
skewed workload
```

é um **cenário diferente** de:

```text
Spark 4.1
×
Glue 6.0
×
Iceberg 1.11
×
Python 3.13
×
Lake Formation
×
MERGE
×
200M records
```

Mesmo que superficialmente ambos sejam “um job Spark usando Iceberg”.

E isso permite ao Spark Forge chegar a algo muito mais poderoso:

> **“Eu conheço esse problema porque conheço essa combinação específica de runtime + versão + engine + formato + arquitetura + workload.”**

Isso também casa perfeitamente com a arquitetura que vocês já construíram de **facts → evidence → claims → conflicts → arbitration → execution**.

Um detalhe especialmente valioso é o **Cross Account Version Doctor** para Lake Formation. A AWS hoje documenta diferenças entre versões 1–5, inclusive o fato de a v5 permitir compartilhamento em escala muito maior e não suportar downgrade depois da atualização. ([Documentação AWS][2])

E eu trataria **troubleshooting como primeira classe**, não como documentação auxiliar. A própria AWS possui uma árvore específica para troubleshooting de Lake Formation cross-account, incluindo `DATA_LOCATION_ACCESS`, `IAMAllowedPrincipals`, RAM, EMR e permissões cross-account. ([Documentação AWS][7])

**Esse é, na minha visão, o caminho para levar o Spark Forge de ~9/10 para algo realmente diferenciado:** não simplesmente saber “Spark”, mas ser capaz de responder **qual Spark, qual distribuição, qual runtime, qual versão, qual Iceberg, qual Glue, qual Lake Formation, qual arquitetura e qual workload — e exatamente o que muda entre eles.**

[1]: https://docs.aws.amazon.com/pt_br/glue/latest/dg/migrating-version-40.html?utm_source=chatgpt.com "Migrar trabalhos do AWS Glue para Spark para o AWS Glue versão 4.0 - AWS Glue"
[2]: https://docs.aws.amazon.com/lake-formation/latest/dg/optimize-ram.html?utm_source=chatgpt.com "Updating cross-account data sharing version settings - AWS Lake Formation"
[3]: https://docs.aws.amazon.com/glue/latest/dg/migrating-version-40.html?utm_source=chatgpt.com "Migrating AWS Glue for Spark jobs to AWS Glue version 4.0 - AWS Glue"
[4]: https://docs.aws.amazon.com/glue/latest/dg/migrating-version-50.html?utm_source=chatgpt.com "Migrating AWS Glue for Spark jobs to AWS Glue version 5.0 - AWS Glue"
[5]: https://docs.aws.amazon.com/us_en/glue/latest/dg/migrating-version-60.html?utm_source=chatgpt.com "Migrating AWS Glue for Spark jobs to AWS Glue version 6.0 - AWS Glue"
[6]: https://iceberg.apache.org/multi-engine-support/?utm_source=chatgpt.com "Multi-Engine Support - Apache Iceberg™"
[7]: https://docs.aws.amazon.com/lake-formation/latest/dg/troubleshooting.html?utm_source=chatgpt.com "Troubleshooting Lake Formation - AWS Lake Formation"


obs: não commite esse prompt!