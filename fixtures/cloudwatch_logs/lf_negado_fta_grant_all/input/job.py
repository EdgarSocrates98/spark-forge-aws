from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

novos = spark.read.parquet("s3://sparkforge-aws-demo/landing/clientes/")
novos.write.mode("append").saveAsTable("analytics.dim_cliente")
