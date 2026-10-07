"""Vendas do dia: o aborto esta DOIS corpos adiante do check.

`main` conta e chama `aborta_se`; `aborta_se` nao decide nada -- repassa a
contagem a `exige_zero`, e e la que o `raise` mora.

O extrator segue UM salto. Aqui a cadeia passa desse limite, e o que ele faz
nao e calar: emite `dq.unresolved` com reason `enforcement_beyond_one_hop`,
nomeando os dois helpers. `SF-DQ-002` continua disparando -- o fact de ponto
cego nao a cala --, e e assim que este job deve ser lido: acusacao com o motivo
do limite escrito ao lado, e nunca acusacao sem explicacao.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def aborta_se(quantidade, mensagem):
    """Fachada do gate: nao decide, repassa."""
    exige_zero(quantidade, mensagem)


def exige_zero(quantidade, mensagem):
    """Onde o job de fato para."""
    if quantidade > 0:
        raise ValueError(f"{mensagem}: {quantidade} linhas")


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
    aborta_se(negativas, "vendas com valor negativo")

    vendas.write.mode("overwrite").partitionBy("data_ref").parquet(
        "s3://lake/curated/vendas/"
    )
    vendas.unpersist()
    job.commit()


if __name__ == "__main__":
    main()
