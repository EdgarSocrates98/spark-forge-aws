"""Referencia -> aresta, ou declaracao de que nao resolveu.

A AFIRMACAO QUE ESTE ARQUIVO EXISTE PARA PRENDER
------------------------------------------------
Aresta ambigua NAO vira aresta. O AST ve `processar()` e nao sabe qual
`processar`; escolher um candidato quando ha varios e inventar, e quem seguisse
a aresta investigaria o arquivo errado sem que nada acusasse. Se
`test_nome_ambiguo_vira_unresolved_e_nao_aresta` passar com a escolha arbitraria
de volta no lugar, esta fase nao garante o que ela existe para garantir.

O SEGUNDO EIXO E A TAXA
-----------------------
`unresolved_refs` e o denominador da honestidade: o relatorio publica a taxa de
resolucao, e ela so vale se vier de contagem. Por isso ha teste separado para o
builtin nao poluir a tabela E para ele continuar no denominador -- tirar ruido
do numerador sem tirar do denominador seria maquiar o numero pelo lado de fora.
"""

import dataclasses

import pytest

from sparkforge.codeintel.db import abrir
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.refs import extrair_referencias
from sparkforge.codeintel.resolve import catalogo_do_banco, resolver


def _preparar(tmp_path, arquivos):
    """Indexa `arquivos` de verdade e devolve `(catalogo, referencias)`.

    O indice e construido por `indexar`, e nao montado a mao, porque o id que a
    aresta carrega tem que ser o MESMO que `nodes` guarda -- um catalogo forjado
    no teste passaria com ids que nao existem no banco.
    """
    for nome, fonte in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(fonte, encoding="utf-8")
    banco = tmp_path / "graph.sqlite3"
    indexar(tmp_path, banco)
    conexao = abrir(banco)
    try:
        catalogo = catalogo_do_banco(conexao)
    finally:
        conexao.close()
    referencias = {nome: extrair_referencias(fonte, nome) for nome, fonte in arquivos.items()}
    return catalogo, referencias


def _qualificados_do_banco(tmp_path):
    conexao = abrir(tmp_path / "graph.sqlite3")
    try:
        return dict(conexao.execute("SELECT id, qualified_name FROM nodes").fetchall())
    finally:
        conexao.close()


def test_resolve_nome_unico_no_indice(tmp_path):
    """Um so candidato: aresta, e ela liga ids que existem em `nodes`."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    nomes = _qualificados_do_banco(tmp_path)
    ligacoes = {(nomes[a.source_id], nomes[a.target_id]) for a in resolucao.arestas}
    assert ("executar", "processar") in ligacoes


def test_nome_ambiguo_vira_unresolved_e_nao_aresta(tmp_path):
    """Duas `processar` em modulos diferentes.

    Escolher uma seria inventar: quem seguisse a aresta investigaria o arquivo
    errado, e nada acusaria. AMBIGUOUS e a resposta honesta.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "a.py": "def processar():\n    pass\n",
            "b.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert nao.reference_name == "processar"
    assert nao.reason == "AMBIGUOUS"


def test_nome_desconhecido_vira_unresolved_no_candidate(tmp_path):
    catalogo, referencias = _preparar(
        tmp_path, {"job.py": "def executar():\n    biblioteca_externa()\n"}
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert (nao.reference_name, nao.reason) == ("biblioteca_externa", "NO_CANDIDATE")


def test_builtin_nao_polui_unresolved(tmp_path):
    """`len`, `print`, `range` nao sao ponto cego -- sao biblioteca padrao.

    Sem esta regra, `unresolved_refs` enche de ruido e o numero perde sentido:
    "3 nao resolvidas" passaria a nao distinguir alvo que valeria a pena
    resolver de alvo que nunca vai estar no indice porque nao esta na arvore.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {"job.py": "def executar():\n    print(len(range(3)))\n"},
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.nao_resolvidas == ()
    assert resolucao.builtins == 3


def test_builtin_continua_no_denominador_da_taxa(tmp_path):
    """Tirar do numerador sem tirar do denominador seria maquiar a taxa.

    Se o builtin sumisse da conta inteira, um arquivo que so chama `print`
    publicaria taxa 0/0 -- ou pior, 100%. Ele nao resolveu; ele so nao e ponto
    cego. As duas coisas sao diferentes e as duas precisam aparecer.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    print(processar())\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert len(resolucao.arestas) == 1
    assert resolucao.builtins == 1
    assert resolucao.taxa_de_resolucao == pytest.approx(0.5)


def test_definicao_da_arvore_vence_o_builtin_de_mesmo_nome(tmp_path):
    """A arvore define `filter`; a chamada e para ela, nao para o builtin.

    A ordem importa: se a checagem de builtin viesse ANTES da busca no indice,
    toda funcao que sombreia um nome da biblioteca padrao perderia as arestas
    dela em silencio.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def filter():\n    pass\n",
            "job.py": "def executar():\n    filter()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert len(resolucao.arestas) == 1
    assert resolucao.builtins == 0


def test_taxa_de_resolucao_e_medida_e_nao_estimada(tmp_path):
    """O relatorio publica a taxa. Este teste garante que ela vem de contagem.

    Duas chamadas resolvem, duas nao: 0.5 exato. Uma taxa constante, arredondada
    ou guardada em campo proprio nao sobrevive a este numero.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": (
                "def executar():\n"
                "    processar()\n"
                "    processar()\n"
                "    externa_um()\n"
                "    externa_dois()\n"
            ),
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert len(resolucao.arestas) == 2
    assert len(resolucao.nao_resolvidas) == 2
    assert resolucao.taxa_de_resolucao == pytest.approx(0.5)


