"""DataGraph de PySpark: tabela lida -> DataFrame -> transformacao -> tabela escrita.

O QUE ESTE MODULO ACRESCENTA AO QUE O REPOSITORIO JA EXTRAI
-----------------------------------------------------------
`sparkforge/facts/pyspark_ast.py` ja reconhece as chamadas da SPEC 34 --
`spark.table`, `spark.read`, `.format/.load`, `.write/.writeTo/.saveAsTable`,
`join/filter/select/withColumn/groupBy/agg`, `repartition/coalesce`,
`cache/persist/checkpoint`, `broadcast/union` -- e emite um Fact por ocorrencia,
com arquivo, linha e simbolo. O que ele NAO faz, e e a razao deste modulo
existir, e LIGAR uma ocorrencia a outra: um `pyspark.read` na linha 10 e um
`pyspark.write` na linha 16 sao dois pontos soltos, e nada no Fact diz que o
DataFrame escrito na 16 descende do lido na 10. Sem essa ligacao nao ha
montante nem jusante, e "de onde vem esta tabela" continua sem resposta.

O QUE E IMPORTADO E O QUE E REESCRITO, EXATAMENTE
-------------------------------------------------
Importados de `pyspark_ast`, sem copia: os conjuntos `_READ_TERMINALS`,
`_WRITE_TERMINALS`, `_PARTITION_METHODS`, `_REDUCTION_METHODS`,
`_DEDUP_METHODS` e `_CACHE_METHODS`, e os andarilhos de espinha fluente
`_Context`, `_chain_methods`, `_chain_calls` e `_is_chain_terminal`. Uma
segunda lista de metodos divergiria da primeira em silencio, e a divergencia so
apareceria como aresta faltando.

Reescritos aqui, e cada um com o motivo no lugar onde esta:

  `_eh_leitura` / `_eh_escrita` -- em `pyspark_ast` a condicao e uma expressao
  solta dentro do laco de deteccao, sem nome que se possa importar.

  `_TRANSFORMACOES_EXTRAS` -- o resto da SPEC 34 (`join`, `withColumn`,
  `groupBy`, `agg`, `union`...) nao esta agrupado la, aparece como literal
  solto.

  `_NEUTROS`, `_ELOS_QUE_CARREGAM_ALVO`, `_ORIGEM_POR_ELO`,
  `_OPERACAO_POR_METODO` -- nao existem em `pyspark_ast`, porque so um grafo
  precisa saber qual elo carrega destino e qual so configura.

A igualdade das duas reescritas com o original nao e confiada a leitura:
`test_codeintel_lineage.py` mede, sobre as 17 fixtures de `fixtures/pyspark/`,
que a classificacao de leitura/escrita daqui bate em CONTAGEM com os Facts
`pyspark.read`/`pyspark.write` do extrator, e falha se as duas se separarem.

POR QUE `attrs["target"]` DO FACT NAO E REUSADO
-----------------------------------------------
Essa e a unica parte de `pyspark_ast` que este modulo deliberadamente NAO
consome, e o motivo esta medido nos goldens do proprio repositorio.
`_target_literal` procura o primeiro literal string da cadeia inteira, sem
distinguir qual elo carrega destino. Em `fixtures/pyspark/clean_job`:

    spark.read.format("parquet").load(entrada)
        -> pyspark.read attrs.target == "parquet"     (e o FORMATO, nao o dado)

    relevantes.write.mode("overwrite").partitionBy("data_pedido").parquet(saida)
        -> pyspark.write attrs.target == "data_pedido" (e a COLUNA de particao)

Nenhum dos dois e um dataset. Uma aresta de linhagem construida sobre eles
criaria as "tabelas" `parquet` e `data_pedido` e mandaria quem investiga olhar
para um nome que nao existe -- o defeito exato que a SPEC 38 proibe. Aqui o
alvo sai do argumento posicional do elo que de fato CARREGA destino
(`_ELOS_QUE_CARREGAM_ALVO`), e `mode`, `format`, `option` e `partitionBy` estao
fora desse conjunto. Quando esse argumento nao e literal, nao ha nome: vira
`nao_resolvido`.

NAO INVENTAR NOME E A REGRA QUE DEFINE ESTE MODULO
---------------------------------------------------
`spark.table(f"{database}.{table}")` nao produz tabela nenhuma no grafo.
Produz um registro em `nao_resolvidos` com `DYNAMIC_TABLE_IDENTIFIER`, o
template com os buracos preservados (`"{database}.{table}"`) e os nomes das
variaveis. E a mesma doutrina de `AMBIGUOUS` em `resolve.py`: um palpite com
cara de fato faz alguem investigar a tabela errada, e nada acusa. Um ponto cego
CONTADO -- que e o que `nao_resolvidos` e -- se le como ponto cego; um nome
inventado se le como resposta.

SEM HEURISTICA DE TIPO
----------------------
Um nome so e DataFrame aqui se ele foi LIGADO a um: atribuido a partir de uma
leitura, de uma transformacao sobre um DataFrame ja conhecido, ou de um
`spark.sql`. `df.filter(...)` onde `df` e parametro de funcao nao produz aresta
nenhuma -- produz `UNKNOWN_RECEIVER`, o mesmo motivo que `resolve.py` usa. Se o
receptor fosse aceito por se chamar `df`, o grafo passaria a conter arestas
saindo de qualquer objeto com um metodo `filter`, e nenhuma delas se
distinguiria das verdadeiras.

O MODELO DE EXECUCAO E LINEAR, E ISSO E LIMITACAO ASSUMIDA
-----------------------------------------------------------
As ligacoes de um escopo sao aplicadas em ordem de linha, e a ultima atribuicao
antes do uso e a que vale. Uma atribuicao dentro de `if` conta como feita. Isto
descreve os FLUXOS POSSIVEIS, nao os executados: `df = spark.table("a")` num
ramo e `df = spark.table("b")` no outro produzem as duas arestas, e as duas sao
verdadeiras como possibilidade. Fica dito para nao ser descoberto como surpresa
por quem contar arestas esperando um caminho unico.

Escopo de funcao NAO herda ligacao do modulo. Herdar exigiria decidir se o
global foi reatribuido antes da chamada, e a ordem de chamada nao esta no AST.

A TAXA DE RESOLUCAO DE TABELA, MEDIDA
--------------------------------------
Sobre `fixtures/pyspark/` -- 17 jobs, o corpus que o resto do motor ja usa --
os datasets vistos sao em sua GRANDE MAIORIA dinamicos: as fixtures leem e
escrevem por parametro (`spark.read.parquet(caminho)`,
`df.write.parquet(destino)`), e so `version_out_of_scope` nomeia uma tabela
literal (`db.tbl`) via `df.writeTo("db.tbl")`. O valor absoluto nao esta
escrito aqui porque ele anda com a arvore; o que esta preso em teste e a RAZAO
-- `datasets_dinamicos > datasets_resolvidos`, com pelo menos um resolvido --
em `TestTaxaDeResolucao.test_no_corpus_a_maioria_dos_datasets_e_dinamica`.

Essa proporcao nao e defeito do detector: e o retrato de como job PySpark de
producao e escrito. E exatamente por isso que a SPEC 38 e a regra que define
esta fase -- se nome dinamico virasse palpite, a maioria do grafo seria
invencao.

POR QUE NADA DISTO E PERSISTIDO EM `db.py`
-------------------------------------------
O grafo e construido em memoria e devolvido; nao ha tabela nova no SQLite. O
schema de `db.py` e derrubado e refeito por `_descartar_schema_de_versao_anterior`
a partir de uma lista FIXA de tabelas (`_TABELAS_PARA_DESCARTE`). Uma tabela
criada daqui nao estaria nessa lista, e sobreviveria a um bump de
`SCHEMA_VERSION` carregando linhas do schema velho -- ponto cego silencioso do
tipo exato que este modulo existe para nao ter. Persistir e decisao de `db.py`,
e cabe a quem for editar `db.py`.
"""

