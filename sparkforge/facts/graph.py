"""Extrator de Facts sobre PROCESSAMENTO DE GRAFO com GraphFrames num `.py`.

NUNCA importa nem executa o codigo do alvo, nao chama AWS e nao le nada alem do
fonte que recebe. Le a mesma arvore que `pyspark_ast.py` e `data_quality.py`
leem, pela terceira vez, porque reconhecer grafo e responsabilidade propria com
API propria -- e porque por dentro de `pyspark_ast.py` um `GraphFrame(v, e)` nem
existe: o laco central dele descarta tudo que nao e `ast.Attribute`
(`pyspark_ast.py:264`), e `g.connectedComponents()` nao casa `frozenset` nenhum
la. Hoje um job de grafo sai indistinguivel de um arquivo sem grafo.

TRES COISAS QUE O PROXIMO LEITOR VAI PERGUNTAR, respondidas antes.

1. POR QUE VOCABULARIO FECHADO AQUI, quando `data_quality.py` recusa reconhecer
   por nome. La a razao e que nome de check e ABERTO -- o usuario inventa o dele
   --, entao a deteccao e pela FORMA da cadeia. Aqui e o inverso: a API do
   GraphFrames e FINITA e publicada, e um `frozenset` e a descricao correta do
   dominio, nao um atalho. As duas convencoes convivem no mesmo objeto --
   `camelCase` da linhagem `graphframes:graphframes` (ate 0.8.4) e `snake_case`
   da `io.graphframes` (0.9.0+) --, e um `frozenset` com uma so perderia metade
   da superficie corrente (`knowledge/graph/graphframes-api.md` §3.2, veto
   V-GF-6).

   O preco do vocabulario por nome e casar um homonimo do usuario, e ele e pago
   em dois niveis. Nomes distintivos (`connectedComponents`, `aggregateMessages`,
   `pregel`) sao lidos sempre. Nomes que tambem sao identificadores comuns de
   Python -- `find` (que e metodo de `str`), `validate`, `degrees` -- so sao
   lidos quando ESTE modulo importa GraphFrames, e a evidencia independente que
   os habilita e exatamente a que o item 2 descreve.

   `GraphFrame`, O CONSTRUTOR, ESTA NO NIVEL DISTINTIVO, e isso e decisao e nao
   descuido: `constructors` nasce semeado com ele, sem exigir import. E o mesmo
   criterio de `connectedComponents` -- nome publicado, especifico da biblioteca,
   improvavel como identificador de usuario --, e exigir o import perderia forma
   real: um `from minha_lib.grafo import GraphFrame` que reexporta o simbolo nao
   deixa `graphframes` nenhum neste arquivo, e a construcao existe do mesmo
   jeito.

   O PRECO DOS DOIS NIVEIS TAMBEM APARECE EM ACHADO, e nao so em fact -- dizer o
   contrario seria declarar meio preco. Com GraphFrames importado, um
   `"...".find(x)` dentro de laco vira `graph.algorithm` com `inside_loop: true`
   e sai como `SF-GRAPH-004` (P2); e um `GraphFrame(v, e)` sem import nenhum vira
   `graph.construction` e pode sair como `SF-GRAPH-003` (P2). Fechar o primeiro
   exigiria correlacionar o receptor com um nome que ESTE arquivo viu ser
   construido como grafo -- o que trocaria um falso positivo estreito (import
   presente E `str.find` dentro de laco) por um falso negativo largo, porque
   grafo que chega por parametro e forma corrente e este modulo ja declara nao
   saltar para o chamador. Medido, e nao fechado: as duas severidades sao P2, e
   nenhuma das duas e a acusacao P0 que esta area existe para nao cometer.

   Tres nomes da API ficam DE FORA de proposito: `cache`, `persist` e
   `unpersist`. Sao herdados da forma de DataFrame, `pyspark.cache` ja os emite
   sobre o mesmo artefato, e reemiti-los aqui duplicaria o sujeito de
   `SF-PY-008` e apagaria a fronteira entre `SF-PY` e `SF-GRAPH` que a fase
   precisa provar. Eles entram neste modulo so como EVIDENCIA de persistencia
   dos vertices e arestas, nunca como algoritmo.

2. POR QUE ESTE MODULO RASTREIA `import`, quando nenhum outro rastreia. A regra
   de disponibilidade afirma "este job usa GraphFrames" -- e a evidencia honesta
   disso e o `import`, nao a chamada de metodo, que um `getattr` esconde e um
   homonimo falsifica, nem a construcao, que um alias renomeia. O `import` e
   tambem o unico sinal que sobrevive a um job que so passa o grafo para uma
   biblioteca interna.

   ALCANCE MEDIDO, e ele e o arquivo inteiro. No corpus de `fixtures/` os 113
   imports estao todos no topo do modulo; no repositorio inteiro, 1081 estao no
   topo, 145 dentro de `FunctionDef`, 16 sob `try` e 1 sob `if`. Import dentro
   de funcao e sob `try` sao formas reais -- `try: import graphframes / except
   ImportError:` e o idioma de dependencia opcional --, e nenhuma delas
   enfraquece a afirmacao "este job usa GraphFrames". Entao TODOS sao lidos, e a
   posicao vai como atributo (`scope`, `guarded`) para que uma regra possa
   estreitar sem que o extrator decida por ela.

   O que NAO e seguido: `importlib.import_module("graphframes")` e
   `__import__`. Dinamico e onde a analise estatica mente -- o nome pode ser
   montado em runtime --, e a decisao e nao adivinhar: vira `graph.unresolved`
   com reason `dynamic_import`, ponto cego CONTADO.

3. O QUE ESTE MODULO NAO SABE, e cada item aqui e um limite declarado, nao um
   defeito a corrigir em silencio:

   - QUAL LINHAGEM esta instalada. `from graphframes import GraphFrame` e
     identico em `0.8.2` e em `0.12.1`, e o `__init__.py` das duas exporta um
     unico nome. Nenhum fact deste modulo afirma versao. Argumento literal de
     parametro introduzido depois de uma release da PISO de versao, nunca teto,
     e nem isso e emitido como versao.
   - DESPACHO DINAMICO. `getattr(g, nome)()` nao vira fact e nao vira
     `unresolved`: emitir um `graph.unresolved` por `getattr` faria todo arquivo
     sem grafo nenhum ganhar ponto cego de grafo. `pyspark.unresolved` ja conta
     `getattr` sobre o mesmo artefato.
   - A QUARTA SAIDA DA EXIGENCIA DE CHECKPOINT. As confs `spark.checkpoint.dir`
     e `spark.graphframes.useLocalCheckpoints` podem vir do IaC ou do `--conf`, e
     ai o `.py` nao as contem. Quando elas aparecem DENTRO do arquivo -- via
     `spark.conf.set(...)` ou via `SparkSession.builder.config(...)`, as duas
     formas correntes -- este modulo as le, justamente para nao produzir uma
     acusacao P0 falsa; quando vem de fora, a ressalva e da regra
     (`knowledge/graph/graphframes-api.md` §8, no padrao de `V-AS-2`).
     A CHAVE QUE NAO DA PARA LER e um limite, e nao uma negativa. Chave por
     constante (`K = "spark.checkpoint.dir"`), por laco (`for k, v in
     CONF.items()`), por `**kwargs` ou por objeto inteiro (`config(conf=...)`)
     OMITE a decisao e conta `graph.unresolved`. Constant folding nao e feito de
     proposito: seguir o valor de um nome ate a atribuicao e inferencia entre
     escopos, que e o que este modulo recusa em toda parte -- e recusar aqui
     custa uma omissao contada, enquanto adivinhar custaria um P0.
   - ARGUMENTO POSICIONAL de `connectedComponents`. A ordem dos parametros mudou
     entre linhagens e nao foi medida; um posicional pode estar declarando
     `algorithm="graphx"`. Entao posicional ali OMITE a decisao de checkpoint e
     conta `graph.unresolved`, em vez de arriscar um P0 sobre codigo correto.
   - PERSISTENCIA QUE MORA NO CHAMADOR. `data_quality.py` da um salto para fora
     (`_persisted_in_caller`); aqui nao ha salto: vertice ou aresta que chega por
     parametro deixa a chave OMITIDA. Subnotificacao declarada, e nunca acusacao.
   - OUTRO ARQUIVO. Um modulo por vez, como todos os extratores de `.py` deste
     repositorio.

O QUE O EXTRATOR DECIDE, e por que decidir e dele. O motor avalia um fact por
vez (`engine._condition_candidates`), `engine._where_matches` compara por
IGUALDADE e reprova caminho ausente, e nao ha operador de "chave ausente" sobre
`attrs`. Logo uma regra NAO consegue exprimir "o codigo nao declarou saida
nenhuma": quem enxerga as tres saidas de uma vez e este modulo, e ele emite o
booleano ja decidido (`checkpoint_required`). Isso e transcricao do modo de
falha documentado -- `java.io.IOException` na primeira iteracao --, nao juizo:
severidade, limiar e recomendacao continuam no catalogo.

OMITIR CHAVE X EMITIR `false`, a regra de governo herdada de
`data_quality.py:39-61`: decide o valor sobre o qual a regra consumidora
dispara. `checkpoint_required` e `vertices_persisted`/`edges_persisted` disparam
regra do lado em que a ignorancia cairia, entao ignorancia OMITE a chave -- e a
omissao vem sempre acompanhada de `graph.unresolved`, para que o ponto cego
seja contado e nao silencio.

A SIMETRIA DAS DUAS METADES DA CONF e o que faz a frase acima ser verdadeira, e
ela foi conquistada na revisao da Fase 6a. Ate ali, o VALOR ilegivel omitia a
decisao e contava o ponto cego, mas a CHAVE ilegivel nao era nem lida: quatro
formas correntes saiam com `checkpoint_configured_in_module: false` sobre codigo
que configurava o checkpoint direitinho, e cada uma disparava P0. Hoje as duas
metades caem do mesmo lado. `inside_loop` fica sempre presente; ja
`checkpoint_configured_in_module` acompanha `checkpoint_required` e some junto
com ele, porque afirmar "o arquivo nao configurou" quando o arquivo tem conf que
ninguem conseguiu ler seria a mesma mentira por outro caminho.

O QUE ESTE MODULO NAO EMITE, e a razao. A pesquisa da Task 1 vetou a regra
"algoritmo iterativo sem limite de iteracao" (V-GF-2, V-GF-3): em nenhum dos
dezesseis algoritmos com nocao de iteracao "ausente" e defeito -- em seis e
`TypeError`, em tres e default documentado, em `pageRank` e o modo `tol`
oficial, e em `connectedComponents` a doc recomenda NAO mexer. Entao nao existe
aqui nenhum `has_max_iter: false`: um booleano que so nasceu para sustentar
regra vetada e regra vetada entrando pela porta dos fundos. O que sai e o que
foi OBSERVADO -- `iteration_arg` nomeia o parametro de iteracao que o codigo
passou, quando passou algum --, e a ausencia dele nao afirma nada.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, NamedTuple

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "graph@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "graph.import",
        "graph.construction",
        "graph.algorithm",
        "graph.checkpoint_dir",
        "graph.unresolved",
        "graph.module_analyzed",
    }
)

# "Este arquivo fala de grafo": import, construcao ou algoritmo. A sentinela
# fica de fora de proposito -- ela sai em TODO arquivo que compilou -- e
# `graph.checkpoint_dir` tambem, porque conf de checkpoint e de Spark e nao de
# GraphFrames.
_GRAPH_SIGNAL_KINDS = frozenset({"graph.import", "graph.construction", "graph.algorithm"})

# Vocabulario FECHADO de razoes de ponto cego, no padrao de `dq.unresolved`:
# ilegivel e contado, nunca omitido em silencio.
UNRESOLVED_REASONS = frozenset(
    {
        "dynamic_import",
        "non_literal_argument",
        # Literal que EXISTE e nao e booleano do Spark: `useLocalCheckpoints` com
        # `1`. Rotular isso de `non_literal_argument` mentia sobre um argumento
        # que e literal, e mandava quem le o ponto cego procurar a variavel
        # errada. O valor foi lido; o que falta e a conversao para booleano, que
        # `java.lang.Boolean.parseBoolean` so faz com "true"/"false".
        "non_boolean_value",
        # A CHAVE da conf nao pode ser lida do `.py`: veio por constante, por
        # laco, por `**kwargs` ou por objeto de conf. Simetrico ao ponto cego do
        # VALOR -- ver a nota de OMITIR CHAVE X EMITIR `false` no cabecalho.
        "unreadable_conf_key",
        "positional_argument",
        "receiver_without_name",
        "syntax_error",
        "read_error",
    }
)

_PACKAGE = "graphframes"
_CONSTRUCTOR = "GraphFrame"

# Nomes distintivos da API, lidos SEMPRE. Medidos em
# `knowledge/graph/graphframes-api.md` §3 sobre as tags `v0.8.3` e `v0.12.1`.
# As duas convencoes convivem de proposito (veto V-GF-6).
_ALGORITHM_CALLS = frozenset(
    {
        # linhagem legada, presentes desde a 0.8.3
        "connectedComponents",
        "stronglyConnectedComponents",
        "pageRank",
        "parallelPersonalizedPageRank",
        "shortestPaths",
        "labelPropagation",
        "triangleCount",
        "svdPlusPlus",
        "bfs",
        "aggregateMessages",
        "filterVertices",
        "filterEdges",
        "dropIsolatedVertices",
        # linhagem io.graphframes
        "powerIterationClustering",  # 0.9.0
        "k_core",  # 0.10.0
        "maximal_independent_set",  # 0.10.0
        "detectingCycles",  # 0.10.0
        "as_undirected",  # 0.10.0
        "type_degree",  # 0.10.0
        "type_in_degree",  # 0.10.0
        "type_out_degree",  # 0.10.0
        "as_reversed",  # 0.11.0
        "aggregate_neighbors",  # 0.11.0
        "hyper_anf",  # 0.12.0
        "neighborhood_aware_cdlp",  # 0.12.0
        "all_paths",  # 0.12.0
    }
)

# `@property` nas DUAS tags, e por isso um vocabulario casado so contra
# `ast.Call` nao emitiria fact nenhum para o Pregel -- o unico algoritmo cujo
# limite de iteracao o usuario de fato controla (veto V-GF-5). Aqui eles sao
# reconhecidos como `ast.Attribute`, e a cadeia
# `g.pregel.setMaxIter(10)...run()` e percorrida PARA FORA a partir dele.
_ALGORITHM_PROPERTIES = frozenset({"pregel", "triplets", "inDegrees", "outDegrees"})

# Nomes da API que TAMBEM sao identificadores comuns de Python: `"abc".find(x)`
# e um metodo de `str`, e `validate`/`degrees` sao nomes que qualquer objeto de
# usuario pode ter. So sao lidos quando o modulo importa GraphFrames -- a
# evidencia independente do item 2 do cabecalho. Silencio sobre eles num modulo
# sem import e subnotificacao; le-los sem import seria acusacao falsa.
_GATED_CALLS = frozenset({"find", "validate"})
_GATED_PROPERTIES = frozenset({"degrees"})

# A exigencia de checkpoint e de `connectedComponents` e SO dela. V-GF-4: na
# linhagem corrente varios outros algoritmos expoem `checkpoint_interval`, mas
# em `0.8.x` os mesmos passam por GraphX e nao exigem diretorio nenhum, e o
# `.py` nao diz qual linhagem esta instalada. Estender acusaria todo job legado
# correto.
_CHECKPOINT_ALGORITHMS = frozenset({"connectedComponents"})

# As tres saidas legitimas DENTRO do artefato (§4.3 da pesquisa). A quarta -- as
# confs -- e modulo, nao argumento, e vive em `_checkpoint_state`.
_ALGORITHM_ARG = "algorithm"
_GRAPHX = "graphx"
_CHECKPOINT_INTERVAL_ARGS = frozenset({"checkpointInterval", "checkpoint_interval"})
_LOCAL_CHECKPOINT_ARGS = frozenset({"useLocalCheckpoints", "use_local_checkpoints"})
_EXIT_ARGS = frozenset({_ALGORITHM_ARG}) | _CHECKPOINT_INTERVAL_ARGS | _LOCAL_CHECKPOINT_ARGS

# Parametros que LIMITAM iteracao ou profundidade, nas duas convencoes. Sao
# OBSERVADOS e nomeados; nenhuma ausencia deles vira booleano (ver o fim do
# cabecalho).
_ITERATION_ARGS = frozenset(
    {"maxIter", "max_iter", "tol", "maxPathLength", "max_path_length", "n_hops"}
)
_PREGEL_MAX_ITER = "setMaxIter"

_SET_CHECKPOINT_DIR = "setCheckpointDir"
_CONF_CHECKPOINT_DIR = "spark.checkpoint.dir"
_CONF_LOCAL_CHECKPOINTS = "spark.graphframes.useLocalCheckpoints"

# Os DOIS metodos que declaram conf de Spark dentro de um `.py`.
#
# `set` e `pyspark.sql.conf.RuntimeConfig.set` (e tambem `SparkConf.set`), e
# `config` e `SparkSession.Builder.config` -- a forma canonica de declarar conf
# na CONSTRUCAO da sessao, que e onde um job Glue ou EMR configura o cluster.
# `.config` entrou no vocabulario na revisao da Fase 6a, e a razao e assimetria
# de custo, nao frequencia: a chave e um literal DISTINTIVO
# (`"spark.checkpoint.dir"`), entao um falso positivo exige que alguem escreva
# essa string exata noutro contexto, enquanto o falso NEGATIVO -- nao ler a
# forma e afirmar `checkpoint_configured_in_module: false` -- e um P0 sobre
# codigo correto, o pior modo de falha desta area. Ler a chave por igualdade
# nao depende de receptor nenhum, e por isso o caminho do literal nao filtra
# receptor: quem escreve `spark.checkpoint.dir` esta falando de checkpoint.
_CONF_SET_METHOD = "set"
_CONF_BUILDER_METHOD = "config"
_CONF_METHODS = frozenset({_CONF_SET_METHOD, _CONF_BUILDER_METHOD})

# Receptores que autorizam CONTAR ponto cego quando a chave e ilegivel. Aqui,
# ao contrario do caminho do literal, nao ha string distintiva para desempatar:
# `d.set(k, v)` num dicionario e `w.config(k, v)` num widget sao codigo comum, e
# conta-los produziria ponto cego de grafo em arquivo que nunca falou de conf.
# O criterio e o NOME do receptor -- `spark.conf`, `conf`, `SparkConf()`,
# `sc._conf` de um lado; `SparkSession.builder`, `builder` e o encadeamento
# `.config(...).config(...)` do outro.
_CONF_RECEIVER_HINT = "conf"
_BUILDER_RECEIVER_HINTS = ("builder", "sparksession", "config")

_PERSIST_METHODS = frozenset({"cache", "persist"})
_UNPERSIST_METHODS = frozenset({"unpersist"})

# Metodos que constroem um DataFrame A PARTIR da raiz da cadeia. Se um deles
# aparece, a raiz e a sessao (ou o reader), NAO o dado: em
# `GraphFrame(spark.read.parquet(p), e)` o vertice e um DataFrame anonimo, e
# registrar `spark` como `vertices_ref` faria o fact apontar para o objeto
# errado -- e a persistencia seria apurada sobre a sessao. Mesma lista e mesmo
# motivo de `data_quality._SOURCE_TERMINALS`.
_SOURCE_TERMINALS = frozenset(
    {
        "table",
        "sql",
        "range",
        "createDataFrame",
        "parquet",
        "csv",
        "json",
        "orc",
        "text",
        "jdbc",
        "load",
        "format",
    }
)

_DYNAMIC_IMPORT_CALLS = frozenset({("importlib", "import_module"), ("importlib", "reload")})
_DYNAMIC_IMPORT_BARE = frozenset({"__import__"})


class _Context:
    """Mapa no -> pai, funcao que envolve, profundidade de laco.

    Pilha explicita e nao recursao, pelo mesmo motivo de `pyspark_ast._Context`:
    cadeia fluente longa produz arvore profunda e recursao por no estouraria a
    pilha do interpretador.

    O mapa de PAIS existe por uma necessidade que so este extrator tem: `pregel`
    e `@property`, entao a leitura da cadeia comeca no MEIO dela e caminha para
    FORA -- de `g.pregel` ate `.run()`. Os outros extratores so caminham para
    dentro, da chamada para a raiz, e por isso nunca precisaram de pai.
    """

    def __init__(self, tree: ast.AST) -> None:
        self.parent: dict[int, ast.AST | None] = {}
        self.function: dict[int, str] = {}
        self.loop_depth: dict[int, int] = {}

        stack: list[tuple[ast.AST, ast.AST | None, str, int]] = [(tree, None, "", 0)]
        while stack:
            node, parent, symbol, depth = stack.pop()
            self.parent[id(node)] = parent
            self.function[id(node)] = symbol
            self.loop_depth[id(node)] = depth
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                symbol = node.name
            if isinstance(node, ast.For | ast.AsyncFor | ast.While):
                depth += 1
            for child in ast.iter_child_nodes(node):
                stack.append((child, node, symbol, depth))


class _ScopeIndex(NamedTuple):
    """O que se enxerga de UM escopo de nome, e nada alem dele.

    Por escopo e nunca por modulo, pela mesma propriedade que
    `data_quality._ScopeIndex` declara: nome nu nao identifica objeto entre
    escopos. `def a(arestas)` e `def b(arestas)` recebem dois DataFrames
    diferentes, e datar o `cache()` de um contra o `GraphFrame(...)` do outro
    seria acusacao falsa com cara de correlacao.

    LIMITE herdado: a separacao vale para `FunctionDef`/`AsyncFunctionDef`.
    `lambda` e corpo de `class` continuam no escopo que os contem.
    """

    persists: dict[str, list[tuple[tuple[int, int], bool]]]
    rebinds: dict[str, set[int]]
    params: frozenset[str]


def _subject(node: ast.AST, path: str, ctx: _Context, lines: list[str]) -> dict[str, Any]:
    """Ancora de um fact deste modulo.

    `col` e preenchido, e nao fixo em zero: `Fact.id` e sha de
    `kind + subject + measures`, e dois algoritmos na mesma linha
    (`g.pageRank(tol=0.01); g.triangleCount()`) sairiam com a MESMA identidade
    se a coluna fosse zero -- o `fact_id` que um Finding cita deixaria de
    identificar evidencia. Mesma leitura de `pyspark_ast.py:133`, o extrator
    irmao sobre o mesmo artefato.
    """
    lineno = getattr(node, "lineno", 0)
    snippet = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
    return {
        "type": "source_location",
        "file": path,
        "line": lineno,
        "col": getattr(node, "col_offset", 0),
        "end_line": getattr(node, "end_lineno", lineno),
        "symbol": ctx.function.get(id(node), ""),
        "snippet": snippet,
    }


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _unresolved(subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any):
    if reason not in UNRESOLVED_REASONS:  # pragma: no cover - guarda de vocabulario
        raise AssertionError(f"reason fora do vocabulario declarado: {reason}")
    return Fact(
        kind="graph.unresolved",
        subject=subject,
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _literal(node: ast.AST) -> Any | None:
    """Valor quando o no e literal constante; `None` caso contrario.

    Desembrulha um nivel de `+`/`-` unario sobre numero, como
    `pyspark_ast._literal`: `checkpointInterval=-1` e literal na fonte e
    `UnaryOp(USub, Constant)` na arvore, e desabilitar checkpoint com valor nao
    positivo e exatamente uma das tres saidas que a regra precisa enxergar.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float | str | bool):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.UAdd | ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int | float)
        and not isinstance(node.operand.value, bool)
    ):
        value = node.operand.value
        return value if isinstance(node.op, ast.UAdd) else -value
    return None


