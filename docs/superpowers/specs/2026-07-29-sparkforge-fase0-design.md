# SparkForge AWS — Fase 0: Contratos, Extração Determinística e Paridade Devin ↔ Claude

**Data:** 2026-07-29
**Status:** implementado em 2026-07-30. Ver §18 para os desvios entre o que esta spec projetou e o que foi entregue.
**Escopo:** Fase 0 de 5. Fases 1–4 estão no roadmap ao final, fora do escopo de implementação desta spec.

> **Aviso de leitura.** As seções 1–17 estão preservadas como foram aprovadas em
> 2026-07-29 — são o registro da decisão, não a descrição do repositório atual.
> Vários números aqui (17 kinds, 12 regras, 10 tools, 16 fixtures) foram
> superados pela própria Fase 0 e pelas Fases 1 e 2. **§18 lista cada desvio.**
> Para o estado corrente do sistema, leia [`../STATUS.md`](../STATUS.md).

---

## 1. Contexto e problema

O SparkForge AWS hoje é um pacote de 18 Agent Skills em markdown (~2,5–3,5 KB cada), 3 agentes Claude com prompt de 3 linhas, ~766 linhas de knowledge/checklists/templates/scripts, espelhado em `.claude/`, `.agents/` (Devin) e `.github/` (Copilot).

O pacote **descreve** o que investigar. Ele não **extrai** nada. Isso produz três problemas concretos:

1. **Qualidade acoplada ao modelo.** Toda evidência é lida e julgada pelo LLM a partir de prosa. Trocar Opus por Sonnet, ou Claude por Devin, muda quais anti-patterns são encontrados, quais limiares são aplicados e quais números são citados.
2. **Análise não é linha a linha.** Sem parsing, "revise o código" é leitura por amostragem. Não há garantia de cobertura nem de âncora (`file:line:col`), e não há como distinguir "não existe o problema" de "o modelo não olhou aquele arquivo".
3. **Sem paridade nem retomada.** Devin e Claude Code rodam em máquinas diferentes, sem contexto compartilhado. Hoje trocar de ferramenta no meio de uma investigação significa recomeçar. Já existe drift entre as cópias: `.claude/agents/spark-performance-architect.md` e `.github/agents/spark-performance-engineer.agent.md` têm nomes e conteúdos diferentes.

Existe também dívida de conhecimento: `knowledge/` tem 134 linhas de prosa sem limiar versionado, sem URL de fonte e sem data de coleta, o que torna impossível auditar se uma recomendação vale para Glue 4.0 (Iceberg 1.0.0) ou apenas para Glue 5.1 (Iceberg 1.10.0).

## 2. Objetivo da Fase 0

Estabelecer os contratos que as Fases 1–4 herdam, e provar cada um deles com **um** analisador funcionando ponta a ponta pelos quatro canais de acesso.

Critério de sucesso: dois operadores usando modelos diferentes, em ferramentas diferentes, sobre o mesmo repositório, produzem os **mesmos** facts, os **mesmos** findings e o **mesmo** próximo passo. A narrativa e o código proposto podem variar; a evidência e o roteamento não.

### Não-objetivos da Fase 0

Explicitamente fora de escopo, com a fase que os cobre:

| Fora de escopo | Fase |
|---|---|
| Parser de Spark event log | 1 |
| Parser de Terraform HCL | 1 |
| Leitor de metadata tables Iceberg | 1 |
| Parser do SQL literal de `spark.sql(...)` | 1 |
| Call graph completo da biblioteca | 1 |
| `refresh_knowledge` (harvest de docs oficiais) | 2 |
| Export de Playbook/Knowledge para conta Devin | 3 |
| Gates fail-closed no roteamento | 4 |
| Coletores AWS além do esqueleto de interface | 1 |

## 3. Decisões tomadas

| # | Decisão | Alternativas rejeitadas | Razão |
|---|---|---|---|
| D1 | Toolkit Python executável + prompts | Só markdown; híbrido opcional | "Linha a linha" e independência de modelo exigem extração determinística |
| D2 | Offline-first, adaptador AWS opcional | AWS-nativo; zero-AWS | Roda em sandbox Devin, CI e máquina sem credencial, sem perder coleta automática quando há credencial |
| D3 | MCP server + skills espelhadas | Playbooks Devin nativos; só CLI | MCP é o único ponto que cobre Devin Desktop, Devin CLI, Claude Code e Copilot com o mesmo comportamento |
| D4 | Case file + roteador determinístico | Prompt longo de orquestração; gates fail-closed | Roteamento como dado sobrevive a troca de sessão, de modelo e de ferramenta |
| D5 | Regras versão-guardadas em YAML + refresh script | Prosa expandida; busca web em runtime | Conhecimento auditável por `rule_id` + fonte + data, aplicável mesmo sem Python |
| D6 | Arquitetura A+C: core library, fato/juízo separados | Juízo embutido no extrator; MCP-first | Conhecimento fora do código; adaptadores triviais; cada camada testável isolada |
| D7 | Fixtures sintéticas versionadas | Artefatos reais no repo | Reprodutível em CI, sem dado sensível, sem superajuste a um caso |
| D8 | Handoff via commit git; artefatos brutos fora do git com manifest + comando de recoleta | Commitar artefatos pequenos; bucket S3 compartilhado | Facts/findings commitados bastam para retomar; bruto pode ser grande e sensível |
| D9 | Core em Python, não TypeScript | TypeScript (recomendação padrão para MCP) | O extrator precisa do `ast` do CPython para fidelidade exata de `line`/`col`/`end_line`. Um servidor TS teria que fazer shell-out para Python, adicionando uma fronteira de processo sem ganho |

## 4. Arquitetura

### 4.1 Fluxo

```
artefatos locais  →  Facts  →  Findings  →  case.yaml  →  next_step  →  skill/LLM
   (collect)        (facts)    (rules)      (case)        (case)      (markdown)
```

### 4.2 Camadas e fronteiras negativas

A fronteira negativa — o que a camada **não** pode fazer — é o mecanismo que garante o determinismo. Sem ela, juízo vaza para dentro do extrator e o resultado volta a depender do modelo.

