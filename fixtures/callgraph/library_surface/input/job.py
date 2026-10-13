"""Job que consome a biblioteca. Prova o uso CROSS-MODULO.

`carrega`, `grava` e `aplica_normalizacao` sao definidas em `biblioteca.py` e
usadas aqui: nenhuma aresta do grafo as liga, porque as arestas de
`pyspark_ast` sao intra-arquivo por construcao. Sem cruzar os nomes lidos em
cada modulo, as tres pareceriam orfas.
"""
from biblioteca import aplica_normalizacao, carrega, grava


def main(spark):
    df = carrega(spark, "s3://bucket/entrada")
    aplica_normalizacao(df.rdd)
    grava(df, "s3://bucket/saida")


if __name__ == "__main__":
    main(spark)  # noqa: F821 -- `spark` vem do runtime Glue
