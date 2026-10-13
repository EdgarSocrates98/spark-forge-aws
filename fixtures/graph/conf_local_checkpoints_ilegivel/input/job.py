"""A conf de local checkpoints com valor que o `.py` nao permite ler.

O valor vem por parametro, entao o arquivo nao diz se o checkpoint local esta
ligado. A decisao de exigencia e OMITIDA de TODA chamada do arquivo -- alcance
de arquivo, porque `SparkContext` e singleton do processo -- e o ponto cego sai
contado em `graph.unresolved`. Afirmar exigencia aqui seria um P0 sobre codigo
que talvez esteja correto.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes(local):
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set("spark.graphframes.useLocalCheckpoints", local)
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
