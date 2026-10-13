"""Great Expectations 1.x sobre um DataFrame Spark, na forma da documentacao.

O que o `.py` revela e o DataFrame sob a chave literal `"dataframe"` do dict de
`batch_parameters` -- montado numa linha e passado por nome na seguinte. As
expectativas em si vivem no store do contexto (`great_expectations.yml` e as
suites em JSON), fora deste arquivo: por isso o fact deste framework NAO afirma
nada sobre varredura compartilhada.
"""
import sys

import great_expectations as gx
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    faturas = (
        spark.read.parquet("s3://lake/raw/faturas/")
        .filter(F.col("data_ref") == args["data_ref"])
        .withColumn("total", F.col("subtotal") + F.col("impostos"))
    )

    contexto = gx.get_context(mode="file", project_root_dir="/opt/ml/gx")
    validation_definition = contexto.validation_definitions.get("faturas_diarias")

    batch_parameters = {"dataframe": faturas}
    resultado = validation_definition.run(batch_parameters=batch_parameters)

    if not resultado.success:
        raise ValueError(f"faturas reprovadas na suite de {args['data_ref']}")

    faturas.write.mode("overwrite").partitionBy("data_ref").parquet("s3://lake/curated/faturas/")


if __name__ == "__main__":
    main()
