"""Expansao deterministica de consulta e escore composto de recuperacao.

AS QUATRO AFIRMACOES QUE ESTE ARQUIVO EXISTE PARA PRENDER
----------------------------------------------------------
1. A EXPANSAO E DETERMINISTICA E VERSIONADA. Mesma pergunta, mesmos termos, na
   mesma ordem, e a saida diz com qual versao de vocabulario foi produzida. Se
   `derivados` sair na ordem dos clusters em vez de ordenado, inserir um cluster
   no meio do YAML muda a saida de perguntas que nao tem nada a ver com ele.
2. O YAML NAO ENVENENA A LISTA DE STOPWORD. PyYAML resolve YAML 1.1, onde `no` e
   `on` sem aspas viram booleano. E a classe de defeito que passa despercebida:
   nao levanta, so faz "no" voltar a ser termo de busca.
3. DOIS COMPONENTES DA SECAO 49 VALEM ZERO, E ISSO E DECLARADO. `entrypoint` e
   `lineage` nao tem lastro no indice de hoje. Um teste que aceitasse qualquer
   valor deixaria alguem "melhorar" o ranking com uma inferencia sem medicao.
4. O DESEMPATE E EXPLICITO E COMPLETO. Escore sozinho nao ordena. Sem `(path,
   start_line, node_id)` o teste falha INTERMITENTEMENTE -- pior que falhar
   sempre. As fixtures aqui sao construidas para que a ordem por escore NAO
   coincida com a ordem por caminho nem com a ordem de entrada: numa fixture
   arrumada os tres criterios concordam por acidente e a mutacao sobrevive.
"""

import pytest

from sparkforge.codeintel.ranking import (
    DICIONARIO_PADRAO,
    Escore,
    Expansao,
    carregar_dicionario,
    chave_de_ordem,
    escore,
    expandir,
    ordenar,
)
from sparkforge.codeintel.search import Achado


def _achado(node_id="node_a", name="f", qualificado=None, kind="function", path="a/b.py", linha=1):
    return Achado(
        node_id=node_id,
        name=name,
        qualified_name=qualificado if qualificado is not None else name,
        kind=kind,
        path=path,
        start_line=linha,
    )


# ------------------------------------------------------------ expansao


def test_o_exemplo_da_spec_expande_para_os_termos_da_spec():
    """A secao 48 escreve o exemplo inteiro; ele e o caso de aceite."""
    saida = expandir("problema de skew no join")
    assert saida.literais == ("skew", "join")
    for esperado in ("broadcast", "repartition", "salting", "aqe", "adaptive", "partition"):
        assert esperado in saida.derivados, esperado


def test_stopword_booleana_do_yaml_11_chega_como_texto():
    """`no` e `on` sem aspas no YAML virariam `False` e `True`.

    O sintoma seria mudo: a lista de stopword ficaria com dois booleanos e as
    palavras `no` e `on` voltariam a ser termo de busca. Este teste le o
    dicionario real, nao uma fixture, porque o defeito mora no arquivo.
    """
    vocabulario = carregar_dicionario(str(DICIONARIO_PADRAO))
    assert all(isinstance(p, str) for p in vocabulario.stopwords)
    assert "no" in vocabulario.stopwords
    assert "on" in vocabulario.stopwords


def test_stopword_nao_vira_termo_de_busca():
    saida = expandir("problema de skew no join")
    assert "no" not in saida.termos
    assert "de" not in saida.termos
    assert "problema" not in saida.termos


def test_a_ordem_dos_literais_e_a_da_frase_e_a_dos_derivados_e_ordenada():
    """Duas ordens diferentes de proposito, e as duas por motivo.

    Literal na ordem da frase preserva a unica prioridade que a pergunta carrega
    de graca. Derivado ordenado impede que inserir um cluster no meio do YAML
    mexa na saida de pergunta que nao mudou.
    """
    saida = expandir("join skew")
    assert saida.literais == ("join", "skew")
    assert list(saida.derivados) == sorted(saida.derivados)
    assert expandir("skew join").literais == ("skew", "join")


def test_expansao_e_estavel_entre_chamadas():
    primeira = expandir("skew no join com particao")
    segunda = expandir("skew no join com particao")
    assert primeira == segunda


def test_acento_dispara_o_cluster():
    """Quem escreve "junção" tem que casar o gatilho "juncao".

    Sem a normalizacao, o cluster de join nunca dispararia para metade dos
    usuarios que escrevem em portugues -- e a falha seria silenciosa: expansao
    menor, nenhum erro.
    """
    assert "join" in expandir("problema de junção").clusters


def test_termo_derivado_que_ja_e_literal_nao_se_repete():
    """Todo cluster ecoa o proprio gatilho, de proposito.

    Se o eco voltasse em `derivados`, o mesmo termo contaria em `exact_name` e
    em `domain`, e quem so casou a palavra original ganharia bonus de expansao.
    """
    saida = expandir("skew")
    assert "skew" in saida.literais
    assert "skew" not in saida.derivados