def _chain_root(node: ast.AST) -> tuple[str | None, list[str]]:
    """(nome da variavel raiz, metodos da cadeia da raiz para fora)."""
    methods: list[str] = []
    current: ast.AST = node
    while True:
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            methods.append(current.func.attr)
            current = current.func.value
        elif isinstance(current, ast.Attribute):
            methods.append(current.attr)
            current = current.value
        else:
            break
    methods.reverse()
    if isinstance(current, ast.Name):
        return current.id, methods
    return None, methods


def _data_root(node: ast.AST) -> str | None:
    """Nome da variavel que E o dado, ou `None` quando a raiz nao e o dado.

    Cadeia que passa por um reader tem raiz que e a sessao, e devolver `spark`
    aqui faria dois dados que nunca se tocaram compartilharem um nome.
    """
    root, methods = _chain_root(node)
    if root is None or any(method in _SOURCE_TERMINALS for method in methods):
        return None
    return root


def _parameter_names(root: ast.AST) -> frozenset[str]:
    """Nomes ligados pela assinatura, quando a raiz do escopo e uma funcao.

    Todas as formas contam -- posicionais, `*args`, keyword-only, `**kwargs` --
    porque a pergunta nao e COMO o valor chega, e sim de ONDE: de fora deste
    escopo, com uma historia que este indice nao viu.
    """
    if not isinstance(root, ast.FunctionDef | ast.AsyncFunctionDef):
        return frozenset()
    args = root.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg is not None:
        named.append(args.vararg)
    if args.kwarg is not None:
        named.append(args.kwarg)
    return frozenset(arg.arg for arg in named)


