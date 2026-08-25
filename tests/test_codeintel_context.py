"""`ContextPack`: o objeto canonico da secao 55, montado sobre indice de verdade.

AS CINCO AFIRMACOES QUE ESTE ARQUIVO EXISTE PARA PRENDER
---------------------------------------------------------
1. O PACOTE CABE, E CABER E MEDIDO EM BYTE. Estimativa de token nao serve de
   teto -- ver `test_codeintel_budget.py`. Aqui a asserção e sobre o tamanho do
   que sai serializado.
2. O QUE O INDICE NAO SABE, O PACOTE NAO AFIRMA. `index.fresh` sai `None`,
   `lineage` e `snippets` saem vazios. `true` num campo que ninguem mede e a
   classe de alegacao que o gate de lastro deste repositorio recusa.
3. O AVISO DE NAO RESOLVIDO SOBREVIVE AO CORTE. A lista pode encolher; o TOTAL
   nao. A maioria das referencias deste indice nao resolve, e um pacote que
   mostrasse vinte linhas sem o total pareceria ter vinte pontos cegos. O numero
   absoluto anda com a arvore e por isso nao esta escrito aqui.
4. A ORDEM E ESTAVEL ENTRE EXECUCOES. Dois `montar` iguais dao os MESMOS bytes.
   Sem isso, um teste de conteudo passaria e um de assinatura falharia de forma
   intermitente.
5. O PONTO DE ENTRADA PRINCIPAL NAO CAI. E o item que a secao 54 protege por
   nome, e o unico que sobrevive a um orcamento absurdo.

O INDICE E CONSTRUIDO POR `indexar`, NUNCA FORJADO
---------------------------------------------------
Mesma razao de `test_codeintel_graph.py`: os `node_id` que a aresta carrega tem
que ser os MESMOS que `nodes` guarda, e um banco montado a mao passaria com ids
que o codigo real nunca produz.

A FIXTURE TEM FUNCAO ANINHADA DE PROPOSITO
-------------------------------------------
Uma arvore em que nome, linha e caminho crescem juntos faz os tres criterios de
desempate concordarem por acidente, e uma mutacao na chave de ordem sobrevive.
Funcao aninhada poe dois simbolos no MESMO arquivo em linhas proximas, com nomes
que ordenam ao contrario da linha -- e e ai que `start_line` na chave passa a
ter o que provar.
"""

import pytest

from sparkforge.codeintel import budget
from sparkforge.codeintel.context import (
    CANDIDATOS_POR_TERMO,
    SCHEMA_VERSION,
    TERMOS_MAXIMOS,
    ContextPack,
    _candidatos,
    _fixar_metricas_do_posfixo,
    montar,
)
from sparkforge.codeintel.index import indexar
from sparkforge.codeintel.ranking import expandir
from sparkforge.codeintel.search import buscar

# `zzz_externa` na linha 2 e `aaa_aninhada` na linha 6: nome e linha ordenam ao
# contrario, no MESMO caminho. E o par que quebra a coincidencia.
ANINHADAS = '''
def zzz_externa(df):
    """Faz o join."""

    def aaa_aninhada(x):
        return broadcast_do_join(x)

    return aaa_aninhada(df)


def broadcast_do_join(x):
    return x
'''

OUTRO_ARQUIVO = '''
def skew_helper(df):
    return df.metodo_que_nao_resolve()


class SkewPlanner:
    def plan(self, df):
        return skew_helper(df)
'''


# Doze simbolos que casam termos de clusters diferentes. Com dois ou tres, TODA
# busca devolve o mesmo no na posicao 0 e a regra da MENOR posicao nunca e
# exercitada -- a mutacao que troca `min` por `ultimo` sobreviveria intacta.
# MEDIDO sobre esta fixture: quatro nos aparecem em posicoes diferentes em
# termos diferentes.
MUITOS_SIMBOLOS = "\n".join(
    f"def {nome}(df):\n    return df\n"
    for nome in (
        "join_a",
        "join_b",
        "join_c",
        "broadcast_join_d",
        "broadcast_e",
        "broadcast_f",
        "skew_join_g",
        "skew_h",
        "partition_join_i",
        "partition_j",
        "shuffle_join_k",
        "shuffle_l",
    )
)


