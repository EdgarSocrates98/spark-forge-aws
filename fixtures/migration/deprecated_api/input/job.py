from pyspark import SparkContext
import pyspark.sql

sc = SparkContext.getOrCreate()
sql_context = pyspark.sql.SQLContext(sc)
