"""Vendas do dia: o gate de qualidade e uma funcao propria, e ela ABORTA.

Forma canonica de biblioteca Glue, e o espelho de `helper_validates_cached_param`:
la o check mora no helper e a persistencia no chamador; aqui e o contrario --
o check mora no chamador e a CONSEQUENCIA mora no helper.

`aborta_se` e reusado por varios jobs, recebe a contagem e decide. O `raise` que
protege este pipeline nao esta no escopo do check: esta no corpo de outra
funcao, um salto adiante. Ate a Fase 5c.2 este job saia com `SF-DQ-002` em P1 --
"validacao sem consequencia" -- sobre um job que para antes de publicar dado
ruim. Acusar quem protegeu e o pior modo de falha desta regra: ensina o leitor a
ignorar a area inteira.
"""
import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def aborta_se(quantidade, mensagem):
    """Gate compartilhado: acima de zero, o job para antes de publicar."""
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