@pytest.fixture
def banco_largo(tmp_path):
    raiz = tmp_path / "larga"
    raiz.mkdir()
    (raiz / "muitos.py").write_text(MUITOS_SIMBOLOS, encoding="utf-8")
    alvo = tmp_path / "largo.sqlite3"
    indexar(raiz, alvo)
    return alvo


@pytest.fixture
def banco(tmp_path):
    raiz = tmp_path / "arvore"
    (raiz / "pipeline").mkdir(parents=True)
    (raiz / "pipeline" / "join_tuning.py").write_text(ANINHADAS, encoding="utf-8")
    (raiz / "pipeline" / "skew_tuning.py").write_text(OUTRO_ARQUIVO, encoding="utf-8")
    alvo = tmp_path / "idx.sqlite3"
    indexar(raiz, alvo)
    return alvo


# ------------------------------------------------------------ forma


def test_o_pacote_tem_exatamente_as_chaves_da_secao_55_mais_reductions(banco):
    """`reductions` e extensao DECLARADA, e nao esquecimento de fidelidade.

    A secao 54 exige uma ordem de reducao; um pacote que encolheu sem dizer o
    que caiu transforma corte em perda de evidencia silenciosa -- o mesmo
    defeito que `pack_context` ja evita com o campo `truncated`.
    """
    saida = montar(banco, "problema de skew no join").para_dicionario()
    assert set(saida) == {
        "schema_version",
        "query",
        "index",
        "entry_points",
        "symbols",
        "relationships",
        "lineage",
        "rules",
        "runtime",
        "snippets",
        "unresolved",
        "security",
        "metrics",
        "reductions",
    }
    assert saida["schema_version"] == SCHEMA_VERSION


def test_o_bloco_de_seguranca_marca_a_origem_como_nao_confiavel(banco):
    """A INV-014 vale para tudo que veio da arvore analisada.

    Nome de simbolo e caminho sao conteudo de repositorio, e um consumidor que
    receba isso sem a marca trata texto de terceiro como instrucao.
    """
    saida = montar(banco, "join").para_dicionario()
    assert saida["security"] == {"trust": "untrusted_repository_content"}


def test_index_fresh_e_nulo_porque_staleness_nao_e_medido(banco):
    """`true` seria afirmacao sem medicao.

    Nao ha comparacao de `content_sha256` contra a arvore na hora da consulta,
    nem `head` de git gravado. `None` diz "nao medido", que e a verdade.
    """
    indice = montar(banco, "join").para_dicionario()["index"]
    assert indice["fresh"] is None
    assert indice["head"] is None
    assert indice["worktree"] is None


def test_a_procedencia_do_indice_sai_sem_nomear_a_maquina(banco):
    """`root_fingerprint`, nunca a raiz -- e a mesma regra de `search.resumo`.

    Um pacote que reconstituisse o caminho desfaria a razao de o metadata
    guardar impressao em vez de nome.
    """
    indice = montar(banco, "join").para_dicionario()["index"]
    assert indice["root_fingerprint"]
    assert "arvore" not in str(indice)


def test_lineage_e_snippets_saem_vazios_e_isso_e_a_afirmacao(banco):
    """Os dois campos existem e ficam vazios por razao registrada.

    `lineage` porque nao ha no de tabela no schema -- `edges` grava chamada.
    `snippets` porque o ciclo de vida de recuperacao de source nao existe e a
    INV-010 proibe corpo de fonte persistido. No dia em que existir, `snippets`
    deve consumir `ContextFunnel`, e nao um empacotador de trecho novo.
    """
    saida = montar(banco, "join").para_dicionario()
    assert saida["lineage"] == []
    assert saida["snippets"] == []


def test_o_texto_da_tarefa_nao_e_ecoado(banco):
    """Ele nao esta na secao 55, e e a unica string do pacote vinda de fora.

    Devolve-la seria carregar conteudo nao sanitizado num objeto que outro
    agente vai ler. O que sai e a EXPANSAO dela, derivada do dicionario.
    """
    marca = "SEGREDO_DA_PERGUNTA"
    saida = montar(banco, f"join {marca}").para_dicionario()
    assert marca not in str(saida)
    assert marca.lower() not in str(saida)


