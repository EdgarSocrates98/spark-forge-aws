from awsglue.context import GlueContext

glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
