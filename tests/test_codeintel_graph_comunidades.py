"""`comunidades()` e `nos_por_grau()`: agrupamento local e grau observado.

Corpus SINTETICO pela mesma razao de `test_codeintel_graph_caminho.py`: as duas
funcoes se definem pela topologia, e provar "dois grupos separados viram duas
comunidades" exige um grafo com dois grupos separados.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge.codeintel.graph import (
    _ALGORITMO_DE_COMUNIDADE,
    _rotulo_mais_frequente,
    comunidades,
    nos_por_grau,
)
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.search import buscar


def _arvore(tmp_path: Path, fonte: str) -> Path:
    (tmp_path / "job.py").write_text(fonte, encoding="utf-8")
    banco = tmp_path / "indice.sqlite3"
    indexar(tmp_path, banco)
    return banco


def _nomes(comunidade) -> set[str]:
    return {no.name for no in comunidade.nos}


# Dois grupos que NAO se tocam: `a1<->a2<->a3` de um lado, `b1<->b2` do outro.
DOIS_GRUPOS = """
def a3():
    return 3


def a2():
    return a3()


def a1():
    return a2()


def b2():
    return 2


def b1():
    return b2()
"""


def test_grupos_desconexos_viram_comunidades_diferentes(tmp_path):
    banco = _arvore(tmp_path, DOIS_GRUPOS)
    particao = comunidades(banco)
    grupos = [_nomes(c) for c in particao.comunidades]
    assert {"a1", "a2", "a3"} in grupos
    assert {"b1", "b2"} in grupos


def test_a_particao_e_reproduzivel(tmp_path):
    """O que este modulo garante e reprodutibilidade, nunca unicidade.

    Propagacao de rotulo canonica visita os nos em ordem ALEATORIA e devolve
    particoes diferentes a cada execucao. Aqui a ordem e `_chave_de_ordem`, o
    empate vence o menor rotulo, e o rotulo inicial e o proprio `node_id`.
    """
    banco = _arvore(tmp_path, DOIS_GRUPOS)
    primeira = comunidades(banco)
    for _ in range(4):
        outra = comunidades(banco)
        assert [c.rotulo for c in outra.comunidades] == [
            c.rotulo for c in primeira.comunidades
        ]
        assert [_nomes(c) for c in outra.comunidades] == [
            _nomes(c) for c in primeira.comunidades
        ]


def test_o_algoritmo_sai_no_resultado_e_nao_em_log(tmp_path):
    """Publicar a particao sem o metodo convidaria a lê-la como canonica."""
    particao = comunidades(_arvore(tmp_path, DOIS_GRUPOS))
    assert particao.algoritmo == _ALGORITMO_DE_COMUNIDADE
    assert particao.iteracoes >= 1
    assert particao.convergiu is True


def test_grafo_vazio_CONVERGIU_e_nao_o_contrario(tmp_path):
    """`convergiu: False` num grafo vazio se leria como "o teto foi atingido".

    Nao ha rotulo que possa mudar, entao a propagacao terminou -- e a distincao
    importa porque `False` manda quem le subir `iteracoes_maximas` sobre um
    grafo onde isso nao muda nada.
    """
    (tmp_path / "vazio.txt").write_text("nao e python\n", encoding="utf-8")
    banco = tmp_path / "indice.sqlite3"
    indexar(tmp_path, banco)
    particao = comunidades(banco)
    assert particao.total == 0
    assert particao.convergiu is True


def test_teto_zero_nao_converge_e_diz_isso(tmp_path):
    """Com zero iteracoes cada no fica no proprio rotulo, e isso NAO e convergir."""
    banco = _arvore(tmp_path, DOIS_GRUPOS)
    particao = comunidades(banco, iteracoes_maximas=0)
    assert particao.iteracoes == 0
    assert particao.convergiu is False
    assert particao.total == 5, "sem propagacao, cada no e a propria comunidade"


def test_o_rotulo_e_o_menor_membro_e_nao_a_marca_da_propagacao(tmp_path):
    """A marca depende de por onde a propagacao passou; o menor membro nao."""
    particao = comunidades(_arvore(tmp_path, DOIS_GRUPOS))
    for comunidade in particao.comunidades:
        assert comunidade.rotulo == min(no.node_id for no in comunidade.nos)


def test_todo_no_cai_em_exatamente_uma_comunidade(tmp_path):
    banco = _arvore(tmp_path, DOIS_GRUPOS)
    particao = comunidades(banco)
    ids = [no.node_id for c in particao.comunidades for no in c.nos]
    assert len(ids) == len(set(ids)), "no em duas comunidades"
    assert len(ids) == 5


def test_as_comunidades_saem_da_maior_para_a_menor(tmp_path):
    particao = comunidades(_arvore(tmp_path, DOIS_GRUPOS))
    tamanhos = [c.tamanho for c in particao.comunidades]
    assert tamanhos == sorted(tamanhos, reverse=True)


class TestOEmpate:
    def test_o_menor_rotulo_vence(self):
        """Sem este desempate, a escolha dependeria da ordem de insercao."""
        assert _rotulo_mais_frequente(["b", "a"]) == "a"
        assert _rotulo_mais_frequente(["z", "z", "a"]) == "z"

    def test_sem_vizinho_nao_ha_escolha(self):
        assert _rotulo_mais_frequente([]) is None


ESTRELA = """
def util(x):
    return x


