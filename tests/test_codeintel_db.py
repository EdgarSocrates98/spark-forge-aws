"""O que o indice exige do interpretador, e o schema que ele monta em cima.

A primeira metade deste arquivo veio ANTES de qualquer schema, de proposito: e
ela que mede o comportamento do SQLite que o schema depois tem que honrar. A
segunda metade -- de `test_schema_cria_as_tabelas_declaradas` em diante --
exercita `sparkforge/codeintel/db.py`, e existe aqui e nao em arquivo proprio
porque as duas afirmam o MESMO contrato de pragma: separa-las deixaria a
medicao de um lado e o codigo que depende dela do outro.

As medicoes que
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

from sparkforge.codeintel.db import PRAGMAS_DE_ABERTURA as PRAGMAS_DO_MODULO
from sparkforge.codeintel.db import (
    SCHEMA_VERSION,
    abrir,
    criar_schema,
    impressao_da_raiz,
)

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


def test_a_lista_do_modulo_e_a_mesma_que_esta_medida_aqui():
    """A lista acima so vale como medicao se for a lista que `db.abrir` usa.

    Ela foi escrita antes de `db.py` existir, e uma copia que sai de sincronia
    transforma sete testes de pragma em teatro: todos verdes sobre uma sequencia
    que o codigo nao aplica mais.
    """
    assert list(PRAGMAS_DO_MODULO) == PRAGMAS_DE_ABERTURA


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


# --------------------------------------------------------------------------
# Daqui em diante: `sparkforge/codeintel/db.py`, o schema construido sobre as
# medicoes acima.
# --------------------------------------------------------------------------


def test_schema_cria_as_tabelas_declaradas(tmp_path):
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    tabelas = {
        linha[0]
        for linha in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
        )
    }
    conexao.close()
    assert {"metadata", "files", "nodes", "unresolved_refs", "symbols_fts"} <= tabelas


def test_schema_tem_edges_e_unresolved(tmp_path):
    """As duas tabelas da fase J4, e as duas juntas de proposito.

    Ate J3 este arquivo afirmava o CONTRARIO -- que `edges` nao existia --
    porque aresta sem resolucao de referencia seria tabela que ninguem sabe
    quando confiar. J4 traz a resolucao, entao a afirmacao inverte. As duas
    andam juntas: `edges` guarda o que resolveu e `unresolved_refs` guarda o
    que nao resolveu, e so as duas somadas dizem qual e a cobertura.
    """
    conexao = abrir(tmp_path / "g.sqlite3")
    criar_schema(conexao)
    tabelas = {
        linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conexao.close()
    assert {"edges", "unresolved_refs"} <= tabelas


def test_apagar_no_apaga_as_arestas_dele(tmp_path):
    """CASCADE nos dois sentidos: aresta que sai e aresta que chega.

    Sem isso, reindexar um arquivo deixa aresta apontando para no que nao existe
    mais -- e uma travessia que segue essa aresta devolve resultado inventado.

    As duas arestas sao o que torna o teste capaz de pegar CASCADE de um lado
    so: apagar `n2` tem que levar a que CHEGA nele e a que SAI dele. Com o
    CASCADE so em `target_id` sobraria `n2 -> n1`; so em `source_id` sobraria
    `n1 -> n2`. Zero exige os dois.
    """
    conexao = abrir(tmp_path / "g.sqlite3")
    criar_schema(conexao)
    conexao.execute("INSERT INTO files (id,path,language,content_sha256,size_bytes,"
                    "modified_ns,indexed_at) VALUES ('f1','a.py','python','x',1,1,1)")
    for nid in ("n1", "n2"):
        conexao.execute("INSERT INTO nodes (id,file_id,kind,name,qualified_name,"
                        "start_line,end_line) VALUES (?,'f1','function',?,?,1,2)",
                        (nid, nid, nid))
    conexao.execute("INSERT INTO edges (source_id,target_id,kind,line) "
                    "VALUES ('n1','n2','calls',5)")
    conexao.execute("INSERT INTO edges (source_id,target_id,kind,line) "
                    "VALUES ('n2','n1','calls',7)")
    conexao.execute("DELETE FROM nodes WHERE id='n2'")
    restantes = conexao.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    conexao.close()
    assert restantes == 0, "aresta sobreviveu ao alvo -- travessia devolveria no fantasma"


def test_edges_tem_indice_nas_duas_pontas_e_no_kind(tmp_path):
    """As tres colunas por onde a travessia entra, cada uma liderando um indice.

    `chamadores` filtra por `target_id`, `callees` por `source_id`, e o corte
    por tipo de aresta por `kind`. Sem indice liderado por elas cada pergunta
    vira varredura das ~25 mil arestas medidas nesta arvore, e a fase J3 ja
    mediu que o indice so se paga quando responde mais rapido que `grep`.

    Afirma a COLUNA LIDER e nao o nome do indice: nome e convencao, coluna
    lider e o que decide se o planejador usa o indice.
    """
    conexao = abrir(tmp_path / "g.sqlite3")
    criar_schema(conexao)
    lideres = set()
    for indice in conexao.execute("PRAGMA index_list('edges')").fetchall():
        colunas = conexao.execute(f"PRAGMA index_info({indice[1]!r})").fetchall()
        lideres.add(colunas[0][2])
    conexao.close()
    assert {"source_id", "target_id", "kind"} <= lideres


def test_banco_de_versao_de_schema_anterior_e_refeito(tmp_path):
    """`CREATE TABLE IF NOT EXISTS` acrescenta tabela nova e nao conserta velha.

    Um banco da versao anterior sobreviveria com as colunas antigas de
    `unresolved_refs`, e o primeiro INSERT da versao nova levantaria
    `no such column` no meio de uma indexacao -- em producao, nao em teste.
    Subir `SCHEMA_VERSION` so significa alguma coisa se alguem age sobre ele.
    """
    caminho = tmp_path / "g.sqlite3"
    conexao = abrir(caminho)
    criar_schema(conexao)
    conexao.execute("INSERT INTO files (id,path,language,content_sha256,size_bytes,"
                    "modified_ns,indexed_at) VALUES ('f1','a.py','python','x',1,1,1)")
    conexao.execute("UPDATE metadata SET value='0' WHERE key='schema_version'")
    conexao.close()

    conexao = abrir(caminho)
    criar_schema(conexao)
    sobrou = conexao.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    versao = conexao.execute(
        "SELECT value FROM metadata WHERE key='schema_version'"
    ).fetchone()[0]
    conexao.close()
    assert sobrou == 0, "banco de versao anterior sobreviveu com o schema antigo"
    assert versao == str(SCHEMA_VERSION)


def test_banco_da_versao_1_de_verdade_e_refeito(tmp_path):
    """O banco que J3 realmente escrevia, com as colunas que J4 aposentou.

    O teste acima simula outra versao mexendo no `metadata`, e por isso passa
    com qualquer valor de `SCHEMA_VERSION` -- inclusive com ele nao subido.
    Este nao: aqui o banco DIZ 1, e se a constante tambem dissesse 1 nada seria
    descartado, `unresolved_refs` sobreviveria com `raw_target`/`kind`, e o
    INSERT com as colunas novas levantaria `no such column`. E o caminho de
    upgrade real, e e o unico jeito de "subiu a versao" virar afirmacao em vez
    de numero decorativo.
    """
    caminho = tmp_path / "g.sqlite3"
    conexao = abrir(caminho)
    conexao.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conexao.execute(
        "CREATE TABLE unresolved_refs ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " file_id TEXT NOT NULL,"
        " from_node_id TEXT,"
        " raw_target TEXT NOT NULL,"
        " kind TEXT NOT NULL,"
        " line INTEGER NOT NULL,"
        " reason TEXT NOT NULL)"
    )
    conexao.execute("INSERT INTO metadata (key, value) VALUES ('schema_version','1')")
    conexao.close()

    conexao = abrir(caminho)
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    conexao.execute(
        "INSERT INTO unresolved_refs "
        "(file_id, reference_name, reference_kind, line, reason) "
        "VALUES ('f1','spark.read','calls',3,'nome externo ao indice')"
    )
    quantas = conexao.execute("SELECT COUNT(*) FROM unresolved_refs").fetchone()[0]
    conexao.close()
    assert quantas == 1


def test_banco_da_versao_corrente_nao_e_jogado_fora(tmp_path):
    """O outro lado da guarda acima, e o que impede que ela apague tudo sempre.

    `indexar` chama `criar_schema` a cada execucao. Se a comparacao de versao
    estivesse invertida -- ou ausente, com o DROP incondicional -- a suite
    inteira continuaria verde e o indice seria refeito do zero toda vez, calado.
    """
    caminho = tmp_path / "g.sqlite3"
    conexao = abrir(caminho)
    criar_schema(conexao)
    conexao.execute("INSERT INTO files (id,path,language,content_sha256,size_bytes,"
                    "modified_ns,indexed_at) VALUES ('f1','a.py','python','x',1,1,1)")
    conexao.close()

    conexao = abrir(caminho)
    criar_schema(conexao)
    sobrou = conexao.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    conexao.close()
    assert sobrou == 1


def test_schema_grava_a_versao_e_nao_grava_caminho_absoluto(tmp_path):
    """O banco nao pode carregar o caminho da maquina.

    Caminho absoluto no `metadata` vazaria o nome do usuario e do diretorio num
    artefato que pode ser copiado, e tornaria o banco preso a uma maquina.
    """
    caminho = tmp_path / "graph.sqlite3"
    conexao = abrir(caminho)
    criar_schema(conexao)
    valores = dict(conexao.execute("SELECT key, value FROM metadata"))
    conexao.close()
    assert valores["schema_version"] == str(SCHEMA_VERSION)
    for chave, valor in valores.items():
        assert str(tmp_path) not in valor, f"{chave} carrega caminho absoluto"


def test_metadata_tem_os_quatro_campos_obrigatorios(tmp_path):
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    valores = dict(conexao.execute("SELECT key, value FROM metadata"))
    conexao.close()
    assert set(valores) >= {"schema_version", "engine_version", "created_at", "root_fingerprint"}
    assert valores["engine_version"]


def test_metadata_com_raiz_declarada_continua_sem_o_caminho(tmp_path):
    """O caso que o teste sem raiz nao cobre.

    Sem `raiz`, a impressao e string vazia e "nao contem o caminho" passa a
    troco de nada. Com raiz declarada e que a afirmacao vale alguma coisa.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao, raiz=tmp_path)
    valores = dict(conexao.execute("SELECT key, value FROM metadata"))
    conexao.close()
    assert valores["root_fingerprint"]
    for chave, valor in valores.items():
        assert str(tmp_path) not in valor, f"{chave} carrega caminho absoluto"
        assert tmp_path.name not in valor, f"{chave} carrega o nome do diretorio"


