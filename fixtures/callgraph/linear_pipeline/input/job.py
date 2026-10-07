"""Pipeline linear: main chama tres auxiliares, nenhuma delas chama outra.

Contraparte de `mutual_recursion`: mesmo formato de corpus, grafo aciclico.
Existe para que `has_cycle: false` e `callgraph.cycle` ausente sejam provados,
nao presumidos.
"""
from pyspark.sql import Window
from pyspark.sql import functions as F


def le_pedidos(spark, caminho):
    return spark.read.parquet(caminho).select("pedido_id", "status", "atualizado_em")


def deduplica(df):
    janela = Window.partitionBy("pedido_id").orderBy(F.col("atualizado_em").desc())
    return df.withColumn("rn", F.row_number().over(janela)).filter(F.col("rn") == 1).drop("rn")


def grava(df, destino):
    df.write.mode("overwrite").parquet(destino)


def main(spark, origem, destino):
    pedidos = le_pedidos(spark, origem)
    corrente = deduplica(pedidos)
    grava(corrente, destino)
