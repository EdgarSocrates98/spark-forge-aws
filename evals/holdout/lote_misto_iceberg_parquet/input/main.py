"""Entrada do job de estoque, montado sobre o pacote `pipeline`."""
import sys

from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from pipeline.escrita import gravar, normalizar
from pipeline.leitura import ler_estoque, preparar_sessao
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
spark = preparar_sessao(GlueContext(SparkContext()).spark_session)

bruto = ler_estoque(spark, "s3://lake/bronze/estoque/")
gravar(normalizar(bruto), spark)
