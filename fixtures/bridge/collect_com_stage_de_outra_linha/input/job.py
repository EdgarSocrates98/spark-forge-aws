"""Job de amostra: um collect sem limite, na linha que o event log cita."""

from pyspark.sql import SparkSession


def principal(spark):
    clientes = spark.read.parquet("s3://bucket/clientes")
    ativos = clientes.filter(clientes.ativo == True)  # noqa: E712
    linhas = ativos.collect()
    return len(linhas)


def main():
    spark = SparkSession.builder.getOrCreate()
    return principal(spark)
