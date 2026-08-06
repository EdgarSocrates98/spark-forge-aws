"""A chave da conf que vem por CONSTANTE, e nao por literal na chamada.

`spark.conf.set(CHECKPOINT_DIR, ...)` configura o checkpoint tao bem quanto a
forma literal, mas este modulo nao segue o valor de um nome ate a atribuicao --
inferencia entre escopos e o que ele recusa em toda parte. Entao a decisao de
exigencia e OMITIDA e o ponto cego sai CONTADO, em vez de o arquivo sair
afirmando `checkpoint_configured_in_module: false` sobre dado que ninguem leu.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession

CHECKPOINT_DIR = "spark.checkpoint.dir"


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set(CHECKPOINT_DIR, "s3://checkpoints/grafo/")
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
