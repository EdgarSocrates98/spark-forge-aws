# SparkForge AWS — Fase 6a: grafo com Spark (`SF-GRAPH`)

**Data:** 2026-08-05
**Status:** **implementado** em 2026-08-05, em sete tasks. Este documento **não foi
reescrito**: ele registra o que se pretendia na data. A §11 lista os pontos em que a
medição da implementação o tornou **errado** — leia-a antes de citar qualquer tabela
daqui.
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

---

## 11. Desvios — onde a medição tornou este documento errado

Registrados na implementação como `D-6a-1`…`D-6a-48`, em
[`../plans/2026-08-05-sparkforge-fase6a-graph.md`](../plans/2026-08-05-sparkforge-fase6a-graph.md).
Aqui ficam só os que **contradizem o texto acima** — não a lista inteira. A ordem é a das
seções que eles invalidam.

### §4 — a tabela de facts está errada em três lugares

**`graph.source_persisted` não existe** (`D-6a-7`). Um kind separado teria de ser reunido
ao `graph.construction` **por nome de variável**, e a Fase 5d já mediu (`D-5d-17`) que essa
correlação casa objeto errado quando há dois sujeitos no mesmo arquivo — dois
`GraphFrame(...)` no mesmo `.py` são o caso literal. `vertices_persisted` e
`edges_persisted` viraram atributos do próprio `graph.construction`. São **6 kinds**, não
7. A §9 autorizava a decisão; a §4 é que ficou errada.

**`has_max_iter` e `max_iter_literal` não existem, e o nome é proibido** (`D-6a-22`). Com a
regra de limite de iteração vetada (abaixo), um atributo chamado `has_max_iter` seria a
regra vetada entrando pela porta dos fundos — bastaria alguém escrever
`where: {attrs.has_max_iter: false}`. O fact carrega `iteration_arg`, que **nomeia o
parâmetro que veio**, porque sem isso nada distingue `maxIter` de `tol`. Há teste que varre
o corpus e reprova se qualquer fact passar a carregar `has_max_iter`, `max_iter_missing`,
`iteration_limited`, `unbounded` ou `has_iteration_limit`.

**A decisão de checkpoint vem pronta do extrator, e a §4 não previa isso** (`D-6a-9`,
`D-6a-12`). `engine._where_matches` compara por igualdade e **reprova caminho ausente**, e
`_expr_matches` engole o `ExprError` devolvendo `False` — logo nenhuma regra deste catálogo
consegue exprimir "o código não declarou saída nenhuma", que é o caso comum. Quem enxerga
as saídas de uma vez é o extrator: `graph.algorithm` carrega `checkpoint_required` **já
decidido** e `checkpoint_configured_in_module` no mesmo fact. E as saídas são **cinco** no
`.py`, não três: além de `algorithm="graphx"`, `checkpointInterval<=0` e
`use_local_checkpoints=True`, o job pode configurar `spark.checkpoint.dir` ou
`spark.graphframes.useLocalCheckpoints` por `spark.conf.set` dentro do próprio arquivo —
ignorá-las faria a regra P0 disparar sobre código que resolveu o problema na linha de cima.
Há um sexto estado, em que a conf é ilegível e `checkpoint_required` sai **ausente**: ponto
cego contado, não acusação.

### §4 e §5 — `pregel` não é método, e o extrator precisou de mecanismo novo

`pregel` é `@property` nas duas linhagens, assim como `triplets`, `degrees`, `inDegrees` e
`outDegrees` (`D-6a-3`). Um `frozenset` casado contra `ast.Call` **não emitiria fact para o
Pregel**, que é justamente o único algoritmo cujo limite de iteração o usuário controla de
fato. A solução casa `ast.Attribute` em contexto `Load` que não é o `func` de uma `Call` e
percorre a cadeia **para fora** por um mapa de pais, recuperando `setMaxIter(10)` de
`g.pregel.setMaxIter(10)...run()` (`D-6a-10`). Todos os outros extratores do repositório
caminham só para dentro; este é o primeiro que precisou de mapa de pais.

O vocabulário também tem **dois níveis**, e a §5 supõe um só (`D-6a-11`): `find`, `validate`
e `degrees` são nomes que qualquer objeto de usuário pode ter — `"abc".find("b")` viraria
`graph.algorithm` —, então só são lidos quando o módulo **importa** GraphFrames.
`cache`/`persist`/`unpersist`, que o `GraphFrame` de fato expõe, ficaram **fora** do
vocabulário de algoritmo: `pyspark.cache` já os emite sobre o mesmo artefato, e reemiti-los
duplicaria o sujeito de `SF-PY-008` (`V-GR-4`).

