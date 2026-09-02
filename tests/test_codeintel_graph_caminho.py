"""`caminho()` e `estatisticas()`: o caminho mais curto, e o tamanho do grafo.

O corpus e SINTETICO e escrito por teste, e nao uma fixture do repositorio. A
razao e que estas funcoes se definem pela TOPOLOGIA -- caminho unico, dois
caminhos empatados, ciclo, ramo morto --, e uma fixture real tem a topologia que
tem: provar "entre dois caminhos minimos ele escolhe o mesmo sempre" exige um
grafo com dois caminhos minimos, e nenhum corpus de job PySpark garante um.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.codeintel.graph import (
    _PROFUNDIDADE_DE_CAMINHO,
    caminho,
    estatisticas,
)
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.search import buscar


def _arvore(tmp_path: Path, fonte: str) -> Path:
    """Escreve `fonte` como `job.py`, indexa, e devolve o banco."""
    (tmp_path / "job.py").write_text(fonte, encoding="utf-8")
    banco = tmp_path / "indice.sqlite3"
    indexar(tmp_path, banco)
    return banco


def _id(banco: Path, nome: str) -> str:
    achados = [a for a in buscar(banco, nome) if a.name == nome]
    assert achados, f"simbolo {nome!r} nao entrou no indice"
    return achados[0].node_id


CADEIA = """
def folha():
    return 1


def meio():
    return folha()


def raiz():
    return meio()
"""


def test_o_caminho_sai_em_ordem_de_percurso(tmp_path):
    banco = _arvore(tmp_path, CADEIA)
    achado = caminho(banco, _id(banco, "raiz"), _id(banco, "folha"))
    assert [n.name for n in achado.nos] == ["raiz", "meio", "folha"]
    assert achado.saltos == 2
    assert achado.existe is True
    assert achado.truncado is False


def test_depth_e_a_posicao_no_caminho(tmp_path):
    """E nao a profundidade em que a travessia alcancou o no.

    Os dois numeros coincidem aqui de propósito; reescrever `depth` na
    reconstrucao e o que garante que continuem coincidindo se a travessia mudar.
    """
    banco = _arvore(tmp_path, CADEIA)
    achado = caminho(banco, _id(banco, "raiz"), _id(banco, "folha"))
    assert [n.depth for n in achado.nos] == [0, 1, 2]


def test_o_sentido_e_descendo_e_o_inverso_nao_existe(tmp_path):
    """`caminho(a, b)` desce. Para subir, trocam-se os argumentos.

    Este teste prende que a direcao NAO e simetrica -- se um dia alguem
    "melhorar" a busca para tentar os dois sentidos, `caminho(folha, raiz)`
    passaria a achar algo e a semantica mudaria em silencio.
    """
    banco = _arvore(tmp_path, CADEIA)
    invertido = caminho(banco, _id(banco, "folha"), _id(banco, "raiz"))
    assert invertido.existe is False


def test_origem_igual_a_destino_e_um_no_e_zero_saltos(tmp_path):
    """'Como x chega em x' tem resposta, e ela e 'ja esta la'."""
    banco = _arvore(tmp_path, CADEIA)
    achado = caminho(banco, _id(banco, "meio"), _id(banco, "meio"))
    assert [n.name for n in achado.nos] == ["meio"]
    assert achado.saltos == 0
    assert achado.truncado is False


def test_no_fora_do_indice_devolve_vazio_sem_truncado(tmp_path):
    """Ausencia de no e resposta, nao recusa por teto."""
    banco = _arvore(tmp_path, CADEIA)
    achado = caminho(banco, _id(banco, "raiz"), "node_inventado")
    assert achado.existe is False
    assert achado.truncado is False


DESCONEXO = """
def isolada():
    return 0


def a():
    return b()


def b():
    return 1
"""


def test_grafo_esgotado_antes_do_teto_nao_marca_truncado(tmp_path):
    """A terceira resposta negativa: ausencia AFIRMADA, e nao recusa.

    Colapsar isto com o caso truncado faria "nao procurei fundo o bastante" ser
    lido como "nao existe" -- que e a leitura mais forte das duas, e a errada.
    """
    banco = _arvore(tmp_path, DESCONEXO)
    achado = caminho(banco, _id(banco, "a"), _id(banco, "isolada"))
    assert achado.existe is False
    assert achado.truncado is False, (
        "o grafo esgotou em 1 salto, muito antes do teto de "
        f"{_PROFUNDIDADE_DE_CAMINHO}: marcar `truncado` aqui afirmaria que a "
        "busca parou por limite quando ela parou por falta de aresta"
    )


LONGA = """
def n5():
    return 5


def n4():
    return n5()


def n3():
    return n4()


def n2():
    return n3()


def n1():
    return n2()


def n0():
    return n1()
