"""O que o indice exige do interpretador, verificado onde o CI roda.

Este arquivo vem antes de qualquer schema de proposito. As medicoes que
justificam a fase foram feitas em Python 3.14.6, e o `pyproject.toml` declara
suporte a partir do 3.10 -- FTS5 e compilado opcional do SQLite, e um ambiente
sem ele faria o indice falhar na criacao, nao na consulta. Melhor descobrir num
teste nomeado do que num traceback de usuario.

REGRA DESTE MODULO: pragma que nao levanta ainda pode nao ter pegado, e a
unica prova e reler o valor efetivo. Tres dos cinco pragmas da abertura nao
aplicam se chegarem depois da primeira escrita, e DOIS deles falham sem
excecao nenhuma -- `journal_mode` devolvendo 'delete' e `foreign_keys`
ficando em 0. Ler "nao levantou" como "funcionou" e a armadilha que este
arquivo existe para desarmar. Todo teste daqui afirma valor efetivo, nunca
ausencia de excecao.
"""

import sqlite3

import pytest

# Ordem em que a abertura do indice pretende aplicar os pragmas. Fica no topo
# porque tres testes abaixo dependem de ser a MESMA lista -- se um deles usasse
# uma copia divergente, o teste de ordem aprovaria uma sequencia que o codigo
# nao usa, que e exatamente o defeito que eles existem para pegar.
PRAGMAS_DE_ABERTURA = [
    "journal_mode=WAL",
    "foreign_keys=ON",
    "synchronous=NORMAL",
    "temp_store=MEMORY",
    "busy_timeout=30000",
]


def test_fts5_esta_disponivel():
    conexao = sqlite3.connect(":memory:")
    try:
        conexao.execute("CREATE VIRTUAL TABLE t USING fts5(a, b)")
    except sqlite3.OperationalError as erro:  # pragma: no cover - so em build sem FTS5
        pytest.fail(
            "FTS5 ausente neste interpretador: o indice de codigo depende dele. "
            f"sqlite {sqlite3.sqlite_version}, erro: {erro}"
        )
    finally:
        conexao.close()


def test_fts5_casa_termo_dentro_de_nome_composto():
    """`iter_source_files` tem que ser achavel por `source`.

    O tokenizador default do FTS5 quebra em nao-alfanumerico, entao
    `iter_source_files` vira tres tokens. Se isso deixar de valer, a busca por
    parte de nome para de funcionar e nenhum outro teste acusa.
    """
    conexao = sqlite3.connect(":memory:")
    conexao.execute("CREATE VIRTUAL TABLE t USING fts5(node_id UNINDEXED, name)")
    conexao.execute("INSERT INTO t VALUES ('n1', 'iter_source_files')")
    achados = conexao.execute("SELECT node_id FROM t WHERE t MATCH 'source'").fetchall()
    conexao.close()
    assert achados == [("n1",)]


@pytest.mark.parametrize("pragma", PRAGMAS_DE_ABERTURA)
def test_pragma_e_aceito(pragma):
    """So prova que o interpretador CONHECE o pragma -- nada alem disso.

    Nao afirma que o pragma pegou, e em `:memory:` varios nem poderiam pegar.
    Quem quiser a garantia de efeito tem que olhar
    `test_pragmas_antes_da_primeira_escrita_pegam`, que rele valor efetivo.
    """
    conexao = sqlite3.connect(":memory:")
    try:
        conexao.execute(f"PRAGMA {pragma}")
    finally:
        conexao.close()


def test_wal_nao_pega_em_banco_de_memoria(tmp_path):
    """`:memory:` responde `memory` a `journal_mode=WAL`, sem levantar erro.

    Nao e detalhe de trivia: `test_pragma_e_aceito` roda em `:memory:` e so
    verifica que o pragma nao explode. Se alguem promover aquele teste a
    "WAL esta ligado", estara afirmando algo que `:memory:` nunca entrega.
    O banco do indice e arquivo, e so em arquivo o modo vira `wal`.
    """
    conexao = sqlite3.connect(":memory:")
    assert conexao.execute("PRAGMA journal_mode=WAL").fetchone() == ("memory",)
    conexao.close()

    conexao = sqlite3.connect(tmp_path / "indice.db")
    assert conexao.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
    conexao.close()


def test_synchronous_recusa_dentro_de_transacao(tmp_path):
    """Depois de uma escrita, `synchronous` levanta em vez de aplicar.

    O modulo `sqlite3` abre transacao implicita no primeiro INSERT. Dentro
    dela o SQLite recusa mudar o nivel de seguranca. Esta e a metade RUIDOSA
    do problema de ordem -- quem aplicar os pragmas tarde vai ver o traceback.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")
    assert conexao.in_transaction

    with pytest.raises(sqlite3.OperationalError, match="Safety level"):
        conexao.execute("PRAGMA synchronous=NORMAL")
    assert conexao.execute("PRAGMA synchronous").fetchone() == (2,)  # 2 == FULL
    conexao.close()


def test_wal_falha_calado_dentro_de_transacao(tmp_path):
    """Depois de uma escrita, `journal_mode=WAL` NAO levanta -- e nao aplica.

    Esta e a metade SILENCIOSA, e a perigosa: o pragma devolve `delete` e seu
    valor efetivo continua `delete`, sem excecao nenhuma. Um indice aberto
    nessa ordem roda a fase inteira em journal de rollback acreditando estar em
    WAL, e nada acusa. Por isso a abertura tem que aplicar os pragmas ANTES de
    qualquer escrita, ou desligar o gerenciamento implicito de transacao.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")
    assert conexao.in_transaction

    assert conexao.execute("PRAGMA journal_mode=WAL").fetchone() == ("delete",)
    assert conexao.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    conexao.close()


