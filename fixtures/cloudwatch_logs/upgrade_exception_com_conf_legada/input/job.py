from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
# Configuracao legada declarada -- e o companheiro que SF-ERR-022 exige.
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
