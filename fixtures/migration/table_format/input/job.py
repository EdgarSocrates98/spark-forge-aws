from awsglue.context import GlueContext

glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

spark.sql("ALTER TABLE catalog.db.tabela SET TBLPROPERTIES ('format-version'='2')")
