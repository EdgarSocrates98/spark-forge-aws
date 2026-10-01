# GraphFrames — a API real, e as duas perguntas que decidem regra

Esta página existe porque a §6 do
[spec da Fase 6a](../../docs/superpowers/specs/2026-08-05-sparkforge-fase6a-graph-design.md)
marcou **quatro perguntas como não verificadas**, e duas delas decidem severidade
e existência de regra. Cada afirmação abaixo tem URL e `retrieved:`. Onde a fonte
contrariou o spec, a conclusão está escrita como **veto**, com o motivo — a §7 é
o bloco que vai para o cabeçalho de `rules/catalog/graph.yaml`.

A forma executável deste conteúdo será [`../../rules/catalog/graph.yaml`](../../rules/catalog/graph.yaml),
escrito na Task 5. A matriz de disponibilidade — qual release tem jar — está em
[`availability.md`](availability.md); esta página é sobre a **API**.

**Coleta desta rodada: 2026-08-05.**

Regra desta página, herdada do [`INDEX.md`](../INDEX.md): o que não foi
encontrado em fonte oficial está escrito como **não encontrado**, não como
inferência. Argumento por ausência está marcado como tal, com a página lida.

---

## 0. Os quatro veredictos, em uma linha cada

| # | Pergunta da §6 do spec | Veredicto | Consequência imediata |
|---|---|---|---|
| 1 | Checkpoint em `connectedComponents` é exigência ou recomendação? | **Exigência, e o algoritmo FALHA** — `throw new IOException(...)` no código, e a prosa diz "requires" | Base para **P0**, mas com **três** saídas legítimas que a regra tem de respeitar (§4.3) |
| 2 | Qual o default de `maxIter` por algoritmo? | **Não há um default único, e em três algoritmos `maxIter` é obrigatório sem default** | A regra "algoritmo iterativo sem `maxIter`" **não existe como enunciada**. Ver §5 |
| 3 | As duas células de Spark 3.3 continuam sem jar? | **Sim, e é pior: nenhum artefato foi publicado para Spark 3.3 em linhagem nenhuma** | Ver [`availability.md`](availability.md) |
| 4 | A AWS documenta GraphFrames? | **Não** | Ver [`availability.md`](availability.md) |

Um sub-veredicto que a pesquisa produziu e o spec não pedia: **o vocabulário do
spec está incompleto e um item dele não é chamada de método.** Ver §3.

---

## 1. Há duas APIs, não uma — e o `.py` não diz qual

A biblioteca partiu em duas linhagens em 2025-07-17, com a release `0.9.0`. Isso
importa para a **API** — não só para o jar — porque assinaturas mudaram.

| | Linhagem legada | Linhagem corrente |
|---|---|---|
| Coordenada | `graphframes:graphframes` (spark-packages) | `io.graphframes:graphframes-spark3_2.1x` (Maven Central) |
| Última | `0.8.4-spark3.5` (2024-07-03) | `0.12.1` (2026-06-17) |
| Python | **dentro do jar** (13 `.py`, medido) | pacote PyPI separado, `graphframes-py` |
| Import Python | `from graphframes import GraphFrame` | `from graphframes import GraphFrame` |

**O nome importado é o mesmo nas duas.** Um `.py` que faz
`from graphframes import GraphFrame` não distingue `0.8.2` de `0.12.1`, e nenhum
sinal no fonte o faz. Consequência direta para o extrator: qualquer regra que
dependa de comportamento **introduzido depois da 0.8.4** precisa de guarda, e a
guarda não pode vir do `.py`.

O que o fonte **sim** distingue, quando o argumento aparece literal:

- `algorithm="two_phase"` ou `"randomized_contraction"` → só existe de `0.10.0`/`0.11.0` em diante.
- `use_local_checkpoints=` → só existe de `0.9.3` em diante.
- `max_iter=` em `connectedComponents` → só existe de `0.9.0` em diante.

Isso é evidência de piso de versão, não de teto, e é a única que o artefato tem.

## 2. Construção, e os nomes de coluna que não são opcionais

A construção é uma chamada ao **construtor da classe**, com dois DataFrames:

```python
from graphframes import GraphFrame

g = GraphFrame(vertices, edges)
```

