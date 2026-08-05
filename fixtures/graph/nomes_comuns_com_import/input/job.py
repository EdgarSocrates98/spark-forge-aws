"""Tres nomes da API do GraphFrames que tambem sao nomes de qualquer objeto.

`find` e metodo de `str`; `validate` e `degrees` sao identificadores que
qualquer objeto de usuario pode ter. Sem import de GraphFrames neste modulo,
NENHUM deles vira `graph.algorithm` -- e este arquivo e o unico lugar do
repositorio onde a acusacao falsa apareceria se alguem "simplificasse" o
vocabulario de dois niveis para um `frozenset` unico.

Par com a fixture irma, e os dois arquivos diferem SO pela linha do import.
"""
import graphframes
from pyspark.sql import SparkSession


class Medidas:
    degrees = 3

    def validate(self, spark):
        return spark is not None


def main():
    spark = SparkSession.builder.appName("texto").getOrCreate()
    cabecalho = "id,src,dst"
    posicao = cabecalho.find("src")
    medidas = Medidas()
    medidas.validate(spark)
    graus = medidas.degrees
    return posicao, graus
