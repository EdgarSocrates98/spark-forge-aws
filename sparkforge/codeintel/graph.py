"""Travessia do grafo de chamadas: quem chama, quem e chamado, e o raio de impacto.

O QUE ESTE MODULO RESPONDE QUE `grep` NAO RESPONDE
--------------------------------------------------
`grep processar` devolve toda linha em que o texto aparece -- definicao,
chamada, comentario e docstring, sem distinguir. A pergunta que decide um
refactor e outra: QUEM chama isto, e o que quebra se eu mudar. Essa e estrutural,
e so sai de aresta resolvida -- `edges`, escrita por `indexar` a partir de
`resolve.resolver`.

O CONJUNTO DE VISITADOS NAO E OTIMIZACAO
----------------------------------------
Recursao mutua existe em codigo real, e `a -> b -> a` e um ciclo. Sem visitados
a travessia REEMITE `a` na profundidade 2, `b` na 3, e assim por diante ate o
teto de profundidade -- e num componente fortemente conectado de k nos o numero
de caminhos cresce com a profundidade, nao o numero de nos. O teto faz a
travessia terminar; o conjunto de visitados e o que a faz devolver CADA no uma
vez so, e na MENOR profundidade em que ele foi alcancado.

A menor profundidade e a resposta certa e nao um detalhe: ela e a distancia do
no ate a mudanca, e e por ela que quem le decide o que revisar primeiro. Um no
alcancavel em 1 salto e em 4 e um vizinho direto, nao um parente distante.

A ORDEM PRECISA DE DESEMPATE EXPLICITO, E DE UM LUGAR SO
--------------------------------------------------------
Vale aqui a mesma medicao de `search.py`: sem `ORDER BY` explicito a ordem e a
que o SQLite achar mais barata, e um teste de determinismo falharia de forma
INTERMITENTE -- pior que falhar sempre, porque some quando alguem vai olhar.

A ordenacao acontece em PYTHON e nao no SQL, e isso e deliberado. A consulta de
cada nivel e emitida em LOTES (ver `_LOTE`), entao um `ORDER BY` no SQL
ordenaria cada lote e nao o nivel: a concatenacao de dois lotes ordenados nao e
ordenada. Com a ordem decidida num lugar so -- `_CHAVE_DE_ORDEM` -- o lote deixa
de ser capaz de quebra-la.

`impacto` INCLUI O PROPRIO NO, `chamadores` NAO
-----------------------------------------------
Nao e inconsistencia, sao perguntas diferentes. `chamadores(x)` responde "quem
chama x", e x nao chama x. `impacto(x)` responde "o que uma mudanca em x
alcanca", e ela alcanca x primeiro -- deixar x de fora do proprio raio de
impacto faria `profundidade=0` devolver lista vazia, que se le como "nada e
afetado" quando a leitura certa e "so o proprio no".
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from sparkforge.codeintel.db import abrir

# O unico `kind` que `resolve.resolver` produz hoje. Fica como parametro com
# default e nao como literal enterrado porque a tabela ja aceita outros tipos de
# aresta, e um dia havera `imports`.
_CALLS = "calls"

# Sentido da travessia. Nomeados em vez de booleano `subir=True` porque
# `chamadores(x, subir=False)` seria lido como "chamadores" e devolveria
# chamados -- o tipo nao pega, e o nome errado sai no relatorio.
_MONTANTE = "montante"  # quem CHAMA a ancora
_JUSANTE = "jusante"  # quem a ancora CHAMA

# `(coluna do vizinho, coluna da ancora)`. Subindo, a ancora e o alvo da aresta
# e o vizinho e a origem; descendo, o inverso.
_LADOS = {
    _MONTANTE: ("source_id", "target_id"),
    _JUSANTE: ("target_id", "source_id"),
}

# Default de `impacto`. Tres e escolha, nao medida: e o alcance em que a lista
# ainda cabe numa revisao humana nesta arvore -- quatro niveis a partir de um
# utilitario comum devolvem quase o modulo inteiro, e uma lista assim nao
# prioriza nada. Quem precisa de mais pede.
_PROFUNDIDADE_DE_IMPACTO = 3

# Teto do caminho mais curto. MAIOR que o de impacto, e a razao e que as duas
# perguntas tem formas diferentes: impacto devolve TUDO ate N saltos, e o custo
# cresce com a vizinhanca a cada nivel; caminho devolve UMA sequencia, e parar
# cedo demais transforma "existe caminho longo" em "nao existe caminho" -- que e
# a resposta errada mais cara que este modulo pode dar.
#
# 6 e escolha e nao medida, e por isso e parametro com default: numa arvore em
# que a maior distancia observada for maior, quem pergunta sobe o teto, e o
# campo `truncado` do resultado diz quando ele foi atingido.
_PROFUNDIDADE_DE_CAMINHO = 6

# Teto de iteracoes da propagacao de rotulo. Propagacao converge rapido em
# grafo esparso -- e grafo de chamadas e esparso --, e o teto existe para o
# caso em que dois rotulos oscilam entre si sem estabilizar. Atingi-lo sai
# como `convergiu: False` no resultado, nunca em silencio.
_ITERACOES_DE_COMUNIDADE = 20

_ALGORITMO_DE_COMUNIDADE = "propagacao-de-rotulo-ordem-fixa/1"

# Quantos nos `nos_por_grau` devolve por padrao. Vinte cabe numa revisao; a
# lista inteira seria o indice ordenado de outro jeito, que nao e resposta.
_LIMITE_DE_GRAU = 20

# Teto de marcadores `?` por consulta. `SQLITE_MAX_VARIABLE_NUMBER` vale 999 nas
# builds anteriores a 3.32 e 32766 depois, e o interpretador embarca a build que
# quiser -- inclusive a antiga, no Python que o cliente tiver. 400 fica abaixo do
# menor dos dois com folga para o marcador de `kind`, e o custo de dividir e uma
# consulta a mais por lote num indice que ja esta em memoria.
#
# O VALOR nao e afirmado por teste, e nao da para ser: baixa-lo e a mutacao que
# o teste `test_ordem_sobrevive_a_consulta_partida_em_lotes` USA como oraculo,
# entao baixa-lo globalmente deixa os dois lados da comparacao iguais e a suite
# verde. O que o teste prende e a propriedade que importa -- a ordem sobrevive a
# consulta partida --, e ela vale para qualquer valor. O numero em si e o teto
# do SQLite, e esta acima.
_LOTE = 400

_SQL_TODOS_OS_NOS = (
    "SELECT nodes.id, nodes.name, nodes.qualified_name, nodes.kind,"
    "       files.path, nodes.start_line"
    "  FROM nodes"
    "  JOIN files ON files.id = nodes.file_id"
)

_SQL_ARESTAS = (
    "SELECT DISTINCT edges.source_id, edges.target_id"
    "  FROM edges"
    " WHERE edges.kind = ?"
)

_SQL_NO = (
    "SELECT nodes.id, nodes.name, nodes.qualified_name, nodes.kind,"
    "       files.path, nodes.start_line"
    "  FROM nodes"
    "  JOIN files ON files.id = nodes.file_id"
    " WHERE nodes.id = ?"
)

# `DISTINCT` porque `f()` chamada tres vezes na mesma funcao sao TRES arestas --
# `edges` nao tem chave unica, de proposito (ver `db.py`) -- e tres arestas nao
# sao tres chamadores. Sem ele o mesmo no sairia repetido na lista.
_SQL_VIZINHOS = (
    "SELECT DISTINCT nodes.id, nodes.name, nodes.qualified_name, nodes.kind,"
    "                files.path, nodes.start_line"
    "  FROM edges"
    "  JOIN nodes ON nodes.id = edges.{vizinho}"
    "  JOIN files ON files.id = nodes.file_id"
    " WHERE edges.kind = ? AND edges.{ancora} IN ({marcadores})"
)


@dataclass(frozen=True)
class NoDoGrafo:
    """Um no alcancado pela travessia, e a que distancia da ancora ele estava.

    Carrega `path` e `start_line` pelo mesmo motivo que `search.Achado`: quem le
    tem que conseguir ir ao codigo sem que o indice guarde o codigo.

    `depth` e a MENOR profundidade em que este no foi alcancado -- ver a
    docstring do modulo. Ela e o que ordena a revisao, e por isso e campo e nao
    algo que quem chama recalcula.
    """

    node_id: str
    name: str
    qualified_name: str
    kind: str
    path: str
    start_line: int
    depth: int


def _chave_de_ordem(no: NoDoGrafo) -> tuple[int, str, int, str]:
    """A ordem total da saida, decidida num lugar so.

    `depth` primeiro porque e a ordem em que se revisa. `path`, `start_line` e
    `node_id` depois porque relevancia sozinha nao desempata: dois nos de mesma
    profundidade empatam sempre, e sem desempate a ordem passa a ser a que o
    SQLite achar mais barata.

    `node_id` fecha a chave, e ele e CINTO e nao desempate ativo -- medido, para
    nao ficar dito por simetria: nos 6028 nos deste repositorio ha ZERO par com
    o mesmo `(path, start_line)`, e `extract.py` nao tem hoje como produzir um
    (`lineno` de funcao decorada ja exclui o decorador). Uma mutacao que tira
    `node_id` da chave SOBREVIVE a suite inteira, e nao ha fixture que a mate
    sem inventar um no que o extrator nao emite.

    Fica na chave mesmo assim porque o custo e uma tupla um item maior e a
    alternativa e ordem nao-total no dia em que o extrator emitir dois nos na
    mesma linha -- e esse dia chegaria como teste intermitente, nao como erro.
    """
    return (no.depth, no.path, no.start_line, no.node_id)


def chamadores(
    banco: str | os.PathLike[str],
    node_id: str,
    kind: str = _CALLS,
) -> list[NoDoGrafo]:
    """Quem chama `node_id` DIRETAMENTE, em ordem estavel.

    Um salto so, e sem o proprio no. Para o alcance transitivo use `impacto`,
    que e a mesma travessia com teto de profundidade e conjunto de visitados --
    e nao esta funcao com um parametro a mais, porque "chamadores em
    profundidade 3" e uma frase que nao quer dizer nada: o que ela devolve e o
    raio de impacto, e ele ja tem nome.

    Devolve lista vazia quando `node_id` nao existe no indice, e nao levanta:
    um id que nao esta no banco e a resposta normal depois de reindexar uma
    arvore em que o simbolo foi renomeado.
    """
    return _um_salto(banco, node_id, kind, _MONTANTE)


def chamados(
    banco: str | os.PathLike[str],
    node_id: str,
    kind: str = _CALLS,
) -> list[NoDoGrafo]:
    """Quem `node_id` chama DIRETAMENTE, em ordem estavel.

    O espelho de `chamadores`, e com a mesma ressalva: o que sai daqui e o que
    a resolucao CONSEGUIU resolver. Chamada que virou `unresolved_refs` -- em
    `df.filtrar()` o tipo de `df` e desconhecido -- nao aparece, e por isso a
    lista vazia significa "nenhuma chamada resolvida", nao "nenhuma chamada".
    Quem precisa do ponto cego le `unresolved_refs`, que existe para isso.
    """
    return _um_salto(banco, node_id, kind, _JUSANTE)


def impacto(
    banco: str | os.PathLike[str],
    node_id: str,
    profundidade: int = _PROFUNDIDADE_DE_IMPACTO,
) -> list[NoDoGrafo]:
    """Tudo que uma mudanca em `node_id` alcanca ate `profundidade` saltos acima.

    Sobe pelos chamadores, transitivamente, e INCLUI o proprio no na
    profundidade 0 -- ver a docstring do modulo sobre por que.
    `profundidade=0` devolve so ele, e nao lista vazia.

    `profundidade` negativa devolve lista vazia e nao levanta, pelo mesmo motivo
    que `buscar` trata `limite <= 0`: o valor absurdo tem que fechar a porta, e
    nao abrir outra. Aqui ele nem chega ao banco.

    Cada no sai UMA vez, na MENOR profundidade em que foi alcancado, e o
    conjunto de visitados que garante isso e o mesmo que faz a travessia
    terminar num ciclo.

    Nao ha parametro `kind` aqui, diferente de `chamadores`: raio de impacto por
    tipo de aresta e uma pergunta que ninguem faz hoje, e um parametro sem
    chamador e sem teste seria superficie que envelhece sem que nada acuse.
    """
    if profundidade < 0:
        return []

    conexao = abrir(banco)
    try:
        ancora = _no(conexao, node_id, profundidade=0)
        if ancora is None:
            return []

        alcancados = [ancora]
        # Comeca com a ancora JA dentro: sem isso um ciclo `a -> b -> a`
        # reemitiria `a` na profundidade 2 -- ela sairia duas vezes na mesma
        # lista, com duas profundidades diferentes.
        visitados = {node_id}
        fronteira = [node_id]

        for salto in range(1, profundidade + 1):
            vizinhos = _vizinhos(conexao, fronteira, _CALLS, _MONTANTE, salto)
            fronteira = []
            for vizinho in vizinhos:
                if vizinho.node_id in visitados:
                    continue
                visitados.add(vizinho.node_id)
                alcancados.append(vizinho)
                fronteira.append(vizinho.node_id)
            if not fronteira:
                # Nada novo neste salto: nada novo em salto nenhum depois dele.
                # Sair aqui e o que impede uma profundidade alta de custar
                # consultas vazias em cima de um grafo ja esgotado.
                break
    finally:
        conexao.close()

    return sorted(alcancados, key=_chave_de_ordem)


@dataclass(frozen=True)
class Caminho:
    """Uma sequencia de chamadas de `origem` ate `destino`, ou a recusa nomeada.

    `nos` vem em ordem de percurso -- `nos[0]` e a origem, `nos[-1]` o destino
    -- e cada `depth` e a POSICAO no caminho, nao a distancia a uma ancora. Os
    dois numeros coincidem aqui, e reescrever `depth` na reconstrucao e o que
    garante que continuem coincidindo se a travessia mudar.

    `truncado` diz que a busca parou no teto SEM ter achado o destino. E a
    distincao que decide se `nos` vazio significa 'nao ha caminho' ou 'nao ha
    caminho ate aqui': sem ela, um teto baixo devolveria a mesma coisa que a
    ausencia real, e quem lesse concluiria o mais forte dos dois.
    """

    nos: tuple[NoDoGrafo, ...]
    truncado: bool
    profundidade_maxima: int

    @property
    def existe(self) -> bool:
        return bool(self.nos)

    @property
    def saltos(self) -> int:
        """Arestas percorridas. Caminho de um no so tem zero saltos."""
        return max(len(self.nos) - 1, 0)


def caminho(
    banco: str | os.PathLike[str],
    origem: str,
    destino: str,
    profundidade: int = _PROFUNDIDADE_DE_CAMINHO,
    kind: str = _CALLS,
) -> Caminho:
    """O caminho MAIS CURTO de `origem` a `destino`, descendo pelas chamadas.

    Responde a pergunta que `impacto` nao responde: nao 'o que isto alcanca',
    mas COMO isto chega ali -- a forma que importa quando o destino e um
    `collect` no driver ou um algoritmo de grafo sem checkpoint. O raio diz que
    ha ligacao; o caminho diz por onde ela passa, e e por onde ela passa que se
    decide onde intervir.

    ## Sentido

    Desce (`_JUSANTE`): `origem` chama ... chama `destino`. Para o sentido
    inverso, troque os argumentos. Nao ha parametro de direcao porque
    `caminho(a, b, subir=True)` e exatamente `caminho(b, a)` invertido, e duas
    formas de escrever a mesma coisa e uma a mais do que precisa existir.

    ## Por que BFS, e o que 'mais curto' significa

    Largura garante que o primeiro encontro com `destino` e por um caminho de
    numero MINIMO de arestas. Nao ha peso: uma chamada nao e mais cara que
    outra neste indice, e inventar peso -- por frequencia, por tamanho da
    funcao -- seria julgamento vestido de medida.

    **Pode haver mais de um caminho minimo, e este devolve UM.** A escolha e
    deterministica: a fronteira e percorrida em `_chave_de_ordem`, entao entre
    predecessores igualmente curtos vence o de menor `(path, start_line,
    node_id)`. Determinismo nao e unicidade, e dizer 'o caminho' quando ha tres
    seria afirmar mais do que se mediu.

    ## As tres respostas negativas, que nao sao a mesma

    - `origem` ou `destino` fora do indice -> vazio, `truncado` falso.
    - travessia foi ate o teto e o destino nao apareceu -> vazio, **`truncado`
      verdadeiro**.
    - o grafo esgotou ANTES do teto -> vazio, `truncado` falso, e ai a ausencia
      de caminho e afirmacao, nao recusa.

    Colapsa-las num `[]` faria 'nao procurei fundo o bastante' ser lido como
    'nao existe'.

    ## O ponto cego, que e o mesmo de `chamados`

    O que sai daqui percorre aresta RESOLVIDA. Chamada que virou
    `unresolved_refs` -- `df.filtrar()` com tipo de `df` desconhecido -- nao e
    aresta, entao caminho que so existiria por ela nao aparece. Vazio significa
    'nenhum caminho resolvido', nunca 'nenhum caminho'.
    """
    if profundidade < 0:
        return Caminho(nos=(), truncado=False, profundidade_maxima=profundidade)

    conexao = abrir(banco)
    try:
        inicio = _no(conexao, origem, profundidade=0)
        if inicio is None or _no(conexao, destino, profundidade=0) is None:
            return Caminho(nos=(), truncado=False, profundidade_maxima=profundidade)

        if origem == destino:
            # Um no so, zero saltos. Nao e caso degenerado a recusar: 'como x
            # chega em x' tem resposta, e ela e 'ja esta la'.
            return Caminho(
                nos=(inicio,), truncado=False, profundidade_maxima=profundidade
            )

        # `predecessor[b] = a` reconstroi o caminho de tras para frente. Guardar
        # o predecessor e nao a lista inteira por no e o que impede a memoria
        # crescer com o numero de CAMINHOS -- que num componente fortemente
        # conectado e exponencial -- em vez de com o numero de nos.
        predecessor: dict[str, str] = {}
        encontrado: dict[str, NoDoGrafo] = {origem: inicio}
        visitados = {origem}
        fronteira = [origem]
        esgotou = False

        for salto in range(1, profundidade + 1):
            vizinhos = sorted(
                _vizinhos(conexao, fronteira, kind, _JUSANTE, salto),
                key=_chave_de_ordem,
            )
            proxima: list[str] = []
            for vizinho in vizinhos:
                if vizinho.node_id in visitados:
                    continue
                visitados.add(vizinho.node_id)
                encontrado[vizinho.node_id] = vizinho
                predecessor[vizinho.node_id] = _predecessor_estavel(
                    conexao, fronteira, vizinho.node_id, kind
                )
                if vizinho.node_id == destino:
                    return Caminho(
                        nos=_reconstruir(encontrado, predecessor, origem, destino),
                        truncado=False,
                        profundidade_maxima=profundidade,
                    )
                proxima.append(vizinho.node_id)
            if not proxima:
                # Grafo esgotado ANTES do teto: a ausencia de caminho aqui e
                # afirmacao, e nao 'nao fui fundo o bastante'.
                esgotou = True
                break
            fronteira = proxima
    finally:
        conexao.close()

    return Caminho(nos=(), truncado=not esgotou, profundidade_maxima=profundidade)


def _predecessor_estavel(
    conexao: sqlite3.Connection,
    fronteira: list[str],
    alvo: str,
    kind: str,
) -> str:
    """Qual no da fronteira chama `alvo`, escolhido deterministicamente.

    `_vizinhos` consulta a fronteira inteira de uma vez e devolve os vizinhos
    sem dizer de qual ancora cada um veio -- e mudar aquela consulta para
    carregar a origem mudaria `NoDoGrafo` para todos os chamadores, por uma
    necessidade que so o caminho tem.

    Entao a origem e reconsultada aqui, uma vez por no NOVO. A `fronteira`
    chega na ordem da rodada anterior, e tomar o PRIMEIRO elegivel e o que faz
    a escolha entre predecessores empatados nao depender da ordem que o SQLite
    achar mais barata.
    """
    candidatos = {
        no.node_id for no in _vizinhos(conexao, [alvo], kind, _MONTANTE, 1)
    }
    elegiveis = [n for n in fronteira if n in candidatos]
    return elegiveis[0] if elegiveis else fronteira[0]


def _reconstruir(
    encontrado: dict[str, NoDoGrafo],
    predecessor: dict[str, str],
    origem: str,
    destino: str,
) -> tuple[NoDoGrafo, ...]:
    """Do destino para a origem, e depois ao contrario, com `depth` reescrito."""
    trilha = [destino]
    while trilha[-1] != origem:
        anterior = predecessor.get(trilha[-1])
        if anterior is None:  # pragma: no cover - defesa: BFS sempre encadeia
            break
        trilha.append(anterior)
    trilha.reverse()
    return tuple(
        NoDoGrafo(
            node_id=encontrado[n].node_id,
            name=encontrado[n].name,
            qualified_name=encontrado[n].qualified_name,
            kind=encontrado[n].kind,
            path=encontrado[n].path,
            start_line=encontrado[n].start_line,
            depth=posicao,
        )
        for posicao, n in enumerate(trilha)
        if n in encontrado
    )


@dataclass(frozen=True)
class Estatisticas:
    """O tamanho do grafo, e o quanto dele NAO e grafo.

    `arestas_resolvidas` e `referencias_nao_resolvidas` saem juntas de
    proposito. Publicar so a primeira faria um indice com 8899 arestas parecer
    completo quando ha 10784 chamadas que a resolucao nao ligou -- e e a taxa,
    nao a contagem de arestas, que diz o quanto uma travessia daqui cobre.
    """

    arquivos: int
    nos: int
    arestas_resolvidas: int
    referencias_nao_resolvidas: int

    @property
    def taxa_de_resolucao(self) -> float:
        """Arestas sobre tentativas. `0.0` quando nao houve tentativa nenhuma.

        Zero tentativas devolve `0.0` e nao `1.0`: um indice vazio nao resolveu
        tudo, ele nao resolveu nada -- e `1.0` ali seria a forma mais silenciosa
        possivel de afirmar cobertura total sobre um banco sem conteudo.
        """
        tentativas = self.arestas_resolvidas + self.referencias_nao_resolvidas
        return self.arestas_resolvidas / tentativas if tentativas else 0.0


def estatisticas(banco: str | os.PathLike[str]) -> Estatisticas:
    """Quatro contagens do indice, e nada derivado alem da taxa.

    Nao tem `god_nodes` nem comunidades, e a ausencia e decisao: grau alto num
    grafo de CHAMADAS nao e causa de gargalo Spark, e publicar 'estes sao os
    nos-deus' ao lado de metricas de execucao convidaria exatamente essa
    leitura. Se um dia entrarem, entram com a razao pela qual grau responde
    alguma pergunta que alguem de fato faz.
    """
    conexao = abrir(banco)
    try:
        return Estatisticas(
            arquivos=_conta(conexao, "files"),
            nos=_conta(conexao, "nodes"),
            arestas_resolvidas=_conta(conexao, "edges"),
            referencias_nao_resolvidas=_conta(conexao, "unresolved_refs"),
        )
    finally:
        conexao.close()


# As quatro contagens, como SQL literal e nao como nome de tabela interpolado.
#
# SQLite nao aceita placeholder em nome de tabela, entao a alternativa seria uma
# f-string -- e o linter reprova (`S608`), com razao. Reprova mesmo aqui, onde os
# quatro nomes sao literais deste arquivo: a defesa que depende de o proximo
# leitor notar que a variavel e confiavel nao e defesa, e no dia em que alguem
# aceitar `tabela` de fora, a supressao que teria sido escrita hoje ja estaria la
# calando o aviso.
#
# Com o conjunto FECHADO em constante, a pergunta some em vez de ser silenciada.
_CONTAGENS = {
    "files": "SELECT COUNT(*) FROM files",
    "nodes": "SELECT COUNT(*) FROM nodes",
    "edges": "SELECT COUNT(*) FROM edges",
    "unresolved_refs": "SELECT COUNT(*) FROM unresolved_refs",
}


def _conta(conexao: sqlite3.Connection, tabela: str) -> int:
    """Conta linhas de `tabela`, e devolve 0 se ela nao existir.

    Tabela ausente e banco de schema mais velho, nao defeito: `estatisticas`
    descreve o indice que HA, e levantar aqui transformaria uma leitura em erro
    por causa de uma tabela que a pergunta nem precisava.

    Nome fora de `_CONTAGENS` tambem devolve 0, e por outra razao: e erro de
    programacao deste modulo, e ele aparece como contagem zero num campo que o
    teste de forma ja confere -- nao como excecao no meio de uma leitura.
    """
    sql = _CONTAGENS.get(tabela)
    if sql is None:
        return 0
    try:
        return int(conexao.execute(sql).fetchone()[0])
    except sqlite3.Error:
        return 0


@dataclass(frozen=True)
class Comunidade:
    """Um grupo de nos que se chamam mais entre si do que com o resto.

    `nos` vem ordenado por `_chave_de_ordem`, e `rotulo` e o `node_id` do
    menor membro -- identidade derivada do conteudo, e nao um contador, para
    que duas execucoes sobre o mesmo indice deem o mesmo rotulo.
    """

    rotulo: str
    nos: tuple[NoDoGrafo, ...]

    @property
    def tamanho(self) -> int:
        return len(self.nos)


@dataclass(frozen=True)
class Particao:
    """O resultado de `comunidades()`, com o metodo DECLARADO ao lado.

    `algoritmo`, `iteracoes` e `convergiu` saem no resultado e nao em log
    porque a particao NAO E UNICA: propagacao de rotulo nao tem resposta
    canonica, e duas ordens de visita dao duas particoes igualmente validas.
    O que este modulo garante e REPRODUTIBILIDADE -- a ordem e fixa --, nao
    unicidade, e publicar a particao sem o metodo convidaria a segunda
    leitura.

    `convergiu: False` significa que o teto de iteracoes foi atingido com
    rotulos ainda mudando. O resultado continua utilizavel e continua
    reproduzivel; o que ele nao e, nesse caso, e estavel sob mais iteracoes.
    """

    comunidades: tuple[Comunidade, ...]
    algoritmo: str
    iteracoes: int
    convergiu: bool

    @property
    def total(self) -> int:
        return len(self.comunidades)


def comunidades(
    banco: str | os.PathLike[str],
    iteracoes_maximas: int = _ITERACOES_DE_COMUNIDADE,
    kind: str = _CALLS,
) -> Particao:
    """Agrupa os nos por propagacao de rotulo, de forma DETERMINISTICA.

    ## Por que este algoritmo, e nao uma dependencia

    O wheel minimo tem DUAS dependencias -- `PyYAML` e `jsonschema` --, e
    detectar comunidade com `networkx` acrescentaria uma terceira para uma
    capacidade que nao julga nada. Propagacao de rotulo cabe em quarenta
    linhas, nao tem dependencia, e e a preferencia que a fase declarou:
    algoritmo local e deterministico antes de biblioteca.

    ## O que 'deterministico' significa aqui, exatamente

    Propagacao de rotulo canonica visita os nos em ordem ALEATORIA, e por
    isso devolve particoes diferentes a cada execucao. Aqui:

    - os nos sao visitados em `_chave_de_ordem`, que e ordem total;
    - o empate entre rotulos igualmente frequentes vence o MENOR rotulo;
    - o rotulo inicial de cada no e o proprio `node_id`.

    Com os tres, duas execucoes sobre o mesmo indice dao a MESMA particao.

    **Reprodutibilidade nao e unicidade.** Nao ha particao canonica de um
    grafo: outra ordem de visita daria outro agrupamento igualmente valido, e
    por isso `Particao.algoritmo` sai no resultado. Quem publicar 'as
    comunidades deste codigo' sem o metodo ao lado esta afirmando mais do que
    foi medido.

    ## O que uma comunidade NAO e

    Nao e modulo, nao e camada, e nao e sugestao de refatoracao. E um grupo
    de simbolos que se chamam mais entre si do que com o resto, medido sobre
    as arestas que a resolucao CONSEGUIU resolver -- e com taxa de resolucao
    de 36% neste repositorio, o que ficou de fora e maior que o que entrou.
    Ler `estatisticas().taxa_de_resolucao` antes de concluir qualquer coisa.
    """
    conexao = abrir(banco)
    try:
        nos = _todos_os_nos(conexao)
        vizinhanca = _vizinhanca_nao_dirigida(conexao, kind)
    finally:
        conexao.close()

    if not nos:
        return Particao(
            comunidades=(),
            algoritmo=_ALGORITMO_DE_COMUNIDADE,
            iteracoes=0,
            # Grafo vazio CONVERGIU: nao ha rotulo que possa mudar. `False`
            # aqui se leria como 'o teto foi atingido', que e outra coisa.
            convergiu=True,
        )

    ordem = [no.node_id for no in sorted(nos.values(), key=_chave_de_ordem)]
    rotulo = {node_id: node_id for node_id in ordem}

    iteracoes = 0
    convergiu = False
    for _ in range(max(0, iteracoes_maximas)):
        iteracoes += 1
        mudou = False
        for node_id in ordem:
            vizinhos = vizinhanca.get(node_id)
            if not vizinhos:
                continue
            escolhido = _rotulo_mais_frequente(
                [rotulo[v] for v in vizinhos if v in rotulo]
            )
            if escolhido is not None and escolhido != rotulo[node_id]:
                rotulo[node_id] = escolhido
                mudou = True
        if not mudou:
            convergiu = True
            break

    grupos: dict[str, list[NoDoGrafo]] = {}
    for node_id, marca in rotulo.items():
        grupos.setdefault(marca, []).append(nos[node_id])

    saida = []
    for membros in grupos.values():
        ordenados = tuple(sorted(membros, key=_chave_de_ordem))
        # O rotulo final e o MENOR `node_id` do grupo, e nao a marca que a
        # propagacao deixou: a marca depende de por onde a propagacao passou,
        # e o menor membro depende so do conteudo do grupo.
        saida.append(
            Comunidade(
                rotulo=min(no.node_id for no in ordenados),
                nos=ordenados,
            )
        )
    saida.sort(key=lambda c: (-c.tamanho, c.rotulo))

    return Particao(
        comunidades=tuple(saida),
        algoritmo=_ALGORITMO_DE_COMUNIDADE,
        iteracoes=iteracoes,
        convergiu=convergiu,
    )


def _rotulo_mais_frequente(rotulos: list[str]) -> str | None:
    """O rotulo mais comum entre os vizinhos; empate vence o MENOR.

    O desempate por menor rotulo e o que torna a propagacao reproduzivel:
    sem ele, dois rotulos igualmente frequentes fariam a escolha depender da
    ordem de insercao no dicionario, que muda com a ordem de leitura do
    banco.
    """
    if not rotulos:
        return None
    contagem: dict[str, int] = {}
    for marca in rotulos:
        contagem[marca] = contagem.get(marca, 0) + 1
    melhor = max(contagem.values())
    return min(marca for marca, n in contagem.items() if n == melhor)


@dataclass(frozen=True)
class NoComGrau:
    """Um no e quantas arestas resolvidas o tocam.

    O nome NAO e `god_node`, e a escolha e deliberada: 'no-deus' e veredito, e
    grau e medida. Um simbolo de grau alto pode ser um utilitario bem
    fatorado, e chama-lo de defeito por causa do grau seria julgamento sem
    fonte -- o mesmo que o veto V-BR-3 recusa para fan-in.
    """

    no: NoDoGrafo
    grau_de_entrada: int
    grau_de_saida: int

    @property
    def grau(self) -> int:
        return self.grau_de_entrada + self.grau_de_saida


def nos_por_grau(
    banco: str | os.PathLike[str],
    limite: int = _LIMITE_DE_GRAU,
    kind: str = _CALLS,
) -> list[NoComGrau]:
    """Os `limite` nos de maior grau, do maior para o menor.

    ## O que este numero NAO responde

    Grau alto num grafo de CHAMADAS nao e causa de gargalo Spark, e nao e
    defeito. Um `_normalizar` chamado de trinta lugares tem grau trinta
    porque foi bem fatorado. Publicar 'estes sao os nos-deus' ao lado de
    metricas de execucao convidaria a leitura de que eles CAUSAM algo.

    O que ele responde e estreito e util: mudar um destes nos toca muita
    coisa, e a revisao de uma mudanca neles custa mais. Para 'o que quebra se
    eu mudar isto', a resposta com nome e `impacto`.

    ## O ponto cego

    Grau conta aresta RESOLVIDA. Uma funcao chamada so por despacho dinamico
    tem grau de entrada zero aqui e nao e folha nenhuma na execucao. Ver
    `estatisticas().taxa_de_resolucao` antes de ler a lista.
    """
    if limite <= 0:
        return []

    conexao = abrir(banco)
    try:
        nos = _todos_os_nos(conexao)
        entrada: dict[str, int] = {}
        saida: dict[str, int] = {}
        for origem, destino in _arestas(conexao, kind):
            saida[origem] = saida.get(origem, 0) + 1
            entrada[destino] = entrada.get(destino, 0) + 1
    finally:
        conexao.close()

    medidos = [
        NoComGrau(
            no=no,
            grau_de_entrada=entrada.get(node_id, 0),
            grau_de_saida=saida.get(node_id, 0),
        )
        for node_id, no in nos.items()
    ]
    # Grau decrescente, e `_chave_de_ordem` desempata -- sem o segundo
    # criterio, dois nos de mesmo grau sairiam na ordem que o SQLite achar
    # mais barata, e um golden sobre esta lista falharia de forma
    # intermitente.
    medidos.sort(key=lambda m: (-m.grau, _chave_de_ordem(m.no)))
    return medidos[:limite]


def _todos_os_nos(conexao: sqlite3.Connection) -> dict[str, NoDoGrafo]:
    """Todos os nos do indice, por id. `depth` sai 0: nao ha ancora aqui."""
    linhas = conexao.execute(_SQL_TODOS_OS_NOS).fetchall()
    return {linha[0]: _do_linha(linha, 0) for linha in linhas}


def _arestas(conexao: sqlite3.Connection, kind: str) -> list[tuple[str, str]]:
    """Os pares `(origem, destino)` distintos.

    `DISTINCT` pela mesma razao de `_SQL_VIZINHOS`: `f()` chamada tres vezes
    na mesma funcao sao TRES arestas, e tres arestas nao sao grau tres.
    """
    return [
        (str(a), str(b))
        for a, b in conexao.execute(_SQL_ARESTAS, (kind,)).fetchall()
    ]


def _vizinhanca_nao_dirigida(
    conexao: sqlite3.Connection, kind: str
) -> dict[str, set[str]]:
    """Adjacencia SEM direcao, que e a forma que a propagacao de rotulo pede.

    Comunidade nao tem sentido: `a` chamar `b` os poe no mesmo grupo tanto
    quanto `b` chamar `a`. Manter a direcao faria a propagacao so descer, e
    todo no sem chamador viraria comunidade de um.
    """
    adjacencia: dict[str, set[str]] = {}
    for origem, destino in _arestas(conexao, kind):
        if origem == destino:
            # Recursao direta e aresta legitima e NAO informa comunidade: um
            # no e sempre do proprio grupo, e conta-la daria peso extra ao
            # rotulo que o no ja tem.
            continue
        adjacencia.setdefault(origem, set()).add(destino)
        adjacencia.setdefault(destino, set()).add(origem)
    return adjacencia


def _um_salto(
    banco: str | os.PathLike[str],
    node_id: str,
    kind: str,
    direcao: str,
) -> list[NoDoGrafo]:
    """Os vizinhos imediatos de `node_id` no sentido `direcao`.

    NAO confere se a ancora existe, e a ausencia da conferencia foi MEDIDA: id
    inventado e id sem vizinho dao a mesma lista vazia com ou sem ela, porque a
    unica saida possivel aqui e uma lista. A conferencia estava escrita, custava
    uma consulta por chamada, e nenhuma mutacao a matava -- codigo que so pode
    ser removido sem efeito nao e defesa, e um comentario dizendo que ele
    distingue os dois casos seria mentira. Quem precisa da distincao pergunta ao
    indice, que e o que `search.resumo` existe para responder.

    `impacto` continua olhando a ancora, e por outro motivo: la ela SAI na
    resposta, entao "nao existe" e "existe e nao tem chamador" sao duas listas
    diferentes -- vazia e de um elemento.

    O proprio no sai da lista quando ele chama a si mesmo: recursao direta e
    aresta legitima de `x` para `x`, e ela pertence a resposta de "quem chama
    x". Aqui nao ha travessia para nao terminar -- e um salto so.
    """
    conexao = abrir(banco)
    try:
        vizinhos = _vizinhos(conexao, [node_id], kind, direcao, 1)
    finally:
        conexao.close()
    return sorted(vizinhos, key=_chave_de_ordem)


def _no(conexao: sqlite3.Connection, node_id: str, profundidade: int) -> NoDoGrafo | None:
    linha = conexao.execute(_SQL_NO, (node_id,)).fetchone()
    if linha is None:
        return None
    return _do_linha(linha, profundidade)


def _vizinhos(
    conexao: sqlite3.Connection,
    ancoras: list[str],
    kind: str,
    direcao: str,
    profundidade: int,
) -> list[NoDoGrafo]:
    """Os vizinhos de TODAS as `ancoras` de uma vez, em lotes de `_LOTE`.

    Um nivel inteiro por consulta -- e nao uma consulta por ancora -- porque o
    numero de ancoras cresce com a profundidade, e uma consulta por no faria o
    custo da travessia ser o numero de nos alcancados em vez do numero de
    niveis.

    Pode devolver o mesmo no mais de uma vez quando ele e vizinho de duas
    ancoras diferentes: `DISTINCT` vale por consulta, e o lote parte a consulta.
    Quem chama deduplica -- em `impacto` e o conjunto de visitados, e em
    `_um_salto` ha uma ancora so e portanto um lote so.
    """
    vizinho, ancora = _LADOS[direcao]
    encontrados: list[NoDoGrafo] = []
    for inicio in range(0, len(ancoras), _LOTE):
        lote = ancoras[inicio : inicio + _LOTE]
        consulta = _SQL_VIZINHOS.format(
            vizinho=vizinho,
            ancora=ancora,
            marcadores=",".join("?" * len(lote)),
        )
        # S608 (`SQL injection`) nao se aplica: `vizinho` e `ancora` saem de
        # `_LADOS`, que e constante de modulo, e `marcadores` e uma contagem de
        # `?`. Nenhum valor vindo de fora e interpolado -- todos entram como
        # parametro ligado, inclusive `kind`.
        linhas = conexao.execute(consulta, (kind, *lote)).fetchall()  # noqa: S608
        encontrados.extend(_do_linha(linha, profundidade) for linha in linhas)
    return encontrados


def _do_linha(linha: tuple, profundidade: int) -> NoDoGrafo:
    return NoDoGrafo(
        node_id=linha[0],
        name=linha[1],
        qualified_name=linha[2],
        kind=linha[3],
        path=linha[4],
        start_line=linha[5],
        depth=profundidade,
    )


__all__ = [
    "Caminho",
    "Comunidade",
    "Estatisticas",
    "NoComGrau",
    "NoDoGrafo",
    "Particao",
    "caminho",
    "chamadores",
    "chamados",
    "comunidades",
    "estatisticas",
    "impacto",
    "nos_por_grau",
]
