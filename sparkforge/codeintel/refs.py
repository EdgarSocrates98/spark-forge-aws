"""AST -> referencia bruta. O que menciona quem, sem saber a quem aponta.

POR QUE EXTRAIR E RESOLVER SAO DOIS MODULOS
-------------------------------------------
Este devolve o que o AST VE. Resolver -- decidir a QUEM cada nome aponta -- e
`resolve.py`. Juntar os dois pareceria economia e custaria o unico numero que
diz se o grafo vale alguma coisa: a taxa de resolucao. Com um passo so, uma
referencia que ninguem conseguiu resolver e uma que ninguem extraiu produzem o
mesmo nada, e nao ha como saber qual das duas aconteceu -- nem, portanto, o que
consertar.

A OUTRA METADE E A PILHA DE ESCOPO, E ELA NAO MORA AQUI
-------------------------------------------------------
`origem_qualificada` tem que casar, caractere por caractere, com o
`No.qualified_name` que `extract.py` produz -- e por essa igualdade que
`resolve.py` acha o no de onde a chamada sai. Duas pilhas de escopo casariam
hoje e divergiriam no proximo commit, calado. Entao ha UMA, em
`extract.VisitanteComEscopo`, e este modulo herda dela. O gate por AST que
impede a segunda esta em `tests/test_codeintel_refs.py`.

O QUE NAO VIRA REFERENCIA, E POR QUE
------------------------------------
Chamada sem nome -- `tabela['k']()`, `(lambda: 1)()` -- nao produz referencia:
nao ha nome a resolver, entao nao ha o que registrar nem em `edges` nem em
`unresolved_refs`. Inventar um nome ai encheria a tabela de ponto cego com
entradas que nunca teriam resolvido, e estragaria justamente o denominador que
o modulo existe para preservar.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from sparkforge.codeintel.extract import VisitanteComEscopo

_CALLS = "calls"
_IMPORTS = "imports"
_SUFIXO_PACOTE = "__init__"


@dataclass(frozen=True)
class Referencia:
    """Uma mencao a nome, do ponto de vista de quem menciona.

    Ela NAO sabe a quem aponta -- resolver e trabalho de `resolve.py`. Separar
    as duas coisas e o que permite medir a taxa de resolucao: sem isso, uma
    referencia que ninguem resolveu seria indistinguivel de uma que ninguem
    extraiu.

    Imutavel porque e EVIDENCIA. Consumidor que corrige o campo em vez de
    registrar um fato novo apaga o que o AST viu, e evidencia editada em
    silencio e o defeito que o schema de `Finding` inteiro existe para evitar.
    """

    origem_qualificada: str  # quem menciona: `Pipeline.executar`
    nome: str  # o que menciona: `processar`
    kind: str  # "calls" | "imports"
    line: int
    receptor: str  # `df` em `df.processar()`; "" quando nao ha


def extrair_referencias(fonte: str, caminho: str) -> list[Referencia]:
    """Referencias de `fonte`, ou lista vazia se ela nao parseia.

    Sintaxe invalida e ponto CEGO e nao erro fatal, pela mesma razao que em
    `extrair_nos`: derrubar a indexacao inteira por um arquivo com sintaxe de
    outra versao de Python trocaria cobertura parcial por nenhuma.

    A captura repete `(SyntaxError, ValueError)` de `extract.py`, e a repeticao
    e deliberada: o byte nulo levanta `ValueError` em 3.10.20 e `SyntaxError` em
    3.11.15 e 3.14.6 -- medido la. Capturar so `SyntaxError` derrubaria 3.10.

    Diferente de `extrair_nos_ou_none`, nao ha variante que distingue "nao
    parseia" de "parseia e nao referencia nada": quem conta ilegivel e
    `indexar`, que ja chamou `extrair_nos_ou_none` sobre a MESMA fonte e ja tem
    a resposta. Uma segunda contagem do mesmo arquivo daria dois numeros para o
    mesmo fato, e um deles ficaria errado primeiro.
    """
    try:
        arvore = ast.parse(fonte)
    except (SyntaxError, ValueError):
        return []
    coletor = _ColetorDeReferencias(modulo_do_caminho(caminho))
    coletor.visit(arvore)
    return coletor.referencias


def modulo_do_caminho(caminho: str) -> str:
    """`pacote/m.py` -> `pacote.m`. E o nome do escopo de TOPO do arquivo.

    Chamada no topo do modulo nao sai de funcao nenhuma, e precisa de uma
    origem mesmo assim -- senao toda inicializacao de modulo viraria referencia
    orfa.

    `__init__.py` some do fim porque `pacote/__init__.py` E o pacote: ninguem
    escreve `import pacote.__init__`, e uma origem com esse nome nao casaria com
    nada que qualquer import produz.

    A barra invertida vira barra porque a varredura entrega POSIX
    (`Path.as_posix`) mas quem chama a mao no Windows entrega o separador nativo.
    Sem normalizar, o MESMO arquivo daria duas origens diferentes e a contagem
    de chamadores se dividiria em duas, calada.
    """
    limpo = caminho.replace("\\", "/").strip("/")
    if limpo.endswith(".py"):
        limpo = limpo[: -len(".py")]
    partes = [parte for parte in limpo.split("/") if parte]
    if partes and partes[-1] == _SUFIXO_PACOTE:
        partes.pop()
    return ".".join(partes)


class _ColetorDeReferencias(VisitanteComEscopo):
    """Chamadas e imports, com a origem que a pilha da base esta segurando.

    Nao ha `visit_ClassDef` nem `visit_FunctionDef` aqui de proposito -- eles
    sao a pilha, e a pilha e da base. Ver o gate em
    `tests/test_codeintel_refs.py`.
    """

    def __init__(self, modulo: str) -> None:
        super().__init__()
        self.modulo = modulo
        self.referencias: list[Referencia] = []

    def visit_Call(self, no: ast.Call) -> None:
        nomeado = _nome_e_receptor(no.func)
        if nomeado is not None:
            nome, receptor = nomeado
            self._registrar(nome, _CALLS, no.lineno, receptor)
        # Desce SEMPRE, inclusive quando a chamada nao virou referencia:
        # `f(g(x))` tem a chamada de dentro nos argumentos, e `tabela['k'](g())`
        # tambem. Parar aqui perderia a composicao, que e a forma mais comum de
        # chamada que existe.
        self.generic_visit(no)

    def visit_Import(self, no: ast.Import) -> None:
        for apelidado in no.names:
            # `apelidado.name` e nao `apelidado.asname`: `import numpy as np`
            # referencia `numpy`. `np` e nome local, nao existe em lugar nenhum
            # do indice, e uma aresta para ele cairia em `unresolved_refs` por
            # um motivo inventado aqui em vez de por o alvo ser mesmo externo.
            self._registrar(apelidado.name, _IMPORTS, no.lineno, "")
        self.generic_visit(no)

    def visit_ImportFrom(self, no: ast.ImportFrom) -> None:
        # Os pontos do import relativo SOBREVIVEM. `from .irmao import f` e
        # `from irmao import f` apontam para lugares diferentes, e o ponto e a
        # unica coisa que os separa -- perde-lo faria a referencia resolver para
        # o modulo de topo de mesmo nome. Aresta errada e pior que ausente.
        prefixo = "." * no.level + (no.module or "")
        for apelidado in no.names:
            self._registrar(f"{prefixo}.{apelidado.name}", _IMPORTS, no.lineno, "")
        self.generic_visit(no)

    def _registrar(self, nome: str, kind: str, line: int, receptor: str) -> None:
        self.referencias.append(
            Referencia(
                origem_qualificada=self._escopo_qualificado() or self.modulo,
                nome=nome,
                kind=kind,
                line=line,
                receptor=receptor,
            )
        )


def _nome_e_receptor(func: ast.expr) -> tuple[str, str] | None:
    """`(nome, receptor)` do que esta sendo chamado, ou `None` se nao ha nome.

    O receptor guarda a CADEIA inteira -- `spark.read` em
    `spark.read.parquet()` -- e nao so o ultimo segmento. Ele existe para
    `resolve.py` desambiguar nome de metodo comum, e o que identifica de onde o
    objeto veio e justamente a cadeia; cortando-a sobra a parte inutil.

    `ast.unparse` e nao reconstrucao a mao pelo mesmo motivo medido em
    `extract.py`: `ast.Str` e `ast.Num` sairam em 3.12, e `unparse` deu saida
    identica caractere por caractere em 3.10.20, 3.11.15 e 3.14.6.
    """
    if isinstance(func, ast.Name):
        return func.id, ""
    if isinstance(func, ast.Attribute):
        return func.attr, ast.unparse(func.value)
    return None


__all__ = ["Referencia", "extrair_referencias", "modulo_do_caminho"]
