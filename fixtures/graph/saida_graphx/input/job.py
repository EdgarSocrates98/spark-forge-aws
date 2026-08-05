"""Primeira das quatro formas de escrever certo: `algorithm="graphx"`.

A implementacao GraphX nao faz checkpoint, e a exigencia nao se aplica. Sem
esta fixture, uma regra que dispare sobre todo `connectedComponents` sem
diretorio acusaria quem escolheu a implementacao que dispensa o diretorio.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents(algorithm="graphx")
