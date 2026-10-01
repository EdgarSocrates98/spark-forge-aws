# Migração de versão: Glue, EMR e o que muda no caminho

Este manual ajuda a responder "o que quebra se eu subir a versão?". Serve para
subir um job **Glue** (por exemplo do 4.0 para o 5.1, ou para o 6.0) e para
migrar entre releases do **EMR**. O SparkForge divide a migração em degraus
(uma versão por vez), julga cada degrau contra o catálogo de regras e diz o que
**não** conseguiu avaliar.

Todos os exemplos usam arquivos sintéticos de `fixtures/` e rodam sem acesso à
AWS.

## Receita rápida

```bash
# 1. O que muda de componente (Spark, Python, Iceberg...) entre as duas versões
sparkforge release diff --left-platform glue --left-release 4.0 \
                        --right-platform glue --right-release 5.1

# 2. Julgar a migração do seu job, degrau a degrau
mkdir -p /tmp/sf
sparkforge migrate glue fixtures/migration/emrfs_config/input --from 4.0 --to 5.0 \
  --out /tmp/sf/migracao.json

# 3. Conferir dependências Python e JARs contra o runtime alvo
sparkforge glue dependency-audit fixtures/migration/jar_binary/input --glue 6.0

# 4. Confirmar o que a versão alvo publica (e o que ela não publica)
sparkforge release describe --platform glue --release 5.1
```

Troque o caminho da fixture pelo diretório do seu job: código, `requirements*.txt`,
`.jar` e, se tiver, os `.tf` do job.

## Palavras que aparecem aqui

- **Runtime**: o conjunto de versões em que o job roda (Glue, Spark, Python,
  Iceberg).
- **Release**: uma versão publicada de uma plataforma, como Glue `5.1` ou EMR
  `7.7.0`.
- **Degrau**: um passo entre duas versões vizinhas. De 5.0 para 6.0 são dois
  degraus: 5.0 para 5.1, e 5.1 para 6.0.
- **EMR on EC2, EMR Serverless, EMR on EKS**: as três formas de rodar Spark no
  Amazon EMR (em máquinas, sem servidor ou em Kubernetes).
- **EMRFS e S3A**: dois "conectores" que o Spark usa para falar com o S3. O Glue
  trocou de um para o outro, e chaves de um são ignoradas pelo outro.
- **AQE (Adaptive Query Execution)**: um recurso do Spark que ajusta o plano
  durante a execução. Veio ligado por padrão a partir do Spark 3.2.
- **Format version do Iceberg**: a versão do formato da tabela (v2, v3). É
  diferente da versão da biblioteca Iceberg.

## Para que serve

- Listar o que muda de componente entre duas releases, com a fonte de cada
  número.
- Julgar o código do job em cada degrau da migração.
- Achar dependência Python ou JAR incompatível com o runtime alvo.
- Avaliar se dá para subir o format version de uma tabela Iceberg sem quebrar
  quem a consome.
- Revisar a configuração de um cluster ou application EMR.

## Quando usar e quando não usar

Use antes de trocar `glue_version` no Terraform, antes de trocar a release de
um cluster EMR, e quando um job migrado passou a falhar com
`NoSuchMethodError`, `ClassNotFoundException` ou erro de ANSI mode.

Não use `release diff` para saber se algo **quebra**: ele só compara versões de
componente. Quem julga é o `migrate`. E nenhum destes verbos mede desempenho: o
ganho de uma versão nova só se prova com benchmark
([Mudanças com prova](mudancas-com-prova.md)).

## Pré-requisitos

- SparkForge instalado ([Instalação](../02-instalacao.md)).
- O diretório do job, com código, `requirements*.txt` e `.jar`.
- Opcional, mas decisivo: os `.tf` do job e o inventário de consumidores em
  `.sparkforge/consumers.yaml`. Sem eles, alguns gates saem `BLOCKED`.

## Passo a passo

### 1. O que muda de componente: `release diff` e `release describe`