def _scopes(tree: ast.AST) -> list[tuple[ast.AST, list[ast.AST]]]:
    """A raiz e os nos de cada escopo de nome, cada escopo num par proprio.

    Worklist explicita, sem `NodeVisitor`, no molde de `data_quality._scopes`:
    `FunctionDef` aninhado e EMPURRADO para `pending` e excluido de `own`, de
    modo que o corpo dele nao contamina o indice de quem o contem.

    A RAIZ acompanha os nos porque a assinatura nao esta no corpo, e sem ela o
    indice nao distingue "nao ha persistencia" de "a persistencia esta num
    escopo que eu nao vejo".
    """
    scopes: list[tuple[ast.AST, list[ast.AST]]] = []
    pending: list[ast.AST] = [tree]
    while pending:
        root = pending.pop()
        own: list[ast.AST] = []
        stack = list(ast.iter_child_nodes(root))
        while stack:
            node = stack.pop()
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                pending.append(node)
                continue
            own.append(node)
            stack.extend(ast.iter_child_nodes(node))
        scopes.append((root, own))
    return scopes


def _persist_events(nodes: list[ast.AST]) -> dict[str, list[tuple[tuple[int, int], bool]]]:
    """Eventos de persistencia por nome, ordenados por posicao.

    Guarda `cache`/`persist` E `unpersist` porque o atributo afirma ESTADO no
    momento da construcao, e nao que um `cache()` existiu em algum lugar do
    arquivo. A posicao e (linha, coluna) para que dois eventos na mesma linha
    ainda se ordenem.

    DOIS nomes recebem evento de uma mesma linha, e isso nao e duplicidade:
    `v = vertices.cache()` persiste `vertices` -- a raiz da cadeia -- e liga `v`
    ao mesmo DataFrame persistido. Contar so a raiz faria `GraphFrame(v, e)`
    sair com `vertices_persisted: false` sobre a forma mais comum de persistir
    em job real, que e uma acusacao falsa e nao subnotificacao.
    """
    events: dict[str, list[tuple[tuple[int, int], bool]]] = {}
    for node in nodes:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method not in _PERSIST_METHODS and method not in _UNPERSIST_METHODS:
                continue
            root = _data_root(node)
            if root is not None:
                events.setdefault(root, []).append(
                    ((node.lineno, node.col_offset), method in _PERSIST_METHODS)
                )
            continue
        targets, value = _assignment(node)
        if value is None:
            continue
        _, methods = _chain_root(value)
        if any(method in _PERSIST_METHODS for method in methods):
            persisted = True
        elif any(method in _UNPERSIST_METHODS for method in methods):
            persisted = False
        else:
            continue
        for target in targets:
            events.setdefault(target, []).append(((node.lineno, node.col_offset), persisted))
    for sequence in events.values():
        sequence.sort()
    return events