from __future__ import annotations

import ast
from collections import deque
from dataclasses import dataclass

from sparkforge.codeintel.extract import VisitanteComEscopo
from sparkforge.codeintel.ids import node_id
from sparkforge.codeintel.resolve import UNKNOWN_RECEIVER
from sparkforge.facts.pyspark_ast import (
    _CACHE_METHODS,
    _DEDUP_METHODS,
    _PARTITION_METHODS,
    _READ_TERMINALS,
    _REDUCTION_METHODS,
    _WRITE_TERMINALS,
    _chain_calls,
    _chain_methods,
    _Context,
    _is_chain_terminal,
)

# Motivos de nao resolucao. `UNKNOWN_RECEIVER` vem de `resolve.py` e nao e
# redefinido aqui: e a mesma pergunta ("de que objeto sai esta chamada?") e um
# segundo literal com o mesmo texto divergiria no dia em que um dos dois mudasse.
DYNAMIC_TABLE_IDENTIFIER = "DYNAMIC_TABLE_IDENTIFIER"
SQL_NOT_PARSED = "SQL_NOT_PARSED"
NESTED_TOO_DEEP = "NESTED_TOO_DEEP"

# Marcador de nome ausente. Nunca e um nome de tabela: quem ler o grafo tem que
# tropecar nele, nao confundi-lo com um identificador do catalogo.
DINAMICO = "<dynamic>"

# Toda aresta emitida aqui vale 1.0, e a coluna existe porque a SPEC 37 pede
# `confidence` na resposta de linhagem. Vale 1.0 pelo mesmo motivo que em
# `resolve.py`: aresta so nasce quando o receptor esta determinado, e o caso em
# que ele nao esta nao vira aresta com desconto -- vira `UNKNOWN_RECEIVER`. Um
# valor intermediario aqui seria palpite com casa decimal.
_CONFIANCA_EXATA = 1.0

# Elos que carregam o DESTINO da operacao no primeiro argumento posicional. A
# ausencia de `mode`, `format`, `option` e `partitionBy` daqui e o conserto
# descrito na docstring do modulo, e nao esquecimento.
_ELOS_QUE_CARREGAM_ALVO = frozenset(
    {
        "table",
        "load",
        "save",
        "saveAsTable",
        "insertInto",
        "writeTo",
        "path",
        "parquet",
        "csv",
        "json",
        "orc",
        "text",
        "sql",
    }
)

# De qual API veio o dataset, e nao qual e a cara da string. `spark.table("x")`
# e tabela porque a API e de tabela; `.parquet("x")` e caminho porque a API e de
# caminho. Decidir por formato do texto ("tem barra, logo e caminho") seria
# adivinhacao sobre um dado que a chamada ja informa.
_ORIGEM_POR_ELO = {
    "table": "table",
    "saveAsTable": "table",
    "insertInto": "table",
    "writeTo": "table",
    "sql": "sql",
}
_ORIGEM_DE_CAMINHO = "path"

# Metodos que levam um DataFrame a outro DataFrame. Os quatro conjuntos vem de
# `pyspark_ast`; o resto da SPEC 34 nao esta agrupado la (aparece como literal
# solto dentro do laco de deteccao) e por isso e nomeado aqui.
_TRANSFORMACOES_EXTRAS = frozenset(
    {
        "join",
        "withColumn",
        "withColumnRenamed",
        "groupBy",
        "groupby",
        "agg",
        "union",
        "unionByName",
        "unionAll",
        "orderBy",
        "sort",
        "limit",
        "alias",
        "checkpoint",
        "localCheckpoint",
        "sample",
        "hint",
    }
)
_TRANSFORMACOES = frozenset(
    _PARTITION_METHODS
    | _REDUCTION_METHODS
    | _DEDUP_METHODS
    | _CACHE_METHODS
    | _TRANSFORMACOES_EXTRAS
)

# Metodos com DOIS DataFrames de entrada. O segundo lado entra pelo argumento
# posicional, e por isso ele e avaliado como expressao propria.
_BINARIOS = frozenset({"join", "union", "unionByName", "unionAll"})

# Elos que nao transformam o dado: configuram a operacao ou abrem o construtor
# de escrita. Passam adiante o DataFrame corrente sem produzir no nem aresta.
#
# `writeTo` esta aqui e nao entre os terminais de escrita porque em
# `df.writeTo("t").append()` quem termina a escrita e `append`, e e la que
# `pyspark_ast` emite `pyspark.write`. `writeTo` so CARREGA o nome da tabela --
# esta em `_ELOS_QUE_CARREGAM_ALVO` por isso. Deixa-lo de fora deste conjunto o
# fazia cair no ramo de metodo desconhecido, que zera o DataFrame corrente: a
# escrita seguinte perdia o receptor e virava `UNKNOWN_RECEIVER` mesmo com a
# variavel ligada duas linhas acima. Era o exemplo da SPEC 35 inteiro sem a
# ultima aresta.
#
# `createOrReplaceTempView` e as irmas NAO estao aqui de proposito: devolvem
# `None` em PySpark, e trata-las como neutras faria o DataFrame corrente
# sobreviver a uma chamada que o consome.
_NEUTROS = frozenset(
    {
        "read",
        "write",
        "writeTo",
        "format",
        "option",
        "options",
        "mode",
        "schema",
        "partitionBy",
        "bucketBy",
        "sortBy",
        "using",
        "tableProperty",
    }
)

