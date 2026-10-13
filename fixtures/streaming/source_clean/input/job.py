from pyspark.sql import SparkSession


spark = SparkSession.builder.getOrCreate()
batch = spark.read.format("parquet").load("s3://lake/events")
batch.write.mode("append").format("parquet").save("s3://lake/curated/events")
