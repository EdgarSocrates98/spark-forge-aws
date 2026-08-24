"""AST -> no do indice, sem o corpo.

O QUE ESTE MODULO NAO GUARDA
----------------------------
Corpo de funcao (INV-010). O indice guarda ONDE o simbolo esta -- caminho e
linhas -- e quem precisa do codigo le o arquivo. Guardar corpo faria o banco
virar copia do repositorio, com o custo de disco e o risco de vazamento junto:
uma senha escrita no corpo passaria a existir em dois lugares.

O NOME QUALIFICADO E A UNICIDADE, E ELE NASCE AQUI
--------------------------------------------------
`node_id` recebe uma string e nao tem como conferir se ela foi qualificada --
esta dito na docstring dele. Quem cumpre esse contrato e a pilha de escopo
daqui. Medido com ESTE extrator sobre a arvore de trabalho da fase J3 -- 378
arquivos `.py` que a varredura enxerga, 5754 simbolos em todos os niveis --,
alimentando `node_id` com um nome ou com o outro e os outros tres campos iguais:

    nome simples      5667 ids distintos -- 87 simbolos colidindo
    nome qualificado  5754 ids distintos --  0 colidindo

`adapters/platforms/targets.py` sozinho tem quatro `platform_name(self)` em
quatro classes (linhas 13, 28, 42 e 58). Sem prefixo de classe os quatro tem
caminho, kind, nome e assinatura iguais, produzem o mesmo id, e o indice perde
tres nos por sobrescrita, calado.

O numero de colisoes se move com a arvore e com a forma da assinatura -- uma
medicao anterior, com assinatura construida de outro jeito, deu 134 sobre 5695
simbolos. O que NAO se move e a direcao: qualificar zera, nao qualificar perde.

POR QUE A ASSINATURA VEM DE `ast.unparse`
-----------------------------------------
O modulo `ast` mudou entre 3.10 e 3.14: `ast.Str` e `ast.Num` sairam em 3.12, e
reconstruir default a mao dependeria deles. `ast.unparse` existe desde 3.9 e foi
MEDIDO devolvendo saida identica, caractere por caractere, em 3.10.20, 3.11.15 e
3.14.6, para assinatura com default de string, tupla, lista, parametro
posicional-apenas, `*args`, `**kw` e anotacao de retorno. Isso importa porque a
assinatura entra no id: assinatura instavel entre versoes daria id instavel, e a
fase incremental veria "mudou" onde nada mudou.

O resultado de `ast.unparse` passa por `normalizar_assinatura` ANTES de virar
`No`, entao nenhum valor literal de default chega ao dataclass -- e daqui ao
banco, que persiste.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from sparkforge.codeintel.ids import normalizar_assinatura


@dataclass(frozen=True)
class No:
    """Um simbolo extraido do AST, sem o corpo dele.

    `normalized_signature` ja vem por `normalizar_assinatura`, entao nenhum
    valor literal de default chega aqui -- e daqui ao banco, que persiste.
    """

    kind: str  # "class" | "function" | "method"
    name: str
    qualified_name: str
    path: str  # relativo a raiz, sempre
    start_line: int
    end_line: int
    normalized_signature: str


def extrair_nos(fonte: str, caminho: str) -> list[No]:
    """Simbolos de `fonte`, ou lista vazia se ela nao parseia.

    Sintaxe invalida e ponto CEGO, nao erro fatal. Um repositorio de cliente tem
    arquivo com sintaxe de outra versao de Python, template com placeholder,
    arquivo pela metade -- este proprio repositorio tem
    `fixtures/graph/fonte_que_nao_compila/input/carga_quebrada.py`, fixture
    deliberada. Derrubar a indexacao inteira por causa de um seria trocar
    cobertura parcial por nenhuma.

    Quem precisa DISTINGUIR "nao parseia" de "parseia e nao tem simbolo" usa
    `extrair_nos_ou_none` -- ver a docstring dela.
    """
    nos = extrair_nos_ou_none(fonte, caminho)
    return [] if nos is None else nos


def extrair_nos_ou_none(fonte: str, caminho: str) -> list[No] | None:
    """Como `extrair_nos`, mas devolve `None` quando a fonte nao parseia.

    Existe porque `indexar` conta `ilegiveis`, e a lista vazia nao serve de
    sinal: arquivo que nao parseia e modulo que so tem constantes produzem os
    dois `[]`. Medido sobre a arvore de trabalho da fase J3, 45 dos 378 arquivos
    `.py` que a varredura enxerga nao tem nenhuma classe nem funcao -- os
    `__init__.py` de reexportacao e os jobs PySpark de fixture, que sao script
    de topo a fundo (`fixtures/migration/legacy_conf/input/job.py`,
    `examples/glue_iceberg_job.py`). Contra UM unico arquivo que nao parseia.
    Usar `[]` como sinal de ilegivel multiplicaria o contador por 45.

    `ValueError` esta na captura porque a excecao do byte nulo MUDOU de tipo
    entre as versoes que o CI roda, e isso foi medido com `a = 1\\x00`:

        3.10.20   ValueError
        3.11.15   SyntaxError
        3.14.6    SyntaxError

    Capturar so `SyntaxError` derrubaria a indexacao inteira em 3.10 por causa
    de um arquivo com byte nulo. `RecursionError` NAO esta na captura porque a
    hipotese nao se confirmou: aninhamento de 1000, 5000 e 20000 colchetes deu
    `SyntaxError` nas tres versoes, nao `RecursionError`.
    """
    try:
        arvore = ast.parse(fonte)
    except (SyntaxError, ValueError):
        return None
    coletor = _Coletor(caminho)
    coletor.visit(arvore)
    return coletor.nos


class VisitanteComEscopo(ast.NodeVisitor):
    """A pilha de escopo, UMA so, para quem precisar de nome qualificado.

    Publica e herdada de proposito. `refs.py` precisa exatamente desta pilha
    para dizer de QUAL funcao sai cada chamada, e uma segunda pilha divergiria
    da primeira em silencio -- J0 ja pagou esse preco com quatro detectores de
    segredo que discordavam entre si. Quem quiser escopo herda daqui e
    implementa `_ao_entrar`; quem escrever `visit_ClassDef` proprio esta
    duplicando, e `tests/test_codeintel_refs.py` afirma que ninguem escreveu.

    Herda de `NodeVisitor` -- e nao percorre so `.body` de def e class -- porque
    def dentro de `if TYPE_CHECKING:` ou de `try/except ImportError` e ordinario,
    e percorrer so os corpos de definicao perderia esses simbolos sem sinal.

    A pilha guarda o TIPO de cada escopo alem do nome, porque so o tipo do
    escopo imediato decide entre `method` e `function`: uma funcao aninhada
    dentro de um metodo e `function`, mesmo tendo uma classe mais acima.

    PONTO CEGO ASSUMIDO: decorador e valor de default sao AVALIADOS no escopo de
    FORA, e chegam aqui ja dentro do escopo da funcao que decoram -- `@fabrica()`
    sobre `def f` conta como chamada saindo de `f`. Sao expressoes do proprio no
    de definicao, e separa-las exigiria visitar `decorator_list` e `args` antes
    de empilhar. Nao foi feito porque a pilha e o contrato compartilhado com
    `extract.py`, e o desvio e de uma linha por definicao decorada; fica dito
    para nao ser descoberto como surpresa numa travessia.
    """

    def __init__(self) -> None:
        self._nomes: list[str] = []
        self._tipos: list[str] = []

    def visit_ClassDef(self, no: ast.ClassDef) -> None:
        self._ao_entrar(no, "class")
        self._nomes.append(no.name)
        self._tipos.append("class")
        self.generic_visit(no)
        self._nomes.pop()
        self._tipos.pop()

    def visit_FunctionDef(self, no: ast.FunctionDef) -> None:
        self._funcao(no)

    def visit_AsyncFunctionDef(self, no: ast.AsyncFunctionDef) -> None:
        self._funcao(no)

    def _funcao(self, no: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = "method" if self._tipos and self._tipos[-1] == "class" else "function"
        self._ao_entrar(no, kind)
        self._nomes.append(no.name)
        self._tipos.append("function")
        self.generic_visit(no)
        self._nomes.pop()
        self._tipos.pop()

    def _ao_entrar(
        self,
        no: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
    ) -> None:
        """Gancho chamado ao ENTRAR numa definicao, antes de empilha-la.

        Antes e nao depois porque o nome qualificado de uma definicao nao inclui
        ela mesma duas vezes: `P.m` sai da pilha `["P"]` mais `m`.

        Vazio por default: quem so quer a pilha -- `refs.py` -- nao registra nada
        na definicao em si.
        """

    def _escopo_qualificado(self) -> str:
        """Nome qualificado do escopo CORRENTE, ou string vazia no topo do modulo.

        Mesma forma que `No.qualified_name`, e isso nao e coincidencia: e por
        essa igualdade que `resolve.py` consegue casar a origem de uma chamada
        com o no de onde ela sai. Se as duas divergissem, toda aresta que sai de
        metodo cairia em `unresolved_refs` sem ninguem entender por que.
        """
        return ".".join(self._nomes)


class _Coletor(VisitanteComEscopo):
    """Escopo -> `No`. Toda a pilha vem da base; aqui so mora o que virar linha."""

    def __init__(self, caminho: str) -> None:
        super().__init__()
        self.caminho = caminho
        self.nos: list[No] = []

    def _ao_entrar(
        self,
        no: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
    ) -> None:
        assinatura = (
            _assinatura_de_classe(no)
            if isinstance(no, ast.ClassDef)
            else _assinatura_de_funcao(no)
        )
        self._registrar(no, kind, assinatura)

    def _registrar(
        self,
        no: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
        assinatura: str,
    ) -> None:
        # `end_lineno` existe desde 3.8 nestes tres tipos de no, mas e Optional
        # na anotacao do `ast`. Cair para `lineno` mantem o invariante
        # `end_line >= start_line` sem inventar posicao que nao foi medida.
        fim = no.end_lineno if no.end_lineno is not None else no.lineno
        self.nos.append(
            No(
                kind=kind,
                name=no.name,
                qualified_name=".".join([*self._nomes, no.name]),
                path=self.caminho,
                start_line=no.lineno,
                end_line=fim,
                normalized_signature=normalizar_assinatura(assinatura),
            )
        )


def _assinatura_de_funcao(no: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """`nome(parametros) -> retorno`, na forma que um humano leria.

    A anotacao de retorno entra porque faz parte da assinatura como ela e lida,
    e `normalizar_assinatura` a preserva de proposito -- ela nao e valor de
    default, e nao carrega segredo.
    """
    assinatura = f"{no.name}({ast.unparse(no.args)})"
    if no.returns is not None:
        assinatura += f" -> {ast.unparse(no.returns)}"
    return assinatura


def _assinatura_de_classe(no: ast.ClassDef) -> str:
    """`Nome(bases, palavras_chave)` -- o cabecalho, nao o corpo.

    As bases distinguem duas classes de mesmo nome, que e para o que a
    assinatura serve no id.

    O VALOR das palavras-chave NAO sobrevive: `class P(Base, metaclass=Meta)`
    vira `P(Base, metaclass=<literal>)`, porque `normalizar_assinatura` mascara
    tudo depois de um `=` no nivel de topo, e ela nao tem como saber que
    `metaclass` nao carrega segredo. Sobra o NOME da palavra-chave, e e ele que
    entra no id -- perda aceita para nao abrir excecao num varredor cuja regra
    inteira e nao deixar valor passar.
    """
    partes = [ast.unparse(base) for base in no.bases]
    partes += [
        f"{chave.arg}={ast.unparse(chave.value)}"
        if chave.arg is not None
        else f"**{ast.unparse(chave.value)}"
        for chave in no.keywords
    ]
    return f"{no.name}({', '.join(partes)})"


__all__ = ["No", "VisitanteComEscopo", "extrair_nos", "extrair_nos_ou_none"]
