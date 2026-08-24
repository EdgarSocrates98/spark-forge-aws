"""Indexacao ponta a ponta: varredura -> AST -> banco.

A FRONTEIRA DE LEITURA NAO E REIMPLEMENTADA AQUI
------------------------------------------------
Quem decide o que pode ser lido e `iter_source_files` da fase J0 -- com poda de
`.venv`, `node_modules`, `vendor`, recusa de `.aws/` e `.pem`, teto de tamanho e
confinamento contra junction. Varrer por conta propria daria um SEGUNDO lugar
que decide o que o motor le, e a auditabilidade dessa fronteira e o motivo de
ela existir num lugar so. A pendencia registrada la -- pular e silencioso --
segue valendo e nao e fechada aqui.

A TRANSACAO EXPLICITA NAO E OTIMIZACAO PREMATURA, E PRECO JA MEDIDO
-------------------------------------------------------------------
`db.abrir` usa `isolation_level=None` de proposito, para que nao exista
transacao implicita bloqueando pragma. O preco disso esta medido na docstring
de `abrir`: 3000 inserts custam ~138 ms em autocommit contra ~6 ms dentro de um
`BEGIN`/`COMMIT` explicito, 21x.

Medido AQUI, ponta a ponta sobre este repositorio, tres rodadas de cada:

    com BEGIN/COMMIT   1.376 / 1.346 / 1.341 s
    autocommit         2.570 / 2.643 / 2.600 s   (1.9x mais lento)

Nao 21x porque nesta escala a maior parte do tempo e `ast.parse`, e nao insert
-- o fator de `abrir` mede so a escrita. Dobrar o tempo total continua sendo
preco alto por nada.

NENHUM TESTE MATA ESSA MUTACAO, e esta dito de proposito: trocar `BEGIN` por
`SELECT 1` deixa a suite inteira verde, porque a propriedade que ela quebra e
desempenho, e teste de tempo e instavel. Sete das oito mutacoes da Task 5
morreram; esta sobreviveu, e o registro dela aqui e o que substitui o teste que
nao existe.

J3 REINDEXA TUDO, DE PROPOSITO
------------------------------
`indexar` limpa `files` e `symbols_fts` antes de carregar. Nao e desperdicio: e
o que garante que arquivo APAGADO do disco desapareca do indice. Reaproveitar o
que ja estava exigiria saber o que mudou, que e exatamente a fase J4 -- e
construi-la aqui de improviso deixaria no fantasma no banco enquanto isso.

`files` cai por `DELETE`, e `nodes` e `unresolved_refs` vao junto pelo
`ON DELETE CASCADE` -- que so acontece porque `abrir` confere `foreign_keys`.
`symbols_fts` NAO cai junto: FTS5 e tabela virtual e chave estrangeira nao a
alcanca. Ela e limpa na mao, e esquecer isso deixaria o indice respondendo busca
com no que nao existe mais.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from sparkforge.codeintel.db import abrir, criar_schema
from sparkforge.codeintel.extract import No, extrair_nos_ou_none
from sparkforge.codeintel.ids import node_id
from sparkforge.facts.scan import iter_source_files

_PADRAO = "*.py"
_LINGUAGEM = "python"
_TAMANHO_DIGEST = 16


@dataclass(frozen=True)
class Resultado:
    """O que uma indexacao produziu, e o que ela NAO conseguiu ler.

    `ilegiveis` e primeira classe de proposito: arquivo que nao parseia e ponto
    cego, e ponto cego contado e diferente de ponto cego silencioso -- que e a
    lacuna que `facts/scan.py` ja registra como pendencia.

    `arquivos` conta o que a varredura ENTREGOU, e `ilegiveis` e um subconjunto
    dele. Contar so o que deu certo faria a razao entre os dois perder sentido:
    "1 ilegivel" sem o total nao diz se a indexacao foi boa ou desastrosa.
    """

    arquivos: int
    nos: int
    ilegiveis: int
    duracao_s: float


def indexar(raiz: str | os.PathLike[str], banco: str | os.PathLike[str]) -> Resultado:
    """Indexa todo `*.py` sob `raiz` no banco `banco`, e devolve o que aconteceu.

    MEDIDO sobre este proprio repositorio, tres rodadas seguidas, resultado
    identico nas tres:

        378 arquivos, 5754 nos, 1 ilegivel
        1.352 s / 1.349 s / 1.335 s
        3 514 368 bytes de `.sqlite3` (3 432 KiB)

    O unico ilegivel e `fixtures/graph/fonte_que_nao_compila/input/
    carga_quebrada.py`, fixture deliberada -- nao ha ilegivel por acidente, e
    nenhuma incompatibilidade de `ast` entre versoes se manifestou.

    OS DOIS PRIMEIROS NUMEROS SE MOVEM COM A ARVORE, e ficam aqui datados em vez
    de reescritos a cada commit: a Task 6 acrescentou `search.py` e o teste dele,
    e a mesma medicao passou a dar 380 arquivos e 5799 nos. O que NAO se move e a
    ordem de grandeza -- e e ela que decide a fase incremental. A medicao viva,
    com prova que executa, esta em `docs/harness/CODEINTEL-GAP.md`.

    Onde os bytes moram, medido derrubando uma tabela por vez e comparando o
    VACUUM (3 411 968 bytes compactado):

        nodes         2 142 208 bytes   63%
        symbols_fts   1 110 016 bytes   33%
        o resto         159 744 bytes    5%

    Sao esses numeros que decidem se a fase incremental (J4) vale a pena, e
    eles dizem que ela NAO e urgente: reindexar tudo custa 1.4 s e 3.4 MiB.
    Incremental so se paga em arvore onde isso doa, e este repositorio nao e
    uma.

    Arquivo que nao parseia entra em `ilegiveis` e a varredura SEGUE. Um
    repositorio de cliente tem arquivo com sintaxe de outra versao, template com
    placeholder, arquivo pela metade; parar em qualquer um trocaria cobertura
    parcial por nenhuma.
    """
    inicio = time.perf_counter()
    base = Path(raiz).expanduser()

    arquivos = 0
    ilegiveis = 0
    total_de_nos = 0

    conexao = abrir(banco)
    try:
        criar_schema(conexao, base)
        conexao.execute("BEGIN")
        try:
            conexao.execute("DELETE FROM symbols_fts")
            conexao.execute("DELETE FROM files")
            for caminho in iter_source_files(base, _PADRAO):
                arquivos += 1
                lido = _ler(caminho)
                if lido is None:
                    ilegiveis += 1
                    continue
                dados, fonte, modificado_ns = lido
                relativo = caminho.relative_to(base).as_posix()
                nos = extrair_nos_ou_none(fonte, relativo)
                if nos is None:
                    ilegiveis += 1
                    continue
                _gravar(conexao, relativo, dados, modificado_ns, nos)
                total_de_nos += len(nos)
            conexao.execute("COMMIT")
        except BaseException:
            # O `ROLLBACK` nao pode mascarar a causa. Se o proprio `COMMIT`
            # falhar, nao ha mais transacao aberta e o `ROLLBACK` levanta por
            # cima -- e quem le o traceback veria "cannot rollback" no lugar do
            # erro que de fato aconteceu.
            try:
                conexao.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
    finally:
        conexao.close()

    return Resultado(
        arquivos=arquivos,
        nos=total_de_nos,
        ilegiveis=ilegiveis,
        duracao_s=time.perf_counter() - inicio,
    )


def _ler(caminho: Path) -> tuple[bytes, str, int] | None:
    """Bytes, texto e `mtime_ns` do arquivo, ou `None` se ele nao pode ser lido.

    Os bytes voltam junto com o texto porque o `content_sha256` tem que ser do
    CONTEUDO no disco, nao do texto decodificado: normalizacao de fim de linha
    faria dois arquivos diferentes terem o mesmo digest, e a fase incremental
    usa esse digest para decidir se o arquivo mudou.

    O `stat()` acontece AQUI, e nao na gravacao, porque tudo que toca o disco
    tem que falhar antes do `INSERT`. La dentro ele estaria no meio da transacao,
    e um arquivo apagado entre a varredura e o `stat` derrubaria a indexacao
    inteira por `ROLLBACK` -- uma corrida de um arquivo custando todos os outros.

    `UnicodeDecodeError` conta como ilegivel e nao como erro porque a varredura
    entrega `.py` por EXTENSAO, e extensao nao garante codificacao -- arquivo
    latin-1 antigo existe. `OSError` cobre o arquivo que sumiu ou ficou sem
    permissao entre a varredura e a leitura.
    """
    try:
        dados = caminho.read_bytes()
        return dados, dados.decode("utf-8"), caminho.stat().st_mtime_ns
    except (OSError, UnicodeDecodeError):
        return None


def _gravar(
    conexao: sqlite3.Connection,
    relativo: str,
    dados: bytes,
    modificado_ns: int,
    nos: list[No],
) -> None:
    """Uma linha em `files`, uma por no em `nodes`, e o espelho em `symbols_fts`."""
    file_id = id_de_arquivo(relativo)
    agora = time.time_ns()
    conexao.execute(
        "INSERT INTO files"
        " (id, path, language, content_sha256, size_bytes, modified_ns, indexed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            file_id,
            relativo,
            _LINGUAGEM,
            hashlib.sha256(dados).hexdigest(),
            len(dados),
            modificado_ns,
            agora,
        ),
    )

    linhas = [
        (
            # `qualified_name` e nao `name`: e ele que carrega a unicidade, e
            # `node_id` nao tem como conferir que recebeu o nome qualificado.
            node_id(no.path, no.kind, no.qualified_name, no.normalized_signature),
            file_id,
            no.kind,
            no.name,
            no.qualified_name,
            no.start_line,
            no.end_line,
            no.normalized_signature,
        )
        for no in nos
    ]
    # `OR REPLACE` e PONTO CEGO ASSUMIDO, e nao descuido. Dois simbolos com
    # caminho, kind, nome qualificado E assinatura iguais produzem o mesmo id --
    # o caso real e a mesma funcao definida nos dois ramos de um `if/else` de
    # compatibilidade. Com `INSERT` seco isso levantaria e derrubaria a
    # indexacao inteira por causa de um arquivo; com `OR REPLACE` sobra um no,
    # e o outro se perde calado. Escolhida a segunda porque cobertura parcial
    # vale mais que nenhuma, e registrada aqui porque perda calada e defeito.
    # Medido nesta arvore: 5754 simbolos, 5754 ids distintos -- zero ocorrencia.
    conexao.executemany(
        "INSERT OR REPLACE INTO nodes"
        " (id, file_id, kind, name, qualified_name, start_line, end_line,"
        "  normalized_signature)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        linhas,
    )
    conexao.executemany(
        "INSERT INTO symbols_fts (node_id, name, qualified_name) VALUES (?, ?, ?)",
        [(linha[0], linha[3], linha[4]) for linha in linhas],
    )


def id_de_arquivo(relativo: str) -> str:
    """Id estavel de um arquivo, derivado so do caminho relativo.

    So o caminho entra, e nao o conteudo: se o digest do conteudo entrasse, o
    id mudaria a cada edicao e o `ON DELETE CASCADE` nunca alcancaria os nos da
    versao anterior -- eles ficariam orfaos apontando para um `file_id` que
    ninguem mais escreve.

    Prefixo `file_` para que um id de arquivo nunca seja confundido com um id de
    no numa consulta escrita a mao.
    """
    digest = hashlib.blake2b(relativo.encode("utf-8"), digest_size=_TAMANHO_DIGEST)
    return f"file_{digest.hexdigest()}"


__all__ = ["Resultado", "id_de_arquivo", "indexar"]
