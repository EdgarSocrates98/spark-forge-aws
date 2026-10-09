"""Consolidacao diaria de eventos -- o job cuja mudanca esta sendo validada.

Este arquivo existe no corpus por UM motivo: dar ao plano o ALVO. `build_plan`
le `pyspark.write.attrs.target` e nada mais deste codigo; a transformacao em si
nao entra no plano, e os valores dos dois lados sao os que o OPERADOR mediu --
estao em `input/before.json` e `input/after.json`, e o motor nunca os produz.
"""
from pyspark.sql import SparkSession


def consolidar(spark):
    eventos = spark.read.table("db.eventos_brutos")
    pedidos = spark.read.table("db.pedidos")
    return eventos.join(pedidos, "pedido_id")


def main():
    spark = SparkSession.builder.getOrCreate()
    consolidar(spark).write.mode("overwrite").saveAsTable("db.eventos")


if __name__ == "__main__":
    main()
