"""Suite PyDeequ com consequencia, para fixar os ATRIBUTOS do kind.

Tres restricoes numa `VerificationSuite` unica: o runner agrupa as agregacoes
que compartilham agrupamento, entao a suite nao custa uma passada por check --
`shares_scan` e `true`. O quanto ela custa depende do agrupamento de cada
restricao, e o `.py` nao diz quantas passadas sao: por isso o fact NAO afirma
`single_pass`, e NAO conta as restricoes declaradas.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pydeequ.checks import Check, CheckLevel
from pydeequ.verification import VerificationSuite
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    assinaturas = (
        spark.read.parquet("s3://lake/raw/assinaturas/")
        .filter(F.col("data_ref") == args["data_ref"])
        .withColumn("mrr", F.col("valor_mensal") * F.col("assentos"))
    )
    assinaturas.cache()

    resultado = (
        VerificationSuite(spark)
        .onData(assinaturas)
        .addCheck(
            Check(spark, CheckLevel.Error, "assinaturas ativas")
            .isComplete("assinatura_id")
            .isNonNegative("mrr")
            .hasMin("assentos", lambda v: v >= 1)
        )
        .run()
    )

    if resultado.status != "Success":
        sys.exit(1)

    assinaturas.write.mode("overwrite").parquet("s3://lake/curated/assinaturas/")
    assinaturas.unpersist()


if __name__ == "__main__":
    main()
