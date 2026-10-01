"""Travessia do grafo: chamadores, chamados e raio de impacto.

AS TRES AFIRMACOES QUE ESTE ARQUIVO EXISTE PARA PRENDER
-------------------------------------------------------
1. O CONJUNTO DE VISITADOS. `a -> b -> a` e ciclo, e sem visitados a travessia
   reemite os mesmos dois nos a cada salto ate o teto. Se
   `test_ciclo_nao_causa_recursao_infinita` passar com o conjunto removido, a
   travessia nao garante o que ela existe para garantir.
2. A PROFUNDIDADE. Ignora-la faz `impacto` devolver a componente conexa inteira
   e chamar isso de raio -- o numero deixa de priorizar coisa nenhuma.
3. O DESEMPATE. Ordenar so por profundidade deixa a ordem dentro do nivel por
   conta do SQLite, e um teste assim falharia INTERMITENTEMENTE -- pior que
   falhar sempre, porque some quando alguem vai olhar.

E A QUARTA, QUE E DE `index.py` E NAO DE `graph.py`
---------------------------------------------------
Ate esta tarefa `resolver` produzia arestas que ninguem gravava, e as duas
tabelas ficavam VAZIAS no indice real. Uma travessia sobre tabela vazia devolve
lista vazia sem erro nenhum, e "ninguem chama isto" e indistinguivel de "a
ligacao nunca foi feita". `test_indexar_grava_as_duas_metades` e o que fecha
essa porta.
"""

import sqlite3

from sparkforge.codeintel import graph
from sparkforge.codeintel.db import abrir
from sparkforge.codeintel.graph import chamadores, chamados, impacto
from sparkforge.codeintel.index import indexar


def _indexar(tmp_path, arquivos):
    """Escreve `arquivos` sob `tmp_path`, indexa de verdade e devolve o banco.

    O indice e construido por `indexar` e nao montado a mao pelo mesmo motivo
    que em `test_codeintel_resolve.py`: os ids que a aresta carrega tem que ser
    os MESMOS que `nodes` guarda, e um banco forjado no teste passaria com ids
    que o codigo real nunca produz.
    """
    for nome, fonte in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(fonte, encoding="utf-8")
    banco = tmp_path / "graph.sqlite3"
    resultado = indexar(tmp_path, banco)
    return banco, resultado


def _ids(banco):
    """`{nome_qualificado: node_id}` do banco recem-indexado."""
    conexao = abrir(banco)
    try:
        linhas = conexao.execute("SELECT qualified_name, id FROM nodes").fetchall()
    finally:
        conexao.close()
    return dict(linhas)


def _nomes(nos):
    return [no.qualified_name for no in nos]


# ---------------------------------------------------------------- um salto


def test_chamadores_diretos(tmp_path):
    """Quem chama `alvo` sai; quem so e chamado por ele, nao."""
    banco, _ = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "quem_chama.py": "from alvo import alvo\n\n\ndef chamador():\n    alvo()\n",
        },
    )
    ids = _ids(banco)

    assert _nomes(chamadores(banco, ids["alvo"])) == ["chamador"]
    assert chamadores(banco, ids["chamador"]) == []


def test_chamados_diretos(tmp_path):
    """O espelho: `chamados` desce, `chamadores` sobe, e um nao vira o outro."""
    banco, _ = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "quem_chama.py": "from alvo import alvo\n\n\ndef chamador():\n    alvo()\n",
        },
    )
    ids = _ids(banco)

    assert _nomes(chamados(banco, ids["chamador"])) == ["alvo"]
    assert chamados(banco, ids["alvo"]) == []


