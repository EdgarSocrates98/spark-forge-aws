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
| [`emr/cluster-configuration.md`](emr/cluster-configuration.md) | Instance groups × fleets, níveis de `Configurations`, `maximizeResourceAllocation`, Spot por papel, managed scaling × alocação dinâmica, committer × commit protocol em S3, `LogUri`, node labels e o ApplicationMaster, bootstrap actions |

### Amazon EMR Serverless
| Arquivo | Conteúdo |
|---|---|
| [`emr-serverless/runtime-matrix.md`](emr-serverless/runtime-matrix.md) | O que a fonte do Serverless publica por release — **só Spark, Hive e Tez** — e por que isso resolve a D-5 da Fase 5d como "`EMR_MATRIX` não se reaproveita". Comparação release a release contra o EC2, as seis releases que só o EC2 tem, e os dois release labels fora da forma `emr-X.Y.Z` |
| [`emr-serverless/application-configuration.md`](emr-serverless/application-configuration.md) | A definição de uma application (`get-application`): tipos reais dos campos, o conjunto **fechado** de unidades de `cpu`/`memory`/`disk`, o faturamento de capacidade pré-inicializada com a application `STARTED`, auto-stop, os três destinos de log e o default que muda a forma da regra, e `EMR.secret@` no `runtimeConfiguration`. Traz o placar das cinco regras candidatas |

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

### Validação de dados
| Arquivo | Conteúdo |
|---|---|
| [`dq/validation-frameworks.md`](dq/validation-frameworks.md) | Superfície pública corrente de Great Expectations e PyDeequ, alcance de versões contra `GLUE_MATRIX`/`EMR_MATRIX`, o que a fonte primária garante sobre passadas sobre o dado, e `assert` sob `python -O`. Traz o bloco de **vetos** que o catálogo `SF-DQ` cita |

### Grafo com Spark
| Arquivo | Conteúdo |
|---|---|
| [`graph/graphframes-api.md`](graph/graphframes-api.md) | Superfície pública do GraphFrames nas **duas linhagens** (`graphframes` até 0.8.4, `io.graphframes` de 0.9.0 em diante): construção, colunas obrigatórias `id`/`src`/`dst`, vocabulário real de algoritmos, e as duas perguntas que decidem regra — checkpoint em `connectedComponents` é **exigência** e o algoritmo **falha** com `java.io.IOException`; `maxIter` **não** tem default único e em nenhum algoritmo a ausência é defeito. Traz o bloco de **vetos** `V-GF-*` |
| [`graph/availability.md`](graph/availability.md) | Matriz GraphFrames × Spark × Glue/EMR: as **nove células sem jar nenhum** (Glue 4.0 e EMR 6.8.0–6.11.1, todas Spark 3.3), o piso de Python 3.10 de `graphframes-py`, e as listas da AWS onde GraphFrames **não** aparece. Traz o bloco de **vetos** `V-AV-*` |

### Plataformas de agente
| Arquivo | Conteúdo |
|---|---|
| [`devin/agents-and-subagents.md`](devin/agents-and-subagents.md) | Superfície oficial de **agents e subagents do Devin** (CLI e Devin Local): diretórios de descoberta, frontmatter literal, importação de `.claude/agents/*.md`, `.agents/skills/`, modelo default por router, `max-nesting`, `subagents_enabled`, MCP e atalhos. Traz o bloco de **vetos** `V-DV-*` e o que isso faz com a nota de `parity.yaml` |

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

Cada arquivo declara `Fontes` com URL e data de coleta no rodapé. Coleta desta rodada: **2026-07-29**; `emr/` foi coletado em **2026-08-01**, `dq/` em **2026-08-03**, `devin/` e `emr-serverless/` em **2026-08-04**, e `graph/` em **2026-08-05**.

**A seção `Fontes` de cada arquivo daqui é vigiada.** `scripts/refresh_knowledge.py::watchlist` deriva a lista de URLs de **duas** origens, e nenhuma das duas é mantida à mão: `sources[].url` das regras do catálogo (campo `rules` no lock) e as URLs que aparecem nos blocos `Fontes` destas páginas (campo `docs`). `tests/test_refresh_knowledge.py::test_the_committed_lock_matches_the_watchlist` exige igualdade exata entre o lock e a união das duas.

Até 2026-08-05 a origem era **só o catálogo**, e o efeito ninguém tinha medido: conhecimento que nenhuma regra cita nunca entrava. O caso que fechou a dívida foi `devin/agents-and-subagents.md` — ela não sustenta regra nenhuma, sustenta **perfil de agente**, e as 24 URLs de `docs.devin.ai` envelheciam sem alarme sobre uma superfície que a própria fonte declara experimental. O lock foi de **51 para 109** fontes: 58 entraram por `knowledge/` e nenhuma delas tem hash ainda, porque hash só se escreve depois de ler a página. A próxima conferência com rede as relata como **NOVA**, que é a verdade.

O **vínculo de volta** é o que impede a segunda origem de virar ruído: toda entrada do lock nomeia pelo menos um consumidor — regra, página, ou as duas —, e o relatório imprime os dois. URL citada pelas duas com `retrieved` diferentes carrega **as duas datas**, para que a divergência apareça em vez de ser resolvida por chute.

Duas convenções do rodapé, e as duas têm razão medida: o bloco é o heading cujo texto é exatamente `Fontes` (o `## Fontes e frescor` desta página fala *sobre* o mecanismo e não é origem), e URL dentro de crase é **padrão, não citação** — a §2 de `emr-serverless/runtime-matrix.md` escreve `release-version-<N>.html` para descrever 24 páginas, e vigiar esse texto daria 404 permanente.

Sem rede: `python scripts/refresh_knowledge.py --update --offline` alinha o conjunto do lock (entra fonte nova sem hash, sai fonte que ninguém cita mais) sem carimbar conferência nenhuma.

Conhecimento aqui **não substitui** a documentação do runtime real. Quando o job em análise contradiz esta base, o runtime ganha e a base é corrigida.
