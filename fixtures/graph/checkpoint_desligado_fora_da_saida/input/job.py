"""O `<= 0` que NAO e tambem saida legitima, que era o outro buraco do corpus.

`saida_intervalo_nao_positivo` ja tinha o valor nao positivo, mas em
`connectedComponents` -- onde desligar o checkpoint e uma das saidas
documentadas da exigencia que `SF-GRAPH-001` julga, e o proprio `meta.yaml`
declara aquele arquivo correto.

Aqui o algoritmo e `labelPropagation`, que na linhagem `io.graphframes` expoe
`checkpoint_interval` e e iterativo do mesmo jeito -- mas nao levanta
`IOException` sem diretorio, entao nao ha excecao da qual escapar. Desligar o
checkpoint aqui e so o plano logico crescendo sem teto.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def build_spark():
    spark = SparkSession.builder.appName("comunidades").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/comunidades/")
    return spark


def comunidades(spark):
    vertices = spark.read.parquet("s3://dados/vertices/")
    arestas = spark.read.parquet("s3://dados/arestas/")
    v = vertices.cache()
    e = arestas.cache()
    g = GraphFrame(v, e)
    return g.labelPropagation(maxIter=5, checkpoint_interval=0)
