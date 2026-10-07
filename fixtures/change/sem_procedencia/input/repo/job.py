def ler(spark, caminho):
    return spark.read.parquet(caminho)