# Rotulo da aresta. Maiuscula porque e como a SPEC 35 desenha a operacao, e
# porque distingue no olho a OPERACAO (`FILTER`) do metodo (`filter`).
_OPERACAO_POR_METODO = {
    "join": "JOIN",
    "union": "UNION",
    "unionByName": "UNION",
    "unionAll": "UNION",
    "filter": "FILTER",
    "where": "FILTER",
    "select": "SELECT",
    "selectExpr": "SELECT",
    "drop": "DROP",
    "withColumn": "WITHCOLUMN",
    "withColumnRenamed": "WITHCOLUMN",
    "groupBy": "GROUPBY",
    "groupby": "GROUPBY",
    "agg": "AGG",
    "dropDuplicates": "DEDUP",
    "drop_duplicates": "DEDUP",
    "distinct": "DEDUP",
    "repartition": "REPARTITION",
    "repartitionByRange": "REPARTITION",
    "coalesce": "COALESCE",
    "cache": "CACHE",
    "persist": "PERSIST",
    "checkpoint": "CHECKPOINT",
    "localCheckpoint": "CHECKPOINT",
    "orderBy": "ORDERBY",
    "sort": "ORDERBY",
    "limit": "LIMIT",
    "alias": "ALIAS",
    "sample": "SAMPLE",
    "hint": "HINT",
}
_LEITURA = "READ"
_ESCRITA = "WRITE"

# Funcoes de modulo que devolvem o proprio DataFrame que recebem. `broadcast` e
# da SPEC 34 e e a que aparece em codigo real; sem ela, `a.join(broadcast(b))`
# perderia o lado direito do join inteiro.
_REPASSADORAS = frozenset({"broadcast"})

# Teto de aninhamento de EXPRESSAO -- `a.join(b.join(c.join(...)))`. Nao e teto
# de cadeia fluente: a cadeia e percorrida por laco, nao por recursao. Existe
# porque uma biblioteca nao pode deixar `RecursionError` vazar para quem chamou
# por causa de um arquivo do repositorio analisado.
_PROFUNDIDADE_MAXIMA_DE_ANINHAMENTO = 32

_KIND_DATASET = "dataset"
_KIND_DATAFRAME = "dataframe"

# Direcoes de travessia. Nomeadas como em `graph.py`, e nao booleano `subir=`,
# porque `montante(x, subir=False)` seria lido como "montante" e devolveria
# jusante -- o tipo nao pega, e o nome errado sai no relatorio.
MONTANTE = "montante"
JUSANTE = "jusante"


@dataclass(frozen=True)
class NoDeDados:
    """Um dataset (tabela ou caminho) ou um DataFrame do grafo.

    `nome` de um dataset nao resolvido e `DINAMICO`, nunca um palpite -- ver a
    docstring do modulo. `resolvido` e campo e nao derivado de `nome != DINAMICO`
    porque um dia um nome pode ser conhecido e a resolucao continuar duvidosa por
    outro motivo, e nesse dia os dois campos precisam poder discordar.
    """

    identificador: str
    kind: str  # "dataset" | "dataframe"
    nome: str
    caminho: str
    linha: int
    escopo: str = ""
    origem: str = ""  # dataset: "table" | "path" | "sql"
    resolvido: bool = True


@dataclass(frozen=True)
class ArestaDeDados:
    """Um passo do fluxo: de onde o dado sai, para onde vai, e por qual operacao.

    Imutavel porque e EVIDENCIA, pelo mesmo motivo que `resolve.Aresta`: quem
    corrigir `destino` em vez de registrar um fato novo apaga o resultado da
    construcao, e aresta editada em silencio e indistinguivel de aresta medida.
    """

    origem: str
    destino: str
    operacao: str
    caminho: str
    linha: int
    confianca: float = _CONFIANCA_EXATA


@dataclass(frozen=True)
class DadoNaoResolvido:
    """Uma referencia a dataset ou a receptor que se TENTOU resolver e nao deu.

    `template` guarda a forma com os buracos preservados (`"{db}.{tbl}"`) quando
    a expressao e f-string, e `DINAMICO` quando nao ha forma nenhuma a mostrar
    (um nome nu, um subscript). `variaveis` sao os nomes lidos da expressao, em
    ordem, sem repeticao -- e o que permite a um humano ir ver de onde o nome
    vem sem que o motor tenha adivinhado.
    """

    reason: str
    caminho: str
    linha: int
    template: str = DINAMICO
    variaveis: tuple[str, ...] = ()
    operacao: str = ""


@dataclass(frozen=True)
class PassoDeLinhagem:
    """Um dataset alcancado pela travessia, com por onde se chegou nele."""

    nome: str
    identificador: str
    profundidade: int
    caminho: str
    linha: int
    operacao: str
    confianca: float
    resolvido: bool


@dataclass(frozen=True)
class GrafoDeDados:
    """O DataGraph inteiro: nos, arestas e os pontos cegos, lado a lado.

    `nao_resolvidos` e campo do grafo e nao lista jogada fora porque uma taxa
    que so conta acerto melhora sozinha quando alguem para de tentar. As duas
    contagens andam juntas, e e a razao entre elas que se pode publicar.
    """

    nos: tuple[NoDeDados, ...] = ()
    arestas: tuple[ArestaDeDados, ...] = ()
    nao_resolvidos: tuple[DadoNaoResolvido, ...] = ()
    # Quantas leituras e escritas foram DETECTADAS, que nao e o mesmo que
    # quantas viraram aresta: `df.writeTo("db.tbl").append()` com `df` de fora
    # do escopo e uma escrita detectada e zero aresta. Os dois numeros existem
    # lado a lado para que "o extrator viu" e "o grafo ligou" nao se confundam
    # -- e sao eles que `test_lineage_concorda_com_pyspark_ast_nas_fixtures`
    # compara com os Facts, que tambem contam deteccao e nao ligacao.
    leituras_detectadas: int = 0
    escritas_detectadas: int = 0

    @property
    def datasets(self) -> tuple[NoDeDados, ...]:
        return tuple(no for no in self.nos if no.kind == _KIND_DATASET)

    @property
    def datasets_resolvidos(self) -> int:
        return sum(1 for no in self.datasets if no.resolvido)

    @property
    def datasets_dinamicos(self) -> int:
        """Datasets que existem como ponto no fluxo mas cujo NOME nao se sabe."""
        return sum(1 for no in self.datasets if not no.resolvido)

    @property
    def taxa_de_resolucao(self) -> float:
        """Datasets nomeados sobre datasets vistos, contada agora e nao guardada.

        Propriedade e nao campo pelo mesmo motivo que em `resolve.Resolucao`: um
        numero gravado na construcao envelheceria em silencio no dia em que
        alguem filtrasse uma das duas listas.

        Zero dataset devolve 0.0 e nao 1.0: 100% sobre nada seria a mentira mais
        confortavel que este modulo poderia contar.
        """
        vistos = len(self.datasets)
        if vistos == 0:
            return 0.0
        return self.datasets_resolvidos / vistos

    def no(self, identificador: str) -> NoDeDados | None:
        return _indice_de_nos(self).get(identificador)