def test_a_expansao_usada_sai_no_pacote_com_a_versao_do_dicionario(banco):
    consulta = montar(banco, "problema de skew no join").para_dicionario()["query"]
    assert "skew" in consulta["terms"]
    assert "join" in consulta["clusters"]
    assert consulta["dictionary_version"]


# ------------------------------------------------------------ recuperacao


def test_o_pacote_acha_o_simbolo_pelo_nome(banco):
    saida = montar(banco, "broadcast_do_join").para_dicionario()
    nomes = [item["qualified_name"] for item in saida["entry_points"] + saida["symbols"]]
    assert "broadcast_do_join" in nomes


def test_a_expansao_de_dominio_traz_simbolo_que_o_nome_sozinho_nao_traria(banco):
    """"skew" nao esta em `broadcast_do_join`; `broadcast` esta, e vem do cluster."""
    so_literal = montar(banco, "skew").para_dicionario()
    nomes = [
        item["qualified_name"]
        for item in so_literal["entry_points"] + so_literal["symbols"]
    ]
    assert "broadcast_do_join" in nomes


def test_a_quebra_do_escore_sai_junto_com_o_simbolo(banco):
    """Sem ela, "por que este veio na frente" so tem resposta relendo o codigo.

    E a resposta muda quando o codigo muda.
    """
    entradas = montar(banco, "join").para_dicionario()["entry_points"]
    assert entradas
    quebra = entradas[0]["score_breakdown"]
    assert set(quebra) == {
        "exact_name",
        "qualified_name",
        "fts",
        "path",
        "graph",
        "domain",
        "entrypoint",
        "lineage",
    }
    assert sum(quebra.values()) == entradas[0]["score"]


def test_as_relacoes_saem_do_grafo_gravado(banco):
    """`zzz_externa` nao chama `broadcast_do_join`; a ANINHADA chama.

    Uma travessia que confundisse escopo devolveria a aresta pendurada na
    funcao errada, e a fixture aninhada e o que separa os dois casos.
    """
    saida = montar(banco, "aaa_aninhada").para_dicionario()
    pares = {(r["source"], r["target"]) for r in saida["relationships"]}
    assert any("aaa_aninhada" in origem for origem, _ in pares)


def test_termo_com_operador_de_fts_nao_levanta(banco):
    """A secao 30 nao tem excecao por procedencia.

    `"` e `(` sao sintaxe de FTS5 e levantariam `OperationalError` interpolados
    direto no `MATCH`. O construtor de `search.py` e quem impede isso, e este
    teste e o que garante que o pacote passa por ele.
    """
    saida = montar(banco, 'join "quebrado( OR NEAR(a b)').para_dicionario()
    assert saida["schema_version"] == SCHEMA_VERSION


def test_duas_montagens_iguais_dao_os_mesmos_bytes(banco):
    """Sem ordem total, um teste de conteudo passa e um de assinatura falha.

    E a falha aparece de forma intermitente, que e pior que falhar sempre.
    """
    primeira = budget.serializar(montar(banco, "join skew").para_dicionario())
    segunda = budget.serializar(montar(banco, "join skew").para_dicionario())
    assert primeira == segunda


# ------------------------------------------------------------ orcamento


def test_o_pacote_cabe_no_orcamento_pedido(banco):
    for pedido in (2400, 5400, 12000):
        saida = montar(banco, "problema de skew no join", max_bytes=pedido).para_dicionario()
        assert budget.tamanho_em_bytes(saida) <= pedido, pedido


def test_nenhum_pacote_passa_do_teto_duro(banco):
    saida = montar(
        banco, "join skew particao memoria iceberg", max_bytes=10**9
    ).para_dicionario()
    assert budget.tamanho_em_bytes(saida) <= budget.TETO_DURO_BYTES


