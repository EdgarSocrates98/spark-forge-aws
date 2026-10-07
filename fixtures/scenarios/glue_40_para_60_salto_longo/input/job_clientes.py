"""Job de enriquecimento de clientes, escrito para o Glue 4.0.

Le do S3, chama o SDK v1 da AWS numa UDF de geolocalizacao e grava em Parquet.
"""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from com.amazonaws.services.s3.model import GetObjectRequest
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glue = GlueContext(sc)
spark = glue.spark_session

# Configuracao herdada do EMR: o EMRFS lia estas chaves, o S3A do Glue 5 nao.
spark.conf.set("fs.s3.consistent", "true")
spark.conf.set("fs.s3.maxRetries", "20")

clientes = spark.read.parquet("s3://lake/bronze/clientes/")

# `documento` chega como texto do formulario; documento invalido sempre virou
# null e o consumidor a jusante conta esses nulls.
enriquecido = clientes.withColumn("documento_num", F.col("documento").cast("long"))

enriquecido.write.mode("overwrite").partitionBy("uf").parquet("s3://lake/silver/clientes/")
