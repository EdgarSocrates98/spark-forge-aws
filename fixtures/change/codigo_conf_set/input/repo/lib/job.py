def registrar(rotulo, resultado):
    return resultado


def configurar(spark):
    registrar("configuração", spark.conf.set("spark.sql.shuffle.partitions", "800"))
