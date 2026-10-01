"""Segunda forma de escrever certo: `checkpointInterval` nao positivo.

`shouldCheckpoint = checkpointInterval > 0`: com valor nao positivo o bloco
inteiro e pulado e nenhum diretorio e exigido. O `-1` esta na fonte como
`UnaryOp(USub, Constant)`, e ler o sinal e o que separa esta fixture de um
falso P0.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents(checkpointInterval=-1)
