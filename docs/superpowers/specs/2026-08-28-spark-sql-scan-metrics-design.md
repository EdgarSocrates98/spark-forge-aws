# SparkForge AWS — Métricas de scan por nó do plano, medidas no event log

**Data:** 2026-08-28
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §2 (Effective Workload), §3 (Multi-source
Workload Analyzer) e §4 (Scan Budget). **É documento de entrada LOCAL e não versionado
neste repositório** — a nota entra aqui porque um leitor de clone limpo procuraria o
arquivo e não o acharia. O que importa dele está reproduzido abaixo.
**Base:** o motor existente — artefato → facts → regras → findings — e o baseline de
histórico entregue por
[`2026-08-26-glue-run-history-collector-design.md`](2026-08-26-glue-run-history-collector-design.md).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: onde este documento entra

A spec do coletor de histórico decompôs o documento de origem em cinco subprojetos:

| # | Subprojeto | Estado |
|---|---|---|
| A | Correção de `SF-GLUE-001` | aberto |
| B | Coletor de histórico de runs | **entregue em 2026-08-28** |
| C | Effective Workload e Fingerprint | **este documento cobre o primeiro recorte** |
| D | Capacity e SLA optimizer | aberto, depende de C |
| E | FinOps | aberto, depende de D |

C é grande demais para uma spec só. Ele pede três coisas independentes: bytes por fonte,
o grafo de joins, e o classificador multidimensional que substitui `micro/small/medium`
por eixos separados. Este documento cobre **apenas a primeira**, e a razão da ordem está
em §1.2.

### 1.1 O princípio que motiva C

O documento de origem tem uma tese central: **o volume da entrada principal não determina
o trabalho físico do DAG**. Um job pode ter batch pequeno e varredura extrema, e o perfil
por número de registros de entrada classifica os dois como a mesma coisa.

Medir isso exige saber quanto cada fonte custou de verdade — bytes lidos, arquivos
abertos, partições tocadas. Sem esse número, `scan_amplification` e
`largest_source_scan_bytes` não têm de onde sair, e o fingerprint de C viraria estimativa
apresentada como medição.

### 1.2 O achado do repositório que este documento consome

**O event log carrega métrica por nó do plano, e o extrator não a lê.**
`sparkforge/facts/event_log.py` trata `SparkListenerTaskEnd`, `StageCompleted`,
`StageExecutorMetrics`, `ExecutorAdded/Removed`, `EnvironmentUpdate`, `LogStart`,
`ApplicationStart`. Não trata nenhum evento do namespace
`org.apache.spark.sql.execution.ui`. Os facts que ele emite são por **stage**
(`spark.stage.task_input` traz `total_bytes`, `p50_bytes`, `p95_bytes`, `max_bytes`), e
stage agrega todas as leituras que caem nele.

Do outro lado, `sparkforge/facts/spark_plan.py` emite `plan.file_scan` por nó de leitura,
com `relation`, `format`, `scan_api`, `pushed_filter_count`, `partition_filter_count` e
contagem de colunas — **e nenhum byte**, porque o artefato dele é texto de
`explain("formatted")`, que não carrega volume.

Existe portanto um número por stage e uma estrutura por nó, e nada que ligue os dois. O
que os liga já está no artefato de event log que o projeto coleta desde a Fase 1, e
ninguém lê.

### 1.3 O que o corpus de fixtures não exercita hoje

`fixtures/eventlog/` tem quatro cenários, e nenhum contém evento SQL. Medido em
2026-08-28 contando `"Event":"..."` distintos nos quatro `eventlog.jsonl`: dezesseis
tipos, todos de Task, Stage, Executor, Job, Environment, Application ou BlockManager.
O corpus atual não prova nada sobre a capacidade que este documento propõe, e é por isso
que §7 cria domínio de fixture próprio em vez de estender o existente.

---

## 2. Escopo

**Entra:**

- Extrator novo, `sparkforge/facts/sql_metrics.py`, que lê o **mesmo artefato de event
  log** com a ótica de "quanto cada fonte custou".
- Facts `spark.sql.scan`, `spark.sql.execution`, `spark.sql.unresolved`,
  `spark.sql.analyzed`.
- Mapa canônico de nomes de métrica em `knowledge/`, com fonte, data e as versões de
  Spark em que cada nome foi verificado.
- Superfície: `analyze sql-metrics` na CLI e a tool MCP correspondente.
- Domínio de fixture `fixtures/sql_metrics/` com módulo golden próprio.