def test_foreign_keys_falha_calado_dentro_de_transacao(tmp_path):
    """Depois de uma escrita, `foreign_keys=ON` NAO levanta -- e fica em 0.

    A terceira falha de ordem, e a pior das tres. `journal_mode` errado custa
    durabilidade; `foreign_keys=0` custa INTEGRIDADE, porque desliga
    `ON DELETE CASCADE` -- veja `test_cascade_nao_acontece_com_foreign_keys_tarde`.
    Existe separado do teste de dano para que ninguem "conserte" a ordem
    achando que so `journal_mode` importava.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")
    assert conexao.in_transaction

    assert conexao.execute("PRAGMA foreign_keys=ON").fetchall() == []
    assert conexao.execute("PRAGMA foreign_keys").fetchone() == (0,)
    conexao.close()


def test_cascade_nao_acontece_com_foreign_keys_tarde(tmp_path):
    """O dano concreto: no orfao sobrevive ao DELETE do arquivo dele.

    Este teste nao e sobre pragma, e sobre a consequencia. Sem CASCADE o
    indice acumula no orfao a cada reindexacao de arquivo alterado, calado, e
    um indice que junta lixo em silencio e pior que um que falha. E o que a
    Task 3 precisa pesar ao escolher entre ordem estrita e isolation_level=None.
    """

    def monta(conexao):
        conexao.execute("CREATE TABLE files (path TEXT PRIMARY KEY)")
        conexao.execute(
            "CREATE TABLE nodes (node_id TEXT PRIMARY KEY, path TEXT "
            "REFERENCES files(path) ON DELETE CASCADE)"
        )
        conexao.execute("INSERT INTO files VALUES ('a.py')")
        conexao.execute("INSERT INTO nodes VALUES ('n1', 'a.py')")

    def orfaos_apos_apagar(conexao):
        conexao.execute("DELETE FROM files WHERE path = 'a.py'")
        return conexao.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    tarde = sqlite3.connect(tmp_path / "tarde.db")
    monta(tarde)
    tarde.execute("PRAGMA foreign_keys=ON")  # tarde demais, fica em 0
    assert tarde.execute("PRAGMA foreign_keys").fetchone() == (0,)
    assert orfaos_apos_apagar(tarde) == 1  # o no sobreviveu: CASCADE nao rodou
    tarde.close()

    cedo = sqlite3.connect(tmp_path / "cedo.db")
    cedo.execute("PRAGMA foreign_keys=ON")
    monta(cedo)
    assert cedo.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert orfaos_apos_apagar(cedo) == 0
    cedo.close()


@pytest.mark.parametrize(
    ("pragma", "leitura", "esperado"),
    [("temp_store=MEMORY", "temp_store", 2), ("busy_timeout=30000", "busy_timeout", 30000)],
)
def test_pragma_de_conexao_pega_mesmo_dentro_de_transacao(tmp_path, pragma, leitura, esperado):
    """Estes dois sao os unicos da lista imunes a ordem, e isso foi medido.

    Sao propriedade da conexao, nao do arquivo de banco, entao transacao aberta
    nao os bloqueia. Fica afirmado para que a Task 3 saiba exatamente quais
    tres pragmas a ordem protege -- e nao gaste esforco protegendo os cinco.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")
    assert conexao.in_transaction

    conexao.execute(f"PRAGMA {pragma}")
    assert conexao.execute(f"PRAGMA {leitura}").fetchone() == (esperado,)
    conexao.close()


def test_pragmas_antes_da_primeira_escrita_pegam(tmp_path):
    """A ordem que a abertura do indice deve usar, afirmada de ponta a ponta.

    Aplicar tudo antes do primeiro INSERT faz os CINCO pragmas PERSISTIREM
    depois da escrita -- que e o contrato que a Task 3 precisa honrar. Le
    valor efetivo de todos, e nao so dos dois que ja falharam em outro teste,
    porque contrato conferido pela metade nao e contrato.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    for pragma in PRAGMAS_DE_ABERTURA:
        conexao.execute(f"PRAGMA {pragma}")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")

    assert conexao.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert conexao.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert conexao.execute("PRAGMA synchronous").fetchone() == (1,)  # 1 == NORMAL
    assert conexao.execute("PRAGMA temp_store").fetchone() == (2,)  # 2 == MEMORY
    assert conexao.execute("PRAGMA busy_timeout").fetchone() == (30000,)
    conexao.close()


def test_autocommit_permite_pragma_depois_da_escrita(tmp_path):
    """`isolation_level=None` e a outra saida, e ela funciona.

    Sem gerenciamento implicito de transacao nao ha transacao aberta pelo
    INSERT, entao os pragmas passam em qualquer ordem. Fica afirmado aqui para
    que a Task 3 possa escolher esta rota com lastro, e nao por suposicao.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db", isolation_level=None)
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")
    assert not conexao.in_transaction

    for pragma in PRAGMAS_DE_ABERTURA:
        conexao.execute(f"PRAGMA {pragma}")
    assert conexao.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert conexao.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert conexao.execute("PRAGMA synchronous").fetchone() == (1,)
    assert conexao.execute("PRAGMA temp_store").fetchone() == (2,)
    assert conexao.execute("PRAGMA busy_timeout").fetchone() == (30000,)
    conexao.close()
