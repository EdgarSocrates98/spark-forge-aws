"""Referencia -> aresta, ou declaracao explicita de que nao resolveu.

AMBIGUO NAO VIRA ARESTA
-----------------------
Esta e a decisao que a fase inteira existe para sustentar. O AST ve
`processar()` e nao sabe QUAL `processar`; se ha dois no indice, escolher um e
inventar. O custo da invencao nao aparece aqui, aparece muito depois: quem
seguir a aresta abre o arquivo errado, conclui a coisa errada, e nada no
caminho acusa -- porque uma aresta errada tem exatamente a mesma forma de uma
aresta certa. Referencia ambigua vai para `unresolved_refs` com `AMBIGUOUS`, e
o ponto cego fica CONTADO em vez de escondido atras de um palpite.

E o mesmo principio que `graph.unresolved` e `sql.unresolved` ja aplicam no
motor: ponto cego e ponto cego, e nao ausencia de problema.

NAO HA HEURISTICA DE TIPO, E ISSO CUSTA CARO DE PROPOSITO
---------------------------------------------------------
`df.filtrar()` NAO resolve, nem quando existe um unico `filtrar` na arvore
inteira. Ligar ali seria afirmar que `df` e do tipo que define `filtrar`, e
ninguem mediu isso -- deduzir tipo do nome da variavel e adivinhacao vestida de
analise. `UNKNOWN_RECEIVER` e a resposta honesta, e ela e a maior fatia do que
esta fase nao resolve: 10521 das 23901 chamadas desta arvore tem receptor.

As duas excecoes NAO sao inferencia de tipo, sao nome escrito por inteiro:

1. `Pipeline.executar()` -- o chamador nomeou o alvo completo, e o indice tem um
   no com esse nome qualificado. Nao ha o que inferir.
2. `self.ajudar()` -- `self` e resolvido para a CLASSE QUE ENVOLVE a chamada,
   que sai de `origem_qualificada` mais o `kind` que `nodes` ja guarda: o maior
   prefixo da origem que e um no de kind `class` no MESMO arquivo. Medido nesta
   arvore: dos 3080 metodos de classe, 3061 tem `self` como primeiro parametro,
   13 sao `staticmethod` e 6 usam `cls`; ZERO tem primeiro parametro com outro
   nome, que e o unico caso em que `self` no corpo apontaria para outra coisa.
   O ponto cego que sobra e despacho dinamico: uma subclasse que sobrescreve
   `ajudar` executa a versao dela, e a aresta aponta para a da classe base --
   que e a definicao que o codigo lido de fato nomeia. Fica dito.

O `self` para na classe envolvente e NAO cai para busca por nome simples. Se
caisse, `self.ajudar()` acharia qualquer `ajudar` da arvore, que e exatamente a
invencao recusada acima.

BUILTIN NAO E PONTO CEGO, MAS CONTINUA NO DENOMINADOR
-----------------------------------------------------
`len`, `print`, `range`, `ValueError` sao biblioteca padrao: eles nunca vao
estar no indice, porque nao estao na arvore. Registra-los em `unresolved_refs`
encheria a tabela de ruido e faria "N nao resolvidas" deixar de distinguir alvo
que valeria a pena resolver de alvo que nunca vai existir ali. Entao eles ficam
FORA da tabela -- e DENTRO do denominador da taxa, em `Resolucao.builtins`.
Tirar do numerador sem tirar do denominador seria maquiar o numero pelo lado de
fora, e um arquivo que so chama `print` publicaria 100% de resolucao.

A checagem de builtin vem DEPOIS da busca no indice, e a ordem nao e estilo: um
projeto que define a propria `filter` perderia as arestas dela em silencio se a
ordem fosse a outra. O conjunto de builtins vem de `vars(builtins)` do
interpretador que roda a indexacao -- entao um nome que nasceu builtin em 3.13
e classificado como builtin em 3.13 e como `NO_CANDIDATE` em 3.10. Nenhum dos
dois vira aresta, entao o efeito e so na contagem, e fica dito em vez de
descoberto.

IMPORT NAO E RESOLVIDO AQUI, E ISSO E CONTADO A PARTE
-----------------------------------------------------
Resolver import exige mapear modulo para arquivo, tratar import relativo e
pacote com `__init__`, e ainda decidir o que fazer quando o alvo e o proprio
MODULO -- que nao e no e nao cabe em `edges`. Nada disso foi feito. As 2528
referencias de import desta arvore nao viram aresta E nao viram ponto cego:
elas entram em `Resolucao.nao_tentadas`, porque ponto cego e o que se tentou
resolver e nao deu, nao o que nunca foi tentado. Enfia-las em
`unresolved_refs` inflaria a tabela em 2528 linhas que nao dizem nada sobre a
qualidade da resolucao.

A TAXA MEDIDA
-------------
Sobre esta arvore, com o indice construido por `indexar` (389 arquivos, 5996
nos, 1 ilegivel) e as referencias de `extrair_referencias`, 23901 chamadas
tentadas:

    arestas               8794   36.8%
    UNKNOWN_RECEIVER      9870   41.3%
    builtin               4356   18.2%
    NO_CANDIDATE           625    2.6%
    AMBIGUOUS              144    0.6%
    NO_SOURCE_NODE         112    0.5%

    taxa de resolucao            36.8%

Contribuicao da regra do `self`, medida ligando e desligando SO ela sobre as
mesmas referencias: 650 arestas, 2.7 pontos percentuais -- sem ela a taxa cai
para 34.1% e os `UNKNOWN_RECEIVER` sobem para 10520.

36.8% e um numero baixo, e ele e publicado como esta. Os 41.3% de
`UNKNOWN_RECEIVER` sao o preco declarado de nao inventar tipo, e e la que a
proxima fase tem o que ganhar -- nao mexendo nestas regras. Os numeros se movem
com a arvore e ficam aqui DATADOS (fase J4) em vez de reescritos a cada commit,
pelo mesmo motivo que os de `indexar`: o que nao se move e a ordem de grandeza.

QUEM ESCREVE NO BANCO NAO E ESTE MODULO
---------------------------------------
`resolver` devolve dados e nao toca em `edges` nem em `unresolved_refs`. A
gravacao mora em quem ja tem a transacao aberta -- `indexar` --, e enquanto
ninguem a fizer as duas tabelas continuam VAZIAS no indice real. Esta dito aqui
porque uma tabela vazia por falta de ligacao e indistinguivel de uma tabela
vazia por falta de dado, e essa confusao e o defeito que este modulo inteiro
existe para nao ter.
"""

