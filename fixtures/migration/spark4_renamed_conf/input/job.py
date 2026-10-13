spark.conf.set("spark.sql.legacy.parquet.int96RebaseModeInWrite", "CORRECTED")
df.write.option("compression", "lz4raw").parquet(destino)
