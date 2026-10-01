# SparkForge Fase 1 Implementation Plan

> **Status: CONCLUÍDO em 2026-07-31.** Documento **retroativo**: reconstruído a
> partir dos commits e do código depois da entrega, não escrito antes do
> trabalho. As tasks abaixo agrupam commits reais; os checkboxes já estão
> marcados porque descrevem o que aconteceu. Não re-execute.
>
> Estado corrente do repositório: [`../STATUS.md`](../STATUS.md).
> Decisões desta fase: [`../specs/2026-07-30-sparkforge-fase1-design.md`](../specs/2026-07-30-sparkforge-fase1-design.md).

**Goal:** construir os extratores e coletores que faltavam para que cada regra do
catálogo dependa de **coleta**, nunca de código faltando — levando o repositório
de 1 extrator e 16 regras vivas para 13 extratores e 38 regras vivas.

**Architecture:** herda as seis camadas e as fronteiras negativas da Fase 0.
Nenhum extrator novo chama rede; todos leem artefato local. Coleta fica isolada
em `collect/aws.py`, extra `[aws]`. A correlação entre dois artefatos vira uma
etapa própria (`facts/fusion.py`) em vez de vazar para dentro de um extrator.

**Tech Stack:** Python stdlib (`ast`, `json`, `re`, `hashlib`), PyYAML,
jsonschema, pytest. Extras: boto3 (`[aws]`), `mcp>=1.0,<2` + starlette + uvicorn
(`[mcp]`).

**Faixa de commits:** `97b0818` … `bb72f9f`, em cinco merges.

---

## Fatos do ambiente no início da fase

- 43 regras committadas, **27 inertes** — `requires_facts` sem extrator.
- Único extrator: `pyspark_ast` (19 kinds).
- 16 fixtures, ~500 testes.
- `blocked_on` já existia como marcação honesta (Fase 0, `e0be155`/`8106d8f`),
  mas sem teste que impedisse um `blocked_on` obsoleto de sobreviver.

---

## Task 1 — Extrator de Spark event log

Commits: `97b0818`, mais `spark.job.spill_summary` e
`spark.executor.memory_usage` adicionados depois em `081a570`.

- [x] `sparkforge/facts/event_log.py` lendo JSON Lines, sem carregar o arquivo inteiro em memória
- [x] 11 kinds: `spark.stage.{task_duration,task_count,task_input,spill,gc}`, `spark.executor.{lost,memory_usage}`, `spark.job.spill_summary`, `spark.cluster.cores`, `spark.log_analyzed`, `spark.unresolved`
- [x] Sentinela `spark.log_analyzed` — sem ela, condição `absent:` é vacuamente verdadeira em log nunca lido
- [x] Desbloqueia a área SF-UI (6 regras)
- [x] `tests/test_facts_event_log.py` + `fixtures/eventlog/skewed_stage/`

## Task 2 — Extrator de Terraform HCL

Commits: `a5cf468`, `74ac494`, `a038a46`, correção de falso positivo em `bb72f9f`.

- [x] `sparkforge/facts/terraform.py` parseando `aws_glue_job` sem executar terraform
- [x] 6 kinds: `tf.{resource,attribute,module_analyzed,unresolved}`, `tf.observability.{spark_ui,unknown}`
- [x] `tf.observability.unknown` para valor interpolado: **ausência de evidência não é evidência de ausência**. Sem isso SF-GLUE-002 acusava observabilidade ausente num job que a tem
- [x] SF-GLUE-002 ancorada por recurso `aws_glue_job` (`a038a46`), não pelo módulo
- [x] Desbloqueia a área SF-GLUE (6 regras)

## Task 3 — `outputSchema` real por tool no MCP

Commits: `4e32fdc`, `7ecc14e`, `5728fd0`.

- [x] Cada tool declara o schema de saída que realmente produz
- [x] Toda tool falível declara também a forma do erro
- [x] Merge `b2e8ed9` fecha a parte um

## Task 4 — Extrator de metadata tables Iceberg

Commit: `f0e791c`.

- [x] `sparkforge/facts/iceberg_metadata.py` lendo dump JSON de `.files`, `.delete_files`, `.snapshots`, `.manifests`, `.partitions`
- [x] 8 kinds, incluindo `iceberg.table_analyzed` (sentinela) e `iceberg.unresolved`
- [x] Distingue data files, delete files, manifests e snapshots — exigência 9 do `CLAUDE.md`
- [x] Desbloqueia a área SF-ICE (5 regras)
- [x] `fixtures/iceberg/` — 8 fixtures, incluindo `healthy_table` como metade negativa

## Task 5 — Extrator de SQL literal

Commit: `83eca13`.

- [x] `sparkforge/facts/sql_literal.py` lendo `spark.sql("...")` de código PySpark e arquivos `.sql` avulsos
- [x] 4 kinds: `sql.{predicate,projection,analyzed,unresolved}`
- [x] SQL montado por concatenação vira `sql.unresolved`, não silêncio

## Task 6 — Construtor de call graph

Commit: `737d072`.

- [x] `sparkforge/facts/call_graph.py` operando sobre Facts já extraídos, não sobre AST — a fronteira da §4.2 vale para dentro
- [x] 4 kinds: `callgraph.{function,summary,cycle,reachable_spark_work}`
- [x] Detecção de ciclo, incluindo recursão mútua (`fixtures/callgraph/mutual_recursion/`)

## Task 7 — Coletores AWS

Commits: `f15e443`, `2b88243`, `61c1db4`, `1019d0f`.

