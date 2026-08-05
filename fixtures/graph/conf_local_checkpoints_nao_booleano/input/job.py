"""O valor da conf que E literal e mesmo assim nao da para ler.

`spark.conf.set("spark.graphframes.useLocalCheckpoints", 1)` passa `1`, que e
literal na fonte e nao e booleano do Spark: `java.lang.Boolean.parseBoolean` so
converte "true" e "false", e `1` chega ao runtime como falso. Chamar isso de
`non_literal_argument` mandava quem le o ponto cego procurar uma variavel que
nao existe -- o rotulo certo e `non_boolean_value`.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    spark.conf.set("spark.graphframes.useLocalCheckpoints", 1)
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
