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

POR QUE NAO HA TABELA `edges` AQUI
----------------------------------
Aresta exige resolucao de referencia, que e onde mora a decisao dificil: o que
fazer com o que nao resolve. Misturar isso com a criacao do banco tornaria as
duas indepuraveis. `unresolved_refs` ja existe porque toda referencia nao
resolvida cai nela, e contar ponto cego e diferente de nao ter ponto cego.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sparkforge import __version__

SCHEMA_VERSION = 1

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
    # Existe desde ja, antes de haver `edges`, porque referencia que nao resolve
    # e o ponto cego do indice -- e ponto cego contado e diferente de ponto cego
    # silencioso. `reason` guarda POR QUE nao resolveu, que e o que permite
    # decidir se vale resolver depois.
    """
    CREATE TABLE IF NOT EXISTS unresolved_refs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id      TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        from_node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
        raw_target   TEXT NOT NULL,
        kind         TEXT NOT NULL,
        line         INTEGER NOT NULL,
        reason       TEXT NOT NULL
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
    """
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
