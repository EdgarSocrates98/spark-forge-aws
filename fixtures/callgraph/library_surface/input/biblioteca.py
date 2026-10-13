"""Biblioteca de ingestao Glue: superficie publica, callback, metodo, e uma sobra.

Corpus deliberadamente cheio de funcoes SEM chamador local. Quase nenhuma delas
e codigo morto -- e por isso que ele existe: uma medida que confundisse "sem
chamador neste corpus" com "codigo morto" devolveria aqui a biblioteca inteira
como achado.
"""
import functools

from pyspark.sql import functions as F

__all__ = ["carrega", "grava"]


def carrega(spark, caminho):
    """Exportada em `__all__`: quem chama e a aplicacao, fora do corpus."""
    return spark.read.parquet(caminho)


def grava(df, destino):
    """Exportada em `__all__`: idem."""
    df.write.mode("append").parquet(destino)


def aplica_normalizacao(rdd):
    """Nenhuma funcao daqui a chama -- `job.py` chama, e a aresta e intra-arquivo."""
    return rdd.foreach(_normaliza_linha)


def _normaliza_linha(linha):
    """Callback: passada por nome a `foreach`, nunca chamada como `_normaliza_linha()`."""
    return linha


@functools.lru_cache(maxsize=None)
def esquema_do_contrato():
    """Decorada: `lru_cache` embrulha, e quem invoca pode ser o framework."""
    return "pedido_id INT, status STRING"


def _rotina_abandonada(df):
    """A UNICA sobra real: ninguem chama, ninguem importa, o nome nao aparece
    em nenhum arquivo do corpus."""
    return df.withColumn("obsoleto", F.lit(1))


class Escritor:
    def __init__(self, destino):
        self.destino = destino

    def executa(self, df):
        """Metodo: a chamada seria `escritor.executa(df)`, um atributo -- nunca
        vira aresta nem leitura do nome."""
        grava(df, self.destino)
