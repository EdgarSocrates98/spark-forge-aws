# =====================================================================
# SPARK FORGE AWS
# GLUE 6.0 / SPARK 4.1 / ICEBERG 1.11 / ICEBERG V3
# MIGRATION & COMPATIBILITY INTELLIGENCE
# MASTER IMPLEMENTATION PROMPT FOR CLAUDE CODE
# =====================================================================

Você está trabalhando no repositório:

https://github.com/EdgarSocrates98/spark-forge-aws

Este projeto já possui:

- analisadores determinísticos;
- catálogo de regras;
- knowledge base versionada;
- runtime detection;
- CLI;
- MCP;
- skills;
- agents;
- golden cases;
- offline-first;
- mecanismos de avaliação;
- arquitetura agentic;
- evolução planejada para Harness Engineering.

NÃO crie um sistema paralelo.

Sua missão é EVOLUIR o Spark Forge adicionando suporte profissional,
profundo, verificável e testável para:

AWS Glue 6.0
Apache Spark 4.1
Apache Iceberg 1.11
Apache Iceberg specification v3

e as seguintes migrações:

Glue 4.0 → 5.1
Glue 4.0 → 6.0
Glue 5.0 → 5.1
Glue 5.0 → 6.0
Glue 5.1 → 6.0

Essa evolução deve ser integrada ao:

Spark Forge Runtime Harness
Spark Forge Evaluation Harness
Token Economy Engine
Capability Registry
Knowledge System
Rule Catalog
CLI
MCP
Agents
Skills
Deterministic Tools
Golden Cases
Holdouts

NÃO apenas documente Glue 6.

CONSTRUA capacidades executáveis.

======================================================================
1. REGRA ABSOLUTA: VERIFICAR FATOS ATUAIS
======================================================================

Glue 6.0 é extremamente recente.

NÃO use conhecimento interno do modelo como fonte final.

Antes de implementar qualquer matriz:

pesquise documentação oficial atual.

Prioridade de fontes:

1. AWS Glue Developer Guide
2. AWS What's New
3. AWS News Blog
4. AWS Glue API/CLI docs
5. AWS Lake Formation docs
6. Apache Spark official docs
7. Apache Iceberg official docs
8. Apache Iceberg specification
9. HashiCorp AWS Provider docs
10. AWS Prescriptive Guidance

Para cada fato temporal registrar:

source
source_type
retrieved_at
verified_at
product_version
confidence
status

Possíveis status:

VERIFIED
CONFLICTING
STALE
UNVERIFIED
UNRESOLVED

Nunca transformar:

CONFLICTING

em:

VERIFIED.

======================================================================
2. CONFLITO PYTHON GLUE 6.0
======================================================================

Existe neste momento uma divergência entre fontes oficiais AWS.

Uma fonte oficial do lançamento informa:

Python 3.12

Outra fonte oficial AWS What's New informa:

Python 3.13

NÃO escolha uma delas arbitrariamente.

Investigue:

AWS Glue Developer Guide
runtime release notes
Docker images se oficiais
API documentation
migration documentation
official release artifacts

Se uma documentação técnica autoritativa resolver o conflito:

registre a resolução.

Caso contrário:

Glue6PythonVersion:

status: UNRESOLVED
evidence:
  - source A: Python 3.12
  - source B: Python 3.13

O Spark Forge deve ser capaz de representar
inconsistência entre fontes.

Isso deve virar um GOLDEN CASE
do Evidence Engine.

======================================================================
3. BASELINE CONHECIDA A SER VERIFICADA
======================================================================

Validar oficialmente:

Glue 4.0:

Spark 3.3.0
Python 3.10
Java 8
Iceberg 1.0.0

Glue 5.0:

validar runtime completo

Glue 5.1:

Spark 3.5.6
Python 3.11
Scala 2.12.x
Java 17
Iceberg 1.10.0

Glue 6.0:

Spark 4.1
Scala 2.13
Iceberg 1.11.0

Python:
resolver conforme seção anterior.

Também pesquisar:

Java
Hadoop
AWS SDK
Boto
JDBC drivers
Glue libraries
Delta
Hudi
Log4j
Arrow
Pandas
PyArrow
Scala binary compatibility.

======================================================================
4. NOVA PRIORIDADE ARQUITETURAL
======================================================================

Glue 6.0 passa a ser:

PRIORITY P0

junto de:

Glue 4→5.1
Lake Formation
Iceberg
Terraform
Spark Performance.

Atualizar:

Capability Matrix
Runtime Matrix
Cross-Service Constraints
Migration Matrix
Knowledge Index
Rules Catalog
Harness Capabilities
Golden Suites.

======================================================================
5. NÃO ABANDONAR GLUE 5.1
======================================================================

Glue 5.1 continua sendo conhecimento crítico.

NÃO substituir:

Glue 4 → 5.1

por:

Glue 4 → 6.

Existem ambientes corporativos onde a migração intermediária
para 5.1 continua relevante.

O Forge deve responder:

Qual target faz mais sentido?

5.1?

6.0?

por quê?

======================================================================
6. TARGET VERSION ADVISOR
======================================================================

Criar capability:

aws.glue.target_version_recommendation

Criar:

forge glue recommend-version

Input:

current Glue version
job code
dependencies
JARs
Python libraries
Iceberg usage
Lake Formation usage
cross-account
Parquet
streaming
consumer compatibility
risk tolerance

Output:

5.1
6.0
STAY_TEMPORARILY
UNRESOLVED

Com:

reasoning summary
evidence
risks
compatibility
required work
future benefit.

Não escolher versão apenas porque é a mais nova.

======================================================================
7. MIGRATION GRAPH
======================================================================

Representar migrações como grafo.

Nodes:

Glue 3
Glue 4
Glue 5
Glue 5.1
Glue 6

Edges possuem:

runtime_delta
spark_delta
python_delta
java_delta
scala_delta
iceberg_delta
connector_delta
behavior_delta
migration_rules

Assim:

4 → 6

pode compor knowledge de:

4 → 5
5 → 5.1
5.1 → 6

quando apropriado.

Mas NÃO obrigar execução intermediária
dessas versões em produção.

======================================================================
8. NOVO AGENT
======================================================================

Evoluir:

sf-glue-migration-specialist

Não criar outro Agent exclusivamente chamado:

sf-glue6-agent

se o especialista existente puder absorver o conhecimento.

Sua especialização deve cobrir:

Glue 2+
Glue 3
Glue 4
Glue 5
Glue 5.1
Glue 6

e upgrades entre versões.

======================================================================
9. NOVAS SKILLS GLUE 6
======================================================================

Criar ou evoluir:

glue-6-runtime

glue-51-to-6-migration

glue-5-to-6-migration

glue-4-to-6-migration

glue-6-breaking-changes

glue-6-dependency-compatibility

glue-6-python-compatibility

glue-6-java-compatibility

glue-6-scala-compatibility

glue-6-spark-compatibility

glue-6-iceberg

glue-6-lakeformation

glue-6-cross-account

glue-6-parquet

glue-6-streaming

glue-6-arrow

glue-6-declarative-pipelines

glue-6-realtime-mode

glue-6-cost

glue-6-performance

glue-6-terraform

glue-6-troubleshooting

Skills devem ser lazy-loaded.

Não carregar todas em qualquer task Glue.

======================================================================
10. SPARK 3.3 → 3.5 → 4.1
======================================================================

Criar knowledge profundo para:

Spark 3.3
→
Spark 3.5
→
Spark 4.1.

Pesquisar breaking changes oficiais.

Cobrir:

Spark SQL

DataFrame API

PySpark

Structured Streaming

Catalyst

AQE

Arrow

UDF

UDTF

timestamps

ANSI mode

casting

schema inference

Parquet

JSON

CSV

JDBC

Python behavior

Scala APIs

Java APIs

serialization

checkpointing

state store

query planner

joins

functions

deprecated APIs

removed APIs.

======================================================================
11. SPARK 4 MIGRATION ANALYZER
======================================================================

Criar tool:

sparkforge_spark4_migration_scan

Input:

PySpark source
SQL
Spark configs

Output:

removed APIs

deprecated APIs

behavior changes

SQL semantic risks

configuration changes

Python compatibility

potential output differences

performance opportunities.

Preferir AST/static rules.

LLM somente para ambiguidades.

======================================================================
12. SPARK 4 SKILLS
======================================================================

Criar:

spark-4-runtime

spark-4-migration

spark-35-to-41

spark-33-to-41

spark-4-sql

spark-4-pyspark

spark-4-streaming

spark-4-arrow

spark-4-udf

spark-4-udtf

spark-4-declarative-pipelines

spark-4-realtime-mode

spark-4-performance

spark-4-breaking-changes.

======================================================================
13. SCALA 2.12 → 2.13
======================================================================

Isso é HIGH RISK para custom JARs.

Criar:

scala-binary-compatibility

spark-scala-212-to-213

custom-jar-glue6-compatibility

Tool:

sparkforge_jar_compatibility_scan

Analisar quando possível:

MANIFEST.MF

Maven coordinates

Scala suffix:

_2.12
_2.13

Spark dependencies

Iceberg dependencies

Hadoop dependencies

AWS SDK dependencies

JDBC drivers.

Detectar:

likely incompatible binary.

======================================================================
14. CUSTOM JAR MIGRATION
======================================================================

Golden cases:

Glue 5.1 + JAR Scala 2.12
→ Glue 6.0.

Glue 4 + Java 8 custom JAR
→ Glue 6.

Glue custom connector
→ Spark 4.

Resultado:

PASS

RECOMPILE_REQUIRED

DEPENDENCY_UPGRADE_REQUIRED

UNKNOWN

BLOCKED.

======================================================================
15. PYTHON MIGRATION
======================================================================

Criar analyzer/skill para:

Python runtime compatibility.

Detectar:

deprecated stdlib

removed APIs

binary wheels

native extensions

version-pinned packages

PyArrow

Pandas

NumPy

custom wheels

requirements.txt

--additional-python-modules

S3 wheel references.

Não instalar pacote suspeito apenas para analisá-lo.

======================================================================
16. DEPENDENCY LOCK ANALYSIS
======================================================================

Criar:

forge glue dependency-audit

Input:

requirements
job parameters
JAR metadata

Output:

runtime dependencies

pins

potential conflicts

