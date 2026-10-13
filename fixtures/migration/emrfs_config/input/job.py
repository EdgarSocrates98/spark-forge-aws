from awsglue.context import GlueContext

glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

spark.conf.set("fs.s3.consistent", "true")
spark.conf.set("fs.s3.maxRetries", "5")