O docstring do `__init__` na tag `v0.12.1` — idêntico em substância ao da `v0.8.3`:

> `:param v:` `:class:`DataFrame`` holding vertex information. Must contain a column named **"id"** that stores unique vertex IDs.
> `:param e:` `:class:`DataFrame`` holding edge information. Must contain two columns **"src"** and **"dst"** storing source vertex IDs and destination vertex IDs of edges, respectively.

Os três nomes — `id`, `src`, `dst` — são **obrigatórios e literais**. O spec
acertou aqui.

**O que o extrator precisa saber e o `pyspark_ast.py` não faz:** `GraphFrame(v, e)`
é `ast.Call` com `func=ast.Name`, e o laço central de `pyspark_ast.py:255`
descarta tudo que não é `ast.Attribute`. O spec já registrou isso; a pesquisa
confirma que **não há forma alternativa de construção em Python** na superfície
pública — `graphframes/__init__.py` exporta exatamente um nome:

```python
from .graphframe import GraphFrame

__all__ = ["GraphFrame"]
```

Nas duas tags, `v0.8.3` e `v0.12.1`. Não há `GraphFrame.fromEdges` no Python,
não há factory de módulo. Os exemplos oficiais usam `graphframes.examples.Graphs`,
que é utilitário de demonstração e **não** deve entrar no vocabulário.

## 3. O vocabulário real, e onde o spec errou

O spec chutou oito nomes: `connectedComponents`, `pageRank`, `shortestPaths`,
`labelPropagation`, `triangleCount`, `bfs`, `aggregateMessages`, `pregel`.

**Os oito existem nas duas linhagens.** Mas o chute erra em duas direções.

### 3.1 `pregel` não é chamada de método — é `@property`

Nas duas tags, `pregel` é decorado com `@property` e devolve um *builder*. A
forma real é uma cadeia:

```python
g.pregel \
    .setMaxIter(10) \
    .withVertexColumn("rank", ...) \
    .sendMsgToDst(...) \
    .aggMsgs(...) \
    .run()
```

`g.pregel` sozinho é `ast.Attribute`, **não** `ast.Call`. Um extrator que só
olhe `ast.Call` com `attrs.name == "pregel"` **nunca emite fact** para o único
algoritmo da biblioteca cujo limite de iteração é de fato controlável pelo
usuário. Este é exatamente o "silêncio no lugar de fact" que o plano teme.

O mesmo vale para `triplets`, `degrees`, `inDegrees` e `outDegrees`: todos são
`@property` nas duas tags.

### 3.2 Faltam nomes, e a linhagem corrente triplicou a superfície

Presentes já na `v0.8.3` e ausentes do chute do spec:

| Nome | Forma |
|---|---|
| `stronglyConnectedComponents` | método, `maxIter` **obrigatório** |
| `parallelPersonalizedPageRank` | método |
| `svdPlusPlus` | método |
| `find` | método (busca de motivo) |
| `filterVertices`, `filterEdges`, `dropIsolatedVertices` | métodos |
| `cache`, `persist`, `unpersist` | métodos herdados da forma de DataFrame |

Acrescentados na linhagem corrente (`v0.12.1`), com a release que os introduziu
quando ela foi identificada:

| Nome | Desde |
|---|---|
| `powerIterationClustering` | `0.9.0` |
| `k_core`, `maximal_independent_set`, `detectingCycles`, `validate`, `as_undirected`, `type_degree`/`type_in_degree`/`type_out_degree` | `0.10.0` |
| `as_reversed`, `aggregate_neighbors` | `0.11.0` |
| `hyper_anf`, `neighborhood_aware_cdlp`, `all_paths` | `0.12.0` |

Note a mudança de convenção: os nomes novos são `snake_case`, os antigos
`camelCase`, e as duas convenções **coexistem** no mesmo objeto. Um `frozenset`
que assuma uma só delas perde metade.

### 3.3 Uma armadilha de assinatura, medida e não documentada em prosa

Em `v0.12.1`, `triangleCount` tem a assinatura:

```python
def triangleCount(self, storage_level: StorageLevel, algorithm: str = "exact", lg_nom_entries: int = 12)
```

