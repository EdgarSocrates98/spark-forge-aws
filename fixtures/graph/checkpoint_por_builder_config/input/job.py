"""A conf de checkpoint declarada na CONSTRUCAO da sessao.

`SparkSession.builder.config("spark.checkpoint.dir", ...)` e a forma canonica de
declarar conf de cluster num job Glue ou EMR, e ate a revisao da Fase 6a este
extrator nao a lia: o vocabulario tinha `set` e nao tinha `config`, e o arquivo
saia com `checkpoint_configured_in_module: false` -- um P0 sobre codigo que
configurou o checkpoint na primeira linha da sessao.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = (
        SparkSession.builder.appName("grafo")
        .config("spark.checkpoint.dir", "s3://checkpoints/grafo/")
        .getOrCreate()
    )
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
