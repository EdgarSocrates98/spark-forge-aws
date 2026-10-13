"""Job de exemplo: leitura, projecao, filtro e escrita particionada.

Idiomatico de proposito -- esta e a fixture mais importante do corpus.
Qualquer finding aqui e falso positivo do catalogo ou do extrator.
"""
from pyspark.sql import SparkSession


def executar(spark: SparkSession, entrada: str, saida: str) -> None:
    pedidos = spark.read.format("parquet").load(entrada)

    relevantes = pedidos.select(
        "pedido_id", "cliente_id", "valor", "data_pedido"
    ).filter("valor > 0")

    relevantes.write.mode("overwrite").partitionBy("data_pedido").parquet(saida)


if __name__ == "__main__":
    spark_session = SparkSession.builder.appName("pedidos").getOrCreate()
    executar(spark_session, "s3://bucket/entrada", "s3://bucket/saida")
    spark_session.stop()