def test_taxa_sem_chamada_nenhuma_e_zero(tmp_path):
    """Zero sobre zero nao levanta, e nao vira 1.0.

    100% sobre nada seria a mentira mais confortavel que este modulo poderia
    contar.
    """
    catalogo, referencias = _preparar(tmp_path, {"vazio.py": "X = 1\n"})
    resolucao = resolver(referencias, catalogo)

    assert resolucao.taxa_de_resolucao == 0.0


def test_receptor_desconhecido_nao_vira_aresta_mesmo_com_candidato_unico(tmp_path):
    """`df.filtrar()` com uma unica `filtrar` na arvore: ainda assim nao resolve.

    Este e o teste que impede a heuristica de tipo de entrar pela porta dos
    fundos. Existe UM `filtrar` no indice, entao a tentacao de ligar e maxima --
    e ceder seria afirmar que `df` e do tipo que define `filtrar`, que ninguem
    mediu. `UNKNOWN_RECEIVER` e a resposta honesta.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "frame.py": "class Frame:\n    def filtrar(self):\n        pass\n",
            "job.py": "def executar(df):\n    df.filtrar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert (nao.reference_name, nao.reason) == ("filtrar", "UNKNOWN_RECEIVER")


def test_receptor_que_e_nome_qualificado_do_indice_resolve(tmp_path):
    """`Pipeline.executar()` nomeia o alvo por inteiro -- nao ha o que inferir."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "job.py": (
                "class Pipeline:\n"
                "    def executar(self):\n"
                "        pass\n"
                "\n"
                "def principal():\n"
                "    Pipeline.executar(None)\n"
            )
        },
    )
    resolucao = resolver(referencias, catalogo)

    nomes = _qualificados_do_banco(tmp_path)
    ligacoes = {(nomes[a.source_id], nomes[a.target_id]) for a in resolucao.arestas}
    assert ("principal", "Pipeline.executar") in ligacoes


def test_self_resolve_para_a_classe_que_envolve_a_chamada(tmp_path):
    """`self` nao e palpite de tipo: e a classe que o indice ja registrou.

    A classe envolvente sai de `origem_qualificada` mais o `kind` gravado em
    `nodes` -- `Pipeline.executar` esta dentro de `Pipeline` porque existe um no
    de kind `class` com esse nome qualificado no MESMO arquivo. Nada aqui olha
    para o nome da variavel para adivinhar tipo.

    Risco medido nesta arvore: dos 3079 metodos de classe, 3060 tem `self` como
    primeiro parametro, 13 sao `staticmethod` e 6 usam `cls`. Zero tem primeiro
    parametro com outro nome -- que e o unico caso em que `self` no corpo
    apontaria para outra coisa.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "job.py": (
                "class Pipeline:\n"
                "    def executar(self):\n"
                "        self.ajudar()\n"
                "\n"
                "    def ajudar(self):\n"
                "        pass\n"
            )
        },
    )
    resolucao = resolver(referencias, catalogo)

    nomes = _qualificados_do_banco(tmp_path)
    ligacoes = {(nomes[a.source_id], nomes[a.target_id]) for a in resolucao.arestas}
    assert ligacoes == {("Pipeline.executar", "Pipeline.ajudar")}


def test_self_com_metodo_que_a_classe_nao_define_nao_resolve(tmp_path):
    """Metodo herdado de outro arquivo e ponto cego declarado, nao aresta.

    A regra do `self` para na classe envolvente e NAO cai para a busca por nome
    simples. Se caisse, `self.ajudar()` acharia qualquer `ajudar` da arvore --
    exatamente a invencao que `UNKNOWN_RECEIVER` existe para recusar.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "base.py": "def ajudar():\n    pass\n",
            "job.py": (
                "class Pipeline:\n    def executar(self):\n        self.ajudar()\n"
            ),
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert (nao.reference_name, nao.reason) == ("ajudar", "UNKNOWN_RECEIVER")


