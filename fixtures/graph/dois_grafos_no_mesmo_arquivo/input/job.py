"""DOIS grafos e DOIS lacos no mesmo arquivo, cada um com seu proprio defeito.

O corpus da Task 5 nao tinha nenhuma fixture com duas construcoes defeituosas
nem com dois lacos, e por isso o `same_subject: true` de `SF-GRAPH-003` e de
`SF-GRAPH-004` podia ser apagado com a suite inteira verde: com um sujeito so,
a regra por entidade e a regra por conjunto produzem o mesmo numero de achados.

Aqui elas divergem: sao DOIS achados de cada regra, e apagar qualquer um dos
dois `same_subject` derruba este golden para um.

OS DOIS GRAFOS ESTAO EM FUNCOES DIFERENTES, e isso e medicao e nao estilo.
`engine._subject_group_key` usa `subject.symbol` quando ele existe, e o `symbol`
de todo fact deste extrator e a FUNCAO que contem o no. Duas construcoes na
MESMA funcao caem no mesmo grupo e viram um achado so -- limite declarado em
`rules/catalog/graph.yaml`, na nota de `SF-GRAPH-003`.

O checkpoint esta configurado de proposito: o eixo em teste aqui e a contagem
de sujeitos, e um P0 de `SF-GRAPH-001` por cima confundiria a leitura.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def _sessao():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/grafo/")
    return spark


def componentes_de_clientes(dias):
    spark = _sessao()
    v = spark.read.parquet("s3://dados/clientes/vertices/").cache()
    e = spark.read.parquet("s3://dados/clientes/arestas/")
    grafo = GraphFrame(v, e)
    saida = []
    for _dia in dias:
        saida.append(grafo.connectedComponents())
    return saida


def componentes_de_produtos(dias):
    spark = _sessao()
    v = spark.read.parquet("s3://dados/produtos/vertices/").cache()
    e = spark.read.parquet("s3://dados/produtos/arestas/")
    grafo = GraphFrame(v, e)
    saida = []
    for _dia in dias:
        saida.append(grafo.connectedComponents())
    return saida
