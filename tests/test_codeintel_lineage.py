"""DataGraph de PySpark: as afirmacoes que este arquivo existe para prender.

1. NAO INVENTAR NOME (SPEC 38). `spark.table(f"{db}.{tbl}")` nao pode produzir
   dataset nomeado. Um nome inventado se le como resposta, e manda quem
   investiga olhar uma tabela que nao existe. `TestNomeDinamico` afirma a
   ausencia, e `TestMutacaoDaRegraDeNaoInventar` prova que a afirmacao nao e
   vazia: com o modulo mutado numa COPIA em tmpdir para inventar o nome, a
   mesma propriedade falha.

2. SEM HEURISTICA DE TIPO. `df.filter(...)` onde `df` nao foi ligado a nada nao
   vira aresta -- vira `UNKNOWN_RECEIVER`. Aceitar o receptor por ele se chamar
   `df` encheria o grafo de arestas indistinguiveis das verdadeiras.

3. O ALVO NAO SAI DE QUALQUER LITERAL DA CADEIA. `pyspark_ast` emite
   `attrs.target == "data_pedido"` para
   `write.mode("overwrite").partitionBy("data_pedido").parquet(saida)` -- a
   coluna de particao, nao o destino -- e `attrs.target == "parquet"` para
   `read.format("parquet").load(entrada)`. `TestAlvoNaoSaiDeQualquerLiteral`
   afirma que nenhum dos dois vira dataset aqui.

4. A DETECCAO NAO DIVERGE DO EXTRATOR. `lineage` reaplica a condicao de
   leitura/escrita de `pyspark_ast` em vez de copiar uma segunda lista de
   metodos; `TestConcordanciaComOExtrator` mede as duas sobre as 17 fixtures de
   `fixtures/pyspark/` e falha se as contagens se separarem.

5. A PROFUNDIDADE CONTA SALTO ENTRE TABELAS, nao aresta. Se contasse aresta,
   `profundidade=1` sobre uma tabela devolveria os `withColumn` do meio do
   caminho em vez das tabelas que a alimentam -- que e o desenho da SPEC 37.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

from sparkforge.codeintel import extract, lineage
from sparkforge.codeintel.lineage import (
    DINAMICO,
    DYNAMIC_TABLE_IDENTIFIER,
    JUSANTE,
    MONTANTE,
    SQL_NOT_PARSED,
    UNKNOWN_RECEIVER,
    construir,
    jusante,
    linhagem_de_tabela,
    mesclar,
    montante,
)
from sparkforge.facts.pyspark_ast import extract_source

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = RAIZ / "fixtures" / "pyspark"
MODULO = RAIZ / "sparkforge" / "codeintel" / "lineage.py"

# O exemplo da SPEC 35, letra por letra. Nao e inventado: e o unico caso do qual
# a SPEC desenha o grafo esperado, e por isso e o que se pode conferir sem
# opinar.
SPEC_35 = '''
orders = spark.table("bronze.orders")
users = spark.table("silver.users")

result = (
    orders
    .join(users, "customer_id")
    .filter(F.col("active"))
)

result.writeTo("gold.active_orders").append()
'''


def _nomes_de_dataset(grafo):
    return sorted(no.nome for no in grafo.datasets)


def _operacoes(grafo):
    return sorted(aresta.operacao for aresta in grafo.arestas)


def _fixtures():
    """Os arquivos de entrada das fixtures PySpark, em ordem estavel."""
    return sorted(FIXTURES.rglob("input/**/*.py"))


class TestDataGraph:
    """SPEC 35: tabela lida -> DataFrame -> transformacao -> DataFrame -> tabela escrita."""

    def test_exemplo_da_spec_produz_read_join_filter_e_write(self):
        grafo = construir(SPEC_35, "job.py")
        assert _operacoes(grafo) == ["FILTER", "JOIN", "JOIN", "READ", "READ", "WRITE"]

    def test_exemplo_da_spec_nomeia_as_tres_tabelas_e_nada_mais(self):
        grafo = construir(SPEC_35, "job.py")
        assert _nomes_de_dataset(grafo) == [
            "bronze.orders",
            "gold.active_orders",
            "silver.users",
        ]

    def test_exemplo_da_spec_nao_deixa_ponto_cego(self):
        """Com tudo literal e tudo ligado, nao sobra nada por resolver.

        E o contraponto de `TestNomeDinamico`: se `nao_resolvidos` viesse cheio
        tambem no caso limpo, o campo estaria medindo ruido do construtor em vez
        de ponto cego do codigo analisado.
        """
        grafo = construir(SPEC_35, "job.py")
        assert grafo.nao_resolvidos == ()
        assert grafo.taxa_de_resolucao == 1.0

    def test_join_tem_dois_lados_entrando_no_mesmo_dataframe(self):
        """As duas arestas JOIN chegam no MESMO no. Se chegassem em dois, o
        join teria virado duas transformacoes independentes e o grafo diria que
        `orders` e `users` nunca se encontraram."""
        grafo = construir(SPEC_35, "job.py")
        destinos = {a.destino for a in grafo.arestas if a.operacao == "JOIN"}
        assert len(destinos) == 1

    def test_reatribuicao_produz_dois_dataframes_e_nao_um_autolaco(self):
        fonte = 'df = spark.table("a.b")\ndf = df.filter("x")\ndf.writeTo("c.d").append()\n'
        grafo = construir(fonte, "job.py")
        assert not [a for a in grafo.arestas if a.origem == a.destino]
        assert _operacoes(grafo) == ["FILTER", "READ", "WRITE"]


class TestNomeDinamico:
    """SPEC 38: quando nao da para resolver, nao inventar."""

    def test_fstring_nao_produz_dataset_nomeado(self):
        grafo = construir('df = spark.table(f"{database}.{table}")\n', "job.py")
        assert _nomes_de_dataset(grafo) == [DINAMICO]

    def test_fstring_registra_razao_template_e_variaveis(self):
        grafo = construir('df = spark.table(f"{database}.{table}")\n', "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.reason == DYNAMIC_TABLE_IDENTIFIER
        assert nao_resolvido.template == "{database}.{table}"
        assert nao_resolvido.variaveis == ("database", "table")

    def test_template_preserva_a_parte_literal_que_se_sabe(self):
        """`f"bronze.{t}"` diz em qual database procurar, e isso nao se joga fora."""
        grafo = construir('df = spark.table(f"bronze.{tabela}")\n', "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.template == "bronze.{tabela}"

    def test_nome_nu_nao_ganha_template_inventado(self):
        """Um `Name` nao tem forma a mostrar; `"{nome}"` sugeriria estrutura que
        a fonte nao tem."""
        grafo = construir("df = spark.table(nome_da_tabela)\n", "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.template == DINAMICO
        assert nao_resolvido.variaveis == ("nome_da_tabela",)

    def test_dataset_dinamico_continua_no_grafo_como_ponto_do_fluxo(self):
        """O no existe -- a leitura aconteceu -- mas nao esta resolvido.

        Omitir o no faria a escrita seguinte parecer sem origem, que e uma
        afirmacao diferente e falsa.
        """
        fonte = 'df = spark.table(nome)\ndf.write.saveAsTable("gold.x")\n'
        grafo = construir(fonte, "job.py")
        (dinamico,) = [no for no in grafo.datasets if not no.resolvido]
        assert dinamico.nome == DINAMICO
        assert [a.operacao for a in grafo.arestas if a.origem == dinamico.identificador] == [
            "READ"
        ]

    def test_fstring_sem_buraco_e_literal(self):
        """`f"gold.vendas"` nomeia tanto quanto `"gold.vendas"`."""
        grafo = construir('df = spark.table(f"gold.vendas")\n', "job.py")
        assert _nomes_de_dataset(grafo) == ["gold.vendas"]
        assert grafo.nao_resolvidos == ()

    def test_numero_nao_vira_nome_de_tabela(self):
        grafo = construir("df = spark.table(7)\n", "job.py")
        assert _nomes_de_dataset(grafo) == [DINAMICO]

    def test_dois_dinamicos_em_arquivos_diferentes_nao_se_fundem(self):
        """Dois desconhecidos nao sao o mesmo desconhecido.

        Fundi-los criaria um caminho de linhagem entre dois jobs que ninguem
        mediu -- pior que nao ter caminho nenhum.
        """
        grafo = mesclar(
            [
                construir("df = spark.table(nome)\n", "a.py"),
                construir("df = spark.table(nome)\n", "b.py"),
            ]
        )
        assert len(grafo.datasets) == 2


class TestSemHeuristicaDeTipo:
    def test_receptor_nao_ligado_nao_vira_aresta(self):
        grafo = construir('def f(df):\n    return df.filter("x")\n', "job.py")
        assert grafo.arestas == ()

    def test_receptor_nao_ligado_e_contado_como_ponto_cego(self):
        grafo = construir('def f(df):\n    return df.filter("x")\n', "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.reason == UNKNOWN_RECEIVER
        assert nao_resolvido.operacao == "FILTER"

    def test_receptor_desconhecido_e_um_ponto_cego_por_cadeia_nao_por_elo(self):
        """Doze `withColumn` sobre um unico `df` desconhecido sao UM
        desconhecimento. Um registro por elo multiplicaria a contagem de pontos
        cegos por doze e esconderia quantos receptores de fato nao resolvem."""
        fonte = FIXTURES / "withcolumn_run" / "input" / "lib" / "job.py"
        grafo = construir(fonte.read_text(encoding="utf-8"), "job.py")
        razoes = [n.reason for n in grafo.nao_resolvidos]
        assert razoes == [UNKNOWN_RECEIVER]

    def test_cadeia_aninhada_reporta_o_proprio_receptor(self):
        """A bandeira de "ja reportei" e por cadeia: a de dentro nao cala a de fora."""
        grafo = construir('def f(a, b):\n    return a.join(b.filter("x"), "k")\n', "job.py")
        assert [n.reason for n in grafo.nao_resolvidos] == [
            UNKNOWN_RECEIVER,
            UNKNOWN_RECEIVER,
        ]

    def test_escopo_de_funcao_nao_herda_ligacao_do_modulo(self):
        """Herdar exigiria saber se o global foi reatribuido antes da chamada, e
        a ordem de chamada nao esta no AST."""
        fonte = 'g = spark.table("a.b")\n\n\ndef f():\n    g.writeTo("c.d").append()\n'
        grafo = construir(fonte, "job.py")
        assert [a.operacao for a in grafo.arestas] == ["READ"]
        assert [n.reason for n in grafo.nao_resolvidos] == [UNKNOWN_RECEIVER]

    def test_metodo_desconhecido_nao_propaga_o_dataframe(self):
        """`df.schema.json()` nao devolve DataFrame, e propagar assumiria que
        todo metodo devolve."""
        fonte = 'df = spark.table("a.b")\nx = df.naoexiste()\nx.writeTo("c.d").append()\n'
        grafo = construir(fonte, "job.py")
        assert [a.operacao for a in grafo.arestas] == ["READ"]

    def test_reatribuir_para_nao_dataframe_apaga_a_ligacao(self):
        """Manter a ligacao antiga faria a aresta seguinte sair do no errado."""
        fonte = 'df = spark.table("a.b")\ndf = 3\ndf.writeTo("c.d").append()\n'
        grafo = construir(fonte, "job.py")
        assert [a.operacao for a in grafo.arestas] == ["READ"]

    def test_broadcast_repassa_o_dataframe_que_recebe(self):
        fonte = (
            'a = spark.table("x.a")\n'
            'b = spark.table("x.b")\n'
            'c = a.join(broadcast(b), "k")\n'
            'c.writeTo("x.c").append()\n'
        )
        grafo = construir(fonte, "job.py")
        assert len({a.destino for a in grafo.arestas if a.operacao == "JOIN"}) == 1
        assert len([a for a in grafo.arestas if a.operacao == "JOIN"]) == 2


class TestAlvoNaoSaiDeQualquerLiteral:
    def test_particao_de_escrita_nao_vira_tabela(self):
        """`partitionBy("data_pedido")` e coluna, nao destino -- e o
        `attrs.target` do golden de `clean_job` diz "data_pedido"."""
        fonte = 'df = spark.table("a.b")\ndf.write.mode("overwrite").partitionBy("d").parquet(p)\n'
        grafo = construir(fonte, "job.py")
        assert "d" not in _nomes_de_dataset(grafo)
        assert "overwrite" not in _nomes_de_dataset(grafo)

    def test_formato_de_leitura_nao_vira_tabela(self):
        """`format("parquet")` e formato -- e o `attrs.target` do golden diz
        "parquet"."""
        grafo = construir('df = spark.read.format("parquet").load(caminho)\n', "job.py")
        assert "parquet" not in _nomes_de_dataset(grafo)
        assert _nomes_de_dataset(grafo) == [DINAMICO]

    def test_clean_job_nao_produz_nenhuma_tabela_nomeada(self):
        """A fixture inteira le e escreve por parametro. Qualquer nome aqui foi
        inventado."""
        fonte = FIXTURES / "clean_job" / "input" / "lib" / "job.py"
        grafo = construir(fonte.read_text(encoding="utf-8"), "job.py")
        assert set(_nomes_de_dataset(grafo)) == {DINAMICO}
        assert grafo.datasets_resolvidos == 0

    def test_writeto_carrega_o_alvo_mesmo_com_append_terminal(self):
        fonte = 'df = spark.table("a.b")\ndf.writeTo("gold.x").append()\n'
        grafo = construir(fonte, "job.py")
        assert "gold.x" in _nomes_de_dataset(grafo)

    def test_origem_vem_da_api_e_nao_da_cara_da_string(self):
        fonte = 'a = spark.table("x")\na.write.saveAsTable("y")\nb = spark.read.parquet("z")\n'
        grafo = construir(fonte, "job.py")
        origens = {no.nome: no.origem for no in grafo.datasets}
        assert origens == {"x": "table", "y": "table", "z": "path"}


class TestLinhagemDeTabela:
    """SPEC 37: alvo, direcao, profundidade, com arquivo, linha, operacao e confianca."""

    def test_montante_devolve_as_tabelas_que_alimentam_o_alvo(self):
        grafo = construir(SPEC_35, "job.py")
        passos = linhagem_de_tabela(grafo, "gold.active_orders", MONTANTE, 5)
        assert [p.nome for p in passos] == ["bronze.orders", "silver.users"]

    def test_cada_passo_carrega_arquivo_linha_operacao_e_confianca(self):
        grafo = construir(SPEC_35, "job.py")
        passo = linhagem_de_tabela(grafo, "gold.active_orders", MONTANTE, 5)[0]
        assert passo.caminho == "job.py"
        assert passo.linha == 2
        assert passo.operacao == "READ"
        assert passo.confianca == 1.0

    def test_jusante_devolve_o_que_o_alvo_alimenta(self):
        grafo = construir(SPEC_35, "job.py")
        passos = linhagem_de_tabela(grafo, "bronze.orders", JUSANTE, 5)
        assert [p.nome for p in passos] == ["gold.active_orders"]

    def test_profundidade_conta_salto_entre_tabelas_e_nao_aresta(self):
        """Entre `gold.c` e `bronze.a` ha oito arestas e duas tabelas. Se a
        profundidade contasse aresta, `profundidade=1` nao alcancaria
        `silver.b`."""
        a = construir(
            'x = spark.table("bronze.a")\n'
            'y = x.filter("f").select("s").withColumn("c", 1).distinct()\n'
            'y.writeTo("silver.b").append()\n',
            "a.py",
        )
        b = construir(
            'z = spark.table("silver.b")\nz.writeTo("gold.c").append()\n',
            "b.py",
        )
        grafo = mesclar([a, b])
        um = linhagem_de_tabela(grafo, "gold.c", MONTANTE, 1)
        dois = linhagem_de_tabela(grafo, "gold.c", MONTANTE, 2)
        assert [p.nome for p in um] == ["silver.b"]
        assert [(p.nome, p.profundidade) for p in dois] == [
            ("silver.b", 1),
            ("bronze.a", 2),
        ]

    def test_linhagem_atravessa_arquivo(self):
        """`mesclar` junta a escrita de um arquivo com a leitura do outro porque
        o id de dataset RESOLVIDO nao carrega caminho."""
        grafo = mesclar(
            [
                construir('a = spark.table("b.x")\na.writeTo("s.y").append()\n', "a.py"),
                construir('c = spark.table("s.y")\nc.writeTo("g.z").append()\n', "b.py"),
            ]
        )
        passos = linhagem_de_tabela(grafo, "g.z", MONTANTE, 5)
        assert [(p.nome, p.caminho) for p in passos] == [("s.y", "b.py"), ("b.x", "a.py")]

    def test_ciclo_nao_causa_travessia_infinita(self):
        """Uma tabela lida e escrita pelo mesmo job e um ciclo. Sem o conjunto de
        visitados a travessia a reemite a cada nivel ate o teto."""
        fonte = 'df = spark.table("t.x")\ndf.filter("f").writeTo("t.x").append()\n'
        grafo = construir(fonte, "job.py")
        passos = linhagem_de_tabela(grafo, "t.x", MONTANTE, 50)
        assert passos == ()

    def test_cada_tabela_sai_uma_vez_na_menor_profundidade(self):
        """Duas rotas ate a mesma tabela nao a fazem sair duas vezes."""
        fonte = (
            'a = spark.table("bronze.a")\n'
            'b = spark.table("bronze.a")\n'
            'c = a.join(b, "k")\n'
            'c.writeTo("gold.c").append()\n'
        )
        grafo = construir(fonte, "job.py")
        passos = linhagem_de_tabela(grafo, "gold.c", MONTANTE, 5)
        assert [(p.nome, p.profundidade) for p in passos] == [("bronze.a", 1)]

    def test_alvo_ausente_devolve_vazio_e_nao_levanta(self):
        """Perguntar pela linhagem de uma tabela que este codigo nao toca e
        pergunta legitima; a resposta e "nenhuma"."""
        grafo = construir(SPEC_35, "job.py")
        assert linhagem_de_tabela(grafo, "nao.existe", MONTANTE, 5) == ()

    def test_direcao_invalida_levanta(self):
        grafo = construir(SPEC_35, "job.py")
        with pytest.raises(ValueError, match="direcao invalida"):
            linhagem_de_tabela(grafo, "gold.active_orders", "para_cima", 5)

    def test_passo_carrega_se_o_dataset_esta_resolvido(self):
        fonte = 'df = spark.table(nome)\ndf.writeTo("gold.x").append()\n'
        grafo = construir(fonte, "job.py")
        (passo,) = linhagem_de_tabela(grafo, "gold.x", MONTANTE, 5)
        assert passo.nome == DINAMICO
        assert passo.resolvido is False


class TestLinhagemDeDataFrame:
    """SPEC 36: o DataFrame e entidade, e responde montante e jusante."""

    def test_montante_de_dataframe_mostra_os_intermediarios(self):
        grafo = construir(SPEC_35, "job.py")
        (escrita,) = [a for a in grafo.arestas if a.operacao == "WRITE"]
        passos = montante(grafo, escrita.origem, 10)
        assert [p.operacao for p in passos] == ["FILTER", "JOIN", "JOIN", "READ", "READ"]

    def test_jusante_de_dataframe_chega_na_tabela_escrita(self):
        grafo = construir(SPEC_35, "job.py")
        (leitura,) = [a for a in grafo.arestas if a.linha == 2]
        passos = jusante(grafo, leitura.destino, 10)
        assert passos[-1].nome == "gold.active_orders"

    def test_no_ausente_devolve_vazio(self):
        grafo = construir(SPEC_35, "job.py")
        assert montante(grafo, "node_inexistente", 3) == ()

    def test_direcao_invalida_levanta(self):
        grafo = construir(SPEC_35, "job.py")
        with pytest.raises(ValueError, match="direcao invalida"):
            lineage._travessia_completa(grafo, "x", "para_o_lado", 1)


class TestSqlNaoVirouAresta:
    def test_spark_sql_registra_ponto_cego_e_nao_inventa_direcao(self):
        """A direcao de um `spark.sql` so se sabe lendo a query: `SELECT` le,
        `MERGE INTO` escreve. Uma aresta na direcao errada manda quem investiga
        para o lado oposto do fluxo."""
        grafo = construir('df = spark.sql("SELECT * FROM bronze.x")\n', "job.py")
        assert grafo.arestas == ()
        assert [n.reason for n in grafo.nao_resolvidos] == [SQL_NOT_PARSED]

    def test_sql_dinamico_e_dynamic_table_identifier(self):
        grafo = construir('df = spark.sql(f"MERGE INTO {alvo} USING u ON 1=1")\n', "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.reason == DYNAMIC_TABLE_IDENTIFIER
        assert nao_resolvido.variaveis == ("alvo",)

    def test_o_template_nao_recebe_o_corpo_da_query(self):
        """O campo e para nome de tabela; um bloco de SQL ali seria fonte
        arrastada para um lugar onde quem le espera um identificador."""
        grafo = construir('df = spark.sql(f"MERGE INTO {alvo} USING u ON 1=1")\n', "job.py")
        (nao_resolvido,) = grafo.nao_resolvidos
        assert nao_resolvido.template == DINAMICO

    def test_dataframe_de_sql_segue_encadeavel_sem_procedencia(self):
        fonte = 'df = spark.sql("SELECT 1")\ndf.writeTo("gold.x").append()\n'
        grafo = construir(fonte, "job.py")
        assert [a.operacao for a in grafo.arestas] == ["WRITE"]


class TestRobustez:
    def test_fonte_que_nao_parseia_devolve_grafo_vazio(self):
        grafo = construir("def f(:\n", "quebrado.py")
        assert grafo == lineage.GrafoDeDados()

    def test_byte_nulo_nao_derruba(self):
        """A excecao do byte nulo mudou de tipo entre 3.10 e 3.11 -- medido em
        `extract.py`, mesma arvore."""
        assert construir("a = 1\x00", "quebrado.py").nos == ()

    def test_dispatch_dinamico_nao_estoura_nem_gasta_aninhamento(self):
        """`getattr(df, metodo)(1)` nao tem espinha de atributo para andar."""
        fonte = FIXTURES / "dynamic_dispatch" / "input" / "lib" / "job.py"
        grafo = construir(fonte.read_text(encoding="utf-8"), "job.py")
        assert grafo.nao_resolvidos == ()
        assert grafo.arestas == ()

    def test_cadeia_de_duzentos_elos_e_percorrida_inteira(self):
        """A espinha fluente e andada por laco, e por isso o comprimento dela
        nao soma profundidade de recursao em `_cadeia`."""
        fonte = 'df = spark.table("a.b")' + '.filter("x")' * 200 + "\n"
        grafo = construir(fonte, "job.py")
        assert len([a for a in grafo.arestas if a.operacao == "FILTER"]) == 200

    def test_cadeia_profunda_demais_vira_ponto_cego_contado(self):
        """O teto nao e de `_cadeia`: e de `VisitanteComEscopo`, que herda de
        `ast.NodeVisitor` e desce a arvore por recursao Python. MEDIDO em
        3.10.20, 3.11.15 e 3.14.6, com o mesmo resultado nas tres: 200 elos
        passam, 250 nao. O mesmo insumo faz `extract.extrair_nos`
        LEVANTAR -- e a mesma pilha compartilhada -- e aqui vira registro, para
        que "profundo demais" nao se confunda com "sem PySpark"."""
        fonte = 'df = spark.table("a.b")' + '.filter("x")' * 500 + "\n"
        grafo = construir(fonte, "job.py")
        assert [n.reason for n in grafo.nao_resolvidos] == [lineage.NESTED_TOO_DEEP]
        assert grafo.arestas == ()

    def test_o_mesmo_insumo_levanta_no_extrator_de_simbolos(self):
        """Registro da medicao que justifica a captura acima. Se um dia
        `extract` parar de levantar, a captura passa a ser desnecessaria e este
        teste e onde isso aparece."""
        fonte = 'df = spark.table("a.b")' + '.filter("x")' * 500 + "\n"
        with pytest.raises(RecursionError):
            extract.extrair_nos(fonte, "job.py")

    def test_aninhamento_extremo_vira_ponto_cego_e_nao_excecao(self):
        """Uma biblioteca nao pode deixar `RecursionError` vazar por causa da
        forma do codigo do repositorio analisado."""
        fonte = "df = " + "broadcast(" * 200 + "x" + ")" * 200 + "\n"
        grafo = construir(fonte, "job.py")
        assert [n.reason for n in grafo.nao_resolvidos] == [lineage.NESTED_TOO_DEEP]

    def test_todas_as_fixtures_constroem_sem_levantar(self):
        for caminho in _fixtures():
            construir(caminho.read_text(encoding="utf-8"), caminho.name)


class TestConcordanciaComOExtrator:
    """A deteccao de leitura/escrita aqui e a de `pyspark_ast`, e nao uma segunda.

    Uma segunda lista de metodos divergiria da primeira em silencio, e a
    divergencia so apareceria como aresta faltando. Estes testes medem as duas
    sobre o corpus e falham se elas se separarem.
    """

    def test_contagem_de_leitura_e_escrita_bate_com_os_facts(self):
        leituras = escritas = 0
        facts_leitura = facts_escrita = 0
        for caminho in _fixtures():
            fonte = caminho.read_text(encoding="utf-8")
            grafo = construir(fonte, caminho.name)
            leituras += grafo.leituras_detectadas
            escritas += grafo.escritas_detectadas
            facts = extract_source(fonte, caminho.name)
            facts_leitura += sum(1 for f in facts if f.kind == "pyspark.read")
            facts_escrita += sum(1 for f in facts if f.kind == "pyspark.write")
        assert (leituras, escritas) == (facts_leitura, facts_escrita)

    def test_o_corpus_tem_leitura_e_escrita_para_a_comparacao_valer(self):
        """Sem isto a igualdade acima seria 0 == 0 -- verdadeira e vazia."""
        grafo = mesclar(
            [construir(c.read_text(encoding="utf-8"), c.name) for c in _fixtures()]
        )
        assert grafo.leituras_detectadas > 0
        assert grafo.escritas_detectadas > 0

    def test_deteccao_e_ligacao_sao_numeros_diferentes(self):
        """`df.writeTo("db.tbl").append()` com `df` de fora do escopo e uma
        escrita DETECTADA e zero aresta. Confundir os dois faria "o extrator
        viu" passar por "o grafo ligou"."""
        fonte = FIXTURES / "version_out_of_scope" / "input" / "lib" / "job.py"
        grafo = construir(fonte.read_text(encoding="utf-8"), "job.py")
        assert grafo.escritas_detectadas == 1
        assert grafo.arestas == ()
        assert "db.tbl" in _nomes_de_dataset(grafo)