def test_receptor_nao_alcanca_funcao_de_topo_de_mesmo_nome(tmp_path):
    """Existe uma `filtrar` de topo na arvore, e `df.filtrar()` NAO e ela.

    Este e o caso em que a queda para busca por nome simples seria mais
    tentadora e mais errada: o nome casa, ha um unico candidato, e mesmo assim
    `df.filtrar()` chama o metodo de um objeto -- nunca a funcao de modulo. Uma
    aresta aqui mandaria quem a seguisse para o arquivo errado com nome certo.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def filtrar():\n    pass\n",
            "job.py": "def executar(df):\n    df.filtrar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert (nao.reference_name, nao.reason) == ("filtrar", "UNKNOWN_RECEIVER")


def test_origem_definida_duas_vezes_no_arquivo_nao_vira_aresta(tmp_path):
    """Duas `executar` no mesmo arquivo: qual delas chama nao esta decidido.

    E o `if/else` de compatibilidade -- mesma funcao, assinaturas diferentes,
    dois nos com o mesmo nome qualificado. Escolher o primeiro seria o mesmo
    defeito do alvo ambiguo, so que na outra ponta da aresta, e mais dificil de
    ver: o alvo estaria certo e a origem errada. `AMBIGUOUS_SOURCE` e separado
    de `NO_SOURCE_NODE` porque este tem conserto e aquele nao.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": (
                "import sys\n"
                "\n"
                "if sys.version_info >= (3, 11):\n"
                "    def executar(a):\n"
                "        processar()\n"
                "else:\n"
                "    def executar(a, b):\n"
                "        processar()\n"
            ),
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    assert [nao.reason for nao in resolucao.nao_resolvidas] == [
        "AMBIGUOUS_SOURCE",
        "AMBIGUOUS_SOURCE",
    ]


def test_self_fora_de_classe_nao_resolve(tmp_path):
    """Funcao de topo com parametro chamado `self` nao tem classe envolvente."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "job.py": (
                "def ajudar():\n    pass\n\ndef executar(self):\n    self.ajudar()\n"
            )
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    assert [nao.reason for nao in resolucao.nao_resolvidas] == ["UNKNOWN_RECEIVER"]


def test_chamada_no_topo_do_modulo_nao_tem_no_de_origem(tmp_path):
    """Modulo nao e no, entao a aresta e impossivel mesmo com o alvo resolvido.

    `edges.source_id` e NOT NULL e `extract.py` extrai classe, funcao e metodo
    -- nao arquivo. Registrar isso como ponto cego e o que torna visivel que
    todo script de topo a fundo fica FORA do grafo de chamadas.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    (nao,) = resolucao.nao_resolvidas
    assert (nao.reason, nao.source_id) == ("NO_SOURCE_NODE", None)


def test_import_nao_e_tentado_e_aparece_como_tal(tmp_path):
    """Import nao vira aresta nem ponto cego nesta fase -- e conta separada.

    Resolver import exige mapear modulo para arquivo, import relativo e pacote
    com `__init__`, e o alvo pode ser o proprio MODULO, que nao e no e nao cabe
    em `edges`. Nada disso foi feito aqui. Jogar os imports em `unresolved_refs`
    encheria a tabela de ponto cego com referencias que ninguem TENTOU resolver
    -- e ponto cego e o que se tentou e nao deu, nao o que nao se tentou.
    """
    catalogo, referencias = _preparar(
        tmp_path, {"job.py": "import json\nfrom os import path\n"}
    )
    resolucao = resolver(referencias, catalogo)

    assert resolucao.arestas == ()
    assert resolucao.nao_resolvidas == ()
    assert resolucao.nao_tentadas == 2
    assert resolucao.taxa_de_resolucao == 0.0