from __future__ import annotations

import builtins as _builtins
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sparkforge.codeintel.refs import Referencia

_CALLS = "calls"
_CLASSE = "class"
_RECEPTOR_DA_INSTANCIA = "self"

# Nao ha aresta com confianca menor que 1.0 saindo daqui: o que nao e casamento
# exato e unico nao vira aresta. A coluna existe para quando houver resolucao
# por tipo; ate la, um valor intermediario seria palpite com casa decimal.
_CONFIANCA_EXATA = 1.0

AMBIGUOUS = "AMBIGUOUS"
NO_CANDIDATE = "NO_CANDIDATE"
UNKNOWN_RECEIVER = "UNKNOWN_RECEIVER"
NO_SOURCE_NODE = "NO_SOURCE_NODE"
AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"

# Ver a docstring do modulo: depende do interpretador, e por isso o efeito dele
# esta limitado a contagem -- builtin e nao-builtin nao viram aresta do mesmo
# jeito.
_BUILTINS = frozenset(vars(_builtins))

_SQL_CATALOGO = (
    "SELECT nodes.id, nodes.kind, nodes.qualified_name, files.path"
    "  FROM nodes"
    "  JOIN files ON files.id = nodes.file_id"
)


@dataclass(frozen=True)
class Aresta:
    """Uma chamada resolvida, entre dois nos que existem em `nodes`.

    Imutavel pelo mesmo motivo que `Referencia`: e EVIDENCIA. Consumidor que
    corrige `target_id` em vez de registrar um fato novo apaga o resultado da
    resolucao, e aresta editada em silencio e indistinguivel de aresta medida.
    """

    source_id: str
    target_id: str
    kind: str
    line: int
    confidence: float


@dataclass(frozen=True)
class NaoResolvida:
    """Uma referencia que se TENTOU resolver e nao deu, com o motivo.

    `source_id` e opcional porque chamada no topo do modulo nao sai de no
    nenhum -- e `caminho` nao e: sem onde, o ponto cego vira um numero que
    ninguem consegue ir ver.
    """

    source_id: str | None
    reference_name: str
    reference_kind: str
    caminho: str
    line: int
    reason: str


