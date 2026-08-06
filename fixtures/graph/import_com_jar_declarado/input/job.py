"""Job de grafo correto no codigo, num runtime onde a plataforma nao instala.

Glue 4.0 e Spark 3.3.0, e NENHUMA linhagem de GraphFrames publicou artefato
para Spark 3.3: `0.8.2` para em 3.2, `0.8.3` comeca em 3.4, `io.graphframes`
compila contra 3.5. O codigo esta certo em todos os eixos que o corpus mede --
checkpoint configurado, vertices e arestas persistidos.

O que decide o destino deste job NAO esta neste arquivo: esta no `main.tf` ao
lado. Por isso as duas fixtures do par compartilham este `.py` byte a byte, e a
unica diferenca entre elas e o `--extra-jars`.
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
