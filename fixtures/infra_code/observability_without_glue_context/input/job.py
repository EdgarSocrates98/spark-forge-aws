"""Job que usa SparkSession pura, sem GlueContext.

`--enable-observability-metrics` esta ligado no Terraform, mas as metricas de
observabilidade do Glue sao publicadas pelo GlueContext -- que este codigo
nunca inicializa. O argumento fica ligado e nao produz metrica nenhuma.
"""
from pyspark.sql import SparkSession


def main():
    spark = SparkSession.builder.getOrCreate()
    pedidos = spark.read.parquet("s3://lake/curated/pedidos/")
    resumo = pedidos.groupBy("status").count()
    resumo.write.mode("overwrite").parquet("s3://lake/curated/resumo_status/")


if __name__ == "__main__":
    main()
