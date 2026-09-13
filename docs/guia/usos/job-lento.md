# Diagnosticar um job PySpark lento no Glue

Este guia mostra como achar **por que** um job do AWS Glue está lento, usando o SparkForge.
Todos os exemplos usam arquivos sintéticos da pasta `fixtures/` e foram rodados de verdade.

Os comandos rodam na raiz do repositório, no Git Bash. `sparkforge` é o comando instalado.
Se ele não for encontrado, troque por `python -m sparkforge.adapters.cli`. É o mesmo programa.

## Receita rápida

O caso mais comum: você tem o código do job, o plano físico e o event log. Estes cinco
passos extraem os dados dos três e devolvem os problemas em ordem de gravidade.

```bash
# 1. pasta temporária para os resultados (fora do repositório)
SAIDA=/tmp/sparkforge-guia; mkdir -p "$SAIDA"
# 2. o código
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --out "$SAIDA/facts_pyspark.json"
# 3. o plano físico
sparkforge analyze plan --path fixtures/plan/pruning_absent/input/plan.txt --out "$SAIDA/facts_plan.json"
# 4. o event log
sparkforge analyze event-log --path fixtures/eventlog/skewed_stage/input/eventlog.jsonl --out "$SAIDA/facts_eventlog.json"
# 5. causas em ordem, e o que ficou sem avaliar
sparkforge root-cause --facts "$SAIDA/facts_pyspark.json" --facts "$SAIDA/facts_plan.json" \
  --facts "$SAIDA/facts_eventlog.json" --glue 5.0 --detail-level summary
```

O passo 5 devolve nove candidatos. O primeiro é `SF-PQ-002`, "Partition pruning ausente no
plano físico", de severidade `P0`. As próximas seções explicam cada peça.

## Para que serve

- Descobrir o **gargalo dominante**, ou seja, o problema que mais pesa. O primeiro problema
  que aparece nem sempre é esse.
- Ligar o que o código faz ao que o Spark realmente executou.
- Receber cada problema com evidência, risco, validação e rollback. Rollback é o jeito de
  desfazer a mudança.

## Quando usar e quando não usar

Use quando o job termina, mas demora, ou quando ele estoura o tempo (timeout).

Não use este guia para:

- **custo e número de workers**: veja [custo-e-capacidade.md](custo-e-capacidade.md);
- **tabela Iceberg, arquivos pequenos ou Parquet**: veja [iceberg-e-parquet.md](iceberg-e-parquet.md);
- **consulta lenta no Athena**, e não no job: veja [athena-e-sql.md](athena-e-sql.md).

## A ordem da investigação

Estas são as regras 1 a 10 do `CLAUDE.md`, em linguagem simples:

1. **Saiba a versão primeiro.** Glue, Spark, Python e Iceberg mudam o que cada número significa.
2. **Não ajuste configuração só olhando o código.** Primeiro colete o plano físico e uma
   medida de base (baseline), que é um run "antes" para comparar.
3. **Ache o gargalo dominante.** Ele pode ser CPU, memória, GC, shuffle, skew, driver, S3,
   metadados, arquivos pequenos ou falta de capacidade. As definições estão logo abaixo.
4. **Reduza trabalho antes de pedir máquina.** Ler menos dado costuma resolver mais do que
   aumentar workers.
5. **Prefira funções nativas do Spark SQL** a UDFs em Python.
6. **Evite os atalhos perigosos.** `collect`, `toPandas`, `coalesce(1)`, `repartition`
   arbitrário e `cache` sem critério costumam piorar o job.
7. **Toda recomendação traz** evidência, efeito esperado (como hipótese), risco, validação e rollback.
8. **Preserve o resultado.** Confira contagens, schema, chaves e agregados antes e depois.
9. **Em Iceberg, diga qual camada.** Pode ser data files, delete files, manifests, snapshots
   ou metadata files (ver [iceberg-e-parquet.md](iceberg-e-parquet.md)).
10. **Nunca rode manutenção destrutiva** sem confirmar escopo e retenção.

Termos que aparecem daqui em diante:

- **Worker**: uma máquina do cluster do Glue. **DPU** é a unidade de capacidade que o Glue cobra.
- **Executor**: o processo do Spark que roda as tarefas dentro de um worker.
- **Stage**: uma etapa do job. **Task** é um pedaço do stage que roda em paralelo.
- **Partição**: um pedaço do dado. Cada task processa uma partição.
- **Shuffle**: redistribuição de dado entre executores. Acontece em `join`, `groupBy` e similares.
- **Skew** (desbalanceamento): poucas partições muito maiores que as outras. Uma task
  demora e o resto do cluster fica esperando.