def construir(fonte: str, caminho: str) -> GrafoDeDados:
    """DataGraph de um arquivo. Nunca levanta por causa da forma da fonte.

    Sintaxe invalida devolve grafo VAZIO e arvore profunda demais devolve grafo
    com um ponto cego `NESTED_TOO_DEEP` -- os dois sao ponto cego e nao erro
    fatal, pela mesma razao de `extract.extrair_nos`: um repositorio de cliente
    tem arquivo com sintaxe de outra versao de Python, e derrubar a construcao
    inteira por causa de um trocaria cobertura parcial por nenhuma.

    Os dois casos nao devolvem a mesma coisa de proposito. Sintaxe invalida ja
    e visivel em `extract` e em `index`, que contam ilegiveis; profundidade nao
    e visivel em lugar nenhum, e um grafo vazio calado a faria passar por
    "arquivo sem PySpark".

    `ValueError` esta na captura porque a excecao do byte nulo mudou de tipo
    entre 3.10 e 3.11 -- medido em `extract.py`, mesma arvore.
    """
    try:
        arvore = ast.parse(fonte)
    except (SyntaxError, ValueError):
        return GrafoDeDados()
    construtor = _Construtor(caminho, arvore)
    try:
        construtor.percorrer()
    except RecursionError:
        # A cadeia fluente e percorrida por laco aqui, mas a descoberta de
        # escopos passa por `VisitanteComEscopo`, que herda de
        # `ast.NodeVisitor` -- e NodeVisitor desce a arvore por recursao
        # Python. Uma cadeia longa produz uma arvore profunda, e a partir de um
        # certo comprimento a pilha acaba. MEDIDO com `spark.table("a.b")`
        # seguido de N `.filter("x")`, com `sys.getrecursionlimit()` em 1000, e
        # o mesmo resultado em 3.10.20, 3.11.15 e 3.14.6:
        #
        #     N = 200   passa
        #     N = 250   RecursionError
        #
        # O mesmo insumo faz `extract.extrair_nos` LEVANTAR nas tres versoes,
        # pela mesma pilha compartilhada -- nao e defeito introduzido aqui.
        #
        # Aqui vira ponto cego CONTADO em vez de excecao vazando: uma
        # biblioteca nao pode derrubar quem a chamou por causa da forma do
        # codigo do repositorio analisado, e devolver grafo vazio calado faria
        # "arquivo profundo demais" ficar indistinguivel de "arquivo sem
        # PySpark".
        return GrafoDeDados(
            nao_resolvidos=(
                DadoNaoResolvido(reason=NESTED_TOO_DEEP, caminho=caminho, linha=0),
            )
        )
    return construtor.grafo()


def mesclar(grafos: list[GrafoDeDados]) -> GrafoDeDados:
    """Une grafos de arquivos diferentes num so.

    E aqui que a linhagem atravessa arquivo: o identificador de um dataset
    RESOLVIDO nao carrega caminho (ver `_id_de_dataset`), entao `gold.vendas`
    escrita em `a.py` e o MESMO no que `gold.vendas` lida em `b.py`, e a aresta
    de um alcanca a do outro. Dataset nao resolvido carrega caminho e linha de
    proposito: dois nomes desconhecidos nao sao o mesmo desconhecido, e uni-los
    inventaria uma ligacao que ninguem mediu.
    """
    nos: dict[str, NoDeDados] = {}
    arestas: list[ArestaDeDados] = []
    nao_resolvidos: list[DadoNaoResolvido] = []
    for grafo in grafos:
        for no in grafo.nos:
            nos.setdefault(no.identificador, no)
        arestas.extend(grafo.arestas)
        nao_resolvidos.extend(grafo.nao_resolvidos)
    return GrafoDeDados(
        nos=tuple(sorted(nos.values(), key=_chave_de_no)),
        arestas=tuple(sorted(arestas, key=_chave_de_aresta)),
        nao_resolvidos=tuple(sorted(nao_resolvidos, key=_chave_de_nao_resolvido)),
        leituras_detectadas=sum(g.leituras_detectadas for g in grafos),
        escritas_detectadas=sum(g.escritas_detectadas for g in grafos),
    )


def linhagem_de_tabela(
    grafo: GrafoDeDados,
    alvo: str,
    direcao: str = MONTANTE,
    profundidade: int = 3,
) -> tuple[PassoDeLinhagem, ...]:
    """Datasets alcancados a partir de `alvo`, com arquivo, linha, operacao e confianca.

    A profundidade conta SALTO ENTRE DATASETS, e nao aresta: os DataFrames
    intermediarios sao atravessados sem consumir nivel. E o que faz
    `profundidade=1` sobre `gold.x` devolver as tabelas que a alimentam
    diretamente, e nao os quatro `withColumn` no meio do caminho -- que e o
    desenho da SPEC 37.

    O conjunto de visitados nao e otimizacao, e vale aqui a mesma razao de
    `graph.py`: um dataset que se le e se escreve no mesmo job e um ciclo, e sem
    visitados a travessia o reemite a cada nivel ate o teto. Cada dataset sai
    UMA vez, na MENOR profundidade em que foi alcancado -- que e a distancia ate
    o alvo, e e por ela que quem le decide o que olhar primeiro.

    `alvo` que nao existe no grafo devolve tupla vazia. Nao levanta: perguntar
    pela linhagem de uma tabela que este codigo nao toca e pergunta legitima, e
    a resposta e "nenhuma", nao um erro.
    """
    if direcao not in (MONTANTE, JUSANTE):
        raise ValueError(f"direcao invalida: {direcao!r}")

    indice = _indice_de_nos(grafo)
    vizinhos = _adjacencia(grafo, direcao)
    inicio = [no.identificador for no in grafo.datasets if no.nome == alvo]
    if not inicio:
        return ()

    visitados = set(inicio)
    passos: list[PassoDeLinhagem] = []
    fila: deque[tuple[str, int, str, float, int, str]] = deque(
        (identificador, 0, "", _CONFIANCA_EXATA, 0, "") for identificador in inicio
    )

    while fila:
        atual, nivel, operacao, confianca, linha, arquivo = fila.popleft()
        no = indice.get(atual)
        if no is None:
            continue
        if no.kind == _KIND_DATASET and nivel > 0:
            passos.append(
                PassoDeLinhagem(
                    nome=no.nome,
                    identificador=no.identificador,
                    profundidade=nivel,
                    caminho=arquivo,
                    linha=linha,
                    operacao=operacao,
                    confianca=confianca,
                    resolvido=no.resolvido,
                )
            )
        if nivel >= profundidade and no.kind == _KIND_DATASET:
            continue
        for aresta, vizinho in vizinhos.get(atual, ()):
            if vizinho in visitados:
                continue
            destino = indice.get(vizinho)
            if destino is None:
                continue
            # So o salto que CHEGA num dataset consome nivel. Atravessar
            # DataFrame de graca e o que faz a profundidade medir distancia
            # entre tabelas, como a SPEC 37 desenha.
            proximo = nivel + 1 if destino.kind == _KIND_DATASET else nivel
            if destino.kind == _KIND_DATASET and proximo > profundidade:
                continue
            visitados.add(vizinho)
            rotulo = aresta.operacao if destino.kind == _KIND_DATASET else operacao
            fila.append(
                (vizinho, proximo, rotulo, aresta.confianca, aresta.linha, aresta.caminho)
            )

    passos.sort(key=lambda p: (p.profundidade, p.nome, p.caminho, p.linha))
    return tuple(passos)