Spark conflicts

Iceberg conflicts

Java conflicts

Scala conflicts

Python ABI risk.

======================================================================
17. ICEBERG 1.11
======================================================================

Atualizar:

sf-iceberg-platform-specialist.

Knowledge profundo de Iceberg 1.11.

Validar oficialmente:

Spark 4.1 support

REST Catalog enhancements

remote scan planning

incremental remote scan planning

metadata table planning

LIMIT pushdown

vectorized Parquet improvements

unique table locations

snapshot cleanup modes

Partition Stats Scan

MERGE schema evolution

Variant support

shredded Variant

streaming planner improvements

adaptive split sizing

Java support changes

Spark support deprecations.

======================================================================
18. ICEBERG SPEC V3
======================================================================

Criar domain:

iceberg-v3.

Cobrir:

Variant

Variant shredding

Geometry

Geography

nanosecond timestamps

Unknown type

default values

multi-argument transforms

row lineage

deletion vectors.

Não limitar knowledge à implementação Glue.

Separar:

ICEBERG SPEC FEATURE

de:

ENGINE SUPPORT.

======================================================================
19. FEATURE COMPATIBILITY MATRIX
======================================================================

Criar uma das peças mais importantes do Forge:

IcebergFeatureCompatibilityMatrix.

Eixos:

Iceberg Feature

× Iceberg Spec Version

× Iceberg Library Version

× Spark Version

× Glue Version

× Athena

× EMR

× PyIceberg

× S3 Tables

× Lake Formation.

Exemplo conceitual:

Deletion Vectors

Iceberg v3:
YES

Iceberg 1.11:
YES

Glue 6:
verify

Athena:
verify

Lake Formation:
verify

Nunca inferir:

Iceberg supports feature
→ therefore Athena supports feature.

======================================================================
20. FEATURE SUPPORT STATES
======================================================================

Estados:

SUPPORTED

UNSUPPORTED

PARTIAL

READ_ONLY

WRITE_ONLY

PREVIEW

UNKNOWN

CONFLICTING.

Cada cell deve possuir evidence.

======================================================================
21. ICEBERG VARIANT
======================================================================

Criar:

iceberg-variant

iceberg-variant-shredding

Cobrir:

schema

write

read

Spark representation

Parquet representation

predicate behavior

performance

evolution

engine compatibility.

Criar fixtures.

======================================================================
22. ICEBERG DELETION VECTORS
======================================================================

Criar:

iceberg-deletion-vectors.

Cobrir:

v3 semantics

Puffin storage

position deletes migration

reader behavior

writer behavior

maintenance

compaction interaction

engine compatibility

performance implications.

======================================================================
23. ROW LINEAGE
======================================================================

Criar:

iceberg-row-lineage.

Cobrir:

next-row-id

first-row-id

snapshot semantics

manifests

upgrade v2 → v3

engine support.

======================================================================
24. ICEBERG V2 → V3 UPGRADE
======================================================================

Criar:

forge iceberg assess-upgrade \
  --from 2 \
  --to 3

NÃO executar upgrade.

Avaliar:

current engine compatibility

consumers

Athena

Glue

EMR

Lake Formation

PyIceberg

writers

readers

maintenance.

Resultado:

SAFE

CONDITIONAL

BLOCKED

UNRESOLVED.

======================================================================
25. CONSUMER-AWARE MIGRATION
======================================================================

Antes de recomendar Iceberg v3:

identificar consumidores.

Exemplo:

Glue 6 writer

Athena reader

EMR reader

PyIceberg service

Lake Formation governance.

Se um consumidor não suportar feature:

BLOCK upgrade/use.

Integrar com:

consumer inventory existente.

======================================================================
26. CROSS-SERVICE CONSTRAINTS
======================================================================

Atualizar profundamente:

knowledge/cross-service-constraints.

Adicionar constraints:

Glue 6
Spark 4.1
Iceberg 1.11
Iceberg v3
Athena
Lake Formation
EMR
S3 Tables
Terraform.

Essa knowledge é crítica.

======================================================================
27. GLUE 6 + LAKE FORMATION
======================================================================

Não presumir que comportamento Glue 5.1
seja automaticamente equivalente em Glue 6.

Pesquisar:

FTA

FGAC

Spark-native permissions

DynamicFrame

GlueContext

DataFrame

DDL

DML

Iceberg writes

Iceberg reads

MERGE

DELETE

UPDATE

INSERT

schema evolution.

======================================================================
28. LAKE FORMATION OPERATION MATRIX
======================================================================

Criar matrix:

Operation
× Glue Version
× Iceberg Version
× FTA/FGAC
× Same/Cross Account.

Operations:

SELECT

INSERT

UPDATE

DELETE

MERGE

CREATE

ALTER

DROP

schema evolution

partition evolution.

Cada resultado:

SUPPORTED
UNSUPPORTED
PARTIAL
UNKNOWN

com source.

======================================================================
29. CROSS-ACCOUNT GLUE 6
======================================================================

Criar Golden Cases para:

Glue 6
→ cross-account Iceberg read.

Glue 6
→ cross-account Iceberg write.

Glue 6
→ local read / cross-account write.

Glue 6
→ cross-account read / local write.