- [x] `sparkforge/collect/aws.py`, extra `[aws]`, cinco coletores offline-first
- [x] `collect_event_log`, `collect_glue_job`, `collect_cloudwatch`, `collect_iceberg_metadata`, `collect_athena_workgroup`
- [x] Verbos `collect` na CLI + `collect verify` que recomputa sha256
- [x] `Stat` correto por métrica no CloudWatch (`61c1db4`) — média de um `Maximum` mente
- [x] Listagem S3 paginada (`1019d0f`) — `list_objects_v2` trunca em 1000
- [x] Negação do Lake Formation nomeada no erro; a mensagem da AWS não diz o que é
- [x] Merge `0c14bb4` fecha a parte dois

## Task 8 — Glue Catalog schema e fusão de facts

Commits: `9c9797b`, `927e64a`, `64bcf1f`, `14119ad`, `67227e2`, `649856f`.

- [x] `sparkforge/facts/catalog_schema.py` — 6 kinds a partir de dump `GetTables`/`GetTable`
- [x] `sparkforge/facts/fusion.py` — correlaciona `sql.projection`/`sql.predicate` com `catalog.table_schema` pelo nome da tabela
- [x] 4 kinds de fusão: `sql.{predicate,projection}.enriched`, `sql.predicate.partition_filter`, `fusion.summary`
- [x] Desbloqueia SF-ATH-002 e SF-ATH-003
- [x] SF-ATH-002 ancorada por localização da query, SF-ATH-003 por tabela do catálogo — sem isso um Finding por arquivo esconde qual query é o problema

## Task 9 — Extrator de workgroup do Athena e superfície completa

Commits: `da6b84b`, `edf85b4`, `104d90b`, `15769d0`.

- [x] `sparkforge/facts/athena_workgroup.py` — 3 kinds
- [x] Verbo `analyze` para **todo** extrator na CLI
- [x] Tools `collect`, `fuse` e `analyze` expostas no MCP
- [x] `parity.yaml` atualizado com `openWorldHint: true` para os coletores
- [x] Merge `4e985a8` fecha a parte três

## Task 10 — Skills reescritas toolkit-first

Commits: `e4c4431`, `6c7b32a`, `e16eaea`, `47035ed`.

- [x] Skills de análise de código passam a chamar as tools em vez de descrever leitura por amostragem
- [x] `analyze-spark-ui` reescrita sobre `analyze event-log`
- [x] Catálogo e skills alinhados às novas semânticas de `judge`

## Task 11 — Semântica de `judge` e mascaramento por `absent`

Commits: `d38f407`, `5f5a8c7`, `4c433b5`, `db910aa`.

- [x] Um Finding por `subject` em regra `same_subject` (`5f5a8c7`) — antes, N ocorrências viravam um Finding e o operador perdia N-1 âncoras
- [x] `judge --facts` repetível, para julgar facts de vários extratores numa passada
- [x] `tests/test_rules_catalog_reachability.py`: regra que exige kind sem extrator **precisa** declarar `blocked_on`, e `blocked_on` que sobrevive ao extrator quebra o teste
- [x] Golden multi-entidade provando que `absent:` não mascara entidade vizinha
- [x] Merge `762dde1` fecha a parte quatro

## Task 12 — Parser de plano físico Spark

Commits: `15d2817`, `fd53869`, `8ed630b`, `b8209ca`, `33d06fa`.

- [x] `sparkforge/facts/spark_plan.py` com ancoragem por nó do plano — 8 kinds
- [x] Semântica de `PartitionFilters` conferida na fonte do Spark (`fd53869`), não inferida
- [x] Plano truncado (`... N more fields`) não vira sumário: `plan.unresolved`
- [x] `analyze plan` na CLI, no MCP e no `parity.yaml`
- [x] Desbloqueia SF-PQ-002 e SF-PQ-004

## Task 13 — Auditoria de fechamento

Commit: `bb72f9f`.

- [x] **Transporte HTTP do MCP consertado** — `build_http_app()` com `StreamableHTTPSessionManager` + Starlette, session manager no lifespan. Antes: `# pragma: no cover` sobre código que não funcionava, com `parity.yaml` afirmando paridade com Devin Desktop
- [x] Teto `mcp>=1.0,<2` — o 2.x removeu os decoradores e instalação limpa quebrava no import em todas as plataformas
- [x] Falso positivo P1 do Terraform fechado com `tf.observability.unknown`
- [x] `athena_workgroup` ganha 49 testes e 3 fixtures — era o único extrator sem teste semântico
- [x] Cobertura de kinds: 72 de 72 em golden, travado por `tests/test_fixtures_kind_coverage.py`
- [x] `knowledge/glue/runtime-matrix.md` parseada e comparada com `GLUE_MATRIX`; fronteira do AQE provada dos dois lados; SF-ENV-002 travada em Glue 5.1 e só 5.1
- [x] Path traversal em `scripts/install_skills.py` fechado — `--target` vira confirmação textual, `install_dest` recusa `..`, caminho absoluto e escape por symlink

---

## Resultado

| | Início | Fim |
|---|---|---|
| Extratores | 1 | 13 |
| Fact kinds | 19 | 72 (80 após a Fase 2) |
| Regras vivas | 16 | 38 |
| Regras com `blocked_on` | 27 | 5 |
| Tools MCP | 10 | 25 |
| Fixtures | 16 | ~56 |
| Testes | ~500 | 1621 |

As 5 regras restantes viraram o escopo da fase seguinte:
[`2026-07-31-sparkforge-fase2.md`](2026-07-31-sparkforge-fase2.md).
