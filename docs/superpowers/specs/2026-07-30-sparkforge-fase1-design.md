# SparkForge AWS — Fase 1: Extratores Restantes e Coletores AWS

**Data do documento:** 2026-07-31
**Data da implementação:** 2026-07-30 a 2026-07-31
**Status:** implementado
**Faixa de commits:** `97b0818` … `bb72f9f`
**Depende de:** contratos da [Fase 0](2026-07-29-sparkforge-fase0-design.md)

> **Documento retroativo.** Escrito depois da implementação, a partir dos commits
> e do código. Não foi um spec aprovado antes do trabalho — o escopo veio da §16
> do spec da Fase 0, e as decisões abaixo foram tomadas commit a commit. Está
> aqui porque uma fase entregue sem registro de decisão obriga a próxima sessão a
> reconstruir o raciocínio a partir do diff.

---

## 1. Problema

A Fase 0 provou o contrato inteiro com **um** extrator: `pyspark_ast`. O efeito
colateral é que o catálogo committado — 43 regras em 7 áreas — nascera quase todo
inerte. Só SF-PY (12) e SF-ENV (4) tinham como disparar. As outras 27 regras
exigiam `requires_facts` de kinds que nenhum extrator emitia: `spark.stage.*`,
`tf.*`, `iceberg.*`, `sql.*`, `athena.*`, `catalog.*`.

Uma regra inerte é pior que uma regra ausente. Sem marcação, `judge` reporta
"`requires_facts` não satisfeito" e o operador entende "colete o artefato" —
quando a verdade é "ninguém construiu o extrator". A Fase 0 mitigou isso com o
campo `blocked_on` (commits `e0be155`, `8106d8f`), que é honesto mas continua
sendo uma promessa não cumprida.

Segundo problema: sem coletores, todo artefato tinha que chegar à mão. A §4.2 da
Fase 0 previu `collect/`, mas entregou só a interface (`base.py`, Task 22).

## 2. Objetivo

Construir os extratores que faltavam e os coletores AWS, de modo que cada regra
do catálogo passe a depender de **coleta**, nunca de código faltando.

Critério de sucesso: o número de regras com `blocked_on` cai monotonicamente, e
toda queda é acompanhada da fixture que prova a regra disparando.

## 3. Decisões

| # | Decisão | Alternativa rejeitada | Razão |
|---|---|---|---|
| F1-D1 | Extratores leem **dumps já coletados**, não a AWS | Extrator chama boto3 direto | Mantém a fronteira negativa da §4.2: extrator é puro, sem rede. Offline-first (§D2 da Fase 0) sobrevive |
| F1-D2 | Coletores AWS num extra opcional `[aws]` | boto3 no núcleo | Devin CLI, CI e sandbox rodam `analyze` sem credencial |
| F1-D3 | Etapa de **fusão** separada dos extratores | Extrator de SQL consulta o catálogo | Correlacionar SQL com schema do Glue exige dois artefatos. Fundir dentro de um extrator quebraria "entrada: um artefato local" |
| F1-D4 | Todo extrator emite um kind sentinela `*_analyzed` | Ausência de fact = ausência do problema | Sem sentinela, uma condição `absent:` é vacuamente verdadeira em qualquer artefato nunca analisado. É a diferença entre "não há spill" e "não olhei o event log" |
| F1-D5 | Todo extrator emite `*.unresolved` | Silêncio no ponto cego | Herdado da §6.2 da Fase 0. Cobertura honesta é o que impede modelo fraco de inflar confiança |
| F1-D6 | Truncamento **suprime** o sumário, não o estima | Emitir sumário parcial | `IsTruncated: true` no S3 e `... N more fields` no plano físico produziriam `file_count` e `avg_bytes` de uma página apresentados como total |
| F1-D7 | Teto `mcp>=1.0,<2` | Range aberto | O SDK 2.x removeu os decoradores `@server.list_tools()` / `@server.call_tool()`. Instalação limpa quebrava no import, em todas as plataformas |

## 4. Extratores entregues

Doze módulos novos em `sparkforge/facts/`, além de `pyspark_ast` e
`runtime_detect` (que vieram na Fase 0). Cada um declara `EMITTED_KINDS`, o que
alimenta o teste de alcançabilidade do catálogo.