def test_chamada_repetida_nao_vira_dois_chamadores(tmp_path):
    """`f()` tres vezes na mesma funcao sao tres ARESTAS e um chamador.

    `edges` nao tem chave unica, de proposito -- tres chamadas sao tres fatos.
    Sem `DISTINCT` na travessia o mesmo no sairia tres vezes, e quem contasse a
    lista publicaria "3 chamadores" para um chamador so.
    """
    banco, resultado = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "tres.py": (
                "from alvo import alvo\n\n\ndef chamador():\n"
                "    alvo()\n    alvo()\n    alvo()\n"
            ),
        },
    )
    ids = _ids(banco)

    assert resultado.arestas == 3
    assert _nomes(chamadores(banco, ids["alvo"])) == ["chamador"]


def test_no_inexistente_devolve_vazio_e_nao_levanta(tmp_path):
    """Id que nao esta no indice e resposta normal depois de um rename."""
    banco, _ = _indexar(tmp_path, {"a.py": "def a():\n    pass\n"})

    assert chamadores(banco, "node_inexistente") == []
    assert chamados(banco, "node_inexistente") == []
    assert impacto(banco, "node_inexistente") == []


# ---------------------------------------------------------------- impacto


def test_impacto_e_transitivo_com_profundidade(tmp_path):
    """`impacto(x, profundidade=2)` alcanca quem chama quem chama x."""
    banco, _ = _indexar(
        tmp_path,
        {
            "n0.py": "def folha():\n    pass\n",
            "n1.py": "from n0 import folha\n\n\ndef meio():\n    folha()\n",
            "n2.py": "from n1 import meio\n\n\ndef topo():\n    meio()\n",
            "n3.py": "from n2 import topo\n\n\ndef acima():\n    topo()\n",
        },
    )
    ids = _ids(banco)

    assert _nomes(impacto(banco, ids["folha"], profundidade=1)) == ["folha", "meio"]
    assert _nomes(impacto(banco, ids["folha"], profundidade=2)) == [
        "folha",
        "meio",
        "topo",
    ]
    # A profundidade CORTA. Sem o corte, `profundidade=2` devolveria `acima`
    # tambem e o numero deixaria de priorizar coisa nenhuma.
    assert "acima" not in _nomes(impacto(banco, ids["folha"], profundidade=2))
    assert "acima" in _nomes(impacto(banco, ids["folha"], profundidade=3))


def test_profundidade_de_cada_no_e_a_menor(tmp_path):
    """No alcancavel por dois caminhos sai UMA vez, na distancia mais curta.

    `atalho` chama `folha` direto e tambem chama `meio`, que chama `folha`.
    Guardar a maior distancia -- ou as duas -- faria a lista dizer que um
    vizinho direto e parente distante, e e por distancia que se decide o que
    revisar primeiro.
    """
    banco, _ = _indexar(
        tmp_path,
        {
            "n0.py": "def folha():\n    pass\n",
            "n1.py": "from n0 import folha\n\n\ndef meio():\n    folha()\n",
            "n2.py": (
                "from n0 import folha\nfrom n1 import meio\n\n\n"
                "def atalho():\n    folha()\n    meio()\n"
            ),
        },
    )
    ids = _ids(banco)

    profundidades = {no.qualified_name: no.depth for no in impacto(banco, ids["folha"])}
    assert profundidades == {"folha": 0, "meio": 1, "atalho": 1}


def test_ciclo_nao_causa_recursao_infinita(tmp_path):
    """`a -> b -> a`. Sem visitados, a travessia nao termina.

    Com teto de profundidade ela termina de qualquer jeito -- e por isso a
    afirmacao aqui nao e "terminou", que passaria com o conjunto removido. E o
    TAMANHO: sem visitados, `alfa` reaparece na profundidade 2 e `beta` na 3,
    e a lista cresce com o teto em vez de parar nos dois nos que existem.
    """
    banco, _ = _indexar(
        tmp_path,
        {
            "a.py": "from b import beta\n\n\ndef alfa():\n    beta()\n",
            "b.py": "from a import alfa\n\n\ndef beta():\n    alfa()\n",
        },
    )
    ids = _ids(banco)

    alcancados = impacto(banco, ids["alfa"], profundidade=25)
    assert _nomes(alcancados) == ["alfa", "beta"]
    assert [no.depth for no in alcancados] == [0, 1]


