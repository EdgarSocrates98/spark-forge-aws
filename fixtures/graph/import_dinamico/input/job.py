"""Import dinamico: ponto cego CONTADO, e nunca adivinhado.

`importlib.import_module("graphframes")` tem o nome literal e conta; o
`__import__(nome)` nao tem nome nenhum legivel e conta pelo motivo oposto -- o
nome pode ser montado em runtime. Nenhuma construcao sai daqui: sem `import`
lido, `gf.GraphFrame(...)` nao e reconhecido, e isso e o limite declarado do
modulo, nao silencio.
"""
import importlib


def carregar(nome):
    gf = importlib.import_module("graphframes")
    outro = __import__(nome)
    return gf, outro
