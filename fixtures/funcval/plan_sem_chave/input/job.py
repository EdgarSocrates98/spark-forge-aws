"""O mesmo job, escrevendo em DOIS destinos.

O segundo destino e um caminho S3, e nenhum `catalog.table_schema` o nomeia --
o casamento de alvo e por string identica contra o `subject.symbol` do catalogo,
e caminho nao e simbolo de tabela. Entao aquele alvo sai com plano de contagem
so, e os eixos de schema e de agregado ficam ESCRITOS como ausentes.
"""
from pyspark.sql import SparkSession


def consolidar(spark):
    eventos = spark.read.table("db.eventos_brutos")
    pedidos = spark.read.table("db.pedidos")
    return eventos.join(pedidos, "pedido_id")


def main():
    spark = SparkSession.builder.getOrCreate()
    consolidado = consolidar(spark)
    consolidado.write.mode("overwrite").saveAsTable("db.eventos")
    consolidado.write.mode("append").parquet("s3://bucket/curated/eventos/")


if __name__ == "__main__":
    main()
