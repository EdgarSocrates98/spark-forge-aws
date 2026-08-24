"""A referencia bruta, antes de saber a quem aponta.

POR QUE ESTE ARQUIVO NAO TESTA RESOLUCAO
----------------------------------------
`extrair_referencias` devolve o que o AST VE. Se ele ja tentasse resolver, uma
referencia que ninguem resolveu seria indistinguivel de uma que ninguem
extraiu, e a taxa de resolucao -- que e o numero que diz se o grafo vale alguma
coisa -- nao teria denominador. Toda afirmacao daqui e sobre o que foi VISTO.
"""

import ast
import dataclasses
import inspect

import pytest

from sparkforge.codeintel import refs
from sparkforge.codeintel.extract import VisitanteComEscopo
from sparkforge.codeintel.refs import Referencia, extrair_referencias


def test_extrai_chamada_simples():
    refs_vistas = extrair_referencias("def a():\n    b()\n", "m.py")
    assert ("a", "b", "calls") in {
        (r.origem_qualificada, r.nome, r.kind) for r in refs_vistas
    }


def test_extrai_chamada_com_receptor():
    (r,) = [
        x
        for x in extrair_referencias("def a():\n    df.filtrar()\n", "m.py")
        if x.nome == "filtrar"
    ]
    assert r.receptor == "df"


def test_receptor_de_cadeia_guarda_a_cadeia_inteira():
    """`spark.read.parquet()` tem receptor `spark.read`, e nao `read`.

    O receptor existe para `resolve.py` ter com o que desambiguar um nome de
    metodo comum. Guardar so o ultimo segmento jogaria fora justamente a parte
    que identifica de onde o objeto veio.
    """
    (r,) = [
        x
        for x in extrair_referencias("spark.read.parquet('p')\n", "m.py")
        if x.nome == "parquet"
    ]
    assert r.receptor == "spark.read"


def test_chamada_sem_receptor_tem_receptor_vazio():
    """String vazia e nao `None`: a coluna do banco e NOT NULL e o campo e str.

    Sem esta afirmacao, `receptor` poderia virar `None` num caminho e `""`
    noutro, e todo consumidor precisaria testar os dois.
    """
    (r,) = [x for x in extrair_referencias("def a():\n    b()\n", "m.py") if x.nome == "b"]
    assert r.receptor == ""


def test_extrai_import_e_from_import():
    refs_vistas = extrair_referencias("import os\nfrom pathlib import Path\n", "m.py")
    nomes = {(r.nome, r.kind) for r in refs_vistas}
    assert ("os", "imports") in nomes
    assert ("pathlib.Path", "imports") in nomes


def test_import_com_alias_guarda_o_nome_importado_e_nao_o_apelido():
    """`import numpy as np` referencia `numpy`. `np` e nome local, nao alvo.

    Uma aresta para `np` nao acharia nada no indice, porque `np` nao existe em
    lugar nenhum -- e a referencia cairia em `unresolved_refs` por um motivo
    inventado aqui, e nao por o alvo ser mesmo externo.
    """
    nomes = {r.nome for r in extrair_referencias("import numpy as np\n", "m.py")}
    assert nomes == {"numpy"}


def test_import_relativo_preserva_os_pontos():
    """`from .irmao import f` e `from irmao import f` apontam para lugares
    diferentes, e o ponto e a unica coisa que os separa.

    Perder o ponto faria uma referencia relativa resolver para o modulo de topo
    de mesmo nome -- aresta errada, e nao aresta ausente. Errada e pior.
    """
    nomes = {
        r.nome
        for r in extrair_referencias("from .irmao import f\nfrom ..pai import g\n", "p/m.py")
    }
    assert nomes == {".irmao.f", "..pai.g"}


def test_origem_e_o_escopo_que_contem_a_chamada():
    """Sem isso a aresta sai do modulo, nao da funcao, e `chamadores` mente."""
    (r,) = [
        x
        for x in extrair_referencias("class P:\n    def m(self):\n        alvo()\n", "m.py")
        if x.nome == "alvo"
    ]
    assert r.origem_qualificada == "P.m"


def test_origem_de_funcao_aninhada_e_a_mais_interna():
    """A pilha nao pode parar no primeiro nivel.

    `chamadores` de `alvo` tem que dar `f.g` e nao `f`: quem chama e a funcao
    interna, e apontar para a externa poe a aresta no lugar errado.
    """
    fonte = "def f():\n    def g():\n        alvo()\n"
    (r,) = [x for x in extrair_referencias(fonte, "m.py") if x.nome == "alvo"]
    assert r.origem_qualificada == "f.g"


def test_chamada_no_topo_do_modulo_tem_origem_do_modulo():
    (r,) = [x for x in extrair_referencias("alvo()\n", "pacote/m.py") if x.nome == "alvo"]
    assert r.origem_qualificada == "pacote.m"