def montante(
    grafo: GrafoDeDados, identificador: str, profundidade: int = 3
) -> tuple[PassoDeLinhagem, ...]:
    """Nos que alimentam `identificador`, DataFrames intermediarios inclusive.

    Diferente de `linhagem_de_tabela`, que so devolve dataset: aqui a pergunta e
    a da SPEC 36, "de que DataFrame veio este DataFrame", e esconder os
    intermediarios apagaria justamente a resposta.
    """
    return _travessia_completa(grafo, identificador, MONTANTE, profundidade)


def jusante(
    grafo: GrafoDeDados, identificador: str, profundidade: int = 3
) -> tuple[PassoDeLinhagem, ...]:
    """Nos alimentados por `identificador`. Ver `montante`."""
    return _travessia_completa(grafo, identificador, JUSANTE, profundidade)


class _ColetorDeEscopos(VisitanteComEscopo):
    """`no de definicao -> nome qualificado do escopo`, via a pilha compartilhada.

    Herda de `VisitanteComEscopo` e nao monta pilha propria porque a base diz,
    na docstring dela, que uma segunda pilha divergiria da primeira em silencio.
    O nome qualificado que sai daqui e o MESMO de `extract.No.qualified_name`, e
    e essa igualdade que permite casar um DataFrame deste grafo com o simbolo do
    indice.
    """

    def __init__(self) -> None:
        super().__init__()
        self.escopos: dict[int, str] = {}

    def _ao_entrar(self, no, kind: str) -> None:
        # `kind` faz parte do contrato da base e nao e usado aqui: esta classe
        # so quer o nome qualificado, e distinguir metodo de funcao nao muda o
        # nome. Fica na assinatura porque a base chama posicionalmente.
        del kind
        self.escopos[id(no)] = ".".join([*self._nomes, no.name])