**`collect/` — coletores (opcional).** Materializa artefatos em `.sparkforge/artifacts/` e grava `manifest.json` com kind, sha256, origem e comando de recoleta. Offline-first: se o arquivo já existe e o hash confere, no-op. `collect/aws.py` (extra `[aws]`, boto3) baixa event log do S3, `get_job` do Glue, `GetMetricData` do CloudWatch, query Athena em metadata tables.
*Não faz:* análise. Só materializa bytes e registra procedência.

**`facts/` — extratores.** Entrada: um artefato local. Saída: `Fact[]`. Puro, determinístico, sem rede, sem limiar, sem severidade, sem ordenação por importância.
*Não faz:* julgar. O extrator não sabe que 41 s de task é ruim.

**`rules/` — motor de regras.** Entrada: `Fact[]` + `RuntimeContext` + catálogo YAML. Saída: `Finding[]`.
*Não faz:* ler artefato bruto. Só vê Facts.

**`findings/` — contratos.** Dataclasses + JSON Schema publicado para `Fact`, `Finding`, `Recommendation`, `RuntimeContext`. Serialização estável, ordenação determinística.
*Não faz:* lógica de domínio.

**`case/` — estado e roteamento.** `.sparkforge/case.yaml` e as funções puras `next_step(case)` e `resume(case)`.
*Não faz:* chamar LLM. O roteamento é decidido por regra.

**`adapters/` — CLI e MCP.** Cascas finas sobre o core.
*Não faz:* conter regra, limiar ou heurística. Trocar de protocolo não move lógica.

**Skills e agents markdown.** Procedimento, interpretação, narrativa, código e patch.
*Não faz:* produzir número que não veio de um `Fact`. Toda afirmação quantitativa cita `rule_id` + `fact_id`. Sem Fact, é hipótese, e tem que estar rotulada como hipótese.

## 5. Contratos de dados

Todos com `schema_version`. Todos serializados com ordenação determinística — chave `(severity, rule_id, subject)` para Findings, `(kind, subject, id)` para Facts — para golden test não flakar.

### 5.1 `Fact`

```yaml
id: f_9c1a4e                     # sha1[:6] de (kind + subject canônico + measures) — estável entre runs
schema_version: 1
kind: pyspark.driver_collect     # namespace pontuado
subject:
  type: source_location          # source_location | stage | task | tf_resource | table | job_run
  file: lib/loader.py
  line: 142
  col: 8
  end_line: 142
  symbol: build_latest_snapshot
  snippet: "rows = df.collect()"
measures: {}                     # numérico; unidade no nome: _ms, _bytes, _count, _ratio
attrs: {bounded: false, inside_loop: true, loop_depth: 1}
provenance:
  artifact: artifacts/src/lib/loader.py
  artifact_sha256: 3f2b...
  extractor: pyspark_ast@0.1.0
```

`measures` sempre numérico com unidade no nome — impede o LLM de reinterpretar unidade. `provenance.artifact_sha256` torna o Fact reauditável meses depois, mesmo que o arquivo mude.

### 5.2 `Finding`

Superset compatível com o bloco `recommendation:` já documentado em `AGENTS.md`. Nada do contrato atual quebra.

```yaml
rule_id: SF-PY-004
schema_version: 1
catalog_version: 1
title: collect() sem limite dentro de loop
severity: P1                     # P0 | P1 | P2 | P3 | P4
confidence: high                 # high | medium | low
status: confirmed                # confirmed = há measure | structural = padrão sem métrica
subject: {...}                   # herdado do fact primário
evidence: [f_9c1a4e, f_22d7b0]   # minItems: 1 — schema rejeita vazio
measured: {}                     # números que dispararam a regra
threshold: {}                    # limiar aplicado, explícito na saída
runtime_scope: {glue: "*", spark: ">=3.1"}
explanation: ...
proposed_change: []
expected_effect: ...             # rotulado hipótese; número só com benchmark referenciado
risks: []
tradeoffs: []
validation: []
rollback: []
sources: [{url: ..., title: ..., retrieved: 2026-07-29}]
```

Dois campos carregam o peso:

- `evidence` com `minItems: 1` — finding sem Fact é inválido; o schema recusa.
- `status: confirmed | structural` — separa "medi isso" de "esse padrão costuma custar caro". Um analisador estático produz `structural`; métricas de execução produzem `confirmed`.

`expected_effect` não aceita percentual sem `benchmark_ref` preenchido. Isso mata "ganho de 40%" inventado na origem, no schema, em vez de depender de disciplina do modelo.

### 5.3 `Rule` — conhecimento como dado

Duas formas: estrutural e por limiar.

`status` na Rule define o `status` que o Finding emitido recebe. `catalog_version` é atributo do **arquivo** de catálogo, não de cada regra; o loader o estampa em cada Finding gerado.

O segundo exemplo abaixo (`SF-UI-002`) usa facts de Spark UI, cuja extração é escopo da Fase 1. Está aqui como prova de que o schema de Rule cobre a forma "por limiar", que a Fase 0 precisa validar antes de existirem 100+ regras.

```yaml
- id: SF-PY-004
  category: pyspark-code
  title: collect() sem limite dentro de loop
  requires_facts: [pyspark.driver_collect]
  when:
    all:
      - fact: pyspark.driver_collect
        where: {attrs.bounded: false, attrs.inside_loop: true}
  status: structural
  severity_default: P1
  runtime_scope: {glue: "*"}
  explanation: ...
  proposed_change: [...]
  risks: [...]
  validation: [...]
  rollback: [...]
  sources: [{url: ..., retrieved: 2026-07-29}]

- id: SF-UI-002          # exemplo de forma "por limiar"; facts vêm na Fase 1
  category: spark-ui
  title: skew de task no stage
  requires_facts: [spark.stage.task_duration]
  when:
    all:
      - fact: spark.stage.task_duration
        expr: "measures.max_ms / measures.p50_ms >= threshold.ratio"
  threshold: {ratio: 3.0}
  status: confirmed
  severity_by:
    - {when: "measures.max_ms / measures.p50_ms >= 10", severity: P0}
    - {when: "measures.max_ms / measures.p50_ms >= 3",  severity: P2}
  runtime_scope: {spark: ">=3.0"}
```

`runtime_scope` é o guarda de versão. Regra fora do range não dispara e aparece no relatório como *skipped por versão*, com o motivo. É o que impede recomendar propriedade Iceberg 1.10 num Glue 4.0.