Glue 6
→ cross-account read/write.

Validar:

RAM

Lake Formation

resource links

Catalog ID

IAM

S3

KMS

Data Location

region.

======================================================================
30. NÃO CONFUNDIR CONTROL PLANE E DATA PLANE
======================================================================

Permission analyzer deve distinguir:

Catalog permissions

Lake Formation permissions

IAM control-plane permissions

S3 data-plane

KMS

resource share.

Nunca diagnosticar:

SELECT granted

como prova de que:

write to S3 works.

======================================================================
31. GLUE 6 MIGRATION HARNESS
======================================================================

Criar novo Harness Contract:

Glue6MigrationHarness.

Inputs:

source Glue version

target = 6.0

job script

job configuration

optional:

requirements

JARs

Terraform

catalog metadata

Lake Formation topology

consumer inventory

event log

Spark plan.

======================================================================
32. HARNESS PIPELINE
======================================================================

Glue6MigrationHarness:

INTAKE

→ CLASSIFY JOB

→ COLLECT FACTS

→ DETECT SOURCE RUNTIME

→ TARGET RUNTIME

→ PYTHON COMPATIBILITY

→ JAVA COMPATIBILITY

→ SCALA COMPATIBILITY

→ SPARK COMPATIBILITY

→ DEPENDENCY COMPATIBILITY

→ S3 FILESYSTEM

→ PARQUET

→ ICEBERG

→ ICEBERG V3

→ LAKE FORMATION

→ CROSS ACCOUNT

→ IAM/KMS

→ NETWORK

→ CONSUMER COMPATIBILITY

→ DATA REGRESSION PLAN

→ PERFORMANCE PLAN

→ COST PLAN

→ SECURITY GATE

→ MIGRATION PLAN

→ ROLLBACK PLAN

→ EVALUATION

→ READINESS SCORE.

======================================================================
33. TOKEN ECONOMY IN GLUE6 HARNESS
======================================================================

Não chamar todos especialistas.

Classificação deve ativar capacidades somente quando necessário.

Exemplo:

simple Parquet job

NÃO carregar:

Iceberg

Lake Formation

Kafka

Neptune.

Iceberg job:

carregar Iceberg.

Cross-account:

carregar Lake Formation/cross-account.

Custom JAR:

carregar Java/Scala compatibility.

======================================================================
34. ROUTING EXAMPLE
======================================================================

Job:

Glue 4

reads cross-account Iceberg

MERGE into local Iceberg

custom Python modules

No JAR.

Router:

glue.migration

spark.compatibility

python.compatibility

iceberg.read

iceberg.write

lakeformation.cross_account.

NOT:

java.compatibility

scala.binary

terraform

unless evidence requires them.

======================================================================
35. EARLY EXIT
======================================================================

Se deterministic analyzer encontrar:

custom JAR compiled for incompatible Scala ABI

migration assessment já pode registrar:

BLOCKING FINDING.

Não precisa chamar cinco Agents
para confirmar fato determinístico.

======================================================================
36. MIGRATION READINESS MODEL
======================================================================

Criar:

GlueMigrationAssessment.

Campos:

source

target

runtime

job_type

features

dependencies

compatibility

breaking_changes

blocking_changes

required_changes

recommended_changes

data_risk

performance_risk

security_risk

operational_risk

cost_impact

consumer_risk

tests

rollback

unresolved

score

recommendation.

Recommendation:

GO

CONDITIONAL_GO

NO_GO

INSUFFICIENT_EVIDENCE.

======================================================================
37. NÃO USAR SCORE PARA ESCONDER BLOCKER
======================================================================

Score 95/100 + critical incompatibility

deve resultar:

NO_GO.

Critical blockers vencem score.

======================================================================
38. GLUE 5.1 → 6.0 GOLDEN SUITE
======================================================================

Criar:

simple-pyspark

partitioned-parquet

iceberg-read

iceberg-write

iceberg-merge

lakeformation-fta

lakeformation-fgac

cross-account-iceberg-read

cross-account-iceberg-write

custom-python

custom-jar

structured-streaming

jdbc

vpc.

======================================================================
39. GLUE 4 → 6 GOLDEN SUITE
======================================================================

Cobrir salto maior.

Especial atenção:

Spark 3.3 → 4.1

Python

Java 8 → target

Scala

Iceberg 1.0 → 1.11

EMRFS/S3A evolution

Lake Formation changes

logging

connectors

JDBC drivers.

======================================================================
40. MULTI-HOP KNOWLEDGE
======================================================================

4 → 6 analysis pode compor:

4 → 5

5 → 5.1

5.1 → 6

mas final report deve deduplicar findings.

Não mostrar ao usuário:

same issue x3.

======================================================================
41. MIGRATION CHANGE GRAPH
======================================================================

Criar representation:

RuntimeChangeGraph.

Node examples:

Spark
Python
Java
Scala
Iceberg
S3 filesystem
connector.

Edges:

from_version
to_version
breaking
source
severity.

Permitir query:

"What changes between Glue 4 and 6?"

sem LLM.

======================================================================
42. DETERMINISTIC KNOWLEDGE
======================================================================

Transformar mudanças verificáveis em rules.

Exemplos:

Scala ABI change

Spark major upgrade

