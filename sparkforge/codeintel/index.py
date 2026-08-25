"""Indexacao ponta a ponta: varredura -> AST -> banco.

A FRONTEIRA DE LEITURA NAO E REIMPLEMENTADA AQUI
------------------------------------------------
Quem decide o que pode ser lido e `iter_source_files` da fase J0 -- com poda de
`.venv`, `node_modules`, `vendor`, recusa de `.aws/` e `.pem`, teto de tamanho e
confinamento contra junction. Varrer por conta propria daria um SEGUNDO lugar
que decide o que o motor le, e a auditabilidade dessa fronteira e o motivo de
ela existir num lugar so. A pendencia registrada la -- pular e silencioso --
JA FOI FECHADA no modulo de varredura: `varrer_source_files` devolve os pulos
com a razao nomeada. Este indexador ainda chama `iter_source_files` e portanto
nao consome esse sinal -- o ponto cego que resta e daqui, nao mais de la, e
fecha-lo e decidir onde o indice guardaria "arquivo que existe e nao foi lido".

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
`edges` cai em SEGUIDA e nao junto: ela referencia `nodes`, nao `files`, entao
so desaparece depois que o CASCADE de `files` levou os nos. E uma cadeia de dois
saltos, e ela depende do mesmo `foreign_keys` efetivo -- se ele falhasse,
sobrariam no orfao E aresta orfa.
`symbols_fts` NAO cai junto: FTS5 e tabela virtual e chave estrangeira nao a
alcanca. Ela e limpa na mao, e esquecer isso deixaria o indice respondendo busca
com no que nao existe mais.

A RESOLUCAO ACONTECE DEPOIS DO ULTIMO ARQUIVO, E NAO A CADA UM
--------------------------------------------------------------
`resolve.resolver` pergunta ao catalogo se um nome tem candidato UNICO, e a
resposta so e verdadeira quando todos os nos ja estao no banco. Resolvendo
arquivo a arquivo, `processar()` chamada no primeiro arquivo viraria
`NO_CANDIDATE` porque a definicao dela ainda nao teria sido lida, e a mesma
chamada no ultimo viraria aresta -- a taxa de resolucao passaria a depender da
ORDEM da varredura, calada. Por isso as referencias sao acumuladas em memoria e
a resolucao roda uma vez, dentro da mesma transacao.

O PRECO DISSO E UMA SEGUNDA PASSAGEM DE `ast.parse`, E ELE FOI MEDIDO
---------------------------------------------------------------------
`extrair_nos_ou_none` e `extrair_referencias` recebem FONTE, e cada uma parseia.
Medido sobre este repositorio, na MESMA maquina e na mesma sessao -- as duas
versoes lado a lado, banco novo a cada rodada, tres rodadas de cada:

    so nos (a versao anterior)    1.889 / 2.058 / 1.974 s
    nos + referencias + arestas   3.651 / 3.632 / 3.515 s   (1.8x)

Lado a lado de proposito: comparar com o 1.35 s que esta na docstring de
`indexar` mediria a maquina, nao a mudanca.

Nao e desperdicio invisivel: esta dito aqui porque o conserto -- parsear uma vez
e passar a arvore para as duas -- muda a assinatura de dois modulos que J4 nao
abriu, e fazer isso de improviso trocaria uma medicao por um refactor sem teste.
Fica registrado como preco conhecido, nao como surpresa.

A SEGUNDA INDEXACAO CUSTAVA 3x A PRIMEIRA, E O MOTIVO NAO ERA O `ast`
----------------------------------------------------------------------
Medido logo depois de ligar as arestas, indexando a mesma arvore quatro vezes
seguidas no mesmo banco:

    1a (banco vazio)   3.417 s
    2a                 9.345 s
    3a                10.444 s
    4a                10.662 s

A causa nao esta neste modulo: `unresolved_refs.source_id` referenciava
`nodes(id)` sem indice, e o `DELETE FROM files` do inicio faz o CASCADE varrer a
tabela inteira UMA VEZ POR NO apagado -- 6028 x 10781. Com
`idx_unresolved_source_id` (ver `db.py`) a segunda indexacao passou a custar
3.815 / 3.993 / 3.844 s, igual a primeira. Fica registrado aqui porque foi esta
mudanca que criou a fatura, e porque a forma dela -- lenta so a partir da
SEGUNDA vez -- e a que nao aparece em teste de tmpdir, onde o banco e sempre
novo.
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
from sparkforge.codeintel.refs import Referencia, extrair_referencias
from sparkforge.codeintel.resolve import Resolucao, catalogo_do_banco, resolver
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
    # As duas metades do contrato de J4, juntas de proposito. `arestas` sozinha
    # nao diz se a resolucao foi boa: 100 arestas sobre 120 chamadas e outra
    # coisa que 100 sobre 3000, e so a segunda metade distingue as duas.
    arestas: int
    nao_resolvidas: int


def indexar(raiz: str | os.PathLike[str], banco: str | os.PathLike[str]) -> Resultado:
    """Indexa todo `*.py` sob `raiz` no banco `banco`, e devolve o que aconteceu.

    MEDIDO sobre este proprio repositorio, quatro rodadas seguidas no mesmo
    banco, resultado identico nas quatro:

        391 arquivos, 6029 nos, 1 ilegivel
        8899 arestas, 10784 referencias nao resolvidas
        3.506 / 3.687 / 3.682 / 3.462 s
        8 437 760 bytes de `.sqlite3` (8 240 KiB)

    Os pontos cegos, por motivo, na mesma medicao:

        UNKNOWN_RECEIVER   9902   `df.x()` com tipo de `df` desconhecido
        NO_CANDIDATE        626
        AMBIGUOUS           144
        NO_SOURCE_NODE      112   chamada no topo do modulo

    Sao 54.8% das chamadas que produziram aresta OU ponto cego. Contando como
    `Resolucao.taxa_de_resolucao` conta -- com os 4375 builtins no denominador,
    porque `len` resolvido pelo interpretador nao e ponto cego mas tambem nao e
    aresta -- a taxa e 37.0%. Os dois numeros ficam porque eles respondem
    perguntas diferentes, e publicar so o maior seria escolher o mais confortavel.

    O unico ilegivel e `fixtures/graph/fonte_que_nao_compila/input/
    carga_quebrada.py`, fixture deliberada -- nao ha ilegivel por acidente, e
    nenhuma incompatibilidade de `ast` entre versoes se manifestou.

    OS DOIS PRIMEIROS NUMEROS SE MOVEM COM A ARVORE, e ficam aqui datados em vez
    de reescritos a cada commit: a Task 6 acrescentou `search.py` e o teste dele,
    e a mesma medicao passou a dar 380 arquivos e 5799 nos. O que NAO se move e a
    ordem de grandeza -- e e ela que decide a fase incremental. A medicao viva,
    com prova que executa, esta em `docs/harness/CODEINTEL-GAP.md`.

    Onde os bytes moram, medido derrubando uma tabela por vez e comparando o
    VACUUM (7 708 672 bytes compactado). O `nodes` que era 63% do arquivo agora
    e 29%: as duas metades do contrato de J4 juntas custam mais que ele:

        nodes             2 240 512 bytes   29.1%
        unresolved_refs   2 228 224 bytes   28.9%
        edges             1 867 776 bytes   24.2%
        symbols_fts         802 816 bytes   10.4%
        files               114 688 bytes    1.5%

    `unresolved_refs` custar o mesmo que `nodes` e o preco de contar ponto cego
    em vez de descarta-lo, e ele esta pago de proposito: 10784 linhas que dizem
    o que o indice NAO sabe valem mais que 2 MiB economizados fingindo que ele
    sabe tudo.

    Sao esses numeros que decidem se a fase incremental vale a pena, e
    eles dizem que ela ficou MENOS folgada: reindexar tudo custava 1.4 s e
    3.4 MiB, e agora custa 3.5 s e 8.0 MiB. Ainda nao e urgente nesta arvore --
    3.5 s e o tempo de um `pytest` curto --, mas o fator entre as duas medicoes
    e o que decide quando ela passa a ser.

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
    referencias_por_arquivo: dict[str, list[Referencia]] = {}

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
                # So depois de `nos is None` ficar para tras: arquivo que nao
                # parseia nao tem referencia para extrair, e `extrair_referencias`
                # devolveria lista vazia sem dizer por que.
                referencias_por_arquivo[relativo] = extrair_referencias(fonte, relativo)
            resolucao = _gravar_arestas(conexao, referencias_por_arquivo)
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
        arestas=len(resolucao.arestas),
        nao_resolvidas=len(resolucao.nao_resolvidas),
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


