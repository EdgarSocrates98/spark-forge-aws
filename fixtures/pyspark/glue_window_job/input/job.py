"""Job Glue com GlueContext, funcao auxiliar e latest-per-key por Window.

Escrito para ser CORRETO: existe para exercitar os facts estruturais
(`pyspark.glue_context_init`, `pyspark.window`, `pyspark.callgraph_edge`), nao
para disparar regra nenhuma.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import Window
from pyspark.sql import functions as F


def build_context():
    sc = SparkContext.getOrCreate()
    return GlueContext(sc)


def read_pedidos(spark, caminho):
    return spark.read.parquet(caminho).select("pedido_id", "cliente_id", "status", "atualizado_em")


def latest_per_key(df):
    janela = Window.partitionBy("pedido_id").orderBy(F.col("atualizado_em").desc())
    return (
        df.withColumn("rn", F.row_number().over(janela))
        .filter(F.col("rn") == 1)
        .drop("rn")
    )


def resumo_por_status(df):
    janela = Window.partitionBy("status")
    return df.withColumn("total_status", F.count("pedido_id").over(janela))


def main():
    args = getResolvedOptions(sys.argv, ["JOB_NAME", "input_path", "output_path"])
    glue_context = build_context()
    spark = glue_context.spark_session

    pedidos = read_pedidos(spark, args["input_path"])
    corrente = latest_per_key(pedidos)
    enriquecido = resumo_por_status(corrente)

    enriquecido.write.mode("overwrite").parquet(args["output_path"])


if __name__ == "__main__":
    main()