### §5 — duas das quatro regras candidatas não existem

**"Algoritmo iterativo sem limite de iteração" foi VETADA, e não por falta de fonte**
(`D-6a-4`, vetos `V-GF-1` e `V-GF-2` no cabeçalho de `rules/catalog/graph.yaml`). A fonte
fechou no sentido **oposto**: em nenhum dos dezesseis algoritmos com noção de iteração a
ausência é defeito. Em seis é `TypeError`/`AssertionError` — código que não roda; em três é
default documentado; em `pageRank` o modo `tol` é oficial e recomendado; e em
`connectedComponents` a doc diz textualmente *"Default is `Integer.MAX_VALUE` (unlimited).
It is generally not recommended to change this value."*

**A regra do IaC não entrou** (`D-6a-30`, veto `V-GR-1`), por **dois** motivos
independentes — basta um. (a) `engine._absent_satisfied` compara **só `kind`**, e o kind é
`tf.attribute` dos dois lados: o que muda é `attrs.key`, e não existe `absent` filtrado por
atributo nem `where` negado. O que fecharia é um kind derivado no extrator de Terraform, no
molde de `tf.observability.spark_ui` — capacidade que esta fase não construiu. (b) Para
Spark 3.3 **não há artefato publicado em linhagem nenhuma**, então qualquer `--extra-jars`
de GraphFrames ali aponta necessariamente para outro minor, e a pesquisa recusa afirmar que
isso roda. `SF-GRAPH-002` dispara nos **dois** lados do par de fixtures, e o `--extra-jars`
aparece no texto do achado como tentativa de contorno.

Restaram **quatro** regras: `SF-GRAPH-001` (checkpoint, P0), `SF-GRAPH-002`
(disponibilidade, P1), `SF-GRAPH-003` (arestas não persistidas, P2) e `SF-GRAPH-004`
(algoritmo em laço, P2). Nenhuma declara `severity_by` (`V-GR-3`) nem `threshold`, e a
razão é o corpus, não esquecimento: os discriminadores plausíveis não têm caso dos dois
lados dentro da mesma regra, e ramo sem golden é severidade que ninguém mediu. O único
limiar numérico com fonte primária desta área — `checkpointInterval > 2` — ficou como
`V-GR-2`, à espera de fixture (`D-6a-31`).

### D-4 — o escopo é por faixa de Spark, e o mecanismo teve de ganhar capacidade nova

A D-4 acerta o **princípio** e erra a **unidade**. A razão de não haver jar não é "a versão
é antiga": é que **nenhum artefato foi publicado para Spark 3.3 em linhagem nenhuma** —
`0.8.2` para em 3.2, `0.8.3` começa em 3.4, `io.graphframes` compila contra 3.5 (`D-6a-6`).
São 9 das 34 células da matriz, e o discriminador é o **minor de Spark**, não a célula de
release: escrito por release, o escopo envelheceria a cada release nova da nuvem, que é o
que `V-AV-1` proíbe.

Escrever isso exigiu mecanismo que não existia (`D-6a-29`). `version_scope.in_scope` lia
**um** spec por chave, e as alternativas com o que havia falham as duas: `"==3.3"` casa
`3.3.0` e **reprova** `3.3.1` e `3.3.2` — os Sparks de EMR 6.10.x e 6.11.x, quatro das nove
células, que sumiriam em silêncio; `">=3.3"` sozinho estenderia a acusação a 3.4 e 3.5,
onde ela é falsa. `version_scope._specs` passou a aceitar **uma lista** de specs numa
chave, conjugando como as chaves entre si, e `{spark: [">=3.3", "<3.4"]}` é o primeiro uso.
Lista vazia levanta `ValueError` de propósito. Mudança aditiva: nenhum `runtime_scope`
existente foi afetado.

Efeito colateral que a D-4 não previa (`D-6a-33`): dois testes de escopo presumiam que
**todo** guarda de versão é de Glue, e uma nona regra guardada por `spark` quebrava os dois.
`SPARK_VERSIONED` virou grupo próprio — a razão dele é "a afirmação só é verdadeira nesta
faixa", não "esta infraestrutura não existe aqui".

### D-5 e §10.6 — a metade "nem o contrário" do critério é falsa, e por construção