def test_recursao_direta_nao_repete_o_no(tmp_path):
    """`f` chama `f`. A aresta e legitima; o no na lista, um so."""
    banco, resultado = _indexar(
        tmp_path,
        {"r.py": "def recursiva(n):\n    if n:\n        recursiva(n - 1)\n"},
    )
    ids = _ids(banco)

    assert resultado.arestas == 1
    assert _nomes(impacto(banco, ids["recursiva"], profundidade=9)) == ["recursiva"]
    # Um salto so nao tem travessia para nao terminar: `f` E chamador de `f`.
    assert _nomes(chamadores(banco, ids["recursiva"])) == ["recursiva"]


def test_profundidade_zero_devolve_so_o_no(tmp_path):
    """Raio zero e o proprio no, nao lista vazia.

    Vazio se leria como "nada e afetado" quando a leitura certa e "so o proprio
    no" -- e essas duas nao podem ter a mesma representacao.
    """
    banco, _ = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "c.py": "from alvo import alvo\n\n\ndef chamador():\n    alvo()\n",
        },
    )
    ids = _ids(banco)

    somente = impacto(banco, ids["alvo"], profundidade=0)
    assert _nomes(somente) == ["alvo"]
    assert somente[0].depth == 0


def test_profundidade_negativa_devolve_vazio(tmp_path):
    """Valor absurdo fecha a porta em vez de abrir outra.

    Sem esta guarda, `range(1, 0)` deixaria a travessia vazia mas a ancora
    sairia mesmo assim -- profundidade -1 devolveria o mesmo que 0, e o absurdo
    passaria por pedido valido.
    """
    banco, _ = _indexar(tmp_path, {"a.py": "def a():\n    pass\n"})
    ids = _ids(banco)

    assert impacto(banco, ids["a"], profundidade=-1) == []


# ---------------------------------------------------------------- ordem


def _fonte_com_chamadores(quantos):
    """Um arquivo por chamador, com nomes que NAO seguem a ordem de varredura."""
    arquivos = {"alvo.py": "def alvo():\n    pass\n"}
    for indice in range(quantos):
        arquivos[f"c{indice}.py"] = (
            f"from alvo import alvo\n\n\ndef chamador_{indice}():\n    alvo()\n"
        )
    return arquivos


def test_ordem_e_deterministica(tmp_path):
    """Sem desempate explicito, a ordem do SQLite nao e garantida.

    Duas afirmacoes, e as duas sao necessarias. A primeira -- repetir a consulta
    da o mesmo resultado -- sozinha passaria com a ordem do banco, que costuma
    ser estavel dentro de um mesmo arquivo de banco. A segunda prende QUAL
    ordem: `(profundidade, path, start_line, node_id)`. Com `DISTINCT`, o
    planejador ordena pelo `node_id` -- que e digest, e portanto nao tem relacao
    nenhuma com caminho nem com linha --, entao a ordem por caminho nao acontece
    por acidente.
    """
    banco, _ = _indexar(tmp_path, _fonte_com_chamadores(8))
    ids = _ids(banco)

    rodadas = [impacto(banco, ids["alvo"], profundidade=1) for _ in range(5)]
    assert all(rodada == rodadas[0] for rodada in rodadas)

    esperado = sorted(
        rodadas[0],
        key=lambda no: (no.depth, no.path, no.start_line, no.node_id),
    )
    assert rodadas[0] == esperado
    assert _nomes(rodadas[0])[0] == "alvo"
    assert _nomes(rodadas[0])[1:] == [f"chamador_{i}" for i in range(8)]


