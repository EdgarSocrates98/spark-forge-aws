"""Entregas do dia: valida num helper, persiste no chamador.

Forma canonica de biblioteca Glue. O gate de qualidade e uma funcao propria --
reusada por varios jobs -- e quem carrega o dado decide se vale a pena pagar
`cache()` antes de chamar. As duas metades vivem em ESCOPOS DIFERENTES.

Dentro de `valida_e_publica` nao ha como saber se `entregas` esta persistido: o
parametro chega com uma historia que o `.py` do escopo nao conta. Aqui ela esta
-- `main` cacheia antes de chamar --, e afirmar "nao persistido" faria
`SF-DQ-003` acusar um job que fez a coisa certa.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def valida_e_publica(entregas):
    """Aborta se houver entrega sem transportadora, e so entao publica."""
    sem_transportadora = entregas.filter(F.col("transportadora_id").isNull()).count()
    if sem_transportadora > 0:
        raise ValueError(f"{sem_transportadora} entregas sem transportadora")

    entregas.write.mode("overwrite").partitionBy("data_ref").parquet(
        "s3://lake/curated/entregas/"
    )


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session
    job = Job(glue)
    job.init(args["JOB_NAME"], args)

    entregas = (
        spark.read.parquet("s3://lake/raw/entregas/")
        .filter(F.col("data_ref") == args["data_ref"])
        .withColumn("prazo_dias", F.datediff(F.col("entregue_em"), F.col("despachado_em")))
    )
    entregas.cache()

    valida_e_publica(entregas)

    entregas.unpersist()
    job.commit()


if __name__ == "__main__":
    main()
