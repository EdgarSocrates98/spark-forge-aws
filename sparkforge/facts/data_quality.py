"""Extrator de Facts sobre VALIDACAO DE DADOS num modulo PySpark.

Modulo separado de `pyspark_ast.py` -- que ja tem 40 KB e 20 kinds -- porque
reconhecer validacao e responsabilidade propria, com frameworks proprios. O
custo aceito e caminhar a mesma AST duas vezes.

Este extrator DECIDE as correlacoes (posicao relativa ao write, persistencia do
alvo, numero de checks sobre o mesmo alvo) porque o motor de regras avalia um
fact por vez: `engine._condition_candidates` le o contexto de um unico fact e
`engine._absent_satisfied` compara so `kind`. E o mesmo padrao que `SF-EMR-008`
fixou na Fase 5b -- se a resposta depende de mais de uma propriedade, o extrator
decide e emite.

Nunca aplica limiar, nunca atribui severidade, nunca adivinha alvo: alvo nao
resolvido vira `dq.unresolved`, contado e nao presumido.

Tres formas sao reconhecidas, cada uma pela FORMA e nunca por lista de nomes: o
check artesanal (`df.filter(...).count()`), a `VerificationSuite` do PyDeequ
(cadeia que contem `onData` e termina em `run`) e a validacao do Great
Expectations (DataFrame sob a chave literal `"dataframe"` de `batch_parameters`,
inline ou um passo atras, no nome ligado dentro do mesmo escopo).
Todas passam pelo MESMO construtor -- `_check` -- e pelo mesmo indice por escopo:
o que muda entre elas nao e a correlacao, e o que o `.py` permite afirmar sobre a
varredura. Dai a assimetria deliberada de `shares_scan`, presente nos dois
primeiros e AUSENTE no terceiro.

PROPRIEDADE DO MODULO: nome nu nao identifica objeto, e os QUATRO atributos de
correlacao tratam isso, cada um do jeito que o seu erro pede.

- Entre escopos, nome igual nao e o mesmo objeto: o indice e por escopo
  (`_ScopeIndex`), e nunca por modulo.
- O que ENTRA no escopo por parametro tem historia que o indice nao viu.
  `target_persisted` OMITE a chave nesse caso, porque persistencia de um
  parametro mora no chamador.
- Dentro de um escopo, religar o nome (`vendas = carrega(...)`) troca o objeto
  sem trocar o nome, entao evidencia de um lado da religacao nao vale do outro.
  `position_vs_write` OMITE a chave -- a regra nao deve opinar sobre ordem que
  nao existe --, enquanto `target_persisted` e `action_after_check` emitem
  `false`: o objeto religado esta NESTE escopo, o indice ve tudo que ha para ver
  sobre ele, e omitir faria da religacao um jeito de sumir com a regra.

A escolha entre omitir e emitir `false` nao e estilo; e a direcao do erro, e ela
depende de sobre qual valor a regra dispara. `SF-DQ-003` dispara sobre
`target_persisted: FALSE` e sobre `action_after_check: TRUE`: os DOIS estao do
lado da acusacao, porque nos dois e o valor que a ignorancia produz que puxa o
gatilho. Emitir `false` na ignorancia sobre persistencia acusa exatamente como
emitir `true` na ignorancia sobre reuso.

Dai a diferenca no remedio de cada um, que nao e simetrica:

- `target_persisted` sob parametro: `false` e a ausencia NAO sao equivalentes --
  `false` dispara, a ausencia cala --, entao omitir e o unico jeito de nao
  acusar.
- `action_after_check`: `false` e a ausencia calam a regra IGUALMENTE, entao nao
  ha o que ganhar em omitir, e a chave fica sempre presente. O argumento "a
  ausencia calaria a regra" vale so para `target_persisted` sob religacao, onde
  calar seria errado.

`dq.enforcement` inverte essa direcao, e por isso as decisoes de borda dele
apontam para o outro lado. `SF-DQ-002` dispara sobre a AUSENCIA dele
(`absent: dq.enforcement` com `same_subject`), entao emitir um enforcement que
nao existe CALA a regra sobre validacao desprotegida -- subnotificacao --, e
deixar de emitir um que existe faz a regra ACUSAR codigo correto. Na duvida
entre reconhecer e nao reconhecer uma forma de consequencia, este kind
reconhece; o que ele nao faz e inventar consequencia onde nao ha nenhuma.

CONSEQUENCIA DISSO, e o unico ponto do modulo em que a politica acima e
contrariada de proposito: `_rebound_between` MUDA DE LADO conforme o kind que o
consome. Nos quatro atributos da Task 2 ele erra para o silencio -- omite uma
chave, ou emite `false`, e a regra deixa de opinar. Em `dq.enforcement` ele erra
para a ACUSACAO, porque descartar a leitura descarta o fact inteiro, e a
ausencia do fact E o gatilho de `SF-DQ-002`. O caso medido:

    try:
        ruins = vendas.filter(vendas.valor < 0).count()
    except Exception:
        ruins = 0
    if ruins > 0:
        raise ValueError(...)

O `ruins = 0` do `except` religa o nome entre o check e o `if`, a evidencia cai,
e sai enforcement NENHUM sobre um codigo que protege. A decisao e mantida --
sem seguir fluxo, o valor testado de fato pode nao ser o do check --, mas ela e
o preco medido, e nao um efeito colateral: quem mexer em `_rebound_between`
precisa saber que o mesmo predicado paga em moedas opostas nos dois lados.
"""
from __future__ import annotations

import ast
import hashlib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, NamedTuple

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "data_quality@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "dq.check",
        "dq.enforcement",
        "dq.unresolved",
        "dq.module_analyzed",
    }
)

# `count` sobre uma cadeia que passou por um destes e a forma artesanal: filtra
# o que viola a regra e conta o que sobrou.
_HANDMADE_GATES = frozenset({"filter", "where"})

# Metodos que constroem um DataFrame A PARTIR da raiz da cadeia. Se um deles
# aparece na cadeia, a raiz e a sessao (ou o reader), NAO o dado validado: em
# `spark.table("t").filter(...).count()` o alvo do check e um DataFrame anonimo,
# e `spark` seria um alvo adivinhado -- `SF-DQ-001` passaria a comparar a linha
# deste check com o write de qualquer outro dado que tambem saia de `spark`, e
# afirmaria "validou depois de publicar" sobre dados que nunca se tocaram. Por
# isso a cadeia que passa por aqui vira `dq.unresolved`, contada, e nunca um
# `dq.check` com alvo errado.
#
# A presenca e testada em QUALQUER posicao, nao so no primeiro elo: `option`,
# `schema` e `format` configuram o reader antes do terminal, entao
# `spark.read.option("mergeSchema", "true").parquet(p)` empurra o terminal para
# fora da posicao 0. Testar so o primeiro elo deixava passar exatamente a forma
# canonica de leitura Delta/Iceberg/JDBC em job Glue real.
#
# Superconjunto de `_READ_TERMINALS` (`pyspark_ast.py:55`): os oito nomes de la
# estao todos aqui, `format` inclusive -- ele sozinho nao produz DataFrame, mas
# a presenca dele ja prova que a raiz da cadeia e um reader. Os quatro a mais
# (`range`, `createDataFrame`, `text`, `jdbc`) sao fabricas de DataFrame a
# partir da sessao: `pyspark_ast` nao precisa delas para classificar leitura, e
# aqui elas produziriam o mesmo alvo adivinhado que as outras.
_SOURCE_TERMINALS = frozenset(
    {
        "table",
        "sql",
        "range",
        "createDataFrame",
        "parquet",
        "csv",
        "json",
        "orc",
        "text",
        "jdbc",
        "load",
        "format",
    }
)


