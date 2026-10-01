"""Schema e abertura do indice local.

ORDEM DOS PRAGMAS -- por que `abrir` faz o que faz
--------------------------------------------------
Tres dos cinco pragmas da abertura nao aplicam se chegarem depois da primeira
escrita, e DOIS deles falham sem excecao nenhuma. Medido nas versoes do CI,
relendo o valor efetivo depois de aplicar dentro de uma transacao ja aberta:

    journal_mode=WAL     devolveu ('delete',)  efetivo 'delete'  calado
    foreign_keys=ON      devolveu []           efetivo 0         calado
    synchronous=NORMAL   levantou              efetivo 2 (FULL)  ruidoso
    temp_store=MEMORY    devolveu []           efetivo 2         PEGOU
    busy_timeout=30000   devolveu (30000,)     efetivo 30000     PEGOU

Os dois ultimos sao imunes porque sao propriedade da CONEXAO, nao do arquivo de
banco. Os tres primeiros nao, e o dano do pior deles foi medido:

    pragma cedo   foreign_keys=1   nos orfaos apos DELETE = 0
    pragma tarde  foreign_keys=0   nos orfaos apos DELETE = 1

Sem `foreign_keys` efetivo o `ON DELETE CASCADE` e declarado e nao acontece, e
o indice acumula no orfao a cada reindexacao, em silencio. Indice que junta
lixo calado e pior que indice que falha.

`abrir` usa as DUAS saidas medidas em `tests/test_codeintel_db.py`, e nao uma:

1. `isolation_level=None` -- sem gerenciamento implicito de transacao nao ha
   transacao aberta para bloquear pragma nenhum, em ordem nenhuma. Isto protege
   contra a proxima pessoa que acrescentar um pragma depois do schema.
2. Pragmas antes de qualquer escrita -- vale por si so, e nao depende de o item
   1 continuar valendo se alguem trocar o modo de transacao um dia.

E RELE o valor efetivo de `foreign_keys` LOGO DEPOIS de aplica-lo, porque a
regra deste modulo e que pragma que nao levanta ainda pode nao ter pegado, e a
unica prova e reler. So esse e motivo de recusa: os outros dois custam
desempenho ou durabilidade, que num cache reconstruivel se paga; `foreign_keys`
custa integridade, e nao ha sistema de arquivos em que ele legitimamente falhe
-- ele e estado de conexao.

O "logo depois" nao e estilo, e foi medido. `synchronous=NORMAL` levanta dentro
de QUALQUER transacao, inclusive quando o valor pedido ja era o corrente, e ele
vem depois de `foreign_keys` na lista. Uma conferencia colocada no fim do laco
seria inalcancavel: o traceback de `synchronous` chegaria primeiro em todo
cenario em que `foreign_keys` falha calado, e a guarda nunca dispararia. Pior
ainda, a corretude passaria a depender de `synchronous` continuar na lista --
acidente, e nao desenho.

A forma da falha de `journal_mode` tambem depende de COMO a transacao abriu, e
isso tambem foi medido:

    transacao implicita, banco fora de WAL   devolveu ('delete',)  calado
    transacao explicita, banco fora de WAL   levantou "cannot change into wal"
    qualquer transacao, banco JA em WAL      devolveu ('wal',)     sem mudar nada

Ou seja, "nao levantou" nao classifica nem esse. So a releitura classifica.

`synchronous=NORMAL` e aceitavel exatamente pelo mesmo motivo: o banco e
DESCARTAVEL. Perder a ultima transacao num crash custa uma reindexacao, nao um
dado -- nada no motor deterministico depende deste arquivo para responder.

`edges` E `unresolved_refs` SAO O MESMO CONTRATO EM DUAS METADES
---------------------------------------------------------------
Ate J3 nao havia `edges` aqui, e a ausencia era deliberada: aresta exige
resolucao de referencia, que e onde mora a decisao dificil -- o que fazer com o
que nao resolve. J4 traz a resolucao, entao a tabela entra, e entra ao lado de
`unresolved_refs` porque uma sem a outra mente. `edges` guarda o que resolveu e
`unresolved_refs` guarda o que nao resolveu; so a soma das duas diz qual e a
cobertura, e contar ponto cego e diferente de nao ter ponto cego.

E `data_flow` REPETE O PAR, PARA OUTRA PERGUNTA
-----------------------------------------------
`edges` responde "quem chama quem". Nenhuma linha dela responde "de que tabela
veio esta tabela": as pontas do fluxo de dado sao dataset e DataFrame, e nenhum
dos dois tem simbolo em `nodes`. Por isso `data_flow` e tabela propria, e por
isso ela entra acompanhada de `data_flow_blind_spots` -- `spark.table(f"{db}.{t}")`
e uma leitura que EXISTE e nao tem nome, e um schema que so guardasse o que
resolveu faria um job inteiro de nomes dinamicos passar por job sem leitura.
A doutrina e a mesma do par acima: contar ponto cego e diferente de nao ter.

O PRECO DAS DUAS ESTA MEDIDO em `index.indexar`, e nao e pequeno.

SUBIR `SCHEMA_VERSION` NAO BASTA -- ALGUEM TEM QUE AGIR SOBRE ELE
-----------------------------------------------------------------
`CREATE TABLE IF NOT EXISTS` acrescenta tabela nova e NAO conserta tabela
antiga. Um banco escrito pela versao 1 sobreviveria a esta com `edges` criada e
`unresolved_refs` ainda nas colunas velhas, e o primeiro INSERT levantaria
`no such column` no meio de uma indexacao -- em producao, nao em teste. Por isso
`criar_schema` compara a versao gravada e joga o banco fora quando ela nao bate.
Jogar fora e aceitavel aqui pelo mesmo motivo que `synchronous=NORMAL` e:
o arquivo e DESCARTAVEL, e refazer custa uma reindexacao, nao um dado.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sparkforge import __version__

# 3 desde o fluxo de dados: `data_flow` e `data_flow_blind_spots` entraram. Banco
# de versao anterior nao e migravel para esta -- ver
# `_descartar_schema_de_versao_anterior`. Subir aqui e o que faz um indice antigo
# ser REFEITO em vez de responder linhagem vazia sobre um schema que nao a tinha:
# sem o bump, `CREATE TABLE IF NOT EXISTS` criaria as duas tabelas vazias e o
# pacote diria "zero fluxo medido" sobre uma arvore que nunca foi lida para isso.
SCHEMA_VERSION = 3

# Onde o indice mora quando ninguem escolhe. Declarado AQUI, no modulo que abre o
# arquivo, e nao em quem consulta: com o caminho repetido em `indexar` e em
# `buscar` bastaria um deles mudar para a CLI indexar num lugar e ler noutro,
# calada. `.sparkforge/local/` esta no `.gitignore` desde 715a657, e e por isso
# que o default aponta para la -- indice de repositorio de cliente que vira
# candidato a commit e vazamento, nao desordem. Relativo de proposito: quem
# chama e que sabe a raiz.
BANCO_PADRAO = Path(".sparkforge") / "local" / "codeintel" / "graph.sqlite3"

# A mesma lista que `tests/test_codeintel_db.py` afirma, e na mesma ordem.
PRAGMAS_DE_ABERTURA = (
    "journal_mode=WAL",
    "foreign_keys=ON",
    "synchronous=NORMAL",
    "temp_store=MEMORY",
    "busy_timeout=30000",
)

# O unico da lista cuja falha corrompe em vez de custar desempenho, e por isso o
# unico conferido. Nomeado para que a conferencia acompanhe a posicao dele se
# alguem reordenar a lista -- ver a docstring do modulo sobre por que a posicao
# decide se a guarda e alcancavel.
_PRAGMA_CRITICO = "foreign_keys=ON"

_TAMANHO_IMPRESSAO = 16

_TABELAS = (
    # Chave/valor porque o conjunto de metadados cresce com as fases, e coluna
    # nova exigiria migracao de tabela num banco que se joga fora e refaz.
    """
    CREATE TABLE IF NOT EXISTS metadata (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    # `path` e relativo a raiz, sempre. Caminho absoluto aqui vazaria o nome da
    # maquina num artefato que pode ser copiado.
    """
    CREATE TABLE IF NOT EXISTS files (
        id             TEXT PRIMARY KEY,
        path           TEXT NOT NULL UNIQUE,
        language       TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        size_bytes     INTEGER NOT NULL,
        modified_ns    INTEGER NOT NULL,
        indexed_at     INTEGER NOT NULL
    )
    """,
    # Sem corpo de funcao de proposito: o indice guarda ONDE, e quem quiser o
    # codigo le o arquivo. `normalized_signature` ja chega por
    # `normalizar_assinatura`, entao nenhum valor literal de default persiste.
    """
    CREATE TABLE IF NOT EXISTS nodes (
        id                   TEXT PRIMARY KEY,
        file_id              TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        kind                 TEXT NOT NULL,
        name                 TEXT NOT NULL,
        qualified_name       TEXT NOT NULL,
        start_line           INTEGER NOT NULL,
        end_line             INTEGER NOT NULL,
        normalized_signature TEXT NOT NULL DEFAULT ''
    )
    """,
    # CASCADE nas DUAS pontas, e nao so no alvo. Reindexar um arquivo apaga os
    # nos dele; a aresta que CHEGAVA num no apagado tem que cair junto com a que
    # SAIA dele, senao uma travessia segue a aresta orfa e devolve no fantasma.
    #
    # Sem chave primaria de proposito: `f(g(), g())` sao duas chamadas com
    # source, target, kind e line iguais, e sao duas arestas. Chave unica ai
    # perderia uma delas calada, e a contagem de chamadas passaria a mentir.
    #
    # `confidence` existe porque nem toda aresta e certeza: `df.filtrar()`
    # resolve por nome de metodo quando o tipo de `df` e desconhecido, e uma
    # travessia tem que poder cortar por quanto confia. Default 1.0 para que a
    # aresta que ninguem classificou nao passe por duvidosa.
    """
    CREATE TABLE IF NOT EXISTS edges (
        source_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        target_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        kind       TEXT NOT NULL,
        line       INTEGER NOT NULL,
        confidence REAL NOT NULL DEFAULT 1.0
    )
    """,
    # A outra metade de `edges`: referencia que nao resolve e o ponto cego do
    # indice, e ponto cego contado e diferente de ponto cego silencioso.
    # `reason` guarda POR QUE nao resolveu, que e o que permite decidir se vale
    # resolver depois.
    #
    # `source_id` e nulavel, e `edges.source_id` nao e: chamada no topo do
    # modulo tem origem no MODULO, e modulo nao e no -- `extract.py` extrai
    # classe, funcao e metodo, nao arquivo. Uma aresta so existe entre dois nos;
    # uma referencia sem no de origem existe, e e aqui que ela cabe.
    """
    CREATE TABLE IF NOT EXISTS unresolved_refs (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id      TEXT REFERENCES nodes(id) ON DELETE CASCADE,
        reference_name TEXT NOT NULL,
        reference_kind TEXT NOT NULL,
        file_id        TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        line           INTEGER NOT NULL,
        reason         TEXT NOT NULL
    )
    """,
    # O fluxo de dado, que `edges` nao sabe guardar: `edges` liga CHAMADA a
    # chamada, e nenhuma linha dela diz que `gold.vendas` descende de
    # `bronze.vendas`. As pontas aqui nao sao `nodes` -- sao dataset e DataFrame,
    # que nao tem simbolo no indice --, e por isso a tabela e propria e nao uma
    # `kind` nova em `edges`: uma chave estrangeira para `nodes(id)` nao teria
    # para onde apontar, e afrouxa-la para aceitar id de fora derrubaria a
    # garantia que faz `edges` nao ter no fantasma.
    #
    # As pontas saem DESNORMALIZADAS -- nome, kind e resolucao gravados na
    # propria linha em vez de uma tabela de nos ao lado. A travessia entre
    # arquivos (`montante`, `jusante`, `linhagem_de_tabela`) continua sendo do
    # grafo em memoria de `lineage.py`, que e onde ela ja esta escrita e testada;
    # o que se consulta daqui e "que fluxo existe NESTES arquivos", que e uma
    # varredura por `file_id` e nao uma travessia. Guardar nos so para reconstruir
    # em SQL uma travessia que ja existe em Python seria uma segunda
    # implementacao da mesma pergunta, e a divergencia entre as duas nao
    # levantaria nada.
    #
    # `source_resolved` e `target_resolved` sao coluna e nao `name = '<dynamic>'`
    # pelo mesmo motivo que em `lineage.NoDeDados`: um dia um nome pode ser
    # conhecido e a resolucao continuar duvidosa, e nesse dia os dois campos
    # precisam poder discordar.
    """
    CREATE TABLE IF NOT EXISTS data_flow (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id         TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        source_name     TEXT NOT NULL,
        source_kind     TEXT NOT NULL,
        source_resolved INTEGER NOT NULL,
        target_name     TEXT NOT NULL,
        target_kind     TEXT NOT NULL,
        target_resolved INTEGER NOT NULL,
        operation       TEXT NOT NULL,
        scope           TEXT NOT NULL,
        line            INTEGER NOT NULL,
        confidence      REAL NOT NULL DEFAULT 1.0
    )
    """,
    # A outra metade de `data_flow`, e ela entra JUNTO pela mesma razao que
    # `unresolved_refs` entrou junto com `edges`: uma sem a outra mente.
    # `spark.table(f"{db}.{tbl}")` e uma leitura que existe e nao tem nome, e
    # descartar a linha faria um job inteiro de nomes dinamicos passar por job
    # sem leitura. `template` guarda a forma com os buracos preservados e
    # `variables` os nomes lidos da expressao -- e o que permite a um humano ir
    # ver de onde o nome vem sem que o motor tenha adivinhado.
    #
    # `variables` e JSON numa coluna TEXT e nao tabela filha: a lista e lida
    # inteira ou nao e lida, ninguem consulta por variavel, e uma terceira
    # tabela custaria mais um CASCADE para atravessar a cada reindexacao.
    """
    CREATE TABLE IF NOT EXISTS data_flow_blind_spots (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id   TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        reason    TEXT NOT NULL,
        template  TEXT NOT NULL,
        variables TEXT NOT NULL,
        operation TEXT NOT NULL,
        line      INTEGER NOT NULL
    )
    """,
    # `node_id` fica UNINDEXED porque e chave de volta, nao termo de busca:
    # indexado, os 32 hex dele passariam a casar em MATCH. Sem tokenizador
    # custom porque e o default que quebra em nao-alfanumerico, e e isso que faz
    # `iter_source_files` ser achavel por `source` -- afirmado sobre esta tabela
    # em test_symbols_fts_acha_por_parte_de_nome_composto.
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
        node_id UNINDEXED,
        name,
        qualified_name
    )
    """,
)

_INDICES = (
    # Reindexar um arquivo apaga os nos dele por `file_id`; sem indice isso e
    # varredura da tabela inteira a cada arquivo alterado.
    "CREATE INDEX IF NOT EXISTS idx_nodes_file_id ON nodes(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_qualified_name ON nodes(qualified_name)",
    "CREATE INDEX IF NOT EXISTS idx_unresolved_file_id ON unresolved_refs(file_id)",
    # Este NAO e para consulta -- e para o CASCADE. Toda coluna que REFERENCIA
    # outra tabela e varrida a cada DELETE no pai, e sem indice essa varredura e
    # da tabela inteira, por linha apagada. MEDIDO neste repositorio, indexando
    # duas vezes seguidas (a segunda apaga 6028 nos e 10781 pontos cegos):
    #
    #     sem idx_unresolved_source_id   10.4 s
    #     com idx_unresolved_source_id    3.5 s
    #
    # 6028 nos x 10781 linhas varridas e o custo inteiro. `edges` ja escapava
    # disso pelos dois indices de travessia -- que existem por outro motivo e
    # cobrem este por acidente. `unresolved_refs.source_id` nao tinha nenhum, e
    # a fatura so aparece na SEGUNDA indexacao, que e a comum.
    #
    # NENHUM TESTE MATA ESSA MUTACAO, pelo mesmo motivo que o `BEGIN`/`COMMIT`
    # de `index.py`: apagar esta linha deixa a suite inteira verde, porque a
    # propriedade que ela quebra e desempenho e teste de tempo e instavel.
    # Medido: 15 mutacoes, 11 mortas, e esta e uma das 4 que sobreviveram. O
    # registro aqui e o que substitui o teste que nao existe.
    "CREATE INDEX IF NOT EXISTS idx_unresolved_source_id ON unresolved_refs(source_id)",
    # As tres colunas por onde a travessia entra, cada uma LIDERANDO um indice.
    # `callees` filtra por `source_id`, `chamadores` por `target_id`, e o corte
    # por tipo de aresta por `kind`. Coluna lider e o que decide se o planejador
    # usa o indice -- `kind` na segunda posicao de um composto nao atende
    # `WHERE kind = ?` sozinho, e por isso ele tem o proprio.
    #
    # `kind` acompanha as duas pontas no composto porque toda travessia que
    # segue aresta escolhe o tipo dela, e assim o indice cobre o filtro inteiro
    # sem voltar a tabela.
    "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id, kind)",
    "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id, kind)",
    "CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind)",
    # Os dois servem A MESMA coluna por dois motivos que valem sozinhos: a
    # consulta do `ContextPack` filtra fluxo por arquivo selecionado, e o
    # `DELETE FROM files` de toda reindexacao dispara o CASCADE por `file_id`.
    # A fatura do segundo motivo ja foi paga uma vez neste banco -- ver
    # `idx_unresolved_source_id` acima, onde a falta do indice custou 10.4 s
    # contra 3.5 s na SEGUNDA indexacao. Nao ha razao para descobrir de novo.
    "CREATE INDEX IF NOT EXISTS idx_data_flow_file_id ON data_flow(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_data_flow_blind_file_id"
    " ON data_flow_blind_spots(file_id)",
)

# Ordem de DROP: filho antes de pai. Com `foreign_keys` efetivo -- e `abrir`
# recusa a conexao em que ele nao pegou -- apagar `files` antes de `nodes`
# dispararia o CASCADE em vez do descarte limpo que se pretende aqui.
_TABELAS_PARA_DESCARTE = (
    "symbols_fts",
    # As duas do fluxo de dado referenciam `files`, entao entram ANTES dela --
    # e a mesma regra de filho antes de pai que vale para o resto da lista.
    # Esquece-las aqui e o ponto cego que a docstring de `lineage.py` prevê:
    # tabela que nao esta nesta lista sobrevive a um bump de `SCHEMA_VERSION`
    # carregando linhas do schema velho, e nada acusa.
    "data_flow_blind_spots",
    "data_flow",
    "unresolved_refs",
    "edges",
    "nodes",
    "files",
    "metadata",
)


def abrir(caminho: str | os.PathLike[str]) -> sqlite3.Connection:
    """Conexao com o indice, com os pragmas aplicados e o critico conferido.

    Ver a docstring do modulo para a medicao que justifica a ordem. Em resumo:
    `isolation_level=None` para que nao exista transacao implicita bloqueando
    pragma, pragmas antes de qualquer escrita para nao depender so disso, e
    releitura de `foreign_keys` porque ele falha calado e a falha dele corrompe.

    O PRECO disso, medido, e que quem escreve em lote precisa abrir a transacao
    na mao: sem gerenciamento implicito, cada INSERT vira uma transacao propria.
    3000 linhas em `files`, mesma maquina, WAL e synchronous=NORMAL:

        autocommit, como esta conexao vem      ~138 ms
        dentro de um BEGIN/COMMIT explicito      ~6 ms   (21x mais rapido)

    Entao `indexar` deve envolver a carga em `BEGIN`/`COMMIT`. Fica dito aqui e
    nao descoberto la, porque a escolha que cria o custo foi feita aqui.
    """
    conexao = sqlite3.connect(caminho, isolation_level=None)
    for pragma in PRAGMAS_DE_ABERTURA:
        conexao.execute(f"PRAGMA {pragma}")
        if pragma == _PRAGMA_CRITICO:
            _exigir_foreign_keys(conexao)
    return conexao


def _exigir_foreign_keys(conexao: sqlite3.Connection) -> None:
    """Recusa a conexao se o CASCADE fosse declarado sem acontecer."""
    (efetivo,) = conexao.execute("PRAGMA foreign_keys").fetchone()
    if efetivo == 1:
        return
    conexao.close()
    raise RuntimeError(
        f"PRAGMA foreign_keys nao pegou (valor efetivo {efetivo!r}): "
        "ON DELETE CASCADE seria declarado e nao aconteceria, e o indice "
        "acumularia no orfao a cada reindexacao, em silencio."
    )


def criar_schema(conexao: sqlite3.Connection, raiz: str | os.PathLike[str] | None = None) -> None:
    """Cria tabelas, indices e metadata. Idempotente.

    `raiz` so entra como IMPRESSAO -- ver `impressao_da_raiz`. O caminho em si
    nunca e gravado.

    Idempotente sobre banco da versao CORRENTE. Sobre banco de outra versao ela
    descarta primeiro -- ver `_descartar_schema_de_versao_anterior`, e a secao
    da docstring do modulo sobre por que subir `SCHEMA_VERSION` nao basta.
    """
    _descartar_schema_de_versao_anterior(conexao)

    for ddl in _TABELAS:
        conexao.execute(ddl)
    for ddl in _INDICES:
        conexao.execute(ddl)

    conexao.executemany(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        (
            ("schema_version", str(SCHEMA_VERSION)),
            ("engine_version", __version__),
            ("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("root_fingerprint", impressao_da_raiz(raiz)),
        ),
    )


def _descartar_schema_de_versao_anterior(conexao: sqlite3.Connection) -> None:
    """Joga o banco fora quando a versao gravada nele nao e a corrente.

    Nao ha migracao aqui, e a ausencia dela e escolha: o arquivo e DESCARTAVEL
    -- nada no motor deterministico depende dele para responder --, entao
    refazer custa uma reindexacao e escrever ALTER TABLE por versao custaria
    para sempre. A versao 1 para a 2 ja nao seria um ALTER: `unresolved_refs`
    trocou tres nomes de coluna.

    Banco NOVO nao tem `metadata`, e essa e a diferenca que decide entre "outra
    versao" e "ainda nao existe". Sem essa distincao a funcao levantaria
    `no such table` na primeira indexacao de todas.

    Banco da versao corrente sai daqui INTACTO, e isso tambem e afirmado em
    teste: `indexar` chama `criar_schema` a cada execucao, e um DROP
    incondicional refaria o indice do zero toda vez sem que nada ficasse
    vermelho.
    """
    existe = conexao.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
    ).fetchone()
    if existe is None:
        return
    gravada = conexao.execute(
        "SELECT value FROM metadata WHERE key = 'schema_version'"
    ).fetchone()
    if gravada is not None and gravada[0] == str(SCHEMA_VERSION):
        return
    for tabela in _TABELAS_PARA_DESCARTE:
        conexao.execute(f"DROP TABLE IF EXISTS {tabela}")


def impressao_da_raiz(raiz: str | os.PathLike[str] | None) -> str:
    """Digest da raiz indexada, para saber QUAL raiz sem guardar o caminho dela.

    O caminho absoluto responderia a mesma pergunta e traria dois defeitos: ele
    nomeia o usuario e o diretorio num artefato que pode ser copiado, e e
    legivel por quem receber o arquivo. O digest identifica sem nomear.

    Mover a arvore invalida a impressao, e isso e correto e nao efeito colateral:
    todo `files.path` la dentro e relativo aquela raiz. O banco e descartavel --
    impressao que nao bate custa uma reindexacao.

    Sem raiz declarada devolve string vazia, e nao o digest do vazio, para que
    "nao foi declarada" e "foi declarada e por acaso deu isto" nao se confundam.
    """
    if raiz is None:
        return ""
    absoluto = str(Path(raiz).resolve())
    return hashlib.blake2b(
        absoluto.encode("utf-8"), digest_size=_TAMANHO_IMPRESSAO
    ).hexdigest()


__all__ = [
    "BANCO_PADRAO",
    "PRAGMAS_DE_ABERTURA",
    "SCHEMA_VERSION",
    "abrir",
    "criar_schema",
    "impressao_da_raiz",
]
