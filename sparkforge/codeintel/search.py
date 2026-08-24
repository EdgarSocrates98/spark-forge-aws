"""Consulta ao indice: buscar por nome, e dizer o que o banco tem.

O TERMO NUNCA CHEGA CRU AO MATCH
--------------------------------
FTS5 nao recebe texto, recebe EXPRESSAO. Aspas, `*`, `(`, `:`, `^`, `-`, `+`,
`OR`, `AND`, `NOT` e `NEAR` sao sintaxe, e um termo vindo de fora que seja
interpolado direto no `MATCH` cai num de dois lados, os dois ruins. Medido sobre
um indice construido por `indexar`, com as formas do plano -- e a mesma medicao
que `tests/test_codeintel_search.py::test_operador_de_fts_nao_e_executado`
refaz a cada execucao, para que esta tabela nao possa envelhecer calada:

    "            OperationalError: unterminated string
    x"y          OperationalError: unterminated string
    (            OperationalError: fts5: syntax error near ""
    *            OperationalError: unknown special query:
    '            OperationalError: fts5: syntax error near "'"
    a OR b       nao levanta -- executa uniao, que o chamador nao pediu
    a AND b      nao levanta -- executa intersecao
    NEAR(a b)    nao levanta -- executa proximidade
    a*           nao levanta -- executa prefixo
    ^x           nao levanta -- exige o token na primeira posicao da coluna
    name:a       nao levanta -- restringe a coluna

As cinco de baixo sao as piores: erro aparece, resultado errado nao. A secao 30
da SPEC exige construtor de consulta por isso, e `construir_consulta` e ele.

A CITACAO SO E SUFICIENTE POR CAUSA DO ALFABETO
-----------------------------------------------
`\\w+` nao casa NENHUM caractere que o FTS5 leia como operador: aspas, `*`,
`(`, `)`, `:`, `^`, `-`, `+`, `{` e `}` ficam todos de fora. E por isso que
envolver cada token em aspas basta -- nao ha o que escapar dentro dele. O
`replace('"', '""')` que sobrou e cinto contra a alteracao do alfabeto por
alguem que nao leia este paragrafo, e `test_construtor_so_emite_token_entre_aspas`
e o que prende o alfabeto onde ele esta.

`\\w` e nao `[A-Za-z0-9_]` porque identificador nao-ASCII e legal em Python e
cliente tem. MEDIDO com o alfabeto trocado, sobre um simbolo com cedilha e til:
o construtor parte o nome nos dois pedacos ASCII em volta do acento, exige os
dois como tokens que nenhum simbolo tem, e a busca devolve lista VAZIA -- sem
erro, sem aviso. E a forma de falha que este modulo inteiro existe para nao ter.
Ver `test_acento_no_termo_sobrevive`, que refaz a medicao.

A ORDEM PRECISA DE DESEMPATE EXPLICITO
--------------------------------------
Relevancia do FTS sozinha nao ordena: `rank` empata sempre que o termo casa do
mesmo jeito em linhas do mesmo tamanho, que e o caso comum de simbolo com o
mesmo nome em arquivos diferentes. Sem `ORDER BY rank, path, start_line,
node_id` a ordem passa a ser a que o SQLite achar mais barata, e um teste de
determinismo falharia de forma INTERMITENTE -- pior que falhar sempre, porque
some quando alguem vai olhar.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sparkforge.codeintel.db import abrir

# Ver a docstring do modulo: e o alfabeto que torna a citacao suficiente.
_TOKEN = re.compile(r"\w+", re.UNICODE)

_LIMITE_PADRAO = 50

_SQL_BUSCA = (
    "SELECT symbols_fts.node_id, nodes.name, nodes.qualified_name, nodes.kind,"
    "       files.path, nodes.start_line"
    "  FROM symbols_fts"
    "  JOIN nodes ON nodes.id = symbols_fts.node_id"
    "  JOIN files ON files.id = nodes.file_id"
    " WHERE symbols_fts MATCH ?"
    " ORDER BY rank, files.path, nodes.start_line, symbols_fts.node_id"
    " LIMIT ?"
)


@dataclass(frozen=True)
class Achado:
    """Uma linha de resultado de busca.

    Ela carrega o suficiente para o chamador ir ao codigo -- `path` mais
    `start_line` -- sem que o indice precise guardar o codigo.
    """

    node_id: str
    name: str
    qualified_name: str
    kind: str
    path: str
    start_line: int


def construir_consulta(termo: str) -> str | None:
    """A expressao de MATCH que corresponde a `termo` lido como TEXTO.

    Devolve `None` quando o termo nao tem token nenhum -- e `None` nao e
    detalhe: `MATCH ''` levanta, e um construtor que devolvesse string vazia
    empurraria o erro para dentro da consulta. Quem chama trata a ausencia de
    token como "nao ha o que buscar", nao como "busque tudo".
    """
    tokens = _TOKEN.findall(termo)
    if not tokens:
        return None
    return " ".join('"' + token.replace('"', '""') + '"' for token in tokens)


def buscar(
    banco: str | os.PathLike[str],
    termo: str,
    limite: int = _LIMITE_PADRAO,
) -> list[Achado]:
    """Simbolos cujo nome ou nome qualificado casa `termo`, em ordem estavel.

    O termo passa por `construir_consulta` SEMPRE. Termo sem token devolve lista
    vazia sem tocar no banco -- e nao o indice inteiro, que e o que uma consulta
    sem filtro devolveria e o que um chamador distraido pediria por acidente.
    `limite <= 0` devolve vazio pela mesma razao, e nao por simetria: `LIMIT -1`
    no SQLite significa SEM limite, entao a porta que o termo vazio fecha estaria
    aberta pelo outro argumento.

    Os tokens sao exigidos TODOS (o espaco entre eles e `AND` implicito no
    FTS5), o que torna `buscar` mais especifico conforme o chamador digita. Nao
    ha busca por prefixo: `sour` nao acha `source`, porque o `*` que faria isso
    e o mesmo operador que o construtor existe para neutralizar, e ligar prefixo
    aqui exigiria uma decisao propria -- ela nao foi tomada, e fica dita em vez
    de acontecer por acidente.
    """
    consulta = construir_consulta(termo)
    if consulta is None:
        return []
    if limite <= 0:
        # `LIMIT -1` no SQLite significa SEM limite, nao "nenhuma linha". Pedir
        # zero ou menos e a mesma porta pela qual o termo vazio devolveria o
        # indice inteiro, so que aberta pelo outro argumento.
        return []
    conexao = abrir(banco)
    try:
        linhas = conexao.execute(_SQL_BUSCA, (consulta, limite)).fetchall()
    finally:
        conexao.close()
    return [
        Achado(
            node_id=linha[0],
            name=linha[1],
            qualified_name=linha[2],
            kind=linha[3],
            path=linha[4],
            start_line=linha[5],
        )
        for linha in linhas
    ]


def resumo(banco: str | os.PathLike[str]) -> dict[str, Any]:
    """O que o indice tem e quando ele foi feito.

    Devolve `root_fingerprint`, nunca a raiz: o metadata guarda impressao
    exatamente para nao nomear o usuario nem o diretorio num arquivo que pode
    ser copiado (ver `db.impressao_da_raiz`), e um resumo que reconstituisse o
    caminho desfaria isso na saida da CLI.

    Contagem por `COUNT(*)` e nao por `Resultado` guardado: o banco e a fonte,
    e um numero gravado na indexacao envelheceria em silencio no dia em que
    alguem apagasse linha por fora.
    """
    conexao = abrir(banco)
    try:
        metadata = dict(conexao.execute("SELECT key, value FROM metadata").fetchall())
        (arquivos,) = conexao.execute("SELECT COUNT(*) FROM files").fetchone()
        (nos,) = conexao.execute("SELECT COUNT(*) FROM nodes").fetchone()
    finally:
        conexao.close()
    return {
        "schema_version": int(metadata.get("schema_version", 0)),
        "engine_version": metadata.get("engine_version", ""),
        "created_at": metadata.get("created_at", ""),
        "root_fingerprint": metadata.get("root_fingerprint", ""),
        "files": arquivos,
        "nodes": nos,
    }


def existe(banco: str | os.PathLike[str]) -> bool:
    """Se `banco` e um indice ja construido, e nao um arquivo por nascer.

    `sqlite3.connect` CRIA o arquivo quando ele nao existe, entao perguntar ao
    banco custaria um banco vazio no disco so por ter perguntado. A checagem
    acontece antes de abrir, por isso.
    """
    return Path(banco).is_file()


__all__ = ["Achado", "buscar", "construir_consulta", "existe", "resumo"]