```bash
sparkforge release diff --left-platform glue --left-release 4.0 \
                        --right-platform glue --right-release 5.1
```

Trecho real da saída:

```json
  "axis": ["release"],
  "changed": [
    {"component": "iceberg", "from": "1.0.0", "to": "1.10.0"},
    {"component": "python", "from": "3.10", "to": "3.11"},
    {"component": "scala", "from": "2.12", "to": "2.12.18"},
    {"component": "spark", "from": "3.3.0", "to": "3.5.6"}
  ],
  "added": [],
  "removed": ["java"],
  "unchanged": [],
  "unresolved": {
    "compatibility_changes": "exige uma tabela de compatibilidade por release, ...",
    "component.delta": "`delta` nao e comparavel entre glue/4.0 e glue/5.1 -- ...",
    ...
```

`removed: ["java"]` não quer dizer que o Java sumiu do Glue 5.1. Quer dizer que
a fonte lida para o 5.1 não publica a versão do Java. Por isso cada componente
sem fonte aparece em `unresolved`, com o que destravaria.

Comparar **plataformas diferentes** também funciona, e o resultado avisa que
não dá para dizer qual das duas diferenças causou cada mudança:

```bash
sparkforge release diff --left-platform glue --left-release 5.0 \
                        --right-platform emr_ec2 --right-release 7.7.0
```

```json
  "axis": ["platform", "release"],
  "changed": [
    {"component": "iceberg", "from": "1.7.1", "to": "1.7.1-amzn-0"},
    {"component": "python", "from": "3.11", "to": "3.9"},
    {"component": "spark", "from": "3.5.4", "to": "3.5.3-amzn-1"}
  ],
  "unresolved": {
    "attribution": "as duas dimensoes variam ao mesmo tempo (platform E release), entao nenhuma linha de `changed` pode ser atribuida a uma delas isoladamente -- ...",
```

`release describe` mostra uma release só. Release que não existe na matriz é
recusada com a lista das conhecidas:

```bash
sparkforge release describe --platform glue --release 9.9
```

```text
release '9.9' (chave '9.9') fora da matriz de glue; conhecidas: 6.0, 5.1, 5.0, 4.0, 3.0
  Cada plataforma tem a sua matriz, e as fronteiras nao coincidem:
  uma release conhecida por uma pode nao existir na outra.
    sparkforge release describe --platform glue --release 6.0
```

As plataformas aceitas em `--platform` são `glue`, `emr_ec2`, `emr_serverless` e
`emr_eks`.

### 2. Julgar a migração: `migrate glue` e `migrate emr`

```bash
sparkforge migrate glue fixtures/migration/emrfs_config/input --from 4.0 --to 5.0
```

A saída é um JSON grande. As partes que importam (trecho real):

```json
{
  "platform": "glue",
  "source_runtime": "4.0",
  "target_runtime": "5.0",
  "steps": [["4.0", "5.0"]],
  "findings": [
    {
      "rule_id": "SF-MIG-002",
      "title": "Configuração exclusiva do EMRFS sobrevivendo em runtime S3A",
      "severity": "P2",
      "subject": {"type": "source_location", "file": "job.py", "line": 6, ...},
      "explanation": "A partir do Glue 5.0 o sistema de arquivos S3 é o S3A do Hadoop, não o EMRFS. ...",
      "proposed_change": ["Remover as chaves `fs.s3.*` exclusivas do EMRFS e substituir pelo equivalente S3A ..."],
      "rollback": ["Restaurar as chaves EMRFS; sem efeito no S3A -- documentar que elas são inertes nesse runtime."],
      ...
```

Num salto maior, o verbo divide em degraus e fecha com gates e uma
recomendação. Resumo real de
`migrate glue fixtures/migration/spark4_removed_api/input --from 5.0 --to 6.0`:

```text
steps           [['5.0', '5.1'], ['5.1', '6.0']]
findings        SF-SPARK4-002 P1 API de pandas-on-Spark removida na versão 4 ainda chamada no código
gates           compatibilidade: FAIL, lakeformation: BLOCKED, consumidor: BLOCKED,
                iam_kms: BLOCKED, rede: BLOCKED, cross_account: BLOCKED, dados: BLOCKED,
                performance: BLOCKED, custo: BLOCKED, canary: BLOCKED
recommendation  NO_GO
```

Como ler:

- **`steps`**: os degraus que o motor percorreu.
- **`gates`**: `PASS` e `FAIL` foram avaliados; **`BLOCKED`** quer dizer "faltou
  evidência para avaliar". Não é aprovação.
- **`missing_evidence`**: para cada gate bloqueado, o que falta. Exemplo real:
  `"consumidor": "nenhum \`env.consumer\` nos facts -- ... declare o inventario em \`.sparkforge/consumers.yaml\`"`.
- **`recommendation`**: nos exemplos aparecem `NO_GO` e `CONDITIONAL_GO`.
- **`coverage`**: quantas regras do catálogo o caminho alcançou, dito por escrito.
- **`component_diff`**: o `release diff` de cada degrau, já embutido.

Para EMR, o verbo é o mesmo, com a plataforma escolhida:

```bash
sparkforge migrate emr fixtures/migration/emrfs_config/input \
  --platform emr_ec2 --from 6.15.0 --to 7.7.0
```

Resumo real: 8 degraus (`6.15.0 -> 7.0.0 -> ... -> 7.7.0`), gate `compatibilidade:
PASS`, os outros `BLOCKED`, e `recommendation: CONDITIONAL_GO`.

Use `--out` para gravar o assessment completo em arquivo. Para Control-M, o
verbo é `migrate controlm` (veja [Control-M](control-m.md)).

### 3. Dependências: `glue dependency-audit`

```bash
sparkforge glue dependency-audit fixtures/migration/jar_binary/input --glue 6.0
```

Trecho real:

```json
  "runtime": {"glue": "6.0", "spark": "4.1.1", "python": "3.13", "iceberg": "1.11.0", ...},
  "dependencies": [
    {"kind": "mig.jar_binary", "name": "connector_2.12-1.4.0.jar",
     "attrs": {"scala": "2.12", "scala_minor": 12}}
  ],
  "findings": [
    {
      "rule_id": "SF-SPARK4-004",
      "title": "JAR compilado contra Scala anterior ao 2.13 no classpath de um runtime Spark 4",
      "severity": "P0",
      ...
```

O Spark 4 (Glue 6.0) usa Scala 2.13, e um JAR de Scala 2.12 falha em runtime. O
mesmo JAR auditado contra `--glue 5.0` não gera finding: Scala 2.12 é o certo no
Spark 3.5.

O verbo lê `requirements*.txt` e só registra dependência **pinada** com `==`. Na
fixture `fixtures/migration/python_dep/input`, `pandas==2.0.3` e
`pyarrow==14.0.1` viram fact; `boto3` sem versão não vira.

### 4. Tabelas Iceberg: `iceberg assess-upgrade`

O verbo avalia subir o format version da tabela contra **quem a consome**. Ele
lê o inventário em `<diretório>/.sparkforge/consumers.yaml`. Não executa nada.

Para testar, copie o inventário de uma fixture para uma pasta temporária:

```bash
mkdir -p /tmp/sf/job_iceberg/.sparkforge
cp fixtures/consumers/v3_with_athena_consumer/input/consumers.yaml /tmp/sf/job_iceberg/.sparkforge/
sparkforge iceberg assess-upgrade /tmp/sf/job_iceberg --from 2 --to 3
```

Trecho real:

```json
{
  "consumers": ["athena", "quicksight"],
  "target_spec_version": 3,
  "verdict": "BLOCKED",
  "cells": [
    {"feature": "default_values", "engine": "athena", "status": "UNKNOWN", ...},
    {"feature": "variant", "engine": "athena", "status": "UNSUPPORTED",
     "source": "https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html",
     "note": "Tabela com 'format-version'='3' nao e lida pelo Athena SQL: \"Cannot read unsupported version 3\". ..."},
    ...
```