Iceberg library change

Java major change

S3 connector change

Python major/minor change.

Não gastar LLM para fatos catalogáveis.

======================================================================
43. RULE CATALOG
======================================================================

Adicionar novas áreas quando arquitetura existente permitir:

SF-GLUE6

SF-SPARK4

SF-ICE-V3

ou integrar a categorias existentes.

Toda rule:

rule_id

description

runtime_scope

requires_facts

condition

severity

explanation

source

source_date

last_verified.

======================================================================
44. FRESHNESS
======================================================================

Como Glue 6 acabou de ser lançado:

knowledge TTL curto inicialmente.

Sugestão:

Glue 6 runtime:
30 dias

Glue 6 migration:
30 dias

Glue 6 + Lake Formation:
30 dias

Iceberg spec:
90-180 dias

fundamental Spark semantics:
longer.

Configurar.

Não hardcode sem configuração.

======================================================================
45. EVIDENCE CONFLICT ENGINE
======================================================================

Criar capacidade real de detectar:

source A != source B.

Exemplo atual:

Python runtime Glue 6.

Output:

CONFLICTING SOURCES.

Ranking de autoridade pode ajudar,
mas não apagar conflito.

======================================================================
46. SOURCE QUALITY
======================================================================

Classificar:

OFFICIAL_TECHNICAL_DOC

OFFICIAL_RELEASE_DOC

OFFICIAL_BLOG

UPSTREAM_SPEC

UPSTREAM_RELEASE

PROVIDER_DOC

COMMUNITY.

Para runtime:

technical docs/spec > marketing announcement,
quando atualizadas.

======================================================================
47. APACHE ICEBERG 1.11 REST CATALOG
======================================================================

Criar knowledge para:

remote scan planning

scan planning mode

incremental scans

metadata tables

dependency references

REST idempotency/reliability

credential refresh

caching.

Avaliar oportunidade de suporte no Forge.

======================================================================
48. REMOTE SCAN PLANNING
======================================================================

Adicionar skill:

iceberg-remote-scan-planning.

Cobrir:

driver memory

manifest planning

server-side planning

streaming

metadata tables

compatibility.

Não recomendar se catalog não suportar.

======================================================================
49. ICEBERG UNIQUE TABLE LOCATIONS
======================================================================

Adicionar rule/skill.

Avaliar risco:

multiple tables sharing locations

rename/recreate

orphan-file cleanup.

Integrar com:

Iceberg Doctor.

======================================================================
50. ICEBERG DOCTOR V2
======================================================================

Expandir:

forge iceberg doctor.

Novo output:

spec_version

library_version

runtime

feature_usage

consumer_support

v3_readiness

DV status

row lineage status

Variant usage

engine compatibility

migration recommendations.

======================================================================
51. COST ENGINE
======================================================================

AWS anuncia redução de preço Glue 6.

NÃO simplesmente codificar "-30%".

Pricing varia e pode mudar.

Atualizar:

pricing knowledge

retrieved_at

region

worker type

runtime.

Comparar:

Glue 5.1

versus:

Glue 6

com pricing oficial atual.

======================================================================
52. PERFORMANCE BENCHMARK
======================================================================

Não afirmar:

Glue 6 is 30% faster.

Preço 30% menor NÃO significa
performance 30% maior.

Benchmark performance separadamente.

Criar:

forge benchmark glue-runtime

Compare:

duration

DPUSeconds

shuffle

spill

GC

rows

bytes

cost.

======================================================================
53. MIGRATION PERFORMANCE HARNESS
======================================================================

Quando before/after runs disponíveis:

Glue 5.1 run

vs

Glue 6 run

Compare:

correctness first

then:

duration

DPU seconds

cost

shuffle

spill

GC

executors

skew.

======================================================================
54. DATA CORRECTNESS
======================================================================

Nenhuma melhoria de performance compensa
alteração não autorizada no resultado.

Regression:

row count

schema

nullability

decimals

timestamps

partitions

aggregates

duplicates

keys

business metrics

sample hashes.

======================================================================
55. REAL-TIME MODE
======================================================================

Criar domain:

glue-6-realtime-mode.

Investigar:

supported operations

limitations

stateless requirement

sources/sinks

checkpoint behavior

latency

fault tolerance

cost

difference from normal Structured Streaming.

Não recomendar por marketing.

Criar decision guide:

normal Spark streaming

versus

Glue real-time mode.

======================================================================
56. DECLARATIVE PIPELINES
======================================================================

Criar:

spark-declarative-pipelines

glue-declarative-pipelines.

Avaliar:

use cases

limitations

migration path

testing

observability

orchestration implications.

Não transformar jobs existentes automaticamente.

======================================================================
57. ARROW-NATIVE UDF/UDTF
======================================================================

Criar:

glue6-arrow-udf

spark4-arrow-udf

spark4-udtf.

Avaliar:

serialization

data types

compatibility

fallback

performance.

Analyzer pode detectar UDF candidates.

Mas:

recommendation != automatic rewrite.

======================================================================
58. VARIANT USE CASE ADVISOR
======================================================================

Criar:

forge iceberg recommend-variant.

Input:

semi-structured JSON/log/event workload.

Avaliar:

schema volatility

consumer compatibility

