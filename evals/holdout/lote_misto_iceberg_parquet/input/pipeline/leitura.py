"""Camada de leitura: Parquet cru no S3, com sessao herdada do EMR."""
from com.amazonaws.services.s3 import AmazonS3ClientBuilder


def preparar_sessao(spark):
    # Herdado do cluster EMR de onde o pipeline veio.
    spark.conf.set("fs.s3.enableServerSideEncryption", "true")
    spark.conf.set("fs.s3.maxRetries", "10")
    return spark


def cliente_s3():
    return AmazonS3ClientBuilder.defaultClient()


def ler_estoque(spark, caminho):
    return spark.read.parquet(caminho)
