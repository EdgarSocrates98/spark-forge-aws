"""Biblioteca com recursao mutua entre etapas do pipeline.

`processa_lote` chama `trata_rejeitados`, que reprocessa chamando
`processa_lote` de novo. E um ciclo real e comum em biblioteca de ingestao --
e e exatamente o que faz uma leitura ou uma action "unica" no codigo virar
trabalho repetido em runtime.
"""
from pyspark.sql import functions as F


def le_lote(spark, caminho):
    return spark.read.parquet(caminho)


def processa_lote(spark, caminho, tentativa):
    df = le_lote(spark, caminho)
    validos = df.filter(F.col("status") != "REJEITADO")
    rejeitados = df.filter(F.col("status") == "REJEITADO")
    if tentativa < 3:
        return trata_rejeitados(spark, rejeitados, caminho, tentativa)
    return validos


def trata_rejeitados(spark, rejeitados, caminho, tentativa):
    corrigidos = rejeitados.withColumn("status", F.lit("PENDENTE"))
    if corrigidos.count() > 0:
        return processa_lote(spark, caminho, tentativa + 1)
    return corrigidos


def main(spark, caminho):
    resultado = processa_lote(spark, caminho, 0)
    resultado.write.mode("overwrite").parquet(caminho + "/saida")