# `df.write`, `df.writeTo(...)` e `df.writeStream` sao ATRIBUTOS, nao chamadas:
# o metodo que termina a escrita (`parquet`, `save`, `append`, `start`) varia e
# nao e o que identifica a publicacao.
_WRITE_ATTRS = frozenset({"write", "writeTo", "writeStream"})

# Chamadas que disparam trabalho sobre o alvo. `save`/`saveAsTable` aparecem
# depois de `.write` -- estao aqui para o caso de a cadeia ser quebrada em duas
# linhas (`w = df.write` / `w.save(p)`), onde o atributo e a chamada nao
# compartilham linha.
_ACTION_METHODS = frozenset({"count", "collect", "show", "foreach", "save", "saveAsTable"})

_PERSIST_METHODS = frozenset({"cache", "persist"})
_UNPERSIST_METHODS = frozenset({"unpersist"})

# A suite do PyDeequ e reconhecida pela FORMA -- cadeia que CONTEM `onData` e
# TERMINA em `run` --, nunca por casar a sequencia exata: a ordem e o numero de
# `addCheck` variam, e `useRepository`/`saveOrAppendResult` entram no meio
# (knowledge/dq/validation-frameworks.md, §2.1).
_SUITE_SOURCE = "onData"
_SUITE_TERMINAL = "run"

# Great Expectations 1.x nao expoe mais `SparkDFDataset`, e detectar por prefixo
# `expect_*` esta vetado (V-GE-1 e V-GE-2 da mesma pagina, §1.1): o prefixo
# sobrevive via `Validator.__getattr__` e o AST nao sabe se a variavel e um
# `Validator`. O que resta legivel no `.py` e o DataFrame sob CHAVE LITERAL no
# dict de `batch_parameters` -- e o receptor da chamada varia (`Checkpoint` e
# `ValidationDefinition` aceitam o mesmo argumento), por isso o `check_type`
# nomeia a EVIDENCIA lida e nao um objeto que o extrator nao enxerga.
_BATCH_PARAMETERS = "batch_parameters"
_DATAFRAME_KEY = "dataframe"

# Formas de aborto que contam como consequencia de um check. `raise` e `assert`
# sao SINTAXE -- nao ha lista de nomes a manter, e e por isso que a deteccao
# nao envelhece. Os `exit` sao chamada, e a lista e curta de proposito.
#
# `assert` CONTA, e isso e uma decisao contra a leitura ingenua da referencia da
# linguagem -- desvio D-5c-4, knowledge/dq/validation-frameworks.md §3.4. Sim,
# `-O`/`PYTHONOPTIMIZE` apagam todo `assert`; NENHUMA fonte da AWS mostra Glue ou
# EMR rodando o driver assim, e no Glue o unico caminho documentado de variavel
# de ambiente do driver (`--customer-driver-env-vars`) exige o prefixo
# `CUSTOMER_`, que impede definir `PYTHONOPTIMIZE`. Sem fonte, vale o
# comportamento padrao do interpretador: `__debug__` e True e o `assert` roda.
# Tratar `assert` como nao-consequencia -- ou como `dq.unresolved`, que o plano
# previa no outro ramo -- faria `SF-DQ-002` ACUSAR justamente quem protegeu o
# pipeline (veto V-AS-1). A ressalva, que e de ambiente e nao de codigo, vive na
# `explanation` da regra (veto V-AS-2). NAO "corrija" isto sem ler a §3.4.
_EXIT_CALLS = frozenset({("sys", "exit"), ("os", "_exit")})

# `from sys import exit` deixa a chamada nua. Reconhecer o nome nu arrisca casar
# uma funcao homonima do usuario; nao reconhecer arrisca acusar quem abortou de
# verdade. A segunda e a acusacao falsa, que e o pior modo de falha deste kind.
_BARE_EXIT = "exit"


class _ScopeIndex(NamedTuple):
    """O que o extrator enxerga de UM ESCOPO: eventos que datam um check, por
    variavel-alvo, mais os dois lookups que so fazem sentido dentro do escopo.

    O motor de regras nao correlaciona dois facts -- `engine._condition_candidates`
    avalia um fact por vez e `engine._absent_satisfied` compara so `kind` -- entao
    quem enxerga o codigo inteiro e quem responde. Este indice e o que o extrator
    enxerga e o catalogo nao enxergaria.

    O indice e por escopo, e nao por modulo, porque nome nu nao identifica objeto
    entre escopos: `def a(vendas)` e `def b(vendas)` recebem dois DataFrames
    diferentes, e datar o check de `b` contra o write de `a` seria a mesma
    acusacao falsa que `_SOURCE_TERMINALS` evita do lado da cadeia.

    LIMITE conhecido: a separacao vale para `FunctionDef`/`AsyncFunctionDef`.
    `lambda` e corpo de `class` continuam no escopo que os contem, e um
    parametro de lambda homonimo ao alvo ainda colide -- forma rara, registrada
    e nao corrigida. O preco inverso tambem existe: funcao que le um DataFrame
    global perde a correlacao com o write feito no modulo, e sai
    `no_write_in_module`. E subnotificacao, nao acusacao.
    """

    writes: dict[str, set[int]]
    persists: dict[str, list[tuple[tuple[int, int], bool]]]
    actions: dict[str, set[int]]
    rebinds: dict[str, set[int]]
    # Dicts literais ligados a um nome, para seguir `batch_parameters=params` UM
    # passo. Fora do escopo, seguir o nome seria a mesma colisao de homonimos que
    # o resto do indice recusa.
    dicts: dict[str, list[tuple[int, ast.Dict]]]
    # `id()` dos nos que sao o RECEPTOR de outra chamada da mesma cadeia. Quem
    # responde por uma cadeia e o no mais externo; sem isso,
    # `VerificationSuite(s).onData(d).addCheck(c)` emitiria um fact por elo.
    chained: frozenset[ast.AST]
    # Nomes que ENTRAM no escopo pela assinatura. Um parametro e, por
    # construcao, um objeto cuja historia comecou fora daqui: o que aconteceu
    # com ele antes da chamada e invisivel para este indice, e afirmar ausencia
    # de evidencia como evidencia de ausencia seria acusar o chamador pelo que
    # ele fez certo. Vazio no escopo do modulo.
    params: frozenset[str]