| módulo | entrada | kinds | desbloqueia |
|---|---|---|---|
| `event_log` | Spark event log (JSON Lines) | 11 — `spark.stage.{task_duration,task_count,task_input,spill,gc}`, `spark.executor.{lost,memory_usage}`, `spark.job.spill_summary`, `spark.cluster.cores`, `spark.log_analyzed`, `spark.unresolved` | SF-UI |
| `terraform` | HCL de `aws_glue_job` | 6 — `tf.{resource,attribute,module_analyzed,unresolved}`, `tf.observability.{spark_ui,unknown}` | SF-GLUE |
| `iceberg_metadata` | dump JSON das metadata tables | 8 — `iceberg.{files,delete_files,snapshots,manifests,partitions}_summary`, `iceberg.{table_property,table_analyzed,unresolved}` | SF-ICE |
| `sql_literal` | `spark.sql("...")` e arquivos `.sql` | 4 — `sql.{predicate,projection,analyzed,unresolved}` | SF-ATH (via fusão) |
| `call_graph` | Facts já extraídos | 4 — `callgraph.{function,summary,cycle,reachable_spark_work}` | análise de biblioteca |
| `catalog_schema` | dump do Glue Data Catalog | 6 — `catalog.{table_schema,table_partitions,table_property,analyzed,unresolved}`, `catalog.table_property.projection_enabled` | SF-PQ-005, fusão |
| `athena_workgroup` | dump de `get_work_group` | 3 — `athena.{workgroup,analyzed,unresolved}` | SF-ATH-001 |
| `spark_plan` | `df.explain()` / `EXPLAIN` | 8 — `plan.{operator,file_scan,join,exchange,python_udf,aqe,analyzed,unresolved}` | SF-PQ-002, SF-PQ-004 |
| `fusion` | facts de SQL × facts de catálogo | 4 — `sql.{predicate,projection}.enriched`, `sql.predicate.partition_filter`, `fusion.summary` | SF-ATH-002/003 |
| `s3_listing` | `s3api list-objects-v2` | 3 — `s3.{prefix_summary,analyzed,unresolved}` | SF-PQ-001/003/005 |
| `consumers` | inventário declarado, escrito por pessoa | 3 — `env.{consumer,consumers_analyzed,unresolved}` | SF-ENV-002 |
| `terraform.extract_terraform_diff` | dois diretórios de HCL | reusa `tf.*` com `attrs.changed` | revisão de PR de infra |

Total após a fase: **80 fact kinds distintos**.

### 4.1 Decisões de extrator que carregam valor

**`s3_listing` agrupa por (formato, compressão).** Um prefixo real mistura
Parquet com `_SUCCESS`, log `.gz` e CSV de carga inicial. Um sumário único
diluiria um `.gz` de 4 GB na média do Parquet e SF-PQ-003 (texto gzip não
splitável) nunca casaria.

**`spark_plan` não infere pruning a partir de ausência.** `PartitionFilters`
vazio num plano truncado não é "não há pruning"; é "não vi". O extrator marca
`partition_status_unknown` e a regra tem condição separada para isso.

**`consumers` é o único extrator que lê arquivo escrito por uma pessoa.**
Deliberado: derivar consumidores do histórico de queries do Athena veria só o
Athena, com retenção limitada, e um consumidor Redshift ou EMR invisível viraria
"sem consumidor". Tabela ausente do inventário não produz fact — ausência de
declaração não é declaração de ausência.

**`extract_terraform_diff` devolve só o lado DEPOIS.** Devolver os dois lados
faria toda regra contar cada recurso duas vezes e acusar o estado antigo, que
ninguém pode mais consertar.

## 5. Coletores AWS

`sparkforge/collect/aws.py`, extra `[aws]`. Cinco coletores, todos offline-first:
se o arquivo já existe no path canônico e o sha256 confere, é no-op.

| coletor | fonte | armadilha tratada |
|---|---|---|
| `collect_event_log` | S3 | listagem paginada — `list_objects_v2` trunca em 1000 |
| `collect_glue_job` | `glue.get_job` | — |
| `collect_cloudwatch` | `GetMetricData` | `Stat` correto por métrica; média de um `Maximum` mente |
| `collect_iceberg_metadata` | query Athena nas metadata tables | Lake Formation nega e a mensagem não diz isso — o erro é nomeado |
| `collect_athena_workgroup` | `athena.get_work_group` | — |

