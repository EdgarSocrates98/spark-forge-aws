def configurar(spark):
    spark.conf.set("spark.sql.shuffle.partitions", "800")
