"""Job que grava em modo append, com GlueContext inicializado.

`max_retries = 3` mais escrita `append` e a combinacao que duplica dado: a
retentativa reexecuta a escrita, e append nao e idempotente.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    glue_context = GlueContext(SparkContext.getOrCreate())
    spark = glue_context.spark_session

    eventos = spark.read.parquet("s3://lake/raw/eventos/")
    eventos.write.mode("append").parquet("s3://lake/curated/eventos/")


if __name__ == "__main__":
    main()
