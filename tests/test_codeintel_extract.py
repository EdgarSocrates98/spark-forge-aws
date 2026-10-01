"""Extracao de no a partir do AST, e o que o indice NAO guarda.

O corpo da funcao nao entra no banco (INV-010 da SPEC): o indice guarda posicao,
e quem precisa do codigo le o arquivo. Guardar corpo faria o banco virar copia
do repositorio, com o custo de disco e o risco de vazamento que vem junto.
"""

import textwrap

from sparkforge.codeintel.extract import extrair_nos, extrair_nos_ou_none


def _nos(fonte: str, caminho: str = "jobs/etl.py"):
    return extrair_nos(textwrap.dedent(fonte), caminho)


def test_extrai_funcao_classe_e_metodo():
    nos = _nos("""
        class Pipeline:
            def executar(self, df):
                return df

        def principal():
            pass
    """)
    por_kind = {(n.kind, n.qualified_name) for n in nos}
    assert ("class", "Pipeline") in por_kind
    assert ("method", "Pipeline.executar") in por_kind
    assert ("function", "principal") in por_kind


def test_posicao_permite_achar_o_codigo_depois():
    (no,) = [n for n in _nos("""
        def principal():
            pass
    """) if n.kind == "function"]
    assert no.start_line == 2
    assert no.end_line >= no.start_line


def test_end_line_cobre_o_corpo_inteiro():
    """`end_line == start_line` seria posicao inventada, nao posicao medida.

    O teste acima aceita a igualdade porque uma funcao de uma linha so a tem.
    Aqui o corpo tem tres linhas, entao o fim TEM que passar do inicio -- e sem
    esta afirmacao um `end_line = start_line` passaria os dois testes.
    """
    (no,) = [n for n in _nos("""
        def longa():
            a = 1
            b = 2
            return a + b
    """) if n.kind == "function"]
    assert no.start_line == 2
    assert no.end_line == 5


def test_nenhum_no_carrega_corpo():
    nos = _nos("""
        def com_segredo():
            senha = "hunter2"
            return senha
    """)
    for no in nos:
        assert "hunter2" not in repr(no), "corpo vazou para o no"


def test_default_literal_nao_entra_na_assinatura():
    (no,) = [n for n in _nos("""
        def conectar(usuario, senha="hunter2"):
            pass
    """) if n.kind == "function"]
    assert "hunter2" not in no.normalized_signature
    assert "senha=<literal>" in no.normalized_signature


def test_arquivo_que_nao_parseia_nao_derruba_a_extracao():
    """Sintaxe invalida e ponto cego, nao erro fatal.

    Um repositorio de cliente tem arquivo com sintaxe de outra versao de Python,
    template com placeholder, arquivo pela metade. Derrubar a indexacao inteira
    por causa de um seria trocar cobertura parcial por nenhuma.
    """
    nos = extrair_nos("def (:::", "quebrado.py")
    assert nos == []


def test_funcao_aninhada_ganha_nome_qualificado_do_escopo():
    nos = _nos("""
        def externa():
            def interna():
                pass
    """)
    qualificados = {n.qualified_name for n in nos}
    assert "externa.interna" in qualificados


def test_metodo_de_classe_aninhada_carrega_a_pilha_inteira():
    """Duas classes com metodo homonimo so se distinguem pelo escopo completo.

    Medido no repositorio: `adapters/platforms/targets.py` tem quatro
    `platform_name(self)` em quatro classes. Com a pilha desligada os quatro
    viram `platform_name` e produzem o mesmo `node_id`, e o indice perde tres
    nos por sobrescrita, sem que nada acuse.
    """
    nos = _nos("""
        class Alvo:
            def nome(self):
                pass

        class Outro:
            def nome(self):
                pass
    """)
    qualificados = {n.qualified_name for n in nos if n.kind == "method"}
    assert qualificados == {"Alvo.nome", "Outro.nome"}


def test_funcao_dentro_de_metodo_e_funcao_e_nao_metodo():
    """So o escopo IMEDIATO decide entre metodo e funcao."""
    nos = {n.qualified_name: n.kind for n in _nos("""
        class Pipeline:
            def executar(self):
                def auxiliar():
                    pass
    """)}
    assert nos["Pipeline.executar"] == "method"
    assert nos["Pipeline.executar.auxiliar"] == "function"


def test_def_dentro_de_if_nao_e_perdido():
    """`if TYPE_CHECKING:` e `try/except ImportError` sao ordinarios.

    Percorrer so o `.body` de def e class perderia estes simbolos sem sinal.
    """
    qualificados = {n.qualified_name for n in _nos("""
        import sys

        if sys.version_info >= (3, 11):
            def compat():
                pass
        else:
            class Compat:
                def usar(self):
                    pass
    """)}
    assert "compat" in qualificados
    assert "Compat.usar" in qualificados


def test_metodo_assincrono_entra():
    """`async def` e um tipo de no proprio e nao herda de FunctionDef."""
    nos = {n.qualified_name: n.kind for n in _nos("""
        class Cliente:
            async def buscar(self):
                pass
    """)}
    assert nos["Cliente.buscar"] == "method"


def test_lista_vazia_nao_distingue_ilegivel_de_sem_simbolo():
    """`indexar` conta `ilegiveis`, e `[]` sozinho nao serve de sinal.

    Modulo de constantes e modulo que nao parseia produzem os dois `[]`. Medido
    na arvore da fase J3: 45 dos 378 arquivos `.py` que a varredura enxerga nao
    tem nenhuma classe nem funcao, contra UM unico que nao parseia
    (`fixtures/graph/fonte_que_nao_compila/input/carga_quebrada.py`).
    """
    assert extrair_nos_ou_none("SEGREDO = 1\n", "constantes.py") == []
    assert extrair_nos_ou_none("def (:::", "quebrado.py") is None