query patterns

engine support

storage

existing JSON/string approach.

Output:

USE_VARIANT

DO_NOT_USE

CONDITIONAL

UNRESOLVED.

======================================================================
59. GEOSPATIAL TYPES
======================================================================

Adicionar knowledge:

geometry

geography.

Cobrir apenas se uso for relevante.

Não carregar em tasks comuns.

======================================================================
60. NANOSECOND TIMESTAMPS
======================================================================

Adicionar compatibility rule.

Especial cuidado:

timestamp precision changes

Parquet

Spark

Athena

downstream systems.

Criar regression fixture.

======================================================================
61. TERRAFORM
======================================================================

Expandir:

sf-terraform-aws-specialist.

Criar:

terraform-glue6

terraform-glue-version-migration

terraform-glue-runtime-review.

Não assumir provider support.

Verificar provider atual.

Testar:

aws_glue_job

glue_version = "6.0"

somente de forma offline/static
ou provider schema quando possível.

======================================================================
62. TERRAFORM PLAN RULE
======================================================================

Se plan altera:

GlueVersion:

4.0 → 6.0

isso NÃO deve aparecer como:

"simple configuration update."

Harness deve ativar:

Glue Migration Assessment.

======================================================================
63. TERRAFORM CHANGE CORRELATION
======================================================================

Correlacionar:

Terraform diff

+

job source

+

dependencies

+

runtime matrix.

Isso é uma funcionalidade forte do Spark Forge.

======================================================================
64. AUTOMATIC MIGRATION DETECTION
======================================================================

Se analyze terraform detectar:

glue_version changed

criar finding:

RUNTIME_MIGRATION_DETECTED.

Sugerir:

forge migrate glue.

======================================================================
65. AWS GLUE SPARK UPGRADE AGENT
======================================================================

AWS fornece capacidade generativa de upgrade.

Criar knowledge sobre:

Spark Upgrade Agent / generative upgrade capability.

O Spark Forge NÃO deve duplicar cegamente esse produto.

Em vez disso:

Spark Forge pode:

prepare

independently analyze

validate

compare

audit results

post-migration verify.

Criar skill:

review-aws-glue-upgrade-agent-result.

======================================================================
66. UPGRADE AGENT REVIEW
======================================================================

Se usuário fornecer output do AWS upgrade agent:

extrair changes

classificar

comparar com Spark Forge findings

detectar missed risks

executar regression plan.

Não confiar automaticamente no output gerado por IA.

======================================================================
67. SECURITY
======================================================================

Glue 6 migration deve revisar:

IAM

Lake Formation

KMS

S3

VPC

security groups

Secrets Manager

JDBC credentials

cross-account roles.

Sem AWS mutation.

======================================================================
68. OFFLINE MODE
======================================================================

Após knowledge sync:

toda análise de runtime deve continuar funcionando offline.

Glue 6 runtime knowledge deve ser incluída no:

offline manifest.

Atualizar SHA-256.

Testar wheel instalado fora do repo.

======================================================================
69. PACKAGE PARITY
======================================================================

A knowledge Glue 6 deve funcionar:

repo checkout

pip wheel

MCP

Claude Plugin

offline mode.

Adicionar ao artifact parity test.

======================================================================
70. MCP
======================================================================

Não criar dezenas de tools.

Preferir expandir:

runtime_detect

migration_audit

knowledge_lookup

iceberg_doctor.

Adicionar apenas se necessário:

glue_target_version_recommend

iceberg_feature_compatibility.

======================================================================
71. TOKEN ECONOMY
======================================================================

Glue 6 não pode resultar em context explosion.

Exemplo:

questão sobre:

"Java compatibility Glue 5.1→6"

não carregar:

Variant

Lake Formation

Kafka

Terraform

Neptune.

Usar Capability Registry.

======================================================================
72. SKILL PROGRESSIVE DISCLOSURE
======================================================================

Skills Glue 6:

SKILL.md curto.

Detalhes em:

references/runtime.md

references/spark4.md

references/iceberg-v3.md

references/migration.md

references/examples.md.

Claude carrega apenas referência necessária.

======================================================================
73. KNOWLEDGE DEDUPLICATION
======================================================================

Não duplicar:

Spark 4 knowledge

em:

Glue 6 skill

Iceberg skill

migration skill.

Referenciar knowledge canônica.

======================================================================
74. HARNESS CAPABILITIES
======================================================================

Adicionar:

aws.glue.runtime.6

aws.glue.migration.to6

spark.runtime.4

spark.migration.3to4

iceberg.library.1_11

iceberg.spec.v3

iceberg.feature.variant

iceberg.feature.dv

iceberg.feature.row_lineage

iceberg.compatibility

lakeformation.glue6

terraform.glue6.

======================================================================
75. ROUTING TESTS
======================================================================

Testar que:

Glue 6 simple Parquet

NÃO ativa:

Iceberg v3 specialist.

Glue 6 Iceberg v2

NÃO carrega Variant knowledge
sem necessidade.

Glue 6 Variant

ativa:

iceberg.variant.

Cross-account:

ativa LF.

Custom JAR:

ativa Scala/Java.

======================================================================
76. EVAL HARNESS
======================================================================

Criar:

evals/glue6/