**Avaliador de `expr`:** mini-avaliador com whitelist de nós AST — `Compare`, `BinOp` (aritmética), `BoolOp`, `UnaryOp`, `Constant`, e acesso a atributo restrito a `measures.*`, `attrs.*`, `threshold.*`. Proibido: `Call`, `Import`, `Subscript` arbitrário, qualquer dunder, qualquer nome fora da whitelist. **Não usar `eval`.** Motivo: o catálogo é dado editável e um dia alguém cola YAML de terceiro nele — o avaliador é superfície de execução e é tratado como tal.

### 5.4 `.sparkforge/case.yaml`

```yaml
schema_version: 1
case_id: sf-2026-07-29-a
created_at: 2026-07-29T14:02:11Z
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
  detected_from: [terraform, event_log]
  divergences: []
scope: {repo: ..., entrypoints: [], job_names: []}
phase: diagnosis        # intake|inventory|facts|diagnosis|hypothesis|experiment|validation|report
artifacts: [{kind, path, sha256, collected_at, source}]
facts_index:    {path: .sparkforge/facts.json,    count: 412, by_kind: {...}}
findings_index: {path: .sparkforge/findings.json, count: 19,  by_severity: {P0: 1, P1: 4}}
baseline: null          # {runtime_s, dpu_hours, input_rows, captured_at} quando existir
hypotheses:
  - id: h1
    statement: ...
    predicted_signal: ...
    experiment: ...
    status: open        # open | accepted | rejected
gates:
  baseline_captured: false
  dominant_bottleneck_identified: false
  functional_validation_defined: false
skills_used: [{skill, at, outcome}]
open_questions: []
```

Timestamps vêm do processo que escreve, nunca do LLM.

### 5.5 `next_step` — roteamento determinístico

Mesmo motor de regras, catálogo separado (`rules/catalog/routing.yaml`), predicado sobre o estado do case em vez de sobre facts.

```yaml
phase: diagnosis
recommended_skill: diagnose-data-skew
reason: "ROUTE-011: stage dominante com max/p50 = 8.3 e spill/input = 1.4"
evidence: [f_7a1c22]
missing_artifacts: [iceberg_metadata_snapshot]
collect_commands: ["sparkforge collect iceberg --table db.tbl"]
blocked_by: [baseline_captured]
alternatives: [{skill: diagnose-oom, reason: "ROUTE-014", rank: 2}]
```

`blocked_by` é **advisory** na Fase 0, não fail-closed: reporta gate não satisfeito e segue. Gate rígido vira impasse quando o dado simplesmente não existe. Endurecer é escopo da Fase 4, e fica registrado aqui como decisão consciente.

### 5.6 `handoff.md` — briefing de retomada

Gerado por `sparkforge handoff` / `sparkforge_resume`. Seções fixas, nesta ordem, para ser diffável:

1. Onde parou (fase, timestamp, ferramenta de origem)
2. Runtime detectado e divergências
3. Baseline (ou "ausente")
4. Top findings por severidade, com `rule_id` e `subject`
5. Hipóteses abertas com experimento pendente
6. Gates e o que falta para cada um
7. Artefatos ausentes com comando de recoleta
8. Próximo passo com `reason` citando a regra de roteamento
9. O que estava em voo no momento da interrupção
10. Cobertura: nós resolvidos vs `unresolved`

## 6. Analisador de referência: PySpark AST

Prova o contrato inteiro end-to-end. Módulo `ast` da stdlib, **estático puro — nunca importa nem executa o código do alvo.** Importar o módulo de um job para inspecioná-lo executaria código arbitrário do repositório analisado.

### 6.1 Três passes

1. **Parent-map e escopo.** Constrói mapa filho→pai para saber o que está dentro de qual `for`/`while`/`with`/`def`, e a profundidade de aninhamento.
2. **Reconstrução de cadeia.** Para `df.select(...).join(...).filter(...).write...`, caminha a espinha `Attribute`/`Call` e grava a **ordem** dos métodos com o span de linhas.
3. **Emissão de Facts.**

O passe 2 é o que paga o "linha a linha": com a ordem da cadeia, "join antes de select/filter" deixa de ser leitura subjetiva e vira predicado — índice de `join` menor que índice de `select`/`filter` na mesma cadeia.

### 6.2 Kinds emitidos

| kind | captura |
|---|---|
| `pyspark.read` | `spark.read.*`, `spark.table`, `spark.sql` |
| `pyspark.write` | `write`, `writeTo`, `saveAsTable`, `insertInto`, `merge` |
| `pyspark.action` | `collect count show take first head toPandas foreach foreachPartition toLocalIterator isEmpty` |
| `pyspark.driver_collect` | subset acima + `attrs.bounded` (há `limit`/`take` na cadeia) |
| `pyspark.udf` | `udf()`, `@udf`, `@pandas_udf`, `spark.udf.register`; `attrs.udf_type`, `return_type` |
| `pyspark.cache` | `cache`/`persist` + `attrs.has_unpersist_in_scope`, `storage_level` |
| `pyspark.partitioning` | `repartition`/`coalesce`; `attrs.literal_arg`, `measures.target_count` |
| `pyspark.join` | `join` + `how`, aridade de `on`, wrapper `broadcast()` presente |
| `pyspark.explode` | `explode`/`posexplode`/`explode_outer` |
| `pyspark.window` | `Window.partitionBy/orderBy`, `rowsBetween`/`rangeBetween` |
| `pyspark.chain` | cadeia ordenada de métodos + span de linhas |
| `pyspark.loop` | `For`/`While` contendo action/write; `measures.loop_depth` |
| `pyspark.withcolumn_run` | `withColumn` consecutivos na mesma cadeia; `measures.run_length` |
| `pyspark.conf_set` | `spark.conf.set(k, v)` com k/v literais |
| `pyspark.dedup` | `dropDuplicates`/`distinct` + colunas quando literais |
| `pyspark.callgraph_edge` | aresta função→função (consumida na Fase 1) |
| `pyspark.unresolved` | `getattr`, dispatch dinâmico, argumento não-literal, SQL montado em string |

`pyspark.unresolved` é obrigatório, não opcional. Sem ele o relatório finge cobertura total. Com ele a saída diz "312 nós resolvidos, 7 não resolvidos em `file:line`", o LLM sabe onde precisa de leitura humana, e um modelo fraco não consegue inflar confiança em cima de um ponto cego.

### 6.3 Catálogo inicial de regras

