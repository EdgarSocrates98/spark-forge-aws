"""Job de grafo correto no codigo, com o jar declarado por valor interpolado.

Glue 5.0 e Spark 3.5.4 DE PROPOSITO, e nao 4.0 como o par de disponibilidade:
aqui ha artefato publicado, entao `SF-GRAPH-002` fica fora e o unico eixo em
jogo e o do IaC. O codigo esta certo em todos os eixos que o corpus mede --
checkpoint configurado, vertices e arestas persistidos.

O que decide o destino deste job NAO esta neste arquivo: esta no `main.tf` ao
lado, onde `--extra-jars` existe com um valor que so o `terraform apply`
resolve.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.sparkContext.setCheckpointDir("s3://checkpoints/grafo/")
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
