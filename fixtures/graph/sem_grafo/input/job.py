"""Job PySpark comum: le, agrega e escreve. Nenhum grafo em lugar nenhum.

A metade que prova que a sentinela sai mesmo quando nao ha nada a dizer. Sem
ela, "este arquivo nao processa grafo" e "o extrator nao rodou aqui" seriam a
mesma saida.
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main():
    spark = SparkSession.builder.appName("vendas").getOrCreate()
    vendas = spark.read.parquet("s3://dados/vendas/")
    por_loja = vendas.groupBy("loja").agg(F.sum("valor").alias("total"))
    por_loja.write.mode("overwrite").parquet("s3://dados/agregado/")
