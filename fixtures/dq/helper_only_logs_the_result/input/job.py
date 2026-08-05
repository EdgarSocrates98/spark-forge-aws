"""Vendas do dia: o helper recebe a contagem e SO REGISTRA. O job publica.

Espelho negativo de `enforcement_behind_helper`, e a chamada e byte a byte a
mesma forma: `registra_qualidade(negativas, "...")` passa o resultado do check
por parametro a uma funcao deste modulo, que le esse parametro num `if`.

O que muda e o corpo: `logger.warning` no lugar do `raise`. Protecao pela metade
-- ler o resultado e apenas registrar -- nao e consequencia, e chamar isso de
consequencia calaria `SF-DQ-002` exatamente sobre o defeito que ela existe para
achar. O job termina verde com dado invalido, e a linha no log e a crenca de que
ha garantia.
"""
import logging
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

LOGGER = logging.getLogger(__name__)


def registra_qualidade(quantidade, mensagem):
    """Anota a contagem no log do driver. Nada para o job."""
    if quantidade > 0:
        LOGGER.warning("%s: %s linhas", mensagem, quantidade)


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session
    job = Job(glue)
    job.init(args["JOB_NAME"], args)

    vendas = spark.read.parquet("s3://lake/raw/vendas/").filter(
        F.col("data_ref") == args["data_ref"]
    )
    vendas.cache()

    negativas = vendas.filter(F.col("valor_total") < 0).count()
    registra_qualidade(negativas, "vendas com valor negativo")

    vendas.write.mode("overwrite").partitionBy("data_ref").parquet(
        "s3://lake/curated/vendas/"
    )
    vendas.unpersist()
    job.commit()


if __name__ == "__main__":
    main()
