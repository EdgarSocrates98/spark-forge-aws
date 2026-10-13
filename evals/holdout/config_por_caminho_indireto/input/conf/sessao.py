"""Aplicacao da configuracao. Le o mapa, nao conhece nenhuma chave."""
from conf.spark_defaults import CONF_PADRAO


def aplicar_conf(spark, extras=None):
    for chave, valor in {**CONF_PADRAO, **(extras or {})}.items():
        spark.conf.set(chave, valor)
    return spark
