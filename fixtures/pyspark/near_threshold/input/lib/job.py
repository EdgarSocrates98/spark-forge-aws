from pyspark.sql.functions import lit


def enriquecer(df):
    return (
        df.withColumn("c1", lit(1))
        .withColumn("c2", lit(1))
        .withColumn("c3", lit(1))
        .withColumn("c4", lit(1))
        .withColumn("c5", lit(1))
        .withColumn("c6", lit(1))
        .withColumn("c7", lit(1))
        .withColumn("c8", lit(1))
        .withColumn("c9", lit(1))
    )
