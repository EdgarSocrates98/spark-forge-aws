"""O Pregel, que e `@property` e nao chamada, e a cadeia que cresce para FORA.

Um vocabulario casado so contra `ast.Call` nao emitiria fact nenhum aqui -- e o
Pregel e o unico algoritmo cujo limite de iteracao o usuario controla de fato.
Vertices e arestas chegam por PARAMETRO: a persistencia comecou fora deste
escopo e a chave fica OMITIDA, que e subnotificacao declarada e nunca acusacao.
"""
from graphframes import GraphFrame
from graphframes.lib import Pregel
from pyspark.sql import functions as F


def rotular(vertices, arestas):
    g = GraphFrame(vertices, arestas)
    return (
        g.pregel.setMaxIter(10)
        .withVertexColumn("rank", F.lit(1.0), F.lit(1.0))
        .sendMsgToDst(Pregel.src("rank"))
        .aggMsgs(F.sum(Pregel.msg()))
        .run()
    )
