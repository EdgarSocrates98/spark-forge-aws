"""Identidade de no, e o que uma assinatura NAO pode carregar.

O id existe para ser estavel entre execucoes: o mesmo simbolo no mesmo lugar
tem que dar o mesmo id, senao o indice incremental da fase seguinte nao
consegue dizer o que mudou. Por isso BLAKE2b sobre campos declarados, e nunca
UUID.

A assinatura existe para ser lida, e por isso ela e o lugar mais provavel de um
segredo entrar no banco: `def connect(password="hunter2")` levaria a senha para
o indice, que persiste em disco. Valor literal e substituido por marcador.
"""

from sparkforge.codeintel.ids import node_id, normalizar_assinatura


def test_mesmo_simbolo_no_mesmo_lugar_da_o_mesmo_id():
    a = node_id("jobs/etl.py", "function", "etl.processar", "processar(df)")
    b = node_id("jobs/etl.py", "function", "etl.processar", "processar(df)")
    assert a == b
    assert a.startswith("node_")


def test_campo_diferente_da_id_diferente():
    base = ("jobs/etl.py", "function", "etl.processar", "processar(df)")
    variantes = [
        ("jobs/outro.py", "function", "etl.processar", "processar(df)"),
        ("jobs/etl.py", "class", "etl.processar", "processar(df)"),
        ("jobs/etl.py", "function", "etl.outro", "processar(df)"),
        ("jobs/etl.py", "function", "etl.processar", "processar(df, extra)"),
    ]
    ids = {node_id(*base)} | {node_id(*v) for v in variantes}
    assert len(ids) == 5, "algum campo nao entra no id"


def test_id_tem_o_tamanho_declarado():
    """32 hex == 16 bytes de digest, e isso e contrato, nao detalhe.

    Sem esta afirmacao, encolher `digest_size` passa por todos os outros testes
    -- medido: a mutacao para 8 bytes sobreviveu. O tamanho e o que separa
    "colisao improvavel" de "colisao improvavel neste repositorio, por
    enquanto", e o id vai para chave primaria de tabela que cresce.
    """
    id_gerado = node_id("jobs/etl.py", "function", "etl.processar", "processar(df)")
    assert len(id_gerado) == len("node_") + 32
    assert set(id_gerado[len("node_") :]) <= set("0123456789abcdef")


def test_separador_impede_colisao_por_concatenacao():
    """Sem separador, ("ab","c") e ("a","bc") dariam o mesmo id."""
    assert node_id("ab", "c", "x", "y") != node_id("a", "bc", "x", "y")


def test_assinatura_troca_literal_por_marcador():
    entrada = "connect(password='hunter2', region='us-east-1', tentativas=3)"
    saida = normalizar_assinatura(entrada)
    assert "hunter2" not in saida
    assert "us-east-1" not in saida
    assert "password=<literal>" in saida
    assert "region=<literal>" in saida


def test_assinatura_preserva_nome_e_ordem_dos_parametros():
    saida = normalizar_assinatura("processar(df, chaves, modo='append')")
    assert saida.startswith("processar(")
    assert saida.index("df") < saida.index("chaves") < saida.index("modo")


def test_assinatura_sem_default_nao_muda():
    assert normalizar_assinatura("processar(df, chaves)") == "processar(df, chaves)"


def test_default_que_abre_parentese_tambem_e_apagado():
    """Default composto e o buraco que um regex de um so token deixa passar.

    Medido neste repositorio: dos 433 defaults dos arquivos versionados, 14
    escapam inteiros a um casamento por token unico -- todos comecam com `(`, e
    4 deles carregam string literal, como `('SF-PY-001',)`. O casamento nao
    ancora em nenhum e devolve o valor INTEIRO intacto, que e o oposto do que a
    normalizacao existe para fazer. Uma tupla de credencial entraria no banco
    sem tocar em nada.
    """
    saida = normalizar_assinatura("assinar(rule_id=('SF-PY-001', 'segredo'), n=frozenset())")
    assert "SF-PY-001" not in saida
    assert "segredo" not in saida
    assert saida == "assinar(rule_id=<literal>, n=<literal>)"


def test_default_com_chamada_aninhada_nao_vaza_o_argumento_dela():
    """`k=b64decode('c2VncmVkbw==')` tem o segredo DENTRO da chamada.

    Consumir so ate o primeiro parentese deixaria `<literal>('c2VncmVkbw==')`.
    O valor de default vai ate a virgula de topo, e e isso que some.
    """
    saida = normalizar_assinatura("conectar(k=b64decode('c2VncmVkbw=='), host='x')")
    assert "c2VncmVkbw" not in saida
    assert saida == "conectar(k=<literal>, host=<literal>)"


def test_virgula_dentro_de_string_de_default_nao_termina_o_parametro():
    """Virgula entre aspas nao e fronteira de parametro.

    Se fosse, o resto da string viraria "proximo parametro" e reapareceria na
    saida -- exatamente o segredo que se queria apagar, com outra roupa.
    """
    saida = normalizar_assinatura("f(a='x, hunter2', b=1)")
    assert "hunter2" not in saida
    assert saida == "f(a=<literal>, b=<literal>)"


def test_anotacao_de_retorno_sobrevive():
    """O que vem depois do parentese que fecha nao e parametro, e fica.

    `-> DataFrame` faz parte da assinatura como lida por um humano, e o id
    inclui a assinatura: apagar isso mudaria id sem que nada tivesse mudado.
    """
    assert normalizar_assinatura("f(df) -> DataFrame") == "f(df) -> DataFrame"