def test_o_ponto_de_entrada_principal_sobrevive_ao_orcamento_minimo(banco):
    """O nucleo irredutivel deste pacote nao cabe no minimo da faixa.

    MEDIDO: com `max_bytes=768` (o minimo da secao 51, 256 tokens x 3) o pacote
    sai com mais de mil bytes, porque procedencia, bloco de seguranca, metricas
    e UM ponto de entrada ja custam isso. A secao 54 manda preservar esses
    itens, entao a saida e maior que o pedido -- e o excedente sai NO PACOTE,
    em `metrics.over_budget_bytes`, em vez de calado.
    """
    saida = montar(banco, "join", max_bytes=768).para_dicionario()
    assert len(saida["entry_points"]) == 1
    assert saida["metrics"]["over_budget_bytes"] > 0
    assert budget.tamanho_em_bytes(saida) <= budget.TETO_DURO_BYTES


def test_orcamento_folgado_nao_reporta_excedente(banco):
    saida = montar(banco, "join", max_bytes=12000).para_dicionario()
    assert saida["metrics"]["over_budget_bytes"] == 0


def test_a_menor_posicao_do_fts_vence_quando_o_no_aparece_em_dois_termos(banco_largo):
    """Aparecer no topo de QUALQUER termo e o sinal.

    Deixar o ultimo termo sobrescrever faria a ordem depender de qual palavra a
    pessoa escreveu por ultimo -- "skew join" e "join skew" dariam pacotes
    diferentes com o mesmo conjunto de termos.

    O teste chama `_candidatos` direto porque a propriedade e dele: por
    `montar`, a diferenca de posicao so muda a ordem quando ela sobrevive ao
    resto do escore, e um teste que dependa disso mede outra coisa. A contagem
    de divergencias no fim e o que impede o teste de ficar vacuo se a fixture
    encolher.
    """
    expansao = expandir("problema de skew no join")
    encontrados = _candidatos(banco_largo, expansao, CANDIDATOS_POR_TERMO)
    divergencias = 0
    for termo in expansao.termos[:TERMOS_MAXIMOS]:
        for posicao, achado in enumerate(buscar(banco_largo, termo, CANDIDATOS_POR_TERMO)):
            guardada = encontrados[achado.node_id][1]
            assert guardada <= posicao, (achado.qualified_name, termo, guardada, posicao)
            if guardada != posicao:
                divergencias += 1
    assert divergencias > 0, "fixture sem divergencia de posicao torna o teste vacuo"


def test_a_escrita_das_metricas_do_posfixo_precisa_de_mais_de_uma_passada():
    """Uma passada so devolve um numero que ja estava errado quando foi escrito.

    MEDIDO: com o corpo minimo abaixo, escrever `estimated_tokens` e
    `over_budget_bytes` uma unica vez deixa os DOIS campos abaixo do valor real
    -- os digitos que entraram no lugar dos zeros sao bytes que a medicao
    anterior nao viu. E a classe de defeito que nao levanta: o pacote sai com
    um numero plausivel e menor que a verdade.

    O teste chama a funcao direto e nao por `montar` porque por `montar` a
    diferenca depende de o tamanho do pacote cair do lado certo do arredondamento
    de `ceil(bytes / 3)` -- verdadeiro para a maioria dos enchimentos, falso para
    um em tres, e um teste que passa em dois de cada tres pacotes e um teste
    intermitente.
    """
    corpo = {"pad": "", "metrics": {"estimated_tokens": 0, "over_budget_bytes": 0}}
    _fixar_metricas_do_posfixo(corpo, 10)
    assert corpo["metrics"]["estimated_tokens"] == budget.estimar_tokens(corpo)
    assert corpo["metrics"]["over_budget_bytes"] == max(
        0, budget.tamanho_em_bytes(corpo) - 10
    )


def test_metricas_do_posfixo_convergem(banco):
    """`estimated_tokens` se mede a si mesmo, e por isso a escrita e em laco.

    Escrever `4210` onde havia `0` acrescenta tres bytes ao corpo, e o numero
    certo passa a ser outro. Uma escrita so devolveria um numero que ja estava
    errado no instante em que foi escrito.

    Varios orcamentos, e nao um: o laco e limitado em quatro voltas, e um
    esgotamento sem igualdade sairia com um numero MENOR que o real e calado.
    Comparar com o tamanho final medido, em pacotes de tamanhos diferentes, e o
    que faz esse dia aparecer aqui e nao em producao.
    """
    for pedido in (2400, 3600, 5400, 7200, 12000):
        saida = montar(banco, "problema de skew no join", max_bytes=pedido).para_dicionario()
        assert saida["metrics"]["estimated_tokens"] == budget.estimar_tokens(saida), pedido
        assert saida["metrics"]["over_budget_bytes"] == max(
            0, budget.tamanho_em_bytes(saida) - pedido
        ), pedido