**Não entra, e a razão de cada um:**

- **Métrica de shuffle e de join por nó.** O mesmo mecanismo as alcança, e emiti-las agora
  seria contrato grande antes de existir consumidor. Elas entram com o recorte de C que as
  consumir.
- **O objeto `WorkloadFingerprint`.** Ele é o mecanismo de julgamento com garantia
  declarada por eixo, e depende deste recorte estar pronto. Classificar antes de medir é
  o que este documento existe para não fazer.
- **Correlação com `plan.file_scan`.** Ver §3.2: o casamento entre duas árvores é escolha
  adiada de propósito, não esquecimento.
- **Regra nova no catálogo.** Nenhuma. Este documento é extração; julgar
  `scan_amplification` exige o fingerprint, que é o recorte seguinte.
- **Estimativa de bytes a partir de tamanho de arquivo.** Se a execução não publicou a
  métrica, a measure não sai. Estimar produziria número com aparência de medido, que é
  exatamente o defeito que §3.3 recusa.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Módulo novo, não crescimento do extrator de event log

`sparkforge/facts/event_log.py` tem 34 KB. Acrescentar o tratamento de eventos SQL nele
somaria um segundo vocabulário a um módulo que já tem o seu.

O precedente do repositório é o oposto de fundir: `data_quality` e `graph` leem o **mesmo
`.py`** que `pyspark_ast`, cada um com a sua ótica e o seu módulo. O `.md` do catálogo
registra que `analyze graph` "lê o mesmo `.py` pela terceira vez". A mesma forma vale
aqui — o artefato é um, as perguntas são duas.

**Alternativa recusada:** estender `event_log.py`. Reduziria uma passada sobre o arquivo
e custaria a fronteira: o extrator de stage passaria a depender do vocabulário de SQL para
compilar, e um defeito no mapa de acumuladores derrubaria a extração de stage junto.

### 3.2 A fonte é o próprio event log, não o plano colado

O `sparkPlanInfo` que vem dentro de `SparkListenerSQLExecutionStart` é a árvore **daquela
execução**, e os `accumulatorId` que ele declara são os mesmos que aparecem nos valores.
Um artefato responde tudo.

**Alternativa recusada:** emitir métrica por `node_id` e casar com `plan.file_scan` na
fusão. O artefato de `analyze plan` é texto colado por um humano, e nada garante que seja
da execução que produziu os números — pode ser de outro dia, de outro ambiente, de outro
volume de dados. Casar duas árvores diferentes introduz um erro que a fonte única não tem,
e o erro seria silencioso: os nós casariam, os bytes estariam errados.

A correlação continua **possível depois**, porque `spark.sql.scan` carrega `relation`. Ela
fica para quem tiver um consumidor que a justifique.

### 3.3 Measure ausente é ausência, nunca zero

Nem toda execução publica toda métrica. `FileSourceScanExec` publica um conjunto;
`BatchScan` da API v2 (Iceberg, Delta) publica outro; a lista muda entre versões de Spark.

Um fact `spark.sql.scan` carrega **apenas as measures que a execução publicou**. Métrica
não publicada não vira `0`, e a razão é a mesma que a entrega de histórico já registrou
para série vazia de CloudWatch: zero é um valor, ausência é um estado, e confundir os dois
faz "não medido" parecer "medido como nada". Uma regra que dividisse por um zero inventado
produziria amplificação infinita a partir de uma lacuna.

### 3.4 Nome de métrica desconhecido é lacuna declarada, não palpite

O mapa de nomes canônicos é lista fechada, versionada em `knowledge/`, com fonte e data.
Nome fora do mapa vira `spark.sql.unresolved` com razão `unknown_metric_name`, carregando
o nome cru e o `node_name` que o publicou.

**Alternativa recusada:** casar por substring (`"bytes"` no nome → bytes lidos). Casaria
`size of files read` corretamente e `bytes of shuffle write` erradamente, e o erro sairia
como medição. Nome de métrica do Spark não é constante universal; tratá-lo como constante
é o defeito que `knowledge/` existe para evitar.

### 3.5 AQE: a última árvore define identidade, e reatribuição é recusa

`SparkListenerSQLAdaptiveExecutionUpdate` posta uma árvore nova para a mesma execução,
com `accumulatorId` novos. A política é declarada, no molde do que `spark_plan.py` já faz
ao tratar `Final Plan` / `Initial Plan`:

- A **última** árvore postada para uma execução define a identidade dos nós, e o fact de
  execução declara `plan_source: final_aqe` quando houve reposta.
- Valores já acumulados continuam atribuídos ao nó que declarou aquele acumulador. Eles
  foram medidos sob aquele plano.
- Se o **mesmo** `accumulatorId` aparecer em dois nós diferentes, nenhum dos dois recebe o
  valor: sai `spark.sql.unresolved` com razão `accumulator_reassigned`. Escolher em
  silêncio atribuiria bytes ao nó errado, e o relatório ficaria plausível e falso.

### 3.6 Duas recusas de vazamento

`description` de execução SQL pode carregar literal de query, com nome de tabela ou valor
de dado. Passa por `sparkforge/facts/secrets.py::redact`, e `redacted: true` entra no
fact quando houve redação — a existência da redação é ela própria um dado.

`Location` do metadata do scan carrega caminho S3 completo, e **não entra no fact**. O que
entra é `relation`, que é identidade e não caminho. `plan.file_scan` já segue essa linha,
e a entrega de histórico recusou `ErrorMessage` pela mesma razão.

### 3.7 Streaming, uma passada, sem carregar o arquivo

`extract_event_log` consome uma linha por vez e o arquivo nunca é lido inteiro para a
memória. O extrator novo segue a mesma disciplina, e ela é mais apertada aqui: uma linha
de `SQLExecutionStart` carrega o `physicalPlanDescription` inteiro e pode ter megabytes
sozinha.

A passada monta o mapa `accumulatorId → (execution_id, node_id, métrica)` quando a árvore
chega, e acumula valores conforme os eventos passam. Acumulador que aparece em
`TaskEnd.Accumulables` e não está no mapa **não é erro** — é acumulador que não pertence a
nó de SQL. Mas é **contado**, e a contagem entra em `spark.sql.analyzed`: descartar em
silêncio faria "nada para atribuir" e "atribuição quebrada" terem a mesma aparência.

---

## 4. Modelo de facts

Puro e determinístico como os extratores irmãos: nunca aplica limiar, nunca atribui
severidade, nunca toca a rede.

### 4.1 `spark.sql.scan`

Um por nó de leitura, por execução.

```
subject   {execution_id, node_id}
attrs     {relation, format, scan_api, node_name}
measures  {bytes_read, files_read, rows_output, partitions_read}
```

Só as measures que a execução publicou (§3.3). `scan_api` distingue v1 de v2, no mesmo
vocabulário que `plan.file_scan` já usa.

### 4.2 `spark.sql.execution`

Um por `executionId`.

```
subject   {execution_id}
attrs     {plan_source: initial | final_aqe, description, redacted}
measures  {scan_nodes, nodes_total}
```

### 4.3 `spark.sql.unresolved`

Lacuna com nome, razão e — quando existe — o que a resolve. Razões previstas:
`unknown_metric_name`, `accumulator_reassigned`, `no_sql_events`, `malformed_event`,
`incomplete_execution`.

### 4.4 `spark.sql.analyzed`

Sentinela da varredura.

```
subject   {artifact}
measures  {executions, scan_nodes, unattributed_accumulators, malformed_lines}
```

`unattributed_accumulators` é o número de §3.7. Ele não é defeito; ele é o que separa
"não havia o que atribuir" de "a atribuição quebrou".

---

## 5. Superfície

### 5.1 CLI

```
sparkforge analyze sql-metrics --path <eventlog.jsonl> [--out F] [--kind K] [--limit N] [--cursor C]
```

Mesma forma de `analyze event-log`: página de facts, `--out` grava a lista completa.

### 5.2 MCP

`sparkforge_analyze_sql_metrics`, read-only local, mesmo `outputSchema` de página de facts
que as outras tools de análise usam.

**A entrega anterior abriu uma exceção que este documento não repete.** Os facts de
`glue.job_run.*` não couberam no enum fechado de `subject.type` de
`_ANALYZE_FACTS_SCHEMA`, e as duas tools novas ganharam `_ANALYZE_GLUE_FACTS_SCHEMA`, com
subject genérico. Aqui a decisão é a outra: o subject declara
`type: "sql_node"`, o valor entra no enum, e a tool reusa `_ANALYZE_FACTS_SCHEMA` como os
catorze extratores que já emitem `subject.type`. Um nó de plano **é** uma entidade
nomeável, ao contrário de uma tupla de capacidade agregada — a exceção anterior existiu
porque `distribution` e `outcome` falam de um grupo, não de uma coisa.