def test_impressao_da_raiz_identifica_sem_nomear(tmp_path):
    """Raizes diferentes dao impressoes diferentes, e a mesma raiz repete."""
    uma = tmp_path / "uma"
    outra = tmp_path / "outra"
    uma.mkdir()
    outra.mkdir()
    assert impressao_da_raiz(uma) == impressao_da_raiz(uma)
    assert impressao_da_raiz(uma) != impressao_da_raiz(outra)
    assert impressao_da_raiz(None) == ""


def test_criar_schema_e_idempotente(tmp_path):
    """Reindexar chama `criar_schema` de novo, e isso nao pode explodir.

    Tambem nao pode duplicar `metadata`: a chave e PRIMARY KEY e a escrita e
    INSERT OR REPLACE, entao a segunda passagem atualiza em vez de somar linha.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    criar_schema(conexao)
    (quantas,) = conexao.execute("SELECT COUNT(*) FROM metadata").fetchone()
    conexao.close()
    assert quantas == 4


def test_apagar_arquivo_apaga_os_nos_dele(tmp_path):
    """ON DELETE CASCADE, verificado de verdade.

    `PRAGMA foreign_keys=ON` nao e o default do SQLite -- sem ele o CASCADE e
    declarado e nao acontece, e o banco acumula no orfao a cada reindexacao.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    conexao.execute(
        "INSERT INTO nodes (id, file_id, kind, name, qualified_name, "
        "start_line, end_line) VALUES ('n1','f1','function','x','a.x',1,2)"
    )
    conexao.execute("DELETE FROM files WHERE id = 'f1'")
    restantes = conexao.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    conexao.close()
    assert restantes == 0


