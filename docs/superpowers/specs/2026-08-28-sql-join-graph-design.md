# SparkForge AWS — Grafo de joins: qual fonte entra em qual join, e de que lado

**Data:** 2026-08-28
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §3 (Multi-source Workload Analyzer). **É documento
de entrada LOCAL e não versionado neste repositório** — a nota entra aqui porque um leitor de
clone limpo procuraria o arquivo e não o acharia.
**Base:** a árvore do event log lida por
[`2026-08-28-spark-sql-scan-metrics-design.md`](2026-08-28-spark-sql-scan-metrics-design.md)
e o perfil de
[`2026-08-28-workload-fingerprint-design.md`](2026-08-28-workload-fingerprint-design.md).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o terceiro recorte de C

| # | Subprojeto | Estado |
|---|---|---|
| A | Correção de `SF-GLUE-001` | aberto |
| B | Coletor de histórico de runs | entregue em 2026-08-28 |
| C1 | Métrica de scan por nó do plano | entregue em 2026-08-28 |
| C2 | WorkloadFingerprint | entregue em 2026-08-28 |
| **C3** | **Grafo de joins** | **este documento** |
| D | Capacity e SLA optimizer | aberto |
| E | FinOps | aberto |

### 1.1 A lacuna exata

`plan.join` existe desde a Fase 1 e carrega `strategy`, `join_type`, `is_broadcast` e
`build_side` — este último extraído do token `BuildLeft`/`BuildRight`
(`sparkforge/facts/spark_plan.py:804`). Ele diz que o lado de build é o **esquerdo**.

Nada diz **o que** está do lado esquerdo.

É a diferença entre "o build side é o esquerdo" e "a tabela de 40 GB está no build side". A
segunda frase é acionável; a primeira não. E é a segunda que o documento de origem pede em §3,
ao descrever o join graph inteiro como pré-requisito do analisador multi-fonte.

### 1.2 Por que a árvore vem do event log

`spark_plan.py` **descarta a estrutura de propósito**. O docstring de `_Node` diz: *"Um
operador do plano, já separado do desenho de árvore."* O parser guarda uma lista plana de nós
com `node_id`, e as arestas não sobrevivem — reconstruí-las exigiria reparsear a indentação do
texto que aquele módulo deliberadamente jogou fora.

O `sparkPlanInfo` que C1 lê do `SparkListenerSQLExecutionStart` tem `children` de verdade, e
`sql_metrics._walk` já percorre a árvore inteira — jogando a estrutura fora ao final, porque
C1 não precisava dela.

Vale aqui o mesmo argumento que C1 registrou em §3.2: a árvore do event log é da execução que
produziu os números, e o artefato de `analyze plan` é texto colado por um humano, que pode ser
de outro dia, outro ambiente, outro volume.

---

## 2. Escopo

**Entra:**

- Dois kinds novos em `sparkforge/facts/sql_metrics.py`: `spark.sql.join` e
  `spark.sql.join_input`.
- Cenários novos em `fixtures/sql_metrics/`, o domínio que já existe.

**Não entra, e a razão de cada um:**

- **Volume que chega a cada join.** Propagar os bytes dos scans subindo a árvore exigiria
  decidir o que acontece quando há agregação no meio do ramo, e o plano não publica a
  cardinalidade de saída de um `HashAggregate`. Um número propagado através de um filtro
  desconhecido seria estimativa vestida de medição.
- **Ordem dos joins como julgamento.** A sequência é observável; dizer que ela está *errada*
  exige cardinalidade das fontes, que nem o plano nem o event log publicam de forma confiável.
- **`reuse_count` por fonte.** É um recorte irmão e independente — a mesma relação lida três
  vezes é desperdício que nenhum eixo enxerga hoje, e merece o seu próprio documento.
- **Regra nova no catálogo.** Nenhuma. As arestas são o insumo; julgar "a fonte grande está no
  build side" precisa do tamanho da fonte cruzado com a aresta, e isso é a fase seguinte.
- **Eixo novo no fingerprint.** `join_intensity` continua estrutural em C2. Enriquecê-lo com o
  grafo é decisão do recorte que consumir estas arestas.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 As arestas saem de `sql_metrics.py`, não de um módulo novo

