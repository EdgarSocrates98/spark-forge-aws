"""A metade negativa do corpus: o mesmo job, feito do jeito certo.

Um unico check, sobre um DataFrame persistido, ANTES do write, e com
consequencia: quando a validacao acusa, o job aborta e nada e publicado.
Nenhuma das quatro regras SF-DQ deve disparar aqui.
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

    estoque = (
        spark.read.parquet("s3://lake/raw/estoque/")
        .filter(F.col("data_ref") == args["data_ref"])
        .withColumn("saldo", F.col("entradas") - F.col("saidas"))
    )
    estoque.cache()

    saldo_negativo = estoque.filter(F.col("saldo") < 0).count()
    if saldo_negativo > 0:
        raise ValueError(f"{saldo_negativo} SKUs com saldo negativo em {args['data_ref']}")

    estoque.write.mode("overwrite").partitionBy("data_ref").parquet("s3://lake/curated/estoque/")
    estoque.unpersist()
    job.commit()


if __name__ == "__main__":
    main()
