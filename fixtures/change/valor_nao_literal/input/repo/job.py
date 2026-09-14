def configurar(spark, particoes):
    spark.conf.set("spark.sql.shuffle.partitions", particoes)
