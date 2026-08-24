"""Teto de saida em BYTES, alocacao por categoria e ordem declarada de reducao.

Secoes 51 a 54 da SPEC. As tres coisas que este modulo decide -- quanto cabe,
como o espaco se reparte e o que morre primeiro quando nao cabe -- ficam juntas
porque a terceira so faz sentido contra as duas primeiras.

POR QUE O TETO E EM BYTES, E O TOKEN E SO REPORTADO
----------------------------------------------------
A secao 51 escreve o teto em token. Aqui ele e aplicado em BYTES, e a diferenca
e deliberada.

Token nao e mensuravel offline. A secao 52 proibe tokenizer que baixe modelo, e
com razao -- baixar tokenizer quebra o "offline" inteiro da secao 7. O que sobra
e ESTIMATIVA, e este repositorio ja tem quatro delas: `agents/budget.py` usa
`(len+3)//4`, `context/funnel.py` usa `len//4`, e `providers/mock.py` usa
`len//4` duas vezes. Elas divergem no arredondamento -- para uma string de 5
caracteres a primeira devolve 2 e a segunda 1 -- e nenhuma conta bytes UTF-8, o
que faz as tres subestimarem qualquer texto acentuado, que e todo texto deste
projeto.

Um teto aplicado sobre estimativa e um teto que nao segura: ele para de segurar
no dia em que a estimativa erra para menos, e ninguem descobre porque nada
compara com a verdade. Byte de UTF-8 e EXATO, `len(payload)` nao tem
arredondamento, e o mesmo numero sai igual em qualquer maquina e em qualquer
versao de Python. O teto e nele.

`estimated_tokens` continua na saida porque a secao 52 exige o campo com esse
nome -- e com esse nome, nunca `exact_tokens`. Ele e INFORMATIVO. O que recusa
saida grande demais e `TETO_DURO_BYTES`.

O NUMERO DE BYTES VEM DA PROPRIA SPEC
--------------------------------------
A secao 52 da a formula do estimador conservador:

    estimate = max(ceil(utf8_bytes / 3), ceil(lexical_units * 1.2))

O ramo de bytes diz que a SPEC considera 3 bytes por token o limite conservador.
Os tetos em byte deste modulo sao os tetos em token da secao 51 multiplicados
por 3 -- nao um numero inventado ao lado da SPEC, mas o numero da SPEC lido pela
razao que a propria SPEC declara. Se o teto em token mudar, estes mudam junto,
e a multiplicacao esta escrita na expressao para que isso seja visivel.

POR QUE ESTE MODULO NAO REUSA `agents/budget.estimate_tokens`
--------------------------------------------------------------
Porque a unidade e outra e o papel e outro: la a estimativa DECIDE o corte, aqui
o byte decide e a estimativa acompanha. Trocar `estimate_tokens` pela formula da
secao 52 mudaria o resultado de `select_context` para toda memoria de agente
deste repositorio -- registros diferentes seriam escolhidos, com o mesmo
orcamento. Isso e mudanca de comportamento fora desta tarefa, e mudanca de
comportamento em silencio e o que a regra de preservar semantica recusa. A
consolidacao dos quatro estimadores continua devida, com esse custo medido e
declarado, e nao acontece de carona aqui.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

# Fator da secao 52: o ramo conservador do estimador e `utf8_bytes / 3`. Os
# tetos em byte sao os tetos em token da secao 51 por este fator, e a conta fica
# escrita para que a origem de cada numero seja lida, nao decorada.
BYTES_POR_TOKEN = 3

TETO_PADRAO_TOKENS = 1800
TETO_MINIMO_TOKENS = 256
TETO_MAXIMO_TOKENS = 8192
TETO_DURO_TOKENS = 12288

ORCAMENTO_PADRAO_BYTES = TETO_PADRAO_TOKENS * BYTES_POR_TOKEN
ORCAMENTO_MINIMO_BYTES = TETO_MINIMO_TOKENS * BYTES_POR_TOKEN
ORCAMENTO_MAXIMO_BYTES = TETO_MAXIMO_TOKENS * BYTES_POR_TOKEN
TETO_DURO_BYTES = TETO_DURO_TOKENS * BYTES_POR_TOKEN

# Secao 53, em pontos percentuais inteiros. A ordem das chaves E a ordem em que
# a sobra da divisao e distribuida -- ver `alocar`.
ALOCACAO_PADRAO: tuple[tuple[str, int], ...] = (
    ("task", 5),
    ("entry_points", 10),
    ("symbols", 15),
    ("relationships", 15),
    ("lineage", 15),
    ("snippets", 30),
    ("rules", 5),
    ("provenance", 5),
)

# Secao 54, na ordem exata em que a SPEC escreve. Tupla e nao lista porque a
# ordem E a politica: uma lista de modulo pode ser reordenada por qualquer
# chamador em tempo de execucao, e a politica de reducao passaria a depender de
# quem importou primeiro.
ORDEM_DE_REDUCAO: tuple[str, ...] = (
    "comments",
    "docstrings",
    "low_score_nodes",
    "low_score_edges",
    "snippet_context_lines",
    "graph_depth",
    "secondary_lineage",
)

# Secao 54, a outra metade: o que nao pode cair ANTES de tudo acima. Nao e "nao
# pode cair nunca" -- e "nao pode cair antes", e a diferenca aparece em
# `aplicar_reducao`, que so toca nestes quando a ordem inteira ja foi gasta.
NUNCA_REDUZIR_PRIMEIRO: frozenset[str] = frozenset(
    {
        "entry_point_principal",
        "provenance",
        "unresolved_warning",
        "security_warnings",
    }
)


class OrcamentoImpossivel(ValueError):
    """O nucleo irredutivel ja passa do teto duro.

    Existe como excecao propria e nao como saida truncada porque a secao 51 diz
    que nenhuma saida pode passar do teto duro DELIBERADAMENTE, e a secao 54 diz
    que ponto de entrada, procedencia e aviso de seguranca nao caem. Quando as
    duas regras se cruzam nao ha saida valida, e devolver algo assim mesmo seria
    escolher qual das duas quebrar em silencio. Falhar fechado e a regra da
    INV-015.
    """


def serializar(pacote: Mapping[str, Any]) -> bytes:
    """`pacote` como os bytes que serao efetivamente entregues.

    A medicao tem que ser sobre a FORMA FINAL, nao sobre a soma dos pedacos: a
    pontuacao, as chaves, as virgulas e o escape de UTF-8 sao bytes que chegam
    ao consumidor, e um orcamento que contasse so o conteudo ficaria abaixo do
    teto e entregaria acima dele.

    `sort_keys=True` porque o mesmo pacote tem que dar os MESMOS bytes em duas
    execucoes -- sem isso o tamanho seria estavel mas a assinatura nao, e um
    teste que compare saida byte a byte falharia por ordem de chave. Separadores
    sem espaco porque espaco de indentacao e byte gasto que nao carrega
    informacao nenhuma. `ensure_ascii=False` porque escapar acento para `\\uXXXX`
    TRIPLICA o custo de cada caractere acentuado -- e a saida deste projeto e
    quase toda em portugues.
    """
    texto = json.dumps(pacote, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return texto.encode("utf-8")


def tamanho_em_bytes(pacote: Mapping[str, Any]) -> int:
    """Quantos bytes `pacote` ocupa entregue. E o numero que o teto compara."""
    return len(serializar(pacote))


def _unidades_lexicais(texto: str) -> int:
    """Quantas unidades lexicais `texto` tem, pelo criterio mais barato que ha.

    `split()` sem argumento, que quebra em qualquer espaco em branco. Nao e um
    tokenizador e nao pretende ser: a secao 52 usa este ramo como PISO
    conservador da estimativa, e um piso construido por um analisador
    sofisticado teria custo de CPU proporcional ao texto para melhorar um numero
    que o teto nem consulta.
    """
    return len(texto.split())


def estimar_tokens(valor: Any) -> int:
    """A estimativa conservadora da secao 52, em `estimated_tokens`.

    Formula literal da SPEC:

        max(ceil(utf8_bytes / 3), ceil(lexical_units * 1.2))

    Os dois ramos existem porque erram para lados opostos. Texto denso e sem
    espaco -- um `node_id` de 32 hex, um caminho longo -- tem muitos bytes e
    poucas unidades, e o ramo de bytes e quem o cobre. Texto com muitas palavras
    curtas tem poucos bytes por palavra, e o ramo lexical e quem o cobre. O
    `max` pega o pior dos dois, que e o que "conservador" quer dizer.

    O ramo lexical usa aritmetica inteira -- `-(-unidades * 12 // 10)` -- e nao
    `ceil(unidades * 1.2)`. A razao esta MEDIDA, e ela e mais fraca do que a
    intuicao sugere: para todo `n` de 1 a 3000000 as duas formas dao o MESMO
    numero. `1.2` nao e representavel em binario, mas o produto e a divisao
    ficam dentro da faixa em que `float` representa inteiro exatamente, e o
    `ceil` cai do lado certo. A primeira divergencia encontrada foi em
    `n = 2**53 + 1`, que e onde essa faixa acaba.

    Ou seja: a forma inteira NAO conserta um defeito que existe neste tamanho de
    pacote -- o teto duro sao 36864 bytes. Ela remove a PERGUNTA. A alternativa
    seria manter `1.2` e um comentario dizendo "e seguro ate 2**53", que e uma
    afirmacao que ninguem reverifica quando o teto muda. `test_o_ramo_lexical_
    usa_aritmetica_inteira` grava a medicao junto para que este paragrafo nao
    possa envelhecer calado.

    Valor que nao e texto e serializado antes, pelo mesmo `json.dumps` que
    `serializar` usa, para que estimar um pacote e medir um pacote falem da
    mesma sequencia de caracteres.
    """
    if isinstance(valor, str):
        texto = valor
    else:
        texto = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    bytes_utf8 = len(texto.encode("utf-8"))
    unidades = _unidades_lexicais(texto)
    return max(-(-bytes_utf8 // BYTES_POR_TOKEN), -(-unidades * 12 // 10))


def normalizar_orcamento(pedido: int | None) -> int:
    """`pedido` preso na faixa da secao 51, em bytes.

    `None` vira o padrao. Abaixo do minimo vira o minimo e acima do maximo vira
    o maximo, em vez de levantar: a secao 51 declara uma FAIXA, e faixa e
    contrato de saturacao, nao de recusa. Recusar 100 bytes obrigaria todo
    chamador a conhecer o minimo antes de pedir, e o unico efeito seria mover o
    mesmo `clamp` para dentro de cada chamador.

    O maximo da faixa e menor que `TETO_DURO_BYTES` de proposito: a faixa e o
    que se pode PEDIR, o teto duro e o que nao se pode passar nem por engano
    interno. Ter os dois iguais faria o teto duro nao ter o que impedir.
    """
    if pedido is None:
        return ORCAMENTO_PADRAO_BYTES
    return max(ORCAMENTO_MINIMO_BYTES, min(int(pedido), ORCAMENTO_MAXIMO_BYTES))


def alocar(
    orcamento_bytes: int,
    alocacao: tuple[tuple[str, int], ...] = ALOCACAO_PADRAO,
) -> dict[str, int]:
    """O orcamento repartido pelas categorias da secao 53, em bytes inteiros.

    Aritmetica INTEIRA, e a sobra distribuida na ordem declarada. Com float, os
    percentuais de 15% tres vezes sobre 5400 bytes dariam
    `809.9999999999999` uma vez e `810.0000000000001` noutra dependendo da ordem
    da soma, e a soma das partes deixaria de ser o todo por um byte que aparece
    e some. Com inteiro, `5400 * 15 // 100` e 810 sempre, e o que a divisao
    truncou volta explicitamente.

    A sobra vai para as PRIMEIRAS categorias da ordem declarada, e nao para a
    maior: as primeiras sao as que a secao 54 protege de reducao (tarefa, pontos
    de entrada), e dar a sobra a elas erra do lado de preservar o que nao pode
    cair.

    A soma das partes e EXATAMENTE `orcamento_bytes`, e
    `test_alocacao_soma_exatamente_o_orcamento` prende isso -- um byte perdido
    por categoria e oito bytes que ninguem usa, e a fatura aparece como saida
    que cabia e foi cortada.
    """
    if orcamento_bytes <= 0:
        return {nome: 0 for nome, _ in alocacao}
    partes = {nome: orcamento_bytes * peso // 100 for nome, peso in alocacao}
    sobra = orcamento_bytes - sum(partes.values())
    for nome, _ in alocacao:
        if sobra <= 0:
            break
        partes[nome] += 1
        sobra -= 1
    return partes


def cortar_por_bytes(
    itens: list[Any],
    limite_bytes: int,
    *,
    minimo: int = 0,
) -> list[Any]:
    """Os primeiros itens de `itens` que cabem em `limite_bytes`, em ordem.

    E o que faz a alocacao da secao 53 ter efeito em vez de ser tabela: sem um
    corte por categoria, `alocar` seria um dicionario que ninguem consulta e a
    unica coisa que limitaria o pacote seria a reducao da secao 54 -- que corta
    o pacote INTEIRO, sem respeitar que a secao 53 reserva 15% para relacoes e
    5% para procedencia. Uma categoria gulosa comeria a fatia das outras e a
    reducao chegaria tarde.

    O corte e por PREFIXO e nao por selecao: as listas que chegam aqui ja estao
    ordenadas por relevancia, e escolher itens de dentro para caber melhor -- o
    problema da mochila -- trocaria a ordem de relevancia por eficiencia de
    empacotamento. Um pacote que devolve o quinto simbolo e nao o segundo porque
    o segundo era grande e um pacote que mente sobre o ranking.

    `minimo` e quantos itens ficam ainda que nao caibam. E como o ponto de
    entrada principal da secao 54 sobrevive a uma fatia pequena demais: sem ele,
    um orcamento apertado devolveria `entry_points` vazio, e o pacote perderia
    justamente o item que a secao 54 diz que nao cai.

    O custo de cada item e medido com a virgula que o separa do proximo, porque
    e assim que ele chega ao JSON -- contar so o objeto subestimaria a lista em
    um byte por item, e a subestimativa cresce com o tamanho da lista.
    """
    if limite_bytes <= 0 and minimo <= 0:
        return []
    saida: list[Any] = []
    usado = 0
    for indice, item in enumerate(itens):
        custo = len(serializar({"i": item})) - len(serializar({"i": None})) + 1
        if indice < minimo:
            saida.append(item)
            usado += custo
            continue
        if usado + custo > limite_bytes:
            break
        saida.append(item)
        usado += custo
    return saida


def aplicar_reducao(
    pacote: dict[str, Any],
    teto_bytes: int,
    redutores: Mapping[str, Callable[[dict[str, Any]], bool]],
    ultimo_recurso: Callable[[dict[str, Any]], bool] | None = None,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """`pacote` reduzido ate caber em `teto_bytes`, na ordem da secao 54.

    Devolve o pacote e os passos que FORAM aplicados, nesta ordem. A lista de
    passos e retorno e nao log porque ela vira campo da saida: quem le um pacote
    encolhido precisa saber o que foi sacrificado, e "encolheu" sem dizer o que
    caiu e a forma de perda de evidencia que este projeto recusa.

    Cada redutor devolve `True` quando conseguiu tirar alguma coisa e `False`
    quando nao havia o que tirar. Um passo da `ORDEM_DE_REDUCAO` sem redutor
    registrado NAO e erro: e o caso de `comments` e `docstrings` num pacote que
    nao carrega corpo de codigo. Ele simplesmente nao aparece nos passos
    aplicados -- e a ausencia dele na lista e a prova de que nao havia o que
    reduzir ali, nao de que a ordem foi ignorada.

    O redutor e chamado EM LACO ate parar de render, e nao uma vez: "tirar os
    nos de menor escore" tira um por chamada, e uma unica passada por categoria
    faria a reducao desistir com o pacote ainda grande enquanto ainda havia nos
    de escore baixo para tirar.

    `ultimo_recurso` roda depois de a ordem inteira ser gasta, e e onde mora a
    unica concessao ao conjunto `NUNCA_REDUZIR_PRIMEIRO`: a secao 54 diz que
    esses itens nao caem ANTES, e depois de todo o resto a alternativa e
    `OrcamentoImpossivel`. Ele preserva o AVISO e larga o detalhe -- a lista de
    nao resolvidos vira contagem, o aviso continua.
    """
    passos: list[str] = []
    if tamanho_em_bytes(pacote) <= teto_bytes:
        return pacote, ()

    for passo in ORDEM_DE_REDUCAO:
        redutor = redutores.get(passo)
        if redutor is None:
            continue
        rendeu = False
        while tamanho_em_bytes(pacote) > teto_bytes and redutor(pacote):
            rendeu = True
        if rendeu:
            passos.append(passo)
        if tamanho_em_bytes(pacote) <= teto_bytes:
            return pacote, tuple(passos)

    if ultimo_recurso is not None:
        while tamanho_em_bytes(pacote) > teto_bytes and ultimo_recurso(pacote):
            if "ultimo_recurso" not in passos:
                passos.append("ultimo_recurso")

    if tamanho_em_bytes(pacote) > TETO_DURO_BYTES:
        raise OrcamentoImpossivel(
            f"nucleo irredutivel tem {tamanho_em_bytes(pacote)} bytes,"
            f" acima do teto duro de {TETO_DURO_BYTES}"
        )
    return pacote, tuple(passos)


__all__ = [
    "ALOCACAO_PADRAO",
    "BYTES_POR_TOKEN",
    "NUNCA_REDUZIR_PRIMEIRO",
    "ORCAMENTO_MAXIMO_BYTES",
    "ORCAMENTO_MINIMO_BYTES",
    "ORCAMENTO_PADRAO_BYTES",
    "ORDEM_DE_REDUCAO",
    "OrcamentoImpossivel",
    "TETO_DURO_BYTES",
    "TETO_DURO_TOKENS",
    "alocar",
    "aplicar_reducao",
    "cortar_por_bytes",
    "estimar_tokens",
    "normalizar_orcamento",
    "serializar",
    "tamanho_em_bytes",
]
