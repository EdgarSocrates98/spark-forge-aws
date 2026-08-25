"""Indexacao ponta a ponta, incluindo sobre o proprio repositorio.

O teste sobre o proprio repo nao e vaidade: ele e o unico que exercita a escala
real e o unico que pegaria uma regressao de desempenho ou um arquivo do
repositorio que o extractor nao aguenta.
"""

import pathlib
import sqlite3

from sparkforge.codeintel.index import indexar


def test_indexa_arvore_pequena(tmp_path):
    (tmp_path / "jobs").mkdir()
    (tmp_path / "jobs" / "etl.py").write_text(
        "class Pipeline:\n    def executar(self):\n        pass\n", encoding="utf-8"
    )
    (tmp_path / "jobs" / "util.py").write_text("def ajudar():\n    pass\n", encoding="utf-8")
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.arquivos == 2
    assert resultado.nos >= 3


def test_caminho_gravado_e_relativo_a_raiz(tmp_path):
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    indexar(tmp_path, tmp_path / "graph.sqlite3")

    conexao = sqlite3.connect(tmp_path / "graph.sqlite3")
    caminhos = [linha[0] for linha in conexao.execute("SELECT path FROM files")]
    conexao.close()
    assert caminhos == ["a.py"]
    for caminho in caminhos:
        assert not pathlib.Path(caminho).is_absolute()


def test_reindexar_sem_mudanca_produz_os_mesmos_ids(tmp_path):
    """Id estavel entre execucoes -- a pre-condicao da fase incremental."""
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")

    def ids():
        indexar(tmp_path, tmp_path / "graph.sqlite3")
        conexao = sqlite3.connect(tmp_path / "graph.sqlite3")
        achados = sorted(linha[0] for linha in conexao.execute("SELECT id FROM nodes"))
        conexao.close()
        return achados

    assert ids() == ids()


def test_reindexar_nao_duplica_nem_deixa_no_de_arquivo_apagado(tmp_path):
    """J3 reindexa tudo; o que sumiu do disco tem que sumir do indice.

    Sem a limpeza, a segunda passada deixaria `antigo.f` respondendo busca sobre
    um arquivo que nao existe mais -- e `symbols_fts` e tabela virtual, entao o
    `ON DELETE CASCADE` nao a alcanca e ela precisa ser limpa na mao.
    """
    banco = tmp_path / "graph.sqlite3"
    (tmp_path / "antigo.py").write_text("def f():\n    pass\n", encoding="utf-8")
    indexar(tmp_path, banco)

    (tmp_path / "antigo.py").unlink()
    (tmp_path / "novo.py").write_text("def g():\n    pass\n", encoding="utf-8")
    indexar(tmp_path, banco)

    conexao = sqlite3.connect(banco)
    caminhos = [linha[0] for linha in conexao.execute("SELECT path FROM files")]
    nomes = [linha[0] for linha in conexao.execute("SELECT qualified_name FROM nodes")]
    do_fts = [linha[0] for linha in conexao.execute("SELECT qualified_name FROM symbols_fts")]
    conexao.close()

    assert caminhos == ["novo.py"]
    assert nomes == ["g"]
    assert do_fts == ["g"]


def test_a_denylist_da_varredura_vale_no_indice(tmp_path):
    """O indice herda a fronteira de leitura da fase J0, nao a reimplementa."""
    (tmp_path / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    ruido = tmp_path / ".venv" / "lib"
    ruido.mkdir(parents=True)
    (ruido / "terceiro.py").write_text("def g():\n    pass\n", encoding="utf-8")
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.arquivos == 1


def test_arquivo_que_nao_parseia_e_contado_e_nao_derruba(tmp_path):
    """Ponto cego CONTADO -- que e o que o distingue de ponto cego silencioso."""
    (tmp_path / "bom.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (tmp_path / "ruim.py").write_text("def (:::\n", encoding="utf-8")
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    assert resultado.arquivos == 2
    assert resultado.ilegiveis == 1
    assert resultado.nos == 1


def test_metodos_homonimos_em_classes_diferentes_nao_se_sobrescrevem(tmp_path):
    """`node_id` tem que receber o nome QUALIFICADO, e quem garante isso e aqui.

    Medido no repositorio: `adapters/platforms/targets.py` tem quatro
    `platform_name(self)` em quatro classes. Alimentar `node_id` com o nome
    simples da aos quatro caminho, kind, nome e assinatura iguais -- mesmo id --
    e o `INSERT OR REPLACE` deixaria UM no de quatro, sem que nada acuse.
    """
    (tmp_path / "alvos.py").write_text(
        "class A:\n    def nome(self):\n        pass\n\n\n"
        "class B:\n    def nome(self):\n        pass\n",
        encoding="utf-8",
    )
    resultado = indexar(tmp_path, tmp_path / "graph.sqlite3")
    conexao = sqlite3.connect(tmp_path / "graph.sqlite3")
    metodos = sorted(
        linha[0]
        for linha in conexao.execute("SELECT qualified_name FROM nodes WHERE kind = 'method'")
    )
    distintos = conexao.execute("SELECT COUNT(DISTINCT id) FROM nodes").fetchone()[0]
    conexao.close()
    assert metodos == ["A.nome", "B.nome"]
    assert distintos == resultado.nos == 4


def test_corpo_da_funcao_nao_chega_ao_banco(tmp_path):
    """INV-010: o indice guarda ONDE, e quem quer o codigo le o arquivo."""
    (tmp_path / "a.py").write_text(
        'def conectar(senha="hunter2"):\n    token = "hunter2"\n    return token\n',
        encoding="utf-8",
    )
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    assert b"hunter2" not in banco.read_bytes()

    # A assinatura SOBREVIVE ao banco -- e ela que faz o indice valer mais que
    # uma lista de nomes. Sem esta afirmacao, gravar coluna vazia passaria pela
    # afirmacao de cima, que so exige a ausencia do segredo.
    conexao = sqlite3.connect(banco)
    (assinatura,) = conexao.execute(
        "SELECT normalized_signature FROM nodes WHERE qualified_name = 'conectar'"
    ).fetchone()
    conexao.close()
    assert assinatura == "conectar(senha=<literal>)"


def test_indexa_o_proprio_repositorio(tmp_path):
    """Limites FROUXOS de proposito.

    Um numero exato quebraria a cada arquivo novo no repositorio, e o que
    interessa aqui e a ordem de grandeza: algumas centenas de arquivos, alguns
    milhares de nos, e ilegivel na casa da unidade e nao da dezena.
    """
    raiz = pathlib.Path(__file__).resolve().parent.parent
    resultado = indexar(raiz, tmp_path / "graph.sqlite3")
    assert resultado.arquivos > 300, resultado.arquivos
    assert resultado.nos > 4000, resultado.nos
    assert resultado.ilegiveis < resultado.arquivos // 10, (
        f"{resultado.ilegiveis} arquivos nao parsearam -- investigue antes de aceitar"
    )
