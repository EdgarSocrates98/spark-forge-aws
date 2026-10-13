from awsglue.context import GlueContext
from pyspark.sql.functions import col, try_cast


def transform(df):
    risco = df.withColumn("valor", col("texto").cast("int"))
    seguro = df.withColumn("seguro", try_cast(col("texto"), "int"))
    return risco, seguro