@dataclass(frozen=True)
class Resolucao:
    """As duas metades do contrato, mais o que ficou fora de cada uma.

    `builtins` e `nao_tentadas` sao campos e nao detalhe de implementacao: sao
    eles que impedem a taxa de melhorar so porque alguem tirou linha da tabela.
    """

    arestas: tuple[Aresta, ...]
    nao_resolvidas: tuple[NaoResolvida, ...]
    builtins: int
    nao_tentadas: int

    @property
    def taxa_de_resolucao(self) -> float:
        """Arestas sobre CHAMADAS tentadas, contadas agora e nao guardadas.

        Propriedade e nao campo de proposito: um numero gravado na construcao
        envelheceria em silencio no dia em que alguem filtrasse uma das listas.

        O denominador inclui `builtins` -- ver a docstring do modulo -- e exclui
        `nao_tentadas`, que sao os imports: colocar no denominador o que nunca
        foi tentado mediria a ausencia de uma fase, nao a qualidade desta.

        Zero chamada devolve 0.0 e nao levanta, e nao vira 1.0: 100% sobre nada
        seria a mentira mais confortavel que este modulo poderia contar.
        """
        tentadas = len(self.arestas) + len(self.nao_resolvidas) + self.builtins
        if tentadas == 0:
            return 0.0
        return len(self.arestas) / tentadas


@dataclass(frozen=True)
class Catalogo:
    """O indice visto do jeito que a resolucao pergunta: por nome qualificado.

    Nao ha busca por `nodes.name` aqui, e a ausencia e deliberada. Chamada nua
    `processar()` NAO alcanca `Pipeline.processar` -- em Python ela procura o
    global do modulo --, e um mapa por nome simples casaria as duas, produzindo
    aresta para metodo que a linguagem nunca chamaria daquele ponto.

    `classes` guarda `(caminho, nome_qualificado)` dos nos de kind `class`
    porque e assim que `self` acha a classe envolvente -- ver a docstring do
    modulo.
    """

    por_qualificado: dict[tuple[str, str], tuple[str, ...]]
    qualificado_global: dict[str, tuple[str, ...]]
    classes: frozenset[tuple[str, str]]


def catalogo_do_banco(conexao: sqlite3.Connection) -> Catalogo:
    """Le `nodes` e monta o catalogo.

    Le o BANCO, e nao a arvore de novo: os ids que a aresta carrega precisam ser
    os mesmos que `nodes` guarda. Uma segunda extracao a partir do AST produziria
    ids que casam hoje e divergem no dia em que a assinatura ou o caminho mudar
    de forma -- e aresta apontando para no que nao existe nao levanta, so
    devolve nada.

    Recebe conexao e nao caminho de banco porque quem chama ja esta dentro da
    transacao de `indexar`: abrir uma segunda conexao no meio dela leria o banco
    ANTES da carga, e o catalogo viria vazio.
    """
    por_qualificado: dict[tuple[str, str], list[str]] = {}
    qualificado_global: dict[str, list[str]] = {}
    classes: set[tuple[str, str]] = set()

    for identificador, kind, qualificado, caminho in conexao.execute(_SQL_CATALOGO):
        por_qualificado.setdefault((caminho, qualificado), []).append(identificador)
        qualificado_global.setdefault(qualificado, []).append(identificador)
        if kind == _CLASSE:
            classes.add((caminho, qualificado))

    return Catalogo(
        por_qualificado={chave: tuple(ids) for chave, ids in por_qualificado.items()},
        qualificado_global={
            chave: tuple(ids) for chave, ids in qualificado_global.items()
        },
        classes=frozenset(classes),
    )