def _gravar_arestas(
    conexao: sqlite3.Connection,
    referencias_por_arquivo: dict[str, list[Referencia]],
) -> Resolucao:
    """Resolve tudo de uma vez e grava as DUAS metades do contrato.

    As duas, e nao so `edges`. Gravar aresta e descartar o que nao resolveu
    deixaria o indice com uma cobertura desconhecida: uma travessia que devolve
    lista vazia seria indistinguivel de "ninguem chama isto" e de "a resolucao
    nao alcancou isto", e essa confusao e o defeito que `unresolved_refs` existe
    para nao ter.

    Nao ha `DELETE FROM edges` nem `DELETE FROM unresolved_refs` aqui, e a
    ausencia e deliberada: o `DELETE FROM files` do inicio da transacao ja
    levou os nos por CASCADE, e as arestas junto com eles no segundo salto da
    cadeia. Um DELETE a mais aqui esconderia a dependencia em `foreign_keys`
    efetivo -- se ele falhasse, o indice acumularia orfao e nada acusaria.
    `test_reindexar_nao_acumula_aresta_nem_ponto_cego` e o que prende isso.

    `file_id` e recalculado a partir de `NaoResolvida.caminho` em vez de
    carregado no dataclass: `resolve.py` nao conhece o esquema de id de arquivo,
    e faze-lo conhecer poria a mesma regra em dois modulos -- bastaria um deles
    mudar para `unresolved_refs` apontar para `files` que nao existe, e a chave
    estrangeira derrubaria a indexacao inteira.
    """
    catalogo = catalogo_do_banco(conexao)
    resolucao = resolver(referencias_por_arquivo, catalogo)

    conexao.executemany(
        "INSERT INTO edges (source_id, target_id, kind, line, confidence)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (
                aresta.source_id,
                aresta.target_id,
                aresta.kind,
                aresta.line,
                aresta.confidence,
            )
            for aresta in resolucao.arestas
        ],
    )
    conexao.executemany(
        "INSERT INTO unresolved_refs"
        " (source_id, reference_name, reference_kind, file_id, line, reason)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                nao.source_id,
                nao.reference_name,
                nao.reference_kind,
                id_de_arquivo(nao.caminho),
                nao.line,
                nao.reason,
            )
            for nao in resolucao.nao_resolvidas
        ],
    )
    return resolucao


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
