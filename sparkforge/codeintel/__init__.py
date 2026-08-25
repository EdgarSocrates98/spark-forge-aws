"""Indice local de codigo, offline e sem dependencia externa.

Ele CONSOME o que o repositorio ja tem -- a varredura de `facts/scan.py` e o
`ast` que os extratores ja usam -- e persiste metadado consultavel. Ele nao
reimplementa extracao, e nao guarda corpo de funcao: o banco tem posicao, e
quem quiser o codigo le o arquivo.

O banco e DESCARTAVEL. Nada no motor deterministico depende dele para
responder; se sumir, a analise continua igual e o indice se reconstroi.
"""

from sparkforge.codeintel.db import BANCO_PADRAO
from sparkforge.codeintel.extract import No, extrair_nos
from sparkforge.codeintel.graph import NoDoGrafo, chamadores, chamados, impacto
from sparkforge.codeintel.ids import node_id, normalizar_assinatura
from sparkforge.codeintel.index import Resultado, indexar
from sparkforge.codeintel.refs import Referencia, extrair_referencias
from sparkforge.codeintel.search import Achado, buscar, resumo

__all__ = [
    "BANCO_PADRAO",
    "Achado",
    "No",
    "NoDoGrafo",
    "Referencia",
    "Resultado",
    "buscar",
    "chamadores",
    "chamados",
    "extrair_nos",
    "extrair_referencias",
    "impacto",
    "indexar",
    "node_id",
    "normalizar_assinatura",
    "resumo",
]