def test_definicao_do_proprio_arquivo_vence_a_de_outro_arquivo(tmp_path):
    """Nao e desempate arbitrario: e a regra de escopo do Python.

    `job.py` define `processar` no topo, entao `processar()` dentro dele acha o
    global do proprio modulo -- a definicao de `outro.py` nao esta no escopo sem
    um import. Sem esta regra o caso viraria AMBIGUOUS, e o indice declararia
    ponto cego onde a linguagem nao tem duvida nenhuma.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "outro.py": "def processar():\n    pass\n",
            "job.py": "def processar():\n    pass\n\ndef executar():\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    nomes = _qualificados_do_banco(tmp_path)
    conexao = abrir(tmp_path / "graph.sqlite3")
    try:
        caminhos = dict(
            conexao.execute(
                "SELECT nodes.id, files.path FROM nodes JOIN files ON files.id = nodes.file_id"
            ).fetchall()
        )
    finally:
        conexao.close()

    (aresta,) = [a for a in resolucao.arestas if nomes[a.target_id] == "processar"]
    assert caminhos[aresta.target_id] == "job.py"


def test_chamada_para_classe_vira_aresta_para_o_no_da_classe(tmp_path):
    """`Pipeline()` e construcao, e o no que existe para receber isso e a classe."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "job.py": "class Pipeline:\n    pass\n\ndef executar():\n    Pipeline()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    nomes = _qualificados_do_banco(tmp_path)
    assert {(nomes[a.source_id], nomes[a.target_id]) for a in resolucao.arestas} == {
        ("executar", "Pipeline")
    }


def test_duas_chamadas_iguais_dao_duas_arestas(tmp_path):
    """`edges` nao tem chave unica de proposito -- dois sitios sao dois fatos."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    processar()\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert len(resolucao.arestas) == 2
    assert sorted(a.line for a in resolucao.arestas) == [2, 3]


def test_nenhuma_aresta_sai_com_confianca_inventada(tmp_path):
    """Tudo que sai daqui e casamento exato e unico, entao tudo sai com 1.0.

    A coluna `confidence` existe para quando houver resolucao por tipo. Ate la,
    um numero intermediario escolhido aqui seria palpite com casa decimal.
    """
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert {a.confidence for a in resolucao.arestas} == {1.0}
    assert {a.kind for a in resolucao.arestas} == {"calls"}


def test_nao_resolvida_guarda_onde_e_por_que(tmp_path):
    """Sem caminho e linha, o ponto cego e um numero que ninguem consegue ir ver."""
    catalogo, referencias = _preparar(
        tmp_path, {"job.py": "def executar():\n    externa()\n"}
    )
    resolucao = resolver(referencias, catalogo)

    (nao,) = resolucao.nao_resolvidas
    assert (nao.caminho, nao.line, nao.reference_kind) == ("job.py", 2, "calls")


def test_reason_distingue_os_casos(tmp_path):
    """Uma `reason` fixa passaria em cada teste isolado e mentiria no conjunto."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "a.py": "def duplicada():\n    pass\n",
            "b.py": "def duplicada():\n    pass\n",
            "job.py": (
                "def executar(df):\n"
                "    duplicada()\n"
                "    externa()\n"
                "    df.metodo()\n"
            ),
        },
    )
    resolucao = resolver(referencias, catalogo)

    assert {nao.reference_name: nao.reason for nao in resolucao.nao_resolvidas} == {
        "duplicada": "AMBIGUOUS",
        "externa": "NO_CANDIDATE",
        "metodo": "UNKNOWN_RECEIVER",
    }


def test_resolucao_e_imutavel(tmp_path):
    """Aresta e EVIDENCIA. Consumidor que corrige o campo apaga o que foi medido."""
    catalogo, referencias = _preparar(
        tmp_path,
        {
            "util.py": "def processar():\n    pass\n",
            "job.py": "def executar():\n    processar()\n",
        },
    )
    resolucao = resolver(referencias, catalogo)

    with pytest.raises(dataclasses.FrozenInstanceError):
        resolucao.arestas[0].target_id = "node_outro"
    with pytest.raises(dataclasses.FrozenInstanceError):
        resolucao.builtins = 99


def test_catalogo_do_banco_le_o_que_o_indice_gravou(tmp_path):
    """O catalogo e uma leitura do indice, nao uma segunda extracao do AST.

    Se ele reparseasse a arvore, os ids que ele oferece poderiam divergir dos
    que `nodes` guarda, e a aresta apontaria para no que nao existe.
    """
    catalogo, _ = _preparar(
        tmp_path, {"job.py": "class Pipeline:\n    def executar(self):\n        pass\n"}
    )
    do_banco = _qualificados_do_banco(tmp_path)

    for ids in catalogo.por_qualificado.values():
        for identificador in ids:
            assert identificador in do_banco