Capability tests:

runtime facts

migration detection

Spark compatibility

Iceberg v3.

Regression tests:

existing Glue 4/5.1 behavior
must continue working.

======================================================================
77. HOLDOUT
======================================================================

Criar scenarios não expostos às Skills.

Exemplos:

mixed Iceberg/Parquet

indirect Spark SQL

custom config

multiple consumers

ambiguous dependencies.

======================================================================
78. CONFLICTING-SOURCE GOLDEN
======================================================================

Obrigatório.

Given:

two official sources disagree on runtime field.

Then:

status = CONFLICTING

not:

pick one.

Essa é uma capacidade essencial
para knowledge quality.

======================================================================
79. ERROR KNOWLEDGE
======================================================================

Adicionar:

knowledge/errors/glue6

knowledge/errors/spark4

knowledge/errors/iceberg-v3

à medida que evidência real/oficial surgir.

Não inventar erros hipotéticos como fatos conhecidos.

Podem existir fixtures hipotéticas claramente marcadas.

======================================================================
80. DOCS
======================================================================

Criar:

docs/aws/glue/6.0/

runtime.md

migration-from-5.1.md

migration-from-5.0.md

migration-from-4.0.md

spark4.md

iceberg-1.11.md

iceberg-v3.md

lakeformation.md

terraform.md

testing.md

known-unknowns.md.

======================================================================
81. MIGRATION DECISION DOCUMENT
======================================================================

Criar:

docs/aws/glue/6.0/decision-guide.md.

Responder:

Should I migrate?

Benefits

Risks

Prerequisites

When to wait

5.1 vs 6.0

testing

rollback.

======================================================================
82. README
======================================================================

Atualizar README de forma concisa.

Não transformar README em documentação Glue 6.

Adicionar somente:

Glue 6 supported/analyzed

e links para docs.

======================================================================
83. ADR
======================================================================

Criar ADR:

Support AWS Glue 6.0 / Spark 4.1 / Iceberg v3.

Explicar:

why now

architectural impact

knowledge strategy

compatibility model

backward compatibility

risks.

======================================================================
84. CI
======================================================================

Adicionar gates:

Glue6 knowledge validation

runtime matrix validation

Iceberg compatibility matrix

source freshness metadata

golden cases

package parity.

Não chamar AWS real no CI.

======================================================================
85. IMPLEMENTAÇÃO EM WAVES
======================================================================

WAVE 0

baseline
research
official sources
source conflict audit.

WAVE 1

runtime knowledge

Spark 4

Iceberg 1.11

Iceberg v3.

WAVE 2

rules

capabilities

routing.

WAVE 3

migration analyzers

dependency analyzer

JAR analyzer.

WAVE 4

Glue6 Migration Harness.

WAVE 5

Lake Formation/cross-account.

WAVE 6

Terraform integration.

WAVE 7

goldens/holdout.

WAVE 8

token benchmark.

WAVE 9

docs/cleanup.

======================================================================
86. DO NOT STOP AT RESEARCH
======================================================================

A tarefa NÃO termina quando você descobrir:

Spark 4.1
Iceberg 1.11
etc.

Depois da pesquisa:

IMPLEMENTE.

======================================================================
87. DO NOT OVERENGINEER
======================================================================

Não criar:

new database server

vector database

workflow platform

large framework

se catálogo YAML + Python atual resolver.

Preservar filosofia lightweight.

======================================================================
88. NÃO QUEBRAR PYTHON SUPPORTED VERSIONS DO FORGE
======================================================================

Glue runtime Python version

NÃO significa:

Spark Forge package itself must require same Python.

Não elevar:

requires-python

sem justificativa.

O Forge analisa runtimes remotos.

Core deve preservar compatibilidade atual
quando possível.

======================================================================
89. SOURCE VERSION != PROJECT VERSION
======================================================================

Não misturar:

Python version used by Glue job

com:

Python required to run Spark Forge.

Mesma regra para:

Java

Scala

Spark.

======================================================================
90. MIGRATION AUTOFIX
======================================================================

Criar autofix apenas quando:

change deterministic

low risk

testable

reversible.

Exemplos:

config rename known

deprecated syntax with deterministic replacement.

Não autofix automaticamente:

business logic

complex SQL semantics

Iceberg table upgrade

Lake Formation security

cross-account policies.

======================================================================
91. PATCH GENERATION
======================================================================

Migration Harness pode produzir:

MigrationPatchProposal.

Campos:

file

line/range

before

after

reason

source

risk

test_required.

Não aplicar HIGH risk automaticamente.

======================================================================
92. TEST GENERATION
======================================================================

Para cada migration finding:

gerar teste recomendado.

Exemplo:

timestamp behavior changed

→ timestamp regression test.

Schema inference risk

→ schema golden.

======================================================================
93. ROLLBACK
======================================================================

Toda migration assessment deve possuir rollback.

Exemplo:

retain Glue 5.1 job definition

version script

version Terraform

preserve output path strategy

avoid irreversible table format changes.

======================================================================
94. ICEBERG TABLE FORMAT UPGRADE SAFETY
======================================================================

Nunca atualizar v2 → v3 automaticamente.

Isso pode impactar consumidores.

Harness:

analyze

