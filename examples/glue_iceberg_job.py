import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "SOURCE_PATH", "TARGET_TABLE"]
)

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

source = (
    spark.read
    .parquet(args["SOURCE_PATH"])
    .select("event_id", "customer_id", "event_ts", "amount", "status")
    .filter(F.col("event_ts") >= F.date_sub(F.current_date(), 2))
)

prepared = (
    source
    .withColumn("event_date", F.to_date("event_ts"))
    .filter(F.col("event_id").isNotNull())
)

prepared.createOrReplaceTempView("updates")

spark.sql(f"""
MERGE INTO {args["TARGET_TABLE"]} AS target
USING updates AS source
ON target.event_id = source.event_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

job.commit()
