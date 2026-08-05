# SparkForge AWS — Fase 6a: grafo com Spark (`SF-GRAPH`)

**Data:** 2026-08-05
**Status:** não implementado nesta data.
**Abre:** o roadmap de bancos, `docs/superpowers/specs/2026-08-03-sparkforge-roadmap-bancos.md`
§3.1 — a primeira das quatro, e a única que não é um banco.
**Base:** [Fase 5c](2026-08-03-sparkforge-fase5c-dq-design.md) fixou o padrão de
extrator de AST com correlação por escopo; [Fase 5d](2026-08-04-sparkforge-fase5d-emr-serverless-design.md)
fixou o padrão de pesquisa antes do código e de fronteira medida entre áreas.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o motor é cego a grafo, e o silêncio não é contado

Dê ao motor, hoje, um job que constrói um `GraphFrame` e roda
`connectedComponents`. Medido em `sparkforge/facts/pyspark_ast.py`:

- `GraphFrame(v, e)` é `ast.Call` com `func=ast.Name`, e o laço central descarta
  tudo que não é `ast.Attribute` (`pyspark_ast.py:255`), exceto quatro casos
  codificados. **Não vira nada.**
- `g.connectedComponents()` passa o filtro, vira `method = "connectedComponents"`,
  não casa nenhum dos dez `frozenset` de `pyspark_ast.py:51-90`, e sai.
  **Não vira fact, e não vira `unresolved`** — as cinco razões de
  `pyspark.unresolved` não cobrem "método desconhecido".
- `for i in range(10): g.aggregateMessages(...)` **não emite nem `pyspark.loop`**:
  aquele fact só nasce se o corpo contiver ação conhecida ou escrita
  (`pyspark_ast.py:1043`). Logo `SF-PY-004` não dispara, e `ROUTE-004` também não.

O único fact que sobra é `pyspark.action` pelo `.show()` final — e ele tem **zero
consumidores**: nenhum `requires_facts` do catálogo o declara.

Isto é pior que uma lacuna de regra. O invariante do projeto é que o que o motor
não sabe ler vira `unresolved` **contado**; aqui o grafo é **invisível**, e a
saída é indistinguível de um arquivo que não tem grafo nenhum.

## 2. Objetivo

Uma área `SF-GRAPH` que julga **código PySpark que processa grafo com
GraphFrames**, a partir do `.py`. Dois eixos: como o grafo é processado, e se a
biblioteca **existe** no runtime onde o job roda.

**Critério de sucesso central:** um job com `connectedComponents` sem
`checkpointDir` produz achado citando `fact_id`; um job que usa GraphFrames num
runtime sem jar disponível produz achado; e um job de grafo escrito corretamente
não produz achado nenhum, nem por `SF-DQ` nem por `SF-PY`.

### Não-objetivos, com razão registrada

| Fora de escopo | Razão |
|---|---|
| **GraphX** | **Não tem API Python.** `graphx-programming-guide` é Scala-only e não existe módulo `pyspark.graphx` em release nenhuma. Um extrator de AST sobre `.py` nunca o verá. Não é adiamento: é impossibilidade medida |
| **Modelagem de grafo** | Se um atributo deve ser vértice ou propriedade é julgamento sobre o domínio, não sobre o código. Vai para `knowledge/`, como o roadmap já registrou |
| **Neptune** | Fase própria (`SF-NEP`), terceira do roadmap. Esta fase não lê banco nenhum |
| Executar o job ou o algoritmo | O motor lê artefato e julga |
| Recomendar algoritmo alternativo | "Use `labelPropagation` em vez de `connectedComponents`" depende da semântica do problema, que o código não descreve |

## 3. Decisões de desenho

### D-1 — extrator próprio, e a regra de laço se reescreve

`sparkforge/facts/graph.py`, namespace `graph.`. A alternativa medida era pôr os
algoritmos nos `frozenset` de `pyspark_ast.py` — eles **são** ações de verdade, e
isso faria `SF-PY-004` e a cadeia de call graph enxergarem grafo de graça.

