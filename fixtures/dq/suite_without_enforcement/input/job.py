"""Cadastro de clientes: valida com PyDeequ e guarda o relatorio de qualidade.

O resultado da suite vira uma tabela de metricas em
`s3://lake/quality/clientes/`. Nada no job LE esse resultado para decidir se a
carga continua: a suite acusa, o relatorio registra, e o job publica do mesmo
jeito.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pydeequ.checks import Check, CheckLevel
from pydeequ.verification import VerificationResult, VerificationSuite
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    clientes = (
        spark.read.option("mergeSchema", "true")
        .parquet("s3://lake/raw/clientes/")
        .withColumn("uf", F.upper(F.col("uf")))
        .dropDuplicates(["cliente_id"])
    )

    resultado = (
        VerificationSuite(spark)
        .onData(clientes)
        .addCheck(
            Check(spark, CheckLevel.Error, "integridade do cadastro")
            .isComplete("cliente_id")
            .isUnique("cliente_id")
            .isContainedIn("uf", ["SP", "RJ", "MG", "RS", "BA"])
        )
        .run()
    )

    relatorio = VerificationResult.checkResultsAsDataFrame(spark, resultado)
    relatorio.withColumn("data_ref", F.lit(args["data_ref"])).write.mode("append").parquet(
        "s3://lake/quality/clientes/"
    )

    clientes.write.mode("overwrite").parquet("s3://lake/curated/clientes/")


if __name__ == "__main__":
    main()