# A funcao aninhada existe para que a ordem do BANCO seja diferente da ordem
# pedida, e a diferenca foi MEDIDA. As referencias saem do AST em ordem de
# linha, entao a de dentro de `interna` (linha 6) e gravada ANTES da de
# `externa` (linha 7) -- e o no de origem da primeira comeca na linha 5, depois
# do da segunda, que comeca na 4. A consulta crua devolve `(5, 4)`:
#
#     ordem crua        externa.interna (5), externa (4)
#     ordem por linha   externa (4), externa.interna (5)
#
# Sem isso o teste de ordem passaria com a ordenacao inteira removida, porque
# em toda outra forma de fixture a varredura ja entrega ordenado -- medido:
# quatro mutacoes de ordem SOBREVIVERAM ate esta fixture entrar.
_NINHO = (
    "from alvo import alvo\n\n\n"
    "def externa():\n"
    "    def interna():\n"
    "        alvo()\n"
    "    alvo()\n"
    "    return interna\n"
)


def test_ordem_por_linha_contraria_a_ordem_do_banco(tmp_path):
    """Mesmo caminho: quem desempata e `start_line`, contra o que o banco deu.

    Ver `_NINHO`: a ordem crua e a inversa desta. Se esta afirmacao passar com
    a ordenacao removida, a fixture parou de divergir e o teste nao prende mais
    nada -- conferir com `SELECT` cru antes de acreditar nela.
    """
    banco, _ = _indexar(
        tmp_path,
        {"alvo.py": "def alvo():\n    pass\n", "ninho.py": _NINHO},
    )
    ids = _ids(banco)

    encontrados = chamadores(banco, ids["alvo"])
    assert _nomes(encontrados) == ["externa", "externa.interna"]
    assert [no.start_line for no in encontrados] == [4, 5]

    # A MESMA afirmacao sobre `impacto`, e nao so sobre `chamadores`. As duas
    # ordenam em lugares diferentes do codigo, e uma medicao de mutacao mostrou
    # que a de `impacto` sobrevivia sozinha quando so `chamadores` era afirmado.
    assert _nomes(impacto(banco, ids["alvo"], profundidade=1)) == [
        "alvo",
        "externa",
        "externa.interna",
    ]


def test_ordem_sobrevive_a_consulta_partida_em_lotes(tmp_path, monkeypatch):
    """`_LOTE` parte o nivel em varias consultas, e a ordem tem que aguentar.

    Esta e a razao de a ordenacao acontecer em Python e nao num `ORDER BY`: o
    SQL ordena cada LOTE, e a concatenacao de lotes ordenados nao e ordenada.
    Com `_LOTE = 1` toda ancora vira uma consulta propria, que e o pior caso.
    """
    arquivos = {"folha.py": "def folha():\n    pass\n"}
    for indice in range(6):
        arquivos[f"m{indice}.py"] = (
            f"from folha import folha\n\n\ndef meio_{indice}():\n    folha()\n"
        )
    arquivos["topo.py"] = (
        "".join(f"from m{i} import meio_{i}\n" for i in range(6))
        + "\n\ndef topo():\n"
        + "".join(f"    meio_{i}()\n" for i in range(6))
    )
    banco, _ = _indexar(tmp_path, arquivos)
    ids = _ids(banco)

    inteiro = impacto(banco, ids["folha"], profundidade=2)
    monkeypatch.setattr(graph, "_LOTE", 1)
    partido = impacto(banco, ids["folha"], profundidade=2)

    assert partido == inteiro
    assert _nomes(partido) == ["folha", *[f"meio_{i}" for i in range(6)], "topo"]


# ------------------------------------------------- a ligacao com `indexar`


def _contar(banco, tabela):
    conexao = abrir(banco)
    try:
        (quantos,) = conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()  # noqa: S608
    finally:
        conexao.close()
    return quantos


def test_indexar_grava_as_duas_metades(tmp_path):
    """`resolver` produzia arestas que ninguem gravava. Isto e a ligacao.

    As DUAS tabelas sao afirmadas. So `edges` deixaria a cobertura desconhecida:
    uma travessia sobre indice sem ponto cego registrado devolve lista vazia com
    a mesma cara de "ninguem chama isto".
    """
    banco, resultado = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "c.py": (
                "from alvo import alvo\n\n\n"
                "def chamador(df):\n    alvo()\n    df.metodo_desconhecido()\n"
            ),
        },
    )

    assert _contar(banco, "edges") == resultado.arestas >= 1
    assert _contar(banco, "unresolved_refs") == resultado.nao_resolvidas >= 1


