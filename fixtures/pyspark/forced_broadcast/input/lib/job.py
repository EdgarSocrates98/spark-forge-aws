from pyspark.sql.functions import broadcast


def unir(a, b):
    return a.join(broadcast(b), "k")
