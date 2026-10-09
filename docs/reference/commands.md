# `sparkforge-aws` command reference

Generated from the real CLI parser by `doc_inventory.py` + `doc_reference.py`. Do not hand-edit generated sections — write between `keep:start`/`keep:end` markers. Status vocabulary: `available` unless marked otherwise.

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

## handoff

### `handoff`

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

**Syntax**

```text
sparkforge-aws install [help] [scope] [host] [profile] [gateway_profile] [root] [yes] [dry_run]
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
| `dry_run` | no | — | — |

<!-- keep:start -->
_free notes — errors, examples, next steps (hand-written, preserved)_
<!-- keep:end -->

### `install doctor`

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
