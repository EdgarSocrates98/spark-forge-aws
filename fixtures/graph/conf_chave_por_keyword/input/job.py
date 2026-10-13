"""A conf declarada por KEYWORD, que e assinatura publica de `RuntimeConfig`.

`spark.conf.set(key=..., value=...)` e a mesma chamada da forma posicional, e
ate a revisao da Fase 6a o extrator so olhava `node.args` -- a chave estava
literal, legivel, e mesmo assim o arquivo saia com
`checkpoint_configured_in_module: false`.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set(key="spark.checkpoint.dir", value="s3://checkpoints/grafo/")
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
