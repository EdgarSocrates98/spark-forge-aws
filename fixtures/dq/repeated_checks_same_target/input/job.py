"""Carga de pagamentos com duas validacoes artesanais sobre o mesmo alvo.

O DataFrame esta em cache -- entao nenhum dos checks recomputa o lineage --,
mas cada `count()` ainda e uma varredura propria do dado persistido: dois
checks sobre `pagamentos` sao duas passadas, e uma suite unica faria o mesmo
trabalho num agrupamento so.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    pagamentos = (
        spark.read.parquet("s3://lake/raw/pagamentos/")
        .filter(F.col("data_ref") == args["data_ref"])
        .withColumn("valor", F.col("valor_centavos") / 100.0)
    )
    pagamentos.cache()

    sem_id = pagamentos.filter(F.col("pagamento_id").isNull()).count()
    negativos = pagamentos.filter(F.col("valor") < 0).count()

    if sem_id > 0 or negativos > 0:
        raise ValueError(
            f"pagamentos invalidos em {args['data_ref']}: "
            f"{sem_id} sem id, {negativos} com valor negativo"
        )

    pagamentos.write.mode("overwrite").parquet("s3://lake/curated/pagamentos/")
    pagamentos.unpersist()


if __name__ == "__main__":
    main()