def _subject(path: str, line: int = 0, col: int = 0) -> dict[str, Any]:
    """Ancora de um fact deste modulo.

    `col` e PREENCHIDO, e nao fixo em zero. `Fact.id` e sha de
    `kind + subject + measures` com `attrs` de fora (`findings/models.py`), entao
    dois checks na mesma linha -- `a = df.filter(...).count(); b = ...` -- saiam
    com a MESMA identidade enquanto a coluna era zero, e o `fact_id` que um
    Finding cita deixava de identificar evidencia.

    Segue a forma de `pyspark_ast.py:135`, o extrator irmao sobre o mesmo
    artefato, que ja usa `col_offset`. Os demais extratores fixam zero porque
    ancoram em artefatos sem coluna util (JSON de event log, HCL, resposta de
    API), nao por escolha de arquitetura.

    Nao afeta `same_subject`: `engine._subject_group_key` monta a chave com
    `file:line` quando nao ha `symbol`, e ignora `col`. Enforcement e check
    continuam no mesmo grupo -- ha teste que prova.
    """
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": col,
        "symbol": "",
        "snippet": "",
    }


def _unresolved(
    path: str, line: int, col: int, reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="dq.unresolved",
        subject=_subject(path, line, col),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _chain_root(node: ast.AST) -> tuple[str | None, list[str]]:
    """(nome da variavel raiz, metodos chamados na cadeia, da raiz para fora)."""
    methods: list[str] = []
    current = node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        methods.append(current.func.attr)
        current = current.func.value
    while isinstance(current, ast.Attribute):
        current = current.value
    methods.reverse()
    if isinstance(current, ast.Name):
        return current.id, methods
    return None, methods


def _chain_target(node: ast.AST) -> str | None:
    """Variavel-alvo da cadeia, ou None quando a raiz nao e o alvo.

    Reusa `_SOURCE_TERMINALS` pelo mesmo motivo que `_handmade_check`: a cadeia
    que passa por um reader tem raiz que e a sessao, e registrar a sessao como
    alvo faria dois dados que nunca se tocaram compartilharem a mesma linha de
    write -- um check seria datado contra a publicacao de outro dado.
    """
    root, methods = _chain_root(node)
    if root is None or any(m in _SOURCE_TERMINALS for m in methods):
        return None
    return root


def _parameter_names(root: ast.AST) -> frozenset[str]:
    """Nomes ligados pela assinatura, quando a raiz do escopo e uma funcao.

    Todas as formas contam -- posicionais, `*args`, keyword-only e `**kwargs` --
    porque a pergunta nao e como o valor chega, e sim de ONDE ele vem: de fora
    deste escopo, com uma historia que este indice nao viu.
    """
    if not isinstance(root, ast.FunctionDef | ast.AsyncFunctionDef):
        return frozenset()
    args = root.args
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg is not None:
        named.append(args.vararg)
    if args.kwarg is not None:
        named.append(args.kwarg)
    return frozenset(arg.arg for arg in named)


def _scopes(tree: ast.AST) -> list[tuple[ast.AST, list[ast.AST]]]:
    """A raiz e os nos de cada escopo de nome, cada escopo num par proprio.

    Corpo do modulo e cada `FunctionDef`/`AsyncFunctionDef` sao escopos
    separados: dentro de um escopo, o mesmo nome e o mesmo objeto (a menos de
    rebind, que `_rebind_lines` apura); entre escopos, nao e.

    A RAIZ acompanha os nos porque a assinatura da funcao nao esta no corpo dela:
    e o unico lugar onde se le quais nomes chegaram de fora, e sem isso o indice
    nao consegue distinguir "nao ha persistencia" de "a persistencia esta num
    escopo que eu nao vejo".
    """
    scopes: list[tuple[ast.AST, list[ast.AST]]] = []
    pending: list[ast.AST] = [tree]
    while pending:
        root = pending.pop()
        own: list[ast.AST] = []
        stack = list(ast.iter_child_nodes(root))
        while stack:
            node = stack.pop()
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                pending.append(node)
                continue
            own.append(node)
            stack.extend(ast.iter_child_nodes(node))
        scopes.append((root, own))
    return scopes


def _lines_by_target(
    nodes: list[ast.AST], attrs: frozenset[str], methods: frozenset[str]
) -> dict[str, set[int]]:
    """Linhas em que cada variavel-alvo aparece na raiz de `df.<attr>` ou de
    `df....<method>()`.

    Guarda o CONJUNTO de linhas, nao a primeira encontrada: a travessia nao e
    por linha -- um write dentro de um laco e visitado depois de um write no
    corpo do modulo -- e "a primeira linha vista" nao e a primeira linha do
    arquivo. Quem consome escolhe o extremo que lhe interessa.

    LIMITE conhecido: alias nao e seguido. `df2 = vendas` seguido de
    `df2.write...` deixa o check sobre `vendas` como `no_write_in_module`. E
    subnotificacao -- o campo diz menos do que o arquivo contem -- e nunca
    acusacao falsa, que e o erro que esta fase recusa.
    """
    found: dict[str, set[int]] = {}
    for node in nodes:
        if isinstance(node, ast.Attribute) and node.attr in attrs:
            chain: ast.AST = node.value
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in methods
        ):
            chain = node
        else:
            continue
        target = _chain_target(chain)
        if target is not None:
            found.setdefault(target, set()).add(node.lineno)
    return found


def _persist_events(nodes: list[ast.AST]) -> dict[str, list[tuple[tuple[int, int], bool]]]:
    """Eventos de persistencia por alvo, ordenados por posicao no arquivo.

    Guarda `cache`/`persist` E `unpersist`, porque `target_persisted` afirma
    ESTADO e nao ocorrencia. A posicao e (linha, coluna) para que dois eventos
    na mesma linha (`vendas.cache(); vendas.unpersist()`) ainda se ordenem.
    """
    events: dict[str, list[tuple[tuple[int, int], bool]]] = {}
    for node in nodes:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        if method not in _PERSIST_METHODS and method not in _UNPERSIST_METHODS:
            continue
        target = _chain_target(node)
        if target is not None:
            events.setdefault(target, []).append(
                ((node.lineno, node.col_offset), method in _PERSIST_METHODS)
            )
    for sequence in events.values():
        sequence.sort()
    return events


