"""Camada de escrita: tabela Iceberg governada, particionada por deposito."""
from pyspark.sql import functions as F

DDL_ESTOQUE = """
CREATE TABLE IF NOT EXISTS glue_catalog.estoque.posicao (
    sku STRING,
    deposito STRING,
    quantidade INT,
    atualizado_em TIMESTAMP
)
USING iceberg
PARTITIONED BY (deposito)
TBLPROPERTIES ('format-version'='2')
"""


def normalizar(df):
    # `quantidade` chega como texto do inventario manual; valor invalido
    # sempre virou null e o relatorio conta esses nulls.
    return df.withColumn("quantidade", F.col("quantidade_txt").cast("int"))


def gravar(df, spark):
    spark.sql(DDL_ESTOQUE)
    df.writeTo("glue_catalog.estoque.posicao").overwritePartitions()