`collect verify` recomputa o sha256 do manifest e falha quando o artefato mudou
por baixo.

`openWorldHint: true` nesses tools, `false` no resto — a §7.1 da Fase 0 previa
exatamente isso.

## 6. Superfície

- **CLI:** 12 subverbos de `analyze` (`pyspark`, `catalog-schema`, `event-log`,
  `plan`, `terraform`, `terraform-diff`, `iceberg`, `sql`, `athena-workgroup`,
  `s3-listing`, `consumers`, `call-graph`), 6 de `collect`, mais `fuse`.
- **MCP:** **28 tools**, cada uma com `outputSchema` e retorno de
  `structuredContent`.
- `parity.yaml` e `manifest.json` acompanham; `test_docs_coverage` compara
  `manifest["tools"]` com `TOOLS.keys()` e falha se divergirem.

## 7. Auditoria de fechamento (`bb72f9f`)

Seis defeitos encontrados ao auditar a fase, três capazes de derrubar ou mentir
em produção. Registrados aqui porque cada um gerou uma guarda permanente.

1. **Transporte HTTP do MCP estava quebrado.** `_run_http` chamava
   `StreamableHTTPServerTransport()` sem argumento obrigatório e um método
   `asgi_app` que nunca existiu. O caminho era `# pragma: no cover` e
   `parity.yaml` já declarava `mcp` para `devin_desktop` — a paridade com Devin
   Desktop era afirmação, não fato. Corrigido com
   `StreamableHTTPSessionManager` + Starlette, session manager amarrado ao
   lifespan, e teste que constrói servidor e app e entra no lifespan sem abrir
   porta.
2. **`build_server()` quebrava com SDK novo** — origem de F1-D7.
3. **Falso positivo P1 em Terraform.** `_check_observability` exigia
   `--spark-event-logs-path` literal; valor interpolado — a forma normal de
   escrever Terraform, porque só existe depois do apply — fazia SF-GLUE-002
   acusar observabilidade ausente num job que a tem. Novo kind
   `tf.observability.unknown` e segunda condição na regra. Ausência de evidência
   não é evidência de ausência.
4. **Cobertura de corpus.** 17 fact kinds não apareciam em golden nenhum, entre
   eles `env.runtime_signal` (alimenta SF-ENV-001, P0) e os quatro
   `*.unresolved`, que são a maquinaria de ponto cego — quando ela para de
   contar, devolve zero sem levantar erro. Passou a 72 de 72, travado por
   `tests/test_fixtures_kind_coverage.py`.
5. **Glue 4.0 / 5.0 / 5.1.** `knowledge/glue/runtime-matrix.md` passa a ser
   parseada e comparada com `GLUE_MATRIX` — fixar literais no teste pega mudança
   acidental no código, não código e documento se afastando, e é o documento que
   o agente lê. Fronteira do AQE provada dos dois lados (Glue 3.0 dispara
   SF-ENV-004, 4.0 não); SF-ENV-002 (Iceberg format V3, que o Athena não lê)
   travada em 5.1 e só 5.1.
6. **Path traversal em `scripts/install_skills.py`.** Quatro achados do Snyk,
   todos de argv fluindo para escrita. A instalação passa a escrever no diretório
   atual e `--target` vira confirmação explícita comparada como texto, sem
   chegar a chamada de filesystem. `install_dest` recusa componente `..`,
   caminho absoluto e escape por symlink no destino resolvido.

## 8. Estado ao fim da fase

43 regras, **5 ainda com `blocked_on`**, 1621 testes. O que sobrou virou o escopo
da fase seguinte — ver [Fase 2](2026-07-31-sparkforge-fase2-design.md).

## 9. Riscos assumidos

| risco | mitigação |
|---|---|
| Extrator de dump depende do formato do dump da AWS mudar | Fixture golden com o dump real capturado; `*.unresolved` para entrada não reconhecida |
| Fusão correlaciona por nome de tabela, que pode colidir entre databases | `fusion.summary` reporta o que não casou; regra ancorada por tabela do catálogo (`649856f`) |
| Coletor AWS grava credencial acidentalmente | Nenhuma credencial vai para case ou manifest; teste dedicado |
| Cinco regras ainda inertes ao fim da fase | `blocked_on` explícito + teste que falha se um `blocked_on` sobreviver ao extrator que o resolveu |