def _rebind_lines(nodes: list[ast.AST]) -> dict[str, set[int]]:
    """Linhas em que cada nome e ligado a outro objeto.

    Todo `ast.Name` em contexto `Store` conta, o que cobre de uma vez `Assign`,
    `AnnAssign`, `AugAssign`, alvo de `for` e `with ... as` -- e tambem alvo de
    comprehension e walrus, que ligam do mesmo jeito.
    """
    lines: dict[str, set[int]] = {}
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            lines.setdefault(node.id, set()).add(node.lineno)
    return lines


def _dict_bindings(nodes: list[ast.AST]) -> dict[str, list[tuple[int, ast.Dict]]]:
    """Dicts LITERAIS ligados a cada nome, ordenados por linha.

    Existe para seguir `batch_parameters=params` um passo: a forma que a
    documentacao do Great Expectations usa monta o dict numa linha e o passa por
    nome na seguinte. Um passo so, sem analise de fluxo -- nome ligado a chamada
    de funcao nao entra aqui, e quem consome trata a ausencia como "nao da para
    ler", nunca como alvo adivinhado.
    """
    found: dict[str, list[tuple[int, ast.Dict]]] = {}
    for node in nodes:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Dict):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                found.setdefault(target.id, []).append((node.lineno, node.value))
    for sequence in found.values():
        sequence.sort(key=lambda binding: binding[0])
    return found


def _chained_receivers(nodes: list[ast.AST]) -> frozenset[ast.AST]:
    """Todo no que e o receptor de uma chamada de metodo do escopo.

    Um no que esta nesta colecao e um ELO INTERNO de uma cadeia -- alguem chama
    um metodo sobre ele --, e quem responde pela cadeia inteira e o no mais
    externo, que nao esta aqui. Sem esta pergunta,
    `VerificationSuite(s).onData(d).addCheck(c)` produziria um fact por elo, ja
    que `onData` esta nos `methods` de cada um deles.

    O conjunto guarda os NOS, nao `id(no)`. No de AST e hashavel por identidade,
    que e exatamente a comparacao desejada, e guardar o objeto elimina a
    condicao que tornaria `id()` valido -- alguem manter o indice vivo depois de
    a arvore morrer reaproveitaria enderecos e casaria nos errados em silencio.
    """
    return frozenset(
        node.func.value
        for node in nodes
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    )


def _scope_index(root: ast.AST, nodes: list[ast.AST]) -> _ScopeIndex:
    return _ScopeIndex(
        writes=_lines_by_target(nodes, _WRITE_ATTRS, frozenset()),
        persists=_persist_events(nodes),
        # `.write` tambem e action: e o que dispara o trabalho de publicar.
        actions=_lines_by_target(nodes, _WRITE_ATTRS, _ACTION_METHODS),
        rebinds=_rebind_lines(nodes),
        dicts=_dict_bindings(nodes),
        chained=_chained_receivers(nodes),
        params=_parameter_names(root),
    )


def _rebound_between(target: str, low: int, high: int, index: _ScopeIndex) -> bool:
    """Ha religacao do nome ESTRITAMENTE entre duas linhas do mesmo escopo.

    Os tres atributos que correlacionam por nome fazem esta mesma pergunta, e o
    que muda entre eles nao e o predicado: e o que cada um FAZ com a resposta --
    omitir a chave, emitir `false`, ou descartar uma candidata. Manter o
    predicado em tres formas distintas garantiria divergencia na proxima
    mudanca, e divergencia aqui e falso positivo ou falso negativo, nunca so
    inconsistencia de estilo.
    """
    return any(low < rebind < high for rebind in index.rebinds.get(target, ()))


def _position_vs_write(target: str, line: int, index: _ScopeIndex) -> str | None:
    """Tres valores, nunca um booleano -- ou nenhum valor, quando nao da para saber.

    `no_write_in_module` e o modulo que valida e nao escreve -- uma biblioteca de
    validacao, um job de auditoria. Achatar isso em `before_write` afirmaria uma
    ordem que o arquivo nao contem.

    `None` (chave OMITIDA, nunca um quarto valor) e o nome religado entre o check
    e o write: em `vendas.write...` / `vendas = carrega(...)` / check, o alvo
    validado e um DataFrame que nunca foi escrito, e qualquer dos tres valores
    seria mentira. Chave ausente e a forma de dizer "nao sei" --
    `engine._where_matches` reprova caminho ausente e a regra nao avalia este
    check --, o mesmo mecanismo que o desvio D-5c-3 fixou para `shares_scan`.

    LIMITE conhecido: write e check na MESMA linha (`;`) caem em `before_write`,
    porque a comparacao e estrita e `lineno` nao tem sub-linha. Raro e de baixo
    impacto.
    """
    lines = index.writes.get(target)
    if not lines:
        return "no_write_in_module"
    write_line = min(lines)
    low, high = sorted((line, write_line))
    if _rebound_between(target, low, high, index):
        return None
    return "after_write" if line > write_line else "before_write"


def _target_persisted(target: str, line: int, index: _ScopeIndex) -> bool | None:
    """Estado no momento do check: o ULTIMO evento antes dele decide.

    `vendas.cache()` seguido de `vendas.unpersist()` deixa o alvo NAO persistido
    quando o check chega -- o campo afirma estado, nao que um `cache()` existiu
    em algum lugar do arquivo.

    Religar o nome entre o ultimo evento e o check tambem derruba a evidencia: em
    `vendas.cache()` / `vendas = carrega(...)` / check, o DataFrame validado nao e
    o que foi persistido. Aqui `false`, e nao a omissao: o objeto que o check
    valida esta neste escopo, foi religado aqui, e nao ha nada sobre ele que este
    indice deixe de ver. Omitir faria da religacao um jeito de sumir com a regra.

    `None` (chave OMITIDA) e o alvo que chega por PARAMETRO sem nenhum evento de
    persistencia no proprio escopo. A forma canonica de biblioteca Glue e validar
    num helper e cachear no chamador:

        def valida(vendas):
            ruins = vendas.filter(...).count()   # persistencia? nao da para saber
        def main(spark):
            vendas = spark.read.parquet(...)
            vendas.cache()                       # ela esta AQUI, noutro escopo
            valida(vendas)

    Persistencia de um parametro e, por construcao, evidencia que vive fora do
    escopo, e `false` afirmaria o que o indice nao sabe -- `SF-DQ-003` dispara
    sobre `target_persisted: false` e acusaria um DataFrame persistido. A chave
    ausente e reprovada por `engine._where_matches`, entao a regra nao avalia
    esses checks.

    O PRECO, aceito: isto cala `SF-DQ-003` para todo helper de validacao,
    inclusive os genuinamente nao persistidos. Subnotificacao e o lado aceito;
    a alternativa era acusar a forma canonica de biblioteca Glue.

    A excecao e ter evidencia LOCAL: `cache`/`persist`/`unpersist` sobre o
    parametro dentro da propria funcao prova o estado sem depender do chamador, e
    ai a chave sai normalmente -- inclusive `false`, quando o evento local e um
    `unpersist`.

    LIMITE conhecido: religar um parametro antes do check (`vendas = carrega(...)`
    na primeira linha do helper) deixa o nome apontando para um DataFrame local, e
    ainda assim a chave e omitida. Erra para menos, que e o lado aceito.
    """
    events = [event for event in index.persists.get(target, ()) if event[0][0] < line]
    if not events:
        return None if target in index.params else False
    (last_line, _), persisted = events[-1]
    if not persisted:
        return False
    return not _rebound_between(target, last_line, line, index)