O critério 6 da §10 exige que nenhuma regra `SF-GRAPH` dispare sobre fixture de `SF-DQ` ou
`SF-PY`, "nem o contrário". A primeira metade está provada. **A segunda é falsa, e é a
construção funcionando** (`D-6a-41`): `SF-PY` dispara **16 vezes sobre `fixtures/graph/`**
— `SF-PY-008` em catorze fixtures e `SF-PY-012` em duas. Nenhum é invasão, e o critério é a
evidência e não a intenção: os dezesseis citam apenas `pyspark.cache` e `pyspark.conf_set`,
o `subject.snippet` de cada um bate com a linha do arquivo, e nenhuma das dezenove fixtures
chama `unpersist`. É `V-GR-4` funcionando — `cache`/`persist`/`unpersist` ficaram fora do
vocabulário de grafo porque `pyspark.cache` já os emite. Os dezesseis estão nomeados um a um
em `ESPERADO_PY_SOBRE_GRAFO`, com o argumento ao lado; silenciar a lista era a única saída
errada.

A porta que a D-5 supunha também não serve (`D-6a-40`): o golden de cada corpus isola o
contrato do **seu** extrator, então sobre ele a fronteira é vácua por construção — `SF-PY`
não pode disparar sobre um conjunto de facts sem nenhum `pyspark.*`.
`tests/test_rules_graph_boundary.py` roda os **três** extratores sobre os três corpora, que
é o que um agente faz numa investigação real.

### §7 — a sexta superfície não tinha entrada a fazer

`ARTIFACT_KINDS` é o vocabulário de artefato **coletado**, e `analyze graph` lê um `.py` do
repositório, cujo kind `source` já estava declarado (`D-6a-18`). Medido por falha: com o
verbo inteiro implementado e nenhuma superfície declarativa atualizada, a suíte reprovou 6
testes em 4 arquivos e **nenhum** deles em `tests/test_collect_base.py`. A sexta superfície
continua real; ela só não é atravessada por esta fase, e volta a valer se a Fase 6a ganhar
coletor. Do mesmo modo, "as quatro listas de `tests/test_adapters_tools.py`" era número
para tool de **coleta**: para uma tool de análise a lista literal é **uma**, mais uma cadeia
`if name == ...` que não é lista (`D-6a-19`).

### §8 — o corpus tem 19 fixtures, e sete existem para provar que o motor cala

A tabela do plano previa 9 (`D-6a-23`). As cinco formas legítimas de escrever certo para
`SF-GRAPH-001` ganharam uma fixture cada, mais o sexto estado em que a conf é ilegível.
Cinco fixtures disparam regra e catorze ficam com golden vazio (`D-6a-36`). O corpus carrega
Terraform, o que nenhum corpus de código fazia (`D-6a-25`), e `fonte_que_nao_compila` é a
primeira fixture do repositório a exercitar `syntax_error` — a mensagem do CPython entra no
golden, e foi medida idêntica em 3.10, 3.11 e 3.14 antes de commitar (`D-6a-26`).

### §9 — as três perguntas em aberto, respondidas

| Questão | Resposta medida |
|---|---|
| Coordenador próprio ou `pyspark-code-reviewer` estendido | **Estendido.** Há discriminador em dado — `SF-GRAPH` dispara 5 vezes em `fixtures/graph/` e **zero** nas 13 de `dq/` e nas 17 de `pyspark/` —, então o bloqueio da 5d não se aplica e a decisão foi tomada no outro eixo: nas 19 fixtures de grafo, `SF-PY` dispara 16 vezes em **14** e `SF-GRAPH` 5 vezes em **5**, e as cinco são **subconjunto** das catorze. O precedente da 5c mede o inverso (`SF-DQ` em 8 de 13 contra `SF-PY` em 2), e por isso *aquele* partiu. `AGENT-004` ganhou `findings_area: SF-GRAPH`; antes disso um case só com achados de grafo voltava de `next_step` com `recommended_agent: None` (`D-6a-45`) |
| Até onde o extrator segue `import` | Import de módulo e `from ... import`, com `guarded` quando sob `try:`; forma dinâmica vira `graph.unresolved`. O import é a **evidência independente** que libera o segundo nível do vocabulário (`D-6a-11`) |
| Se `graph.source_persisted` é kind próprio ou atributo | **Atributo**, pela razão de `D-6a-7` acima |

### §10.9 e §10.10 — os números que o fechamento mediu

Regras 77 → **81**; áreas 14 → **15**; extratores 18 → **19**; kinds 112 → **118**; tools
MCP 40 → **41**; fixtures 145 → **164** em 20 → **21** domínios; fontes vigiadas 109 →
**131**; ramos de severidade 85 → **89**. Rotas seguem **24**, porque `SF-GRAPH` entrou numa
rota existente em vez de abrir uma. Coordenadores seguem **8** e skills seguem **20**.