def test_o_campo_de_token_e_estimativa_e_o_teto_e_byte(banco):
    """Os dois numeros nao sao o mesmo numero, e o pacote nao finge que sao."""
    saida = montar(banco, "join", max_bytes=5400).para_dicionario()
    assert "estimated_tokens" in saida["metrics"]
    assert "exact_tokens" not in saida["metrics"]
    assert saida["metrics"]["estimated_tokens"] != budget.tamanho_em_bytes(saida)


def test_orcamento_apertado_reduz_e_diz_o_que_reduziu(banco):
    """Corte silencioso e perda de evidencia; corte declarado e corte."""
    folgado = montar(banco, "join skew", max_bytes=12000).para_dicionario()
    apertado = montar(banco, "join skew", max_bytes=2400).para_dicionario()
    assert len(apertado["entry_points"] + apertado["symbols"]) <= len(
        folgado["entry_points"] + folgado["symbols"]
    )
    assert budget.tamanho_em_bytes(apertado) < budget.tamanho_em_bytes(folgado)


def test_a_alocacao_da_secao_53_limita_a_categoria_gulosa(banco):
    """Sem ela, a lista de nao resolvidas come a fatia de simbolo e de relacao.

    A secao 53 reserva 5% para procedencia. `alocar` deixaria de ter efeito -- e
    de ser consultada por alguem -- se o corte por categoria nao existisse.
    """
    saida = montar(banco, "skew", max_bytes=2400).para_dicionario()
    fatias = budget.alocar(2400)
    assert budget.tamanho_em_bytes({"u": saida["unresolved"]}) <= fatias["provenance"] + 20


def test_o_total_de_nao_resolvidas_sobrevive_ao_corte_da_lista(banco):
    """A lista e amostra; o total e o aviso, e a secao 54 protege o aviso.

    A fixture tem `df.metodo_que_nao_resolve()`, que e exatamente o caso
    `UNKNOWN_RECEIVER` que domina este repositorio.
    """
    saida = montar(banco, "skew_helper").para_dicionario()
    assert saida["metrics"]["unresolved_total"] >= len(saida["unresolved"])
    assert saida["metrics"]["unresolved_total"] > 0


# ------------------------------------------------------------ integracao


def test_regras_e_runtime_entram_por_parametro_e_nao_sao_inventados(banco):
    """O motor de regras consome FATO e o indice devolve SIMBOLO.

    Ligar os dois e decisao de outra fase. Aceitar os dois como entrada deixa o
    pacote completo para quem ja os tem, sem este modulo fingir integracao.
    """
    vazio = montar(banco, "join").para_dicionario()
    assert vazio["rules"] == []
    assert vazio["runtime"] == {}
    cheio = montar(
        banco,
        "join",
        regras=({"rule_id": "SPARK-001"},),
        runtime={"glue_version": "5.0"},
    ).para_dicionario()
    assert cheio["rules"] == [{"rule_id": "SPARK-001"}]
    assert cheio["runtime"] == {"glue_version": "5.0"}


def test_o_pacote_e_congelado(banco):
    """Ele e RESULTADO: a reducao ja aconteceu quando ele existe.

    Uma lista mutavel convidaria quem le a acrescentar item depois do corte, e o
    pacote passaria do teto que acabou de respeitar sem nada medir de novo.
    """
    pacote = montar(banco, "join")
    assert isinstance(pacote, ContextPack)
    assert isinstance(pacote.entry_points, tuple)
    with pytest.raises(AttributeError):
        pacote.entry_points = ()


def test_pergunta_sem_termo_nao_levanta_e_devolve_pacote_vazio(banco):
    saida = montar(banco, "de o a").para_dicionario()
    assert saida["entry_points"] == []
    assert saida["symbols"] == []
    assert saida["security"]["trust"] == "untrusted_repository_content"
