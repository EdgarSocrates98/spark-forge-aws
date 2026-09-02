# SparkForge AWS — A ponte entre o código e a execução: o callsite que o Spark já escreve

**Data:** 2026-09-02
**Status:** **proposta**.
**Origem:** terceiro incremento de `prompt_evo_graph_economy.md` (FASE 6).
**Depende de:** [incremento 1](2026-09-02-sparkforge-recall-economia-design.md) (gate de
recall, PR #28) e [incremento 2](#) (`code path`, PR #29).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. A lacuna, medida

O motor tem 146 regras. Medido em 2026-09-02, por `requires_facts`:

| | |
|---|---|
| Regras que usam **só** fato estático (`callgraph.*`, `graph.*`, `pyspark.*`, `sql.*`) | **20** |
| Regras que usam **só** fato de runtime (`spark.*`, `glue.*`, `emr*`) | **35** |
| Regras que **cruzam** os dois | **0** |

Zero. O motor lê código e lê execução, e nunca os põe lado a lado — que é exatamente o
que a FASE 6 do prompt de origem pede.

## 2. A âncora existe, está intacta, e ninguém a consome

`spark.stage.*` carrega `subject = {"type": "stage", "symbol": <Stage Name>, "stage_id": N}`,
e `sparkforge/facts/event_log.py:584` guarda o `Stage Name` **verbatim** do event log.

O Spark escreve esse nome no formato de **callsite**: `<método> at <arquivo>:<linha>` —
`collect at job.py:42`, `count at etl.py:87`. É a mesma string que aparece na Spark UI.

**Ou seja: a ponte já está no artefato, e sempre esteve.** O que falta é lê-la.

## 3. Objetivo

Um kind derivado que extrai o callsite do nome do stage, e **uma** regra que o usa para
transformar suspeita estática em achado corroborado por execução.

### Não-objetivos, com razão registrada

- **Atribuir custo a um stage por causa de uma linha de código.** Seria violar a regra 13
  do `CLAUDE.md` — "nunca atribua custo a uma causa". O callsite diz *onde nasceu o RDD*,
  não *quanto aquela linha custou*.
- **Correlacionar algoritmo GraphFrames com stage.** `connectedComponents` roda em Scala,
  e o callsite aponta para dentro da biblioteca (`GraphFrame.scala`), não para o `.py` do
  operador. Cruzar isso exigiria mapa de biblioteca que ninguém publica.
- **Inferir callsite quando o nome não tem a forma.** Nome sem ` at <arquivo>:<linha>` sai
  `unresolved` nomeado. É a instrução literal do prompt: *"falta de artefato runtime como
  `unresolved`, não como negativo"*.
- **Regra sobre fan-in alto com shuffle.** O prompt a lista, e ela **não tem fonte**:
  `fan_in > N` é limiar inventado, e "chamada de muitos lugares e faz shuffle" não é
  defeito — é descrição. Fica como veto escrito.

## 4. Decisões de desenho

### D-1 — o callsite é kind DERIVADO, e o extrator o decide uma vez

`spark.stage.callsite`, no molde de `tf.graphframes.jar` e `ctm.event_logic`: o parser roda
no extrator, e a regra fica com condição simples sobre o kind já decidido.

A alternativa — regex no `when` da regra — foi recusada pela razão que a área `SF-GRAPH`
já pagou: `engine._where_matches` não casa padrão, e pôr a decisão na regra faria cada
regra nova reimplementar o parse.

### D-2 — o parser aceita a forma que o Spark escreve, e recusa o resto

Aceita `<método> at <arquivo>:<linha>`, com `<arquivo>` terminando em `.py`. Recusa, com
razão nomeada em `attrs.reason`:

| Razão | Exemplo |
|---|---|
| `sem_forma_de_callsite` | `mapPartitions` sem ` at ` |
| `arquivo_nao_python` | `count at GraphFrame.scala:112` — é biblioteca, não código do operador |
| `linha_nao_numerica` | ` at job.py:<unknown>` |

**`arquivo_nao_python` não é defeito e não é lacuna.** É a fronteira do não-objetivo da
§3: stage nascido dentro de biblioteca Scala não tem linha no `.py` do operador, e
inventar uma seria pior que recusar.

### D-3 — a regra corrobora, e é isso que ela acrescenta

`SF-PY-002` já diz *"`collect()` sem limite na cadeia"* — leitura **estática**, `status:
structural`. A regra nova dispara quando **o mesmo callsite** aparece num stage cujo
`task_input` mede o volume que de fato chegou.

A diferença é de natureza, não de grau: uma diz *"este código pode puxar tudo para o
driver"*, a outra diz *"este código puxou N bytes para o driver, e aqui está o stage"*.
A segunda é `confirmed`, e o eixo `confirmed`/`structural` já existe no catálogo.

**Sem event log a regra não dispara** — sai em `refused` com a medida que a destravaria.
É a mesma disciplina de `RuntimeContext` das quatro plataformas de EMR.

### D-4 — área própria, `SF-BRIDGE`

Não entra em `SF-PY` (que é estático) nem em `SF-SPARK` (que é runtime): a regra é sobre a
**junção**, e enfiá-la num dos dois faria o coordenador daquela área receber um caso cujo
artefato ele não sabe pedir. Rota própria em `routing.yaml`, no molde de `AGENT-082`.

## 5. Testes e gates

- **O contrafactual da corroboração:** o mesmo código com e sem event log produz achados
  **diferentes** — `structural` sozinho contra `confirmed` + `structural`. Sem isso, a
  regra não cruza nada.
- **O callsite casa por arquivo E linha**, nunca só por arquivo: dois `collect` no mesmo
  arquivo são dois callsites, e casar por arquivo os confundiria.
- Cada uma das três razões de recusa tem fixture.
- Golden positivo e negativo; todo kind novo em algum golden; extrator nas duas listas
  manuais de teste.
- Gates de sempre, mais `check_recall_economy.py` (o gold set cresce se a regra nova
  ancorar símbolo).

## 6. Critérios de conclusão

- `spark.stage.callsite` sai de nome de stage com a forma, e `unresolved` nomeado do resto.
- A regra cruza estático e runtime — e o contrafactual prova que cruza.
- Sem event log, recusa nomeada, não silêncio.
- O veto de fan-in está escrito com a medida que o destravaria.

## 7. Fora do escopo

| | |
|---|---|
| Comunidades e god nodes | incremento 4 (F8) |
| `GraphifyJsonAdapter` | incremento 5 (F1.6) |
| Callsite de stage nascido em biblioteca Scala | recusa declarada, não lacuna |
| Atribuição de custo a linha de código | proibido pela regra 13 |
