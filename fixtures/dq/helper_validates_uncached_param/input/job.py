"""Entregas do dia: valida num helper, e NAO persiste no chamador.

O espelho de `helper_validates_cached_param`, e a metade que prova que a
heranca da Fase 5c.2 resolve nos DOIS sentidos. Mesma forma de biblioteca Glue
-- gate de qualidade em funcao propria, `main` carrega e chama --, e a unica
diferenca e a linha que nao existe: nao ha `cache()` antes da chamada.

O check e o write vivem os dois dentro de `valida_e_publica`, sobre o mesmo
`entregas`, e sem persistencia o lineage inteiro roda duas vezes: uma para
contar as entregas sem transportadora, outra para escrever. `SF-DQ-003`
dispara, e o que a faz disparar e evidencia que mora NO CHAMADOR -- de dentro
do helper nao ha `cache`/`persist`/`unpersist` nenhum sobre o parametro.
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

    valida_e_publica(entregas)

    job.commit()


if __name__ == "__main__":
    main()