class _Construtor:
    """Uma passagem por arquivo: descobre escopos, depois liga statements em ordem.

    Estado mutavel de proposito, e por isso e classe e nao funcao: `_ligacoes`
    muda a cada atribuicao, e passar esse dicionario por parametro por seis
    niveis de chamada esconderia que ele e o unico estado que importa.
    """

    def __init__(self, caminho: str, arvore: ast.Module) -> None:
        self.caminho = caminho
        self.arvore = arvore
        self.ctx = _Context(arvore)
        self.nos: dict[str, NoDeDados] = {}
        self.arestas: list[ArestaDeDados] = []
        self.nao_resolvidos: list[DadoNaoResolvido] = []
        self._ligacoes: dict[str, str] = {}
        self._escopo = ""
        self._anonimos = 0
        self._receptor_reportado = False
        self.leituras = 0
        self.escritas = 0

    def grafo(self) -> GrafoDeDados:
        return GrafoDeDados(
            nos=tuple(sorted(self.nos.values(), key=_chave_de_no)),
            arestas=tuple(sorted(self.arestas, key=_chave_de_aresta)),
            nao_resolvidos=tuple(sorted(self.nao_resolvidos, key=_chave_de_nao_resolvido)),
            leituras_detectadas=self.leituras,
            escritas_detectadas=self.escritas,
        )

    def percorrer(self) -> None:
        coletor = _ColetorDeEscopos()
        coletor.visit(self.arvore)

        definicoes: list[tuple[ast.AST, str]] = [(self.arvore, "")]
        for no in ast.walk(self.arvore):
            nome = coletor.escopos.get(id(no))
            if nome is not None:
                definicoes.append((no, nome))

        for definicao, escopo in definicoes:
            self._escopo = escopo
            # Escopo novo comeca SEM ligacao herdada -- ver a docstring do modulo.
            self._ligacoes = {}
            for stmt in _statements_do_escopo(getattr(definicao, "body", [])):
                self._statement(stmt)

    def _statement(self, stmt: ast.stmt) -> None:
        if isinstance(stmt, ast.Assign):
            valor = self._expressao(stmt.value, 0)
            for alvo in stmt.targets:
                self._ligar(alvo, valor)
            return
        if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            self._ligar(stmt.target, self._expressao(stmt.value, 0))
            return
        if isinstance(stmt, ast.AugAssign):
            # `df += x` nao e idioma de DataFrame; avaliar o lado direito ainda
            # registra o que houver de leitura/escrita nele, mas o alvo nao e
            # religado: religa-lo afirmaria uma transformacao que nao existe.
            self._expressao(stmt.value, 0)
            return
        if isinstance(stmt, ast.Expr):
            self._expressao(stmt.value, 0)
            return
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            self._expressao(stmt.value, 0)
            return
        for filho in ast.iter_child_nodes(stmt):
            if isinstance(filho, ast.expr):
                self._expressao(filho, 0)

    def _ligar(self, alvo: ast.expr, valor: str | None) -> None:
        """Associa um nome ao DataFrame que ele passa a designar.

        Alvo que nao e `Name` -- tupla, subscript, atributo -- nao e ligado.
        Ligar `d["x"] = df` exigiria saber que `d["x"]` sera lido depois com a
        mesma chave, e a chave pode ser calculada: seria palpite.
        """
        if not isinstance(alvo, ast.Name):
            return
        if valor is None:
            # Reatribuicao para algo que nao e DataFrame conhecido APAGA a
            # ligacao anterior. Manter a antiga faria o nome continuar
            # designando um DataFrame que ele ja nao designa, e a aresta
            # seguinte sairia do no errado.
            self._ligacoes.pop(alvo.id, None)
            return
        self._ligacoes[alvo.id] = valor

    def _expressao(self, expressao: ast.expr, aninhamento: int) -> str | None:
        """Identificador do DataFrame que `expressao` produz, ou None.

        `None` significa "nao e um DataFrame que este modulo conhece", e nao "e
        um erro": literal, chamada de funcao qualquer e parametro nao ligado
        caem todos aqui.
        """
        if aninhamento > _PROFUNDIDADE_MAXIMA_DE_ANINHAMENTO:
            self._registrar_nao_resolvido(
                NESTED_TOO_DEEP, _linha(expressao), operacao=""
            )
            return None

        if isinstance(expressao, ast.Name):
            return self._ligacoes.get(expressao.id)

        if not isinstance(expressao, ast.Call):
            # `glue_context.spark_session` e afins caem aqui: o nome da raiz pode
            # estar ligado, mas devolver a ligacao da raiz afirmaria que o
            # ATRIBUTO e o DataFrame da raiz, o que e falso.
            return None

        if isinstance(expressao.func, ast.Name):
            if expressao.func.id in _REPASSADORAS and expressao.args:
                return self._expressao(expressao.args[0], aninhamento + 1)
            return None

        if not isinstance(expressao.func, ast.Attribute):
            # `getattr(df, metodo)(1)` -- fixture `dynamic_dispatch`. O chamado
            # e o RESULTADO de outra chamada, e `_chain_methods` nao tem espinha
            # de atributo para andar: devolve a propria expressao como raiz.
            # Entregar isso a `_cadeia` faria `_expressao` chamar a si mesma com
            # o mesmo no ate o teto de aninhamento -- profundidade gasta para
            # concluir o que ja se sabe aqui, que nao ha cadeia a seguir.
            return None

        return self._cadeia(expressao, aninhamento)

    def _cadeia(self, chamada: ast.Call, aninhamento: int) -> str | None:
        """Roda `_elos` com a bandeira de receptor ja reportado zerada.

        Um receptor desconhecido e UM ponto cego, e nao um por elo: a cadeia de
        doze `withColumn` de `fixtures/pyspark/withcolumn_run` sai de um unico
        `df` que e parametro de funcao. Doze registros do mesmo desconhecimento
        inflariam a contagem de pontos cegos por doze e esconderiam quantos
        receptores de fato nao resolvem.

        A bandeira e salva e RESTAURADA porque cadeia aninha:
        `a.join(b.filter(x))` tem duas, e a de dentro nao pode calar a de fora.
        """
        anterior = self._receptor_reportado
        self._receptor_reportado = False
        try:
            return self._elos(chamada, aninhamento)
        finally:
            self._receptor_reportado = anterior

    def _elos(self, chamada: ast.Call, aninhamento: int) -> str | None:
        """Percorre a espinha fluente em ordem de escrita, elo por elo.

        Laco e nao recursao: uma cadeia com doze `withColumn` produz uma arvore
        de doze niveis, e recursao por elo somaria essa profundidade a de cada
        expressao aninhada. Mesmo motivo pelo qual `_Context` e `_chain_methods`
        usam pilha explicita.

        Chamada so por `_cadeia`, que e quem cuida da bandeira -- entrar por
        aqui direto faria a cadeia herdar o "ja reportei" da cadeia anterior.
        """
        metodos, raiz = _chain_methods(chamada)
        chamadas = _chain_calls(chamada)
        corrente = self._expressao(raiz, aninhamento + 1) if isinstance(raiz, ast.expr) else None

        for elo in chamadas:
            if not isinstance(elo.func, ast.Attribute):
                continue
            metodo = elo.func.attr

            if _eh_leitura(elo, metodo, metodos, raiz, self.ctx):
                self.leituras += 1
                corrente = self._leitura(elo, metodo, chamadas)
                continue

            if _eh_escrita(elo, metodo, metodos, self.ctx):
                self.escritas += 1
                self._escrita(elo, metodo, chamadas, corrente)
                corrente = None
                continue

            if metodo in _NEUTROS:
                continue

            if metodo in _TRANSFORMACOES:
                corrente = self._transformacao(elo, metodo, corrente, aninhamento)
                continue

            # Metodo desconhecido nao propaga o DataFrame. Propagar seria
            # assumir que todo metodo devolve DataFrame -- `df.schema.json()`
            # nao devolve, e a aresta seguinte sairia de um no que nao existe.
            corrente = None

        return corrente

    def _leitura(self, elo: ast.Call, metodo: str, chamadas: list[ast.Call]) -> str | None:
        alvo, elo_do_alvo = _expressao_do_alvo(elo, metodo, chamadas)
        origem = _ORIGEM_POR_ELO.get(elo_do_alvo, _ORIGEM_DE_CAMINHO)
        linha = _linha(elo)

        if origem == "sql":
            # SQL nao e parseado aqui, e por isso NAO ha aresta: a direcao de um
            # `spark.sql` so se sabe lendo a query (`SELECT` le, `MERGE INTO`
            # escreve), e uma aresta na direcao errada manda quem investiga para
            # o lado oposto do fluxo. O ponto cego e registrado; o DataFrame que
            # `sql` devolve existe e segue encadeavel, so nasce sem procedencia.
            literal = _texto_literal(alvo) is not None
            razao = SQL_NOT_PARSED if literal else DYNAMIC_TABLE_IDENTIFIER
            # O template NAO recebe a query. Em `spark.sql` o argumento e SQL
            # inteiro, nao um identificador de tabela com buracos: guardar o
            # texto da query aqui poria um bloco de fonte num campo que quem le
            # espera que seja um nome, e ainda arrastaria para o registro o
            # corpo do MERGE de `examples/glue_iceberg_job.py`. As variaveis
            # ficam, porque sao elas que dizem onde ir olhar.
            _, variaveis = _forma_dinamica(alvo)
            self._registrar_nao_resolvido(
                razao, linha, variaveis=variaveis, operacao=_LEITURA
            )
            return self._dataframe_anonimo(linha)

        dataset = self._dataset(alvo, origem, linha, _LEITURA)
        destino = self._dataframe_anonimo(linha)
        self.arestas.append(
            ArestaDeDados(
                origem=dataset,
                destino=destino,
                operacao=_LEITURA,
                caminho=self.caminho,
                linha=linha,
            )
        )
        return destino

    def _escrita(
        self,
        elo: ast.Call,
        metodo: str,
        chamadas: list[ast.Call],
        corrente: str | None,
    ) -> None:
        alvo, elo_do_alvo = _expressao_do_alvo(elo, metodo, chamadas)
        origem = _ORIGEM_POR_ELO.get(elo_do_alvo, _ORIGEM_DE_CAMINHO)
        linha = _linha(elo)
        dataset = self._dataset(alvo, origem, linha, _ESCRITA)

        if corrente is None:
            # A escrita EXISTE e o dataset e registrado; o que falta e de onde o
            # dado vem. Omitir o dataset porque o receptor e desconhecido
            # esconderia uma tabela que o job de fato escreve.
            self._receptor_desconhecido(linha, _ESCRITA)
            return

        self.arestas.append(
            ArestaDeDados(
                origem=corrente,
                destino=dataset,
                operacao=_ESCRITA,
                caminho=self.caminho,
                linha=linha,
            )
        )

    def _transformacao(
        self,
        elo: ast.Call,
        metodo: str,
        corrente: str | None,
        aninhamento: int,
    ) -> str | None:
        linha = _linha(elo)
        operacao = _OPERACAO_POR_METODO.get(metodo, metodo.upper())

        lado_direito = None
        if metodo in _BINARIOS and elo.args:
            lado_direito = self._expressao(elo.args[0], aninhamento + 1)

        if corrente is None:
            self._receptor_desconhecido(linha, operacao)
            return None

        destino = self._dataframe_anonimo(linha)
        self.arestas.append(
            ArestaDeDados(
                origem=corrente,
                destino=destino,
                operacao=operacao,
                caminho=self.caminho,
                linha=linha,
            )
        )
        if lado_direito is not None:
            self.arestas.append(
                ArestaDeDados(
                    origem=lado_direito,
                    destino=destino,
                    operacao=operacao,
                    caminho=self.caminho,
                    linha=linha,
                )
            )
        return destino

    def _dataset(
        self, alvo: ast.expr | None, origem: str, linha: int, operacao: str
    ) -> str:
        nome = _texto_literal(alvo) if alvo is not None else None
        if nome is None:
            template, variaveis = _forma_dinamica(alvo)
            self._registrar_nao_resolvido(
                DYNAMIC_TABLE_IDENTIFIER,
                linha,
                template=template,
                variaveis=variaveis,
                operacao=operacao,
            )
            identificador = _id_de_dataset(DINAMICO, origem, self.caminho, linha)
            self._registrar_no(
                NoDeDados(
                    identificador=identificador,
                    kind=_KIND_DATASET,
                    nome=DINAMICO,
                    caminho=self.caminho,
                    linha=linha,
                    origem=origem,
                    resolvido=False,
                )
            )
            return identificador

        identificador = _id_de_dataset(nome, origem, "", 0)
        self._registrar_no(
            NoDeDados(
                identificador=identificador,
                kind=_KIND_DATASET,
                nome=nome,
                caminho=self.caminho,
                linha=linha,
                origem=origem,
                resolvido=True,
            )
        )
        return identificador

    def _dataframe_anonimo(self, linha: int) -> str:
        """Um DataFrame por PASSO, e nao por variavel.

        `df = df.filter(x)` e uma reatribuicao em Python e dois DataFrames no
        fluxo: colapsar os dois no nome `df` produziria uma aresta de `df` para
        `df` -- um autolaco que a travessia teria de aprender a ignorar, e que
        apagaria a ordem das transformacoes junto.
        """
        self._anonimos += 1
        identificador = node_id(
            self.caminho, _KIND_DATAFRAME, f"{self._escopo}#{self._anonimos}", str(linha)
        )
        self._registrar_no(
            NoDeDados(
                identificador=identificador,
                kind=_KIND_DATAFRAME,
                nome=f"#{self._anonimos}",
                caminho=self.caminho,
                linha=linha,
                escopo=self._escopo,
            )
        )
        return identificador

    def _registrar_no(self, no: NoDeDados) -> None:
        self.nos.setdefault(no.identificador, no)

    def _receptor_desconhecido(self, linha: int, operacao: str) -> None:
        """Registra o receptor nao resolvido da cadeia corrente, uma vez so."""
        if self._receptor_reportado:
            return
        self._receptor_reportado = True
        self._registrar_nao_resolvido(UNKNOWN_RECEIVER, linha, operacao=operacao)

    def _registrar_nao_resolvido(
        self,
        reason: str,
        linha: int,
        template: str = DINAMICO,
        variaveis: tuple[str, ...] = (),
        operacao: str = "",
    ) -> None:
        self.nao_resolvidos.append(
            DadoNaoResolvido(
                reason=reason,
                caminho=self.caminho,
                linha=linha,
                template=template,
                variaveis=variaveis,
                operacao=operacao,
            )
        )