A maioria das células sai `UNKNOWN`. Esse é o resultado honesto: nenhuma fonte
publicou a resposta, e o projeto não preenche por dedução.

### 5. A versão do runtime: `runtime detect`

```bash
sparkforge runtime detect --glue 3.0
```

```json
{
  "glue": "3.0",
  "spark": "3.1.1",
  "python": "3.7",
  "iceberg": "0.13.1",
  "detected_from": ["cli"],
  "divergences": []
}
```

Se duas fontes discordam, o verbo não escolhe em silêncio. Ele registra a
divergência:

```bash
sparkforge runtime detect --glue 5.0 --spark 3.3.0
```

```json
  "spark": "3.3.0",
  "divergences": [
    "spark: valores divergentes entre fontes (cli=3.3.0, cli:matrix=3.5.4)"
  ]
```

Com divergência, nenhum limiar é confiável ainda. Resolva a versão antes de
aplicar qualquer recomendação. Com `--facts`, as versões observadas pelos
extratores (Terraform, event log) entram como fonte própria.

### 6. Revisar o EMR: `analyze emr-cluster`, `emr-serverless` e `emr-eks`

Cada forma de EMR tem o seu dump e o seu verbo:

| Plataforma | Dump de entrada | Verbo |
|---|---|---|
| EMR on EC2 | `describe-cluster` e as listas que o completam | `analyze emr-cluster` |
| EMR Serverless | `get-application` | `analyze emr-serverless` |
| EMR on EKS | `describe-virtual-cluster` + `describe-job-run` no mesmo arquivo | `analyze emr-eks` |

```bash
sparkforge analyze emr-cluster --path fixtures/emr/auto_termination_idle_week/input \
  --out /tmp/sf/facts_emr.json
sparkforge judge --facts /tmp/sf/facts_emr.json
```

O `judge` tira a release do próprio dump (`"emr": "7.5.0"`,
`"detected_from": ["describe_cluster"]`) e acha:

```text
SF-EMR-009 P1 Janela de ociosidade da auto-terminação larga demais para terminar o cluster
           medido: {"release_major": 7, "release_minor": 5, "idle_timeout_seconds": 604800}
```

Os outros dois, com `--detail-level summary` (contagem real por kind):

```bash
sparkforge analyze emr-serverless --path fixtures/emr_serverless/preinit_sem_autostop/input --detail-level summary
# by_kind: emrs.analyzed 1, emrs.application 1, emrs.initial_capacity 2, emrs.monitoring 1

sparkforge analyze emr-eks --path fixtures/emr_eks/pod_template_declarado/input --detail-level summary
# by_kind: emrc.analyzed 1, emrc.configuration 3, emrc.job_run 1, emrc.monitoring 1,
#          emrc.pod_template.unresolved 2, emrc.spark_submit_parameters 1, emrc.virtual_cluster 1
```

`emrc.pod_template.unresolved` é uma recusa visível: o pod template não está no
dump do `emr-containers`, e o projeto diz que não o leu em vez de supor. O
`analyze emr-serverless` descreve o **padrão** da application, não o que um job
run executou.

## A versão muda o significado do número

A regra 18 do `CLAUDE.md` diz: **a versão muda o significado do número, não o
número.** O exemplo clássico é `spark.sql.shuffle.partitions`:

| Runtime | AQE | O que `shuffle.partitions = 200` quer dizer |
|---|---|---|
| Glue 3.0 (Spark 3.1.1) | desligado por padrão | 200 é o número **final** de partições |
| Glue 4.0 e 5.x (Spark 3.3 ou mais) | ligado por padrão | 200 é o **ponto de partida**, que o motor ainda junta |

Por isso "confie no AQE" é conselho errado para Glue 3.0. A fixture
`fixtures/runtime/pre_aqe_runtime` prova a regra `SF-ENV-004`, que dispara nesse
caso para impedir essa recomendação. Antes de copiar qualquer número de um job
para outro, rode `runtime detect` e confira em que versão ele vale. O
documento [Precisão de versão](../../precisao-de-versao.md) mostra as outras
três proibições do projeto sobre versão.