"""


def test_teto_atingido_marca_truncado(tmp_path):
    """A segunda resposta negativa, e a que mais importa distinguir."""
    banco = _arvore(tmp_path, LONGA)
    achado = caminho(banco, _id(banco, "n0"), _id(banco, "n5"), profundidade=2)
    assert achado.existe is False
    assert achado.truncado is True
    assert achado.profundidade_maxima == 2


def test_o_mesmo_par_com_teto_suficiente_acha(tmp_path):
    """O contrafactual do teste acima: o caminho EXISTE, so nao cabia em 2."""
    banco = _arvore(tmp_path, LONGA)
    achado = caminho(banco, _id(banco, "n0"), _id(banco, "n5"), profundidade=5)
    assert achado.existe is True
    assert achado.saltos == 5


def test_profundidade_negativa_fecha_a_porta(tmp_path):
    """Valor absurdo fecha a porta, nao abre outra -- como `buscar` com limite <= 0."""
    banco = _arvore(tmp_path, CADEIA)
    achado = caminho(banco, _id(banco, "raiz"), _id(banco, "folha"), profundidade=-1)
    assert achado.existe is False
    assert achado.truncado is False


CICLO = """
def par(n):
    return impar(n - 1)


def impar(n):
    return par(n - 1)


def entrada(n):
    return par(n)
"""


def test_ciclo_nao_impede_o_caminho_nem_o_faz_repetir(tmp_path):
    """Recursao mutua e aresta legitima; o conjunto de visitados so evita reemitir."""
    banco = _arvore(tmp_path, CICLO)
    achado = caminho(banco, _id(banco, "entrada"), _id(banco, "impar"))
    assert [n.name for n in achado.nos] == ["entrada", "par", "impar"]
    ids = [n.node_id for n in achado.nos]
    assert len(ids) == len(set(ids)), "no repetido no caminho"


EMPATE = """
def destino():
    return 0


def esquerda():
    return destino()


def direita():
    return destino()


def topo(flag):
    return esquerda() if flag else direita()
"""


def test_entre_caminhos_minimos_empatados_a_escolha_e_estavel(tmp_path):
    """Determinismo NAO e unicidade, e o teste prende o primeiro.

    Ha dois caminhos de 2 saltos (`topo -> esquerda -> destino` e
    `topo -> direita -> destino`). A funcao devolve UM, e o que se exige aqui e
    que devolva SEMPRE o mesmo -- sem isso, um golden que cite o caminho falharia
    de forma intermitente, que e pior que falhar sempre.
    """
    banco = _arvore(tmp_path, EMPATE)
    origem, destino = _id(banco, "topo"), _id(banco, "destino")
    primeiro = caminho(banco, origem, destino)
    assert primeiro.saltos == 2
    for _ in range(4):
        assert [n.node_id for n in caminho(banco, origem, destino).nos] == [
            n.node_id for n in primeiro.nos
        ]


def test_o_caminho_empatado_escolhido_e_o_de_menor_chave_de_ordem(tmp_path):
    """Qual dos dois vence esta declarado, e nao e acidente da ordem do SQLite.

    `esquerda` e definida ANTES de `direita` no fonte, entao tem `start_line`
    menor, e `_chave_de_ordem` a poe primeiro. Se um dia a escolha mudar, este
    teste diz que mudou -- e nao um golden que ninguem sabe reler.
    """
    banco = _arvore(tmp_path, EMPATE)
    achado = caminho(banco, _id(banco, "topo"), _id(banco, "destino"))
    assert [n.name for n in achado.nos] == ["topo", "esquerda", "destino"]


def test_estatisticas_conta_as_quatro_tabelas(tmp_path):
    banco = _arvore(tmp_path, CADEIA)
    medida = estatisticas(banco)
    assert medida.arquivos == 1
    assert medida.nos == 3
    assert medida.arestas_resolvidas >= 2
    assert medida.referencias_nao_resolvidas >= 0


def test_a_taxa_de_resolucao_de_um_indice_vazio_e_zero_e_nao_um(tmp_path):
    """`1.0` num banco sem conteudo seria a forma mais silenciosa de afirmar
    cobertura total sobre nada."""
    (tmp_path / "vazio.txt").write_text("nao e python\n", encoding="utf-8")
    banco = tmp_path / "indice.sqlite3"
    indexar(tmp_path, banco)
    medida = estatisticas(banco)
    assert medida.nos == 0
    assert medida.taxa_de_resolucao == 0.0


def test_a_taxa_sai_junto_com_a_contagem_de_nao_resolvidas(tmp_path):
    """Publicar arestas sem as nao resolvidas faria o indice parecer completo.

    Medido sobre `sparkforge/codeintel/` em 2026-09-02: 299 arestas contra 517
    referencias nao resolvidas -- taxa de 0.366. Um relatorio que citasse so as
    299 sugeriria cobertura que nao ha.
    """
    banco = _arvore(tmp_path, CADEIA)
    medida = estatisticas(banco)
    tentativas = medida.arestas_resolvidas + medida.referencias_nao_resolvidas
    assert medida.taxa_de_resolucao == pytest.approx(
        medida.arestas_resolvidas / tentativas
    )


def test_estatisticas_nao_levanta_em_banco_de_schema_mais_velho(tmp_path):
    """Tabela ausente e 0, nao excecao: a funcao descreve o indice que HA."""
    import sqlite3

    banco = tmp_path / "antigo.sqlite3"
    conexao = sqlite3.connect(banco)
    conexao.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
    conexao.commit()
    conexao.close()

    medida = estatisticas(banco)
    assert medida.arquivos == 0
    assert medida.nos == 0
    assert medida.arestas_resolvidas == 0
