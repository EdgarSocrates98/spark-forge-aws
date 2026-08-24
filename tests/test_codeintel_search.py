"""Busca por nome, e a seguranca da consulta.

FTS5 tem sintaxe propria: aspas, `*`, `NEAR`, `OR`, `^` e `coluna:` sao
operadores. Termo vindo de fora que chegue cru ao MATCH pode virar erro de
sintaxe -- ou consulta que o chamador nao pediu. A secao 30 da SPEC exige
construtor de consulta, nunca MATCH com texto de terceiro.

POR QUE EXISTE UMA FIXTURE SO PARA OS OPERADORES
------------------------------------------------
Metade das dez formas do plano NAO levanta no indice minimo: `a OR b`,
`a AND b`, `NEAR(a b)`, `a*` e `^x` sao sintaxe VALIDA de FTS5, e num indice que
nao tem simbolo chamado `a` nem `b` elas devolvem lista vazia -- que e a mesma
coisa que o construtor devolveria. Um teste que so afirmasse "nao levantou"
passaria com o construtor DESLIGADO, e o proprio plano avisa disso.

`indexado_com_operadores` da corpo ao que faltava: simbolos `a`, `b`, `x`,
`abacaxi` e `zebra_x`, dispostos para que os operadores listados em `PERIGOSAS`
produzam resultado DIFERENTE do que o construtor produz.
`test_operador_de_fts_nao_e_executado`
afirma os dois lados na mesma execucao -- o que `buscar` devolve e o que o MATCH
cru devolveria --, entao ele acusa tanto o construtor removido quanto a fixture
que deixou de tornar a forma perigosa.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from sparkforge.adapters.cli import main as cli_main
from sparkforge.codeintel.db import BANCO_PADRAO, SCHEMA_VERSION
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.search import Achado, buscar, construir_consulta, resumo

FONTE_OPERADORES = (
    # `b.a` da uma linha cujo `qualified_name` tem os dois tokens `b` e `a`, que e
    # o que torna `a AND b` e `NEAR(a b)` capazes de casar alguma coisa no MATCH
    # cru. Sem ela as duas formas devolveriam vazio por falta de dado, e o teste
    # nao mediria nada.
    "class b:\n"
    "    def a(self):\n"
    "        pass\n"
    "\n"
    "\n"
    "def x():\n"
    "    pass\n"
    "\n"
    "\n"
    "def abacaxi():\n"
    "    pass\n"
    "\n"
    "\n"
    "def zebra_x():\n"
    "    pass\n"
)


@pytest.fixture
def indexado(tmp_path):
    (tmp_path / "jobs").mkdir()
    (tmp_path / "jobs" / "etl.py").write_text(
        "def iter_source_files():\n    pass\n\n\ndef processar_lote():\n    pass\n",
        encoding="utf-8",
    )
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    return banco


@pytest.fixture
def indexado_com_operadores(tmp_path):
    (tmp_path / "ops.py").write_text(FONTE_OPERADORES, encoding="utf-8")
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    return banco


@pytest.fixture
def indexado_com_empate(tmp_path):
    """Tres arquivos com o MESMO simbolo, e um deles reinserido por ultimo.

    A relevancia do FTS empata entre os tres -- mesmo termo, mesma coluna, mesmo
    comprimento --, entao so o desempate decide a ordem entre eles.

    A REINSERCAO NAO E TRUQUE, E O CASO DA FASE SEGUINTE. `iter_source_files`
    entrega os arquivos ja ordenados por caminho e `indexar` reconstroi tudo,
    entao num indice recem-construido a ordem de insercao E a ordem de caminho
    -- e um teste sobre esse indice passaria com o desempate REMOVIDO, porque a
    ordem barata do SQLite ja coincide com a certa. A fase incremental (J4)
    reindexa um arquivo por vez, e o arquivo reindexado volta para o fim: e
    exatamente o que `_reinserir` faz aqui, com o schema real.
    """
    for nome in ("a_primeiro.py", "b_segundo.py", "c_terceiro.py"):
        (tmp_path / nome).write_text(
            "def alvo():\n    pass\n\n\ndef alvo_de_novo():\n    pass\n", encoding="utf-8"
        )
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    _reinserir(banco, "a_primeiro.py")
    return banco


def _reinserir(banco, path: str) -> None:
    """Move as linhas de `path` para o fim das tabelas, sem mudar valor nenhum.

    E a forma que uma reindexacao incremental deixaria no banco. Nada aqui
    inventa dado: as mesmas colunas voltam com os mesmos valores, so a ordem
    fisica muda.
    """
    conexao = sqlite3.connect(banco)
    conexao.execute("PRAGMA foreign_keys=ON")
    try:
        arquivo = conexao.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
        nos = conexao.execute(
            "SELECT nodes.* FROM nodes JOIN files ON files.id = nodes.file_id"
            " WHERE files.path = ?",
            (path,),
        ).fetchall()
        fts = conexao.execute(
            "SELECT symbols_fts.node_id, symbols_fts.name, symbols_fts.qualified_name"
            "  FROM symbols_fts JOIN nodes ON nodes.id = symbols_fts.node_id"
            "  JOIN files ON files.id = nodes.file_id WHERE files.path = ?",
            (path,),
        ).fetchall()
        conexao.execute(
            "DELETE FROM symbols_fts WHERE node_id IN"
            " (SELECT nodes.id FROM nodes JOIN files ON files.id = nodes.file_id"
            "  WHERE files.path = ?)",
            (path,),
        )
        conexao.execute("DELETE FROM files WHERE path = ?", (path,))
        conexao.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?)", arquivo)
        conexao.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", nos)
        conexao.executemany("INSERT INTO symbols_fts VALUES (?, ?, ?)", fts)
        conexao.commit()
    finally:
        conexao.close()


def _match_cru(banco, termo: str) -> list[str] | str:
    """O que o MATCH devolveria com o termo interpolado cru, ou o nome do erro.

    Existe para o teste poder afirmar que a forma testada E perigosa neste
    indice -- sem isso, "buscar devolveu X" nao distingue construtor funcionando
    de operador que por acaso nao tinha o que casar.
    """
    conexao = sqlite3.connect(banco)
    try:
        linhas = conexao.execute(
            "SELECT nodes.qualified_name FROM symbols_fts"
            " JOIN nodes ON nodes.id = symbols_fts.node_id"
            " WHERE symbols_fts MATCH ? ORDER BY nodes.qualified_name",
            (termo,),
        ).fetchall()
    except sqlite3.Error as exc:
        return type(exc).__name__
    finally:
        conexao.close()
    return [linha[0] for linha in linhas]


class TestBuscaBasica:
    def test_acha_por_parte_do_nome(self, indexado):
        achados = buscar(indexado, "source")
        assert [a.name for a in achados] == ["iter_source_files"]

    def test_resultado_traz_arquivo_e_linha(self, indexado):
        (achado,) = buscar(indexado, "processar")
        assert achado.path == "jobs/etl.py"
        assert achado.start_line > 0

    def test_resultado_traz_o_bastante_para_ir_ao_codigo(self, indexado):
        (achado,) = buscar(indexado, "processar")
        assert isinstance(achado, Achado)
        assert achado.kind == "function"
        assert achado.qualified_name == "processar_lote"
        assert achado.node_id

    def test_nao_devolve_corpo_de_funcao(self, indexado):
        """INV-010 tem que valer na SAIDA, e nao so no schema.

        O banco nao guarda corpo, entao `buscar` nao teria como devolver -- mas
        "nao teria como" e propriedade de hoje, e um campo novo em `Achado` que
        lesse o arquivo em disco quebraria isso sem quebrar nenhum outro teste.
        """
        (achado,) = buscar(indexado, "processar")
        assert not hasattr(achado, "body")
        assert "pass" not in repr(achado)

    def test_termo_que_nao_existe_devolve_vazio(self, indexado):
        assert buscar(indexado, "inexistente_no_indice") == []

    def test_limite_corta_o_resultado(self, indexado_com_empate):
        assert len(buscar(indexado_com_empate, "alvo")) > 1
        assert len(buscar(indexado_com_empate, "alvo", limite=1)) == 1

    def test_limite_nao_positivo_devolve_vazio_e_nao_tudo(self, indexado_com_empate):
        """`LIMIT -1` no SQLite e SEM limite, e nao "nenhuma linha".

        E a mesma porta do termo vazio devolvendo o indice inteiro, aberta pelo
        outro argumento -- `--limit -1` na CLI chegaria aqui.
        """
        assert buscar(indexado_com_empate, "alvo", limite=0) == []
        assert buscar(indexado_com_empate, "alvo", limite=-1) == []


class TestOrdemDeterministica:
    def test_ordem_e_deterministica(self, indexado):
        assert [a.node_id for a in buscar(indexado, "e")] == [
            a.node_id for a in buscar(indexado, "e")
        ]

    def test_empate_de_relevancia_e_desempatado_por_caminho_e_linha(
        self, indexado_com_empate
    ):
        """O desempate explicito, medido onde a relevancia nao decide nada.

        Sem `(path, start_line, node_id)` no ORDER BY a ordem seria a que o
        SQLite achar mais barata -- que aqui e a ordem fisica das linhas, e a
        fixture move `a_primeiro.py` para o fim justamente para que ela NAO
        coincida com a ordem de caminho. Ordem instavel falharia de forma
        intermitente, que e pior que falhar sempre.
        """
        achados = buscar(indexado_com_empate, "alvo")
        # Dois grupos de relevancia: `alvo` casa exato e vem antes de
        # `alvo_de_novo`, que casa um token de tres. DENTRO de cada grupo o
        # `rank` empata, e ai so o desempate ordena.
        assert [(a.path, a.start_line) for a in achados] == [
            ("a_primeiro.py", 1),
            ("b_segundo.py", 1),
            ("c_terceiro.py", 1),
            ("a_primeiro.py", 5),
            ("b_segundo.py", 5),
            ("c_terceiro.py", 5),
        ]


class TestSegurancaDaConsulta:
    # As dez do plano, mais as que faltavam: filtro de coluna (`name:`,
    # `{name qualified_name}:`), negacao (`NOT`, `-`), operador solto no fim,
    # parenteses fechado, chaves e `+`. Todas sao sintaxe REAL de FTS5.
    FORMAS = (
        '"',
        'x"y',
        "a OR b",
        "NEAR(a b)",
        "*",
        "a*",
        "(",
        "a AND b",
        "'",
        "^x",
        "a NOT b",
        "-a",
        "name:a",
        "{name qualified_name} : a",
        ")",
        "a OR",
        "AND",
        "{",
        "a + b",
        "NEAR(a b, 2)",
        '""',
        "a:b:c",
    )

    @pytest.mark.parametrize("termo", FORMAS)
    def test_sintaxe_de_fts_no_termo_nao_levanta(self, indexado_com_operadores, termo):
        """Termo com operador de FTS e tratado como texto, nunca como sintaxe."""
        buscar(indexado_com_operadores, termo)

    # (termo, o que `buscar` deve devolver, o que o MATCH CRU devolveria).
    # O terceiro campo e o que prova que a forma e perigosa NESTE indice: se ele
    # deixar de bater, a fixture parou de tornar o operador real e o primeiro
    # campo virou afirmacao vazia.
    PERIGOSAS = (
        ("a OR b", [], ["b", "b.a"]),
        ("a AND b", [], ["b.a"]),
        ("NEAR(a b)", [], ["b.a"]),
        ("a*", ["b.a"], ["abacaxi", "b.a"]),
        ("^x", ["x", "zebra_x"], ["x"]),
        ("name:a", [], ["b.a"]),
        # `a NOT b` NAO entra aqui, e a ausencia e deliberada: nesta fixture o
        # unico simbolo com o token `a` tem `b` no nome qualificado, entao o
        # MATCH cru tambem devolve vazio e a linha nao distinguiria nada. Ela
        # continua em `FORMAS`, onde o que se afirma e so que nao levanta.
        ('"', [], "OperationalError"),
        ('x"y', [], "OperationalError"),
        ("(", [], "OperationalError"),
        ("*", [], "OperationalError"),
        ("'", [], "OperationalError"),
    )

    @pytest.mark.parametrize(("termo", "esperado", "cru"), PERIGOSAS)
    def test_operador_de_fts_nao_e_executado(
        self, indexado_com_operadores, termo, esperado, cru
    ):
        assert _match_cru(indexado_com_operadores, termo) == cru, (
            f"a fixture deixou de tornar {termo!r} perigoso -- o MATCH cru "
            "nao produz mais resultado diferente, entao o outro assert deste "
            "teste passaria com o construtor de consulta desligado"
        )
        assert sorted(a.qualified_name for a in buscar(indexado_com_operadores, termo)) == esperado

    def test_termo_vazio_devolve_vazio_e_nao_o_indice_inteiro(self, indexado):
        assert buscar(indexado, "") == []
        assert buscar(indexado, "   ") == []

    def test_termo_so_de_pontuacao_devolve_vazio(self, indexado):
        """Sem token nao ha consulta -- e `MATCH ''` levanta, nao devolve tudo."""
        assert buscar(indexado, "*.-()") == []

    def test_termo_sem_token_nem_chega_a_consultar(self, indexado):
        assert construir_consulta("") is None
        assert construir_consulta("   ") is None
        assert construir_consulta("*.-()") is None

    def test_construtor_so_emite_token_entre_aspas(self):
        """O alfabeto do token e o que torna a citacao suficiente.

        `\\w+` nao casa nenhum caractere que o FTS5 leia como operador -- aspas,
        `*`, `(`, `:`, `^`, `-` e `+` ficam todos de fora. Este teste prende esse
        alfabeto: alarga-lo para deixar passar uma aspa faria a citacao virar
        decoracao, e o termo voltaria a ser sintaxe.
        """
        assert construir_consulta('a" OR "b') == '"a" "OR" "b"'
        assert construir_consulta("iter_source_files") == '"iter_source_files"'
        assert construir_consulta("NEAR(a b)") == '"NEAR" "a" "b"'

    def test_acento_no_termo_sobrevive(self, tmp_path):
        """Identificador nao-ASCII e legal em Python, e cliente tem.

        MEDIDO com o alfabeto trocado para `[A-Za-z0-9_]`, que e a alternativa
        obvia e errada: o construtor produziria `"convers" "o"` -- dois tokens
        que nenhum simbolo tem -- e a busca devolveria lista vazia em silencio.
        Com `\\w+` o caractere acentuado fica DENTRO do token.

        O segundo assert registra comportamento do FTS5 que ninguem escolheu e
        que convem saber: o tokenizador `unicode61` dobra diacritico, entao o
        termo sem acento acha o simbolo com acento. Isso e do SQLite, nao deste
        modulo -- esta aqui para que a mudanca dele apareca como falha de teste,
        e nao como busca que parou de achar.
        """
        (tmp_path / "acento.py").write_text(
            "def conversão_de_moeda():\n    pass\n", encoding="utf-8"
        )
        banco = tmp_path / "graph.sqlite3"
        indexar(tmp_path, banco)
        assert construir_consulta("conversão") == '"conversão"'
        assert [a.name for a in buscar(banco, "conversão")] == ["conversão_de_moeda"]
        assert [a.name for a in buscar(banco, "conversao")] == ["conversão_de_moeda"]


class TestResumo:
    def test_conta_o_que_o_banco_tem_e_quando_foi_feito(self, indexado):
        estado = resumo(indexado)
        assert estado["files"] == 1
        assert estado["nodes"] == 2
        # Contra a constante e nao contra um literal: o numero sobe a cada
        # mudanca de schema, e o que o resumo tem que provar e que ele reporta
        # a versao QUE O BANCO TEM -- nao a que estava escrita aqui em J3.
        assert estado["schema_version"] == SCHEMA_VERSION
        assert estado["created_at"]
        assert estado["root_fingerprint"]

    def test_nao_expoe_caminho_absoluto_da_raiz(self, indexado, tmp_path):
        """O metadata guarda impressao, nao caminho -- e o resumo nao pode desfazer."""
        texto = repr(resumo(indexado))
        assert str(tmp_path) not in texto
        assert ":\\" not in texto and "/home/" not in texto


class TestCli:
    """O verbo `code`, exercitado pela mesma porta que o operador usa.

    Testar `buscar` direto nao alcanca o que a CLI acrescenta: a resolucao do
    caminho do banco (um lugar para os tres subcomandos), a recusa antes de
    abrir e a forma do JSON. Cada um desses ja foi defeito em CLI deste
    repositorio.
    """

    def _arvore(self, tmp_path):
        (tmp_path / "jobs").mkdir()
        (tmp_path / "jobs" / "etl.py").write_text(
            "def iter_source_files():\n    pass\n", encoding="utf-8"
        )
        return tmp_path

    def test_index_grava_no_default_sob_root_e_search_le_do_mesmo_lugar(
        self, tmp_path, capsys
    ):
        raiz = self._arvore(tmp_path)
        assert cli_main(["code", "index", "--root", str(raiz)]) == 0
        indexado = json.loads(capsys.readouterr().out)
        assert indexado["files"] == 1
        assert indexado["nodes"] == 1
        assert indexado["unreadable"] == 0
        assert indexado["db"].endswith(BANCO_PADRAO.as_posix())
        assert (raiz / BANCO_PADRAO).is_file()

        assert cli_main(["code", "search", "source", "--root", str(raiz)]) == 0
        busca = json.loads(capsys.readouterr().out)
        assert busca["returned_count"] == 1
        assert busca["results"][0]["name"] == "iter_source_files"
        assert busca["results"][0]["path"] == "jobs/etl.py"

    def test_status_mostra_o_que_o_banco_tem(self, tmp_path, capsys):
        raiz = self._arvore(tmp_path)
        cli_main(["code", "index", "--root", str(raiz)])
        capsys.readouterr()
        assert cli_main(["code", "status", "--root", str(raiz)]) == 0
        estado = json.loads(capsys.readouterr().out)
        assert estado["files"] == 1
        assert estado["nodes"] == 1
        assert estado["created_at"]

    def test_search_sem_indice_recusa_e_nao_cria_banco_vazio(self, tmp_path, capsys):
        """`sqlite3.connect` cria o arquivo -- perguntar nao pode deixar rastro."""
        banco = tmp_path / "nao_existe.sqlite3"
        assert cli_main(["code", "search", "x", "--db", str(banco)]) == 2
        erro = capsys.readouterr().err
        assert "code index" in erro
        # O erro tem que nomear o banco QUE FOI PEDIDO. `--db` ignorado em favor
        # do default sob `--root` daria o mesmo codigo de saida e a mesma frase,
        # e o operador procuraria o defeito no arquivo errado.
        assert banco.as_posix() in erro
        assert not banco.exists()

    def test_operador_de_fts_pela_cli_nao_levanta(self, tmp_path, capsys):
        raiz = self._arvore(tmp_path)
        cli_main(["code", "index", "--root", str(raiz)])
        capsys.readouterr()
        assert cli_main(["code", "search", "a OR b", "--root", str(raiz)]) == 0
        assert json.loads(capsys.readouterr().out)["returned_count"] == 0


class TestCaminhoPadrao:
    def test_o_banco_padrao_mora_sob_o_estado_local_ignorado_pelo_git(self):
        """`.sparkforge/local/` esta no `.gitignore` desde 715a657.

        Se o default sair de la, o indice de um repositorio de cliente passa a
        ser candidato a commit -- que e vazamento, nao desordem.
        """
        assert BANCO_PADRAO.as_posix() == ".sparkforge/local/codeintel/graph.sqlite3"
