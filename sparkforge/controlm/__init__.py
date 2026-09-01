"""Control-M (BMC) como dominio de conhecimento versionado.

POR QUE UM PACOTE PROPRIO, E NAO `sparkforge/facts/runtime_matrix.py`.

O prompt desta entrega mandou MEDIR antes de decidir, e a medida e esta: as
tres matrizes de EMR carregam por `_carrega_matriz_fechada`, e as tres funcoes
que sustentam aquele caminho -- `_versoes`, `_carrega_matriz_fechada` e
`_procedencia_por_release` -- keyam TODAS pelo bloco `versions:`, com uma
release por chave e um escalar por celula. A matriz do Control-M nao tem
`versions:`: ela tem `capabilities:` (chaveada por CAPACIDADE, com a versao
dentro como fronteira) e `components:` (chaveada por componente e so entao por
versao). Encaixar os dois eixos naquele carregador exigiria reescrever o
carregador das quatro matrizes de runtime para um caso que nao e runtime --
Control-M nao tem Spark, nao tem release label e nao tem componente -> versao.

`sparkforge/controlm/` fica, entao, com a mesma divisao interna que
`sparkforge/migration/` ja usa e que o docstring de `release_descriptor.py`
declara: `matrix.py` CARREGA dado externo de `knowledge/`, e `descriptor.py`
COMPOE sobre o que a matriz carregou. A linha entre extrair e compor e a mesma
que o `CLAUDE.md` deste repositorio desenha entre `analyze *` e os verbos de
topo.
"""