O módulo já percorre `sparkPlanInfo`, já sabe quais nós são scan (`_scan_of`) e já extrai a
relação de cada um. As arestas saem da mesma passada.

**Alternativa recusada:** `facts/sql_graph.py`, lendo o mesmo event log pela terceira vez.
Seguiria a letra do precedente `data_quality`/`graph`, que leem o mesmo `.py` que
`pyspark_ast` com óticas diferentes. O que separa os dois casos é o **tamanho do que se
duplica**: lá o compartilhado seria uma fórmula de cinco linhas — e o repositório registrou
por escrito que preferia duplicá-la, porque o que garante que as cópias concordam é teste, não
import. Aqui seria o parser da árvore mais a detecção de scan, e duas cópias disso divergem
por conta própria.

**Alternativa também recusada:** módulo separado importando o walk de `sql_metrics`. Não
duplica nada e fura a doutrina de independência entre extratores, criando um acoplamento que o
repositório hoje não tem em lugar nenhum.

A razão que C1 deu para deixar join fora — *"o mesmo mecanismo as alcança, e emiti-las agora
seria contrato grande antes de existir consumidor"* — **caducou**: o consumidor existe.

### 3.2 Toda fonte do lado, com a distância

Uma aresta por `(join, relação, lado)`, carregando `via_joins`: quantos joins existem entre
aquele scan e este join. Fonte que entra direto tem `via_joins: 0`.

```
Plano:  (A join B) join C

Join externo, lado esquerdo:   A via_joins 1,  B via_joins 1
Join externo, lado direito:    C via_joins 0
Join interno, lado direito:    B via_joins 0
```

**Alternativa recusada:** nomear só a fonte direta, deixando o lado com join aninhado sem
fonte. O join externo diria apenas `C`, e o outro lado ficaria mudo — perdendo justamente a
informação de que há duas tabelas entrando ali.

**Alternativa recusada:** toda fonte, sem `via_joins`. Apaga a diferença entre a tabela que
entra direto no broadcast e a que chega três joins abaixo, e essa diferença muda o que a
recomendação deveria ser.

### 3.3 `position` é observação; `side` é derivação, e pode ser `unknown`

A aresta carrega os dois:

- `position`: `left` ou `right`. É a posição na árvore, sempre observável, porque
  `sparkPlanInfo` publica `children` em ordem.
- `side`: `build`, `stream` ou `unknown`. Derivado do token `BuildLeft`/`BuildRight` do
  `simpleString`.

`SortMergeJoin` não tem lado de build — os dois lados são ordenados e mesclados. Atribuir um
seria afirmar o que o plano não diz, e o fact sairia plausível e falso.

**Alternativa recusada:** omitir a aresta quando não há build side. Perderia a estrutura de
todo join que não é broadcast, que é a maioria dos joins caros.

### 3.4 Profundidade tem teto declarado, e estourar vira lacuna

`_walk` é recursivo. Um `sparkPlanInfo` suficientemente profundo estoura a pilha do Python
antes de qualquer verificação, e o extrator morreria com `RecursionError` no meio de uma
extração que já produziu facts válidos.

O teto é declarado no módulo, e a árvore que o excede produz `spark.sql.unresolved` com razão
`plan_too_deep`, nomeando a profundidade observada. Falha com nome é diagnóstico; falha por
estouro de pilha é acidente.

---

## 4. Modelo de facts

### 4.1 `spark.sql.join`

Um por nó de join, por execução.

```
subject   {type: plan_node, node_id, operator, relation: "", symbol, execution_id}
attrs     {strategy, join_type, build_side}
measures  {inputs_left, inputs_right}
```

`build_side` reproduz o vocabulário que `plan.join` já usa (`left`, `right`, `""`), para que
quem leia os dois não precise traduzir. `inputs_left`/`inputs_right` são as contagens de
fontes de cada lado — é o que distingue um join de duas tabelas de um join cujo lado esquerdo
é uma árvore de cinco.

### 4.2 `spark.sql.join_input`

Uma por `(join, relação, lado)`.