### 5.3 Nenhum artefato novo

O artefato é o event log, que `collect event-log` já grava e o manifesto já verifica.
Nenhum `kind` novo em `ARTIFACT_KINDS`, nenhuma chamada AWS nova.

---

## 6. Erros, cada um com o seu nome

| Situação | Saída |
|---|---|
| Arquivo não existe ou não abre | `spark.sql.unresolved`, razão `read_error`, nunca exceção — igual a `extract_event_log_path` |
| Linha com JSON inválido | `unresolved` razão `malformed_event`, com o número da linha; a passada continua |
| Nenhum evento SQL no log | `analyzed` com `executions: 0` e `unresolved` razão `no_sql_events`. Job RDD-only não é defeito |
| Execução sem evento de fim | measures parciais e `unresolved` razão `incomplete_execution` |
| Nome de métrica fora do mapa | `unresolved` razão `unknown_metric_name`, com o nome cru |
| `accumulatorId` em dois nós | `unresolved` razão `accumulator_reassigned`; nenhum dos dois recebe o valor |

---

## 7. Testes

### 7.1 Domínio de fixture próprio

`fixtures/sql_metrics/`, com `tests/test_fixtures_golden_sql_metrics.py`. Precedente:
`data_quality` e `graph` leem o mesmo `.py` que `pyspark_ast` e cada um ganhou domínio
próprio (`fixtures/dq`, `fixtures/graph`). É também o que satisfaz
`test_every_fixture_domain_has_a_golden_module`, que cobra um módulo
`tests/test_fixtures_*.py` declarando `FIXTURES = ROOT / "fixtures" / "<domínio>"` — sem
ele o corpus existe, parece cobertura, e `scripts/verify_wheel.py` nunca o executa contra
o pacote instalado.

Cenários, todos sintéticos, sem nome, número ou particularidade de ambiente real:

| Cenário | Prova |
|---|---|
| `scan_parquet_measured` | `FileSourceScanExec` com bytes e arquivos publicados |
| `scan_iceberg_batchscan` | `BatchScan`, conjunto de métricas diferente |
| `aqe_replans_the_scan` | árvore inicial e final, ids distintos, `plan_source: final_aqe` |
| `unknown_metric` | nome fora do mapa vira `unresolved`, não palpite |
| `no_sql_events` | log RDD-only: `executions: 0`, sem falso defeito |
| `truncated_log` | execução sem fim: `incomplete_execution` |

### 7.2 O teste que vale mais que os seis

**Nenhum `spark.sql.scan` carrega measure que a execução não publicou.**

É a garantia que separa medido de inferido, e é dela que depende a confiabilidade do
fingerprint de C. Escrito como propriedade sobre o corpus inteiro, não como asserção de
um cenário: cenário novo entra e a garantia continua cobrada.

---

## 8. Documentação

- `knowledge/spark/sql-metrics.md` mais o YAML legível por máquina com o mapa canônico, no
  molde de `knowledge/glue/observability.yaml` + `sparkforge/facts/cloudwatch_retention.py`
  que a entrega anterior estabeleceu. Fonte em `knowledge/sources.lock.json` com URL,
  `retrieved` e sha256, e o `.md` apontando para o YAML em vez de repetir a tabela.
- `README.md`: a linha do verbo novo na tabela de extração, e os números de extratores e
  de kinds **medidos**, nunca copiados.
- `docs/superpowers/STATUS.md`: a fase, o que ficou de fora e os desvios.

---

## 9. Critérios de aceite

1. `spark.sql.scan` sai com `bytes_read` medido para um scan que publicou a métrica, e
   **sem** a measure para um que não publicou.
2. Nome de métrica fora do mapa produz `unresolved` com o nome cru, e nenhum
   `spark.sql.scan` com valor inventado.
3. AQE com árvore reposta produz `plan_source: final_aqe`, e `accumulatorId` reatribuído
   produz `accumulator_reassigned` sem atribuir o valor a ninguém.
4. Event log sem evento SQL produz `executions: 0` e `no_sql_events`, e nenhum fact que
   sugira defeito no job.
5. `Location` não aparece em nenhum fact; `description` com literal sai redigida e
   marcada.
6. O extrator consome o arquivo em streaming: nenhum teste precisa carregar um event log
   inteiro em memória para passar.
7. Suíte completa verde, gate de números verde, gate de bundle offline verde, gate de
   órfão de tool verde — os quatro que a entrega anterior mediu como os que mordem.
