"""Job de faturamento. A configuracao vem do pacote `conf`, nunca inline."""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from conf.sessao import aplicar_conf
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
spark = aplicar_conf(GlueContext(SparkContext()).spark_session)

faturas = spark.read.parquet("s3://lake/silver/faturas/")
faturas.write.mode("append").parquet("s3://lake/gold/faturamento/")