12 regras. Onze migram a tabela de referência rápida que já existe em `skills/optimize-pyspark-code/SKILL.md`; uma é de ambiente.

| rule_id | Regra | status |
|---|---|---|
| SF-PY-001 | Python UDF em transformação expressável em Spark SQL nativo | structural |
| SF-PY-002 | `collect()`/`toPandas()` sem `limit` na cadeia | structural |
| SF-PY-003 | `join` antes de `select`/`filter` na mesma cadeia | structural |
| SF-PY-004 | Action ou write dentro de loop | structural |
| SF-PY-005 | `coalesce(1)` | structural |
| SF-PY-006 | `explode` sem filtro nem projeção anterior na cadeia | structural |
| SF-PY-007 | Sequência de `withColumn` acima do limiar (`run_length >= 10`) | structural |
| SF-PY-008 | `cache`/`persist` sem `unpersist` no escopo | structural |
| SF-PY-009 | `broadcast()` forçado | structural |
| SF-PY-010 | `repartition` com argumento literal arbitrário | structural |
| SF-PY-011 | `dropDuplicates`/`distinct` sem colunas explícitas | structural |
| SF-ENV-001 | Divergência de runtime entre fontes de detecção | confirmed |

Migrar essa prosa para catálogo é o teste real do modelo de dados: se um item da tabela não couber como regra, o schema está errado — e descobrimos isso na Fase 0, não na Fase 3.

### 6.4 Detecção de `RuntimeContext`

Cruza, em ordem de precedência: event log (`spark.version`), Terraform (`glue_version`, `--datalake-formats`), `requirements.txt`/`pyproject.toml`, e `knowledge/runtime-compatibility.md` como tabela de derivação. Divergência entre fontes **não** é resolvida silenciosamente pelo extrator — gera `SF-ENV-001` e preenche `runtime.divergences` no case.

## 7. Superfície MCP e CLI

### 7.1 Tools da Fase 0

Prefixo consistente `sparkforge_`. Toda tool declara `outputSchema` — são os JSON Schemas da seção 5 — e retorna `structuredContent`, para o cliente processar sem reparsing de texto.

| tool | annotations | papel |
|---|---|---|
| `sparkforge_case_open` | readOnly:false, destructive:false, idempotent:false | cria `.sparkforge/case.yaml` |
| `sparkforge_case_get` | readOnly:true, idempotent:true | lê o case |
| `sparkforge_case_update` | readOnly:false, destructive:false, idempotent:false | grava fase, hipótese, gate, skill usada |
| `sparkforge_next_step` | readOnly:true, idempotent:true | roteamento determinístico |
| `sparkforge_resume` | readOnly:true, idempotent:true | payload de reidratação + `handoff.md` |
| `sparkforge_runtime_detect` | readOnly:true, idempotent:true | matriz de versões + divergências |
| `sparkforge_analyze_pyspark` | readOnly:true, idempotent:true | Facts linha a linha |
| `sparkforge_judge` | readOnly:true, idempotent:true | Facts + catálogo → Findings |
| `sparkforge_rules_lookup` | readOnly:true, idempotent:true | regra por id, categoria ou sintoma |
| `sparkforge_validate_output` | readOnly:true, idempotent:true | valida contra JSON Schema o que o LLM escreveu |

`openWorldHint` é `false` para todas as tools do core offline, e `true` apenas para os coletores AWS (Fase 1).

`sparkforge_rules_lookup` e `sparkforge_validate_output` são o núcleo da independência de modelo:

- **`rules_lookup`**: o modelo não precisa *saber* o conhecimento — ele consulta, e recebe limiar, guarda de versão, ação, risco, validação, rollback e fonte com data.
- **`validate_output`**: o modelo escreve a recomendação, a tool rejeita se `evidence` está vazio ou se há percentual sem `benchmark_ref`, o modelo corrige. Um modelo fraco fica preso no gate até conformar. É gate de **saída** — advisory no roteamento, rígido no schema. Não trava investigação; trava alucinação.

### 7.2 Filtragem e paginação

Obrigatórias, não opcionais: `facts.json` de uma biblioteca real tem centenas a milhares de entradas, e despejar isso no contexto degrada qualquer modelo.

- `sparkforge_analyze_pyspark`: `--kind`, `--path`, `--symbol`, `limit`, `cursor`
- `sparkforge_judge`: `--severity`, `--rule`, `--path`, `--status`, `limit`, `cursor`
- Toda resposta paginada inclui `total_count`, `returned_count`, `next_cursor` e `filters_applied`, para o agente saber que está vendo um subconjunto.

Default de `limit`: 50, ordenado por severidade. Resumo agregado (`by_severity`, `by_rule`, `by_file`) sempre presente independente da paginação — o agente vê a forma do todo antes de pedir detalhe.

### 7.3 Erros acionáveis

Nenhum erro genérico. Cada erro traz causa, o que falta e o comando que resolve:

```
ERRO artifact_missing: event log ausente para job_run jr_abc123.
  Esperado: .sparkforge/artifacts/eventlog/jr_abc123.json
  Recoleta:  sparkforge collect eventlog --job-run jr_abc123
  Sem credencial AWS? Baixe manualmente de s3://.../spark-event-logs/ e coloque no path acima.
```

### 7.4 Transporte

**stdio** para Claude Code, Devin CLI e CI. **Streamable HTTP stateless** para Devin Desktop, que configura MCP por `serverUrl`. Mesmo core, duas cascas de transporte, sem sessão com estado no servidor — o estado vive no `case.yaml`, no repositório.

### 7.5 CLI

Verbos espelham as tools: `sparkforge case open|get|update`, `next-step`, `resume`, `handoff`, `runtime detect`, `analyze pyspark`, `judge`, `rules lookup`, `validate`, `collect <kind>`.

Extração e julgamento são verbos separados no CLI, não um só. Isso força a fronteira da seção 4.2 e permite rejulgar facts antigos com catálogo novo sem reprocessar código — que é exatamente o que torna auditável a evolução do conhecimento.

## 8. Portabilidade Devin ↔ Claude

Requisito declarado: ficar sem token em uma ferramenta e continuar na outra, com a mesma base de conhecimento, integrações e qualidade. Paridade é **invariante testado**, não convenção.

### 8.1 Git é o barramento

Sessão Devin e sessão Claude Code são máquinas diferentes sem contexto conversacional compartilhado. O que trafega entre elas é commit.