def resolver(
    referencias_por_arquivo: Mapping[str, Sequence[Referencia]],
    catalogo: Catalogo,
) -> Resolucao:
    """Resolve as referencias de varios arquivos de uma vez, e conta o resultado.

    Recebe TODOS os arquivos numa chamada em vez de um por vez porque a taxa de
    resolucao e do conjunto: somar `Resolucao` de arquivo em arquivo daria a
    quem chama a chance de somar seis das sete e publicar um numero que parece o
    total.

    O caminho vem da CHAVE do mapa e nao da referencia: `Referencia` guarda a
    origem qualificada, que nao diz em que arquivo ela esta. Ele precisa ser o
    mesmo caminho relativo que `files.path` guarda, senao nenhuma consulta ao
    catalogo casa e tudo vira `NO_CANDIDATE` -- em silencio, com a taxa em zero.
    """
    arestas: list[Aresta] = []
    nao_resolvidas: list[NaoResolvida] = []
    builtins = 0
    nao_tentadas = 0

    for caminho, referencias in referencias_por_arquivo.items():
        for referencia in referencias:
            if referencia.kind != _CALLS:
                nao_tentadas += 1
                continue

            origem = _origem(caminho, referencia, catalogo)
            alvo, motivo = _alvo(caminho, referencia, catalogo)

            if alvo is None:
                if motivo is None:
                    builtins += 1
                    continue
                nao_resolvidas.append(
                    _nao_resolvida(caminho, referencia, origem, motivo)
                )
                continue

            if origem is None:
                # O alvo resolveu e a aresta e impossivel mesmo assim:
                # `edges.source_id` e NOT NULL, e chamada no topo do modulo nao
                # sai de no nenhum. Contado para que a fatia do grafo que fica
                # de fora -- script de topo a fundo -- seja visivel.
                nao_resolvidas.append(
                    _nao_resolvida(
                        caminho,
                        referencia,
                        None,
                        _motivo_da_origem(caminho, referencia, catalogo),
                    )
                )
                continue

            arestas.append(
                Aresta(
                    source_id=origem,
                    target_id=alvo,
                    kind=referencia.kind,
                    line=referencia.line,
                    confidence=_CONFIANCA_EXATA,
                )
            )

    return Resolucao(
        arestas=tuple(arestas),
        nao_resolvidas=tuple(nao_resolvidas),
        builtins=builtins,
        nao_tentadas=nao_tentadas,
    )


def _nao_resolvida(
    caminho: str,
    referencia: Referencia,
    origem: str | None,
    motivo: str,
) -> NaoResolvida:
    return NaoResolvida(
        source_id=origem,
        reference_name=referencia.nome,
        reference_kind=referencia.kind,
        caminho=caminho,
        line=referencia.line,
        reason=motivo,
    )


def _origem(caminho: str, referencia: Referencia, catalogo: Catalogo) -> str | None:
    """O id do no de onde a chamada sai, ou `None` se ele nao existe ou repete.

    `origem_qualificada` casa caractere por caractere com `nodes.qualified_name`
    porque as duas saem da MESMA pilha de escopo -- ver a docstring de
    `refs.py`. Quando a origem e o modulo, nao ha no com esse nome e a resposta
    e `None`, que e o caso comum de chamada no topo do arquivo.
    """
    candidatos = catalogo.por_qualificado.get((caminho, referencia.origem_qualificada))
    if candidatos is None or len(candidatos) != 1:
        return None
    return candidatos[0]


def _motivo_da_origem(
    caminho: str, referencia: Referencia, catalogo: Catalogo
) -> str:
    """Distingue "nao ha no de origem" de "ha mais de um".

    Os dois impedem a aresta e por motivos diferentes: o primeiro e chamada no
    topo do modulo, que nenhuma fase futura conserta sem inventar no de arquivo;
    o segundo e a mesma funcao definida nos dois ramos de um `if/else` de
    compatibilidade, que tem conserto. Uma `reason` so para os dois esconderia
    qual dos dois esta acontecendo.
    """
    candidatos = catalogo.por_qualificado.get((caminho, referencia.origem_qualificada))
    if candidatos is None:
        return NO_SOURCE_NODE
    return AMBIGUOUS_SOURCE


def _alvo(
    caminho: str, referencia: Referencia, catalogo: Catalogo
) -> tuple[str | None, str | None]:
    """`(id_do_alvo, None)` quando resolve; `(None, motivo)` quando nao.

    O motivo `None` com alvo `None` e o builtin: nao resolveu e nao e ponto
    cego. Ver a docstring do modulo.
    """
    if referencia.receptor:
        return _alvo_com_receptor(caminho, referencia, catalogo)
    return _alvo_por_nome_nu(caminho, referencia, catalogo)


