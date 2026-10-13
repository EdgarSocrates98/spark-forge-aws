"""Terceira forma de escrever certo: `use_local_checkpoints=True` (0.9.3+).

Sem diretorio persistente nao ha excecao. O nome vem em `snake_case` porque e
da linhagem `io.graphframes`, e as duas convencoes convivem no mesmo objeto.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents(use_local_checkpoints=True)