```
.sparkforge/
  case.yaml                 ← commitado   (estado, fases, hipóteses, gates, decisões)
  facts.json                ← commitado   (evidência, com sha256 de origem)
  findings.json             ← commitado   (juízo + rule_id + fonte)
  handoff.md                ← commitado   (briefing de retomada, gerado)
  artifacts/manifest.json   ← commitado   (kind, sha256, origem, comando de recoleta)
  artifacts/**              ← gitignored  (event log bruto, .tf copiado, dumps)
```

Facts e findings são pequenos e derivados: commitados, então o outro lado não reprocessa nada. Artefatos brutos ficam fora do git (dado de negócio, centenas de MB), mas o manifest commitado diz o que falta e qual comando recoleta. Retomada nunca fica cega, e nunca vaza dado bruto para o histórico.

`.gitignore` recebe `.sparkforge/artifacts/*` com `!.sparkforge/artifacts/manifest.json`.

### 8.2 Escada de degradação

Toda capacidade tem três caminhos, e todo caminho entrega o mesmo conhecimento.

| camada | Claude Code | Devin Desktop | Devin CLI | Copilot / CI |
|---|---|---|---|---|
| MCP | stdio (plugin ou `.mcp.json`) | `serverUrl` HTTP | stdio | stdio |
| CLI shell | `sparkforge ...` | terminal do sandbox | nativo | nativo |
| markdown + YAML puro | `.claude/skills` | `.agents/skills` | `.agents/skills` | `.github/` |

O terceiro degrau é o que garante paridade absoluta: o catálogo de regras é **YAML legível**, então mesmo sem MCP e sem Python o agente lê `rules/catalog/*.yaml` e aplica o mesmo limiar, com a mesma guarda de versão e a mesma fonte. Cai a automação, não o conhecimento.

### 8.3 Por que o procedimento fica no repo, não em Playbooks Devin

Devin CLI não lê Knowledge nem Playbooks da conta Devin — só Devin Desktop e clientes MCP leem. Publicar o procedimento como Playbook faria Desktop e CLI divergirem exatamente no cenário que o requisito quer cobrir. Procedimento em arquivo no repositório funciona nos dois. Export de Playbook/Knowledge fica como conveniência opcional da Fase 3, nunca como fonte da verdade.

### 8.4 Paridade como CI gate

Três testes, e nenhum deles é o byte-mirror que já existe:

1. **Capability parity.** Manifesto `parity.yaml` mapeia cada capacidade × plataforma × mecanismo de entrega. Falha se alguma capacidade não tiver caminho em alguma plataforma.
2. **No-platform-knowledge.** Falha se conhecimento — limiar numérico, `rule_id`, URL de fonte — aparecer dentro de `.claude/`, `.agents/` ou `.github/`. Conhecimento só vive em `rules/catalog/` e `knowledge/`. É este teste que impede o drift crescer.
3. **Round-trip de retomada.** Fixture com `case.yaml` no meio da fase de diagnóstico: `resume` produz briefing determinístico e `next_step` idêntico, independente de qual ferramenta escreveu o case.

O byte-mirror atual (`sync_skills.py --check`) continua, estendido para `agents/`.

## 9. Distribuição — quatro canais

| canal | público | conteúdo |
|---|---|---|
| Plugin Claude Code | Claude Code | `.claude-plugin/plugin.json`, `skills/`, `agents/`, `commands/`, `.mcp.json` |
| MCP server | Devin Desktop, Devin CLI, Copilot, Cursor | stdio + HTTP |
| pip | CI, sandbox, shell | `pip install sparkforge-aws[aws,mcp]`, entry point `sparkforge` |
| Espelhos markdown | qualquer agente compatível | `.claude/`, `.agents/`, `.github/` |

**O repositório passa a ser o plugin.** O layout de plugin Claude Code espera `skills/` na raiz — que já é a fonte da verdade atual. Adicionar `.claude-plugin/plugin.json` e `.mcp.json` na raiz converte o repositório em plugin instalável sem reorganizar nada.

`.mcp.json` referencia o servidor por `${CLAUDE_PLUGIN_ROOT}`, nunca por caminho absoluto:

```json
{
  "mcpServers": {
    "sparkforge": {
      "command": "python",
      "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
      "env": {"PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}"}
    }
  }
}
```

`commands/` recebe os verbos de ciclo de vida do case, que são ação e não conhecimento: `/sf-open`, `/sf-next`, `/sf-resume`, `/sf-handoff`. As 18 skills permanecem em `skills/` e continuam ativando por contexto.

## 10. Agentes: direcionamento e coordenação

### 10.1 Fonte única

`agents/` na raiz passa a ser a fonte da verdade. `scripts/sync_skills.py` é estendido para gerar `.claude/agents/`, `.agents/agents/` e `.github/agents/*.agent.md` a partir dela. Isso corrige o drift já existente entre `spark-performance-architect` (Claude) e `spark-performance-engineer` (Copilot), e o teste de paridade passa a detectá-lo.

### 10.2 `AGENT_PROTOCOL.md`

Injetado em todo agente e toda skill pelo sync. Regras duras:

1. Abrir ou carregar case antes de qualquer análise.
2. Chamar `next_step` antes de escolher skill. Não escolher rota por conta.
3. Nenhum número na saída sem `fact_id` que o sustente.
4. `rules_lookup` em vez de memória para limiar, versão e fonte.
5. `validate_output` antes de apresentar recomendação.
6. Registrar no case cada skill usada, o resultado e o motivo de não usar as descartadas.
7. Reportar `unresolved` sempre; nunca omitir ponto cego.
8. Confirmar `runtime` antes de citar API ou propriedade de configuração.
9. Manutenção destrutiva (expiração de snapshot, remoção de órfãos, mudança de partition spec, overwrite) só com escopo, retenção e confirmação explícita.

### 10.3 Loop de fase

Substitui a árvore de decisão em prosa:

```
next_step → coletar → extrair facts → julgar → hipótese → experimento
   → medir → validar dados → atualizar case → next_step
```

A árvore de decisão vive em `routing.yaml` (dado), não no prompt (prosa que cada modelo interpreta diferente).

Resultado: trocar Opus por Sonnet, por Devin, por Copilot muda a qualidade da narrativa e do código proposto. Não muda quais evidências foram extraídas, quais regras dispararam, nem qual é o próximo passo.