def _alvo_com_receptor(
    caminho: str, referencia: Referencia, catalogo: Catalogo
) -> tuple[str | None, str | None]:
    """So resolve quando o receptor NOMEIA o alvo -- nunca quando ele o sugere."""
    if referencia.receptor == _RECEPTOR_DA_INSTANCIA:
        classe = _classe_envolvente(caminho, referencia.origem_qualificada, catalogo)
        if classe is None:
            return None, UNKNOWN_RECEIVER
        # Sem queda para busca global: `self` e a classe envolvente ou nada.
        return _unico(
            catalogo.por_qualificado.get((caminho, f"{classe}.{referencia.nome}")),
            UNKNOWN_RECEIVER,
        )

    chave = f"{referencia.receptor}.{referencia.nome}"
    do_arquivo = catalogo.por_qualificado.get((caminho, chave))
    if do_arquivo is not None:
        return _unico(do_arquivo, UNKNOWN_RECEIVER)
    return _unico(catalogo.qualificado_global.get(chave), UNKNOWN_RECEIVER)


def _alvo_por_nome_nu(
    caminho: str, referencia: Referencia, catalogo: Catalogo
) -> tuple[str | None, str | None]:
    """Escopo aninhado, depois topo do proprio arquivo, depois arvore inteira.

    A ordem e a regra de resolucao de nome do Python, e nao desempate escolhido:
    `processar()` dentro de `executar` acha primeiro uma `processar` definida
    dentro de `executar`, depois a global do modulo, e so entao o que veio de
    fora por import. Sem os dois primeiros passos, um projeto com duas
    `processar` em modulos diferentes declararia AMBIGUOUS onde a linguagem nao
    tem duvida nenhuma.

    Nenhum passo cai para o seguinte quando encontra MAIS DE UM candidato: dois
    candidatos no mesmo escopo e ambiguidade de verdade, e seguir adiante ali
    trocaria a ambiguidade por um palpite de outro escopo.
    """
    aninhado = f"{referencia.origem_qualificada}.{referencia.nome}"
    for candidatos in (
        catalogo.por_qualificado.get((caminho, aninhado)),
        catalogo.por_qualificado.get((caminho, referencia.nome)),
        catalogo.qualificado_global.get(referencia.nome),
    ):
        if candidatos:
            return _unico(candidatos, NO_CANDIDATE)

    if referencia.nome in _BUILTINS:
        # Depois do indice, nunca antes: quem define a propria `filter` perderia
        # as arestas dela se a ordem fosse a outra.
        return None, None
    return None, NO_CANDIDATE


def _unico(
    candidatos: tuple[str, ...] | None, motivo_se_vazio: str
) -> tuple[str | None, str | None]:
    """Um candidato resolve; varios sao AMBIGUOUS; nenhum e o motivo de quem chama.

    Esta funcao e o lugar unico onde "varios" vira decisao, e por isso ela nao
    tem ramo que escolhe: nao ha `candidatos[0]`, nao ha ordenacao, nao ha
    preferencia. Se aparecer um, a fase perdeu a garantia que ela existe para
    dar.
    """
    if not candidatos:
        return None, motivo_se_vazio
    if len(candidatos) > 1:
        return None, AMBIGUOUS
    return candidatos[0], None


def _classe_envolvente(
    caminho: str, origem_qualificada: str, catalogo: Catalogo
) -> str | None:
    """O maior prefixo da origem que e um no de kind `class` no mesmo arquivo.

    Do maior para o menor porque classe aninhada existe: dentro de
    `Externa.Interna.metodo`, `self` e `Externa.Interna`, nao `Externa`. E a
    resposta sai do que o indice GRAVOU -- ha um no de kind `class` com esse
    nome qualificado --, nao de uma convencao de nomenclatura.

    Funcao de topo com um parametro chamado `self` nao tem prefixo nenhum que
    seja classe, e devolve `None`.
    """
    partes = origem_qualificada.split(".")
    for corte in range(len(partes) - 1, 0, -1):
        prefixo = ".".join(partes[:corte])
        if (caminho, prefixo) in catalogo.classes:
            return prefixo
    return None


__all__ = [
    "AMBIGUOUS",
    "AMBIGUOUS_SOURCE",
    "NO_CANDIDATE",
    "NO_SOURCE_NODE",
    "UNKNOWN_RECEIVER",
    "Aresta",
    "Catalogo",
    "NaoResolvida",
    "Resolucao",
    "catalogo_do_banco",
    "resolver",
]
