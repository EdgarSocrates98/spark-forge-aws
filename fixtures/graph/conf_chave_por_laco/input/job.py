"""As confs aplicadas por LACO, que e como um job parametrizado as declara.

`for chave, valor in CONFS.items(): spark.conf.set(chave, valor)` pode conter
`spark.checkpoint.dir` e pode nao conter -- o `.py` nao diz qual, porque a chave
so existe em runtime. A resposta e "nao sei": decisao de exigencia OMITIDA e
ponto cego contado.
"""
from graphframes import GraphFrame
from pyspark.sql import SparkSession

CONFS = {
    "spark.checkpoint.dir": "s3://checkpoints/grafo/",
    "spark.sql.shuffle.partitions": "400",
}


def componentes():
    spark = SparkSession.builder.appName("grafo").getOrCreate()
    for chave, valor in CONFS.items():
        spark.conf.set(chave, valor)
    v = spark.read.parquet("s3://dados/vertices/").cache()
    e = spark.read.parquet("s3://dados/arestas/").cache()
    g = GraphFrame(v, e)
    return g.connectedComponents()