## 11. Testes

### 11.1 Fixtures

Cada fixture é um diretório autocontido:

```
fixtures/pyspark/collect_in_loop/
  input/lib/loader.py          # anti-pattern plantado em linha conhecida
  expected/facts.json          # golden — inclui line/col/end_line
  expected/findings.json       # golden — rule_id, severity, evidence
  meta.yaml                    # runtime alvo, o que a fixture prova, kinds esperados
```

Golden test falha em dois sentidos: perder finding (falso negativo) **e** inventar finding (falso positivo). O segundo importa mais — analisador que grita demais treina o operador a ignorar a saída.

Fixtures obrigatórias na Fase 0: uma por regra do catálogo (12), mais quatro adversariais:

| fixture adversarial | resultado esperado |
|---|---|
| `dynamic_dispatch` — `getattr`, método montado em string | `pyspark.unresolved`, zero findings |
| `clean_job` — código idiomático sem anti-pattern | zero findings |
| `version_out_of_scope` — regra fora do `runtime_scope` | regra *skipped por versão*, com motivo |
| `near_threshold` — `withColumn` run_length = 9 | zero findings (limiar é 10) |

### 11.2 Camadas de teste

Nenhuma precisa de AWS nem de LLM.

| camada | teste |
|---|---|
| facts | golden JSON por fixture; determinismo (2 execuções → byte-idêntico) |
| rules | Facts sintéticos inline; limiar de borda (`ratio` 2.99 / 3.0 / 3.01); guarda de versão |
| expr evaluator | **segurança**: `__import__`, `Call`, dunder, nome fora da whitelist devem ser rejeitados |
| schemas | valida golden; rejeita `evidence: []`; rejeita percentual sem `benchmark_ref` |
| case/router | estados de case → `next_step` esperado; round-trip de retomada |
| paridade | capability parity; no-platform-knowledge; byte-mirror de skills e agents |
| catálogo | `rule_id` único; `sources` com `retrieved` em toda regra; todo `requires_facts` existe como kind real; `expr` parseável |

Os testes existentes (`tests/test_package_structure.py`, `test_skill_content.py`, `test_v020_structure.py`) permanecem e ganham o eixo de agents.

### 11.3 Suíte de avaliação — a prova de independência de modelo

`evals/fase0.xml`, 10 pares pergunta/resposta sobre o corpus de fixtures, no formato:

```xml
<evaluation>
  <qa_pair>
    <question>No fixture collect_in_loop, qual rule_id dispara e em qual linha do arquivo lib/loader.py?</question>
    <answer>SF-PY-004:142</answer>
  </qa_pair>
</evaluation>
```

Cada pergunta é independente, read-only, exige múltiplas chamadas de tool, e tem resposta única verificável por comparação de string que não muda com o tempo.

**Gate de aceitação, dois níveis:**

- **Nível determinístico:** facts e findings gerados pelas tools devem ser 100% idênticos entre execuções e entre modelos. Isso não é medido por eval — é garantido por construção e verificado pelos golden tests. Se divergir, é bug.
- **Nível de agente:** a eval mede se o agente *usa as tools corretamente*. Gate: 10/10 para qualquer modelo testado. Uma resposta errada significa que o protocolo ou a descrição da tool está ambígua — a correção é no prompt/descrição, não no modelo.

Matriz de execução: Opus, Sonnet, Haiku e Devin. A qualidade da narrativa não é gated — só a corretude do uso das tools.

## 12. Empacotamento, versionamento, CI

### 12.1 Dependências

Núcleo com dependência mínima: stdlib + `PyYAML` + `jsonschema`. Extras: `[aws]` → boto3; `[mcp]` → MCP Python SDK; `[dev]` → pytest, ruff.

Motivo do núcleo enxuto: Devin CLI e sandbox precisam rodar `sparkforge analyze` sem instalar o mundo.

**Python:** `requires-python = ">=3.10"`. Desenvolvimento e CI rodam em 3.11 (o runtime do Glue 5.x), mas o core não usa sintaxe posterior a 3.10, para que o pacote também execute sob Glue 4.0 caso alguém o rode dentro do próprio job. CI testa nas duas versões.

### 12.2 Três eixos de versionamento

Independentes porque envelhecem em ritmos diferentes:

- `schema_version` por contrato — muda raro, quebra compatibilidade.
- `catalog_version` — muda quando limiar ou fonte muda. Findings gravam a versão que os julgou, então permanecem reauditáveis.
- `extractor: nome@semver` em `provenance` — muda quando a extração muda; golden test pinado detecta mudança silenciosa.

`manifest.json` da raiz (hoje `version: 0.3.0`) passa a `0.4.0` e ganha `tools`, `mcp` e `schemas`.

### 12.3 CI

`.github/workflows/ci.yml`: ruff → testes por camada → paridade → `sync_skills.py --check` → validação de catálogo → eval determinística sobre fixtures (sem LLM).

Job separado e manual para `refresh_knowledge` (Fase 2), que **nunca commita sozinho**: abre PR com o diff das docs oficiais para revisão humana. Conhecimento entra por revisão, não por scraper.

## 13. Segurança

| risco | mitigação |
|---|---|
| Executar código do repositório analisado | Extrator é `ast` estático. Nunca `import`, nunca `exec` do alvo |
| Catálogo YAML como vetor de execução | Avaliador `expr` com whitelist de nós AST. Sem `eval`. Sem `Call`. Teste de segurança dedicado |
| Vazamento de dado de negócio no git | `artifacts/**` gitignored; só manifest commitado; teste que falha se artefato bruto for staged |
| Segredo em default arguments do Glue | Extratores redigem valores de chaves com padrão de segredo antes de gravar Fact; `SF-TF-*` (Fase 1) alerta sobre segredo em IaC |
| Manutenção destrutiva acidental | Nenhuma tool da Fase 0 escreve fora de `.sparkforge/`. `destructiveHint: false` em todas. Regra 9 do `AGENT_PROTOCOL` exige confirmação explícita de escopo e retenção |
| Credencial AWS em ambiente compartilhado | Coletores AWS são extra opcional; núcleo nunca requer credencial; nenhuma credencial é gravada em case ou manifest |

## 14. Estrutura de diretórios resultante

