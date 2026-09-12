def carregar(df):
    return df.write.mode("overwrite").parquet("s3://destino/saida/")
