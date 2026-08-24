"""Expansao deterministica de consulta e escore composto de recuperacao.

Duas metades da secao 48 e da secao 49 da SPEC, no mesmo modulo porque a
segunda so tem sentido sobre a saida da primeira: o escore precisa saber quais
termos vieram da pergunta (literais) e quais vieram do dicionario (derivados),
e separar isso em dois arquivos obrigaria a repassar a distincao por parametro
em toda chamada.

POR QUE O ESCORE E INTEIRO
--------------------------
A secao 49 escreve o escore como soma de componentes, e nao diz o tipo. Ele e
INTEIRO aqui por uma razao de determinismo, nao de gosto: `0.1 + 0.2 != 0.3` em
ponto flutuante, e dois candidatos que deveriam empatar por construcao passam a
diferir no ultimo bit conforme a ORDEM em que os componentes foram somados. O
empate deixaria de acontecer, o desempate explicito deixaria de ser exercitado,
e a ordem passaria a depender de qual candidato o loop somou primeiro -- que e
um teste que falha uma vez a cada muitas execucoes. Com inteiro o empate e
exato, e o desempate `(path, start_line, node_id)` roda de verdade.

DOIS COMPONENTES DA SPEC VALEM ZERO, E ISSO ESTA DECLARADO
-----------------------------------------------------------
A secao 49 lista oito componentes. Seis sao mensuraveis sobre o indice de hoje.
Dois NAO sao, e eles aparecem em `Escore` com valor zero em vez de sumir:

- `entrypoint`: `nodes` guarda `kind` em {module, class, function, method}. Nao
  ha marca de ponto de entrada -- nem `__main__`, nem entrada de console script,
  nem handler. Inferir "e entrypoint porque ninguem o chama" confundiria ponto
  de entrada com simbolo morto e com simbolo cuja chamada caiu em
  `unresolved_refs` -- e a MAIORIA das referencias deste indice cai la, com
  `UNKNOWN_RECEIVER` dominando o motivo. O numero absoluto anda com a arvore e
  por isso nao esta escrito aqui; `Resultado.nao_resolvidas` de `indexar` o
  devolve medido. Um peso construido sobre essa inferencia ordenaria por
  acidente.
- `lineage`: nao existe no de tabela no schema. `edges` grava chamada; leitura,
  escrita e transformacao de dado nao tem onde ser ponta de aresta. Nao ha o que
  medir.

Ficam como campo de valor zero, e nao como componente ausente, porque a
diferenca importa para quem le a saida: zero declarado diz "a SPEC pede, o
indice ainda nao sustenta". Campo ausente diria "ninguem pensou nisso".
`test_componentes_sem_lastro_sao_zero_declarado` prende os dois onde estao.

O QUE ESTE MODULO NAO PROMETE
-----------------------------
Ele melhora a ORDEM de um conjunto de candidatos que a busca por nome ja
devolveu. Ele nao torna a busca por nome mais barata que `grep -n "def X"`: na
medicao da fase J3 o indice PERDIA nessa pergunta e GANHAVA em pergunta
estrutural, por fatores da ordem de dois para um e de dez para um
respectivamente. As razoes andam com a arvore e nao ficam gravadas aqui; o
sinal e que nao muda, e ranking nao o inverte. Nao e para isso que ele existe.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.codeintel.search import Achado

DICIONARIO_PADRAO = Path(__file__).with_name("domain_terms.yaml")

# Peso de cada componente da secao 49. Sao constantes de modulo e nao numeros
# soltos no corpo do escore para que uma mudanca de politica de ordenacao seja
# uma linha visivel no diff, e nao um literal escondido numa expressao.
PESO_EXACT_NAME = 100
PESO_QUALIFIED_NAME = 40
PESO_FTS_TOPO = 30
PESO_PATH = 20
PESO_GRAFO_ANCORA = 25
PESO_GRAFO_POR_SALTO = 10
PESO_DOMINIO_POR_TERMO = 10
# Teto do componente de dominio. Sem teto, um cluster grande (o de `iceberg`
# tem sete termos) daria 70 pontos a qualquer simbolo que casasse todos eles e
# passaria por cima do `exact_name`, que vale 100 -- a expansao passaria a
# mandar mais que a palavra que a pessoa digitou.
DOMINIO_MAXIMO_DE_TERMOS = 3
# Os dois componentes que a SPEC pede e o indice nao sustenta. Ver a docstring
# do modulo: ficam declarados em zero, nao omitidos.
PESO_ENTRYPOINT = 0
PESO_LINEAGE = 0

_COMBINANTE = "Mn"


def _normalizar(texto: str) -> str:
    """`texto` em minuscula e sem acento, para COMPARACAO e nada mais.

    O indice guarda o nome como ele e -- `search.construir_consulta` usa `\\w+`
    justamente para nao quebrar identificador nao-ASCII, que cliente tem. Esta
    normalizacao existe so do lado do dicionario e do lado da comparacao: quem
    escreve "junção" na pergunta tem que casar o gatilho "juncao", e sem isso o
    cluster de join nunca dispararia para metade dos usuarios que escrevem em
    portugues. O termo que sai para a busca continua sendo o do dicionario, que
    e ASCII por construcao.
    """
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != _COMBINANTE)
    return sem_acento.casefold()


@dataclass(frozen=True)
class Dicionario:
    """O vocabulario carregado, com a versao que o produziu.

    `versao` nao e enfeite: uma expansao gravada num case so e reproduzivel se
    der para dizer com qual vocabulario ela foi feita, e a versao do pacote nao
    serve porque ela muda por motivos que nao sao este.
    """

    versao: str
    schema_version: int
    stopwords: frozenset[str]
    # {gatilho normalizado: (id do cluster, termos)}
    gatilhos: Mapping[str, tuple[str, tuple[str, ...]]]


def _texto(valor: Any, onde: str) -> str:
    """`valor` como texto, ou erro que diz qual entrada do YAML esta errada.

    YAML 1.1 resolve `no`, `on`, `y` e `yes` sem aspas como booleano, e uma
    stopword assim chegaria aqui como `False`. Falhar com o nome da entrada e o
    que transforma isso em conserto de trinta segundos; deixar passar
    silenciosamente faria "no" voltar a ser termo de busca sem que nada acuse.
    """
    if not isinstance(valor, str):
        raise ValueError(f"{onde}: esperava texto, veio {type(valor).__name__} ({valor!r})")
    return valor


@lru_cache(maxsize=4)
def carregar_dicionario(caminho: str | None = None) -> Dicionario:
    """O dicionario de dominio, lido uma vez por caminho.

    Cache por `lru_cache` e nao por variavel global porque o teste precisa
    carregar um dicionario de fixture sem envenenar o padrao para os testes
    seguintes -- chave diferente, entrada diferente. `maxsize=4` porque o
    numero de dicionarios distintos vivos num processo e o padrao mais o que um
    teste montar, nunca uma colecao.

    `yaml.safe_load` e nao `yaml.load`: o arquivo e nosso, mas o construtor
    completo do PyYAML instancia objeto arbitrario, e um carregador que aceita
    isso e uma porta que so precisa de um arquivo trocado para virar execucao.
    """
    alvo = Path(caminho) if caminho is not None else DICIONARIO_PADRAO
    dados = yaml.safe_load(alvo.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError(f"{alvo}: dicionario de dominio vazio ou nao mapeado")

    stopwords = frozenset(
        _normalizar(_texto(p, f"{alvo}: stopwords")) for p in dados.get("stopwords", ())
    )

    gatilhos: dict[str, tuple[str, tuple[str, ...]]] = {}
    for bruto in dados.get("clusters", ()):
        identificador = _texto(bruto.get("id", ""), f"{alvo}: clusters[].id")
        termos = tuple(
            _texto(t, f"{alvo}: clusters[{identificador}].termos") for t in bruto.get("termos", ())
        )
        for gatilho in bruto.get("gatilhos", ()):
            chave = _normalizar(_texto(gatilho, f"{alvo}: clusters[{identificador}].gatilhos"))
            # Primeiro cluster vence, e a ordem do arquivo decide. Um gatilho
            # repetido em dois clusters seria expansao dependente da ordem de
            # iteracao se o ultimo vencesse por acaso; assim ele e uma decisao
            # de quem escreve o arquivo, e o teste de expansao a exercita.
            gatilhos.setdefault(chave, (identificador, termos))

    return Dicionario(
        versao=_texto(dados.get("version", ""), f"{alvo}: version"),
        schema_version=int(dados.get("schema_version", 0)),
        stopwords=stopwords,
        gatilhos=gatilhos,
    )


@dataclass(frozen=True)
class Expansao:
    """O que a pergunta virou, e de onde cada pedaco veio.

    `literais` e `derivados` ficam SEPARADOS porque o escore trata os dois de
    forma diferente: o que a pessoa escreveu vale `exact_name`, o que o
    dicionario acrescentou vale `dominio`, que e dez vezes menor. Juntar os dois
    numa lista so faria a expansao competir de igual para igual com a pergunta.
    """

    literais: tuple[str, ...]
    derivados: tuple[str, ...]
    clusters: tuple[str, ...]
    versao: str

    @property
    def termos(self) -> tuple[str, ...]:
        """Tudo que a busca deve procurar, literais primeiro.

        A ordem importa porque quem consome corta por limite: cortar cedo tem
        que sacrificar termo derivado, nunca a palavra que a pessoa digitou.
        """
        return self.literais + self.derivados


def _tokens(texto: str) -> list[str]:
    """Palavras de `texto`, normalizadas, na ordem em que aparecem.

    Quebra em qualquer coisa que nao seja letra ou digito -- `_` incluido, ao
    contrario de `search._TOKEN`. La o alfabeto existe para casar identificador
    Python inteiro; aqui ele existe para casar PALAVRA de uma pergunta em
    linguagem natural, e `latest_per_key` numa pergunta deve disparar os
    gatilhos de `latest`, `per` e `key`, nao procurar por um simbolo com esse
    nome exato -- para isso ha `buscar`, que o chamador ja usa em cima destes
    tokens.
    """
    palavra: list[str] = []
    saida: list[str] = []
    for caractere in _normalizar(texto):
        if caractere.isalnum():
            palavra.append(caractere)
        elif palavra:
            saida.append("".join(palavra))
            palavra = []
    if palavra:
        saida.append("".join(palavra))
    return saida


def expandir(tarefa: str, *, dicionario: str | None = None) -> Expansao:
    """A pergunta virada em conjunto de termos de busca, sem rede e sem modelo.

    Deterministica em tres eixos, e os tres tiveram que ser decididos:

    1. `literais` sai na ORDEM DE APARICAO, deduplicada. Ordenar alfabeticamente
       destruiria a unica informacao de prioridade que a frase carrega de graca
       -- quem escreve "skew no join" esta perguntando de skew.
    2. `derivados` sai ORDENADO, nao na ordem dos clusters. A ordem dos clusters
       e a do arquivo YAML, e ela mudaria a saida no dia em que alguem inserisse
       um cluster no meio -- um diff de vocabulario nao deve mexer na ordem de
       termo que nao mudou.
    3. Termo derivado que ja e literal NAO se repete. Repetido, ele contaria
       duas vezes no escore de dominio, e um cluster que ecoa o proprio gatilho
       (todos ecoam, de proposito) daria bonus a quem so casou a palavra
       original.

    Token de UM caractere e descartado junto com as stopwords: no FTS ele casa
    em quantidade de simbolo que nenhum peso recupera depois, e nenhuma palavra
    de dominio deste vocabulario tem uma letra so.
    """
    vocabulario = carregar_dicionario(dicionario)

    literais: list[str] = []
    vistos: set[str] = set()
    clusters: list[str] = []
    derivados: set[str] = set()

    for token in _tokens(tarefa):
        if len(token) < 2 or token in vocabulario.stopwords:
            continue
        if token not in vistos:
            vistos.add(token)
            literais.append(token)
        disparado = vocabulario.gatilhos.get(token)
        if disparado is not None:
            identificador, termos = disparado
            if identificador not in clusters:
                clusters.append(identificador)
            derivados.update(_normalizar(t) for t in termos)

    return Expansao(
        literais=tuple(literais),
        derivados=tuple(sorted(derivados - vistos)),
        clusters=tuple(clusters),
        versao=vocabulario.versao,
    )


@dataclass(frozen=True)
class Escore:
    """Os oito componentes da secao 49, cada um com seu valor, mais o total.

    A quebra por componente e campo e nao calculo interno porque ela e o que
    torna a ordem AUDITAVEL: sem ela, "por que este simbolo veio na frente" so
    tem resposta relendo o codigo do escore, e a resposta muda quando o codigo
    muda. Com ela, a resposta esta na saida.
    """

    exact_name: int
    qualified_name: int
    fts: int
    path: int
    graph: int
    domain: int
    entrypoint: int
    lineage: int

    @property
    def total(self) -> int:
        return (
            self.exact_name
            + self.qualified_name
            + self.fts
            + self.path
            + self.graph
            + self.domain
            + self.entrypoint
            + self.lineage
        )


def _segmentos_do_caminho(caminho: str) -> set[str]:
    """As palavras de `caminho`, para casar termo contra diretorio e arquivo.

    `sparkforge/codeintel/search.py` vira {sparkforge, codeintel, search, py}.
    Quebrar em `_` tambem: `latest_per_key.py` tem que casar o termo `latest`,
    senao o componente de caminho so serviria para nome de arquivo de uma
    palavra so.
    """
    return set(_tokens(caminho))


def escore(
    achado: Achado,
    expansao: Expansao,
    *,
    posicao_fts: int = 0,
    profundidade_no_grafo: int | None = None,
) -> Escore:
    """O escore composto de `achado` para `expansao`.

    `posicao_fts` e a posicao (base zero) em que a busca devolveu este achado --
    `buscar` ja ordena por `rank`, entao a posicao E a relevancia do FTS, e
    reabrir a conexao para pedir o `rank` numerico de novo custaria uma consulta
    por candidato para reconstruir uma ordem que ja veio pronta. Quando o mesmo
    no aparece na busca de mais de um termo, quem chama passa a MENOR posicao.

    `profundidade_no_grafo` e `None` quando o no nao foi alcancado pela
    travessia, e nao zero: zero e a ancora, o no mais proximo que existe.
    Confundir os dois daria peso maximo de proximidade a todo candidato que o
    grafo nunca viu.

    Nao abre banco. O modulo inteiro e funcao pura sobre o que ja foi lido, e e
    isso que deixa o escore ser testado sem indice e mutado sem fixture.
    """
    literais = set(expansao.literais)
    nome = _normalizar(achado.name)
    qualificado = set(_tokens(achado.qualified_name))
    caminho = _segmentos_do_caminho(achado.path)

    exact = PESO_EXACT_NAME if nome in literais else 0
    qualificado_bate = PESO_QUALIFIED_NAME if literais & qualificado else 0
    relevancia_fts = max(0, PESO_FTS_TOPO - max(0, posicao_fts))
    relevancia_caminho = PESO_PATH if literais & caminho else 0

    if profundidade_no_grafo is None:
        proximidade = 0
    else:
        salto = max(0, profundidade_no_grafo)
        proximidade = max(0, PESO_GRAFO_ANCORA - PESO_GRAFO_POR_SALTO * salto)

    derivados = set(expansao.derivados)
    batidas = len(derivados & (qualificado | caminho | {nome}))
    dominio = min(batidas, DOMINIO_MAXIMO_DE_TERMOS) * PESO_DOMINIO_POR_TERMO

    return Escore(
        exact_name=exact,
        qualified_name=qualificado_bate,
        fts=relevancia_fts,
        path=relevancia_caminho,
        graph=proximidade,
        domain=dominio,
        entrypoint=PESO_ENTRYPOINT,
        lineage=PESO_LINEAGE,
    )


def chave_de_ordem(par: tuple[Achado, Escore]) -> tuple[int, str, int, str]:
    """A ordem total do ranking, decidida num lugar so.

    Escore DECRESCENTE primeiro (por isso o sinal), e depois `path`,
    `start_line` e `node_id` -- o mesmo desempate de `graph._chave_de_ordem` e
    de `search._SQL_BUSCA`, e pelo mesmo motivo: escore sozinho nao ordena.
    Simbolos com o mesmo nome em arquivos diferentes empatam em TODOS os
    componentes, e sem desempate a ordem passa a ser a que o `sort` recebeu, que
    e a que o SQLite achou mais barata. Um teste de determinismo sobre isso
    falharia de forma INTERMITENTE, que e pior que falhar sempre.

    Os tres campos do desempate sao necessarios juntos, e nao por simetria: dois
    simbolos podem partilhar `path` (funcao aninhada e a funcao que a contem
    estao no mesmo arquivo), e `path` mais `start_line` ainda empataria no dia
    em que o extrator emitisse dois nos na mesma linha.
    """
    achado, pontos = par
    return (-pontos.total, achado.path, achado.start_line, achado.node_id)


def ordenar(pontuados: list[tuple[Achado, Escore]]) -> list[tuple[Achado, Escore]]:
    """`pontuados` em ordem estavel de relevancia.

    `sorted` e nao `list.sort` para nao mutar a lista de quem chama: o pacote de
    contexto monta a pontuacao uma vez e ordena mais de uma, e uma ordenacao no
    lugar faria a segunda chamada operar sobre saida da primeira.
    """
    return sorted(pontuados, key=chave_de_ordem)


__all__ = [
    "DICIONARIO_PADRAO",
    "Dicionario",
    "Escore",
    "Expansao",
    "carregar_dicionario",
    "chave_de_ordem",
    "escore",
    "expandir",
    "ordenar",
]