plan

validate

wait for approval.

======================================================================
95. DUAL-RUNTIME TEST STRATEGY
======================================================================

Quando possível gerar estratégia:

baseline runtime

candidate runtime

same input

isolated output

compare.

Nunca escrever candidate output
sobre production output.

======================================================================
96. CANARY
======================================================================

Migration recommendations podem incluir:

small partition

historical partition

sample dataset

isolated S3 prefix

temporary Iceberg table

shadow run.

Não executar sem autorização.

======================================================================
97. OPERATIONAL RISK
======================================================================

Classificar:

LOW

MEDIUM

HIGH

CRITICAL.

Glue 4→6 default initial migration risk:

HIGH

até analysis reduzir risco.

Glue 5.1→6:

não hardcode como LOW.

Avaliar workload.

======================================================================
98. COST VS PERFORMANCE
======================================================================

Separar:

runtime price

job duration

DPU usage

total execution cost.

Não confundir.

======================================================================
99. HARNESS OBSERVABILITY
======================================================================

Registrar:

which migration rules fired

which capabilities selected

which Skills loaded

which tools called

which Agents called

context size

estimated tokens

cache hits

evaluation results.

Isso permitirá provar economia.

======================================================================
100. TOKEN BENCHMARK
======================================================================

Comparar análise Glue migration:

BEFORE

agents + large prompt

AFTER

deterministic Harness.

Medir:

correctness

tokens

tools

agents

latency.

Meta:

mais ou mesma qualidade

menos tokens.

======================================================================
101. EXPECTED RESULT
======================================================================

Ao final Spark Forge deverá conseguir receber:

job.py

e opcionalmente:

terraform

requirements

JAR metadata

catalog dumps

Lake Formation topology

consumer inventory

e responder:

"This Glue 4.0 job can/cannot safely move to Glue 6.0."

Com:

evidence

runtime changes

Spark risks

Python risks

Java risks

Scala risks

Iceberg risks

Lake Formation risks

cross-account risks

consumer compatibility

data tests

performance tests

cost analysis

security analysis

migration patch

rollback.

======================================================================
102. DEFINITION OF DONE
======================================================================

Não considere completo até:

Glue6 runtime knowledge criada

source conflicts represented

Spark4 knowledge criada

Iceberg1.11 knowledge criada

Iceberg v3 knowledge criada

feature compatibility matrix criada

migration routes criadas

Glue4→6 supported

Glue5→6 supported

Glue5.1→6 supported

Migration Harness integrado

Lake Formation checks integrados

cross-account checks integrados

Terraform correlation integrada

goldens passando

holdouts criados

offline funcionando

wheel parity passando

MCP funcionando

existing tests não regressarem

token benchmark produzido

docs completas.

======================================================================
103. FINAL REPORT
======================================================================

Criar:

docs/vnext/GLUE6-IMPLEMENTATION-REPORT.md

Contendo:

EXECUTIVE SUMMARY

OFFICIAL SOURCES

SOURCE CONFLICTS

RUNTIME MATRIX

SPARK 4.1

PYTHON

JAVA

SCALA

ICEBERG 1.11

ICEBERG V3

VARIANT

DELETION VECTORS

ROW LINEAGE

GLUE 4→6

GLUE 5→6

GLUE 5.1→6

LAKE FORMATION

CROSS ACCOUNT

PARQUET

CUSTOM PYTHON

CUSTOM JARS

TERRAFORM

HARNESS

TOKEN ECONOMY

EVALS

GOLDENS

HOLDOUT

TEST RESULTS

KNOWN UNKNOWNS

RISKS

NEXT STEPS.

======================================================================
104. AUTONOMIA
======================================================================

Você pode:

pesquisar

criar

alterar

refatorar

testar

documentar

criar Skills

criar rules

criar tools

evoluir Agents

evoluir Harness

evoluir CLI

evoluir MCP

evoluir knowledge.

Você NÃO pode automaticamente:

alterar AWS production

executar Terraform apply

executar Terraform destroy

migrar Glue Job real

alterar Lake Formation real

alterar tabela Iceberg production

upgrade Iceberg v2→v3 real

deletar dados.

Essas operações requerem aprovação explícita.

======================================================================
105. COMEÇAR AGORA
======================================================================

Execute na seguinte ordem:

1. inspect current repository;

2. execute baseline tests;

3. research Glue 6 from official sources;

4. resolve or document Python source conflict;

5. research Spark 4.1;

6. research Iceberg 1.11 and v3;

7. create verified runtime matrix;

8. update cross-service constraints;

9. update Capability Registry;

10. implement deterministic migration rules;

11. implement Spark4 migration scan;

12. implement dependency/JAR compatibility;

13. evolve Glue Migration Harness;

14. create Glue5.1→6 golden suite;

15. create Glue4→6 golden suite;

16. implement Iceberg v3 compatibility matrix;

17. integrate Lake Formation/cross-account;

18. integrate Terraform migration detection;

19. execute regression suite;

20. execute token benchmark;

21. simplify anything that does not provide measurable value;

22. produce final report.

Do not stop at planning.

Do not invent facts.

Do not hide unresolved evidence.

Do not equate newest with best.

Do not call LLM when deterministic code is enough.

Implement.