- **Spill**: dado que não coube na memória e foi escrito em disco. É lento.
- **GC** (garbage collection): tempo que a JVM gasta limpando memória em vez de trabalhar.
- **AQE** (Adaptive Query Execution): o Spark reajusta o plano durante a execução.

Os termos do próprio SparkForge (fact, finding, recusa) estão em [01-conceitos.md](../01-conceitos.md).

## Pré-requisitos: o que coletar

| Artefato | O que é | Como obter |
|---|---|---|
| Código do job | Os arquivos `.py` | Já estão no seu repositório |
| Plano físico | O que o Spark decidiu executar | Rode `df.explain("formatted")` ou `EXPLAIN FORMATTED <consulta>` e salve o texto num arquivo |
| Event log | O registro de tudo que o Spark executou (é o que a Spark UI mostra) | `sparkforge collect event-log` (acessa AWS) |
| Métricas do CloudWatch | CPU, memória e outras métricas do run | `sparkforge collect cloudwatch` (acessa AWS) |
| Histórico de runs | Duração e DPU de cada execução | `sparkforge collect glue-job-runs` (acessa AWS) |

Os comandos `collect` acessam sua conta AWS. Por isso eles não foram rodados neste guia.
As flags abaixo foram conferidas no `--help`:

```bash
sparkforge collect event-log --repo . --job-run <id-do-run> --bucket <bucket> --prefix <prefixo> --now <ISO8601>
sparkforge collect cloudwatch --repo . --job-name <job> --job-run <id-do-run> --start <ISO8601> --end <ISO8601> --now <ISO8601>
sparkforge collect glue-job-runs --repo . --job-name <job> --now <ISO8601>
```

`--now` é a data e hora atual no formato ISO 8601, por exemplo `2026-09-13T10:00:00Z`.

## Passo a passo

### 1. Confirme a versão do runtime

```bash
sparkforge runtime detect --facts "$SAIDA/facts_eventlog.json" --glue 5.0
```

```json
{
  "glue": "5.0",
  "emr": "",
  "spark": "3.5.4",
  "python": "3.11",
  "iceberg": "1.7.1",
  "athena": "",
  "detected_from": ["cli", "event_log"],
  "divergences": []
}
```

- `detected_from` diz de onde veio cada versão. Aqui ela veio da flag `--glue` (`cli`) e do event log.
- `divergences` fica cheio quando duas fontes discordam. O SparkForge avisa, e não escolhe um
  lado em silêncio.

### 2. Extraia facts do código

```bash
sparkforge analyze pyspark --path fixtures/pyspark/python_udf/input --out "$SAIDA/facts_pyspark.json"
```

```json
{
  "total_count": 3,
  ...
  "by_kind": {
    "pyspark.function_def": 1,
    "pyspark.module_analyzed": 1,
    "pyspark.udf": 1
  },
  ...
```

O SparkForge **não executa** o seu código. Ele só lê o texto. Cada item é um **fact**, um fato
extraído com arquivo e linha.

### 3. Extraia facts do plano físico

```bash
sparkforge analyze plan --path fixtures/plan/pruning_absent/input/plan.txt --out "$SAIDA/facts_plan.json"
```

```json
  "by_kind": {
    "plan.analyzed": 1,
    "plan.aqe": 1,
    "plan.exchange": 1,
    "plan.file_scan": 1,
    "plan.join": 1
  },
  "unresolved": 0,
```

`plan.file_scan` é a leitura de uma tabela. É nele que o SparkForge confere se o filtro de
partição chegou até a leitura.

### 4. Extraia facts do event log

```bash
sparkforge analyze event-log --path fixtures/eventlog/skewed_stage/input/eventlog.jsonl --out "$SAIDA/facts_eventlog.json"
```

```json
  "by_kind": {
    "spark.cluster.cores": 1,
    "spark.conf_effective": 5,
    ...
    "spark.stage.shuffle": 2,
    "spark.stage.spill": 2,
    "spark.stage.task_duration": 2,
    "spark.unresolved": 1
  },
  "unresolved": 1,
  "unresolved_at": [
    { "file": "eventlog.jsonl", "line": 14, "reason": "malformed_json" }
  ],
```

`unresolved_at` mostra que a linha 14 do arquivo estava quebrada. O SparkForge não inventa o
que estaria nela: ele diz onde está a lacuna.

Duas leituras extras do mesmo tipo de arquivo:

```bash
# bytes e arquivos lidos por consulta SQL
sparkforge analyze sql-metrics --path fixtures/sql_metrics/scan_parquet_measured/input/eventlog.jsonl --detail-level summary
# métricas do CloudWatch já coletadas
sparkforge analyze cloudwatch --path fixtures/glue_job_run/correlated/cloudwatch/synthetic-job_jr_0001.json --detail-level summary
```

Trecho real do primeiro: `"kind": "spark.sql.scan", "measures": { "files_read": 3, "bytes_read": 47185920 }`.

### 5. Julgue os facts contra o catálogo de regras

```bash
sparkforge judge --facts "$SAIDA/facts_pyspark.json" --facts "$SAIDA/facts_plan.json" \
  --facts "$SAIDA/facts_eventlog.json" --glue 5.0 --out "$SAIDA/findings.json"
```

```json
{
  "total_count": 9,
  ...
  "by_severity": { "P0": 3, "P1": 3, "P2": 2, "P4": 1 },
  ...
  "plan": {
    "order": ["SF-PQ-002", "SF-UI-005", "SF-PY-001", "SF-UI-003", "SF-UI-004",
              "SF-UI-002", "SF-UI-001", "SF-UI-006", "SF-PLAN-004"],
    ...
    "unresolved": [
      {
        "question": "spark.unresolved: que medida fecha a lacuna do fact f_06f3ca?",
        "evidence_needed": ["spark.unresolved", "reason: malformed_json"]
      }
    ],
    "persisted": false,
    ...
  },
  "items": [
    {
      "rule_id": "SF-PQ-002",
      "title": "Partition pruning ausente no plano físico",
      "severity": "P0",
      "confidence": "high",
      "status": "confirmed",
      "subject": { "type": "plan_node", "file": "plan.txt", "line": 10,
                   "symbol": "(1) Scan parquet analytics.transacoes", ... },
      "evidence": ["f_553798"],
      "measured": { ..., "partition_filter_count": 0, "pushed_filter_count": 1 },
      "proposed_change": ["Mover o filtro para antes do join, verificando que aparece em PartitionFilters.", ...],
      "risks": ["Mover filtro para antes de outer join altera o resultado; verificar o tipo de join."],
      "validation": ["PartitionFilters preenchido no plano físico após a mudança.", ...],
      "rollback": ["Reverter o commit."],
      ...
```

Cada item é um **finding**, um achado. O item acima diz que a tabela é particionada, mas a
leitura não usa o filtro de partição: o job lê a tabela inteira. **Partition pruning** é pular
as partições que o filtro descarta.

`--facts` pode ser repetido, e isso importa. Algumas regras cruzam fontes diferentes e só
disparam com todas na mesma chamada.

### 6. Ordene as causas e veja o que ficou sem avaliar

```bash
sparkforge root-cause --facts "$SAIDA/facts_pyspark.json" --facts "$SAIDA/facts_plan.json" \
  --facts "$SAIDA/facts_eventlog.json" --glue 5.0 --detail-level summary
```

Resumo real dos candidatos:

```text
1 SF-PQ-002   P0  Partition pruning ausente no plano físico
2 SF-UI-001   P0  Skew de duração de task no stage
3 SF-UI-005   P0  Executor removido sem OOM registrado no log
4 SF-PY-001   P1  Python UDF em transformação expressável nativamente
5 SF-UI-003   P1  Spill em disco maior que o input do stage
...
```

E a parte que mostra o que **não** foi avaliado:

```json
  "missing_evidence": [
    { "source": "rule_not_evaluated", "rule_id": "SF-PQ-001", "area": "SF-PQ",
      "missing_kinds": ["s3.prefix_summary"],
      "emitted_by": { "s3.prefix_summary": "s3_listing" } },
    ...
  ],
  "refused": [
    { "what": "confidence_score", "why": "Nenhum experimento calibrou peso nenhum neste repositorio. ..." },
    ...
    { "what": "expected_gain", "why": "Exige o custo do run que não aconteceu (regra 13 do CLAUDE.md)." }
  ]
```

- `missing_evidence` separa "não há defeito" de "ninguém coletou". A regra `SF-PQ-001`
  (arquivos pequenos) ficou sem avaliar porque falta o fact `s3.prefix_summary`. Quem produz
  esse fact é o extrator `s3_listing` (`analyze s3-listing`).
- `refused` lista o que o SparkForge **se recusa** a inventar: nota de confiança, impacto
  medido em segurança e ganho esperado. Recusar é qualidade, porque ele diz o que não sabe.
- A ordem é por consequência declarada (severidade), e não por probabilidade.

### 7. Derive o valor de configuração que a medida sustenta