`storage_level` é **posicional sem default**. Na `v0.8.3` a assinatura era
`triangleCount(self)`. Ou seja: `g.triangleCount()` — a forma que toda a
documentação e todo o corpus existente escreve — **levanta `TypeError` na
`0.12.1`**. Não há nota de migração para isso nas release notes lidas.

Isto **não vira regra**: o motor não sabe qual versão está instalada, e acusar
`g.triangleCount()` seria acusar quem escreveu certo para todas as versões
anteriores. Fica registrado porque explica um `TypeError` que um usuário pode
trazer, e porque proíbe a regra inversa.

## 4. Pergunta 1 — checkpoint em `connectedComponents`

### 4.1 A frase

> _With GraphFrames 0.3.0 and later releases, the default Connected Components algorithm **requires** setting a Spark checkpoint directory. Users can revert to the old algorithm using `connectedComponents.setAlgorithm("graphx")`. Starting from GraphFrames 0.9.3 release, users can also use `localCheckpoints` that does not require setting a Spark checkpoint directory. To use `localCheckpoints` users can set the config `spark.graphframes.useLocalCheckpoints` to `true` or use the API `connectedComponents.setUseLocalCheckpoints(true)`. While `localCheckpoints` provides better performance they are not as reliable as the persistent checkpointing._

— https://graphframes.io/04-user-guide/05-traversals.html (retrieved 2026-08-05)

**É exigência, não recomendação.** O verbo é `requires`.

### 4.2 O modo de falha, no código

A prosa diz "requires"; o código diz **o que acontece**. Na `v0.8.3`, no
docstring de `setCheckpointInterval` de `ConnectedComponents.scala`:

> _Checkpoint data is saved under `org.apache.spark.SparkContext.getCheckpointDir` with prefix "connected-components". **If the checkpoint directory is not set, this throws a `java.io.IOException`.** Set a nonpositive value to disable checkpointing._

E no corpo do algoritmo, `v0.8.3`:

```scala
val shouldCheckpoint = checkpointInterval > 0
val checkpointDir: Option[String] = if (shouldCheckpoint) {
  val dir = sc.getCheckpointDir.map { d =>
    new Path(d, s"$CHECKPOINT_NAME_PREFIX-$runId").toString
  }.getOrElse {
    throw new IOException(
      "Checkpoint directory is not set. Please set it first using sc.setCheckpointDir().")
  }
```

Na `v0.12.1` o bloco migrou para `TwoPhase.scala` e ganhou uma alternativa:

```scala
val shouldCheckpoint = checkpointInterval > 0
val checkpointDir: Option[String] = if (useLocalCheckpoints) { None }
else if (shouldCheckpoint) {
  val dir = sc.getCheckpointDir
    .orElse {
      spark.conf.getOption("spark.checkpoint.dir") match {
        ...
        throw new IOException(
          "Checkpoint directory is not set. Please set it first using sc.setCheckpointDir()" +
            "or by specifying the conf 'spark.checkpoint.dir'.")
```

**O algoritmo falha, não degrada.** Exceção na primeira iteração, antes de
qualquer trabalho útil. Isso sustenta **P0** — e é o único ponto desta fase em
que a fonte autoriza P0 sem heurística de campo.

### 4.3 As três saídas legítimas, e por que a regra tem de conhecê-las

Uma regra que exija `sc.setCheckpointDir(...)` de todo `connectedComponents`
**acusa quem escreveu certo** em três casos medidos:

1. **`algorithm="graphx"`.** A implementação GraphX não checkpoint-a: a exigência
   é da implementação default. A doc corrente registra o valor como saída
   explícita ("Users can revert to the old algorithm").
2. **`checkpointInterval <= 0`.** `shouldCheckpoint = checkpointInterval > 0`; com
   valor não positivo o bloco inteiro é pulado e nenhuma `IOException` é lançada.
   O docstring diz literalmente "Set a nonpositive value to disable checkpointing"
   e, na mesma frase, que desabilitar "is not recommended". A regra correta aqui é
   **outra regra**, com severidade menor, não a mesma.
3. **`use_local_checkpoints=True` (0.9.3+), ou a conf `spark.graphframes.useLocalCheckpoints`.**
   Sem `checkpointDir` persistente, sem exceção.

