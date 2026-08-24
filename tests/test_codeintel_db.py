"""O que o indice exige do interpretador, verificado onde o CI roda.

Este arquivo vem antes de qualquer schema de proposito. As medicoes que
justificam a fase foram feitas em Python 3.14.6, e o `pyproject.toml` declara
suporte a partir do 3.10 -- FTS5 e compilado opcional do SQLite, e um ambiente
sem ele faria o indice falhar na criacao, nao na consulta. Melhor descobrir num
teste nomeado do que num traceback de usuario.
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


def test_pragmas_antes_da_primeira_escrita_pegam(tmp_path):
    """A ordem que a abertura do indice deve usar, afirmada de ponta a ponta.

    Aplicar tudo antes do primeiro INSERT faz WAL e synchronous PERSISTIREM
    depois da escrita -- que e o contrato que a Task 3 precisa honrar.
    """
    conexao = sqlite3.connect(tmp_path / "indice.db")
    for pragma in PRAGMAS_DE_ABERTURA:
        conexao.execute(f"PRAGMA {pragma}")
    conexao.execute("CREATE TABLE t (a)")
    conexao.execute("INSERT INTO t VALUES (1)")

    assert conexao.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert conexao.execute("PRAGMA synchronous").fetchone() == (1,)  # 1 == NORMAL
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
    assert conexao.execute("PRAGMA synchronous").fetchone() == (1,)
    conexao.close()