def test_apagar_arquivo_apaga_as_referencias_nao_resolvidas_dele(tmp_path):
    """`unresolved_refs` tambem e por arquivo, e tambem tem que cair junto.

    Ela e a tabela que mais cresce por reindexacao -- toda referencia que nao
    resolve cai la. Orfao acumulado aqui inflaria a contagem de ponto cego, que
    e justamente o numero que ela existe para tornar confiavel.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    conexao.execute(
        "INSERT INTO unresolved_refs "
        "(file_id, reference_name, reference_kind, line, reason) "
        "VALUES ('f1','spark.read','calls',3,'nome externo ao indice')"
    )
    conexao.execute("DELETE FROM files WHERE id = 'f1'")
    restantes = conexao.execute("SELECT COUNT(*) FROM unresolved_refs").fetchone()[0]
    conexao.close()
    assert restantes == 0


def test_symbols_fts_acha_por_parte_de_nome_composto(tmp_path):
    """A medicao de FTS5 la de cima, agora sobre a tabela que o schema cria.

    `test_fts5_casa_termo_dentro_de_nome_composto` provou o comportamento numa
    tabela improvisada. Este prova que `symbols_fts` foi declarada de um jeito
    que o preserva -- um tokenizador custom no CREATE quebraria a busca por
    parte de nome sem que aquele outro teste piscasse.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO symbols_fts (node_id, name, qualified_name) "
        "VALUES ('n1','iter_source_files','scan.iter_source_files')"
    )
    achados = conexao.execute(
        "SELECT node_id FROM symbols_fts WHERE symbols_fts MATCH 'source'"
    ).fetchall()
    conexao.close()
    assert achados == [("n1",)]


