from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("etl-sintetico")
    .config("spark.sql.shuffle.partitions", 800)
    .getOrCreate()
)