def test_reindexar_nao_acumula_aresta_nem_ponto_cego(tmp_path):
    """Duas indexacoes da mesma arvore dao os mesmos numeros, nao o dobro.

    `edges` cai por CASCADE de DOIS saltos -- `files` leva `nodes`, e `nodes`
    leva `edges` -- e isso so acontece com `foreign_keys` efetivo. Se ele
    falhasse calado, o indice dobraria de tamanho a cada reindexacao sem que
    nada acusasse, que e exatamente a forma de falha que `db.abrir` recusa.
    """
    arquivos = {
        "alvo.py": "def alvo():\n    pass\n",
        "c.py": (
            "from alvo import alvo\n\n\n"
            "def chamador(df):\n    alvo()\n    df.metodo_desconhecido()\n"
        ),
    }
    banco, primeira = _indexar(tmp_path, arquivos)
    arestas_1 = _contar(banco, "edges")
    cegos_1 = _contar(banco, "unresolved_refs")

    segunda = indexar(tmp_path, banco)

    assert (segunda.arestas, segunda.nao_resolvidas) == (
        primeira.arestas,
        primeira.nao_resolvidas,
    )
    assert _contar(banco, "edges") == arestas_1
    assert _contar(banco, "unresolved_refs") == cegos_1


def test_arquivo_apagado_leva_a_aresta_dele_junto(tmp_path):
    """Reindexar depois de apagar o chamador nao deixa aresta apontando do nada.

    Aresta orfa nao levanta: ela so faz a travessia devolver um no fantasma, ou
    contar um chamador que nao existe mais.
    """
    banco, _ = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "c.py": "from alvo import alvo\n\n\ndef chamador():\n    alvo()\n",
        },
    )
    ids = _ids(banco)
    assert _nomes(chamadores(banco, ids["alvo"])) == ["chamador"]

    (tmp_path / "c.py").unlink()
    indexar(tmp_path, banco)

    assert chamadores(banco, ids["alvo"]) == []
    assert _contar(banco, "edges") == 0


def test_travessia_le_um_indice_com_foreign_keys_efetivo(tmp_path):
    """A conexao da travessia e `db.abrir`, e ela recusa banco sem integridade.

    Dito como teste porque `graph.py` poderia ter aberto o banco com
    `sqlite3.connect` direto -- funcionaria, e perderia a unica conferencia que
    existe contra o CASCADE declarado que nao acontece.
    """
    banco, _ = _indexar(tmp_path, {"a.py": "def a():\n    pass\n"})
    conexao = abrir(banco)
    try:
        (ligado,) = conexao.execute("PRAGMA foreign_keys").fetchone()
    finally:
        conexao.close()
    assert ligado == 1


def test_banco_sem_edges_nao_e_confundido_com_grafo_vazio(tmp_path):
    """Tabela ausente levanta; tabela vazia devolve lista. Nao e a mesma coisa.

    Se um dia `edges` sumir do schema, a travessia tem que QUEBRAR, e nao
    responder "ninguem chama isto" para o repositorio inteiro.
    """
    banco, _ = _indexar(
        tmp_path,
        {
            "alvo.py": "def alvo():\n    pass\n",
            "c.py": "from alvo import alvo\n\n\ndef chamador():\n    alvo()\n",
        },
    )
    ids = _ids(banco)

    conexao = abrir(banco)
    try:
        conexao.execute("DROP TABLE edges")
    finally:
        conexao.close()

    try:
        chamadores(banco, ids["alvo"])
    except sqlite3.OperationalError:
        return
    raise AssertionError("travessia sem tabela `edges` devolveu resposta em vez de erro")
