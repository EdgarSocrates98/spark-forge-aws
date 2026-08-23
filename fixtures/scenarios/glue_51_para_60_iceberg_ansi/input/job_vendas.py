"""Job de consolidacao diaria de vendas, gravando numa tabela Iceberg."""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "data_ref"])
sc = SparkContext()
glue = GlueContext(sc)
spark = glue.spark_session

spark.sql(
    """
    CREATE TABLE IF NOT EXISTS glue_catalog.vendas.consolidado (
        pedido_id STRING,
        cliente_id STRING,
        valor_centavos BIGINT,
        data_ref DATE
    )
    USING iceberg
    PARTITIONED BY (data_ref)
    TBLPROPERTIES ('format-version'='2', 'write.parquet.compression-codec'='zstd')
    """
)

bruto = spark.read.parquet("s3://lake/bronze/vendas/")

# O arquivo de origem entrega `valor` como texto livre digitado no ponto de
# venda; o job sempre tratou valor invalido como ausente.
tratado = bruto.withColumn("valor_centavos", F.col("valor").cast("bigint")).withColumn(
    "pedido_id", F.col("pedido").cast("string")
)

tratado.filter(F.col("data_ref") == args["data_ref"]).writeTo(
    "glue_catalog.vendas.consolidado"
).overwritePartitions()
