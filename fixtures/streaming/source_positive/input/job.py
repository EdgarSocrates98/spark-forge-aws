from pyspark.sql import SparkSession


spark = SparkSession.builder.getOrCreate()
events = (
    spark.readStream.format("kafka")
    .option("subscribe", "events")
    .load()
    .withWatermark("event_time", "10 minutes")
)
dimensions = spark.readStream.format("rate").load()
joined = events.join(dimensions, "key")
stateful = joined.groupBy("key").count()
deduplicated = stateful.dropDuplicates(["key"])


def write_batch(batch, epoch_id):
    batch.write.mode("append").format("iceberg").saveAsTable("analytics.events")


query = (
    deduplicated.writeStream.outputMode("update")
    .option("checkpointLocation", "s3://lake/checkpoints/events")
    .trigger(processingTime="10 seconds")
    .foreachBatch(write_batch)
    .start()
)

query_without_checkpoint = (
    deduplicated.writeStream.outputMode("append").start()
)