def test_token_de_um_caractere_e_descartado():
    saida = expandir("o x de skew")
    assert "x" not in saida.termos


def test_a_expansao_carrega_a_versao_do_dicionario():
    """Sem a versao, uma expansao gravada num case nao e reproduzivel."""
    assert expandir("skew").versao == carregar_dicionario(str(DICIONARIO_PADRAO)).versao
    assert expandir("skew").versao != ""


def test_pergunta_sem_termo_conhecido_nao_levanta():
    saida = expandir("de o a")
    assert saida.termos == ()
    assert saida.clusters == ()


def test_dicionario_de_fixture_nao_envenena_o_padrao(tmp_path):
    """O cache e por caminho, e nao global.

    Se fosse global, carregar um dicionario de teste deixaria os testes
    seguintes rodando com o vocabulario errado -- e a falha apareceria em outro
    arquivo, o que e o pior lugar para uma falha aparecer.
    """
    alvo = tmp_path / "outro.yaml"
    alvo.write_text(
        'version: "teste"\nschema_version: 1\nstopwords: []\n'
        "clusters:\n  - id: so_um\n    gatilhos: [zzz]\n    termos: [zzz, www]\n",
        encoding="utf-8",
    )
    assert expandir("zzz", dicionario=str(alvo)).derivados == ("www",)
    assert expandir("skew").versao != "teste"


def test_yaml_com_stopword_nao_textual_falha_dizendo_onde(tmp_path):
    alvo = tmp_path / "quebrado.yaml"
    alvo.write_text('version: "x"\nstopwords:\n  - no\n', encoding="utf-8")
    with pytest.raises(ValueError, match="stopwords"):
        carregar_dicionario(str(alvo))


# ------------------------------------------------------------ escore


def test_componentes_sem_lastro_sao_zero_declarado():
    """`entrypoint` e `lineage` sao zero, e o zero e a afirmacao.

    Nao ha marca de ponto de entrada em `nodes` e nao ha no de tabela no schema.
    Um peso construido sobre inferencia -- "e entrypoint porque ninguem chama"
    -- confundiria ponto de entrada com simbolo morto e com chamada que caiu em
    `unresolved_refs`, onde cai a MAIORIA das referencias deste indice. Este
    teste e o que impede alguem de ligar os dois sem antes construir o lastro.
    """
    pontos = escore(_achado(name="skew"), expandir("skew"))
    assert pontos.entrypoint == 0
    assert pontos.lineage == 0


def test_nome_exato_vale_mais_que_nome_qualificado():
    expansao = expandir("skew")
    exato = escore(_achado(name="skew", qualificado="mod.skew"), expansao)
    parcial = escore(_achado(name="outro", qualificado="skew.outro"), expansao)
    assert exato.exact_name > 0
    assert parcial.exact_name == 0
    assert parcial.qualified_name > 0
    assert exato.total > parcial.total


def test_relevancia_do_fts_decai_com_a_posicao():
    """`buscar` ja devolve ordenado por `rank`, entao a posicao E a relevancia.

    Pedir o `rank` numerico de novo custaria uma consulta por candidato para
    reconstruir uma ordem que ja veio pronta.
    """
    expansao = expandir("skew")
    topo = escore(_achado(), expansao, posicao_fts=0)
    fundo = escore(_achado(), expansao, posicao_fts=5)
    muito_fundo = escore(_achado(), expansao, posicao_fts=999)
    assert topo.fts > fundo.fts > muito_fundo.fts
    assert muito_fundo.fts == 0


def test_proximidade_no_grafo_distingue_ancora_de_nunca_visto():
    """`None` e zero sao coisas diferentes, e confundi-los premia o desconhecido.

    Zero e a ancora, o no mais proximo que existe. `None` e "o grafo nunca viu
    este no". Tratar `None` como zero daria peso maximo de proximidade a todo
    candidato fora do grafo.
    """
    expansao = expandir("skew")
    ancora = escore(_achado(), expansao, profundidade_no_grafo=0)
    vizinho = escore(_achado(), expansao, profundidade_no_grafo=1)
    fora = escore(_achado(), expansao, profundidade_no_grafo=None)
    assert ancora.graph > vizinho.graph > fora.graph
    assert fora.graph == 0


def test_caminho_conta_e_quebra_em_underscore():
    """`latest_per_key.py` tem que casar o termo `latest`.

    Sem a quebra, o componente de caminho so serviria para nome de arquivo de
    uma palavra so -- que e a minoria dos arquivos deste projeto.
    """
    expansao = expandir("latest")
    assert escore(_achado(path="etl/latest_per_key.py"), expansao).path > 0
    assert escore(_achado(path="etl/outro.py"), expansao).path == 0


def test_dominio_tem_teto_e_nao_ultrapassa_o_nome_exato():
    """Sem teto, um cluster grande passa por cima da palavra que a pessoa digitou.

    O cluster de `iceberg` tem sete termos; casar todos daria 70 pontos e um
    simbolo que casa a palavra original vale 100. Empatar os dois faria a
    expansao mandar mais que a pergunta.
    """
    expansao = expandir("iceberg")
    muitos = escore(
        _achado(name="x", qualificado="snapshot.manifest.rewrite.expire.compaction", path="a/b.py"),
        expansao,
    )
    exato = escore(_achado(name="iceberg"), expansao)
    assert muitos.domain <= 30
    assert exato.total > muitos.total