def _action_after_check(target: str, line: int, index: _ScopeIndex) -> bool:
    """Ha action sobre o alvo depois do check, e sobre o MESMO objeto.

    Estritamente posterior: a linha do proprio check tem a action que o define
    -- o `count()` -- e o check nao e action depois de si.

    Religar o nome entre o check e uma action candidata invalida AQUELA action,
    nao o intervalo inteiro: se ha action em 3, religacao em 5 e action em 7, com
    o check em 2, a de 3 continua valendo e o atributo e `true`. Sao N candidatas,
    e cada uma responde por si.

    O erro deste atributo cai do lado da ACUSACAO, e ele divide esse lado com
    `target_persisted`: `SF-DQ-003` dispara sobre `action_after_check: true` E
    sobre `target_persisted: false`, entao afirmar reuso de um nome que ja aponta
    para outro objeto acusa um check cujo DataFrame nunca foi reusado, do mesmo
    jeito que afirmar `false` sobre persistencia que o indice nao viu.

    A chave fica sempre presente, e o motivo aqui NAO e o de `_target_persisted`:
    para este atributo `false` e a ausencia calam a regra igualmente, entao nao ha
    o que ganhar em omitir. Parametro tambem nao muda nada -- a action posterior
    esta dentro do escopo e e observada de fato; so a persistencia vem de fora.

    LIMITE conhecido: um check IRMAO sobre o mesmo alvo conta como action
    posterior, e e verdade -- sem cache, os dois recomputam o lineage --, mas
    quem ler o campo como "o dado e reusado" se engana: o reuso aqui e recomputo,
    nao releitura de algo materializado.
    """
    return any(
        action > line and not _rebound_between(target, line, action, index)
        for action in index.actions.get(target, ())
    )


def _check(
    path: str,
    node: ast.Call,
    index: _ScopeIndex,
    provenance: dict[str, Any],
    *,
    framework: str,
    check_type: str,
    target: str,
    **extra: Any,
) -> Fact:
    """Um `dq.check` de qualquer framework, com os atributos de correlacao.

    Caminho UNICO de proposito. Os quatro atributos correlacionam por nome nu, e
    nome nu nao identifica objeto: escopo e religacao ja estao tratados aqui
    dentro, cada um do jeito que o seu erro pede. Um segundo caminho por
    framework divergiria na proxima mudanca, e divergencia aqui e falso positivo
    ou falso negativo -- e o mesmo argumento que reuniu `_rebound_between`.

    O que muda de framework para framework e o que o `.py` PERMITE afirmar, e
    isso entra por `extra`: `shares_scan` para os dois frameworks cuja passada o
    codigo revela, e chave nenhuma para o Great Expectations, que nao a revela.

    Recebe o NO, e nao `line`: linha e coluna da ancora saem do mesmo lugar, e
    nao ha como um chamador passar uma sem a outra.
    """
    line = node.lineno
    attrs: dict[str, Any] = {
        "framework": framework,
        "check_type": check_type,
        "target": target,
    }
    # Inserida ANTES de `action_after_check` mesmo sendo condicional: a ordem das
    # chaves e o que o golden compara byte a byte, e mover uma chave produziria
    # diff em sete fixtures sem que um unico valor mudasse -- churn que esconde a
    # proxima mudanca de verdade.
    persisted = _target_persisted(target, line, index)
    if persisted is not None:
        attrs["target_persisted"] = persisted
    # A assimetria e deliberada e medida: `action_after_check` continua valendo
    # para parametro, porque a action posterior esta DENTRO do escopo e e
    # observada de fato. So a persistencia vem de fora.
    attrs["action_after_check"] = _action_after_check(target, line, index)
    attrs.update(extra)
    position = _position_vs_write(target, line, index)
    if position is not None:
        attrs["position_vs_write"] = position
    return Fact(
        kind="dq.check",
        subject=_subject(path, line, node.col_offset),
        measures={"line": line},
        attrs=attrs,
        provenance=provenance,
    )


def _handmade_check(
    node: ast.Call, path: str, index: _ScopeIndex, provenance: dict[str, Any]
) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "count":
        return None
    target, methods = _chain_root(node)
    if not any(m in _HANDMADE_GATES for m in methods):
        return None
    if target is None or any(m in _SOURCE_TERMINALS for m in methods):
        return _unresolved(
            path,
            node.lineno,
            node.col_offset,
            "unresolved_target",
            provenance,
            check_type="count_of_violations",
        )
    return _check(
        path,
        node,
        index,
        provenance,
        framework="handmade",
        check_type="count_of_violations",
        target=target,
        # Todo check artesanal paga varredura propria: cada `count()` e uma
        # passada sobre o alvo, sem compartilhamento com os outros checks do
        # modulo. So a `VerificationSuite` do Deequ agrupa agregacoes
        # (knowledge/dq/validation-frameworks.md, §2.3).
        shares_scan=False,
    )


def _on_data_argument(node: ast.Call) -> ast.expr | None:
    """Primeiro argumento posicional do `onData` da cadeia, sem interpretar.

    O alvo do PyDeequ NAO e a raiz da cadeia: `_chain_root` sobre
    `VerificationSuite(spark).onData(df)...run()` devolve raiz `None`, porque a
    raiz e um `ast.Call` -- e, se devolvesse nome, seria `VerificationSuite` ou
    `spark`, o alvo adivinhado que `_SOURCE_TERMINALS` recusa do outro lado.
    Quem nomeia o dado validado e o argumento de `onData`.
    """
    current: ast.AST = node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        if current.func.attr == _SUITE_SOURCE and current.args:
            return current.args[0]
        current = current.func.value
    return None


