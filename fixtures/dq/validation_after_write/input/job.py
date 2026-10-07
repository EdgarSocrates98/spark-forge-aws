"""Consolidacao diaria de vendas na camada curated.

O job publica a particao do dia e SO DEPOIS conta as linhas com valor
negativo. Quando a validacao acusa, o dado ruim ja esta em
`s3://lake/curated/vendas/` e ja e visivel para o Athena.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session
    job = Job(glue)
    job.init(args["JOB_NAME"], args)

    pedidos = spark.read.parquet("s3://lake/raw/pedidos/")
    itens = spark.read.parquet("s3://lake/raw/itens/")

    vendas = (
        pedidos.join(itens, "pedido_id", "inner")
        .withColumn("valor_total", F.col("quantidade") * F.col("preco_unitario"))
        .withColumn("data_ref", F.lit(args["data_ref"]))
        .select("pedido_id", "cliente_id", "data_ref", "valor_total")
    )

    vendas.write.mode("overwrite").format("parquet").partitionBy("data_ref").save(
        "s3://lake/curated/vendas/"
    )

    negativos = vendas.filter(F.col("valor_total") < 0).count()
    if negativos > 0:
        raise ValueError(f"{negativos} vendas com valor_total negativo em {args['data_ref']}")

    job.commit()


if __name__ == "__main__":
    main()