## Como ler o resultado

- **`unresolved` e `unresolved_detail`**: o componente que a fonte não publica,
  com a razão e o que destravaria. É o projeto dizendo o que não sabe (veja
  [Recusa nomeada](../01-conceitos.md#recusa-nomeada)).
- **`BLOCKED` num gate**: faltou evidência. Leia `missing_evidence` e forneça o
  artefato pedido (os `.tf` do job, o inventário de consumidores).
- **`divergences`**: fontes de versão discordando. Resolva antes de seguir.
- **`UNKNOWN`** no assessment de Iceberg: ninguém publicou. Não é "suportado".

## Erros comuns

- **Apontar `migrate glue` só para o `.py`.** Funciona, mas os gates de Lake
  Formation, IAM/KMS e rede ficam `BLOCKED`. Aponte para o diretório que também
  tem os `.tf`.
- **Ler `release diff` como veredito de compatibilidade.** Ele compara versões.
  Quem julga é o `migrate`.
- **Esquecer o `consumers.yaml`.** O gate `consumidor` e o `iceberg assess-upgrade`
  dependem dele.
- **Deixar chaves `fs.s3.*` do EMRFS no job depois de ir para o Glue 5.x.** O S3A
  as ignora sem erro (`SF-MIG-002`).
- **Pedir release inexistente.** O erro lista as conhecidas; use uma delas.

## Para ir além

- Agent [`sf-runtime-specialist`](../referencia/agents/sf-runtime-specialist.md):
  Glue, EMR, runtimes e compatibilidade entre versões numa migração.
- Agent [`emr-infra-reviewer`](../referencia/agents/emr-infra-reviewer.md):
  risco na infraestrutura do EMR (EC2, Serverless e EKS).
- Skills:
  [`migrate-glue-6`](../referencia/skills/migrate-glue-6.md),
  [`compare-releases`](../referencia/skills/compare-releases.md),
  [`spark4-compatibility`](../referencia/skills/spark4-compatibility.md),
  [`iceberg-v3-readiness`](../referencia/skills/iceberg-v3-readiness.md),
  [`review-emr-cluster`](../referencia/skills/review-emr-cluster.md),
  [`review-emr-eks`](../referencia/skills/review-emr-eks.md).
- Referência dos comandos: [`migrate`](../referencia/cli/migrate.md),
  [`release`](../referencia/cli/release.md), [`glue`](../referencia/cli/glue.md),
  [`iceberg`](../referencia/cli/iceberg.md), [`runtime`](../referencia/cli/runtime.md),
  [`analyze`](../referencia/cli/analyze.md).
- Tools MCP equivalentes:
  [`sparkforge_migration_assess`](../referencia/tools/sparkforge_migration_assess.md),
  [`sparkforge_release_describe`](../referencia/tools/sparkforge_release_describe.md),
  [`sparkforge_release_diff`](../referencia/tools/sparkforge_release_diff.md),
  [`sparkforge_glue_dependency_audit`](../referencia/tools/sparkforge_glue_dependency_audit.md),
  [`sparkforge_iceberg_assess_upgrade`](../referencia/tools/sparkforge_iceberg_assess_upgrade.md),
  [`sparkforge_runtime_detect`](../referencia/tools/sparkforge_runtime_detect.md).
- O que o projeto **ainda não cobre** numa migração de Glue está mapeado em
  [MIGRATIONS-GLUE-GAP](../../harness/MIGRATIONS-GLUE-GAP.md).

## Próximos passos

1. Acesso quebrou depois da migração? Veja [Lake Formation e acesso](lake-formation-e-acesso.md).
2. Precisa do dump do cluster ou da application? Veja [Coleta na AWS](coleta-na-aws.md).
3. Quer provar que a versão nova ficou igual ou melhor? Veja [Mudanças com prova](mudancas-com-prova.md).