```
subject   {type: plan_node, do JOIN}
attrs     {relation, position, side, strategy}
measures  {via_joins}
```

Ancorada no **join**, e não no scan, porque a afirmação é sobre o join: "esta junção consome
esta fonte deste lado". `same_subject` agrupa por join, que é a entidade sobre a qual uma
regra futura vai falar.

### 4.3 `spark.sql.unresolved`

Razões novas: `join_side_without_source` e `plan_too_deep`. As de C1 continuam.

---

## 5. Superfície

**Nenhuma.** Os kinds saem do extrator que `analyze sql-metrics` já executa e que a tool
`sparkforge_analyze_sql_metrics` já expõe. Nenhum verbo novo, nenhuma tool nova, nenhuma
entrada nova em `manifest.json` ou `parity.yaml`.

É consequência de §3.1: estender o extrator existente estende a superfície existente.

---

## 6. Erros, cada um com o seu nome

| Situação | Saída |
|---|---|
| Lado do join sem nenhum scan abaixo | `unresolved`, razão `join_side_without_source`, nomeando o `node_id` do join e a posição. Subquery, relação em cache e `Scan ExistingRDD` não são fonte nomeável |
| Operador de join sem `BuildLeft`/`BuildRight` | `side: unknown` na aresta. Não é lacuna: `position` continua observado, e a maioria dos joins caros cai aqui |
| Árvore mais profunda que o teto | `unresolved`, razão `plan_too_deep`, com a profundidade observada |
| Nó de join sem nenhum filho | `unresolved`, razão `join_without_children` — plano malformado, e o extrator não inventa a estrutura que falta |

---

## 7. Testes

### 7.1 Sem domínio de fixture novo

Os cenários entram em `fixtures/sql_metrics/`, que já tem `tests/test_fixtures_golden_sql_metrics.py`.
O artefato é o mesmo e o extrator é o mesmo; criar domínio novo aqui seria cerimônia sem
conteúdo, e ainda exigiria um segundo módulo golden lendo o mesmo corpus.

| Cenário | Prova |
|---|---|
| `join_broadcast_build_side` | a fonte nomeada do lado de build, com `side: build` |
| `join_nested_via_joins` | `(A join B) join C`: `via_joins` correto nos dois níveis |
| `join_sort_merge_without_build` | `side: unknown` e `position` preenchido |
| `join_side_without_source` | lado que lê de `ExistingRDD`: lacuna nomeada, e o outro lado continua com a aresta |

### 7.2 A garantia sobre o corpus inteiro

**Toda `spark.sql.join_input` aponta para um `node_id` que é join naquela mesma execução, e
toda `relation` que ela nomeia aparece num `spark.sql.scan` da mesma execução.**

Aresta que aponta para o nada é pior que aresta ausente: ela parece grafo. Verificada sobre o
corpus inteiro, e não por cenário — um erro de índice na numeração de preorder passaria em
cada cenário isolado e quebraria aqui.

---

## 8. Documentação

- `docs/superpowers/STATUS.md`: a fase, os dois kinds e o que ficou de fora.
- `README.md`: os números de extratores e kinds **medidos**. Nenhum verbo novo a documentar.
- `knowledge/`: nada novo. Este documento não introduz limiar nem fonte externa.

---

## 9. Critérios de aceite

1. Um plano `(A join B) join C` produz `via_joins: 1` para A e B no join externo e
   `via_joins: 0` para C.
2. `BroadcastHashJoin` com `BuildRight` produz `side: build` para as fontes do filho direito e
   `side: stream` para as do esquerdo.
3. `SortMergeJoin` produz `side: unknown` nos dois lados, com `position` preenchido, e nenhuma
   aresta omitida.
4. Lado sem scan nomeável produz `join_side_without_source` e **não** impede a aresta do outro
   lado.
5. Toda `join_input` referencia um join real e uma relação observada na mesma execução.
6. Árvore acima do teto produz `plan_too_deep`, nunca `RecursionError`.
7. Suíte completa verde, gate de números verde, e os goldens de `fixtures/sql_metrics/`
   regravados com a leitura de cada um.
