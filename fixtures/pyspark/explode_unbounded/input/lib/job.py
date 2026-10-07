from pyspark.sql.functions import col, explode


def expandir(df):
    return df.select(explode(col("itens")).alias("item")).filter(col("item").isNotNull())