def _eh_leitura(
    elo: ast.Call, metodo: str, metodos: list[str], raiz: ast.AST, ctx: _Context
) -> bool:
    """Mesma condicao que `pyspark_ast` aplica para emitir `pyspark.read`.

    Escrita aqui em vez de importada porque em `pyspark_ast` ela e uma expressao
    solta dentro do laco de deteccao, sem nome. A igualdade entre as duas nao e
    confiada a leitura: `test_lineage_concorda_com_pyspark_ast_nas_fixtures` a
    mede em contagem sobre as 17 fixtures do corpus, e falha se divergirem.
    """
    return (
        metodo in _READ_TERMINALS
        and _is_chain_terminal(elo, _READ_TERMINALS, ctx)
        and (
            "read" in metodos
            or (metodo in ("table", "sql") and isinstance(raiz, ast.Name) and raiz.id == "spark")
        )
    )


def _eh_escrita(elo: ast.Call, metodo: str, metodos: list[str], ctx: _Context) -> bool:
    """Mesma condicao que `pyspark_ast` aplica para emitir `pyspark.write`. Ver `_eh_leitura`."""
    return (
        metodo in _WRITE_TERMINALS
        and _is_chain_terminal(elo, _WRITE_TERMINALS, ctx)
        and ("write" in metodos or "writeTo" in metodos)
    )


def _expressao_do_alvo(
    elo: ast.Call, metodo: str, chamadas: list[ast.Call]
) -> tuple[ast.expr | None, str]:
    """Expressao que nomeia o dataset, e o metodo do elo que a carrega.

    Procura no proprio elo terminal primeiro e so depois volta na cadeia, e a
    volta e restrita a `_ELOS_QUE_CARREGAM_ALVO`. E a restricao que impede
    `partitionBy("data_pedido")` de virar destino -- ver a docstring do modulo,
    onde o caso esta medido no golden de `clean_job`.
    """
    if metodo in _ELOS_QUE_CARREGAM_ALVO and elo.args:
        return elo.args[0], metodo
    for anterior in reversed(chamadas):
        if anterior is elo:
            continue
        if not isinstance(anterior.func, ast.Attribute):
            continue
        nome = anterior.func.attr
        if nome in _ELOS_QUE_CARREGAM_ALVO and anterior.args:
            return anterior.args[0], nome
    return None, metodo


def _texto_literal(no: ast.expr | None) -> str | None:
    """A string se `no` e literal de string; None em qualquer outro caso.

    `ast.Constant` com valor bool ou numero devolve None de proposito: nome de
    tabela e texto, e aceitar `True` produziria o dataset chamado "True".
    """
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return no.value
    if isinstance(no, ast.JoinedStr) and all(
        isinstance(parte, ast.Constant) for parte in no.values
    ):
        # f-string sem nenhum buraco e literal: `f"gold.vendas"` nomeia tanto
        # quanto `"gold.vendas"`.
        return "".join(str(parte.value) for parte in no.values)  # type: ignore[attr-defined]
    return None