def test_origem_de_modulo_init_e_o_pacote():
    """`pacote/__init__.py` E o pacote, e `pacote.__init__` nao existe.

    Sem isso a origem de toda chamada de topo em `__init__.py` seria um nome que
    nenhum import escreve, e nenhuma delas casaria com nada.
    """
    (r,) = [
        x for x in extrair_referencias("alvo()\n", "pacote/__init__.py") if x.nome == "alvo"
    ]
    assert r.origem_qualificada == "pacote"


def test_caminho_com_barra_invertida_da_o_mesmo_modulo():
    """A varredura entrega POSIX, mas quem chama a mao no Windows nao sabe disso.

    Duas origens diferentes para o mesmo arquivo dariam duas contagens de
    chamador para a mesma funcao, calado.
    """
    (barra,) = [x for x in extrair_referencias("alvo()\n", "pacote/m.py") if x.nome == "alvo"]
    (invertida,) = [
        x for x in extrair_referencias("alvo()\n", "pacote\\m.py") if x.nome == "alvo"
    ]
    assert barra.origem_qualificada == invertida.origem_qualificada == "pacote.m"


def test_chamada_aninhada_conta_as_duas():
    """`a(b())` sao duas referencias, e a de dentro nao pode sumir.

    Registrar a chamada e parar de descer perderia todo argumento que e chamada
    -- e `f(g(x))` e a forma mais comum de composicao que existe.
    """
    nomes = [r.nome for r in extrair_referencias("def m():\n    a(b())\n", "m.py")]
    assert sorted(nomes) == ["a", "b"]


def test_a_mesma_chamada_duas_vezes_na_linha_da_duas_referencias():
    """`f(g(), g())` chama `g` duas vezes, e a contagem tem que dizer duas.

    E o caso que justifica `edges` sem chave unica: as duas linhas tem source,
    target, kind e line iguais.
    """
    nomes = [r.nome for r in extrair_referencias("def m():\n    f(g(), g())\n", "m.py")]
    assert nomes.count("g") == 2


def test_linha_e_a_da_chamada_e_nao_a_da_definicao():
    """Sem a linha certa, a evidencia da aresta aponta para o lugar errado."""
    fonte = "def m():\n    pass\n\n\ndef n():\n    alvo()\n"
    (r,) = [x for x in extrair_referencias(fonte, "m.py") if x.nome == "alvo"]
    assert r.line == 6


def test_chamada_sem_nome_nao_vira_referencia():
    """`tabela['k']()` nao tem nome para referenciar, e inventar um seria pior.

    Ponto cego assumido: nao ha nome a resolver, entao nao ha o que registrar
    nem em `edges` nem em `unresolved_refs`. Afirmado para que a ausencia seja
    escolha e nao esquecimento.
    """
    assert extrair_referencias("def m():\n    tabela['k']()\n", "m.py") == []


def test_sintaxe_invalida_devolve_vazio():
    assert extrair_referencias("def (:::", "m.py") == []


def test_referencia_e_imutavel():
    """Ela e evidencia. Consumidor que a corrige em vez de registrar novo fato
    apagaria o que o AST viu, e o campo de evidencia nao pode ser editavel."""
    (r,) = [x for x in extrair_referencias("alvo()\n", "m.py") if x.nome == "alvo"]
    assert isinstance(r, Referencia)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.nome = "outro"  # type: ignore[misc]


# --------------------------------------------------------------------------
# O gate estrutural: uma pilha de escopo so.
# --------------------------------------------------------------------------


def test_refs_usa_a_pilha_de_escopo_de_extract_e_nao_uma_propria():
    """Duas pilhas de escopo divergiriam, e a divergencia seria calada.

    J0 pagou esse preco com quatro detectores de segredo que discordavam entre
    si, e o gate por AST de `tests/test_facts_secrets.py` existe para impedir o
    quinto. Este e o mesmo gate para a pilha de escopo: `refs.py` pode HERDAR
    de `VisitanteComEscopo`, e nao pode reescrever `visit_ClassDef`,
    `visit_FunctionDef` nem `visit_AsyncFunctionDef` -- que sao os tres metodos
    onde a pilha e mantida.

    Por AST e nao por comportamento porque uma copia da pilha passaria em todos
    os testes de comportamento acima. E exatamente esse o defeito que o gate
    pega: a copia que funciona hoje e diverge no proximo commit.
    """
    arvore = ast.parse(inspect.getsource(refs))
    reescritos = {
        no.name
        for no in ast.walk(arvore)
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        and no.name in {"visit_ClassDef", "visit_FunctionDef", "visit_AsyncFunctionDef"}
    }
    assert not reescritos, f"pilha de escopo duplicada em refs.py: {sorted(reescritos)}"

    visitantes = [
        objeto
        for objeto in vars(refs).values()
        if inspect.isclass(objeto)
        and issubclass(objeto, ast.NodeVisitor)
        and objeto is not ast.NodeVisitor
    ]
    assert visitantes, "refs.py nao tem visitante -- o gate estaria vazio"
    for visitante in visitantes:
        assert issubclass(visitante, VisitanteComEscopo), (
            f"{visitante.__name__} nao herda a pilha de escopo compartilhada"
        )
