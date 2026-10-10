# `sparkforge-aws` command reference

Generated from the real CLI parser by `doc_inventory.py` + `doc_reference.py`. Do not hand-edit generated sections — write between `keep:start`/`keep:end` markers. `por que`/`quando` lines come from the curated `command-rationale.json` — edit rationale there, never here. Status vocabulary: `available` unless marked otherwise.

Rationale coverage: **65/65** first-level groups curated in `command-rationale.json`.

## Groups

- [`agentops`](#agentops) — 6 command(s)
- [`agents`](#agents) — 3 command(s)
- [`analyze`](#analyze) — 51 command(s)
- [`arbitrate`](#arbitrate) — 1 command(s)
- [`architecture`](#architecture) — 2 command(s)
- [`autonomy`](#autonomy) — 2 command(s)
- [`benchmark`](#benchmark) — 1 command(s)
- [`blackboard`](#blackboard) — 3 command(s)
- [`budget`](#budget) — 2 command(s)
- [`capacity`](#capacity) — 1 command(s)
- [`case`](#case) — 4 command(s)
- [`change`](#change) — 4 command(s)
- [`code`](#code) — 14 command(s)
- [`collect`](#collect) — 20 command(s)
- [`context`](#context) — 5 command(s)
- [`controlm`](#controlm) — 2 command(s)
- [`debate`](#debate) — 5 command(s)
- [`decision`](#decision) — 7 command(s)
- [`decisions`](#decisions) — 3 command(s)
- [`detach`](#detach) — 1 command(s)
- [`distribution`](#distribution) — 5 command(s)
- [`doctor`](#doctor) — 2 command(s)
- [`dq-ai`](#dq-ai) — 2 command(s)
- [`economy`](#economy) — 3 command(s)
- [`finops`](#finops) — 1 command(s)
- [`funcval`](#funcval) — 3 command(s)
- [`fuse`](#fuse) — 1 command(s)
- [`gain`](#gain) — 1 command(s)
- [`glue`](#glue) — 2 command(s)
- [`graph`](#graph) — 4 command(s)
- [`handoff`](#handoff) — 1 command(s)
- [`iceberg`](#iceberg) — 2 command(s)
- [`install`](#install) — 2 command(s)
- [`integrate`](#integrate) — 1 command(s)
- [`journal`](#journal) — 2 command(s)
- [`judge`](#judge) — 1 command(s)
- [`knowledge`](#knowledge) — 3 command(s)
- [`lab`](#lab) — 17 command(s)
- [`lakeformation`](#lakeformation) — 4 command(s)
- [`mcp`](#mcp) — 2 command(s)
- [`migrate`](#migrate) — 4 command(s)
- [`next-step`](#next-step) — 1 command(s)
- [`pack`](#pack) — 3 command(s)
- [`playbook`](#playbook) — 1 command(s)
- [`policy`](#policy) — 4 command(s)
- [`proof`](#proof) — 1 command(s)
- [`receipt`](#receipt) — 3 command(s)
- [`release`](#release) — 3 command(s)
- [`repair`](#repair) — 1 command(s)
- [`report`](#report) — 4 command(s)
- [`resume`](#resume) — 1 command(s)
- [`root-cause`](#root-cause) — 1 command(s)
- [`rules`](#rules) — 2 command(s)
- [`runtime`](#runtime) — 2 command(s)
- [`scan`](#scan) — 1 command(s)
- [`sdd`](#sdd) — 4 command(s)
- [`simulate`](#simulate) — 1 command(s)
- [`status`](#status) — 1 command(s)
- [`telemetry`](#telemetry) — 2 command(s)
- [`tune`](#tune) — 1 command(s)
- [`uninstall`](#uninstall) — 1 command(s)
- [`update`](#update) — 1 command(s)
- [`validate`](#validate) — 1 command(s)
- [`workload`](#workload) — 1 command(s)
- [`workspace`](#workspace) — 5 command(s)

## agentops

### `agentops`

**para que:** Inspeciona runs locais, compara baseline e atribui desperdicio observado.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agentops baseline`

**para que:** Salva ou compara baseline local.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops baseline [help] <action> <run_id> <baseline_path> [repo] [db_path]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `action` | yes | — | — |
| `run_id` | yes | — | — |
| `baseline_path` | yes | — | — |
| `repo` | no | — | — |
| `db_path` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agentops compare`

**para que:** Compara dois runs locais.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops compare [help] <run_a> <run_b> [repo] [db_path]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_a` | yes | — | — |
| `run_b` | yes | — | — |
| `repo` | no | — | — |
| `db_path` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agentops critical-path`

**para que:** Maiores duracoes, retries e waiting medidos do run.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops critical-path [help] <run_id> [repo] [db_path]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_id` | yes | — | — |
| `repo` | no | — | — |
| `db_path` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agentops inspect`

**para que:** Inspeciona um run local.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops inspect [help] <run_id> [repo] [db_path]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_id` | yes | — | — |
| `repo` | no | — | — |
| `db_path` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agentops timeline`

**para que:** Linha do tempo do run, por lane de componente.

- **por que:** inspeciona runs locais e atribui desperdício observado contra baseline
- **quando usar:** medir o que uma execução agentica realmente custou — nunca estimativa

**Syntax**

```text
sparkforge-aws agentops timeline [help] <run_id> [repo] [db_path]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_id` | yes | — | — |
| `repo` | no | — | — |
| `db_path` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## agents

### `agents`

**para que:** Lista e inspeciona agentes do runtime agêntico.

- **por que:** lista e inspeciona agentes do runtime agêntico
- **quando usar:** ver o roster declarado antes de rotear trabalho

**Syntax**

```text
sparkforge-aws agents [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agents inspect`

**para que:** Inspeciona um agente.

- **por que:** lista e inspeciona agentes do runtime agêntico
- **quando usar:** ver o roster declarado antes de rotear trabalho

**Syntax**

```text
sparkforge-aws agents inspect [help] [repo] <id>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `id` | yes | — | ID do agente. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `agents list`

**para que:** Lista agentes disponíveis.

- **por que:** lista e inspeciona agentes do runtime agêntico
- **quando usar:** ver o roster declarado antes de rotear trabalho

**Syntax**

```text
sparkforge-aws agents list [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## analyze

### `analyze`

**para que:** Extrai facts deterministicos de codigo-fonte.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze airflow-dag`

**para que:** Extrai facts do arquivo .py de um DAG do Apache Airflow, lido por AST e NUNCA executado: um fact por operador instanciado, com classe, task_id, os argumentos literais que as regras julgam (job_name, wait_for_completion, deferrable, stop_job_run_on_kill, retries, execution_timeout), as dependencias declaradas, e a marca do que nao e literal.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze airflow-dag [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .py do DAG ou diretorio com eles (a pasta de DAGs). |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze athena-workgroup`

**para que:** Extrai facts de um dump JSON de workgroups do Athena.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze athena-workgroup [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps de workgroups. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze call-graph`

**para que:** Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze call-graph [help] <facts> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts gerado por `analyze pyspark --out`. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze catalog-schema`

**para que:** Extrai facts de um dump JSON do Glue Data Catalog.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze catalog-schema [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps do catalogo. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze cdc`

**para que:** Extrai facts offline de dumps CDC, Debezium ou AWS DMS.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze cdc [help] <path> <artifact> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON/JSONL. |
| `artifact` | yes | — | Vocabulário do dump: eventos CDC, Debezium ou AWS DMS. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze cloudwatch`

**para que:** Extrai facts de um artefato de metricas do CloudWatch ja coletado.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze cloudwatch [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON do CloudWatch. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze cloudwatch-logs`

**para que:** Extrai facts do LOG do run ja coletado do CloudWatch Logs.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze cloudwatch-logs [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON de `collect cloudwatch-logs`, ou o DIRETORIO deles. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze consumers`

**para que:** Extrai facts do inventario declarado de consumidores de tabela.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze consumers [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .yaml do inventario, ou diretorio com varios. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze controlm-jobs`

**para que:** Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, job com Type/Name/RunAs/Application, agendamento (When), dependencia por evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE versionado, nunca execucao. Com --version, cruza as capacidades observadas com a matriz do Automation API e diz quais a versao declarada nao tem.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze controlm-jobs [help] <path> [version] [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .json ou diretorio com definicoes Jobs-as-Code. |
| `version` | no | — | A versao do Control-M Automation API do ambiente ALVO (9.0.21.200--9.0.22.100). E DECLARACAO do operador: o JSON de Jobs-as-Code nao a carrega, e deduzi-la do conteudo seria adivinhar. Sem ela o cruzamento com a matriz nao acontece e a regra SF-CTM-001 fica pulada por `requires_facts`. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze data-observability`

**para que:** Avalia SLI/SLO, error budget, incidentes e dependências offline.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze data-observability [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON/YAML de observabilidade. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze data-quality`

**para que:** Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great Expectations e validacao artesanal): onde o check roda, se tem consequencia, e quantas passadas custa.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze data-quality [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .py ou diretorio com codigo PySpark. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze dbt-artifacts`

**para que:** Analisa manifest, catalog e run_results do dbt sem executar dbt.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze dbt-artifacts [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretório dbt ou manifest.json. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze dq-ai`

**para que:** Extrai facts de manifesto Glue DQ BASIC/ADVANCED sem carregar linhas.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze dq-ai [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Manifesto JSON/YAML de recomendacao. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze duckdb-microscope`

**para que:** Analisa bundle read-only de DuckDB/Parquet/Iceberg sem executar SQL.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze duckdb-microscope [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON/YAML do microscópio DuckDB. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze emr-cluster`

**para que:** Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os cinco dumps que o completam).

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze emr-cluster [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps de cluster EMR. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze emr-eks`

**para que:** Extrai facts de um dump JSON de execucao Amazon EMR on EKS (describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe neste dump.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze emr-eks [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps de execucao EMR on EKS. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze emr-serverless`

**para que:** Extrai facts de um dump JSON de application EMR Serverless (get-application). Descreve o PADRAO da application, nunca o que um job run executou -- StartJobRun sobrepoe.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze emr-serverless [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps de application. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze error-signatures`

**para que:** Casa knowledge/errors/ contra os facts do case. Derivacao pura.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze error-signatures [help] <facts> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts com a UNIAO do case -- `spark.exception` do event log E `cloudwatch.log_event` do log. Metade dos facts nao produz metade das respostas: produz ponto cego que nao aparece. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze event-driven`

**para que:** Extrai facts offline de EventBridge/Pipes, SQS e SNS.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze event-driven [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze event-log`

**para que:** Extrai facts de um Spark event log (.jsonl) ja coletado.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze event-log [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo de event log. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze flink`

**para que:** Extrai facts offline de dumps Apache Flink ou Managed Flink.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze flink [help] <path> <artifact> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON/JSONL. |
| `artifact` | yes | — | Vocabulário do dump: Flink upstream ou Managed Flink. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze forge-lab`

**para que:** Descreve topologia e cenários do Forge Lab sem executar Docker ou falhas.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze forge-lab [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo YAML/JSON da topologia Forge Lab. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze glue-job-runs`

**para que:** Extrai facts de historico do diretorio de artefatos de run Glue.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze glue-job-runs [help] <path> <job_name> [cloudwatch] [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | DIRETORIO de artefatos glue_job_run. |
| `job_name` | yes | — | — |
| `cloudwatch` | no | — | Diretorio de artefatos cloudwatch, para correlacionar por job_run_id. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze glue-resource-link`

**para que:** Extrai a topologia do catalogo ja coletada: link, alvo e nome.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze glue-resource-link [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON de `collect glue-resource-link`, ou o DIRETORIO deles. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze glue-streaming`

**para que:** Extrai facts offline de dumps AWS Glue Streaming/Real-Time Mode.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze glue-streaming [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON/JSONL. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze graph`

**para que:** Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: import e versao declarada, construcao do GraphFrame e persistencia dos dois DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige checkpoint sem que o modulo o configure.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze graph [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .py ou diretorio com codigo PySpark. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze iam-access`

**para que:** Extrai a DECISAO de IAM ja simulada, com a camada que decidiu.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze iam-access [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON de `collect iam-access`, ou o DIRETORIO deles. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze iceberg`

**para que:** Extrai facts de um dump JSON das metadata tables Iceberg.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze iceberg [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio com dumps das metadata tables. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze lakeformation-grants`

**para que:** Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings).

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze lakeformation-grants [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON de `collect lakeformation`, ou o DIRETORIO deles. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze lakehouse-catalog`

**para que:** Analisa topologia declarada de catalogs, engines, tabelas e bindings.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze lakehouse-catalog [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON/YAML da topologia de catalog. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze orchestration`

**para que:** Analisa mapa normalizado de Airflow, Dagster, Step Functions e Control-M.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze orchestration [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON/YAML do control plane. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze parquet-footer`

**para que:** Extrai facts do FOOTER do Parquet ja coletado.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze parquet-footer [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Artefato JSON de `collect parquet-footer`, ou o DIRETORIO deles. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze plan`

**para que:** Extrai facts do texto de um plano fisico (`df.explain("formatted")` / EXPLAIN FORMATTED).

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze plan [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo de texto com a saida de explain. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze platform-ecosystem`

**para que:** Analisa serving, ingestion, AI Data Engineering e radar opcional.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze platform-ecosystem [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON/YAML do inventário. |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze platform-graph`

**para que:** Analisa Metadata Graph declarado e impacto de linhagem, sem acessar serviços externos.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze platform-graph [help] <path> [changed_node] [changed_attribute] [direction] [max_depth] [max_items] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo JSON ou YAML do Platform Intelligence Graph. |
| `changed_node` | no | — | ID da entidade alterada para calcular blast radius. |
| `changed_attribute` | no | — | Caminho de atributo declarado no nó alterado. |
| `direction` | no | — | — |
| `max_depth` | no | — | — |
| `max_items` | no | — | — |
| `out` | no | — | Escreve o envelope completo em JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze pyspark`

**para que:** Extrai facts de PySpark via AST estatico (nunca importa o codigo).

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze pyspark [help] <path> [upstream] [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio a analisar. |
| `upstream` | no | — | Documento sparkforge_aws/upstream-facts/v1 com facts de outro motor (evidencia, nunca instrucao); entram no fim de `items`. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze s3-listing`

**para que:** Extrai facts de um dump de `aws s3api list-objects-v2` (small files, compressao nao splitavel).

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze s3-listing [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .json ou diretorio com paginas da listagem. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze schema-registry`

**para que:** Extrai facts offline de contratos e evolução de schemas.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze schema-registry [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON/JSONL. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze sfn-history`

**para que:** Extrai facts do HISTORICO de execucao de uma state machine do AWS Step Functions (a saida salva de `aws stepfunctions get-execution-history`): uma tentativa por par TaskScheduled/terminal, com ordem, resultado, duracao, erro e o JobRunId do Glue lido do output do TaskSubmitted. Le o que ACONTECEU, nunca a definicao.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze sfn-history [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .json salvo de get-execution-history, ou diretorio com eles. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze sql`

**para que:** Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze sql [help] [path] [from_pyspark] [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | no | — | Arquivo .sql a analisar. |
| `from_pyspark` | no | — | Arquivo .py: extrai texto de chamadas spark.sql("...") em vez de ler --path. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze sql-metrics`

**para que:** Extrai metrica por no do plano de um Spark event log ja coletado.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze sql-metrics [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Event log em JSON Lines. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze step-functions`

**para que:** Extrai facts da definicao ASL de uma state machine do AWS Step Functions (`.asl.json` ou a saida salva de `aws stepfunctions describe-state-machine`): um fact por estado Task, com padrao de integracao, JobName, retry efetivo, Catch e TimeoutSeconds. Le a DEFINICAO, nunca o historico de execucao.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze step-functions [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo .json (ASL ou describe-state-machine) ou diretorio com eles. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze streaming`

**para que:** Extrai facts de fonte Structured Streaming ou StreamingQueryProgress.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze streaming [help] <path> <artifact> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio a analisar. |
| `artifact` | yes | — | Tipo do artefato: fonte PySpark ou progresso JSON/JSONL. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze streaming-composition`

**para que:** Compõe facts já extraídos de streaming, transporte e Iceberg.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze streaming-composition [help] <facts> <mode> [table] [query_name] [slo_name] [transport_key] [max_skew_seconds] [pipeline_path] [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts gerado por um analyze; repetível para unir fontes. |
| `mode` | yes | — | Relação a analisar: streaming→Iceberg, janela streaming→Iceberg, progresso→transporte, SLO→progress/sink/transporte, janela temporal pareada ou contrato pipeline. |
| `table` | no | — | Tabela Iceberg declarada. |
| `query_name` | no | — | Query Structured Streaming declarada. |
| `slo_name` | no | — | Nome do SLO declarado; obrigatório quando há mais de uma declaração. |
| `transport_key` | no | — | Grupo/topic Kafka ou stream Kinesis declarado; obrigatório no mode=slo de transporte. |
| `max_skew_seconds` | no | — | Tolerância temporal declarada para modes temporal/iceberg_temporal; sem valor sai unresolved. |
| `pipeline_path` | no | — | Contrato JSON declarativo de nós/arestas; obrigatório quando mode=pipeline. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetível. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze streaming-integrations`

**para que:** Extrai facts offline de checkpoints, Kafka Connect/Streams e OpenLineage.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze streaming-integrations [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretório JSON/JSONL. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetível. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze streaming-ops`

**para que:** Extrai facts declarados de SLO, FinOps, segurança e serving streaming.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze streaming-ops [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretório JSON. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetível. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze terraform`

**para que:** Extrai facts de blocos aws_glue_job em HCL Terraform.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze terraform [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio .tf a analisar. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze terraform-diff`

**para que:** Compara dois estados de um modulo Terraform e marca o que mudou.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze terraform-diff [help] <before> <after> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `before` | yes | — | Diretorio do estado anterior. |
| `after` | yes | — | Diretorio do estado proposto. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze transport`

**para que:** Extrai facts offline de dumps Kafka, MSK ou Kinesis.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze transport [help] <path> <artifact> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo ou diretorio JSON/JSONL. |
| `artifact` | yes | — | Vocabulário do dump: Kafka, MSK ou Kinesis. |
| `out` | no | — | Escreve a lista completa de facts (JSON). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `analyze workload`

**para que:** Extrai facts do inventario declarado de workload (workload.yaml: SLA e fonte primaria), que capacity, finops e workload consomem.

- **por que:** extrai facts determinísticos de código-fonte (AST, provenance sha256)
- **quando usar:** inventário factual de jobs antes de judge/playbook — sem rodar nada

**Syntax**

```text
sparkforge-aws analyze workload [help] <path> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Arquivo workload.yaml. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## arbitrate

### `arbitrate`

**para que:** Executor agentico deterministico: arbitra findings ja julgados e grava claim, evidencia, contradicao, lacuna e decisao no blackboard do case. Nao estima ganho, nao publica score, nao executa debate.

- **por que:** executor agêntico determinístico: arbitra findings já julgados e grava claim+evidência
- **quando usar:** transformar findings julgados em ação auditável com recibo

**Syntax**

```text
sparkforge-aws arbitrate [help] <findings> <facts> [repo] [glue] [emr] [databricks] [photon] [spark] [python] [iceberg] [athena]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `findings` | yes | — | Arquivo de findings (JSON) gerado por `judge --out`. Aceita a lista nua e o objeto com a chave `findings` (ou `items`). |
| `facts` | yes | — | Arquivo de facts (JSON). Repetivel, e a repeticao e o ponto: o executor recebe a UNIAO dos facts do case -- o MESMO conjunto que `judge` recebeu para produzir aqueles findings. Alimenta-lo com um subconjunto fabrica claim desancorada que a execucao real nao produz. Aceita a lista nua e o objeto com a chave `facts` (ou `items`); fact sem `id` tem o id computado pelo conteudo. |
| `repo` | no | — | Raiz do case. O blackboard fica em <repo>/.sparkforge_aws/blackboard/. |
| `glue` | no | — | — |
| `emr` | no | — | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `databricks` | no | — | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## architecture

### `architecture`

**para que:** Avalia arquitetura declarada sem escolher por preferência ou custo inventado.

- **por que:** avalia arquitetura declarada sem preferência nem custo inventado
- **quando usar:** revisão estrutural honesta de topologia declarada

**Syntax**

```text
sparkforge-aws architecture [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `architecture streaming`

**para que:** Compara candidatos streaming por constraints factuais declaradas.

- **por que:** avalia arquitetura declarada sem preferência nem custo inventado
- **quando usar:** revisão estrutural honesta de topologia declarada

**Syntax**

```text
sparkforge-aws architecture streaming [help] <path> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | JSON com requirements e assumptions separados. |
| `out` | no | — | Escreve o ADR e a matriz completa neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## autonomy

### `autonomy`

**para que:** Mostra níveis de autonomia L0-L5.

- **por que:** mostra os níveis de autonomia L0-L5
- **quando usar:** entender o que cada nível permite antes de subir autonomia

**Syntax**

```text
sparkforge-aws autonomy [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `autonomy show`

**para que:** Mostra perfil de um nível.

- **por que:** mostra os níveis de autonomia L0-L5
- **quando usar:** entender o que cada nível permite antes de subir autonomia

**Syntax**

```text
sparkforge-aws autonomy show [help] <level>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `level` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## benchmark

### `benchmark`

**para que:** Compara duas execucoes a partir dos facts de event log de cada uma. Nao executa nada e nao mede relogio.

- **por que:** compara duas execuções por facts de event log — não executa nada
- **quando usar:** validar se uma mudança melhorou uma run já medida

**Syntax**

```text
sparkforge-aws benchmark [help] <before> <after> [out] [before_runtime] [after_runtime] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `before` | yes | — | Arquivo de facts gerado por `analyze event-log --out` da execucao ANTES. |
| `after` | yes | — | Arquivo de facts gerado por `analyze event-log --out` da execucao DEPOIS. |
| `out` | no | — | Escreve a lista completa de facts (JSON) neste arquivo. |
| `before_runtime` | no | — | Versao de runtime em que a execucao ANTES rodou (ex.: 5.1). |
| `after_runtime` | no | — | Versao de runtime em que a execucao DEPOIS rodou (ex.: 6.0). |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## blackboard

### `blackboard`

**para que:** Lê o shared blackboard (.sparkforge_aws/blackboard/).

- **por que:** lê o shared blackboard do case (.sparkforge_aws/blackboard/)
- **quando usar:** ver o que agentes já publicaram no case atual

**Syntax**

```text
sparkforge-aws blackboard [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `blackboard list`

**para que:** Lista entidades de um tipo.

- **por que:** lê o shared blackboard do case (.sparkforge_aws/blackboard/)
- **quando usar:** ver o que agentes já publicaram no case atual

**Syntax**

```text
sparkforge-aws blackboard list [help] [repo] <type>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `type` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `blackboard summary`

**para que:** Resumo contável do blackboard.

- **por que:** lê o shared blackboard do case (.sparkforge_aws/blackboard/)
- **quando usar:** ver o que agentes já publicaram no case atual

**Syntax**

```text
sparkforge-aws blackboard summary [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## budget

### `budget`

**para que:** Mostra estado do budget do case.

- **por que:** estado do budget do case
- **quando usar:** conferir quanto de contexto/custo o case já consumiu

**Syntax**

```text
sparkforge-aws budget [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `budget show`

**para que:** Mostra budget do case.

- **por que:** estado do budget do case
- **quando usar:** conferir quanto de contexto/custo o case já consumiu

**Syntax**

```text
sparkforge-aws budget show [help] [repo] [template]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `template` | no | — | Mostra os valores PADRAO do codigo, rotulados como template. Nao e o estado do case -- sem esta flag, budget nao declarado sai como unresolved. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## capacity

### `capacity`

**para que:** Escolhe a capacidade mais barata que cumpre o SLA, entre as capacidades que o job JA rodou. Nunca aplica a mudanca.

- **por que:** escolhe a capacidade mais barata que cumpre o SLA — entre capacidades que o job JÁ rodou
- **quando usar:** dimensionar DPU/worker com evidência, nunca extrapolação

**Syntax**

```text
sparkforge-aws capacity [help] <facts> <job_name> <job_run> [history] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (--out de analyze). |
| `job_name` | yes | — | — |
| `job_run` | yes | — | Id do run que este plano descreve. |
| `history` | no | — | Diretorio com um arquivo de facts por run anterior (`analyze glue-job-runs --out`), para as capacidades observadas. |
| `out` | no | — | Escreve o plano completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## case

### `case`

**para que:** Gerencia o estado do case em .sparkforge_aws/case.yaml.

- **por que:** gerencia o estado do case (.sparkforge_aws/case.yaml)
- **quando usar:** iniciar/inspecionar o case que ancora findings e evidência

**Syntax**

```text
sparkforge-aws case [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `case get`

**para que:** Le o case atual.

- **por que:** gerencia o estado do case (.sparkforge_aws/case.yaml)
- **quando usar:** iniciar/inspecionar o case que ancora findings e evidência

**Syntax**

```text
sparkforge-aws case get [help] <repo>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `case open`

**para que:** Cria um case novo, em fase intake.

- **por que:** gerencia o estado do case (.sparkforge_aws/case.yaml)
- **quando usar:** iniciar/inspecionar o case que ancora findings e evidência

**Syntax**

```text
sparkforge-aws case open [help] <repo> <case_id> <now> [glue] [emr] [databricks] [photon] [spark] [python] [iceberg] [athena] [facts] [strict_gates] [reopen]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `case_id` | yes | — | — |
| `now` | yes | — | Timestamp ISO 8601. Nunca lido do relogio pela CLI. |
| `glue` | no | — | — |
| `emr` | no | — | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `databricks` | no | — | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `facts` | no | — | Arquivo de facts (JSON) gerado por `analyze`. Repetivel. O runtime do case passa a sair do que os extratores observaram, nao so das flags. |
| `strict_gates` | no | — | Grava no case que gate com produtor declarado passa a bloquear a transicao de fase. A escolha e do case, nao da invocacao: vale pela investigacao inteira, e quem retoma noutra maquina herda o rigor de quem abriu. Sem a flag, o comportamento e o de sempre (gate advisory). |
| `reopen` | no | — | Recomeca do zero por cima de um case que ja existe. Sem esta flag, abrir sobre um case existente e RECUSADO: sobrescrever apagaria a fase, o rigor e os overrides gravados. O `strict_gates` do case atual e herdado -- `--strict-gates` sobe o rigor, e nada o baixa por omissao de flag. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `case update`

**para que:** Atualiza fase, gate ou registra uso de skill no case.

- **por que:** gerencia o estado do case (.sparkforge_aws/case.yaml)
- **quando usar:** iniciar/inspecionar o case que ancora findings e evidência

**Syntax**

```text
sparkforge-aws case update [help] <repo> [phase] [gate] [gate_value] [skill] [now] [outcome] [hypothesis] [prediction] [experiment] [ID] [hypothesis_outcome] [evidence] [override_gate] [reason] [facts]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `phase` | no | — | — |
| `gate` | no | — | — |
| `gate_value` | no | — | — |
| `skill` | no | — | — |
| `now` | no | — | — |
| `outcome` | no | — | — |
| `hypothesis` | no | — | Afirmacao testavel a registrar no case. Exige `--prediction` e `--experiment`: afirmacao sem previsao nao e testavel, e previsao sem experimento nao diz quem a testa. |
| `prediction` | no | — | O que muda no numero se a hipotese valer. |
| `experiment` | no | — | Como medir a previsao. |
| `ID` | no | — | Fecha a hipotese com este id. Exige `--hypothesis-outcome`. O registro e acrescimo: a afirmacao original fica onde esta. |
| `hypothesis_outcome` | no | — | Desfecho do experimento. `abandoned` existe porque a terceira coisa que acontece de verdade e o experimento nunca rodar. |
| `evidence` | no | — | Onde ler o que fechou a hipotese (stage, run, arquivo de facts). |
| `override_gate` | no | — | Passa por cima de um gate num case estrito, quando o dado genuinamente nao existe (job descontinuado, ambiente que sumiu). Exige `--reason`. Fica gravado no case como lista: dois overrides do mesmo gate sao dois fatos, e nenhum apaga o outro. |
| `reason` | no | — | Motivo do `--override-gate`. Sem ele o override e recusado. |
| `facts` | no | — | Arquivo de facts (JSON) que comprova os gates da fase pedida. Repetivel. Num case estrito, e daqui que sai a evidencia que destrava `--phase`. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## change

### `change`

**para que:** Autonomia L1-L2: gera o diff de um valor de configuracao (plan) e aplica um diff numa copia isolada para ver o que ele move nos achados (sandbox).

- **por que:** autonomia L1-L2: diff de config (plan) e aplicação numa cópia
- **quando usar:** ensaiar uma mudança de configuração com evidência antes/depois

**Syntax**

```text
sparkforge-aws change [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `change plan`

**para que:** Diff e diff de rollback de um valor de configuracao, achado pela procedencia dos facts (Terraform --conf ou spark.conf.set). Nao aplica nada.

- **por que:** autonomia L1-L2: diff de config (plan) e aplicação numa cópia
- **quando usar:** ensaiar uma mudança de configuração com evidência antes/depois

**Syntax**

```text
sparkforge-aws change plan [help] <facts> [repo] [from_tune] [CHAVE=VALOR] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Facts do case (repetivel): a uniao que o judge recebeu. |
| `repo` | no | — | Raiz usada na extracao dos facts (padrao: .). |
| `from_tune` | no | — | Usa o valor que o tune deriva da medida. |
| `CHAVE=VALOR` | no | — | Valor a propor (repetivel), por exemplo spark.sql.shuffle.partitions=320. |
| `out` | no | — | Grava o diff neste arquivo .patch (so quando pedido). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `change propose`

**para que:** Monta o pacote de um PR em .sparkforge_aws/proposal/<id>/ a partir do sandbox ja rodado: patch, rollback, corpo assinado, recibo e os comandos git/gh que o HOST roda. Nao executa git nem gh.

- **por que:** autonomia L1-L2: diff de config (plan) e aplicação numa cópia
- **quando usar:** ensaiar uma mudança de configuração com evidência antes/depois

**Syntax**

```text
sparkforge-aws change propose [help] [repo] <sandbox> [benchmark] [funcval] [now]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |
| `sandbox` | yes | — | O id que `sparkforge-aws change sandbox` devolveu. |
| `benchmark` | no | — | Facts com `bench.*` de dois runs medidos (repetivel). Sem ele, fica PENDENTE. |
| `funcval` | no | — | Facts com `funcval.*` do funcval compare. Sem ele, fica PENDENTE. |
| `now` | no | — | Instante ISO 8601 do recibo (padrao: agora, em UTC). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `change sandbox`

**para que:** Aplica um diff numa copia em .sparkforge_aws/sandbox/<id>/, roda o scan antes e depois e compara os achados. A arvore principal nao muda.

- **por que:** autonomia L1-L2: diff de config (plan) e aplicação numa cópia
- **quando usar:** ensaiar uma mudança de configuração com evidência antes/depois

**Syntax**

```text
sparkforge-aws change sandbox [help] [repo] [diff] [clean]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |
| `diff` | no | — | Arquivo de diff unificado (de change plan --out ou de git diff). |
| `clean` | no | — | Apaga .sparkforge_aws/sandbox/ e sai. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## code

### `code`

**para que:** Indice local de codigo: prepara, sincroniza, busca simbolo, monta contexto e diagnostica.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code context`

**para que:** Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code context [help] [root] [db] <task> [max_tokens] [include]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `task` | yes | — | — |
| `max_tokens` | no | — | — |
| `include` | no | — | Repetivel. Omitido, todas as secoes que este motor sabe preencher. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code doctor`

**para que:** Diagnostico local do indice e da superficie. Sai 1 quando alguma checagem falha. Nao testa conectividade de internet.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code doctor [help] [root] [db]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code export`

**para que:** Exporta o grafo no formato de extracao que a fonte publica.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code export [help] [root] [db] [communities] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `communities` | no | — | Nao calcula comunidade. `algorithm` sai `null`, que diz 'nao calculei'. |
| `detail_level` | no | — | `summary` para as contagens e a declaracao de compatibilidade; `normal` e `full` trazem nos e arestas. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code index`

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code index [help] [root] [db]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code init`

**para que:** Prepara o indice sob --root: preflight de seguranca, diretorio, conferencia do .gitignore, banco, indexacao e integridade. `index` e o nome antigo do mesmo comando.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code init [help] [root] [db]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code path`

**para que:** O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code path [help] [root] [db] <origem> <destino> [depth] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `origem` | yes | — | — |
| `destino` | yes | — | — |
| `depth` | no | — | Teto de saltos. Satura no maximo; atingi-lo sai como `depth_exhausted`. |
| `detail_level` | no | — | `summary` para o veredito e as contagens do grafo; `normal` e `full` acrescentam os nos do caminho. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code purge`

**para que:** Apaga SOMENTE .sparkforge_aws/local/codeintel/. Qualquer outro diretorio e recusado.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code purge [help] [root] [db]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code read`

**para que:** Le um trecho do repositorio, por --node-id OU por --file com faixa. Tetos duros: 250 linhas, 32 KiB, 4096 tokens.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code read [help] [root] [db] [node_id] [file] [start_line] [end_line] [context_lines] [max_tokens]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `node_id` | no | — | — |
| `file` | no | — | Caminho RELATIVO a --root. |
| `start_line` | no | — | — |
| `end_line` | no | — | — |
| `context_lines` | no | — | — |
| `max_tokens` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code search`

**para que:** Busca simbolo por parte do nome.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code search [help] [root] [db] <term> [kind] [path_prefix] [limit]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `term` | yes | — | — |
| `kind` | no | — | Filtra por tipo de no: function, class, method. |
| `path_prefix` | no | — | Filtra por prefixo do caminho relativo. |
| `limit` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code shape`

**para que:** Comunidades e nos de maior grau. Nao e julgamento, e forma.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code shape [help] [root] [db] [top] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `top` | no | — | Quantas comunidades e quantos nos por grau. Satura no teto. |
| `detail_level` | no | — | `summary` para as contagens e o metodo; `normal` e `full` acrescentam os membros e a lista por grau. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code status`

**para que:** Estado do indice: frescor, contagens, seguranca e o que mudou na arvore.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code status [help] [root] [db] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `detail_level` | no | — | Mesmos niveis das tools de fact, conteudo proprio deste verbo: `full` acrescenta o bloco de seguranca (SPEC 67) e o de mudancas (SPEC 63); `normal` e `summary` param no estado do indice. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code symbol`

**para que:** Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code symbol [help] [root] [db] <node_id> [depth] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `node_id` | yes | — | — |
| `depth` | no | — | — |
| `detail_level` | no | — | `summary` para no metadado; `normal` acrescenta vizinhanca direta; `full` acrescenta o raio de impacto e os testes nele. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `code sync`

**para que:** Poe o indice em dia com a arvore. Unica escrita do verbo.

- **por que:** índice local de código: símbolos, contexto, diagnóstico
- **quando usar:** busca estrutural de código sem varrer o repo inteiro

**Syntax**

```text
sparkforge-aws code sync [help] [root] [db]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `db` | no | — | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## collect

### `collect`

**para que:** Coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg).

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect athena-workgroup`

**para que:** Baixa a configuracao de um workgroup via a API do Athena.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect athena-workgroup [help] <repo> <workgroup> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `workgroup` | yes | — | — |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect cloudwatch`

**para que:** Baixa metricas de observabilidade Glue via CloudWatch.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect cloudwatch [help] <repo> <job_name> <job_run> <start> <end> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `job_name` | yes | — | — |
| `job_run` | yes | — | — |
| `start` | yes | — | Inicio ISO 8601. |
| `end` | yes | — | Fim ISO 8601. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect cloudwatch-logs`

**para que:** Baixa o LOG do run no CloudWatch Logs (o caminho das assinaturas de mensagem).

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect cloudwatch-logs [help] <repo> <job_name> <job_run> <log_group> <start> <end> [filter_pattern] [max_events] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `job_name` | yes | — | — |
| `job_run` | yes | — | — |
| `log_group` | yes | — | Log group. Sem default -- `/aws-glue/jobs/error`, `/aws-glue/jobs/output` e `/aws-glue/jobs/logs-v2` tem conteudo diferente. |
| `start` | yes | — | Inicio ISO 8601. |
| `end` | yes | — | Fim ISO 8601. |
| `filter_pattern` | no | — | Filtro do CloudWatch Logs, aplicado no servidor. Declara a relevancia. |
| `max_events` | no | — | Teto de eventos. Quando morde, o artefato sai com truncated: true. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect emr-cluster`

**para que:** Baixa describe-cluster, grupos/fleets, bootstrap actions e as politicas de scaling de um cluster EMR on EC2.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect emr-cluster [help] <repo> <cluster_id> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `cluster_id` | yes | — | j-XXXXXXXXXXXXX |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect emr-eks`

**para que:** Baixa describe-virtual-cluster e describe-job-run de uma execucao Amazon EMR on EKS e grava as duas respostas num arquivo so. Duas chamadas, nao uma: no `emr-containers` cluster virtual e execucao sao APIs separadas.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect emr-eks [help] <repo> <virtual_cluster_id> <job_run_id> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `virtual_cluster_id` | yes | — | Id do cluster virtual. Nome NAO serve: `DescribeJobRun` exige o id. |
| `job_run_id` | yes | — | Id da execucao. Os DOIS ids sao obrigatorios porque `DescribeJobRun` exige `virtualClusterId` junto do `id`. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect emr-serverless`

**para que:** Baixa get-application de uma application EMR Serverless. Uma chamada, nao seis: capacidade, auto-stop, runtimeConfiguration e monitoramento chegam no mesmo objeto.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect emr-serverless [help] <repo> <application_id> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `application_id` | yes | — | Id da application (`00fXXXXXXXXXXXXX`). Nome NAO serve: e opcional na API e nao ha fonte que o declare unico. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect event-log`

**para que:** Baixa o Spark event log de um job run via S3.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect event-log [help] <repo> <job_run> <bucket> <prefix> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `job_run` | yes | — | — |
| `bucket` | yes | — | — |
| `prefix` | yes | — | — |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect glue-job`

**para que:** Baixa a definicao de um job via a API do Glue.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect glue-job [help] <repo> <job_name> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `job_name` | yes | — | — |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect glue-job-runs`

**para que:** Baixa o historico de execucoes de um job, um artefato por run terminal.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect glue-job-runs [help] <repo> <job_name> [max_runs] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `job_name` | yes | — | — |
| `max_runs` | no | — | Teto de paginacao. A API devolve do mais recente para tras. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect glue-resource-link`

**para que:** Le o resource link na conta consumidora e o recurso de origem que ele declara.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect glue-resource-link [help] <repo> <database> [table] [catalog_id] [no_verify_target] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `database` | yes | — | Banco do link na conta consumidora. |
| `table` | no | — | Nome do link de TABELA. Sem ele o alvo e um BANCO -- e a comparacao de nome muda, porque `TargetDatabase` nao tem campo `Name`. |
| `catalog_id` | no | — | Id da conta CONSUMIDORA, onde o link mora. O catalogo de origem sai medido do proprio link e nunca e passado a mao. |
| `no_verify_target` | no | — | Pula a leitura do recurso de ORIGEM. O default e conferir: link que aponta para lugar nenhum e o defeito que este coletor existe para achar. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect iam-access`

**para que:** Simula acoes contra um role via SimulatePrincipalPolicy e grava a decisao.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect iam-access [help] <repo> <role_arn> [actions] [resource_arns] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `role_arn` | yes | — | ARN do role a simular -- tipicamente o runtime role do job. |
| `actions` | no | — | Acao a simular. Repetivel. Sem ela, a lista default de Lake Formation e Glue -- e passar a lista inteira quando a pergunta e sobre UMA escrita produz decisoes que nao dizem nada sobre o caso. |
| `resource_arns` | no | — | Recurso contra o qual simular. Repetivel. Sem ele a resposta e sobre `*`. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect iceberg-metadata`

**para que:** Consulta metadata tables Iceberg de uma tabela via Athena.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect iceberg-metadata [help] <repo> <table> <workgroup> <output_location> <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `table` | yes | — | db.tabela |
| `workgroup` | yes | — | — |
| `output_location` | yes | — | — |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect lakeformation`

**para que:** Coleta grant, registro de localizacao S3 e data lake settings de UMA tabela.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect lakeformation [help] <repo> <database> <table> [catalog_id] [resource_arn] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `database` | yes | — | Banco da tabela no catalogo. |
| `table` | yes | — | Nome da tabela. |
| `catalog_id` | no | — | Id da conta dona do catalogo. Obrigatorio em cross-account: a MESMA `db.tabela` existe em contas diferentes, e sem ele as duas coletas se sobrescrevem no manifesto. |
| `resource_arn` | no | — | Localizacao S3 a conferir em `describe_resource`. Sem ela o bloco sai `nao_coletado` em vez de sumir -- bloco ausente e indistinguivel de vazio. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect managed-flink`

**para que:** Coleta descrição read-only de uma aplicação Managed Flink; com janela explícita, coleta cinco métricas temporais de aplicação.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect managed-flink [help] <repo> <application_name> [region_name] [metrics_start] [metrics_end] [metrics_period] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `application_name` | yes | — | Nome da aplicação Managed Flink. |
| `region_name` | no | — | Região AWS explícita. |
| `metrics_start` | no | — | Início ISO 8601 da janela CloudWatch Managed Flink. |
| `metrics_end` | no | — | Fim ISO 8601 da janela CloudWatch Managed Flink; exige --metrics-start. |
| `metrics_period` | no | — | Período CloudWatch em segundos (60..86400, múltiplo de 60). |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect parquet-footer`

**para que:** Le so o FOOTER dos Parquet de um prefixo (diretorio local ou s3://): row group, estatistica por coluna e sort order. Nenhuma linha de dado. Exige pyarrow.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect parquet-footer [help] <repo> <prefix> [max_files] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `prefix` | yes | — | Diretorio local com .parquet, ou s3://bucket/prefixo/. |
| `max_files` | no | — | Quantos arquivos ler, os primeiros pelo nome (padrao do coletor: 20; teto 500). |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect schema-registry`

**para que:** Coleta metadata e latest version read-only do AWS Glue Schema Registry.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect schema-registry [help] <repo> [registry_name] [schema_name] [schema_arn] [region_name] [max_schemas] [max_definition_bytes] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `registry_name` | no | — | Nome do registry Glue. |
| `schema_name` | no | — | Filtra schema dentro do registry. |
| `schema_arn` | no | — | ARN do schema Glue. |
| `region_name` | no | — | Região AWS explícita. |
| `max_schemas` | no | — | Teto de schemas (1..500). |
| `max_definition_bytes` | no | — | Teto por definição; acima sai unresolved. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect streaming-integrations`

**para que:** Coleta snapshots read-only de checkpoint Spark, Glue Streaming, Kinesis, MSK e DMS; com janela explícita, coleta cinco métricas stream-level temporais do Kinesis; Connect/Streams/OpenLineage continuam unresolved sem endpoint proprio.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect streaming-integrations [help] <repo> [checkpoint_s3_uri] [glue_job_name] [kinesis_stream_name] [msk_cluster_arn] [dms_task_arn] [region_name] [max_objects] [max_shards] [metrics_start] [metrics_end] [metrics_period] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `checkpoint_s3_uri` | no | — | Prefixo S3 do checkpoint Spark. |
| `glue_job_name` | no | — | Nome do job Glue. |
| `kinesis_stream_name` | no | — | Nome do stream Kinesis. |
| `msk_cluster_arn` | no | — | ARN do cluster MSK. |
| `dms_task_arn` | no | — | ARN da replication task DMS. |
| `region_name` | no | — | Região AWS explícita, quando necessária. |
| `max_objects` | no | — | Teto de objetos do checkpoint (1..500). |
| `max_shards` | no | — | Teto de shards Kinesis (1..500). |
| `metrics_start` | no | — | Início ISO 8601 da janela CloudWatch Kinesis; exige --metrics-end. |
| `metrics_end` | no | — | Fim ISO 8601 da janela CloudWatch Kinesis; exige --metrics-start. |
| `metrics_period` | no | — | Período CloudWatch em segundos (60..86400, múltiplo de 60). |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect verify`

**para que:** Verifica presenca e integridade de todos os artefatos do manifesto.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect verify [help] <repo>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `collect workspace-graph`

**para que:** Coleta grafo live limitado aos cloud_resources declarados no workspace manifest.

- **por que:** coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg)
- **quando usar:** trazer evidência de runtime para análise offline — requer credencial

**Syntax**

```text
sparkforge-aws collect workspace-graph [help] <repo> <manifest> [max_objects] <now>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `manifest` | yes | — | — |
| `max_objects` | no | — | Teto de objetos S3 por recurso declarado; truncamento fica nomeado no artefato. |
| `now` | yes | — | Timestamp ISO 8601. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## context

### `context`

**para que:** Descobre capabilities e empacota contexto deterministico sob limite explicito.

- **por que:** descobre capabilities e empacota contexto sob limite explícito
- **quando usar:** montar contexto determinístico para um agente/host

**Syntax**

```text
sparkforge-aws context [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `context expand`

**para que:** Expande uma referencia ctx://v1 sob budget.

- **por que:** descobre capabilities e empacota contexto sob limite explícito
- **quando usar:** montar contexto determinístico para um agente/host

**Syntax**

```text
sparkforge-aws context expand [help] <ref> [max_bytes] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `ref` | yes | — | — |
| `max_bytes` | no | — | Teto de bytes serializados; omitido usa default economy. |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `context inspect`

**para que:** Inspeciona qualidade de contexto sem inferir tokens por bytes.

- **por que:** descobre capabilities e empacota contexto sob limite explícito
- **quando usar:** montar contexto determinístico para um agente/host

**Syntax**

```text
sparkforge-aws context inspect [help] <input> [observed_provider_tokens]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `input` | yes | — | JSON com itens e refs de evidencia. |
| `observed_provider_tokens` | no | — | Tokens observados no transcript do host; omitido permanece unresolved. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `context resolve`

**para que:** Resolve locality repo/workspace/target sem ler fontes.

- **por que:** descobre capabilities e empacota contexto sob limite explícito
- **quando usar:** montar contexto determinístico para um agente/host

**Syntax**

```text
sparkforge-aws context resolve [help] [root] [scope] [target] [impact]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `scope` | no | — | — |
| `target` | no | — | — |
| `impact` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `context start`

**para que:** Inicia descoberta, selecao, reducao e materializacao de contexto.

- **por que:** descobre capabilities e empacota contexto sob limite explícito
- **quando usar:** montar contexto determinístico para um agente/host

**Syntax**

```text
sparkforge-aws context start [help] <intent> [profile] [max_bytes] [items] [role] [role_plan] [repo] [case_id]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `intent` | yes | — | — |
| `profile` | no | — | — |
| `max_bytes` | no | — | Teto de bytes serializados; omitido usa default do profile. |
| `items` | no | — | JSON com lista de facts/findings/knowledge/codigo ja extraidos. |
| `role` | no | — | Role com plano declarado (sf-inventory/sf-extractor/sf-judge/sf-verifier/sf-synthesizer); desconhecida nega contexto. |
| `role_plan` | no | — | Arquivo JSON com RoleContextPlan serializado (vence --role). |
| `repo` | no | — | — |
| `case_id` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## controlm

### `controlm`

**para que:** Conhecimento versionado do Control-M Automation API. Le matriz de versao; NAO le artefato, NAO chama BMC e NAO julga.

- **por que:** conhecimento versionado do Control-M Automation API — lê matriz, não artefato
- **quando usar:** avaliar migração/integração Control-M com fonte versionada

**Syntax**

```text
sparkforge-aws controlm [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `controlm describe`

**para que:** O que vale numa versao do Automation API. Versao fora da faixa coberta sai como recusa NOMEADA, com o intervalo.

- **por que:** conhecimento versionado do Control-M Automation API — lê matriz, não artefato
- **quando usar:** avaliar migração/integração Control-M com fonte versionada

**Syntax**

```text
sparkforge-aws controlm describe [help] <version> [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `version` | yes | — | A versao do Automation API (ex.: 9.0.21.300). A faixa coberta e 9.0.21.200--9.0.22.100. |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o descritor inteiro -- e o modo de reauditoria. `compact` reduz `capabilities` a lista de slugs e tira `unresolved_detail` (`unresolved`, a mesma lista sem a razao, fica); `deprecated` continua INTEIRO, porque e a resposta direta a `o que eu nao posso mais usar` e cortar obrigaria uma segunda chamada para a MESMA pergunta. `minimal` reduz a `version`, `covers`, a CONTAGEM de `capabilities`, os SLUGS de `deprecated` e a CONTAGEM de `unresolved` -- a contagem nunca some, mesmo em zero, porque e a recusa nomeada da matriz; a lista de slugs e a razao de cada uma exigem `compact`/`full`. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## debate

### `debate`

**para que:** Conduz e arbitra o protocolo de debate do case. Nao gera argumento: quem escreve cada submissao e o host.

- **por que:** conduz e arbitra o protocolo de debate do case — não gera argumento
- **quando usar:** quando o caso exige debate estruturado entre submissões

**Syntax**

```text
sparkforge-aws debate [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `debate next`

**para que:** O brief do lado da vez, ou `done` com a Decision. Grava a Decision no fechamento; depois dele devolve sempre o mesmo `done`.

- **por que:** conduz e arbitra o protocolo de debate do case — não gera argumento
- **quando usar:** quando o caso exige debate estruturado entre submissões

**Syntax**

```text
sparkforge-aws debate next [help] [repo] <debate>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do case. |
| `debate` | yes | — | O `debate_id` que `start` devolveu. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `debate referee`

**para que:** Diz se o fechamento declarado pode ser publicado: hipotese que sobrevive, claim sem evidencia, objecao sem replica, referencia pendurada.

- **por que:** conduz e arbitra o protocolo de debate do case — não gera argumento
- **quando usar:** quando o caso exige debate estruturado entre submissões

**Syntax**

```text
sparkforge-aws debate referee [help] <repo>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `debate start`

**para que:** Congela o plano de debate do par --rules A,B em <repo>/.sparkforge_aws/debate/<debate_id>/, a partir dos MESMOS insumos do `arbitrate`. Recusa `budget_undeclared` sem `budget:` no case.yaml.

- **por que:** conduz e arbitra o protocolo de debate do case — não gera argumento
- **quando usar:** quando o caso exige debate estruturado entre submissões

**Syntax**

```text
sparkforge-aws debate start [help] <rules> <findings> <facts> [repo] [glue] [emr] [databricks] [photon] [spark] [python] [iceberg] [athena]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `rules` | yes | — | As duas regras em contradicao, `A,B`. O lado A defende a primeira. |
| `findings` | yes | — | Arquivo de findings (JSON) gerado por `judge --out` -- o mesmo do `arbitrate`. |
| `facts` | yes | — | Arquivo de facts (JSON). Repetivel: o plano e recalculado sobre a UNIAO dos facts do case, o mesmo conjunto que `arbitrate` recebeu. |
| `repo` | no | — | Raiz do case. |
| `glue` | no | — | — |
| `emr` | no | — | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `databricks` | no | — | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `debate submit`

**para que:** Valida e grava a submissao do lado da vez. Recusa por nome e deixa o estado igual.

- **por que:** conduz e arbitra o protocolo de debate do case — não gera argumento
- **quando usar:** quando o caso exige debate estruturado entre submissões

**Syntax**

```text
sparkforge-aws debate submit [help] [repo] <debate> <file>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do case. |
| `debate` | yes | — | O `debate_id` que `start` devolveu. |
| `file` | yes | — | A submissao (objeto JSON), no schema que o brief publica em `submission_schema`. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## decision

### `decision`

**para que:** Valida e observa decisões declarativas sem alterar o dispatch atual.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision benchmark`

**para que:** Executa a suíte seed offline do Decision Plane.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision benchmark [help] [fixture] [repo] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `fixture` | no | — | — |
| `repo` | no | — | — |
| `out` | no | — | Escreve o relatório neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision compare`

**para que:** Compara uma decisão shadow persistida com uma rota atual.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision compare [help] <shadow> <current_route> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `shadow` | yes | — | JSON de resultado shadow. |
| `current_route` | yes | — | — |
| `out` | no | — | Escreve a comparação neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision evaluate`

**para que:** Avalia contrato bounded genérico em modo offline.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision evaluate [help] [contract] <input> [repo] [now] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `contract` | no | — | — |
| `input` | yes | — | JSON de estado declarado. |
| `repo` | no | — | — |
| `now` | no | — | — |
| `out` | no | — | Escreve o resultado completo neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision receipt`

**para que:** Verifica receipt content-addressed de decisão shadow.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision receipt [help] <path> [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision shadow`

**para que:** Avalia estado normalizado e compara com a rota atual.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision shadow [help] [contract] <input> [repo] [now] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `contract` | no | — | — |
| `input` | yes | — | JSON de DecisionInput. |
| `repo` | no | — | — |
| `now` | no | — | — |
| `out` | no | — | Escreve o resultado completo neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decision validate`

**para que:** Valida um contrato Decision Plane versionado.

- **por que:** valida e observa decisões declarativas sem alterar dispatch
- **quando usar:** experimentar uma decisão antes de adotá-la

**Syntax**

```text
sparkforge-aws decision validate [help] [contract] [version] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `contract` | no | — | — |
| `version` | no | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## decisions

### `decisions`

**para que:** Lista e explica decisões registradas.

- **por que:** lista e explica decisões registradas
- **quando usar:** auditar o histórico de decisões do case

**Syntax**

```text
sparkforge-aws decisions [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decisions explain`

**para que:** Explica uma decisão.

- **por que:** lista e explica decisões registradas
- **quando usar:** auditar o histórico de decisões do case

**Syntax**

```text
sparkforge-aws decisions explain [help] [repo] <id>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `id` | yes | — | ID da decisão. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `decisions list`

**para que:** Lista decisões.

- **por que:** lista e explica decisões registradas
- **quando usar:** auditar o histórico de decisões do case

**Syntax**

```text
sparkforge-aws decisions list [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## detach

### `detach`

**para que:** Remove a integracao de usuario do host: so o que o manifesto ~/.sparkforge_aws/integrations.json registrou e ainda tem o sha256 gravado.

- **por que:** remove a integração de usuário do host — só o que o manifesto declara
- **quando usar:** desinstalar limpo sem órfãos nos hosts

**Syntax**

```text
sparkforge-aws detach [help] <host> [scope] [dry_run]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `host` | yes | — | Host, ou all. |
| `scope` | no | — | Escopo da integracao; so user nesta versao. |
| `dry_run` | no | — | Lista o que seria removido, sem remover. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## distribution

### `distribution`

**para que:** Inspeção e inicialização portátil offline.

- **por que:** inspeção e inicialização portátil offline
- **quando usar:** distribuir o pacote em ambiente sem rede

**Syntax**

```text
sparkforge-aws distribution [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `distribution doctor`

**para que:** Portable distribution doctor.

- **por que:** inspeção e inicialização portátil offline
- **quando usar:** distribuir o pacote em ambiente sem rede

**Syntax**

```text
sparkforge-aws distribution doctor [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `distribution init`

**para que:** Portable distribution init.

- **por que:** inspeção e inicialização portátil offline
- **quando usar:** distribuir o pacote em ambiente sem rede

**Syntax**

```text
sparkforge-aws distribution init [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `distribution inspect`

**para que:** Portable distribution inspect.

- **por que:** inspeção e inicialização portátil offline
- **quando usar:** distribuir o pacote em ambiente sem rede

**Syntax**

```text
sparkforge-aws distribution inspect [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `distribution status`

**para que:** Portable distribution status.

- **por que:** inspeção e inicialização portátil offline
- **quando usar:** distribuir o pacote em ambiente sem rede

**Syntax**

```text
sparkforge-aws distribution status [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## doctor

### `doctor`

**para que:** Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, knowledge, indice de codigo, artefatos, credencial AWS e a integracao de usuario de cada host. Sai 1 com alguma falha.

- **por que:** confere ambiente: pacote, extras, MCP, catálogo, packs, índice
- **quando usar:** primeira linha: pós-install, máquina nova, erro de import

**Syntax**

```text
sparkforge-aws doctor [help] [repo] [online]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |
| `online` | no | — | Confirma a credencial na AWS (STS get_caller_identity). Unico modo com rede. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `doctor agentic`

**para que:** Confere readiness local do plano agêntico, sem rede.

- **por que:** confere ambiente: pacote, extras, MCP, catálogo, packs, índice
- **quando usar:** primeira linha: pós-install, máquina nova, erro de import

**Syntax**

```text
sparkforge-aws doctor agentic [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## dq-ai

### `dq-ai`

**para que:** Avalia governanca Glue DQ ADVANCED sobre facts e artefatos observados.

- **por que:** avalia governança Glue DQ ADVANCED sobre facts observados
- **quando usar:** julgamento de data quality com evidência, não suposição

**Syntax**

```text
sparkforge-aws dq-ai [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `dq-ai assess`

**para que:** Compõe facts, julga regras e renderiza o relatório canônico.

- **por que:** avalia governança Glue DQ ADVANCED sobre facts observados
- **quando usar:** julgamento de data quality com evidência, não suposição

**Syntax**

```text
sparkforge-aws dq-ai assess [help] <facts> [dqdl] [review] [cost_facts] [glue] [spark] [python_version] [view] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | — |
| `dqdl` | no | — | DQDL externo a validar por sintaxe. |
| `review` | no | — | Manifesto externo de revisão humana. |
| `cost_facts` | no | — | Medição observada de custo Athena em JSON. |
| `glue` | no | — | — |
| `spark` | no | — | — |
| `python_version` | no | — | — |
| `view` | no | — | — |
| `out` | no | — | Escreve o relatório completo (JSON). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## economy

### `economy`

**para que:** O que a execucao poe na janela de contexto: byte medido, nunca token estimado.

- **por que:** o que a execução põe na janela de contexto — byte medido
- **quando usar:** quantificar contexto antes de reclamar de custo

**Syntax**

```text
sparkforge-aws economy [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `economy provider-cost`

**para que:** Calcula custo observado do transcript com pricing e cost_basis declarados.

- **por que:** o que a execução põe na janela de contexto — byte medido
- **quando usar:** quantificar contexto antes de reclamar de custo

**Syntax**

```text
sparkforge-aws economy provider-cost [help] <host_transcript> <pricing> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `host_transcript` | yes | — | — |
| `pricing` | yes | — | — |
| `out` | no | — | Escreve o relatorio (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `economy report`

**para que:** Agrupa os spans de um run e poe a superficie ao lado.

- **por que:** o que a execução põe na janela de contexto — byte medido
- **quando usar:** quantificar contexto antes de reclamar de custo

**Syntax**

```text
sparkforge-aws economy report [help] <run_id> [host_transcript] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_id` | yes | — | — |
| `host_transcript` | no | — | Transcript JSONL do host, quando houver. Sem ele o relatorio traz `tokens_unresolved` -- token de provider e do host, nao deste processo. |
| `out` | no | — | Escreve o relatorio (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## finops

### `finops`

**para que:** O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta -- capacidade ou codigo.

- **por que:** relatório financeiro: custo, troca recurso-tempo, alavanca de capacidade
- **quando usar:** decidir configuração por custo com dados reais de run

**Syntax**

```text
sparkforge-aws finops [help] <facts> <job_name> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (--out de analyze). |
| `job_name` | yes | — | — |
| `out` | no | — | Escreve o relatorio completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## funcval

### `funcval`

**para que:** Validacao funcional: deriva o que medir nos dois lados de uma mudanca e compara antes contra depois. Nao executa nada.

- **por que:** validação funcional: deriva o que medir nos dois lados e compara
- **quando usar:** provar equivalência antes/depois de uma mudança

**Syntax**

```text
sparkforge-aws funcval [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `funcval compare`

**para que:** Compara os dois resultados que VOCE mediu contra o plano. Antes contra depois, nunca observado contra catalogo.

- **por que:** validação funcional: deriva o que medir nos dois lados e compara
- **quando usar:** provar equivalência antes/depois de uma mudança

**Syntax**

```text
sparkforge-aws funcval compare [help] <plan> <before> <after> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `plan` | yes | — | Arquivo gerado por `funcval plan --out`. |
| `before` | yes | — | Resultado medido ANTES da mudanca: JSON com `target` e `checks`, um objeto por check. `value: null` exige `unavailable_reason`; check que voce nao mediu fica AUSENTE, nunca zero. |
| `after` | yes | — | Resultado medido DEPOIS, no mesmo contrato. |
| `out` | no | — | Escreve a comparacao (JSON de facts) neste arquivo, que e o que `judge --facts` le. Opcional, ao contrario do `--out` do `plan`: o plano e a entrada do proximo verbo, esta e uma saida terminal. Grava a lista COMPLETA, nunca a pagina -- `--limit` corta o stdout e nao o arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `funcval plan`

**para que:** Deriva o plano de validacao (contagem, schema, agregados) dos facts ja extraidos, e grava o artefato que `funcval compare` rele.

- **por que:** validação funcional: deriva o que medir nos dois lados e compara
- **quando usar:** provar equivalência antes/depois de uma mudança

**Syntax**

```text
sparkforge-aws funcval plan [help] <facts> [key] <out> [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (JSON) gerado por `analyze pyspark --out` ou `analyze catalog-schema --out`. Repetivel, e precisa ser: o alvo vem do `pyspark.write` e o schema/os agregados vem do `catalog.table_schema`, que nenhum verbo produz no mesmo arquivo. |
| `key` | no | — | Chave de negocio DECLARADA, repetivel. Virgula faz chave COMPOSTA (`--key loja_id,pedido_id` e uma chave de duas colunas, nao duas chaves). Nenhum fact do repositorio nomeia chave de negocio, entao o eixo so existe se voce o declarar -- e o check sai com `origin: declared`. Sem `--key`, o plano escreve o eixo como ausente em `undeclared_axes`. |
| `out` | yes | — | Escreve o plano (JSON de facts) neste arquivo. OBRIGATORIO, ao contrario do `--out` dos verbos de `analyze`: o plano e a entrada de `funcval compare --plan` e a evidencia do gate, nao uma conveniencia. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## fuse

### `fuse`

**para que:** Correlaciona facts de SQL com schema do catalogo (sparkforge_aws.facts.fusion), antes de judge.

- **por que:** correlaciona facts de SQL com schema do catálogo
- **quando usar:** cruzar uso real de tabelas/colunas com o catálogo antes de julgar

**Syntax**

```text
sparkforge-aws fuse [help] <facts> [out] [kind] [limit] [cursor] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (JSON) gerado por `analyze`. Repetivel: fusao precisa ver as fontes que quer correlacionar na mesma chamada. |
| `out` | no | — | Escreve a lista completa de facts fundidos (JSON) neste arquivo. |
| `kind` | no | — | Filtra por kind. Repetivel. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `detail_level` | no | — | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## gain

### `gain`

**para que:** Ganho OBSERVADO entre runs medidos antes e depois de uma mudanca: por lado, N, mediana, minimo e maximo de tempo, DPU-segundos e custo, e o delta das medianas. Nunca projeta economia nem atribui causa.

- **por que:** ganho OBSERVADO entre runs medidos antes/depois — por lado, N, mediana
- **quando usar:** comprovar melhoria estatística, não impressão

**Syntax**

```text
sparkforge-aws gain [help] <baseline> <candidate>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `baseline` | yes | — | Facts de runs do antes. Repetivel. |
| `candidate` | yes | — | Facts de runs do depois. Repetivel. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## glue

### `glue`

**para que:** Comandos especificos do runtime AWS Glue.

- **por que:** comandos específicos do runtime AWS Glue
- **quando usar:** operações de assessment/migração no domínio Glue

**Syntax**

```text
sparkforge-aws glue [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `glue dependency-audit`

**para que:** Audita dependencia Python e binario Scala do job contra um runtime.

- **por que:** comandos específicos do runtime AWS Glue
- **quando usar:** operações de assessment/migração no domínio Glue

**Syntax**

```text
sparkforge-aws glue dependency-audit [help] <path> <glue_version>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretorio do job (requirements*.txt e .jar). |
| `glue_version` | yes | — | Versao de Glue a auditar. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## graph

### `graph`

**para que:** Grafo do indice de codigo: status, ForgeGraphView e Graph Studio local.

- **por que:** grafo do índice de código: ForgeGraphView + Graph Studio local
- **quando usar:** navegar dependências do código indexado

**Syntax**

```text
sparkforge-aws graph [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `graph status`

**para que:** Estado do grafo: contagens e origem do indice.

- **por que:** grafo do índice de código: ForgeGraphView + Graph Studio local
- **quando usar:** navegar dependências do código indexado

**Syntax**

```text
sparkforge-aws graph status [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `graph ui`

**para que:** Abre o Graph Studio local (read-only, 127.0.0.1).

- **por que:** grafo do índice de código: ForgeGraphView + Graph Studio local
- **quando usar:** navegar dependências do código indexado

**Syntax**

```text
sparkforge-aws graph ui [help] [root] [limit] [no_browser] [port]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `limit` | no | — | — |
| `no_browser` | no | — | Serve sem abrir navegador (SSH). |
| `port` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `graph view`

**para que:** Emite o documento ForgeGraphView/v1 (contrato do Graph Studio).

- **por que:** grafo do índice de código: ForgeGraphView + Graph Studio local
- **quando usar:** navegar dependências do código indexado

**Syntax**

```text
sparkforge-aws graph view [help] [root] [limit]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `limit` | no | — | Teto de nos exportados (o restante fica em limitations). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## handoff

### `handoff`

**para que:** Escreve .sparkforge_aws/handoff.md e imprime o payload.

- **por que:** escreve .sparkforge_aws/handoff.md + payload
- **quando usar:** transferir o case para outro host/agente com contexto completo

**Syntax**

```text
sparkforge-aws handoff [help] <repo> [findings] [unresolved] [in_flight]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `findings` | no | — | — |
| `unresolved` | no | — | — |
| `in_flight` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## iceberg

### `iceberg`

**para que:** Comandos especificos de Apache Iceberg.

- **por que:** comandos específicos de Apache Iceberg
- **quando usar:** assessment de tabelas/catálogo Iceberg

**Syntax**

```text
sparkforge-aws iceberg [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `iceberg assess-upgrade`

**para que:** Avalia subir o format version da tabela contra quem a consome. NAO executa.

- **por que:** comandos específicos de Apache Iceberg
- **quando usar:** assessment de tabelas/catálogo Iceberg

**Syntax**

```text
sparkforge-aws iceberg assess-upgrade [help] <path> <from_spec> <to_spec>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretorio do job, com o inventario em .sparkforge_aws/consumers.yaml. |
| `from_spec` | yes | — | Format version de origem. |
| `to_spec` | yes | — | Format version alvo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## install

### `install`

**para que:** Instala o SparkForge no projeto/workspace (--scope) ou no HOME (--scope user, delegado ao integrate). Escreve so arquivos gerenciados; --dry-run mostra o plano.

- **por que:** instala SparkForge no projeto/workspace (--scope) ou HOME (--scope user)
- **quando usar:** instalar a forja num escopo governado

**Syntax**

```text
sparkforge-aws install [help] [scope] [host] [profile] [gateway_profile] [root] [yes] [components] [dry_run]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scope` | no | — | — |
| `host` | no | — | — |
| `profile` | no | — | — |
| `gateway_profile` | no | — | — |
| `root` | no | — | Raiz do alvo (default: raiz do VCS ou cwd). |
| `yes` | no | — | Aprovacao explicita: sem ela, --dry-run. |
| `components` | no | — | Componentes opcionais csv: skills,agents,mcp,tui,graph-studio. |
| `dry_run` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `install doctor`

**para que:** Saude da instalacao no alvo.

- **por que:** instala SparkForge no projeto/workspace (--scope) ou HOME (--scope user)
- **quando usar:** instalar a forja num escopo governado

**Syntax**

```text
sparkforge-aws install doctor [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## integrate

### `integrate`

**para que:** Instala skills, agents e o MCP do SparkForge nos diretorios de USUARIO do host (Claude Code por marketplace local; Devin, Codex e Copilot CLI), a partir do pacote instalado. Nada e escrito no repositorio, exceto a remocao da copia vendorizada que o operador escolher.

- **por que:** instala skills, agents e MCP nos diretórios de USUÁRIO do host
- **quando usar:** ativar a forja no Claude/Codex/Devin do usuário

**Syntax**

```text
sparkforge-aws integrate [help] <host> [profile] <scope> [dry_run] [on_conflict]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `host` | yes | — | Host, ou all. |
| `profile` | no | — | Profile Gateway; economy/balanced integram MCP Compact. |
| `scope` | yes | — | Escopo da integracao; so user nesta versao. |
| `dry_run` | no | — | Lista o que seria escrito, sem escrever. |
| `on_conflict` | no | — | Copia vendorizada em dobro no repositorio atual: overwrite apaga do repo, merge apaga so o identico, ignore nao toca. Sem a flag e sem terminal: ignore. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## journal

### `journal`

**para que:** Journal de eventos do case (.sparkforge_aws/journal.jsonl): um started e um finished por verbo que muda estado, encadeados por hash.

- **por que:** journal de eventos do case — started/finished por verbo
- **quando usar:** auditar sequência de operações do case

**Syntax**

```text
sparkforge-aws journal [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `journal verify`

**para que:** Recalcula a cadeia: intact, broken (com o seq da quebra), torn_tail ou absent. Sai 1 em broken.

- **por que:** journal de eventos do case — started/finished por verbo
- **quando usar:** auditar sequência de operações do case

**Syntax**

```text
sparkforge-aws journal verify [help] <repo>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## judge

### `judge`

**para que:** Aplica o catalogo de regras versionado sobre facts ja extraidos.

- **por que:** aplica o catálogo de regras versionado sobre facts extraídos
- **quando usar:** depois do analyze: transformar facts em findings com rule_id

**Syntax**

```text
sparkforge-aws judge [help] <facts> [glue] [emr] [databricks] [photon] [spark] [python] [iceberg] [athena] [severity] [out] [limit] [cursor] [show_skipped] [source_freshness] [as_of]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (JSON) gerado por `analyze`. Repetivel: regra que correlaciona extratores diferentes (SF-GLUE-004 cruza tf.attribute com pyspark.write) so dispara com as duas fontes na mesma chamada. |
| `glue` | no | — | — |
| `emr` | no | — | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `databricks` | no | — | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `severity` | no | — | Filtra por severidade. Repetivel. |
| `out` | no | — | Escreve a lista completa de findings (JSON) neste arquivo. |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `show_skipped` | no | — | — |
| `source_freshness` | no | — | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `as_of` | no | — | Dia de referencia do estado das fontes (AAAA-MM-DD). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## knowledge

### `knowledge`

**para que:** Localiza os arquivos de conhecimento versionado.

- **por que:** localiza arquivos de conhecimento versionado
- **quando usar:** achar a fonte canônica de regras/playbooks

**Syntax**

```text
sparkforge-aws knowledge [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `knowledge drift`

**para que:** Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), as regras e documentos que a leram antes da mudanca e os goldens, evals e agentes dessas regras. Sem rede.

- **por que:** localiza arquivos de conhecimento versionado
- **quando usar:** achar a fonte canônica de regras/playbooks

**Syntax**

```text
sparkforge-aws knowledge drift [help] [source] [as_of]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `source` | no | — | So esta fonte do lock (a chave do lock). |
| `as_of` | no | — | Dia de referencia do estado das fontes (AAAA-MM-DD). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `knowledge path`

**para que:** Imprime a raiz de knowledge e, com --file, um arquivo dentro dela.

- **por que:** localiza arquivos de conhecimento versionado
- **quando usar:** achar a fonte canônica de regras/playbooks

**Syntax**

```text
sparkforge-aws knowledge path [help] [file] [source_freshness] [as_of]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `file` | no | — | — |
| `source_freshness` | no | — | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `as_of` | no | — | Dia de referencia do estado das fontes (AAAA-MM-DD). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## lab

### `lab`

**para que:** Planeja e inspeciona experimentos Forge Lab; execução mutável exige confirmação explícita.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab analyze`

**para que:** Aponta artifacts capturados para análise posterior.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab analyze [help] <path> [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab compare`

**para que:** Compara dois receipts/runs sem afirmar performance.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab compare [help] <before> <after> [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `before` | yes | — | — |
| `after` | yes | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab describe`

**para que:** Descreve um cenário

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab describe [help] <scenario> [repo] [backend] [seed] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scenario` | yes | — | — |
| `repo` | no | — | — |
| `backend` | no | — | — |
| `seed` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab doctor`

**para que:** Verifica host, registry e perfis sem iniciar serviços.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab doctor [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab down`

**para que:** Derruba projeto Compose

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab down [help] [repo] [project] [profile] [service] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `project` | no | — | — |
| `profile` | no | — | — |
| `service` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab gc`

**para que:** Planeja coleta de runs

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab gc [help] [repo] [project] [profile] [service] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `project` | no | — | — |
| `profile` | no | — | — |
| `service` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab inspect`

**para que:** Inspeciona run/receipt e verifica hash.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab inspect [help] <path> [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab plan`

**para que:** Compila cenário em actions

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab plan [help] <scenario> [repo] [backend] [seed] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scenario` | yes | — | — |
| `repo` | no | — | — |
| `backend` | no | — | — |
| `seed` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab profiles`

**para que:** Lista profiles e requisitos declarados.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab profiles [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab promote-fixture`

**para que:** Promove run revisado para fixture curated.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab promote-fixture [help] <run> <destination> [reviewed] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run` | yes | — | — |
| `destination` | yes | — | — |
| `reviewed` | no | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab reproduce`

**para que:** Verifica receipt e devolve plano reproduzível.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab reproduce [help] <receipt> [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `receipt` | yes | — | — |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab run`

**para que:** Planeja ou executa cenário

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab run [help] <scenario> [repo] [backend] [seed] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scenario` | yes | — | — |
| `repo` | no | — | — |
| `backend` | no | — | — |
| `seed` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab scenarios`

**para que:** Lista o Golden 20 e suas fidelidades.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab scenarios [help] [repo] [json]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `json` | no | — | Mantido por compatibilidade; saída já é JSON. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab shell`

**para que:** Planeja shell de serviço

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab shell [help] [repo] [project] [profile] [service] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `project` | no | — | — |
| `profile` | no | — | — |
| `service` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab up`

**para que:** Sobe profile Compose

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab up [help] [repo] [project] [profile] [service] [execute] [confirm]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |
| `project` | no | — | — |
| `profile` | no | — | — |
| `service` | no | — | — |
| `execute` | no | — | — |
| `confirm` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lab verify`

**para que:** Verifica registry, Golden 20, schemas e action plans offline.

- **por que:** experimentos Forge Lab; execução mutável exige confirmação explícita
- **quando usar:** cenários reproduzíveis offline; nada muta sem opt-in

**Syntax**

```text
sparkforge-aws lab verify [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## lakeformation

### `lakeformation`

**para que:** Eixo de VERSAO de Lake Formation por runtime Glue -- capacidade, nao versao de componente.

- **por que:** eixo de versão Lake Formation por runtime Glue — capacidade, não componente
- **quando usar:** verificar o que cada runtime Glue suporta em LF

**Syntax**

```text
sparkforge-aws lakeformation [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lakeformation access-graph`

**para que:** O caminho de acesso como GRAFO, a partir de facts. `is_accessible` e TERNARIO -- `null` e 'o que olhei nao impede', nao 'funciona'.

- **por que:** eixo de versão Lake Formation por runtime Glue — capacidade, não componente
- **quando usar:** verificar o que cada runtime Glue suporta em LF

**Syntax**

```text
sparkforge-aws lakeformation access-graph [help] <facts_paths> [principal_arn] [target_table]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts_paths` | yes | — | — |
| `principal_arn` | no | — | — |
| `target_table` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lakeformation architect`

**para que:** Avalia arquitetura declarada de FGAC/FTA, ownership de catalogos, cross-account e capability por release. Nao toca AWS.

- **por que:** eixo de versão Lake Formation por runtime Glue — capacidade, não componente
- **quando usar:** verificar o que cada runtime Glue suporta em LF

**Syntax**

```text
sparkforge-aws lakeformation architect [help] <input>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `input` | yes | — | Arquivo JSON com engine, runtime, catalogos, modelo de acesso e evidencias. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `lakeformation matrix`

**para que:** Imprime o eixo: filesystem S3 default, FGAC por caminho, DDL/DML e FTA, com a frase da fonte quando ela existe.

- **por que:** eixo de versão Lake Formation por runtime Glue — capacidade, não componente
- **quando usar:** verificar o que cada runtime Glue suporta em LF

**Syntax**

```text
sparkforge-aws lakeformation matrix [help] [runtime] [axis] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `runtime` | no | — | Versao de Glue. Sem ela, todas as que a matriz cobre. Versao fora da matriz sai `unresolved` com o que destravaria -- nunca palpite por analogia com a versao vizinha. |
| `axis` | no | — | Eixo especifico (ex.: `fgac_spark_native_write`). Sem ele, todos. |
| `detail_level` | no | — | `summary` omite fonte, frase e nota. Ver a regra 28 do CLAUDE.md. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## mcp

### `mcp`

**para que:** Operacoes do servidor MCP.

- **por que:** operações do servidor MCP
- **quando usar:** servir a forja via MCP ou inspecionar o catálogo

**Syntax**

```text
sparkforge-aws mcp [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `mcp verify`

**para que:** Handshake JSON-RPC real: initialize + tools/list contra o server.

- **por que:** operações do servidor MCP
- **quando usar:** servir a forja via MCP ou inspecionar o catálogo

**Syntax**

```text
sparkforge-aws mcp verify [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## migrate

### `migrate`

**para que:** Avalia migracao entre versoes de runtime com o catalogo.

- **por que:** avalia migração entre versões de runtime com o catálogo
- **quando usar:** Glue 4→5/6, EMR, Spark — assessment versionado

**Syntax**

```text
sparkforge-aws migrate [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `migrate controlm`

**para que:** Julga a migracao de um job Control-M entre um par de versoes, degrau a degrau, por CAPACIDADE e nao por runtime.

- **por que:** avalia migração entre versões de runtime com o catálogo
- **quando usar:** Glue 4→5/6, EMR, Spark — assessment versionado

**Syntax**

```text
sparkforge-aws migrate controlm [help] <path> <from_runtime> <to_runtime> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretorio com as definicoes de `Jobs-as-Code` (`*.json`), ou um arquivo sozinho. E o mesmo artefato que o `ctm build` valida. |
| `from_runtime` | yes | — | Versao de Control-M de origem, na grafia da matriz (`9.0.21.300`). |
| `to_runtime` | yes | — | Versao alvo. Pode ser ANTERIOR a origem: descer e caso legitimo. |
| `out` | no | — | Escreve o assessment completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `migrate emr`

**para que:** Julga a migracao de um job EMR entre um par de releases, degrau a degrau, na matriz da plataforma escolhida.

- **por que:** avalia migração entre versões de runtime com o catálogo
- **quando usar:** Glue 4→5/6, EMR, Spark — assessment versionado

**Syntax**

```text
sparkforge-aws migrate emr [help] <path> <platform> <from_runtime> <to_runtime> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando existem e o inventario de consumidores em .sparkforge_aws/consumers.yaml --, ou um .py sozinho. |
| `platform` | yes | — | Qual matriz de EMR ordena o caminho e da o runtime de cada degrau. |
| `from_runtime` | yes | — | Release de origem, com ou sem o prefixo `emr-`. |
| `to_runtime` | yes | — | Release alvo, com ou sem o prefixo `emr-`. |
| `out` | no | — | Escreve o assessment completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `migrate glue`

**para que:** Julga a migracao de um job Glue entre um par de versoes, degrau a degrau.

- **por que:** avalia migração entre versões de runtime com o catálogo
- **quando usar:** Glue 4→5/6, EMR, Spark — assessment versionado

**Syntax**

```text
sparkforge-aws migrate glue [help] <path> <from_runtime> <to_runtime> [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `path` | yes | — | Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando existem e o inventario de consumidores em .sparkforge_aws/consumers.yaml --, ou um .py sozinho. |
| `from_runtime` | yes | — | Versao de Glue de origem. |
| `to_runtime` | yes | — | Versao de Glue alvo. |
| `out` | no | — | Escreve o assessment completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## next-step

### `next-step`

**para que:** Rota deterministica a partir de routing.yaml (nunca julgamento do agente).

- **por que:** rota determinística via routing.yaml — nunca julgamento do agente
- **quando usar:** o próximo passo correto a partir dos findings do case

**Syntax**

```text
sparkforge-aws next-step [help] <repo> [findings]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `findings` | no | — | Arquivo de findings (JSON) usado para casar condicoes. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## pack

### `pack`

**para que:** Forge Packs: regras, knowledge e fixtures de terceiro (SPARKFORGE_AWS_PACKS).

- **por que:** Forge Packs: regras, knowledge e fixtures de terceiro
- **quando usar:** estender a forja com packs versionados externos

**Syntax**

```text
sparkforge-aws pack [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `pack check`

**para que:** Roda cada fixture do pack pelo judge. Sai 1 quando uma regra do pack nao dispara no fixture que a declara, ou quando o pack e recusado.

- **por que:** Forge Packs: regras, knowledge e fixtures de terceiro
- **quando usar:** estender a forja com packs versionados externos

**Syntax**

```text
sparkforge-aws pack check [help] <dir>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `dir` | yes | — | Diretorio do pack (com pack.yaml). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `pack list`

**para que:** Packs ativos, recusados com o motivo, e o mapa prefixo -> pack.

- **por que:** Forge Packs: regras, knowledge e fixtures de terceiro
- **quando usar:** estender a forja com packs versionados externos

**Syntax**

```text
sparkforge-aws pack list [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## playbook

### `playbook`

**para que:** Decomposicao de um coordenador em passos sequenciais -- o PISO de orquestracao das cinco plataformas: unico caminho em Codex e Copilot CI, e o caminho em Claude Code, Devin CLI e Devin Local agent quando o despacho de subagente esta desligado -- e, no Devin, tambem quando ele esta ligado, porque subagente nao gera subagente por default. Le agents/, nunca repete a lista de executores.

- **por que:** decomposição de coordenador em passos sequenciais — piso de orquestração
- **quando usar:** executar fluxo multi-passo declarado, deterministicamente

**Syntax**

```text
sparkforge-aws playbook [help] <coordinator> [repo] [findings]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `coordinator` | yes | — | — |
| `repo` | no | — | — |
| `findings` | no | — | Arquivo de findings (JSON) usado para resolver o next_step embutido (AGENT-*). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## policy

### `policy`

**para que:** Politica de seguranca do repositorio (.sparkforge_aws/policy.yaml): validar, explicar uma decisao e gerar as regras ask do .claude/settings.json.

- **por que:** política de segurança do repo (.sparkforge_aws/policy.yaml)
- **quando usar:** validar/explicar regras de política aplicadas

**Syntax**

```text
sparkforge-aws policy [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `policy check`

**para que:** Valida a policy e lista as regras; sai 2 se ela for invalida.

- **por que:** política de segurança do repo (.sparkforge_aws/policy.yaml)
- **quando usar:** validar/explicar regras de política aplicadas

**Syntax**

```text
sparkforge-aws policy check [help] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `policy explain`

**para que:** Diz a decisao (allow, ask, deny), a regra que casou e qual porta a impoe.

- **por que:** política de segurança do repo (.sparkforge_aws/policy.yaml)
- **quando usar:** validar/explicar regras de política aplicadas

**Syntax**

```text
sparkforge-aws policy explain [help] [repo] [bash] [path] [tool]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |
| `bash` | no | — | Comando de shell a conferir. |
| `path` | no | — | Caminho de escrita a conferir. |
| `tool` | no | — | Nome de tool MCP a conferir. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `policy sync-settings`

**para que:** Gera permissions.ask no .claude/settings.json a partir das regras ask; --check so confere e sai 1 se divergir.

- **por que:** política de segurança do repo (.sparkforge_aws/policy.yaml)
- **quando usar:** validar/explicar regras de política aplicadas

**Syntax**

```text
sparkforge-aws policy sync-settings [help] [repo] [check]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | no | — | Raiz do repositorio (padrao: .). |
| `check` | no | — | So confere; nao grava. Sai 1 se divergir. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## proof

### `proof`

**para que:** Obrigacoes de prova de cada recomendacao APLICADA: resolucao (a regra deixou de disparar no depois?) e um eixo por item de action.moves (funcval, benchmark ou sem comparador). Desfechos: refuted, not_refuted, inconclusive, unproven -- nunca provado.

- **por que:** obrigações de prova de recomendações APLICADAS
- **quando usar:** provar que a regra deixou de disparar após aplicar

**Syntax**

```text
sparkforge-aws proof [help] <findings> <facts> <after_facts> <applied> [glue] [spark] [python] [iceberg] [athena] [emr] [databricks] [photon]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `findings` | yes | — | Findings do antes (`judge --out`). |
| `facts` | yes | — | Uniao de facts do case, com os de funcval e benchmark. Repetivel. |
| `after_facts` | yes | — | Facts extraidos dos artefatos do depois. Repetivel. |
| `applied` | yes | — | RULE_ID ou RULE_ID:simbolo de cada recomendacao aplicada. Repetivel. |
| `glue` | no | — | — |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `emr` | no | — | — |
| `databricks` | no | — | — |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## receipt

### `receipt`

**para que:** Recibo content-addressed da execucao do case: prova CORRESPONDENCIA entre o recibo e os artefatos, nunca autoria.

- **por que:** recibo content-addressed da execução — prova correspondência
- **quando usar:** verificar que o recibo corresponde aos artefatos da run

**Syntax**

```text
sparkforge-aws receipt [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `receipt emit`

**para que:** Grava .sparkforge_aws/receipts/<receipt_id>.json com caminho e sha256 do case, dos facts, dos findings, do report, do blackboard, dos ADRs e dos debates, os spans do run declarado e o host declarado. Sem conteudo de caso.

- **por que:** recibo content-addressed da execução — prova correspondência
- **quando usar:** verificar que o recibo corresponde aos artefatos da run

**Syntax**

```text
sparkforge-aws receipt emit [help] <facts> <findings> <now> [report] [run_id] [host_transcript] [provider] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts. Repetivel, e a repeticao e o contrato: a UNIAO do case. |
| `findings` | yes | — | Findings (JSON) gerados por `judge --out`. |
| `now` | yes | — | Instante ISO 8601 da emissao. Entra no hash. |
| `report` | no | — | Relatorio assinado, se houver. |
| `run_id` | no | — | Run cujos spans de tool entram. Sem ele, a parte tools sai em unresolved. |
| `host_transcript` | no | — | Transcript JSONL do host. So o sha256 entra; modelo e agente saem dele. |
| `provider` | no | — | Provider do host, DECLARADO (anthropic). |
| `repo` | no | — | Raiz do case. Caminhos relativos resolvem contra ela. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `receipt verify`

**para que:** Recalcula cada parte contra o disco e diz qual divergiu. Sai com codigo 1 quando o recibo nao corresponde.

- **por que:** recibo content-addressed da execução — prova correspondência
- **quando usar:** verificar que o recibo corresponde aos artefatos da run

**Syntax**

```text
sparkforge-aws receipt verify [help] <receipt> [host_transcript] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `receipt` | yes | — | — |
| `host_transcript` | no | — | O mesmo transcript da emissao; sem ele a parte host sai not_rechecked. |
| `repo` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## release

### `release`

**para que:** O que uma release publica, e o que muda entre duas. Le matriz de versao; NAO avalia se algo quebra.

- **por que:** o que uma release publica e o que muda entre duas — lê matriz de versão
- **quando usar:** comparar releases sem avaliar ambiente

**Syntax**

```text
sparkforge-aws release [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `release describe`

**para que:** O que a fonte daquela plataforma publica para uma release. Componente nao publicado sai em `unresolved` NOMEADO.

- **por que:** o que uma release publica e o que muda entre duas — lê matriz de versão
- **quando usar:** comparar releases sem avaliar ambiente

**Syntax**

```text
sparkforge-aws release describe [help] <platform> <release>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `platform` | yes | — | Uma das quatro: glue, emr_ec2, emr_serverless, emr_eks. |
| `release` | yes | — | O rotulo da release, com ou sem o prefixo `emr-` (ex.: 7.7.0, emr-7.7.0, 5.1). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `release diff`

**para que:** O que muda entre duas releases, com o eixo (`release`, `platform` ou os dois) DECLARADO na saida.

- **por que:** o que uma release publica e o que muda entre duas — lê matriz de versão
- **quando usar:** comparar releases sem avaliar ambiente

**Syntax**

```text
sparkforge-aws release diff [help] <left_platform> <left_release> <right_platform> <right_release>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `left_platform` | yes | — | Plataforma do lado de ONDE o operador sai. |
| `left_release` | yes | — | Release do lado de ONDE o operador sai. |
| `right_platform` | yes | — | Plataforma do lado PARA ONDE o operador vai. |
| `right_release` | yes | — | Release do lado PARA ONDE o operador vai. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## repair

### `repair`

**para que:** Regrava assets gerenciados que sumiram ou mudaram.

- **por que:** regrava assets gerenciados que sumiram ou mudaram
- **quando usar:** restaurar a integração sem reinstalar

**Syntax**

```text
sparkforge-aws repair [help] [scope] [root] [dry_run]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scope` | no | — | — |
| `root` | no | — | — |
| `dry_run` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## report

### `report`

**para que:** Assinatura de CORRESPONDENCIA do relatorio: prova que o texto foi derivado daquela evidencia com aquele catalogo. Nunca autoria.

- **por que:** assinatura de correspondência do relatório — texto derivado da evidência
- **quando usar:** provar que o relatório saiu daquela evidência, não de prosa

**Syntax**

```text
sparkforge-aws report [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `report github`

**para que:** Projeta findings ja julgados para o GitHub: SARIF para o Code Scanning e resumo Markdown para o PR, em .sparkforge_aws/report/ (nomes fixos), e uma anotacao ::error/::warning/::notice por finding com linha no stdout. Finding sem linha no repositorio sai no resumo com o motivo. Nao chama rede.

- **por que:** assinatura de correspondência do relatório — texto derivado da evidência
- **quando usar:** provar que o relatório saiu daquela evidência, não de prosa

**Syntax**

```text
sparkforge-aws report github [help] <findings> <facts> [repo] [source_roots] [fail_on] [category] [source_freshness] [as_of]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `findings` | yes | — | Saida de `judge --out` (findings.json). |
| `facts` | yes | — | Facts da UNIAO do case (repetivel): o fact de evidencia de codigo empresta a linha a um finding que nao tem a propria. |
| `repo` | no | — | Raiz do repositorio git. A saida vai para <repo>/.sparkforge_aws/report/. |
| `source_roots` | no | — | Diretorio (relativo a --repo) que foi passado a um `analyze --path`, repetivel, na mesma ordem. O caminho dos findings e relativo a ele. |
| `fail_on` | no | — | Sai com codigo 1 quando ha finding desta severidade ou pior. |
| `category` | no | — | Categoria do upload no Code Scanning (automationDetails.id). |
| `source_freshness` | no | — | Secao Fontes que pedem releitura no resumo, com o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `as_of` | no | — | Dia de referencia do estado das fontes (AAAA-MM-DD). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `report sign`

**para que:** Escreve o bloco de assinatura no fim do relatorio. Reassinar e barato e devolve o mesmo arquivo quando nada mudou.

- **por que:** assinatura de correspondência do relatório — texto derivado da evidência
- **quando usar:** provar que o relatório saiu daquela evidência, não de prosa

**Syntax**

```text
sparkforge-aws report sign [help] <report> <findings>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `report` | yes | — | Markdown do relatorio. E reescrito no lugar. |
| `findings` | yes | — | Arquivo de findings (JSON) gerado por `judge --out`. E dele que saem os quatro campos nao-corpo da assinatura: `evidence` (os fact_id citados), `rule_id`, `catalog_version` e `schema_version`. O arquivo de FACTS nao tem os tres ultimos -- por isso o verbo pede findings, e nao facts. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `report verify`

**para que:** Confere a assinatura e diz QUAL parte divergiu: evidencia, catalogo ou corpo. Sai com codigo 1 quando nao corresponde.

- **por que:** assinatura de correspondência do relatório — texto derivado da evidência
- **quando usar:** provar que o relatório saiu daquela evidência, não de prosa

**Syntax**

```text
sparkforge-aws report verify [help] <report> <findings>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `report` | yes | — | — |
| `findings` | yes | — | O mesmo arquivo de findings contra o qual o relatorio foi assinado. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## resume

### `resume`

**para que:** Payload de rehidratacao do case.

- **por que:** payload de reidratação do case
- **quando usar:** retomar um case noutro processo/host

**Syntax**

```text
sparkforge-aws resume [help] <repo> [findings] [unresolved] [in_flight]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | — |
| `findings` | no | — | — |
| `unresolved` | no | — | — |
| `in_flight` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## root-cause

### `root-cause`

**para que:** Ordena os achados por consequencia declarada e nomeia a lacuna. Nao calcula confianca e nao estima ganho.

- **por que:** ordena achados por consequência declarada e nomeia a lacuna
- **quando usar:** priorizar findings pela causa, não pela ordem de emissão

**Syntax**

```text
sparkforge-aws root-cause [help] <facts_paths> [glue] [spark] [python] [iceberg] [athena] [emr] [databricks] [photon] [all_missing] [detail_level]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts_paths` | yes | — | Arquivo de facts. REPETIVEL, e a repeticao e o contrato: uma regra pode exigir facts de mais de um extrator, e a lacuna publicada e sobre a UNIAO. |
| `glue` | no | — | — |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `emr` | no | — | — |
| `databricks` | no | — | — |
| `photon` | no | — | — |
| `all_missing` | no | — | Lista as regras nao avaliadas de TODAS as areas, e nao so das que ja tem achado. O TOTAL sai nos dois casos -- medido: 129 num case de Terraform sozinho, contra 5 no recorte. |
| `detail_level` | no | — | `summary` corta remediacao, validacao, rollback e os riscos da regra. Nunca corta `rule_id`, severidade, evidencia nem a lacuna. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## rules

### `rules`

**para que:** Consulta o catalogo de regras versionado.

- **por que:** consulta o catálogo de regras versionado
- **quando usar:** ver regras disponíveis e seus metadados

**Syntax**

```text
sparkforge-aws rules [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `rules lookup`

**para que:** Busca regras por id ou categoria (thresholds, fontes, severidade).

- **por que:** consulta o catálogo de regras versionado
- **quando usar:** ver regras disponíveis e seus metadados

**Syntax**

```text
sparkforge-aws rules lookup [help] [id] [category] [limit] [cursor] [severity] [runtime] [index] [source_freshness] [as_of]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `id` | no | — | — |
| `category` | no | — | — |
| `limit` | no | — | — |
| `cursor` | no | — | — |
| `severity` | no | — | Filtra por severity_default. |
| `runtime` | no | — | Filtra pelas regras cujo runtime_scope tem esta CHAVE (glue, spark, ...). Nao compara versao: o escopo vem na resposta para voce ler. |
| `index` | no | — | Forma compacta em rules_index (id, category, title, severity_default, runtime_scope), com rules vazia. Para procurar regra por atributo sem baixar o catalogo inteiro. |
| `source_freshness` | no | — | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `as_of` | no | — | Dia de referencia do estado das fontes (AAAA-MM-DD). |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## runtime

### `runtime`

**para que:** Deteccao de runtime Glue/EMR/Databricks/Spark/Python/Iceberg/Athena.

- **por que:** detecção de runtime Glue/EMR/Databricks/Spark/Python/Iceberg/Athena
- **quando usar:** identificar o runtime alvo da análise

**Syntax**

```text
sparkforge-aws runtime [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `runtime detect`

**para que:** Deriva a matriz de runtime a partir de facts ja extraidos e de flags.

- **por que:** detecção de runtime Glue/EMR/Databricks/Spark/Python/Iceberg/Athena
- **quando usar:** identificar o runtime alvo da análise

**Syntax**

```text
sparkforge-aws runtime detect [help] [glue] [emr] [databricks] [photon] [spark] [python] [iceberg] [athena] [facts]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `glue` | no | — | — |
| `emr` | no | — | Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. E DECLARACAO, nao observacao: perde para o event log e para um dump de `describe-cluster`, e discordar de um deles vira divergencia reportada, nunca valor substituido em silencio. Serve a quem sabe a release e nao tem o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts `emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e medidamente errada. |
| `databricks` | no | — | Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde para a versao que o event log traz, e discordar vira divergencia reportada. Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml. |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `facts` | no | — | Arquivo de facts (JSON) gerado por `analyze`. Repetivel. A versao OBSERVADA pelos extratores (`tf.attribute` glue_version, `spark.runtime_version`) entra como fonte propria -- sem isto, so as flags alimentam a deteccao. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## scan

### `scan`

**para que:** Roda sozinho os analyzes que cabem num repositorio: artefato coletado pelo manifesto, codigo pela extensao; depois fuse, judge e um resumo em .sparkforge_aws/scan/. Sem rede.

- **por que:** roda sozinho os analyzes que cabem no repo
- **quando usar:** primeira passada num repo desconhecido — descoberta por presença

**Syntax**

```text
sparkforge-aws scan [help] [raiz] [dry_run] [format] [fail_on] [glue] [spark] [python] [iceberg] [athena] [emr] [databricks] [photon]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `raiz` | no | — | Pasta a varrer (padrao: .). |
| `dry_run` | no | — | So mostra o plano; nao roda nem grava nada. |
| `format` | no | — | sarif grava tambem o SARIF e o resumo de PR, como `report github`. |
| `fail_on` | no | — | Sai 1 se houver finding nesta severidade (P1 inclui P0). |
| `glue` | no | — | — |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `emr` | no | — | — |
| `databricks` | no | — | — |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## sdd

### `sdd`

**para que:** Confere os artefatos de spec em docs/sdd/<FEATURE>/<fase>.md: recusa por nome o que nao fecha, sem julgar a prosa.

- **por que:** confere a cadeia de artefatos de spec em docs/sdd/<FEATURE>/<fase>.md
- **quando usar:** gate de spec-driven development antes de build/ship

**Syntax**

```text
sparkforge-aws sdd [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `sdd check`

**para que:** Roda os gates. Sai 1 se houver recusa; lacuna sozinha sai 0.

- **por que:** confere a cadeia de artefatos de spec em docs/sdd/<FEATURE>/<fase>.md
- **quando usar:** gate de spec-driven development antes de build/ship

**Syntax**

```text
sparkforge-aws sdd check [help] <repo> [root] [feature]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | Raiz do repositorio. |
| `root` | no | — | Pasta dos artefatos, relativa a --repo. |
| `feature` | no | — | Confere so esta feature. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `sdd stamp`

**para que:** Grava upstream.sha256 do artefato. Escreve so a linha do hash.

- **por que:** confere a cadeia de artefatos de spec em docs/sdd/<FEATURE>/<fase>.md
- **quando usar:** gate de spec-driven development antes de build/ship

**Syntax**

```text
sparkforge-aws sdd stamp [help] <repo> [root] <path>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | Raiz do repositorio. |
| `root` | no | — | Pasta dos artefatos, relativa a --repo. |
| `path` | yes | — | Artefato, relativo a --repo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `sdd status`

**para que:** Fase atual de cada feature e o que a impede de avancar.

- **por que:** confere a cadeia de artefatos de spec em docs/sdd/<FEATURE>/<fase>.md
- **quando usar:** gate de spec-driven development antes de build/ship

**Syntax**

```text
sparkforge-aws sdd status [help] <repo> [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `repo` | yes | — | Raiz do repositorio. |
| `root` | no | — | Pasta dos artefatos, relativa a --repo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## simulate

### `simulate`

**para que:** O que uma mudanca de configuracao move, estruturalmente: altera o valor de facts que ja existem, rederiva e julga os dois lados, e diz que achados somem e aparecem. Nunca preve spill, tempo ou custo.

- **por que:** o que uma mudança de config move estruturalmente — sobre facts existentes
- **quando usar:** ensaiar impacto de config sem executar

**Syntax**

```text
sparkforge-aws simulate [help] <facts> <sets> [glue] [spark] [python] [iceberg] [athena] [emr] [databricks] [photon]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Facts do case. Repetivel. |
| `sets` | yes | — | camada:chave=valor, camada em tf, code, effective, emr. Repetivel. |
| `glue` | no | — | — |
| `spark` | no | — | — |
| `python` | no | — | — |
| `iceberg` | no | — | — |
| `athena` | no | — | — |
| `emr` | no | — | — |
| `databricks` | no | — | — |
| `photon` | no | — | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## status

### `status`

**para que:** Estado da instalacao (ledger + drift + health doc).

- **por que:** estado da instalação (ledger + drift + health doc)
- **quando usar:** ver se a instalação divergiu do manifesto

**Syntax**

```text
sparkforge-aws status [help] [scope] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scope` | no | — | — |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## telemetry

### `telemetry`

**para que:** Os spans de tool e o transcript do host em OTLP/JSON, para um OTLP Collector.

- **por que:** spans de tool e transcript do host em OTLP/JSON
- **quando usar:** exportar telemetria para um OTLP Collector

**Syntax**

```text
sparkforge-aws telemetry [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `telemetry export`

**para que:** Grava .sparkforge_aws/telemetry/<run_id>.traces.jsonl e .metrics.jsonl (nomes fixos), com gen_ai.* e mcp.* da semconv GenAI (Development). O Collector le com o receiver otlp_json_file. Nao chama rede; token so com transcript do host.

- **por que:** spans de tool e transcript do host em OTLP/JSON
- **quando usar:** exportar telemetria para um OTLP Collector

**Syntax**

```text
sparkforge-aws telemetry export [help] <run_id> [host_transcript] [provider] [repo]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `run_id` | yes | — | — |
| `host_transcript` | no | — | Transcript JSONL do host, quando houver: vira o span invoke_agent com tokens. |
| `provider` | no | — | Provider do host (gen_ai.provider.name), DECLARADO: anthropic, aws.bedrock, gcp.vertex_ai. Sem ele o atributo fica em unresolved e a metrica de token nao sai. |
| `repo` | no | — | Raiz do repositorio. A saida vai para <repo>/.sparkforge_aws/telemetry/. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## tune

### `tune`

**para que:** Configuracao Spark derivada da medida, com a procedencia de cada propriedade. Nunca aplica a mudanca.

- **por que:** configuração Spark derivada da medida, com provenance — nunca aplica
- **quando usar:** obter config recomendada com evidência, sem mutação

**Syntax**

```text
sparkforge-aws tune [help] <facts> [out] [headroom]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (--out de analyze). |
| `out` | no | — | Escreve o relatorio completo (JSON) neste arquivo. |
| `headroom` | no | — | Folga declarada sobre o piso de memoryOverhead e de broadcastTimeout (0.2 = +20%%). Sem ela, o piso. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## uninstall

### `uninstall`

**para que:** Remove so o que o manifesto declara como gerenciado.

- **por que:** remove só o que o manifesto declara como gerenciado
- **quando usar:** desinstalação honesta e delimitada

**Syntax**

```text
sparkforge-aws uninstall [help] [scope] [host] [root] [purge] [dry_run]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `scope` | no | — | — |
| `host` | no | — | — |
| `root` | no | — | — |
| `purge` | no | — | Apaga tambem o state dir .sparkforge_aws/install. |
| `dry_run` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## update

### `update`

**para que:** Atualiza o runtime instalado pelo bootstrap.

- **por que:** atualiza o runtime instalado pelo bootstrap
- **quando usar:** manter a distribuição instalada atual

**Syntax**

```text
sparkforge-aws update [help] [to] [repo] [dry_run]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `to` | no | — | Versao pinned (nunca 'latest'). |
| `repo` | no | — | Checkout para instalar/atualizar. |
| `dry_run` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## validate

### `validate`

**para que:** Valida findings contra o JSON Schema e a regra de ganho sem benchmark_ref.

- **por que:** valida findings contra JSON Schema + regra de ganho
- **quando usar:** conformidade estrutural de findings antes de consumir

**Syntax**

```text
sparkforge-aws validate [help] <findings> [facts]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `findings` | yes | — | — |
| `facts` | no | — | Opcional. Arquivo de facts (tipicamente `sparkforge-aws benchmark --out`). Sem ele, `benchmark_ref` so e cobrado na FORMA (`f_` + 6 hex); com ele, o `fact_id` citado precisa existir no conjunto -- achado que cita medicao ausente da evidencia passa a ser rejeitado. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## workload

### `workload`

**para que:** Perfil de workload por eixos, a partir de facts ja extraidos.

- **por que:** perfil de workload por eixos, a partir de facts
- **quando usar:** caracterizar a carga para orientar capacidade/tune

**Syntax**

```text
sparkforge-aws workload [help] <facts> <job_name> <job_run> [history] [out]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `facts` | yes | — | Arquivo de facts (--out de analyze). |
| `job_name` | yes | — | — |
| `job_run` | yes | — | Id do run que este perfil descreve. |
| `history` | no | — | Diretorio com um arquivo de facts por run anterior (`analyze glue-job-runs --out`), para a escala. |
| `out` | no | — | Escreve o fingerprint completo (JSON) neste arquivo. |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

## workspace

### `workspace`

**para que:** Workspace virtual declarado e descoberta limitada.

- **por que:** workspace virtual declarado e descoberta limitada
- **quando usar:** trabalhar multi-projeto dentro de um workspace declarado

**Syntax**

```text
sparkforge-aws workspace [help]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `workspace add`

**para que:** Portable workspace add.

- **por que:** workspace virtual declarado e descoberta limitada
- **quando usar:** trabalhar multi-projeto dentro de um workspace declarado

**Syntax**

```text
sparkforge-aws workspace add [help] [root] [name] <repository>
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `name` | no | — | — |
| `repository` | yes | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `workspace discover`

**para que:** Portable workspace discover.

- **por que:** workspace virtual declarado e descoberta limitada
- **quando usar:** trabalhar multi-projeto dentro de um workspace declarado

**Syntax**

```text
sparkforge-aws workspace discover [help] [root] [max_depth] [max_directories]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `max_depth` | no | — | — |
| `max_directories` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `workspace init`

**para que:** Portable workspace init.

- **por que:** workspace virtual declarado e descoberta limitada
- **quando usar:** trabalhar multi-projeto dentro de um workspace declarado

**Syntax**

```text
sparkforge-aws workspace init [help] [root] [name]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |
| `name` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `workspace status`

**para que:** Portable workspace status.

- **por que:** workspace virtual declarado e descoberta limitada
- **quando usar:** trabalhar multi-projeto dentro de um workspace declarado

**Syntax**

```text
sparkforge-aws workspace status [help] [root]
```

| argument/flag | required | default | description |
|---|---|---|---|
| `help` | no | — | show this help message and exit |
| `root` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->
