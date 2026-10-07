"""O positivo da exigencia de checkpoint, e so ele.

Vertices e arestas persistidos, nada dentro de laco, nenhum ponto cego: o
UNICO defeito e que `connectedComponents` roda sem diretorio de checkpoint em
lugar nenhum do arquivo, e a implementacao default levanta `java.io.IOException`
na primeira iteracao.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    vertices = spark.read.parquet("s3://dados/vertices/")
    arestas = spark.read.parquet("s3://dados/arestas/")
    v = vertices.cache()
    e = arestas.cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
