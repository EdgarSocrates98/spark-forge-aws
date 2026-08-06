---
name: optimize-pyspark-code
description: Use quando revisar, refatorar ou otimizar código PySpark/Spark SQL para AWS Glue — script, função, módulo, PR ou trecho de DataFrame — suspeito de UDF Python evitável, collect/toPandas, join sem redução prévia, cache indevido, coalesce(1), repartition arbitrário, explode sem controle, sequência longa de withColumn, dropDuplicates sem chave explícita ou spark.conf.set em runtime. Use também quando a pergunta for "por que esse código está lento", "isso vai escalar", "tem algo errado nesse DataFrame" ou "como eu melhoro isso", mesmo que ninguém cite UDF, shuffle ou cardinalidade pelo nome. Use também quando o job constrói `GraphFrame` e chama `connectedComponents`, `pageRank`, `aggregateMessages` ou `pregel` — é o mesmo `.py`, lido por `sparkforge analyze graph`. Se você está prestes a ler o arquivo linha a linha procurando esses padrões, rode `sparkforge analyze pyspark` em vez disso — ele varre a árvore inteira, não uma amostra, e ancora cada achado em file:line:col.
---

# Optimize PySpark Code

Ler código à procura de UDF, join mal ordenado, `coalesce(1)` ou cache sem `unpersist` é leitura amostrada: um revisor cansado no arquivo 40 não olha com o mesmo cuidado que no arquivo 2, e dois revisores param em pontos diferentes. O extrator de AST não cansa e não amostra — ele percorre a árvore inteira e emite um fact por ocorrência, com `file:line:col`. O catálogo `SF-PY-001..012` julga esses facts contra critérios versionados, cada um com explicação, risco e plano de validação.

Seu trabalho não é vasculhar o arquivo à procura do padrão. É **extrair, julgar, e decidir o que fazer com o que voltou**.

## Procedimento

### 1. Extraia os facts

```bash
sparkforge analyze pyspark --path <arquivo-ou-diretório> --out .sparkforge/facts.json
```

Leia `by_kind` na saída: se o arquivo tem joins e a contagem de `pyspark.join` é zero, ou o módulo é grande e `by_kind` está vazio, o parser não reconheceu a forma do código antes de concluir "está limpo". Leia `unresolved` sempre — linha que o AST não conseguiu resolver (import dinâmico, `conf.set` com valor não literal) é ponto cego, não ausência de problema.

