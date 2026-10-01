def ler(spark):
    return spark.read.table("db.pedidos")