def _forma_dinamica(no: ast.expr | None) -> tuple[str, tuple[str, ...]]:
    """Template com os buracos preservados e os nomes lidos na expressao.

    `f"{db}.{tbl}"` devolve `("{db}.{tbl}", ("db", "tbl"))`. Um nome nu ou um
    subscript nao tem forma a mostrar e devolve `DINAMICO` -- inventar
    `"{nome}"` para eles sugeriria uma estrutura que a fonte nao tem.

    O template guarda as partes LITERAIS da f-string, e isso e deliberado: e
    exatamente `bronze.` em `f"bronze.{tabela}"` que diz em qual database
    procurar, e apaga-lo deixaria o registro sem a metade que se sabe.
    """
    if no is None:
        return DINAMICO, ()

    variaveis: list[str] = []
    vistos: set[str] = set()
    for sub in ast.walk(no):
        if isinstance(sub, ast.Name) and sub.id not in vistos:
            vistos.add(sub.id)
            variaveis.append(sub.id)

    if not isinstance(no, ast.JoinedStr):
        return DINAMICO, tuple(variaveis)

    partes: list[str] = []
    for parte in no.values:
        if isinstance(parte, ast.Constant):
            partes.append(str(parte.value))
        elif isinstance(parte, ast.FormattedValue):
            nome = parte.value.id if isinstance(parte.value, ast.Name) else DINAMICO
            partes.append("{" + nome + "}")
    return "".join(partes), tuple(variaveis)


def _statements_do_escopo(corpo: list[ast.stmt]) -> list[ast.stmt]:
    """Statements do escopo em ordem de linha, sem entrar em definicao aninhada.

    Pilha explicita e nao recursao: `if` dentro de `for` dentro de `try` aninha,
    e a profundidade e do arquivo analisado, nao deste modulo. Uma biblioteca
    nao pode estourar a pilha do interpretador por causa da forma do codigo de
    quem a chamou.

    A ordenacao por `(linha, coluna)` no fim e o que torna a leitura linear: a
    pilha desempilha ao contrario, e sem a ordenacao a ligacao de um nome seria
    aplicada DEPOIS do uso dela.
    """
    saida: list[ast.stmt] = []
    pilha: list[ast.stmt] = list(corpo)
    while pilha:
        stmt = pilha.pop()
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        saida.append(stmt)
        for campo in ("body", "orelse", "finalbody"):
            pilha.extend(getattr(stmt, campo, None) or [])
        for tratador in getattr(stmt, "handlers", None) or []:
            pilha.extend(tratador.body)
    saida.sort(key=lambda s: (getattr(s, "lineno", 0), getattr(s, "col_offset", 0)))
    return saida


def _linha(no: ast.AST) -> int:
    return getattr(no, "lineno", 0)


def _id_de_dataset(nome: str, origem: str, caminho: str, linha: int) -> str:
    """Id de dataset. Resolvido ignora arquivo; nao resolvido nao pode ignorar.

    `gold.vendas` e a MESMA tabela vista de qualquer arquivo, e por isso o id
    dela nao carrega caminho -- e o que permite a `mesclar` juntar a escrita de
    um arquivo com a leitura de outro. Ja dois `<dynamic>` em arquivos
    diferentes nao sao a mesma tabela desconhecida: uni-los criaria um caminho
    de linhagem entre dois jobs que ninguem mediu, que e pior que nao ter
    caminho nenhum.
    """
    if nome == DINAMICO:
        return node_id(caminho, _KIND_DATASET, f"{origem}:{DINAMICO}", str(linha))
    return node_id("", _KIND_DATASET, f"{origem}:{nome}", "")


def _indice_de_nos(grafo: GrafoDeDados) -> dict[str, NoDeDados]:
    return {no.identificador: no for no in grafo.nos}


def _adjacencia(
    grafo: GrafoDeDados, direcao: str
) -> dict[str, list[tuple[ArestaDeDados, str]]]:
    """`no -> [(aresta, vizinho)]` no sentido pedido.

    Montado por chamada e nao guardado no grafo porque o grafo e frozen e uma
    travessia so lê: um indice guardado teria de ser invalidado por `mesclar`, e
    indice desatualizado devolve vizinho que nao existe mais sem levantar nada.
    """
    saida: dict[str, list[tuple[ArestaDeDados, str]]] = {}
    for aresta in grafo.arestas:
        if direcao == MONTANTE:
            saida.setdefault(aresta.destino, []).append((aresta, aresta.origem))
        else:
            saida.setdefault(aresta.origem, []).append((aresta, aresta.destino))
    return saida


def _travessia_completa(
    grafo: GrafoDeDados, identificador: str, direcao: str, profundidade: int
) -> tuple[PassoDeLinhagem, ...]:
    if direcao not in (MONTANTE, JUSANTE):
        raise ValueError(f"direcao invalida: {direcao!r}")
    indice = _indice_de_nos(grafo)
    if identificador not in indice:
        return ()
    vizinhos = _adjacencia(grafo, direcao)

    visitados = {identificador}
    passos: list[PassoDeLinhagem] = []
    fila: deque[tuple[str, int, ArestaDeDados | None]] = deque([(identificador, 0, None)])
    while fila:
        atual, nivel, aresta = fila.popleft()
        no = indice[atual]
        if aresta is not None:
            passos.append(
                PassoDeLinhagem(
                    nome=no.nome,
                    identificador=no.identificador,
                    profundidade=nivel,
                    caminho=aresta.caminho,
                    linha=aresta.linha,
                    operacao=aresta.operacao,
                    confianca=aresta.confianca,
                    resolvido=no.resolvido,
                )
            )
        if nivel >= profundidade:
            continue
        for proxima, vizinho in vizinhos.get(atual, ()):
            if vizinho in visitados or vizinho not in indice:
                continue
            visitados.add(vizinho)
            fila.append((vizinho, nivel + 1, proxima))

    passos.sort(key=lambda p: (p.profundidade, p.nome, p.caminho, p.linha))
    return tuple(passos)


def _chave_de_no(no: NoDeDados) -> tuple:
    return (no.kind, no.caminho, no.linha, no.nome, no.identificador)


def _chave_de_aresta(aresta: ArestaDeDados) -> tuple:
    return (aresta.caminho, aresta.linha, aresta.operacao, aresta.origem, aresta.destino)


def _chave_de_nao_resolvido(item: DadoNaoResolvido) -> tuple:
    return (item.caminho, item.linha, item.reason, item.operacao, item.template)


__all__ = [
    "DINAMICO",
    "DYNAMIC_TABLE_IDENTIFIER",
    "JUSANTE",
    "MONTANTE",
    "NESTED_TOO_DEEP",
    "SQL_NOT_PARSED",
    "UNKNOWN_RECEIVER",
    "ArestaDeDados",
    "DadoNaoResolvido",
    "GrafoDeDados",
    "NoDeDados",
    "PassoDeLinhagem",
    "construir",
    "jusante",
    "linhagem_de_tabela",
    "mesclar",
    "montante",
]
