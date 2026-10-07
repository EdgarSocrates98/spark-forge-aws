"""Helper de validacao generico: o alvo do check nao se le no `.py`.

`valida_tabela` recebe o NOME da tabela e monta o DataFrame na propria cadeia
do check. A raiz da cadeia e a sessao, e nao o dado validado -- registrar
`spark` como alvo dataria este check contra o write de qualquer outro dado que
tambem saia de `spark`. O ponto cego e CONTADO em `dq.unresolved`, e nenhum
alvo e adivinhado.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


def valida_tabela(spark, tabela, coluna):
    """Conta as linhas da tabela em que a coluna obrigatoria esta nula."""
    ausentes = spark.table(tabela).filter(F.col(coluna).isNull()).count()
    if ausentes > 0:
        raise ValueError(f"{ausentes} linhas com {coluna} nulo em {tabela}")


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
    sc = SparkContext.getOrCreate()
    glue = GlueContext(sc)
    spark = glue.spark_session

    for tabela, coluna in (
        ("curated.clientes", "cliente_id"),
        ("curated.produtos", "sku"),
    ):
        valida_tabela(spark, tabela, coluna)

    resumo = (
        spark.table("curated.vendas")
        .filter(F.col("data_ref") == args["data_ref"])
        .groupBy("cliente_id")
        .agg(F.sum("valor_total").alias("total"))
    )
    resumo.write.mode("overwrite").parquet("s3://lake/mart/resumo_cliente/")


if __name__ == "__main__":
    main()
