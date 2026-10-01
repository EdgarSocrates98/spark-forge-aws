"""A outra grafia da quarta forma: a conf de local checkpoints, ligada no job.

`spark.graphframes.useLocalCheckpoints=true` dispensa o diretorio do mesmo
jeito que o argumento `use_local_checkpoints`, e o valor da conf do Spark e
STRING -- e o `_truthy` que le `"true"` e nao um booleano de Python.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set("spark.graphframes.useLocalCheckpoints", "true")
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