E há uma quarta saída que **não está no `.py`**: a conf `spark.checkpoint.dir`
(0.9.3+). Um job pode declará-la no IaC ou no `--conf` e o `.py` não conterá
`setCheckpointDir` nenhum. Isto **limita a regra** — ver §8.

### 4.4 A exigência vale só para `connectedComponents`? — Não

Na linhagem corrente, `labelPropagation`, `shortestPaths`,
`neighborhood_aware_cdlp`, `k_core`, `maximal_independent_set`, `detectingCycles`,
`all_paths` e `aggregate_neighbors` **todos** expõem `checkpoint_interval` e
`use_local_checkpoints`, porque todos ganharam implementação DataFrame-nativa
iterativa. Na `v0.8.3`, nenhum deles expunha: só `connectedComponents` e `Pregel`
checkpoint-avam.

**Não estendi a regra a eles**, e a razão é a §1: o `.py` não diz qual linhagem
está instalada, e em `0.8.x` esses algoritmos passam por GraphX e não exigem
diretório nenhum. Acusar `g.labelPropagation(maxIter=5)` sem `setCheckpointDir`
seria acusar todo job legado correto. Fica como **veto V-GF-4**.

### 4.5 Os valores de `algorithm` — o spec chutou errado

O spec supõe dois valores, `graphx` e `graphframes`. Medido:

| Versão | Valores aceitos | Default |
|---|---|---|
| `0.8.3` | `"graphframes"`, `"graphx"` | `"graphframes"` |
| `0.12.1` | `"graphx"`, `"two_phase"`, `"randomized_contraction"`, `"graphframes"` (alias) | `"graphframes"` no Python; a doc diz `two_phase` |

> _The algorithm name `graphframes` is a **deprecated alias** for `two_phase` and will be removed in a future release. Replace any usage of `setAlgorithm("graphframes")` with `setAlgorithm("two_phase")`._

Há uma divergência entre doc e código na `0.12.1`: a doc lista o default como
`two_phase`, o Python declara `algorithm: str = "graphframes"`. Como
`"graphframes"` é alias de `"two_phase"`, o comportamento é o mesmo — mas
**não citar "o default é `two_phase`" como se o fonte Python o dissesse**.

## 5. Pergunta 2 — `maxIter`, algoritmo a algoritmo

Esta é a pergunta em que o spec estava mais perto de escrever uma regra que
acusa quem escreveu certo. A tabela é o veredicto.

| Algoritmo | Parâmetro de iteração | Default | Ausente significa |
|---|---|---|---|
| `pageRank` | `maxIter` **ou** `tol` | nenhum dos dois | **crash**: "Exactly one of maxIter or tol should be set" |
| `parallelPersonalizedPageRank` | `maxIter` | nenhum | **crash**: `assert maxIter is not None` |
| `labelPropagation` | `maxIter` | **obrigatório, posicional** | `TypeError` |
| `stronglyConnectedComponents` | `maxIter` | **obrigatório, posicional** | `TypeError` |
| `powerIterationClustering` (0.9.0+) | `maxIter` | **obrigatório, posicional** | `TypeError` |
| `neighborhood_aware_cdlp` (0.12+) | `max_iter` | **obrigatório, posicional** | `TypeError` |
| `svdPlusPlus` | `maxIter` | **2** | roda 2 iterações |
| `connectedComponents` (0.9.0+) | `max_iter` | `Integer.MAX_VALUE` | roda **até convergir** |
| `connectedComponents` (≤0.8.4) | — | não existe | roda até convergir |
| `Pregel` | `setMaxIter` | **10** | roda 10 superpassos |
| `bfs` | `maxPathLength` (não é `maxIter`) | **10** | limita profundidade |
| `shortestPaths` | — | não existe | não é iterativo pelo usuário |
| `triangleCount` | — | não existe | não é iterativo |
| `aggregateMessages` | — | não existe | **uma rodada só**, por construção |
| `hyper_anf` (0.12+) | `n_hops` | 3 | 3 saltos |
| `all_paths` (0.12+) | `max_path_length` | 5 | limita profundidade |

### 5.1 `pageRank`: a armadilha, verbatim