def test_abrir_deixa_os_cinco_pragmas_efetivos_depois_de_escrever(tmp_path):
    """O contrato de `abrir`, conferido onde importa: DEPOIS da primeira escrita.

    Ler os pragmas logo apos abrir provaria pouco -- a falha medida e que eles
    nao SOBREVIVEM a escrita quando chegam tarde. Aqui o schema inteiro ja foi
    criado e uma linha ja foi inserida antes da releitura.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    assert conexao.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert conexao.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert conexao.execute("PRAGMA synchronous").fetchone() == (1,)
    assert conexao.execute("PRAGMA temp_store").fetchone() == (2,)
    assert conexao.execute("PRAGMA busy_timeout").fetchone() == (30000,)
    conexao.close()


def test_abrir_recusa_conexao_em_que_foreign_keys_nao_pegou(tmp_path, monkeypatch):
    """A guarda de `abrir` tem que ser demonstravel, senao e decoracao.

    Sem este teste nada distingue `abrir` com a releitura de `abrir` sem ela:
    no caminho feliz o valor sempre da 1, e uma guarda que nunca dispara em
    teste nenhum e indistinguivel de guarda ausente.

    O gatilho e a regressao real e nao uma situacao inventada: e `abrir` sem
    `isolation_level=None`, com uma escrita antes dos pragmas. Foi medido que
    nesse estado `journal_mode=WAL` devolve `('delete',)` sem levantar e
    `foreign_keys=ON` devolve `[]` sem levantar, e e a guarda -- e so ela --
    que transforma isso em erro.

    Transacao ABERTA COM `BEGIN` nao serviria: medido, ali `journal_mode=WAL`
    levanta antes, e o teste passaria pelo motivo errado.
    """
    conectar_de_verdade = sqlite3.connect

    def conectar_como_se_isolation_level_tivesse_sumido(*args, **kwargs):
        kwargs.pop("isolation_level", None)
        conexao = conectar_de_verdade(*args, **kwargs)
        conexao.execute("CREATE TABLE _sujeira (a)")
        conexao.execute("INSERT INTO _sujeira VALUES (1)")
        return conexao

    monkeypatch.setattr(sqlite3, "connect", conectar_como_se_isolation_level_tivesse_sumido)
    with pytest.raises(RuntimeError, match="foreign_keys"):
        abrir(tmp_path / "graph.sqlite3")


def test_abrir_nao_deixa_transacao_implicita_aberta(tmp_path):
    """A defesa que protege a PROXIMA pessoa, e nao so esta abertura.

    Aplicar os pragmas cedo resolve hoje. `isolation_level=None` resolve tambem
    para quem acrescentar um pragma depois do schema daqui a tres fases, que e
    exatamente como o defeito medido volta.
    """
    conexao = abrir(tmp_path / "graph.sqlite3")
    criar_schema(conexao)
    conexao.execute(
        "INSERT INTO files (id, path, language, content_sha256, size_bytes, "
        "modified_ns, indexed_at) VALUES ('f1','a.py','python','abc',1,1,1)"
    )
    assert not conexao.in_transaction
    conexao.close()
