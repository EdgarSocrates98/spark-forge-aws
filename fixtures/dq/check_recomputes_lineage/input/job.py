"""Enriquecimento de transacoes com a dimensao de cambio.

O DataFrame validado nao esta persistido e e reusado depois do check: o
`count()` da validacao paga o join e a janela inteiros, e o `write` seguinte
paga tudo de novo.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import Window
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    transacoes = spark.read.parquet("s3://lake/raw/transacoes/")
    cambio = spark.read.parquet("s3://lake/ref/cambio/")

    ultima_cotacao = Window.partitionBy("moeda").orderBy(F.col("cotado_em").desc())

    enriquecido = (
        transacoes.join(F.broadcast(cambio), "moeda", "left")
        .withColumn("ordem", F.row_number().over(ultima_cotacao))
        .filter(F.col("ordem") == 1)
        .withColumn("valor_brl", F.col("valor") * F.col("taxa"))
        .drop("ordem")
    )

    sem_cotacao = enriquecido.filter(F.col("valor_brl").isNull()).count()
    if sem_cotacao > 0:
        raise ValueError(f"{sem_cotacao} transacoes sem cotacao em {args['data_ref']}")

    enriquecido.write.mode("overwrite").partitionBy("data_ref").parquet(
        "s3://lake/curated/transacoes/"
    )


if __name__ == "__main__":
    main()
