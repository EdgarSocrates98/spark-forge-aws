"""A forma de `SF-DQ-003` com outro sujeito: a aresta que sera relida.

Checkpoint configurado, vertices em `cache()`, e as arestas nao. O algoritmo
itera sobre as arestas; sem persistencia, cada iteracao refaz a leitura do S3.
O UNICO eixo defeituoso e `edges_persisted`.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/grafo/")
    vertices = spark.read.parquet("s3://dados/vertices/").cache()
    arestas = spark.read.parquet("s3://dados/arestas/")
    g = GraphFrame(vertices, arestas)
    return g.connectedComponents()