`tune` calcula `spark.sql.shuffle.partitions` a partir do shuffle **medido**:

```bash
sparkforge tune --facts fixtures/tuning/valor_atual_vem_do_codigo/input/facts.json
```

```json
{
  "runtime": { "glue_version": "", "spark_version": "3.5.4", "aqe_default": true },
  "properties": [
    {
      "key": "spark.sql.shuffle.partitions",
      "current": { "value": "800", "provenance": "code", "evidence": ["f_37daad", "f_0303dd"] },
      "derived": {
        "value": 10,
        "formula": "ceil(shuffle_write_bytes / target_partition_bytes)",
        "basis": { "shuffle_write_bytes": 671088640.0, "target_partition_bytes": 67108864.0,
                   "target_source": "spark_default" }
      },
      "safety": "REVIEW",
      "explanation": "Com AQE ligado por default nesta versao, este numero e o PISO de paralelismo inicial: ..."
    }
  ],
  "refused": [
    { "reason": "no_measured_basis", "property": "spark.executor.memoryOverhead", "detail": "..." },
    { "reason": "no_measured_basis", "property": "spark.sql.autoBroadcastJoinThreshold", "detail": "..." },
    ...
  ]
}
```

Os campos que importam:

- `derived.formula` e `derived.basis` mostram a conta inteira: 640 MiB de shuffle divididos
  por um alvo de 64 MiB por partição dá 10.
- `runtime.aqe_default` muda o sentido do número. Com AQE (Spark 3.2+, Glue 4.0 e 5.x), 10 é o
  **piso** inicial, e o Spark junta partições depois. Sem AQE (Glue 3.0), 10 é o número
  **final**. Compare com `fixtures/tuning/shuffle_medido_sem_aqe`, que tem a mesma conta e outra explicação.
- `current.provenance` diz **quem pediu** o valor de hoje, não quem venceu:

| Procedência | Significado | Fixture de exemplo |
|---|---|---|
| `code` | O código do job define o valor | `fixtures/tuning/valor_atual_vem_do_codigo` |
| `terraform` | A infraestrutura (Terraform) define o valor | `fixtures/tuning/valor_atual_vem_do_terraform` |
| `runtime_or_cluster` | Ninguém no repositório pediu; veio do runtime ou do cluster | — |
| `spark_default_explicit` | Alguém escreveu à mão o próprio valor padrão do Spark (não muda nada) | `fixtures/tuning/default_escrito_a_mao` |
| `unset` | Ninguém definiu | `fixtures/tuning/shuffle_medido_com_aqe` |

- `safety: REVIEW` quer dizer que uma pessoa precisa olhar antes de ir para produção.
- `refused` lista as propriedades sem base medida, com a medida que destravaria cada uma.
  Sem shuffle medido, até a proposta principal vira recusa: `no_shuffle_measured`
  (`fixtures/tuning/sem_shuffle_medido`).

`tune` nunca aplica a mudança. Ele só propõe.

## "Timeout" é quatro coisas

Quando o job estoura o tempo, a pergunta é **qual** tempo estourou. O SparkForge separa quatro
categorias (regra 15):

| Categoria | O que estourou |
|---|---|
| `wall_clock` | O relógio do Glue (o limite do job). É consequência, não causa. |
| `broadcast` | O envio de uma tabela pequena para todos os executores (broadcast) |
| `network` | Uma espera de rede entre processos do Spark |
| `heartbeat` | O sinal periódico de "estou vivo" que o executor manda ao driver |

O diagnóstico é derivado pelo `fuse`. Rode o `fuse` antes do `judge`:

```bash
sparkforge fuse --facts fixtures/timeout/timeout_com_spill_e_skew/input/facts.json --out "$SAIDA/facts_timeout.json"
sparkforge judge --facts "$SAIDA/facts_timeout.json" --glue 5.0
```

Trecho real do fact derivado e do achado:

```json
"kind": "spark.timeout.diagnosis",
"measures": { "skew_p95_over_p50": 11.4, "spill_over_input": 0.4, "executor_lost_count": 0.0 },
"attrs": { "category": "wall_clock", "basis": "glue_job_run_state",
           "evidence_text": "glue.job_run.state = TIMEOUT (timeout_min=60)", "also_seen": [] }
...
"rule_id": "SF-TIMEOUT-001",
"title": "Timeout com sintoma medido ao lado — aumentar o limite mascara a causa",
"severity": "P1",
```

