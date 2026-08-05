"""Quarta forma de escrever certo, e ela as vezes ESTA no `.py`.

`spark.conf.set("spark.checkpoint.dir", ...)` satisfaz a exigencia sem nenhum
`setCheckpointDir`. Tratar a conf como se fosse sempre externa faria a regra P0
disparar sobre codigo que configurou o checkpoint na linha de cima.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set("spark.checkpoint.dir", "s3://checkpoints/grafo/")
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