def _assignment(node: ast.AST) -> tuple[list[str], ast.expr | None]:
    """Nomes ligados por uma atribuicao simples, e o valor ligado a eles."""
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)], node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id], node.value
    return [], None


def _rebind_lines(nodes: list[ast.AST]) -> dict[str, set[int]]:
    """Linhas em que cada nome e ligado a outro objeto.

    Todo `ast.Name` em contexto `Store`, o que cobre de uma vez `Assign`,
    `AnnAssign`, `AugAssign`, alvo de `for`, `with ... as`, comprehension e
    walrus.
    """
    lines: dict[str, set[int]] = {}
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            lines.setdefault(node.id, set()).add(node.lineno)
    return lines


def _scope_index(root: ast.AST, nodes: list[ast.AST]) -> _ScopeIndex:
    return _ScopeIndex(
        persists=_persist_events(nodes),
        rebinds=_rebind_lines(nodes),
        params=_parameter_names(root),
    )


def _rebound_between(name: str, low: int, high: int, index: _ScopeIndex) -> bool:
    """Ha religacao do nome ESTRITAMENTE entre duas linhas do mesmo escopo."""
    return any(low < rebind < high for rebind in index.rebinds.get(name, ()))


def _persisted(argument: ast.expr, position: tuple[int, int], index: _ScopeIndex) -> bool | None:
    """Vertices ou arestas persistidos quando o grafo foi construido.

    Tres respostas, e a terceira e a chave OMITIDA:

    - A cadeia do proprio argumento carrega a persistencia
      (`GraphFrame(v.cache(), e)`): `true`, sem depender de indice nenhum.
    - O argumento e um nome LOCAL: o ultimo evento antes da construcao decide, e
      religar o nome depois do `cache()` derruba a evidencia -- o objeto passado
      nao e o que foi persistido. Aqui `false`, e nao omissao, porque o objeto
      esta NESTE escopo e o indice ve tudo que ha para ver sobre ele; omitir
      faria da religacao um jeito de sumir com a regra.
    - O argumento chega por PARAMETRO, ou nao e um nome: `None`. A historia
      comecou fora deste escopo, e `false` acusaria quem persistiu no chamador.
      A regra de persistencia dispara sobre `false`, entao a ignorancia tem de
      calar -- exatamente a direcao que `data_quality._target_persisted` fixou.
      Diferenca declarada: ali a pergunta da um salto para o unico call site;
      aqui nao ha salto, e o preco e subnotificacao.
    """
    if isinstance(argument, ast.Call):
        _, methods = _chain_root(argument)
        if any(method in _PERSIST_METHODS for method in methods):
            return True
        if any(method in _UNPERSIST_METHODS for method in methods):
            return False
    if not isinstance(argument, ast.Name):
        return None
    name = argument.id
    events = [event for event in index.persists.get(name, ()) if event[0] < position]
    if not events:
        return None if name in index.params else False
    (last_line, _), persisted = events[-1]
    if not persisted:
        return False
    return not _rebound_between(name, last_line, position[0], index)