```
spark-forge-aws/
  .claude-plugin/plugin.json         NOVO  manifesto do plugin
  .mcp.json                          NOVO  servidor MCP via ${CLAUDE_PLUGIN_ROOT}
  AGENT_PROTOCOL.md                  NOVO  regras duras injetadas em agents e skills
  sparkforge/                        NOVO  pacote Python
    facts/pyspark_ast.py
    rules/{engine.py,expr.py,loader.py}
    rules/catalog/{pyspark.yaml,env.yaml,routing.yaml}
    findings/{models.py,schemas/*.json}
    case/{store.py,router.py,resume.py}
    collect/{base.py,aws.py}
    adapters/{cli.py,mcp.py}
  agents/                            NOVO  fonte única dos agentes
  commands/                          NOVO  /sf-open /sf-next /sf-resume /sf-handoff
  fixtures/pyspark/*/                NOVO  corpus + golden outputs
  evals/fase0.xml                    NOVO  10 QA pairs
  parity.yaml                        NOVO  manifesto de paridade
  skills/                            existente — fonte da verdade das skills
  knowledge/                         existente — passa a apontar para rules/catalog
  templates/ checklists/ examples/   existentes
  .claude/ .agents/ .github/         existentes — espelhos gerados
  scripts/sync_skills.py             estendido para agents e protocolo
  tests/                             estendido
```

## 15. Critérios de aceitação da Fase 0

A Fase 0 está concluída quando todos forem verdadeiros:

1. `sparkforge analyze pyspark` produz Facts ancorados em `file:line:col` para as 17 kinds da seção 6.2, validados por JSON Schema.
2. `sparkforge judge` produz Findings para as 12 regras do catálogo, com `evidence` não vazio e `rule_id` rastreável até fonte com data.
3. Executar duas vezes o mesmo comando sobre o mesmo input gera saída byte-idêntica.
4. As 16 fixtures (12 de regra + 4 adversariais) passam golden test nos dois sentidos.
5. Teste de segurança do avaliador `expr` passa: todo nó fora da whitelist é rejeitado.
6. `sparkforge_*` disponível via MCP stdio e via HTTP, com `outputSchema` e `structuredContent` em todas as tools.
7. Plugin Claude Code instala e o servidor MCP sobe usando `${CLAUDE_PLUGIN_ROOT}`.
8. `pip install -e .` e `sparkforge --help` funcionam sem boto3 e sem SDK MCP instalados.
9. `sparkforge resume` sobre um `case.yaml` de fixture gera `handoff.md` determinístico com as 10 seções.
10. Os três testes de paridade passam, incluindo `no-platform-knowledge`.
11. `agents/` é fonte única; drift `spark-performance-architect` / `spark-performance-engineer` resolvido.
12. `evals/fase0.xml` com 10 pares; gate 10/10 em pelo menos dois modelos de tamanhos diferentes.
13. CI verde com todos os jobs da seção 12.3.
14. `README.md`, `GUIA_DE_USO.md` e `PROMPT_INICIAL_MESTRE.md` atualizados com os quatro canais e o fluxo de handoff.

## 16. Roadmap das fases seguintes

| Fase | Escopo | Depende de |
|---|---|---|
| 1 | Extratores restantes: Spark event log (métricas por stage/task, skew, spill, GC, executores perdidos), Terraform HCL, metadata tables Iceberg, SQL literal, call graph da biblioteca. Coletores AWS completos | contratos da Fase 0 |
| 2 | Knowledge: expansão do catálogo para as 18 skills, `refresh_knowledge` com PR de diff das docs oficiais, matriz de compatibilidade automatizada | schema de Rule |
| 3 | Integração profunda: export de Playbook/Knowledge Devin, MCP HTTP hospedado, marketplace de plugin, distribuição pip | superfície MCP |
| 4 | Rigor: gates fail-closed opcionais, benchmark automatizado antes/depois, validação funcional automatizada (contagem, schema, chaves, agregados), assinatura de relatório | case + router |

## 17. Riscos desta fase

| risco | probabilidade | mitigação |
|---|---|---|
| Regra da tabela de prosa não cabe no schema de Rule | média | É o objetivo do exercício. Se acontecer, o schema muda na Fase 0, antes de 100+ regras existirem |
| Extração de cadeia falha em código com alto dinamismo | alta em código real | `pyspark.unresolved` reporta em vez de fingir cobertura |
| Falso positivo treina o operador a ignorar a saída | média | Golden test bidirecional; fixture `clean_job` com zero findings; fixture `near_threshold` |
| Custo de manter quatro canais de distribuição | média | Fonte única + sync + teste de paridade. O canal que não passa no teste não é publicado |
| Eval de agente vira teste de modelo em vez de teste de contrato | média | Falha de eval é corrigida na descrição da tool ou no protocolo, nunca trocando o modelo |

---

## 18. Desvios pós-implementação

Escrito em 2026-07-31, depois das Fases 0, 1 e 2. Esta seção é a errata da spec:
cada item diz o que as seções 1–17 afirmam, o que existe no repositório, e por quê.
Nada acima foi editado — a spec permanece auditável como decisão de 2026-07-29.

### 18.1 Desvios decididos durante a implementação

**D-A. Catálogo mora na raiz, não dentro do pacote.**
§14 coloca o catálogo em `sparkforge/rules/catalog/`. Ele está em `rules/catalog/`.
Motivo: é dado consultável e é o **terceiro degrau da escada de degradação** (§8.2) —
um agente sem Python lê o YAML direto. Enterrá-lo no pacote destrói a descoberta.
`loader.catalog_dir()` resolve na ordem `SPARKFORGE_CATALOG` → raiz do repo →
fallback relativo ao pacote. Registrado no plano de implementação como Desvio 1.

**D-B. Predicados de roteamento são declarativos, não `expr`.**
§5.5 sugere reaproveitar o motor de `expr` para `routing.yaml`. O `routing.yaml`
committado precisava de `len(...)`, `any(...)` e `in`, que exigem `ast.Call` e
`ast.In` — proibidos pela whitelist de §5.3. Enfraquecer o avaliador não era
aceitável: o catálogo é dado editável, logo superfície de execução (§13).
As 16 rotas usam operadores declarativos: `equals`, `count_gt`, `contains`,
`any_where`, `absent`. Registrado no plano como Desvio 2.