Recusada porque muda o comportamento de regras existentes sobre código que hoje
elas ignoram: todo golden de `pyspark` precisaria ser reavaliado, e a fronteira
entre `SF-PY` e `SF-GRAPH` deixaria de existir por construção.

**O custo é real e vai declarado:** `pyspark.loop` não enxerga trabalho de grafo,
então a regra de "laço com algoritmo de grafo dentro" é **reescrita** dentro de
`SF-GRAPH`, sobre fact próprio. Duas regras acusam o mesmo defeito em dois
vocabulários. Isso é preço da isolação, não descuido.

### D-2 — vocabulário fechado, e por que aqui isso é honesto

`data_quality.py` **recusa** reconhecer por nome: reconhece PyDeequ pela forma da
cadeia e Great Expectations pela chave literal, *"cada uma pela FORMA e nunca por
lista de nomes"* (`data_quality.py:17-21`). A razão é que nome de check é aberto —
o usuário inventa o dele.

Aqui é o inverso: **a API do GraphFrames é finita**. `connectedComponents`,
`pageRank`, `shortestPaths`, `labelPropagation`, `triangleCount`, `bfs`,
`aggregateMessages`, `pregel`. Um `frozenset` é a descrição correta do domínio,
não um atalho.

A razão vai escrita no cabeçalho do módulo, senão a próxima pessoa lê a diferença
como inconsistência com o precedente.

### D-3 — a fase precisa rastrear `import`, que nenhum extrator faz

Nenhum extrator do repositório rastreia import. `data_quality.py` declara isso
como decisão (`:17-21`), e `pyspark_ast.py` também não o faz.

Mas a regra de disponibilidade afirma **"este job usa GraphFrames"**, e a
evidência honesta disso é o `from graphframes import GraphFrame` — não a chamada
de método, que qualquer `getattr` esconderia, e não a construção, que um alias
mudaria de nome.

Vira kind próprio, `graph.import`. É capacidade nova, e o limite dela vai escrito:
import dentro de função, import condicional e `importlib` são formas que o extrator
precisa decidir se lê ou conta como `unresolved` — a Task de implementação mede
qual, não este spec.

### D-4 — `runtime_scope` aqui faz o oposto do que a Fase 5b recusou

`rules/catalog/emr-infra.yaml:8-19` registra uma decisão **contra** usar
`runtime_scope` naquela área: a série vinha de `measures.release_major` do próprio
fact, e um `{emr: ...}` seria segundo guarda sobre o mesmo dado — apagaria a área
inteira num `judge` sem `--emr`.

Aqui a situação é a inversa, e por isso a decisão também é:

- O artefato é `.py`. **Não há release label em fact nenhum.**
- Sem saber o runtime, **é impossível afirmar** que falta jar para aquele Spark.
- Portanto regra pulada por `runtime_scope`, com a razão registrada em `skipped`,
  é a **resposta certa** — não um efeito colateral.

O motor já diz isso da forma certa: `engine.py:235-238` põe a regra em `skipped`
com `reason: runtime_scope`, nunca em descarte silencioso.

### D-5 — a fronteira com `SF-DQ` e `SF-PY` é medida, não afirmada

Dois vizinhos, e os dois foram medidos:

- **`SF-DQ-003`** (`data-quality.yaml:272-291`) acusa "validação recomputa o
  lineage" quando `attrs.target_persisted: false` **e** `attrs.action_after_check:
  true`, sobre `dq.check`. "Aresta não persistida varrida a cada iteração" é a
  mesma forma com outro sujeito.
- **`SF-PY-008`** (`pyspark.yaml:303`) acusa `.cache()` sem `.unpersist()` no
  escopo, sobre `pyspark.cache`. Um job de grafo que persiste arestas
  **corretamente** pode cair nela.

A Fase 5d mediu que fronteira afirmada não vale nada: classificar por prefixo
daria 15 regras a `SF-EMR` e zero a `SF-EMRS`, com o teste passando vacuamente.
Esta fase entrega teste de fronteira nas **três** direções — `SF-GRAPH` × `SF-DQ`,
`SF-GRAPH` × `SF-PY` —, comparando pela área declarada e não por prefixo de id.

## 4. Facts

| Kind | Quando | Carrega |
|---|---|---|
| `graph.import` | `import` de GraphFrames visível | `symbol`, `form` (`from`/`plain`), `measures.line` |
| `graph.construction` | um `GraphFrame(...)` é construído | `vertices_ref`, `edges_ref`, `inside_loop`, `measures.line` |
| `graph.algorithm` | um algoritmo do vocabulário é chamado | `name`, `receiver`, `inside_loop`, `has_max_iter`, `max_iter_literal`, `measures.line` |
| `graph.checkpoint_dir` | `setCheckpointDir` visível no módulo | `literal`, `measures.line` |
| `graph.source_persisted` | decisão sobre vértices/arestas do grafo | por construção: `vertices_persisted`, `edges_persisted` — **omitidas** quando indecidível |
| `graph.unresolved` | leitura impossível | vocabulário fechado: import não literal, receptor sem raiz nomeada, argumento não literal onde a regra exige número |
| `graph.module_analyzed` | sempre | sentinela: quantos imports, construções, algoritmos, pontos cegos |

A sentinela sai **mesmo quando nada foi encontrado**. É o que distingue "não há
grafo neste arquivo" de "não consegui ler", e é o invariante que a §1 mostra
quebrado hoje.

## 5. Regras candidatas

Nenhuma entra sem fonte. A pesquisa da §6 confirma ou **veta** cada uma, e o veto
fica escrito no cabeçalho do catálogo.

**Eixo de uso:**

| Pergunta | Por que é cara |
|---|---|
| `connectedComponents` sem `checkpointDir` | A biblioteca documenta que o algoritmo exige checkpoint; sem ele o lineage cresce por iteração até derrubar o driver |
| Algoritmo iterativo sem limite de iteração | `maxIter` ausente, ou Pregel sem critério de parada |
| Vértices ou arestas não persistidos, varridos a cada iteração | Recomputação do lineage inteiro por iteração — a forma de `SF-DQ-003` com outro sujeito |
| `GraphFrame` construído dentro de laço | Reconstrução por iteração, e o plano nunca reusa |

**Eixo de disponibilidade:**

| Pergunta | Mecanismo |
|---|---|
| GraphFrames num runtime onde **nenhum jar existe** | `runtime_scope`. Medido: Glue 4.0 (Spark 3.3.0) e EMR 6.8.0–6.11.1 (Spark 3.3.0–3.3.2) não têm artefato em repositório nenhum |
| Job usa GraphFrames e o IaC não declara `--extra-jars` nem `--packages` | Cruza `graph.import` com `tf.attribute`. `SF-GLUE-004` é precedente de regra que cruza extratores |

**A severidade proposta não é a final.** A fonte decide; onde ela não disser, a
nota `field-heuristic` vai junto, no padrão de `rules/catalog/README.md:57`.

## 6. Pesquisa, antes do código

`knowledge/` tem **zero linhas** sobre grafo — `grep -i "grafo\|graph"` só devolve
grafo de *chamadas*, que é outra coisa. A fase começa por `knowledge/graph/`, no
formato do repositório: corpo com o link do espelho executável, seção `## Fontes`
com `Título. URL (retrieved AAAA-MM-DD)`, e os parágrafos finais que declaram **o
que a fonte não sustenta**.

Perguntas que decidem regra:

1. A documentação do GraphFrames **exige** `checkpointDir` em
   `connectedComponents`, ou recomenda? Exigir e recomendar dão severidades
   diferentes, e inventar a diferença seria o defeito.
2. Qual o default de `maxIter` em cada algoritmo? **Ausente pode significar "roda
   até convergir"**, que é diferente de "sem limite" — e uma regra que confunde os
   dois acusa quem escreveu certo.
3. As duas células de Spark 3.3 continuam sem jar? A medição de 2026-08-05 diz que
   sim, pelo Maven Central (`io.graphframes`) e pelo spark-packages
   (`graphframes`); a fonte precisa ficar datada, porque isso muda com um release.