> _There are two implementations of PageRank._
> _- The first one uses the `org.apache.spark.graphx.graph` interface with `aggregateMessages` and runs PageRank for a fixed number of iterations. This can be executed by setting `maxIter`._
> _- The second implementation uses the `org.apache.spark.graphx.Pregel` interface and runs PageRank **until convergence** and this can be run by setting `tol`._

— https://graphframes.io/04-user-guide/03-centralities.html (retrieved 2026-08-05)

E o código Python, idêntico em `v0.8.3` e `v0.12.1`:

```python
if maxIter is not None:
    builder = builder.maxIter(maxIter)
    assert tol is None, "Exactly one of maxIter or tol should be set."
else:
    assert tol is not None, "Exactly one of maxIter or tol should be set."
    builder = builder.tol(tol)
```

**`tol` não é "sem limite": é "até convergir", que é o segundo modo oficial.** E
não é opcional escolher: passar os dois é erro, passar nenhum é erro. Uma regra
"pageRank sem `maxIter`" acusaria metade dos usos corretos da API — e a metade
que a própria documentação usa **primeiro** no exemplo Python.

O fact tem de dizer **qual dos dois veio**, e a regra só pode olhar
"nenhum dos dois", que é código que já não roda. Ou seja: a regra não tem valor.
**Veto V-GF-2.**

### 5.2 `connectedComponents`: a fonte proíbe a regra explicitamente

> `maxIter` — _For `graphx` **only**. Limits the maximum number of Pregel iterations. Default is `Integer.MAX_VALUE` (unlimited). **It is generally not recommended to change this value.**_

— https://graphframes.io/04-user-guide/05-traversals.html (retrieved 2026-08-05)

Três coisas de uma vez: o parâmetro só vale para uma das três implementações; o
default é ilimitado **de propósito**, porque o algoritmo converge; e a fonte
recomenda **não mexer**. Uma regra que exija `max_iter` aqui contradiz a
documentação da própria biblioteca. **Veto V-GF-3.**

### 5.3 O que sobra

Dos dezesseis algoritmos com alguma noção de iteração, **em nenhum** "`maxIter`
ausente" é um defeito:

- em seis, ausente é `TypeError` ou `AssertionError` — código que não roda;
- em três, ausente é um default documentado e sensato (2, 10, 3);
- em um, ausente é "até convergir", que é o modo recomendado;
- nos demais, o parâmetro não existe.

**A regra "algoritmo iterativo sem limite de iteração" da §5 do spec não entra.**
Não por falta de fonte — por a fonte dizer o contrário.

O que **sobra** com fundamento é o oposto e é bem mais estreito: `Pregel` sem
`setMaxIter` **e** sem `setStopIfAllNonActiveVertices`/`setEarlyStopping` roda
exatamente 10 superpassos, e 10 pode não bastar para convergir num grafo de
diâmetro maior. Isso é **falta de convergência**, não "sem limite", e a fonte
não declara nenhum limiar. Se virar regra, é `origin: field-heuristic`.

## 6. `checkpointInterval` — o número que a fonte dá, e o que ela recomenda

Único limiar numérico com fonte primária nesta área:

> _`checkpoint_interval` — For `two_phase` and `randomized_contraction`. To avoid exponential growth of the Spark logical plan, DataFrame lineage, and query optimization time, checkpointing is performed periodically. **It is recommended to keep this value at `2` or below.**_

E o código avisa, mas não impede:

```scala
def setCheckpointInterval(value: Int): this.type = {
  if (value <= 0 || value > 2) {
    logWarn(
      s"Set checkpointInterval to $value. This would blow up the query plan and hang the " +
        "driver for large graphs.")
  }
```

Default: `2`. Limiar da fonte: `> 2` **ou** `<= 0` merece aviso. Este é limiar
citável — não é heurística de campo.

## 7. Bloco de vetos, para o cabeçalho de `rules/catalog/graph.yaml`

