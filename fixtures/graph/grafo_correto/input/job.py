"""A metade negativa do corpus: o mesmo job de grafo, feito do jeito certo.

Checkpoint configurado NOUTRA funcao (a forma canonica de job Glue/EMR),
vertices e arestas persistidos pela forma mais comum -- `v = vertices.cache()`
--, e um `pageRank` que limita por `tol` em vez de `maxIter`, que e modo
oficial e NAO e defeito.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def build_spark():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/grafo/")
    return spark


def componentes(spark):
    vertices = spark.read.parquet("s3://dados/vertices/")
    arestas = spark.read.parquet("s3://dados/arestas/")
    v = vertices.cache()
    e = arestas.cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()


def ranking(spark, v, e):
    g = GraphFrame(v.cache(), e.cache())
    return g.pageRank(tol=0.01)