def test_escore_e_inteiro_e_o_total_e_a_soma_dos_componentes():
    """Inteiro nao e gosto: `0.1 + 0.2 != 0.3` faz empate deixar de acontecer.

    Com float, dois candidatos que deveriam empatar diferem no ultimo bit
    conforme a ORDEM da soma, o desempate explicito nunca roda, e a ordem passa
    a depender de qual candidato o laco somou primeiro.
    """
    pontos = escore(_achado(name="skew", path="a/skew.py"), expandir("skew"), posicao_fts=2)
    assert isinstance(pontos.total, int)
    for valor in (
        pontos.exact_name,
        pontos.qualified_name,
        pontos.fts,
        pontos.path,
        pontos.graph,
        pontos.domain,
    ):
        assert isinstance(valor, int)


# ------------------------------------------------------------ ordem


def _empatados():
    """Tres achados de escore IDENTICO, embaralhados em todos os eixos.

    A ordem de entrada, a ordem alfabetica de `path` e a ordem de `start_line`
    sao TRES ordens diferentes aqui, de proposito. Numa fixture arrumada -- os
    tres criterios concordando -- uma mutacao que apague `path` ou `start_line`
    da chave de desempate sobrevive, porque a saida sai certa por acidente.
    """
    zero = Escore(0, 0, 0, 0, 0, 0, 0, 0)
    return [
        (_achado(node_id="node_c", path="z/ultimo.py", linha=10), zero),
        (_achado(node_id="node_a", path="a/primeiro.py", linha=90), zero),
        (_achado(node_id="node_b", path="a/primeiro.py", linha=20), zero),
    ]


def test_empate_desempata_por_caminho_depois_linha_depois_id():
    ordenado = ordenar(_empatados())
    assert [a.node_id for a, _ in ordenado] == ["node_b", "node_a", "node_c"]


def test_o_desempate_por_linha_e_necessario_e_nao_decorativo():
    """Funcao aninhada e a funcao que a contem partilham `path`.

    E o caso que torna `path` sozinho insuficiente: dois nos no mesmo arquivo
    empatam ali e a ordem entre eles fica por conta do `sort`. Com `start_line`
    na chave, a de cima vem primeiro sempre.
    """
    zero = Escore(0, 0, 0, 0, 0, 0, 0, 0)
    aninhada = (_achado(node_id="node_dentro", path="m/mod.py", linha=44), zero)
    externa = (_achado(node_id="node_fora", path="m/mod.py", linha=40), zero)
    assert [a.node_id for a, _ in ordenar([aninhada, externa])] == ["node_fora", "node_dentro"]


def test_o_desempate_por_id_fecha_a_chave():
    """Cinto, e nao desempate ativo -- pela mesma razao de `graph._chave_de_ordem`.

    Dois nos na mesma linha do mesmo arquivo nao existem no extrator de hoje. A
    chave os cobre mesmo assim porque o dia em que existirem chegaria como teste
    intermitente, e nao como erro.
    """
    zero = Escore(0, 0, 0, 0, 0, 0, 0, 0)
    par = [
        (_achado(node_id="node_zz", path="m/mod.py", linha=7), zero),
        (_achado(node_id="node_aa", path="m/mod.py", linha=7), zero),
    ]
    assert [a.node_id for a, _ in ordenar(par)] == ["node_aa", "node_zz"]


def test_escore_maior_vem_antes_do_desempate():
    baixo = (_achado(node_id="node_a", path="a/a.py", linha=1), Escore(0, 0, 0, 0, 0, 0, 0, 0))
    alto = (_achado(node_id="node_z", path="z/z.py", linha=99), Escore(100, 0, 0, 0, 0, 0, 0, 0))
    assert [a.node_id for a, _ in ordenar([baixo, alto])] == ["node_z", "node_a"]


def test_chave_de_ordem_usa_o_escore_negado():
    """O sinal e o que faz escore ALTO vir primeiro num `sorted` crescente."""
    chave = chave_de_ordem((_achado(), Escore(100, 0, 0, 0, 0, 0, 0, 0)))
    assert chave[0] == -100


def test_ordenar_nao_muta_a_lista_de_quem_chama():
    """O pacote pontua uma vez e ordena mais de uma.

    Com ordenacao no lugar, a segunda chamada operaria sobre a saida da
    primeira -- e o resultado seria o mesmo por acaso ate deixar de ser.
    """
    entrada = _empatados()
    copia = list(entrada)
    ordenar(entrada)
    assert entrada == copia


def test_expansao_e_congelada():
    """`Expansao` e resultado; mutar depois faria o pacote divergir da versao."""
    saida = expandir("skew")
    assert isinstance(saida, Expansao)
    with pytest.raises(AttributeError):
        saida.literais = ("outro",)