def _pydeequ_check(
    node: ast.Call, path: str, index: _ScopeIndex, provenance: dict[str, Any]
) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node in index.chained:
        return None
    _, methods = _chain_root(node)
    if _SUITE_SOURCE not in methods:
        return None
    if _SUITE_TERMINAL not in methods:
        # PONTO CEGO, e nao achado -- a diferenca importa e quem vier depois vai
        # querer transformar isto em regra. A cadeia pode ser guardada numa
        # variavel e executada em outro lugar (`s = VerificationSuite(...)
        # .onData(df)` / `s.run()`, ou passada a outra funcao), e o extrator nao
        # segue o objeto: a afirmacao honesta e "ha uma suite aqui cuja execucao
        # eu nao enxergo", nunca "esta suite nao roda". Suite declarada e nunca
        # executada e um defeito real, mas provar isso exige seguir o valor, que
        # esta fase nao faz -- entao a exclusao e CONTADA, no mesmo padrao de
        # `opaque_caller_function_count` da Fase 5b, e nao silenciosa.
        return _unresolved(
            path,
            node.lineno,
            node.col_offset,
            "suite_run_not_visible",
            provenance,
            check_type="verification_suite",
        )
    argument = _on_data_argument(node)
    if not isinstance(argument, ast.Name):
        return _unresolved(
            path,
            node.lineno,
            node.col_offset,
            "unresolved_target",
            provenance,
            check_type="verification_suite",
        )
    return _check(
        path,
        node,
        index,
        provenance,
        framework="pydeequ",
        check_type="verification_suite",
        target=argument.id,
        # `shares_scan`, NUNCA `single_pass`: o runner do Deequ roda numa mesma
        # passada as agregacoes que compartilham o mesmo agrupamento, e
        # `isUnique`/entropia exigem re-particionamento e pagam passada propria
        # (Schelter et al., PVLDB 2018, §4.1 e §5.1 --
        # knowledge/dq/validation-frameworks.md §2.3). Uma suite com N checks
        # custa uma passada POR AGRUPAMENTO, e nao uma. O contraste com N
        # `count()` separados -- que sao N passadas por construcao -- e o que
        # `SF-DQ-004` precisa, e ele sobrevive a correcao.
        shares_scan=True,
    )


def _dataframe_key(mapping: ast.Dict) -> ast.expr | None:
    """Valor sob a chave literal `"dataframe"`, ou `None` se ela nao existir."""
    for key, value in zip(mapping.keys, mapping.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == _DATAFRAME_KEY:
            return value
    return None


def _dict_bound_to(name: str, line: int, index: _ScopeIndex) -> ast.Dict | None:
    """O dict literal que este nome carrega na linha do uso -- UM passo atras.

    Vale o ultimo dict ligado ANTES da linha do uso, e a religacao entre a
    ligacao e o uso derruba a evidencia: em `params = {...}` / `params = f()` /
    `run(batch_parameters=params)`, o dict lido nao e o que chega a chamada.
    E a mesma pergunta que os quatro atributos de correlacao fazem, e a resposta
    vem do mesmo `_rebound_between` -- manter um predicado proprio aqui
    garantiria divergencia na proxima mudanca.

    Um nome ligado a algo que nao e dict literal (`params = monta()`) nao produz
    ligacao nenhuma: a ultima ligacao literal anterior fica separada do uso por
    aquela religacao, e a guarda acima ja a derruba.
    """
    bindings = [binding for binding in index.dicts.get(name, ()) if binding[0] < line]
    if not bindings:
        return None
    bound_line, mapping = bindings[-1]
    if _rebound_between(name, bound_line, line, index):
        return None
    return mapping


def _batch_dataframe(node: ast.Call, index: _ScopeIndex) -> ast.expr | None:
    """Valor sob a chave literal `"dataframe"` do dict de `batch_parameters`.

    O dict pode estar inline ou UM passo atras, num nome ligado no MESMO escopo
    -- e a forma que a documentacao corrente usa (§1.2 de
    knowledge/dq/validation-frameworks.md) e a segunda:

        batch_parameters = {"dataframe": dataframe}
        validation_definition.run(batch_parameters=batch_parameters)

    Reconhecer so o dict inline seria reconhecer a forma que a documentacao NAO
    usa. Um passo so, dentro do escopo, com religacao respeitada: seguir mais
    exigiria analise de fluxo, e adivinhar seria pior do que nao ver.

    `None` quando nao ha o que ler -- sem o argumento, sem ligacao legivel, ou
    sem a chave --, e ai nao ha validacao GE RECONHECIDA. Nao ha `dq.unresolved`
    nesses casos de proposito: sem a chave literal nada prova que a chamada e do
    Great Expectations, e contar um ponto cego que pode ser qualquer funcao com
    um argumento homonimo inflaria `unresolved_count`. Erra para menos, que e a
    direcao aceita nesta area.
    """
    for keyword in node.keywords:
        if keyword.arg != _BATCH_PARAMETERS:
            continue
        mapping: ast.expr | None = keyword.value
        if isinstance(mapping, ast.Name):
            mapping = _dict_bound_to(mapping.id, node.lineno, index)
        if isinstance(mapping, ast.Dict):
            value = _dataframe_key(mapping)
            if value is not None:
                return value
    return None


def _great_expectations_check(
    node: ast.Call, path: str, index: _ScopeIndex, provenance: dict[str, Any]
) -> Fact | None:
    value = _batch_dataframe(node, index)
    if value is None:
        return None
    if not isinstance(value, ast.Name):
        return _unresolved(
            path,
            node.lineno,
            node.col_offset,
            "unresolved_target",
            provenance,
            check_type="batch_parameters_dataframe",
        )
    return _check(
        path,
        node,
        index,
        provenance,
        framework="great_expectations",
        check_type="batch_parameters_dataframe",
        target=value.id,
        # SEM `shares_scan`, de proposito: quais e quantas expectativas rodam
        # vive no store do contexto (`great_expectations.yml` e as suites em
        # JSON), fora do `.py`. `engine._where_matches` reprova caminho ausente,
        # entao `SF-DQ-004` nao avalia este check -- que e o correto. Chave
        # ausente e como este motor diz "nao sei"; `false` afirmaria que a
        # validacao NAO compartilha varredura, e isso seria mentira.
    )


# Ordem da tentativa. Um mesmo `ast.Call` produz UM fact: a primeira forma que
# reconhece a chamada responde por ela, e as seguintes nem sao consultadas.
_DETECTORS = (_handmade_check, _pydeequ_check, _great_expectations_check)


class _Read(NamedTuple):
    """Como um teste alcanca o resultado do check: pelo no, ou por nome."""

    # O proprio no do check esta DENTRO do teste (`if df.filter(...).count()`).
    # Identidade de no, nao nome: nao ha o que religar, e nada a verificar.
    inline: bool
    # Nomes ligados ao resultado do check que o teste le. Nome nu nao identifica
    # objeto, entao cada um ainda paga a guarda de religacao.
    names: frozenset[str]


def _is_exit_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return (func.value.id, func.attr) in _EXIT_CALLS
    return isinstance(func, ast.Name) and func.id == _BARE_EXIT


def _abort_in(branches: list[ast.stmt]) -> tuple[str, int] | None:
    """(forma, linha) do PRIMEIRO aborto dentro dos ramos, em ordem de fonte.

    Um `if` que le o resultado pode abortar de mais de um jeito e em mais de um
    ponto; o fact afirma que ha consequencia, e a linha que ele mede e a da
    primeira. Ordenar por (linha, coluna) e o que torna a escolha independente
    da ordem de travessia, que nao e ordem de fonte.

    QUATRO LIMITES CONHECIDOS, todos do mesmo lado -- o fact afirma consequencia
    onde ela pode nao acontecer, e o erro cai no SILENCIO de `SF-DQ-002`, nunca
    na acusacao. Sao aceitos por isso, e estao escritos porque decisao sem razao
    escrita vira acidente na proxima leitura:

    1. `try: raise ... except: pass` em volta do aborto ainda conta. Provar que
       a excecao escapa exige seguir handlers, e um `except` que engole o aborto
       da propria validacao e codigo que ninguem escreve por engano.
    2. `sys.exit(0)` conta como aborto. O fact afirma que o resultado leva a
       saida do processo, e nao que a saida sinaliza falha; distinguir pelo
       argumento exigiria julgar o valor, e julgar nao e trabalho de extrator.
    3. Um `raise` ou `assert` NAO RELACIONADO dentro do ramo conta:
       `if ruins > 0: assert conf is not None` seguido de `logger.warning(...)`
       tem aborto no ramo, mas o aborto nao e a resposta ao check. Amarrar um ao
       outro exigiria analise de dependencia dentro do ramo.
    4. Um `raise` dentro de um `def` aninhado no ramo conta, e nao deveria --
       ele nao roda ali. Raro o bastante para nao pagar uma travessia com escopo
       proprio.
    """
    found: list[tuple[int, int, str]] = []
    for branch in branches:
        for node in ast.walk(branch):
            if isinstance(node, ast.Raise):
                found.append((node.lineno, node.col_offset, "raise"))
            elif isinstance(node, ast.Assert):
                found.append((node.lineno, node.col_offset, "assert"))
            elif _is_exit_call(node):
                found.append((node.lineno, node.col_offset, "exit"))
    if not found:
        return None
    line, _, form = min(found)
    return form, line


def _bound_names(nodes: list[ast.AST], check: ast.AST) -> frozenset[str]:
    """Nomes que carregam o resultado do check no escopo.

    CONTEM o no, e nao "e" o no: `ha_ruins = df.filter(...).count() > 0` liga o
    nome a uma comparacao, e a forma e tao comum quanto a atribuicao direta. Os
    tres frameworks caem aqui pelo mesmo caminho -- `ruins = ....count()`,
    `r = VerificationSuite(...).run()`, `res = validation_definition.run(...)` --
    porque o que se procura e o no do check, e nao a forma da cadeia que o
    produziu. Um percurso por framework divergiria na proxima mudanca, como o
    caminho unico de `_check` ja registrou.

    `NamedExpr` entra porque `if (ruins := ....count()) > 0` liga e le na mesma
    linha, e o walrus e a forma que o `if` inline usa quando o valor e reusado.

    O alvo e caminhado, e nao testado por `isinstance(..., ast.Name)`:
    `ruins, total = ....count(), 10` desempacota uma tupla, e filtrar por `Name`
    descartava a ligacao inteira. Caminhar liga tambem `total`, que nao carrega
    o resultado -- e o erro cai do lado do silencio, que e o lado que este kind
    escolheu: reconhecer um nome a mais faz `SF-DQ-002` calar, reconhecer um a
    menos faz ela acusar quem protegeu.
    """
    names: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Assign):
            value, targets = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr) and node.value is not None:
            value, targets = node.value, [node.target]
        else:
            continue
        if not any(child is check for child in ast.walk(value)):
            continue
        names.update(
            bound_name.id
            for target in targets
            for bound_name in ast.walk(target)
            if isinstance(bound_name, ast.Name) and isinstance(bound_name.ctx, ast.Store)
        )
    return frozenset(names)