```
# VETOS APURADOS NA PESQUISA DE FONTES (2026-08-05).
# Detalhe e URLs: knowledge/graph/graphframes-api.md e knowledge/graph/availability.md
#
# V-GF-1  Checkpoint em connectedComponents E EXIGENCIA e o algoritmo FALHA
#         (java.io.IOException na 1a iteracao), o que autoriza P0. Mas a regra
#         NAO pode disparar quando o codigo declara qualquer das tres saidas:
#         algorithm="graphx"; checkpointInterval<=0; use_local_checkpoints=True.
#         Ha uma quarta saida FORA do .py (conf spark.checkpoint.dir, 0.9.3+):
#         a ressalva vai escrita DENTRO do achado, no padrao de V-AS-2.
# V-GF-2  NAO exigir maxIter de pageRank. A API tem DOIS modos oficiais --
#         maxIter (n fixo) e tol (ate convergir) -- e passar os dois e erro.
#         Quem passou tol escreveu certo. O fact precisa dizer QUAL veio.
# V-GF-3  NAO exigir max_iter de connectedComponents. A doc declara: "For
#         graphx only... Default is Integer.MAX_VALUE (unlimited). It is
#         generally not recommended to change this value." A regra
#         contradiria a fonte.
# V-GF-4  NAO estender a exigencia de checkpoint a labelPropagation,
#         shortestPaths, k_core, cycles, all_paths e afins. Eles so passaram a
#         checkpointar na linhagem io.graphframes; em 0.8.x vao por GraphX e
#         nao exigem diretorio. O .py nao diz qual linhagem esta instalada.
# V-GF-5  `pregel`, `triplets`, `degrees`, `inDegrees` e `outDegrees` sao
#         @property, nao metodo. Vocabulario que so casa ast.Call perde o
#         pregel inteiro -- silencio no lugar de fact.
# V-GF-6  O vocabulario tem DUAS convencoes de nome no mesmo objeto:
#         camelCase (0.8.x) e snake_case (0.10+). frozenset com uma so perde
#         metade da superficie corrente.
# V-GF-7  NAO acusar `g.triangleCount()` sem argumento. Em 0.12.1
#         storage_level virou posicional obrigatorio, mas em toda versao
#         anterior a forma sem argumento e a unica correta e e a que a doc usa.
# V-GF-8  NAO recomendar `algorithm="graphframes"`: e alias DEPRECIADO de
#         "two_phase" desde 0.10.0. Detecta-lo e legitimo; propo-lo nao.
```

## 8. O que a fonte NÃO sustenta

**A quarta saída do checkpoint não está no artefato.** A conf
`spark.checkpoint.dir` (0.9.3+) e a conf `spark.graphframes.useLocalCheckpoints`
satisfazem a exigência sem que o `.py` contenha `setCheckpointDir` nenhum. Esta
área lê apenas o `.py`. A regra de checkpoint é, portanto, uma afirmação sobre o
**código**, não sobre a execução — e a ressalva precisa ir escrita dentro do
achado, no mesmo padrão de `V-AS-2` em [`../dq/validation-frameworks.md`](../dq/validation-frameworks.md).
Sem essa ressalva a regra afirma mais do que a evidência sustenta.

**Não citar número para "quantas iterações o `two_phase` leva".** A doc compara
complexidade de convergência entre as três implementações qualitativamente
("Fast", "O(diameter) iterations", "~5x faster than skewed join") e não publica
nenhum número absoluto. A única grandeza citável é `O(diameter)` para `graphx`.

**Não citar limiar para "grafo grande".** Nenhuma página da documentação define
tamanho a partir do qual `graphx` deixa de servir, nem a partir do qual
`broadcast_threshold` deveria virar `-1`. As frases são comparativas
("for small-medium sized graphs", "for large or wide graphs"), e transformá-las
em número seria invenção.

**Não afirmar qual versão de GraphFrames um `.py` usa.** O import é idêntico nas
duas linhagens e o `__init__.py` exporta o mesmo nome único. Só argumento
literal de parâmetro introduzido depois de uma release dá **piso** de versão, e
nunca teto.

**O custo de recomputação de vértices/arestas não persistidos não foi encontrado
quantificado em fonte nenhuma.** A doc menciona `storage_level` e diz que o
`DataFrame` devolvido é persistido — "_Be aware, that returned `DataFrame` is
persistent and should be unpersisted manually after processing to avoid memory
leaks!_" —, mas não declara em lugar nenhum quantas passadas um algoritmo faz
sobre os vértices de entrada. A regra de persistência, se entrar, é
`origin: field-heuristic`, herdando a forma de `SF-DQ-003` e **não** citando
estas páginas como se elas a sustentassem.