def um():
    return util(1)


def dois():
    return util(2)


def tres():
    return util(3)
"""


def test_o_no_de_maior_grau_sai_primeiro(tmp_path):
    banco = _arvore(tmp_path, ESTRELA)
    medidos = nos_por_grau(banco, 4)
    assert medidos[0].no.name == "util"
    assert medidos[0].grau_de_entrada == 3
    assert medidos[0].grau_de_saida == 0


def test_grau_e_a_soma_das_duas_direcoes(tmp_path):
    medidos = nos_por_grau(_arvore(tmp_path, ESTRELA), 4)
    for medida in medidos:
        assert medida.grau == medida.grau_de_entrada + medida.grau_de_saida


def test_o_limite_corta_e_zero_fecha_a_porta(tmp_path):
    banco = _arvore(tmp_path, ESTRELA)
    assert len(nos_por_grau(banco, 2)) == 2
    assert nos_por_grau(banco, 0) == []
    assert nos_por_grau(banco, -1) == []


def test_a_ordem_desempata_e_nao_fica_por_conta_do_sqlite(tmp_path):
    """`um`, `dois` e `tres` tem grau 1 cada. Sem desempate, a ordem entre eles
    seria a que o SQLite achar mais barata -- e um golden sobre esta lista
    falharia de forma INTERMITENTE, que e pior que falhar sempre."""
    banco = _arvore(tmp_path, ESTRELA)
    primeira = [m.no.node_id for m in nos_por_grau(banco, 4)]
    for _ in range(4):
        assert [m.no.node_id for m in nos_por_grau(banco, 4)] == primeira


def test_o_nome_nao_e_god_node_e_a_escolha_e_deliberada():
    """'No-deus' e veredito; grau e medida.

    Um simbolo de grau alto pode ser um utilitario bem fatorado, e chama-lo de
    defeito por causa do grau seria julgamento sem fonte -- o mesmo que o veto
    V-BR-3 recusa para fan-in. Este teste existe para que a renomeacao "obvia"
    para `god_nodes` tenha de passar por cima de uma decisao escrita.
    """
    from sparkforge.codeintel import graph

    assert not hasattr(graph, "god_nodes")
    assert hasattr(graph, "nos_por_grau")


def test_recursao_direta_nao_conta_para_comunidade(tmp_path):
    """Um no e sempre do proprio grupo; a auto-aresta so daria peso extra."""
    banco = _arvore(
        tmp_path,
        "def sozinha(n):\n    return sozinha(n - 1) if n else 0\n",
    )
    particao = comunidades(banco)
    assert particao.total == 1
    assert particao.comunidades[0].tamanho == 1


def test_o_indice_precisa_ter_o_simbolo_para_a_medida_valer(tmp_path):
    """Guarda do proprio corpus: se `indexar` parar de ver estes simbolos, os
    testes acima passariam a medir um grafo vazio e continuariam verdes."""
    banco = _arvore(tmp_path, ESTRELA)
    assert [a for a in buscar(banco, "util") if a.name == "util"]
