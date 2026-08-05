"""Construcao e algoritmo POR ITERACAO, e o import opcional dentro da funcao.

Um `GraphFrame` por dia processado: cada iteracao reconstroi o grafo e roda o
algoritmo inteiro. O import esta dentro de `try:` dentro da funcao -- o idioma
de dependencia opcional --, e continua sendo evidencia de que este job usa
GraphFrames: `scope: function`, `guarded: true`, com alias.
"""
from pyspark.sql import SparkSession


def por_dia(dias):
    try:
        from graphframes import GraphFrame as GF
    except ImportError:
        return []
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/grafo/")
    saida = []
    for dia in dias:
        v = spark.read.parquet("s3://dados/vertices/" + dia).cache()
        e = spark.read.parquet("s3://dados/arestas/" + dia).cache()
        g = GF(v, e)
        saida.append(g.connectedComponents())
    return saida