class TestTaxaDeResolucao:
    """A taxa e publicada com as duas contagens, e nao sozinha.

    Uma taxa que so conta acerto melhora quando alguem para de tentar. As duas
    contagens andam juntas, e o teste prende a RAZAO -- nao um valor absoluto,
    que envelheceria a cada fixture nova.
    """

    def test_zero_dataset_devolve_zero_e_nao_cem_por_cento(self):
        assert construir("x = 1\n", "job.py").taxa_de_resolucao == 0.0

    def test_resolvidos_mais_dinamicos_dao_o_total_de_datasets(self):
        grafo = mesclar(
            [construir(c.read_text(encoding="utf-8"), c.name) for c in _fixtures()]
        )
        assert grafo.datasets_resolvidos + grafo.datasets_dinamicos == len(grafo.datasets)

    def test_no_corpus_a_maioria_dos_datasets_e_dinamica(self):
        """Medido, nao esperado: as fixtures leem e escrevem por parametro, e so
        `version_out_of_scope` nomeia uma tabela (`db.tbl`). Um dia em que a
        maioria virar resolvida sem fixture nova significa que alguem passou a
        inventar nome, e este teste e onde isso aparece."""
        grafo = mesclar(
            [construir(c.read_text(encoding="utf-8"), c.name) for c in _fixtures()]
        )
        assert grafo.datasets_dinamicos > grafo.datasets_resolvidos
        assert grafo.datasets_resolvidos >= 1


