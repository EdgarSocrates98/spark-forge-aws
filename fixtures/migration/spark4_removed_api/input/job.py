import pyspark.pandas as ps

base = ps.read_parquet(origem)
novo = base.append(extra)
