def salvar(df, destino):
    df.coalesce(1).write.mode("overwrite").parquet(destino)
