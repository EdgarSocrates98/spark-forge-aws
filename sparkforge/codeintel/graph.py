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


__all__ = ["NoDoGrafo", "chamadores", "chamados", "impacto"]