def _reader(node: ast.AST) -> tuple[list[ast.expr], list[ast.stmt]] | None:
    """(o que le, onde o aborto pode estar) de um no que consome um resultado.

    Uma porta so para as cinco formas de leitura, porque a pergunta e sempre a
    mesma -- alguma expressao alcanca o resultado do check, e algum ramo aborta
    -- e so a sintaxe muda. Cada forma que faltava aqui era subreconhecimento, e
    subreconhecer e o lado da ACUSACAO FALSA neste kind: `SF-DQ-002` dispara
    sobre a ausencia de `dq.enforcement`.

    `while` tem a forma exata do `if`. `match` le pelo `subject` e por cada
    `guard`, e aborta dentro de qualquer `case` (o piso do projeto e Python
    3.10, entao `ast.Match` sempre existe). O `assert` e ele proprio o aborto,
    entao ele e o proprio ramo.

    `ast.Expr` cobre o curto-circuito e o `IfExp` em posicao de statement --
    `ruins > 0 and sys.exit(1)`, `sys.exit(1) if ruins > 0 else None` --, onde
    leitura e aborto vivem na MESMA expressao: o statement e ao mesmo tempo o
    que le e o ramo onde o aborto esta. Isso nao afrouxa a exigencia de aborto:
    `print(ruins)` tambem e `ast.Expr`, e `_abort_in` nao acha nada nele.

    LIMITE conhecido: a mesma expressao em posicao de VALOR
    (`x = sys.exit(1) if ruins > 0 else 0`) nao e lida. Cobri-la exigiria tratar
    todo statement como leitor em potencial, e abortar dentro do valor de uma
    atribuicao nao e forma que se escreva. Erra para o silencio.
    """
    if isinstance(node, ast.If | ast.While):
        return [node.test], node.body + node.orelse
    if isinstance(node, ast.Assert):
        return [node.test], [node]
    if isinstance(node, ast.Match):
        tests: list[ast.expr] = [node.subject]
        tests.extend(case.guard for case in node.cases if case.guard is not None)
        return tests, [statement for case in node.cases for statement in case.body]
    if isinstance(node, ast.Expr):
        return [node.value], [node]
    return None


def _read_of(tests: list[ast.expr], check: ast.AST, bound: frozenset[str]) -> _Read:
    inline = False
    names: set[str] = set()
    for test in tests:
        for node in ast.walk(test):
            if node is check:
                inline = True
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in bound:
                names.add(node.id)
    return _Read(inline, frozenset(names))


