"""O golden positivo que faltava: `checkpointInterval` acima do teto da fonte.

A doc diz "It is recommended to keep this value at `2` or below" e o codigo
avisa em `value <= 0 || value > 2`. Aqui o intervalo e `10`, e ESTE e o unico
eixo defeituoso: o checkpoint esta configurado em `build_spark`, vertices e
arestas estao persistidos, e nao ha laco -- entao nenhuma outra regra da area
pode disparar sobre este arquivo.
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
    return g.connectedComponents(checkpointInterval=10)
