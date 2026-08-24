"""Teto em bytes, alocacao por categoria e ordem declarada de reducao.

AS QUATRO AFIRMACOES QUE ESTE ARQUIVO EXISTE PARA PRENDER
----------------------------------------------------------
1. O TETO E EM BYTE, E O BYTE E DE UTF-8. Este repositorio ja tem quatro
   estimadores de token, todos `len/4`, nenhum contando byte -- e todos
   subestimam texto acentuado, que e todo texto deste projeto. Um teto sobre
   estimativa para de segurar no dia em que a estimativa erra para menos, e
   ninguem descobre porque nada compara com a verdade.
2. A ARITMETICA E INTEIRA, E O MOTIVO ESTA MEDIDO E E MAIS FRACO DO QUE PARECE.
   `ceil(n * 1.2)` e a forma inteira NAO divergem para nenhum `n` de 1 a 20000
   -- muito acima do teto duro de 36864 bytes. A primeira divergencia esta em
   `2**53 + 1`. A forma inteira nao conserta defeito que exista neste tamanho;
   ela remove a pergunta. O teste grava a medicao para que a afirmacao no codigo
   nao possa envelhecer calada.
3. A ORDEM DE REDUCAO E A DA SECAO 54, E ELA E EXERCITADA. Um passo pulado
   deixaria o pacote encolher pelo lado errado: sacrificar simbolo antes de
   aresta muda o que a resposta consegue dizer.
4. A SOMA DAS FATIAS E EXATAMENTE O ORCAMENTO. Um byte perdido por categoria e
   oito bytes que ninguem usa, e a fatura aparece como saida que cabia e foi
   cortada.
"""

import pytest

from sparkforge.codeintel import budget

# ------------------------------------------------------------ estimativa


def test_a_estimativa_conta_byte_de_utf8_e_nao_caractere():
    """"ç" e um caractere e dois bytes.

    Os quatro estimadores deste repositorio usam `len(texto)`, que conta
    caractere. Sobre texto em portugues eles subestimam sistematicamente, e um
    teto construido sobre eles seria menor que a saida real.
    """
    assert len("ç") == 1
    assert len("ç".encode()) == 2
    assert budget.estimar_tokens("ç" * 30) > budget.estimar_tokens("c" * 30)