class _Imports(NamedTuple):
    """O que os `import` do modulo ligaram, e se ha GraphFrames aqui.

    `present` habilita o vocabulario de nomes ambiguos (item 1 do cabecalho).

    `constructors` e `packages` sao de MODULO e nao por escopo, ao contrario do
    resto deste extrator. A razao e que o nome ligado por um import identifica um
    simbolo importado, nao um DataFrame do usuario: para haver colisao alguem
    teria de religar `GF` a outra coisa noutro escopo, forma que nao apareceu em
    medicao nenhuma. Nome nu de DADO continua sendo por escopo, que e onde a
    colisao acontece de verdade.
    """

    present: bool
    constructors: frozenset[str]
    packages: frozenset[str]


def _import_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> tuple[list[Fact], _Imports]:
    """`graph.import` de todas as formas, e os nomes que elas ligaram.

    Quatro formas lidas, medidas como as que o codigo real usa:
    `from graphframes import GraphFrame`, `from graphframes import GraphFrame as
    GF`, `import graphframes` e `import graphframes as gf` -- em qualquer
    posicao do arquivo. Submodulo (`from graphframes.lib import Pregel`) conta
    como import do pacote.
    """
    facts: list[Fact] = []
    constructors = {_CONSTRUCTOR}
    packages: set[str] = set()
    present = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module != _PACKAGE and not module.startswith(_PACKAGE + "."):
                continue
            for alias in node.names:
                present = True
                if alias.name == _CONSTRUCTOR:
                    constructors.add(alias.asname or alias.name)
                facts.append(
                    _import_fact(node, alias, "from", module, path, ctx, lines, provenance)
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != _PACKAGE and not alias.name.startswith(_PACKAGE + "."):
                    continue
                present = True
                packages.add(alias.asname or alias.name.split(".")[0])
                facts.append(
                    _import_fact(node, alias, "plain", alias.name, path, ctx, lines, provenance)
                )

    return facts, _Imports(present, frozenset(constructors), frozenset(packages))


def _import_fact(
    node: ast.AST,
    alias: ast.alias,
    form: str,
    module: str,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    scope = ctx.function.get(id(node), "")
    attrs: dict[str, Any] = {
        "form": form,
        "module": module,
        "symbol": alias.name,
        # Onde o import esta. A afirmacao "este job usa GraphFrames" nao
        # enfraquece por o import estar dentro de uma funcao, mas quem escreve
        # regra pode querer estreitar, e a decisao e dela.
        "scope": "function" if scope else "module",
        # `try:`/`if` em volta e o idioma de dependencia OPCIONAL. Continua
        # sendo uso de GraphFrames; o atributo deixa a regra distinguir.
        "guarded": _guarded(node, ctx),
    }
    if alias.asname:
        attrs["alias"] = alias.asname
    return Fact(
        kind="graph.import",
        subject=_subject(node, path, ctx, lines),
        measures={"line": getattr(node, "lineno", 0)},
        attrs=attrs,
        provenance=provenance,
    )


def _guarded(node: ast.AST, ctx: _Context) -> bool:
    """O no esta sob `try` ou `if` em algum ponto ate a raiz."""
    current = ctx.parent.get(id(node))
    while current is not None:
        if isinstance(current, ast.Try | ast.If):
            return True
        current = ctx.parent.get(id(current))
    return False


def _dynamic_import_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> list[Fact]:
    """`importlib.import_module(...)` e `__import__(...)`: ponto cego CONTADO.

    So conta quando o pacote aparece LITERAL no argumento, ou quando o argumento
    nao e literal nenhum -- neste caso o nome pode ser montado em runtime, e a
    honestidade e dizer "nao sei", nao varrer o arquivo inteiro. Import dinamico
    de outro pacote, com nome literal, nao e assunto desta area.
    """
    facts: list[Fact] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            root, methods = _chain_root(node)
            if (root, methods[-1] if methods else "") not in _DYNAMIC_IMPORT_CALLS:
                continue
        elif isinstance(node.func, ast.Name) and node.func.id in _DYNAMIC_IMPORT_BARE:
            pass
        else:
            continue
        first = node.args[0] if node.args else None
        literal = _literal(first) if first is not None else None
        if literal is not None and not (
            isinstance(literal, str)
            and (literal == _PACKAGE or literal.startswith(_PACKAGE + "."))
        ):
            continue
        facts.append(
            _unresolved(
                _subject(node, path, ctx, lines),
                "dynamic_import",
                provenance,
                detail=literal if isinstance(literal, str) else "",
            )
        )
    return facts


def _receiver_name(node: ast.AST) -> str:
    """Ultimo segmento de nome do receptor, em minusculas. `""` quando nao ha."""
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    if isinstance(node, ast.Name):
        return node.id.lower()
    if isinstance(node, ast.Call):
        return _receiver_name(node.func)
    return ""


def _conf_receiver(node: ast.Call, method: str) -> bool:
    """O receptor autoriza CONTAR ponto cego de conf ilegivel neste no?

    Sem string distintiva para desempatar, o nome do receptor e a unica
    evidencia disponivel -- e ele e exigido so aqui, no caminho da chave que
    NAO deu para ler. O caminho do literal continua sem filtro de receptor.
    """
    name = _receiver_name(node.func.value) if isinstance(node.func, ast.Attribute) else ""
    if not name:
        return False
    if method == _CONF_BUILDER_METHOD:
        return any(hint in name for hint in _BUILDER_RECEIVER_HINTS)
    return _CONF_RECEIVER_HINT in name


def _conf_pairs(node: ast.Call, method: str) -> tuple[list[tuple[str, ast.AST | None]], bool]:
    """Pares (chave da conf, no do valor) que ESTA chamada declara.

    Devolve tambem se algo ficou ilegivel. Quatro formas correntes sao lidas, e
    a quinta e a que produz o ponto cego:

    - posicional -- `spark.conf.set("spark.checkpoint.dir", d)`;
    - keyword -- `spark.conf.set(key=..., value=...)`, e o mesmo em `config`;
    - `builder.config("spark.checkpoint.dir", d)`, na construcao da sessao;
    - `builder.config(map={...})` com dicionario de chaves literais;
    - qualquer chave que nao seja string literal -- constante, variavel de laco,
      `**kwargs`, ou um objeto inteiro em `config(conf=...)`. Ai a resposta e
      "nao sei", nunca "nao esta configurado".
    """
    keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
    starred = any(kw.arg is None for kw in node.keywords)

    if method == _CONF_BUILDER_METHOD and ("map" in keywords or "conf" in keywords):
        mapping = keywords.get("map")
        if "conf" in keywords or not isinstance(mapping, ast.Dict):
            # Um `SparkConf` inteiro, ou um mapa que nao e literal na fonte: as
            # chaves podem estar la e este modulo nao as ve.
            return [], True
        pairs: list[tuple[str, ast.AST | None]] = []
        for key_node, value_node in zip(mapping.keys, mapping.values, strict=True):
            literal = _literal(key_node) if key_node is not None else None
            if not isinstance(literal, str):
                return pairs, True
            pairs.append((literal, value_node))
        return pairs, starred

    if node.args:
        key_node = node.args[0]
        value_node = node.args[1] if len(node.args) > 1 else keywords.get("value")
    elif "key" in keywords:
        key_node = keywords["key"]
        value_node = keywords.get("value")
    elif starred:
        return [], True
    else:
        # Chamada sem argumento nenhum: nao declara conf, e nao e ponto cego.
        return [], False

    key = _literal(key_node)
    if not isinstance(key, str):
        return [], True
    return [(key, value_node)], False


def _checkpoint_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> tuple[list[Fact], str, list[Fact]]:
    """`graph.checkpoint_dir` e o estado de checkpoint DO ARQUIVO INTEIRO.

    ALCANCE MEDIDO, e o argumento e o objeto: `setCheckpointDir` e chamado no
    `SparkContext`, que e um singleton do processo -- o diretorio vale para a
    aplicacao inteira, nao para um escopo de nome. A forma canonica de job Glue
    ou EMR e configurar a sessao no topo do modulo, ou num `build_spark()`, e
    rodar o algoritmo noutra funcao. Correlacionar por escopo, como este modulo
    faz com vertices e arestas, produziria acusacao P0 sobre exatamente essa
    forma correta. E o inverso -- alcance de arquivo para nome de DADO -- e o
    que o resto do modulo recusa, porque ali dois nomes iguais sao dois objetos;
    aqui nao ha dois SparkContext.

    As DUAS confs entram no mesmo alcance e pelo mesmo motivo: quando aparecem
    no `.py` elas satisfazem ou dispensam a exigencia tanto quanto a chamada.
    Quando vem do IaC ou do `--conf`, nao estao aqui, e essa e a ressalva
    declarada da regra.

    Devolve tambem o estado -- `configured`, `absent` ou `unreadable` -- e os
    pontos cegos PENDENTES. `unreadable` cobre as duas metades da mesma conf, e
    a simetria e o conserto da revisao da Fase 6a: o VALOR ilegivel de local
    checkpoints ja omitia a decisao, e a CHAVE ilegivel afirmava `false` sobre
    dado que ninguem leu -- P0 sobre codigo correto em quatro formas correntes
    (`.config()` do builder, chave por constante, chave por laco, chave por
    keyword). Hoje qualquer das duas metades OMITE a decisao e conta o ponto
    cego.

    Os pontos cegos de CHAVE saem pendentes, e nao no retorno principal, porque
    quem decide se eles existem e o arquivo inteiro: emiti-los num `.py` sem
    grafo nenhum daria ponto cego de grafo a quem nunca falou de grafo, que e
    exatamente a razao pela qual o item 3 do cabecalho recusa emitir `unresolved`
    por `getattr`. `extract_graph` os descarta quando o arquivo nao tem sinal de
    grafo -- e ai o estado nao muda nada, porque nao ha algoritmo que consulte.
    """
    facts: list[Fact] = []
    pending: list[Fact] = []
    configured = False
    unreadable = False

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        if method == _SET_CHECKPOINT_DIR:
            configured = True
            attrs: dict[str, Any] = {"form": "set_checkpoint_dir"}
            value = _literal(node.args[0]) if node.args else None
            if isinstance(value, str):
                attrs["literal"] = value
            root, _ = _chain_root(node)
            if root is not None:
                attrs["receiver"] = root
            facts.append(
                Fact(
                    kind="graph.checkpoint_dir",
                    subject=_subject(node, path, ctx, lines),
                    measures={"line": node.lineno},
                    attrs=attrs,
                    provenance=provenance,
                )
            )
            continue
        if method not in _CONF_METHODS:
            continue

        pairs, illegible = _conf_pairs(node, method)
        if illegible and _conf_receiver(node, method):
            unreadable = True
            pending.append(
                _unresolved(
                    _subject(node, path, ctx, lines),
                    "unreadable_conf_key",
                    provenance,
                    method=method,
                )
            )
        for key, value_node in pairs:
            if key == _CONF_CHECKPOINT_DIR:
                configured = True
                attrs = {"form": "conf_checkpoint_dir", "method": method}
                value = _literal(value_node) if value_node is not None else None
                if isinstance(value, str):
                    attrs["literal"] = value
                facts.append(
                    Fact(
                        kind="graph.checkpoint_dir",
                        subject=_subject(node, path, ctx, lines),
                        measures={"line": node.lineno},
                        attrs=attrs,
                        provenance=provenance,
                    )
                )
            elif key == _CONF_LOCAL_CHECKPOINTS:
                value = _literal(value_node) if value_node is not None else None
                enabled = _truthy(value)
                if enabled is None:
                    unreadable = True
                    facts.append(
                        _unresolved(
                            _subject(node, path, ctx, lines),
                            # O rotulo diz QUAL metade falhou: sem valor literal
                            # nenhum e uma coisa, e um literal que nao converte
                            # para booleano (`1`) e outra.
                            "non_literal_argument" if value is None else "non_boolean_value",
                            provenance,
                            param=_CONF_LOCAL_CHECKPOINTS,
                        )
                    )
                    continue
                if enabled:
                    configured = True
                facts.append(
                    Fact(
                        kind="graph.checkpoint_dir",
                        subject=_subject(node, path, ctx, lines),
                        measures={"line": node.lineno},
                        attrs={
                            "form": "conf_local_checkpoints",
                            "method": method,
                            "enabled": enabled,
                        },
                        provenance=provenance,
                    )
                )

    if configured:
        return facts, "configured", pending
    return facts, ("unreadable" if unreadable else "absent"), pending


def _truthy(value: Any) -> bool | None:
    """Verdade de uma conf do Spark, que e string ou bool. `None` = ilegivel."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
    return None


def _construction_facts(
    node: ast.Call,
    imports: _Imports,
    path: str,
    ctx: _Context,
    lines: list[str],
    index: _ScopeIndex,
    provenance: dict[str, Any],
) -> list[Fact] | None:
    """`GraphFrame(v, e)`, que e `ast.Call` com `func=ast.Name`.

    O laco de `pyspark_ast.py:264` descarta tudo que nao e `ast.Attribute`, e
    por isso ele nao pode ser copiado aqui: a construcao do grafo cairia fora.
    A forma por atributo (`graphframes.GraphFrame(v, e)`) tambem entra, e ela so
    e reconhecida quando o `import` ligou aquele nome de pacote -- sem isso,
    `qualquer_coisa.GraphFrame(...)` seria adivinhacao.

    A PERSISTENCIA VAI NESTE MESMO FACT, e nao num kind proprio. A Fase 5d
    mediu (`D-5d-17`) que correlacao entre dois kinds casa objeto errado quando
    ha varios sujeitos; dois `GraphFrame(...)` no mesmo arquivo sao exatamente
    esse caso, e um `graph.source_persisted` separado teria de ser reunido por
    nome -- que e o que este modulo recusa fazer entre escopos.
    """
    if isinstance(node.func, ast.Name):
        if node.func.id not in imports.constructors:
            return None
        constructor = node.func.id
    elif isinstance(node.func, ast.Attribute) and node.func.attr == _CONSTRUCTOR:
        root, _ = _chain_root(node)
        if root is None or root not in imports.packages:
            return None
        constructor = f"{root}.{_CONSTRUCTOR}"
    else:
        return None

    position = (node.lineno, node.col_offset)
    attrs: dict[str, Any] = {
        "constructor": constructor,
        "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
    }
    for slot, key_ref, key_persisted in (
        (0, "vertices_ref", "vertices_persisted"),
        (1, "edges_ref", "edges_persisted"),
    ):
        argument = node.args[slot] if len(node.args) > slot else None
        if argument is None:
            continue
        root = _data_root(argument)
        if root is not None:
            attrs[key_ref] = root
        persisted = _persisted(argument, position, index)
        if persisted is not None:
            attrs[key_persisted] = persisted

    return [
        Fact(
            kind="graph.construction",
            subject=_subject(node, path, ctx, lines),
            measures={"line": node.lineno},
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _pregel_chain(node: ast.AST, ctx: _Context) -> list[tuple[str, ast.Call]]:
    """Metodos chamados SOBRE uma `@property`, caminhando para FORA.

    `g.pregel.setMaxIter(10).withVertexColumn(...).run()` comeca em `g.pregel`,
    que e o no que o vocabulario casa, e cresce para fora. Um `_chain_root`, que
    caminha para dentro, veria a cadeia a partir de `run` e chegaria a `g` sem
    nunca precisar do pai -- mas o no que dispara a leitura aqui e o do meio,
    entao a travessia e a oposta. Sem ela, `setMaxIter` fica invisivel.
    """
    chain: list[tuple[str, ast.Call]] = []
    current: ast.AST = node
    while True:
        parent = ctx.parent.get(id(current))
        if isinstance(parent, ast.Attribute) and parent.value is current:
            grandparent = ctx.parent.get(id(parent))
            if isinstance(grandparent, ast.Call) and grandparent.func is parent:
                chain.append((parent.attr, grandparent))
                current = grandparent
                continue
            current = parent
            continue
        break
    return chain


def _algorithm_arguments(
    node: ast.Call, name: str
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[str, dict[str, Any]]], bool]:
    """Argumentos LITERAIS que a pesquisa identificou como decisivos.

    Devolve (attrs, measures, pontos cegos, saida_ilegivel). `saida_ilegivel` e
    verdadeiro quando uma das tres saidas da exigencia de checkpoint aparece com
    valor que nao da para ler, ou quando a chamada tem posicional numa posicao
    que poderia ser uma delas. Nesses casos a decisao de checkpoint e OMITIDA:
    afirmar exigencia sobre codigo que talvez a tenha dispensado seria um P0
    falso, que e o pior modo de falha desta area.

    Os pontos cegos saem como (reason, extra) e nao como `Fact`, porque quem
    decide quantos emitir e `_algorithm_fact` -- ver a nota de UM PONTO CEGO POR
    CHAMADA la.
    """
    attrs: dict[str, Any] = {}
    measures: dict[str, Any] = {}
    blind: list[tuple[str, dict[str, Any]]] = []
    unreadable = False

    if name in _CHECKPOINT_ALGORITHMS and node.args:
        # A ordem dos parametros mudou entre linhagens e nao foi medida: um
        # posicional aqui pode ser `algorithm="graphx"`.
        unreadable = True
        blind.append(("positional_argument", {"algorithm": name}))

    for keyword in node.keywords:
        param = keyword.arg
        if param is None:
            # `**kwargs` pode conter qualquer uma das saidas.
            if name in _CHECKPOINT_ALGORITHMS:
                unreadable = True
                blind.append(("non_literal_argument", {"param": "**"}))
            continue
        if param not in _EXIT_ARGS and param not in _ITERATION_ARGS:
            continue
        value = _literal(keyword.value)
        if value is None:
            if param in _EXIT_ARGS:
                unreadable = True
            blind.append(("non_literal_argument", {"param": param}))
            continue
        if param == _ALGORITHM_ARG and isinstance(value, str):
            attrs["algorithm_arg"] = value
        elif param in _CHECKPOINT_INTERVAL_ARGS and isinstance(value, int | float):
            measures["checkpoint_interval"] = value
        elif param in _LOCAL_CHECKPOINT_ARGS:
            enabled = _truthy(value)
            if enabled is None:
                # `use_local_checkpoints=1` E literal, e chama-lo de
                # `non_literal_argument` mandava quem le procurar uma variavel
                # que nao existe. O que falta e a conversao para booleano.
                unreadable = True
                blind.append(("non_boolean_value", {"param": param}))
            else:
                attrs["use_local_checkpoints"] = enabled
        elif param in _ITERATION_ARGS:
            attrs["iteration_arg"] = param
            if isinstance(value, int | float) and not isinstance(value, bool):
                measures["iteration_literal"] = value

    return attrs, measures, blind, unreadable


def _checkpoint_required(
    name: str, attrs: dict[str, Any], measures: dict[str, Any], unreadable: bool
) -> bool | None:
    """A exigencia se aplica a ESTA chamada? `None` quando nao da para dizer.

    Transcricao do modo de falha medido, e nao juizo: com a implementacao
    default, sem `checkpointInterval` nao positivo e sem local checkpoints, o
    algoritmo levanta `java.io.IOException` na primeira iteracao se nao houver
    diretorio. As tres saidas legitimas (§4.3 da pesquisa) devolvem `false`:

    - `algorithm="graphx"` -- a implementacao GraphX nao faz checkpoint;
    - `checkpointInterval <= 0` -- `shouldCheckpoint = checkpointInterval > 0`,
      e com valor nao positivo o bloco inteiro e pulado;
    - `use_local_checkpoints=True` (0.9.3+) -- sem diretorio persistente, sem
      excecao.

    Emitir `false` nas tres e deliberado: sao declaracoes LIDAS no artefato, e
    calar sobre elas apagaria a diferenca entre "declarou saida" e "nao deu para
    ler", que e justamente o que o `None` marca.
    """
    if name not in _CHECKPOINT_ALGORITHMS:
        return None
    if unreadable:
        return None
    if attrs.get("algorithm_arg") == _GRAPHX:
        return False
    interval = measures.get("checkpoint_interval")
    if isinstance(interval, int | float) and interval <= 0:
        return False
    if attrs.get("use_local_checkpoints") is True:
        return False
    return True


def _algorithm_fact(
    node: ast.AST,
    name: str,
    form: str,
    call: ast.Call | None,
    receiver: ast.AST,
    path: str,
    ctx: _Context,
    lines: list[str],
    checkpoint_state: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    subject = _subject(node, path, ctx, lines)
    blind: list[tuple[str, dict[str, Any]]] = []
    attrs: dict[str, Any] = {
        "name": name,
        # Como o nome foi LIDO no fonte. `pregel` e `@property`, e um consumidor
        # que leia `form: "property"` sabe que nao ha lista de argumentos onde
        # procurar -- os parametros do Pregel vem por `setMaxIter(...)` na
        # cadeia, nao por keyword.
        "form": form,
        "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
    }
    root = _data_root(receiver)
    if root is None:
        blind.append(("receiver_without_name", {"algorithm": name}))
    else:
        attrs["receiver"] = root

    measures: dict[str, Any] = {"line": getattr(node, "lineno", 0)}
    unreadable = False
    if call is not None:
        extra_attrs, extra_measures, argument_blind, unreadable = _algorithm_arguments(call, name)
        attrs.update(extra_attrs)
        measures.update(extra_measures)
        blind = argument_blind + blind
    else:
        for method, chain_call in _pregel_chain(node, ctx):
            if method != _PREGEL_MAX_ITER or not chain_call.args:
                continue
            attrs["iteration_arg"] = _PREGEL_MAX_ITER
            value = _literal(chain_call.args[0])
            if isinstance(value, int | float) and not isinstance(value, bool):
                measures["iteration_literal"] = value

    unknown_exit = unreadable or checkpoint_state == "unreadable"
    required = _checkpoint_required(name, attrs, measures, unknown_exit)
    if required is not None:
        attrs["checkpoint_required"] = required
        # Sempre presente ao lado da exigencia, e nunca sozinho: e a metade da
        # pergunta que mora no arquivo e nao na chamada, e o motor nao
        # correlaciona dois facts. Fora de `connectedComponents` a pergunta nao
        # existe, e emitir o booleano ali seria ruido com cara de evidencia.
        attrs["checkpoint_configured_in_module"] = checkpoint_state == "configured"

    facts = [
        Fact(
            kind="graph.algorithm",
            subject=subject,
            measures=measures,
            attrs=attrs,
            provenance=provenance,
        )
    ]
    # UM PONTO CEGO POR CHAMADA. `Fact.id` e sha de `kind + subject + measures`
    # e `attrs` fica de FORA (`findings/models.py`), entao dois `graph.unresolved`
    # sobre o MESMO no sairiam com a mesma identidade e o `fact_id` que um
    # Finding cita deixaria de identificar evidencia. Uma chamada com posicional
    # E keyword ilegivel e um unico ponto cego -- "algo aqui nao deu para ler" --,
    # e a precedencia poe o argumento antes do receptor porque e o argumento que
    # suprime a decisao de checkpoint.
    if blind:
        reason, extra = blind[0]
        facts.append(_unresolved(subject, reason, provenance, **extra))
    return facts


def _is_called(node: ast.AST, ctx: _Context) -> bool:
    parent = ctx.parent.get(id(node))
    return isinstance(parent, ast.Call) and parent.func is node


def extract_graph(source: str, path: str) -> list[Fact]:
    """Extrai Facts de `source`. `path` e ancora e procedencia.

    Mesma assinatura de `pyspark_ast.extract_source`, o extrator irmao sobre o
    mesmo artefato: fonte em texto, e nao arvore, porque so quem tem o texto
    pode TENTAR o parse -- e o que a tentativa frustrada precisa produzir e o
    `graph.unresolved` com reason `syntax_error`, o ponto cego contado de um
    arquivo que ninguem conseguiu ler.

    A SENTINELA NAO SAI nesse caminho, e e deliberado: `graph.module_analyzed`
    carrega `parsed: True` e as quatro contagens do arquivo, e emiti-la sobre
    uma arvore que nao existe afirmaria "varri este arquivo" quando o que houve
    foi o contrario. A fixture `fonte_que_nao_compila` fixa esse retorno de UM
    fact so.
    """
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    provenance = {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            _unresolved(
                {
                    "type": "source_location",
                    "file": path,
                    "line": exc.lineno or 0,
                    "col": exc.offset or 0,
                    "symbol": "",
                    "snippet": "",
                },
                "syntax_error",
                provenance,
                detail=str(exc.msg),
            )
        ]

    ctx = _Context(tree)
    facts, imports = _import_facts(tree, path, ctx, lines, provenance)
    facts.extend(_dynamic_import_facts(tree, path, ctx, lines, provenance))
    checkpoint_facts, checkpoint_state, pending_blind = _checkpoint_facts(
        tree, path, ctx, lines, provenance
    )
    facts.extend(checkpoint_facts)

    calls = _ALGORITHM_CALLS | (_GATED_CALLS if imports.present else frozenset())
    properties = _ALGORITHM_PROPERTIES | (_GATED_PROPERTIES if imports.present else frozenset())

    for root, nodes in _scopes(tree):
        index = _scope_index(root, nodes)
        for node in nodes:
            if isinstance(node, ast.Call):
                construction = _construction_facts(
                    node, imports, path, ctx, lines, index, provenance
                )
                if construction is not None:
                    facts.extend(construction)
                    continue
                if isinstance(node.func, ast.Attribute) and node.func.attr in calls:
                    facts.extend(
                        _algorithm_fact(
                            node,
                            node.func.attr,
                            "call",
                            node,
                            node.func.value,
                            path,
                            ctx,
                            lines,
                            checkpoint_state,
                            provenance,
                        )
                    )
            elif (
                isinstance(node, ast.Attribute)
                and node.attr in properties
                and isinstance(node.ctx, ast.Load)
                and not _is_called(node, ctx)
            ):
                facts.extend(
                    _algorithm_fact(
                        node,
                        node.attr,
                        "property",
                        None,
                        node.value,
                        path,
                        ctx,
                        lines,
                        checkpoint_state,
                        provenance,
                    )
                )

    # Ponto cego de CHAVE de conf so conta em arquivo que fala de grafo. Sem
    # esta guarda, todo `.py` que configura Spark por laco ou por constante --
    # e nenhum deles menciona GraphFrames -- ganharia um ponto cego de GRAFO,
    # que e a objecao do item 3 do cabecalho ao `unresolved` por `getattr`.
    # Descartar aqui nao muda decisao nenhuma: sem sinal de grafo nao ha
    # `graph.algorithm`, e `checkpoint_state` so e consultado por ele.
    if any(f.kind in _GRAPH_SIGNAL_KINDS for f in facts):
        facts.extend(pending_blind)

    # Sentinela: prova de que a extracao de grafo rodou sobre este arquivo. Sem
    # ela, "nao ha grafo aqui" e "nao consegui ler" sao a mesma saida -- que e
    # exatamente o defeito que a §1 do spec mede no motor de hoje -- e uma
    # condicao `absent:` do catalogo seria vazamente verdadeira.
    facts.append(
        Fact(
            kind="graph.module_analyzed",
            subject=_file_subject(path),
            measures={
                "import_count": sum(1 for f in facts if f.kind == "graph.import"),
                "construction_count": sum(1 for f in facts if f.kind == "graph.construction"),
                "algorithm_count": sum(1 for f in facts if f.kind == "graph.algorithm"),
                "unresolved_count": sum(1 for f in facts if f.kind == "graph.unresolved"),
            },
            attrs={"parsed": True},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_graph_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.py`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira um unico `graph.unresolved` com reason `read_error`, e
    nunca uma excecao que derruba quem chamou: arquivo ilegivel e ponto cego
    CONTADO, e nao o fim da varredura. Mesma convencao de
    `data_quality.extract_data_quality_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [
            _unresolved(
                _file_subject(anchor),
                "read_error",
                {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                detail=str(exc),
            )
        ]
    return extract_graph(text, anchor)


def extract_graph_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.py` sob `root`, em ordem deterministica de path."""
    facts: list[Fact] = []
    for py_file in iter_source_files(root, "*.py"):
        rel = str(py_file.relative_to(repo_root)) if repo_root else str(py_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_graph_path(py_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            # Guarda larga de proposito: um `.py` que nao decodifica levanta
            # `UnicodeDecodeError`, que e `ValueError` e escaparia da guarda
            # estreita de `extract_graph_path`.
            facts.append(
                _unresolved(
                    _file_subject(anchor),
                    "read_error",
                    {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                    detail=str(exc),
                )
            )
    return sort_facts(facts)