class TestMutacaoDaRegraDeNaoInventar:
    """Prova que a afirmacao da SPEC 38 nao e vazia.

    Um teste que afirma ausencia passa tambem quando o codigo nunca produz nada.
    Aqui o modulo e mutado numa COPIA em tmpdir -- a arvore de trabalho nao e
    tocada, pelo mesmo cuidado de `test_codeintel_security.py` -- para inventar
    o nome a partir do texto da expressao. Com a mutacao, a mesma propriedade
    que `TestNomeDinamico` afirma tem que FALHAR. Se passar nos dois, ela nao
    esta prendendo nada.
    """

    @staticmethod
    def _carregar_mutado(tmp_path, velho: str, novo: str):
        copia = tmp_path / "lineage_mutado.py"
        shutil.copyfile(MODULO, copia)
        fonte = copia.read_text(encoding="utf-8")
        assert fonte.count(velho) == 1, "a linha alvo da mutacao mudou de forma"
        copia.write_text(fonte.replace(velho, novo), encoding="utf-8")
        spec = importlib.util.spec_from_file_location("lineage_mutado", copia)
        modulo = importlib.util.module_from_spec(spec)
        # Registrado em `sys.modules` ANTES de executar porque `dataclasses`
        # resolve anotacao de campo procurando o modulo da classe la dentro --
        # com `from __future__ import annotations` as anotacoes sao strings, e
        # sem o registro a resolucao acha `None` e levanta.
        sys.modules[spec.name] = modulo
        try:
            spec.loader.exec_module(modulo)
        finally:
            sys.modules.pop(spec.name, None)
        return modulo

    def test_mutante_que_inventa_nome_produz_a_tabela_que_nao_existe(self, tmp_path):
        mutado = self._carregar_mutado(
            tmp_path,
            "        nome = _texto_literal(alvo) if alvo is not None else None",
            "        nome = (_texto_literal(alvo) or ast.unparse(alvo)) if alvo else None",
        )
        grafo = mutado.construir('df = spark.table(f"{database}.{table}")\n', "job.py")
        (dataset,) = grafo.datasets
        assert dataset.nome != DINAMICO
        assert dataset.resolvido is True
        assert grafo.nao_resolvidos == ()

    def test_o_modulo_real_nao_faz_isso(self, tmp_path):
        """O outro lado da mutacao, lado a lado, para a comparacao ser visivel."""
        del tmp_path
        grafo = construir('df = spark.table(f"{database}.{table}")\n', "job.py")
        assert [no.nome for no in grafo.datasets] == [DINAMICO]
        assert [n.reason for n in grafo.nao_resolvidos] == [DYNAMIC_TABLE_IDENTIFIER]

    def test_mutante_que_solta_o_receptor_inventa_aresta(self, tmp_path):
        """A segunda regra: aceitar receptor desconhecido criaria aresta a
        partir de um no que o grafo nao conhece."""
        mutado = self._carregar_mutado(
            tmp_path,
            "        if corrente is None:\n"
            "            self._receptor_desconhecido(linha, operacao)\n"
            "            return None",
            "        if corrente is None:\n"
            "            corrente = self._dataframe_anonimo(linha)",
        )
        grafo = mutado.construir('def f(df):\n    return df.filter("x")\n', "job.py")
        assert [a.operacao for a in grafo.arestas] == ["FILTER"]
        assert grafo.nao_resolvidos == ()