### 2. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --show-skipped
```

`--show-skipped` mostra as regras que não avaliaram por falta do fact esperado ou por incompatibilidade de `runtime_scope` — sem isso, "zero findings" e "não consegui avaliar" ficam indistinguíveis.

**Sobre a versão: aqui não há de onde tirá-la, e isso não custa nada.** `analyze pyspark` lê a árvore sintática; nenhum fact que ele emite carrega versão de runtime, e o motor não deduz versão de sintaxe de API de propósito — "usou `df.observe`, logo Spark >= 3.3" seria julgamento disfarçado de fato. Então `runtime` volta com os campos vazios e `detected_from: []`, e é isso mesmo. Nenhuma das doze regras `SF-PY-*` declara `runtime_scope`: elas são estruturais, valem em toda versão suportada, e um `runtime` vazio não pula nenhuma delas.

O que aparece em `--show-skipped` com `reason: runtime_scope` são as regras de infraestrutura Glue, que este `facts.json` não teria como disparar de qualquer forma. Não preencha `--glue` com um chute para "limpar" essa lista — a flag é para declarar uma versão que você sabe de fonte confiável (o `.tf`, o console, o job run), e é o que muda quando a pergunta passa a ser de infra. Se ela for, o caminho é dar ao motor a fonte, não o palpite: `sparkforge analyze terraform` e os dois arquivos na mesma chamada (`--facts` é repetível), e aí `runtime.detected_from` passa a dizer `["terraform"]`.

### 3. Interprete

Cada finding vem com `explanation`, `proposed_change`, `risks`, `tradeoffs` e `validation` do próprio catálogo — não repita esse texto de memória, ele já está na saída de `judge`. Seu trabalho é decidir a prioridade real no contexto do job (SLA, volume, frequência de execução) e produzir a correção.

### 4. Produza a saída

- Achados por severidade, cada um citando `rule_id` e `fact_id`.
- Correção mínima de baixo risco e, quando justificada, refatoração estrutural — mostrando diff ou antes/depois.
- Plano de validação (contagem, schema, chaves, agregados de controle) e como confirmar o ganho no plano físico e nas métricas reais, encadeando `analyze-spark-plan` ou `benchmark-pyspark-job`.

## Preferências de reescrita

Ordem de preferência, do `knowledge/spark/execution-model.md` seção 4: função Spark SQL nativa → higher-order function (`transform`, `filter`, `aggregate`) → `pandas_udf` medido → `udf` Python só com justificativa registrada. Nunca mover dado não amostrado para o driver. Detalhes de anti-pattern por categoria (driver, transformações, joins, cache, escrita) estão em `knowledge/anti-patterns.md`.

## Quando o job constrói um grafo

Se o módulo importa `graphframes` ou `io.graphframes`, o mesmo `.py` tem uma quarta leitura,
e ela não é opcional — pular apaga a área `SF-GRAPH` do relatório em silêncio:

```bash
sparkforge analyze graph --path <arquivo-ou-diretório> --out .sparkforge/facts_graph.json
```

Quatro regras: `SF-GRAPH-001` (`connectedComponents` sem diretório de checkpoint — **P0**,
porque o algoritmo levanta `java.io.IOException` na primeira iteração em vez de degradar),
`SF-GRAPH-002` (GraphFrames importado num Spark sem artefato publicado), `SF-GRAPH-003`
(arestas não persistidas) e `SF-GRAPH-004` (algoritmo de grafo dentro de laço Python).

**Duas coisas que este verbo faz diferente do `analyze pyspark`, e as duas mordem.**

A afirmação acima — "nenhuma das doze `SF-PY-*` declara `runtime_scope`, então `runtime`
vazio não pula nenhuma" — **não vale para `SF-GRAPH-002`**. Ela é a única regra deste
coordenador com guarda de versão, e a guarda é por **faixa de Spark** (`>=3.3` e `<3.4`),
não por Glue: sobre um `.py` solto ela sai em `skipped` com `reason: runtime_scope`, e isso
é a resposta certa — "não há artefato publicado para ESTE Spark" é impossível de afirmar sem
saber o Spark. Para trazê-la de volta, dê a fonte de versão (o `.tf`, o dump de
`describe-cluster`), nunca um `--glue` chutado.

E `SF-PY-008` dispara sobre job de grafo, com razão. Medido nas 25 fixtures de
`fixtures/graph/`: `SF-PY-008` em vinte delas, `SF-PY-012` em três, e nenhum dos vinte e três
cita fact `graph.*`. `cache`/`persist`/`unpersist` ficaram **fora** do vocabulário de
`graph.algorithm` justamente porque `pyspark.cache` já os emite — as duas áreas falam da
mesma linha dizendo coisas diferentes, e suprimir uma entrega metade do achado.

## Limiares

A maioria das 12 regras é estrutural (presença/ausência de um padrão), não numérica — mas `SF-PY-007` (sequência de `withColumn`) tem um limiar de contagem, e ele pode mudar. Não decore:

```bash
sparkforge rules lookup --id SF-PY-007
```

Cada regra devolve o limiar atual, a guarda de versão (`runtime_scope`), o risco de aplicar a mudança e a fonte com data.

## Quando NÃO usar

- O gargalo já está identificado em dados/infra (skew, small files, Iceberg, capacidade de workers): use a skill específica.
- Revisão formal de PR com classificação P0–P4 e comparação contra a base: use `review-pyspark-pr`.
- O código é uma biblioteca com múltiplos módulos e o entrypoint não conta a história toda: comece por `analyze-library-call-graph`.
- Precisa do plano físico para decidir estratégia de join ou confirmar pushdown: passe antes por `analyze-spark-plan`.
- O padrão é especificamente um loop de batch ou um latest-per-key: use `analyze-batch-loop` ou `optimize-latest-per-key`, que aplicam o mesmo extrator com foco mais estreito.

## Referência rápida

| Regra | O que pega | Fact que sustenta |
|---|---|---|
| `SF-PY-001` | UDF Python onde existe alternativa nativa | `pyspark.udf` |
| `SF-PY-002` | `collect()`/`toPandas()` sem limite na cadeia | `pyspark.driver_collect` |
| `SF-PY-003` | join antes de `select`/`filter` na mesma cadeia | `pyspark.chain` + `pyspark.join` |
| `SF-PY-004` | action ou write dentro de loop | `pyspark.loop` |
| `SF-PY-005` | `coalesce(1)` | `pyspark.partitioning` |
| `SF-PY-006` | `explode` sem redução prévia | `pyspark.explode` + `pyspark.chain` |
| `SF-PY-007` | sequência longa de `withColumn` | `pyspark.withcolumn_run` |
| `SF-PY-008` | `cache`/`persist` sem `unpersist` no escopo | `pyspark.cache` |
| `SF-PY-009` | `broadcast()` forçado por hint | `pyspark.join` |
| `SF-PY-010` | `repartition(n)` com `n` literal arbitrário | `pyspark.partitioning` |
| `SF-PY-011` | `dropDuplicates`/`distinct` sem colunas explícitas | `pyspark.dedup` |
| `SF-PY-012` | `spark.conf.set` em runtime | `pyspark.conf_set` |

## Red flags

- Aceitar um finding `status: structural` como prova de custo real sem olhar `risks` e `tradeoffs` do próprio catálogo — a regra descreve o padrão, não necessariamente confirma que ele domina o runtime.
- Forçar `broadcast()` ou remover um hint sem medir o tamanho serializado do lado pequeno.
- Refatorar `cache()`/`dropDuplicates()` sem antes confirmar reuso real ou a chave de negócio verdadeira.
- Aplicar a correção proposta sem executar o plano de `validation` da própria regra (contagem, schema, chaves, agregados).

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva você **não executa** — recomende, e a confirmação de escopo e
retenção **sobe a quem pode ser perguntado**: o agente pai que despachou, ou o
operador na sessão.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a
confirmação aqui não é difícil: é impossível — por isso a regra 9 de
`AGENT_PROTOCOL.md` manda não executar e devolver a decisão a quem pode ser
perguntado.