def _reads_this_check(read: _Read, check_line: int, read_line: int, index: _ScopeIndex) -> bool:
    """O teste le o resultado DESTE check, e nao um homonimo de outro momento.

    Pelo no, nao ha o que perguntar. Por nome, valem as duas guardas que o resto
    do modulo ja aplica: a leitura tem de vir DEPOIS do check -- ler `ruins`
    antes da linha que o liga e ler outra coisa -- e o nome nao pode ter sido
    religado no meio, senao o valor testado nao e o do check. Cada nome responde
    por si: `a = b = check` com `a` religado ainda vale se o teste le `b`.

    AQUI `_rebound_between` ERRA PARA A ACUSACAO, ao contrario dos quatro
    atributos da Task 2, onde ele erra para o silencio. Descartar a leitura
    descarta o fact, e a ausencia do fact e o gatilho de `SF-DQ-002`: o
    `except Exception: ruins = 0` em volta do check religa o nome e faz a regra
    acusar quem protegeu. Mantido -- sem seguir fluxo, o valor testado pode
    mesmo nao ser o do check --, e registrado no cabecalho do modulo com o caso
    medido. Nao e simetria esquecida; e assimetria conhecida.
    """
    if read.inline:
        return True
    return any(
        read_line > check_line and not _rebound_between(name, check_line, read_line, index)
        for name in read.names
    )


def _enforcements(
    check: ast.Call,
    subject: dict[str, Any],
    nodes: list[ast.AST],
    index: _ScopeIndex,
    provenance: dict[str, Any],
) -> list[Fact]:
    """`dq.enforcement` para um check: consequencia PRESENTE e COERENTE.

    Consequencia e combinacao de duas propriedades -- o resultado e lido, e a
    leitura leva a aborto --, e `engine._absent_satisfied` compara so `kind`: o
    motor nao sabe compor a ausencia de uma combinacao. Entao a combinacao e
    decidida aqui, e `SF-DQ-002` le `absent: dq.enforcement`. Mesmo padrao de
    `SF-EMR-008` na Fase 5b.

    Protecao pela metade NAO emite: `if ruins > 0: log(...)` le o resultado e
    segue publicando o dado ruim, e chamar isso de consequencia calaria a regra
    exatamente sobre o defeito que ela existe para achar.

    O subject e o do CHECK, copiado -- arquivo e linha do check, sem `symbol`.
    E o que faz `_subject_group_key` cair na mesma chave e o `same_subject` de
    `SF-DQ-002` funcionar. Subject proprio poria a protecao num grupo onde o
    check nao esta, e a regra dispararia sobre check protegido.

    `measures.line` e a linha da propria consequencia, que e a unica coisa que o
    fact tem para distinguir dois enforcements do mesmo check: dois consumidores
    do mesmo resultado sao dois facts, e o par (forma, linha) e a identidade
    deles. Sem isso, `Fact.id` -- sha de kind+subject+measures -- colidiria.

    LIMITE conhecido: consequencia atras de helper (`aborta_se(ruins)`) nao e
    vista, e `SF-DQ-002` acusa um codigo que protege. Provar isso exige seguir o
    valor para dentro da funcao, o que esta fase nao faz; o achado declara o
    recorte -- "sem consequencia NESTE corpus" --, como a 5b passou a fazer em
    `unreferenced_function_count`.
    """
    bound = _bound_names(nodes, check)
    check_line = check.lineno
    seen: set[tuple[str, int]] = set()
    for node in nodes:
        reader = _reader(node)
        if reader is None:
            continue
        tests, branches = reader
        read = _read_of(tests, check, bound)
        if not (read.inline or read.names):
            continue
        if not _reads_this_check(read, check_line, node.lineno, index):
            continue
        consequence = _abort_in(branches)
        if consequence is not None:
            seen.add(consequence)
    return [
        Fact(
            kind="dq.enforcement",
            subject=dict(subject),
            measures={"line": line},
            attrs={"form": form},
            provenance=provenance,
        )
        for line, form in sorted((line, form) for form, line in seen)
    ]


def extract_data_quality(tree: ast.AST, path: str, artifact_sha256: str = "") -> list[Fact]:
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    for root, nodes in _scopes(tree):
        index = _scope_index(root, nodes)
        found: list[Fact] = []
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            for detector in _DETECTORS:
                fact = detector(node, path, index, provenance)
                if fact is not None:
                    found.append(fact)
                    if fact.kind == "dq.check":
                        # Sem check nao ha subject a proteger: um enforcement
                        # sobre alvo nao resolvido seria um fact solto, e o
                        # `same_subject` de SF-DQ-002 nao teria par para ele.
                        found.extend(_enforcements(node, fact.subject, nodes, index, provenance))
                    break

        # Segundo passe: quantos checks ha sobre o mesmo alvo so e conhecido
        # depois de a travessia terminar. Por escopo, pelo mesmo motivo que o
        # indice: dois checks sobre `vendas` em duas funcoes diferentes nao sao
        # dois checks sobre o mesmo alvo.
        per_target = Counter(f.attrs["target"] for f in found if f.kind == "dq.check")
        facts.extend(
            replace(f, measures={**f.measures, "checks_on_target": per_target[f.attrs["target"]]})
            if f.kind == "dq.check"
            else f
            for f in found
        )

    check_count = sum(1 for f in facts if f.kind == "dq.check")
    unresolved_count = sum(1 for f in facts if f.kind == "dq.unresolved")
    facts.append(
        Fact(
            kind="dq.module_analyzed",
            subject=_subject(path),
            measures={"check_count": check_count, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_data_quality_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.py`, ancorando o path relativo a `repo_root`.

    Mesma convencao de `athena_workgroup.extract_athena_workgroup_path`: falha
    ao abrir o arquivo vira um unico Fact `dq.unresolved` com reason
    "read_error"; fonte que nao compila vira "syntax_error". Nunca uma excecao
    que derruba quem chamou -- um arquivo ilegivel e um ponto cego CONTADO, e
    nao o fim da varredura.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [_unresolved(anchor, 0, 0, "read_error", empty, detail=str(exc))]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance_sha = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            _unresolved(
                anchor,
                exc.lineno or 0,
                # Mesma leitura que `pyspark_ast.py:436` faz do mesmo erro.
                exc.offset or 0,
                "syntax_error",
                provenance_sha,
                detail=str(exc.msg),
            )
        ]
    return extract_data_quality(tree, anchor, artifact_sha256=sha)


def extract_data_quality_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.py` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um `.py` problematico vira `dq.unresolved`
    para aquele arquivo e a travessia continua -- mesma convencao de
    `athena_workgroup.extract_athena_workgroup_tree`.
    """
    facts: list[Fact] = []
    for py_file in sorted(root.rglob("*.py")):
        rel = str(py_file.relative_to(repo_root)) if repo_root else str(py_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_data_quality_path(py_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            # Um `.py` que nao decodifica levanta UnicodeDecodeError -- um
            # ValueError, nao um OSError -- e escaparia da guarda estreita de
            # `extract_data_quality_path`. Aqui a guarda e larga de proposito:
            # um arquivo ilegivel custa um fact contado, nunca a varredura
            # inteira.
            facts.append(
                _unresolved(
                    anchor,
                    0,
                    0,
                    "read_error",
                    {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                    detail=str(exc),
                )
            )
    return sort_facts(facts)