def test_o_ramo_lexical_usa_aritmetica_inteira():
    """A forma inteira e a de `ceil(n * 1.2)` NAO divergem neste tamanho.

    A medicao esta aqui e nao so na docstring porque ela e o que impede aquele
    paragrafo de envelhecer calado. `1.2` nao e representavel em binario, mas
    para todo `n` de 1 a 20000 -- muito acima do que o teto duro de 36864 bytes
    permite -- as duas formas dao o mesmo numero, porque o produto fica dentro
    da faixa em que `float` representa inteiro exatamente.

    A forma inteira fica no codigo assim mesmo: ela nao conserta um defeito que
    exista neste tamanho, ela remove a pergunta. A alternativa seria um
    comentario dizendo "e seguro ate 2**53", que ninguem reverifica quando o
    teto muda.
    """
    from math import ceil

    divergentes = [n for n in range(1, 20001) if ceil(n * 1.2) != -((-n * 12) // 10)]
    assert divergentes == []
    assert ceil((2**53 + 1) * 1.2) != -((-(2**53 + 1) * 12) // 10)
    assert budget.estimar_tokens("a b c d e") == 6


def test_a_estimativa_e_o_maior_dos_dois_ramos():
    """Os dois ramos erram para lados opostos, e por isso os dois existem.

    Texto denso e sem espaco -- um `node_id` de 32 hex -- tem muitos bytes e
    poucas unidades. Texto de muitas palavras curtas tem o contrario.
    """
    denso = "f" * 96
    esparso = " ".join("a" * 1 for _ in range(50))
    assert budget.estimar_tokens(denso) == 32
    assert budget.estimar_tokens(esparso) == 60


def test_o_campo_nunca_promete_exatidao():
    """A secao 52 e explicita: `estimated_tokens`, nunca `exact_tokens`."""
    assert "estimar" in budget.estimar_tokens.__name__
    assert "exact" not in budget.estimar_tokens.__doc__.lower()


def test_valor_que_nao_e_texto_e_serializado_antes():
    """Estimar um pacote e medir um pacote tem que falar da mesma sequencia."""
    pacote = {"b": 2, "a": "x"}
    assert budget.estimar_tokens(pacote) == budget.estimar_tokens(
        '{"a":"x","b":2}'
    )


# ------------------------------------------------------------ tetos


def test_os_tetos_em_byte_derivam_dos_tetos_em_token_da_spec():
    """3 bytes por token e o ramo conservador da propria secao 52.

    O numero nao foi inventado ao lado da SPEC: se o teto em token mudar, o teto
    em byte muda junto, e a multiplicacao esta escrita para que isso seja lido.
    """
    assert budget.BYTES_POR_TOKEN == 3
    assert budget.TETO_DURO_BYTES == budget.TETO_DURO_TOKENS * 3
    assert budget.ORCAMENTO_PADRAO_BYTES == 1800 * 3


def test_a_faixa_pedivel_e_menor_que_o_teto_duro():
    """Iguais, o teto duro nao teria o que impedir."""
    assert budget.ORCAMENTO_MAXIMO_BYTES < budget.TETO_DURO_BYTES


def test_orcamento_fora_da_faixa_satura_em_vez_de_recusar():
    """Faixa e contrato de saturacao, nao de recusa.

    Levantar obrigaria todo chamador a conhecer o minimo antes de pedir, e o
    unico efeito seria mover o mesmo `clamp` para dentro de cada chamador.
    """
    assert budget.normalizar_orcamento(1) == budget.ORCAMENTO_MINIMO_BYTES
    assert budget.normalizar_orcamento(10**9) == budget.ORCAMENTO_MAXIMO_BYTES
    assert budget.normalizar_orcamento(None) == budget.ORCAMENTO_PADRAO_BYTES
    assert budget.normalizar_orcamento(3000) == 3000


# ------------------------------------------------------------ alocacao


def test_alocacao_soma_exatamente_o_orcamento():
    for orcamento in (768, 1801, 5400, 24576, 12345):
        assert sum(budget.alocar(orcamento).values()) == orcamento


def test_a_sobra_da_divisao_vai_para_as_primeiras_categorias():
    """As primeiras sao as que a secao 54 protege.

    Dar a sobra a elas erra do lado de preservar o que nao pode cair.
    """
    fatias = budget.alocar(1001)
    assert fatias["task"] >= 1001 * 5 // 100


def test_as_fatias_sao_inteiras():
    for valor in budget.alocar(5400).values():
        assert isinstance(valor, int)


def test_a_alocacao_reproduz_os_percentuais_da_secao_53():
    fatias = budget.alocar(10000)
    assert fatias["snippets"] == 3000
    assert fatias["symbols"] == 1500
    assert fatias["provenance"] == 500


def test_orcamento_nao_positivo_zera_todas_as_categorias():
    assert set(budget.alocar(0).values()) == {0}


# ------------------------------------------------------------ corte por bytes


def test_o_corte_e_por_prefixo_e_nao_por_mochila():
    """Escolher itens de dentro para caber melhor mentiria sobre o ranking.

    As listas que chegam la ja estao ordenadas por relevancia; devolver o quinto
    e nao o segundo porque o segundo era grande e reordenar por eficiencia de
    empacotamento.
    """
    itens = [{"a": "x" * 40}, {"b": "y"}, {"c": "z"}]
    saida = budget.cortar_por_bytes(itens, 20)
    assert saida == []


def test_o_minimo_sobrevive_a_uma_fatia_pequena_demais():
    """E como o ponto de entrada principal da secao 54 nao cai.

    Sem `minimo`, um orcamento apertado devolveria `entry_points` vazio -- e o
    pacote perderia justamente o item que a secao 54 diz que nao cai.
    """
    itens = [{"a": "x" * 200}, {"b": "y"}]
    saida = budget.cortar_por_bytes(itens, 5, minimo=1)
    assert saida == [itens[0]]


def test_o_corte_respeita_o_limite_quando_ha_espaco():
    itens = [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}]
    saida = budget.cortar_por_bytes(itens, 1000)
    assert saida == itens


# ------------------------------------------------------------ serializacao


def test_a_serializacao_e_estavel_byte_a_byte():
    """Sem `sort_keys`, o tamanho seria estavel e a assinatura nao."""
    pacote = {"b": [1, 2], "a": {"z": 1, "y": 2}}
    assert budget.serializar(pacote) == budget.serializar(dict(reversed(list(pacote.items()))))


def test_acento_nao_e_escapado_para_uxxxx():
    """Escapar TRIPLICA o custo de cada caractere acentuado.

    A saida deste projeto e quase toda em portugues, entao `ensure_ascii=True`
    seria um imposto de tres para um sobre o orcamento inteiro.
    """
    assert b"\\u" not in budget.serializar({"a": "ção"})
    assert budget.tamanho_em_bytes({"a": "ção"}) < len(
        b'{"a":"\\u00e7\\u00e3o"}'
    )


# ------------------------------------------------------------ reducao


def _pacote(n):
    return {"symbols": [{"i": i, "pad": "x" * 20} for i in range(n)], "nucleo": "fixo"}


def test_pacote_que_ja_cabe_nao_e_reduzido():
    pacote = {"a": 1}
    saida, passos = budget.aplicar_reducao(pacote, 1000, {})
    assert passos == ()
    assert saida == {"a": 1}


def test_a_ordem_da_secao_54_e_seguida():
    """Sacrificar simbolo antes de aresta muda o que a resposta consegue dizer."""
    chamados = []

    def marca(nome):
        def redutor(pacote):
            chamados.append(nome)
            pacote["itens"].pop() if pacote["itens"] else None
            return bool(pacote["itens"])

        return redutor

    pacote = {"itens": ["x" * 50 for _ in range(20)]}
    budget.aplicar_reducao(
        pacote,
        60,
        {
            "low_score_edges": marca("edges"),
            "low_score_nodes": marca("nodes"),
        },
    )
    assert chamados[0] == "nodes"


def test_passo_sem_redutor_nao_aparece_nos_passos_aplicados():
    """A ausencia e o registro: nao havia o que reduzir ali.

    Um redutor que devolvesse sempre `False` teria o mesmo efeito em execucao e
    o efeito oposto na leitura -- pareceria que a reducao tentou e nao rendeu.
    """
    pacote = _pacote(20)

    def tira(p):
        if not p["symbols"]:
            return False
        p["symbols"].pop()
        return True

    _, passos = budget.aplicar_reducao(pacote, 120, {"low_score_nodes": tira})
    assert passos == ("low_score_nodes",)
    assert "comments" not in passos


def test_o_redutor_e_chamado_em_laco_ate_parar_de_render():
    """Uma passada so desistiria com o pacote grande e nos de sobra para tirar."""
    pacote = _pacote(30)

    def tira(p):
        if not p["symbols"]:
            return False
        p["symbols"].pop()
        return True

    saida, _ = budget.aplicar_reducao(pacote, 200, {"low_score_nodes": tira})
    assert budget.tamanho_em_bytes(saida) <= 200
    assert len(saida["symbols"]) < 30


def test_nucleo_irredutivel_acima_do_teto_duro_falha_fechado():
    """A secao 51 e a secao 54 se cruzam, e nao ha saida valida.

    Devolver algo assim mesmo seria escolher qual das duas quebrar em silencio.
    A INV-015 manda falhar fechado.
    """
    gigante = {"nucleo": "x" * (budget.TETO_DURO_BYTES + 10)}
    with pytest.raises(budget.OrcamentoImpossivel):
        budget.aplicar_reducao(gigante, 100, {})


def test_ultimo_recurso_roda_so_depois_da_ordem_inteira():
    """A secao 54 diz que o aviso nao cai ANTES -- nao que nao caia nunca."""
    ordem = []
    pacote = {"symbols": ["x" * 40 for _ in range(10)], "aviso": ["y" * 40]}

    def tira_no(p):
        ordem.append("nodes")
        if not p["symbols"]:
            return False
        p["symbols"].pop()
        return True

    def ultimo(p):
        ordem.append("ultimo")
        if not p["aviso"]:
            return False
        p["aviso"] = []
        return True

    _, passos = budget.aplicar_reducao(
        pacote, 40, {"low_score_nodes": tira_no}, ultimo_recurso=ultimo
    )
    assert ordem.index("nodes") < ordem.index("ultimo")
    assert passos[-1] == "ultimo_recurso"


def test_a_ordem_de_reducao_e_a_da_spec_e_e_imutavel():
    """Lista de modulo pode ser reordenada por qualquer chamador em execucao.

    A politica de reducao passaria a depender de quem importou primeiro.
    """
    assert budget.ORDEM_DE_REDUCAO == (
        "comments",
        "docstrings",
        "low_score_nodes",
        "low_score_edges",
        "snippet_context_lines",
        "graph_depth",
        "secondary_lineage",
    )
    assert isinstance(budget.ORDEM_DE_REDUCAO, tuple)


def test_o_conjunto_protegido_e_o_da_secao_54():
    assert budget.NUNCA_REDUZIR_PRIMEIRO == frozenset(
        {
            "entry_point_principal",
            "provenance",
            "unresolved_warning",
            "security_warnings",
        }
    )