- Leia `category` e `also_seen` (o que mais apareceu) antes de mexer em configuração.
- `SF-TIMEOUT-001` dispara porque há sintoma ao lado: skew com razão p95/p50 de 11,4 e spill.
  Aumentar o limite aqui só troca uma falha rápida por uma falha cara.
- Sem sintoma nenhum, a regra não dispara. Aí aumentar o limite pode ser a decisão certa.
- A relação entre duas propriedades é conferível: `heartbeatInterval >= network.timeout` é
  sempre errado (`SF-TIMEOUT-002`, regra 16). O valor isolado de cada uma não é.

Há fixtures para as outras categorias em `fixtures/timeout/` (`broadcast_estourado`,
`network_futures_timeout`, `heartbeat_perdido`).

## Utilização baixa não é capacidade sobrando

Workers ociosos parecem desperdício. Mas, com skew, eles estão ociosos **porque** uma task
segura o stage inteiro. Reduzir workers não resolve a causa (regra 17).

O catálogo tem um par de regras para isso:

- `SF-WASTE-001`: só quando worker ocioso, memória com folga, disco com folga e **sem** skew
  aparecem juntos. Aí a pergunta de capacidade tem base (ver [custo-e-capacidade.md](custo-e-capacidade.md)).
- `SF-WASTE-002`: utilização baixa **com** skew alto. Trate o skew primeiro.

Limite desta versão: as duas regras leem o fact `glue.utilization.summary`, e nenhum verbo da
CLI produz esse fact hoje. Rodar `judge` sobre `fixtures/waste/ocioso_por_skew/input/facts.json`
devolve zero achados. Até isso mudar, faça a leitura à mão: se `SF-UI-001` (skew) aparece no
`judge`, não conclua que há capacidade sobrando.

## Erros comuns

- **Usar a saída da tela em vez do `--out`.** A tela é paginada: `filters_applied.limit` vale
  50. O arquivo do `--out` tem tudo.
- **Julgar uma fonte de cada vez.** Passe todos os `--facts` na mesma chamada do `judge` e do
  `root-cause`.
- **Esquecer a versão.** Sem `--glue` (ou um event log), regras que dependem de versão ficam
  de fora.
- **Rodar `judge` direto sobre facts de timeout.** Sem o `fuse`, `SF-TIMEOUT-001` não aparece.
- **Pedir mais workers primeiro.** Com skew, spill ou pruning ausente, mais máquina não resolve.
- **Ler `refused` como erro.** É o SparkForge dizendo o que falta medir.

## Para ir além

- Agent coordenador: [spark-performance-architect](../referencia/agents/spark-performance-architect.md).
- Job com carga full e incremental, OOM depois de horas: [glue-incremental-performance-architect](../referencia/agents/glue-incremental-performance-architect.md).
- Skills focadas: [sparkforge-diagnose](../referencia/skills/sparkforge-diagnose.md),
  [analyze-spark-plan](../referencia/skills/analyze-spark-plan.md),
  [analyze-spark-ui](../referencia/skills/analyze-spark-ui.md),
  [diagnose-data-skew](../referencia/skills/diagnose-data-skew.md),
  [diagnose-oom](../referencia/skills/diagnose-oom.md),
  [tune-glue-job](../referencia/skills/tune-glue-job.md),
  [optimize-pyspark-code](../referencia/skills/optimize-pyspark-code.md),
  [benchmark-pyspark-job](../referencia/skills/benchmark-pyspark-job.md).
- Referência dos comandos: [analyze](../referencia/cli/analyze.md), [judge](../referencia/cli/judge.md),
  [root-cause](../referencia/cli/root-cause.md), [tune](../referencia/cli/tune.md),
  [fuse](../referencia/cli/fuse.md), [runtime](../referencia/cli/runtime.md),
  [collect](../referencia/cli/collect.md).
- As mesmas operações como tools MCP: [sparkforge_judge](../referencia/tools/sparkforge_judge.md),
  [sparkforge_root_cause](../referencia/tools/sparkforge_root_cause.md),
  [sparkforge_tune](../referencia/tools/sparkforge_tune.md).

## Próximos passos

1. Corrija o achado de maior severidade. Mude uma coisa por vez.
2. Antes de mudar, defina o que conferir no resultado com `sparkforge funcval plan` (veja a
   [referência do funcval](../referencia/cli/funcval.md)).
3. Rode o job de novo e compare os dois runs com `sparkforge benchmark` (veja a
   [referência do benchmark](../referencia/cli/benchmark.md)). Só escreva "melhorou X%" com essa medida.
4. Se a dúvida virar custo ou capacidade, siga para [custo-e-capacidade.md](custo-e-capacidade.md).