**As datas das release notes do GitHub não conferem com as do Maven Central para
a série 0.10–0.12 quando lidas por resumo automático.** As datas usadas aqui vêm
da API do GitHub (`published_at`) e do `maven-metadata.xml`, não da renderização
da página de releases. `v0.8.4` **não tem release no GitHub** — existe só como
artefato no spark-packages.

**A release note da `0.8.3` afirma "Support Spark 3.3 / Scala 2.12"; nenhum
artefato `0.8.3-spark3.3` foi publicado.** A contradição está medida em
[`availability.md`](availability.md) §2, e ali o repositório de artefatos vence
a nota de release — porque o que se instala é o jar.

## Fontes

**Documentação da biblioteca**

- GraphFrames — página inicial e release corrente (`0.12.1`). https://graphframes.io/ (retrieved 2026-08-05)
- Traversals and Connectivity — `connectedComponents`, a NOTE da exigência de checkpoint, as três implementações, os argumentos e o default de `maxIter`. https://graphframes.io/04-user-guide/05-traversals.html (retrieved 2026-08-05)
- Centrality Metrics — as duas implementações de `pageRank`, `maxIter` × `tol`, K-Core e HyperANF. https://graphframes.io/04-user-guide/03-centralities.html (retrieved 2026-08-05)
- Community Detection — `labelPropagation`, `neighborhood_aware_cdlp`, `powerIterationClustering`. https://graphframes.io/04-user-guide/06-graph-clustering.html (retrieved 2026-08-05)
- Installation — coordenadas Maven, `graphframes-py`, Spark/Scala suportados. https://graphframes.io/02-quick-start/01-installation.html (retrieved 2026-08-05)

**Código, que é onde o modo de falha está**

- `python/graphframes/graphframe.py`, tag `v0.8.3` — assinaturas e defaults da linhagem legada. https://raw.githubusercontent.com/graphframes/graphframes/v0.8.3/python/graphframes/graphframe.py (retrieved 2026-08-05)
- `python/graphframes/graphframe.py`, tag `v0.12.1` — assinaturas e defaults da linhagem corrente. https://raw.githubusercontent.com/graphframes/graphframes/v0.12.1/python/graphframes/graphframe.py (retrieved 2026-08-05)
- `python/graphframes/lib/pregel.py`, tags `v0.8.3` e `v0.12.1` — `setMaxIter` default 10. https://raw.githubusercontent.com/graphframes/graphframes/v0.12.1/python/graphframes/lib/pregel.py (retrieved 2026-08-05)
- `ConnectedComponents.scala`, tag `v0.8.3` — `throw new IOException("Checkpoint directory is not set...")` e o docstring de `setCheckpointInterval`. https://raw.githubusercontent.com/graphframes/graphframes/v0.8.3/src/main/scala/org/graphframes/lib/ConnectedComponents.scala (retrieved 2026-08-05)
- `TwoPhase.scala`, tag `v0.12.1` — o mesmo bloco com `useLocalCheckpoints` e a conf `spark.checkpoint.dir`. https://raw.githubusercontent.com/graphframes/graphframes/v0.12.1/core/src/main/scala/org/graphframes/lib/TwoPhase.scala (retrieved 2026-08-05)
- `GraphFramesConf.scala`, tag `v0.12.1` — `spark.graphframes.useLocalCheckpoints` e `spark.graphframes.connectedComponents.checkpointinterval`. https://raw.githubusercontent.com/graphframes/graphframes/v0.12.1/core/src/main/scala/org/apache/spark/sql/graphframes/GraphFramesConf.scala (retrieved 2026-08-05)
- `python/graphframes/__init__.py`, tags `v0.8.3` e `v0.12.1` — `__all__` com um nome só. https://raw.githubusercontent.com/graphframes/graphframes/v0.12.1/python/graphframes/__init__.py (retrieved 2026-08-05)
- Release notes, via API. https://api.github.com/repos/graphframes/graphframes/releases (retrieved 2026-08-05)

**Deste repositório**

- `GLUE_MATRIX` e `EMR_MATRIX` em [`../../sparkforge/facts/runtime_detect.py`](../../sparkforge/facts/runtime_detect.py).
- [`availability.md`](availability.md) — a matriz de jar por release, e o silêncio da AWS.