4. A AWS documenta GraphFrames em algum lugar? A medição diz que **não** — não é
   aplicação do EMR, não é módulo do Glue, não há blog. Isso precisa ficar escrito,
   porque é o que sustenta a regra do IaC: se a AWS não instala, alguém tem que
   declarar.

## 7. Superfície

| Onde | O quê |
|---|---|
| `sparkforge/facts/graph.py` | extrator; `EMITTED_KINDS` fechado |
| `sparkforge/adapters/{_core,cli,tools}.py` | `analyze graph` |
| as duas listas `EXTRACTORS` | adições manuais independentes |
| as quatro listas de `tests/test_adapters_tools.py` | medidas na Fase 4b, confirmadas na 5d |
| `sparkforge/collect/base.py` | `ARTIFACT_KINDS` — a **sexta** superfície, que a Fase 5d achou por `ValueError` na escrita do manifesto |
| `rules/catalog/graph.yaml` | área `SF-GRAPH` |
| `fixtures/graph/` | domínio novo, golden bidirecional |
| `knowledge/graph/` | pesquisa com fonte datada; `sources.lock.json` ganha as URLs **na task do catálogo**, porque a watchlist agora tem duas origens |
| coordenador | decisão da task de fechamento — ver §9 |
| `parity.yaml`, `manifest.json` | o verbo novo nas cinco superfícies declarativas |

Áreas 14 → 15. Extratores 18 → 19.

## 8. Testes

- Golden bidirecional por fixture, regenerado por `scripts/regen_fixtures.py`,
  nunca escrito à mão.
- Toda regra com golden **positivo e negativo**, e **nenhuma condição apagável
  sem deixar golden vermelho** — a verificação condição a condição que a Fase 4c
  instituiu e a 5d refinou até pegar duas conjunções soltas.
- **Todo ramo de `severity_by` com golden**, que desde 2026-08-05 é invariante do
  repositório: `test_every_severity_branch_has_a_golden_that_produces_it`.
- Todo kind de `EMITTED_KINDS` em algum golden, com o domínio registrado em
  `tests/test_fixtures_kind_coverage.py`.
- **Fronteira nas três direções**, comparando pela área declarada — o `loader`
  não propaga `area:` para dentro da regra, medido na Fase 5d.

## 9. O que fica em aberto para a implementação decidir

| Questão | Critério de decisão |
|---|---|
| Coordenador próprio ou `pyspark-code-reviewer` estendido | O critério da Fase 4c: coordenador novo exige **fronteira de despacho** medida. A 5d mediu que fronteira de catálogo **não** é fronteira de despacho, e manteve o coordenador estendido por não haver discriminador em dado |
| Até onde o extrator segue `import` | Import em função, condicional, `importlib`, alias. Medir o que o corpus real usa, e contar como `unresolved` o que passar |
| Se `graph.source_persisted` é kind próprio ou atributo | A Fase 5d mediu que correlação entre dois kinds casa objeto errado quando há vários sujeitos no mesmo diretório (`D-5d-17`). Medir antes de separar |

## 10. Critérios de conclusão

1. `graph.py` não importa PySpark, não chama AWS, não lê nada além do `.py`.
2. Toda regra tem golden positivo **e** negativo, e nenhuma condição é apagável
   sem deixar golden vermelho.
3. Todo ramo de `severity_by` tem golden.
4. Todo kind de `EMITTED_KINDS` aparece em algum golden.
5. `graph.module_analyzed` sai mesmo quando o arquivo não tem grafo.
6. Nenhuma regra `SF-GRAPH` dispara sobre fixture de `SF-DQ` ou `SF-PY`, nem o
   contrário. Provado por teste, não afirmado.
7. Toda regra cita fonte com data, ou carrega `origin: field-heuristic` com nota.
8. As perguntas 1 e 2 da §6 estão respondidas por escrito, com fonte — e onde a
   fonte não fechar, o limite está declarado.
9. As seis superfícies concordam, e `sync_skills.py --check` está limpo.
10. `STATUS.md` mede os números novos em vez de copiá-los, e a linha `SF-GRAPH` do
    roadmap de bancos passa a apontar para esta fase como concluída.
