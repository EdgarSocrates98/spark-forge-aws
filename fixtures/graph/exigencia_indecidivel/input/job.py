"""Tres pontos cegos, um por chamada, e nenhuma acusacao.

`Fact.id` e sha de kind + subject + measures e deixa `attrs` de fora: dois
`graph.unresolved` sobre o MESMO no sairiam com id identico e o `fact_id` que um
Finding cita deixaria de identificar evidencia. Por isso e no maximo UM ponto
cego por chamada, com o argumento vindo antes do receptor.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def carregar(spark):
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    return GraphFrame(v, e)


def componentes(spark, escolha):
    g = carregar(spark)
    posicional = g.connectedComponents("graphx")
    variavel = g.connectedComponents(algorithm=escolha)
    anonimo = carregar(spark).pageRank(maxIter=5)
    return posicional, variavel, anonimo