**D-C. O catálogo nasceu com 43 regras, não 12.**
§6.3 projeta um catálogo inicial de 12 regras. O commit `ffcf150`
(`feat(knowledge): build version-guarded knowledge base and rule catalog`),
anterior ao código, já entregou 43 regras em 7 áreas: SF-PY 12, SF-UI 6,
SF-GLUE 6, SF-ATH 5, SF-ICE 5, SF-PQ 5, SF-ENV 4 — mais 16 `ROUTE-*`.
Consequência não prevista pela spec: **a maioria das regras nasceu inerte**,
porque os extratores que produzem os `requires_facts` delas só chegaram na Fase 1.
Isso gerou um mecanismo que a spec não tem: o campo `blocked_on` e o teste
`tests/test_rules_catalog_reachability.py`, que falha quando uma regra exige um
kind sem extrator **e** não declara o bloqueio — e falha também quando um
`blocked_on` sobrevive ao extrator que o resolveu.

**D-D. `pyspark_ast` emite 19 kinds, não 17.**
A tabela de §6.2 lista 17. A implementação precisou de dois sentinelas a mais:
`pyspark.module_analyzed` (âncora para condições `absent:` — sem ele, "não existe
X neste módulo" é vacuamente verdadeiro em módulo nenhum analisado) e
`pyspark.glue_context_init` (detecção de `GlueContext`, exigida por SF-GLUE).

**D-E. Versionamento — resolvido em 2026-07-31, e não do jeito óbvio.**
§12.2 define três eixos independentes. Até 2026-07-31 os três estavam parados em
`1` / `1` / `0.4.0`, mesmo após as Fases 1 e 2 terem adicionado 12 extratores e
18 tools. A correção **não** foi subir os três: o pacote foi para `0.5.0`, e
`schema_version` e `catalog_version` ficaram em `1` deliberadamente, porque
nenhum contrato de dados mudou e nenhum limiar existente mudou. Subir os três
juntos destruiria exatamente a propriedade que a §12.2 quer — um Finding gravado
com `catalog_version: 2` sugeriria que o limiar que o julgou é outro, e a
reauditabilidade some.

O teste que fixava o literal `0.4.0` foi trocado pelo invariante que ele tentava
proteger: as quatro fontes da versão (`pyproject.toml`, `manifest.json`,
`plugin.json`, `sparkforge.__version__`) têm que concordar entre si. O bump pela
metade é a falha real — `pip install` entrega uma versão e o plugin anuncia
outra —, e um literal num teste não pegava isso.

### 18.2 Números superados

Referências numéricas das seções 1–17 e o valor de hoje (2026-07-31):

| Seção | Spec diz | Hoje | Causa |
|---|---|---|---|
| §6.2, §15.1 | 17 fact kinds, só `pyspark.*` | **80 kinds** em 13 extratores | D-D + Fase 1 |
| §6.3, §15.2 | catálogo de 12 regras | **43 regras**, nenhuma `blocked_on` | D-C + Fase 2 |
| §7.1, §15.6 | 10 tools MCP | **28 tools** | Fase 1 |
| §7.5 | ~11 verbos de CLI | 12 subverbos `analyze` + 6 `collect` + `fuse`, `judge`, `case`, `next-step`, `resume`, `handoff`, `runtime detect`, `rules lookup`, `validate` | Fase 1 |
| §11.1, §15.4 | 16 fixtures | **73 fixtures** em 15 domínios | Fases 1 e 2 |
| §11.2 | 7 camadas de teste | mesmas camadas, **1726 testes** | acumulado |
| §14 | árvore de diretórios | acrescidos `adapters/tools.py`, `adapters/_core.py`, `findings/validate.py`, `rules/version_scope.py`, `facts/` com 13 módulos, `scripts/regen_fixtures.py` | Fase 1 |

Namespaces de fact que não existiam nesta spec e existem hoje: `spark.*`
(event log), `tf.*` (Terraform), `iceberg.*`, `sql.*`, `athena.*`, `s3.*`,
`glue.*` (CloudWatch), `consumers.*`.

### 18.3 Roadmap de §16 — situação real

| Fase da §16 | Status | Observação |
|---|---|---|
| 1 — extratores restantes + coletores AWS | **entregue** | Ver [spec da Fase 1](2026-07-30-sparkforge-fase1-design.md) |
| 2 — knowledge: expansão do catálogo, `refresh_knowledge`, matriz de compatibilidade | **entregue** em 2026-07-31 | `scripts/refresh_knowledge.py` + workflow manual/semanal que abre PR e nunca commita em main; watchlist derivada dos `sources[].url` do próprio catálogo, cobrindo as fontes da matriz de compatibilidade; catálogo expandido com SF-PLAN e SF-CG (43 → 48 regras). Atenção ao nome: a "Fase 2" executada no branch `feat/fase2-desbloqueios` é escopo **diferente** — ver [spec da Fase 2 executada](2026-07-31-sparkforge-fase2-design.md) |
| 3 — export Devin, MCP HTTP hospedado, marketplace, pip | **não iniciado** | O transporte HTTP existe (`--transport http`), mas hospedagem, export de Playbook e publicação no PyPI/marketplace não |
| 4 — gates fail-closed, benchmark automatizado, validação funcional automatizada, assinatura de relatório | **não iniciado** | `blocked_by` continua advisory, como §5.5 decidiu |

### 18.4 O que continua valendo sem alteração

Para não induzir desconfiança generalizada: as decisões estruturais da spec foram
implementadas como escritas. Continuam válidas e testadas —

- as fronteiras negativas de §4.2 (extrator não julga, motor de regras não lê artefato bruto, adaptador não contém heurística);
- os contratos `Fact` / `Finding` / `RuntimeContext` de §5, incluindo `evidence` com `minItems: 1` e a recusa de percentual sem `benchmark_ref`;
- o avaliador `expr` com whitelist de nós AST e sem `eval` (§5.3, §13);
- a guarda de versão `runtime_scope`, falha fechada quando a versão não é detectada (§5.3);
- `pyspark.unresolved` obrigatório — cobertura honesta em vez de silêncio (§6.2);
- git como barramento de handoff, com `artifacts/**` fora do git e manifest committado (§8.1);
- a escada de degradação MCP → CLI → markdown+YAML (§8.2);
- os quatro canais de distribuição de §9;
- `AGENT_PROTOCOL.md` com as 9 regras duras de §10.2;
- golden test bidirecional — perder finding e inventar finding falham igual (§11.1).
