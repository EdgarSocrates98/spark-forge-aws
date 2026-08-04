"""Validacao funcional: o plano derivado, e depois a comparacao antes/depois.

Funcao PURA sobre `Fact`: nunca executa consulta, nunca le artefato bruto, nunca
chama AWS. `build_plan` recebe os Facts que o motor ja tem -- os do
`analyze pyspark` e os do `analyze catalog` -- e devolve o que deve ser medido
nos dois lados de uma mudanca. Quem mede e o operador; o motor deriva o plano,
le o resultado e compara. Quarto modulo desta natureza, depois de
`call_graph.py`, `fusion.py` e `benchmark.py`, e pelo mesmo motivo dos tres:
`engine._condition_candidates` avalia UM fact por vez, entao "o depois divergiu
do antes" nao e expressavel como condicao de catalogo.

O QUE O PLANO PODE AFIRMAR, medido kind a kind sobre os 102 kinds dos 16
extratores (Task 1 da Fase 4c):

  * CONTAGEM sai de `pyspark.write.attrs.target` -- a IDENTIDADE do alvo, nunca
    o valor, que so a execucao do operador produz. `mode` PODE FALTAR
    (`insertInto`), entao nada aqui depende dele.
  * SCHEMA sai de `catalog.table_schema.attrs.column_types`, o unico lugar do
    repositorio onde coluna e tipo aparecem juntos.
  * AGREGADOS saem do mesmo mapa: cada coluna numerica vira `agg:sum:<coluna>`
    carregando o TIPO DECLARADO VERBATIM -- `decimal(18,2)` sobrevive --, porque
    e o tipo que escolhe comparacao exata contra tolerante (D-4 do spec). A
    escolha e da comparacao, nao do plano: aqui o tipo so viaja.
  * CHAVES nao saem de fact nenhum. Os sete candidatos (`pyspark.join`,
    `pyspark.dedup`, `pyspark.window`, `plan.join`, `plan.exchange`,
    `sql.predicate`, `sql.projection`) carregam booleano, contagem ou coluna de
    outra natureza -- `pyspark.join` da `on_arity`, o NUMERO de colunas do `on`,
    e nem isso na forma com keyword. Entao o eixo entra DECLARADO pelo operador
    (`--key`), com `origin: "declared"`, ou nao entra -- e quando nao entra,
    `undeclared_axes` diz isso por escrito (D-4c-1, D-4c-2).

`origin` existe em TODO check, derivado ou declarado. Se aparecesse so no caso
declarado seria excecao, e excecao nao e procedencia: ninguem leria um campo que
so existe quando a resposta e feia.

A FRONTEIRA QUE ESTE MODULO NAO ATRAVESSA (D-4c-3):

O catalogo serve para saber QUAIS colunas e tipos existem, e nada mais. A
comparacao e sempre antes contra depois, nunca observado contra declarado --
essa e asserção absoluta sobre o dado, que a §2 do spec poe fora de escopo e que
pertence a `SF-DQ`. Por isso o check de `schema` no plano carrega so
`origin`/`type`/`derived_from` e NAO o mapa coluna->tipo do catalogo: levar o
mapa junto daria a comparacao um lado "verdadeiro" contra o qual conferir, e o
criterio 10 da §9 depende dessa fronteira valer tambem dentro do modulo. Pelo
mesmo motivo, chave declarada nao e conferida contra o schema do catalogo.

UM PLANO POR ALVO, medido:

`pyspark_ast.extract_path` sobre um unico arquivo com cinco writes emite CINCO
facts e QUATRO alvos distintos (`db.vendas` duas vezes, `db.clientes`,
`cat.db.tbl`, um caminho `s3://`). Nenhuma fixture do repositorio exercita hoje
mais de um write por corpus -- as sete que emitem `pyspark.write` emitem
exatamente um --, mas o corpus do verbo `funcval plan` e um ARQUIVO de facts, que
e a uniao de tudo que o operador extraiu. Entao o caso e alcancavel e precisa de
decisao.

A decisao e um `funcval.plan` por alvo distinto, e ela nao e estetica:

  * as chaves de `checks` (`count`, `schema`, `agg:sum:<coluna>`) nao tem
    namespace de alvo, entao dois alvos num plano so colidiriam nelas;
  * o contrato do resultado (Task 1, Step 3) fixa `target` como string SINGULAR,
    e resultado com `target` diferente do plano e `funcval.unresolved` -- um
    plano com N alvos obrigaria a comparacao a ESCOLHER, que e adivinhar;
  * `Fact.id` e sha1 de (kind, subject, measures), e o subject por alvo
    (`{"type": "table", "symbol": <alvo>}`) ja separa os planos sem gambiarra.

O mesmo alvo escrito duas vezes continua sendo UM plano: a chave e o alvo, e os
dois `fact_id` entram juntos em `derived_from`. Presenca por CHAVE, nao por
fact -- a mesma disciplina de `benchmark.py`.

CASAMENTO DE ALVO, ESTRITO POR STRING IDENTICA:

O subject de `pyspark.write` e `source_location` (o `symbol` e a funcao
envolvente), entao o alvo mora em `attrs` e o casamento e por string contra o
`subject.symbol` de `catalog.table_schema`, que e `{type: "table", symbol:
"db.eventos"}`. Nome de tres partes (`cat.db.tbl`) contra simbolo de duas
(`db.tbl`) NAO casa: vira `funcval.unresolved` com o quase-casamento nomeado em
`near_symbols`, nunca alvo adivinhado por sufixo. Adivinhar o catalogo do alvo
errado produziria plano de agregados sobre colunas de outra tabela.

O alvo tambem chega errado por construcao do extrator, e isso e medido: em
`fixtures/pyspark/clean_job`, `df.write.mode(...).partitionBy("data_pedido")
.parquet(saida)` emite `target: "data_pedido"` -- o argumento do `partitionBy`,
porque o do `.parquet()` e variavel. Este modulo nao tem como saber disso, e nao
tenta: o alvo entra verbatim e o casamento estrito o transforma em
`catalog_schema_unmatched`, que e exatamente o sinal visivel de que o nome nao
descreve tabela nenhuma. Corrigir na origem e outra fase.

O QUE FICA DITO EM VEZ DE CALADO -- os cinco `funcval.unresolved`:

  * `no_write_target`: o corpus inteiro nao da um alvo. Sem ele, "nao ha o que
    validar" e "nao consegui derivar" ficariam indistinguiveis.
  * `write_without_target`: um write existe e nao nomeia destino -- medido em
    `fixtures/pyspark/action_in_loop`, que emite `pyspark.write` com `attrs`
    VAZIO. Ele nao apaga os planos dos outros alvos; so nao vira um.
  * `catalog_schema_unmatched`: o alvo nao casa com simbolo nenhum do catalogo.
  * `catalog_schema_ambiguous`: dois `catalog.table_schema` distintos para o
    mesmo simbolo. Escolher um seria chute com cara de derivacao.
  * `column_type_unclassified`: tipo que este modulo nao sabe se e numerico.
    Sem ele, um tipo desconhecido sumiria do eixo de agregados em silencio, e
    cobertura menor com cara de cobertura completa e o defeito que a fase existe
    para acusar.

Cada `funcval.unresolved` leva alvo e motivo dentro do `symbol` do subject:
`Fact.id` ignora `attrs` (D-4a-2), entao dois unresolved sem measures e com o
mesmo subject teriam o mesmo id e um sumiria da saida.

======================================================================
A COMPARACAO (Task 3): `build_comparison`
======================================================================

Entra o plano (o `attrs` de um `funcval.plan`) e os DOIS resultados que o
operador produziu; sai um `funcval.check_delta` por check comparado, a sentinela
`funcval.analyzed` e um `funcval.unresolved` para cada coisa que impediu uma
comparacao. O modulo continua sem executar nada: os valores sao do operador, e a
comparacao e sempre ANTES contra DEPOIS -- nunca observado contra catalogo
(D-4c-3).

O MODO DE COMPARACAO VEM DO PLANO, NUNCA DO RESULTADO:

`type` do check no PLANO escolhe exata contra relativa. Se viesse do resultado, o
operador escolheria se o proprio numero dele e comparado exato ou com tolerancia,
que e escolher o veredito. O `type` do resultado so e lido para check que o plano
NAO pediu, onde nao ha plano para ler (contrato minimo, regra 5).

  * EXATA para inteiro, decimal, contagem, chave e schema.
  * RELATIVA para ponto flutuante (`float`, `real`, `double`): soma de float
    depende da ORDEM DE REDUCAO, e um `repartition` legitimo muda o total nos
    ultimos bits. Comparacao exata daria falso positivo justamente na mudanca que
    a fase existe para aprovar.

QUEM APLICA A TOLERANCIA E O CATALOGO, E NAO ESTE MODULO (D-4c-10):

O check de ponto flutuante sai com `measures.relative_delta` e SEM `diverged`. O
numero que separa reassociacao de divergencia real e `field-heuristic` -- nao ha
fonte oficial que diga a partir de quantos ULP uma diferenca deixa de ser
reassociacao --, e heuristica de campo mora no YAML: `SF-FVAL-004` compara
`measures.relative_delta` contra `threshold.relative_tolerance`, exatamente como
`SF-BENCH-002` compara `total_task_ms_delta_pct` contra `threshold.regression_pct`.
Nenhum limiar deste repositorio mora em Python, e `Fact` e por definicao
"observacao deterministica ancorada, nunca contem juizo nem limiar"
(`findings/models.py`). Um `diverged` de ponto flutuante seria um limiar dentro de
um Fact.

A comparacao EXATA nao tem esse problema: "os dois valores nao sao identicos" e
observacao, nao limiar, entao ali o `diverged` fica no fact. Onde ele e omitido, a
razao vai escrita em `diverged_omitted_reason` -- chave que some sem explicacao e
o defeito que este repositorio persegue.

`relative_delta` e SIMETRICO -- `|depois - antes| / max(|antes|, |depois|)` --, e
nao a variacao com sinal de `benchmark._delta_pct`. Aqui a pergunta e "quao longe
um do outro", nao "para que lado andou", e a forma simetrica ainda fecha o furo
da base zero: antes 0 e depois 5.0 da 1.0 (totalmente distintos) em vez de uma
chave omitida por divisao por zero. Zero contra zero da 0.0.

OS TRES ESTADOS DE COBERTURA, QUE PRECISAM CONTINUAR DISTINTOS:

  1. check rodou e deu valor  -> `{"value": <n>}`, entra na comparacao e CONTA
     como reportado;
  2. check rodou e nao deu    -> `{"value": null, "unavailable_reason": "..."}`,
     vira `funcval.unresolved` e NAO conta como reportado;
  3. check nao foi reportado  -> a CHAVE nao esta em `checks`.

So o terceiro e cobertura faltante, e a presenca e por CHAVE -- a mesma
disciplina de `benchmark.py`. `value: null` SEM `unavailable_reason` viola o
contrato e nao vira nem zero nem ausencia: vira unresolved nomeado. Valor nao
numerico onde a comparacao exige numero tambem nao vira zero -- zero ali seria
observacao inventada.

CHECK QUE O RESULTADO TRAZ E O PLANO NAO PEDIU (D-4c-11):

E COMPARADO e fica MARCADO. Ignorar perderia divergencia observada; tratar como
divergencia de cobertura acusaria quem mediu a mais. Entao: sai um
`funcval.unresolved` com `reason: "check_not_planned"` (§5 do spec pede esse
estado por escrito), e um `funcval.check_delta` com `planned: false` quando ele da
para comparar -- o modo vindo do `type` do resultado, unico lugar onde ele e lido.
Sem `type` declarado o modulo nao adivinha: fica so o unresolved. O check nao
planejado NUNCA entra em `reported_check_count`, entao ele nao paga cobertura que
o plano pediu e nao veio.

O QUE A SENTINELA DECLARA, e por que isso e campo e nao comentario:

`funcval.analyzed` carrega em `attrs` que os quatro sao PROXIES: contagem,
schema, chaves e agregados iguais nao provam que o dado e o mesmo -- duas linhas
podem trocar valores entre si e os quatro passam. E o criterio 8 da §9 do spec, e
mora na saida porque quem le "quatro proxies bateram" nao pode ter que ir ao spec
para descobrir o que isso nao prova.

O QUE IMPEDE A COMPARACAO INTEIRA, em vez de um check so:

alvo do resultado diferente do alvo do plano (comparar numeros de tabelas
diferentes e pior que nao comparar), `side` do resultado contradizendo o lado em
que ele foi passado (comparacao invertida sai como melhora), e `plan_ref`
diferente entre os dois lados (foram medidos contra planos diferentes). Nos tres
sai `funcval.unresolved` e a sentinela SEMPRE sai junto, com `blocked_by` -- sem
ela, "nao comparei" e "comparei e estava tudo bem" ficariam indistinguiveis, que
e o defeito que a sentinela existe para fechar.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "funcval@0.1.0"

# Os quatro kinds do namespace (§5 do spec). `funcval.check_delta` e
# `funcval.analyzed` so passam a ser EMITIDOS pelo comparador da Task 3; estao
# declarados desde ja porque a assercao final deste modulo compara o emitido
# contra esta lista, e porque o namespace e contrato do modulo, nao diario de
# implementacao -- mesmo precedente de `benchmark.py`.
EMITTED_KINDS = frozenset(
    {
        "funcval.plan",
        "funcval.check_delta",
        "funcval.analyzed",
        "funcval.unresolved",
    }
)

# Os quatro eixos da §2 do spec, na ordem em que a fase os nomeia. `count` nunca
# aparece em `undeclared_axes`: se ha alvo ha plano, e se ha plano ha contagem.
_AXIS_SCHEMA = "schema"
_AXIS_AGGREGATES = "aggregates"
_AXIS_KEYS = "keys"

# Classificacao do tipo DECLARADO, so para decidir se a coluna admite `sum`. O
# tipo em si viaja verbatim para o check -- aqui ele e lido, nunca reescrito.
#
# Os tres tipos que as fixtures do repositorio exercitam hoje sao `bigint`,
# `double` e `string`; o resto da lista cobre o vocabulario de Hive/Glue e o de
# `DataType.simpleString` do Spark, que e o que um dump de catalogo traz. O que
# nao esta em nenhuma das duas listas NAO vira agregado e NAO fica em silencio:
# vira `column_type_unclassified`. Tipo novo e decisao de quem o adiciona, e
# adivinhar "parece numero" a partir do nome seria a resposta errada com cara de
# resposta certa.
_NUMERIC_BASE_TYPES = frozenset(
    {
        "tinyint", "byte", "smallint", "short", "int", "integer", "bigint", "long",
        "float", "real", "double", "decimal", "numeric", "dec",
    }
)

_NON_NUMERIC_BASE_TYPES = frozenset(
    {
        "string", "varchar", "char", "boolean", "bool", "binary", "date",
        "timestamp", "timestamp_ntz", "interval", "void", "null",
        "array", "map", "struct", "uniontype", "object", "json", "variant",
    }
)

# O `type` dos checks que nao sao coluna do catalogo.
#
# `count` e `key:*` sao contagens inteiras -- linhas, e valores de chave que
# ocorrem mais de uma vez --, entao comparacao exata, que e o que `bigint` diz a
# Task 3. `schema` nao e tipo de coluna: e o sentinela que diz "o valor deste
# check e um MAPA coluna->tipo", e nao um numero. `column_count` nao serviria no
# lugar dele -- nao distingue coluna removida de coluna renomeada, e a
# `SF-FVAL-002` fala das duas.
_COUNT_TYPE = "bigint"
_SCHEMA_TYPE = "schema"

_DERIVED = "derived"
_DECLARED = "declared"

# Os tipos de ponto flutuante, os UNICOS que a D-4 do spec compara com
# tolerancia. `decimal` NAO esta aqui: decimal e aritmetica exata, e compara-lo
# com tolerancia esconderia diferenca de centavo, que e diferenca de dinheiro.
_FLOAT_BASE_TYPES = frozenset({"float", "real", "double"})

_COMPARISON_EXACT = "exact"
_COMPARISON_RELATIVE = "relative"

# A natureza do valor do check, que decide COMO comparar antes de decidir com que
# rigor: numero se compara por diferenca, mapa se compara por coluna.
_VALUE_NUMBER = "number"
_VALUE_MAPPING = "mapping"

# O eixo do check, em `attrs`, para o catalogo selecionar sem funcao de string:
# `rules/expr.py` proibe `ast.Call`, entao `startswith("agg:")` nao e expressavel
# numa condicao. Sem este campo, `SF-FVAL-004` nao teria como falar so dos
# agregados.
_AXIS_COUNT = "count"
_AXIS_KEY = "key"
_AXIS_AGGREGATE = "aggregate"
_AXIS_OTHER = "other"

# Estado de um check em UM lado. Os tres primeiros sao os tres estados de
# cobertura do contrato; `malformed` e o contrato violado, que nao e nenhum dos
# tres e nao pode ser lido como nenhum deles.
_STATE_USABLE = "usable"
_STATE_ABSENT = "absent"
_STATE_UNAVAILABLE = "unavailable"
_STATE_MALFORMED = "malformed"

_SIDES = ("before", "after")

# O limite que a §3 do spec fixa, na SAIDA e nao so no spec (criterio 8 da §9).
_PROXY_AXES = ("count", "schema", "keys", "aggregates")

_PROXY_LIMIT = (
    "contagem, schema, chaves e agregados iguais NAO provam que o dado e o "
    "mesmo: duas linhas podem trocar valores entre si e os quatro passam. Esta "
    "comparacao afirma 'nenhum dos quatro proxies detectou divergencia', nunca "
    "'o resultado e identico'. Comparacao linha a linha e inviavel sobre volume "
    "real, e e por isso que os quatro sao proxies -- fortes, baratos e "
    "incompletos."
)

_RELATIVE_JUDGED_BY_CATALOG = (
    "comparacao relativa: o numero que separa reassociacao de ponto flutuante de "
    "divergencia real e heuristica de campo, e heuristica de campo mora no "
    "catalogo (SF-FVAL-004, threshold.relative_tolerance), nunca em Python -- um "
    "Fact nunca contem limiar. O fact carrega relative_delta; quem julga e a "
    "regra"
)

_KEYS_UNDECLARED_REASON = (
    "nenhum dos 102 kinds dos 16 extratores nomeia chave de negocio: "
    "pyspark.join da on_arity (o numero de colunas do on), pyspark.dedup e "
    "pyspark.window dao booleanos, e particao como proxy foi medida e rejeitada. "
    "Declare com --key <col>[,<col>] para o eixo entrar (D-4c-1, D-4c-2)"
)


def _check(origin: str, type_: str, derived_from: Sequence[str]) -> dict[str, Any]:
    """Um item do plano. Os tres campos existem nos DOIS origins: `origin` sem
    `derived_from` seria procedencia pela metade, e `derived_from: []` e a forma
    de dizer "isto nao veio de fact nenhum" sem que a chave desapareca."""
    return {"origin": origin, "type": type_, "derived_from": list(derived_from)}


def _base_type(declared: str) -> str:
    """A cabeca do tipo declarado, so para classificar: `decimal(18,2)` ->
    `decimal`, `array<int>` -> `array`. O valor guardado no check continua sendo
    o declarado inteiro, verbatim."""
    head = declared.strip().lower()
    for sep in ("(", "<"):
        cut = head.find(sep)
        if cut >= 0:
            head = head[:cut]
    return head.strip()


def _location(fact: Fact) -> str:
    """`arquivo:linha:coluna` do subject, para dar identidade propria ao
    unresolved de cada write mudo."""
    subject = fact.subject if isinstance(fact.subject, dict) else {}
    return "{}:{}:{}".format(
        subject.get("file", ""), subject.get("line", ""), subject.get("col", "")
    )


def _unresolved_subject(path_hint: str, detail: str) -> dict[str, Any]:
    """Subject proprio por motivo, e por alvo dentro do motivo.

    `Fact.id` e sha1 de (kind, subject, measures) -- `attrs` fica FORA (D-4a-2)
    --, entao dois `funcval.unresolved` sem measures e com o mesmo subject
    teriam o mesmo id e um deles desapareceria da saida.

    O tipo do subject e `table` em todo `funcval.*`, porque a unidade do dominio
    e o alvo; nos unresolved que nao tem alvo (o corpus sem write, o `--key`
    vazio) o `symbol` carrega o motivo e o `path_hint` ancora de qual corpus se
    trata. `s3.prefix_summary` ja usa `table` para um prefixo de S3, entao alvo
    em forma de caminho aqui segue precedente.
    """
    return {"type": "table", "symbol": f"{path_hint or 'funcval'}#{detail}"}


def _near_symbols(target: str, symbols: Sequence[str]) -> list[str]:
    """Os simbolos do catalogo que diferem do alvo SO por qualificacao -- um e
    sufixo do outro em segmentos separados por ponto.

    E diagnostico, nunca casamento: `cat.db.tbl` contra `db.tbl` fica nomeado
    para que o operador conserte o nome, e continua sem casar. Casar por sufixo
    juntaria `db.tbl` do catalogo `a` com `db.tbl` do catalogo `b`, que sao
    tabelas diferentes com o mesmo nome curto.
    """
    parts = target.split(".")
    near = []
    for symbol in symbols:
        other = symbol.split(".")
        if other == parts:
            continue
        shorter, longer = sorted((parts, other), key=len)
        if shorter and longer[-len(shorter):] == shorter:
            near.append(symbol)
    return sorted(near)


def _normalize_keys(keys: Sequence[str]) -> tuple[list[tuple[str, ...]], list[str]]:
    """As chaves declaradas como tuplas de coluna, mais as declaracoes vazias.

    Cada elemento de `keys` e um `--key`, e uma virgula dentro dele faz chave
    COMPOSTA: `--key loja_id,pedido_id` e uma chave de duas colunas, nao duas
    chaves. Declaracao que nao sobra coluna nenhuma nao vira check fantasma --
    vira `empty_key_declaration`, porque `--key ""` e engano do operador e o
    silencio o esconderia.
    """
    declared: list[tuple[str, ...]] = []
    empty: list[str] = []
    for raw in keys:
        columns = tuple(part.strip() for part in str(raw).split(",") if part.strip())
        if not columns:
            empty.append(str(raw))
            continue
        if columns not in declared:
            declared.append(columns)
    return declared, sorted(set(empty))


def _write_targets(
    facts: Sequence[Fact],
) -> tuple[dict[str, list[str]], list[tuple[str, dict[str, Any]]], int]:
    """Alvo -> ids dos writes que o escrevem, mais os writes mudos, mais o total.

    O alvo entra VERBATIM: `.strip()` mudaria a string que o casamento compara, e
    normalizacao silenciosa e como um alvo errado vira alvo plausivel. Alvo que
    nao e texto, ou que e so espaco, nao e alvo.
    """
    by_target: dict[str, list[str]] = {}
    mute: list[tuple[str, dict[str, Any]]] = []
    total = 0
    for fact in facts:
        if fact.kind != "pyspark.write":
            continue
        total += 1
        attrs = fact.attrs if isinstance(fact.attrs, dict) else {}
        target = attrs.get("target")
        if not isinstance(target, str) or not target.strip():
            location = _location(fact)
            mute.append(
                (
                    f"write_without_target#{location}",
                    {
                        "reason": "write_without_target",
                        "target": "",
                        "write_location": location,
                        "write_fact_id": fact.id,
                    },
                )
            )
            continue
        by_target.setdefault(target, []).append(fact.id)
    return by_target, mute, total


def _catalog_schemas(facts: Sequence[Fact]) -> dict[str, list[Fact]]:
    """Simbolo do catalogo -> os `catalog.table_schema` distintos que o nomeiam.

    Lista e nao fact unico porque um arquivo de facts pode juntar dois dumps: se
    eles discordarem, escolher um seria chute. Facts identicos (mesmo `Fact.id`)
    nao sao discordancia -- sao o mesmo dump lido duas vezes.
    """
    by_symbol: dict[str, dict[str, Fact]] = {}
    for fact in facts:
        if fact.kind != "catalog.table_schema":
            continue
        subject = fact.subject if isinstance(fact.subject, dict) else {}
        symbol = str(subject.get("symbol", "") or "")
        if not symbol:
            continue
        by_symbol.setdefault(symbol, {})[fact.id] = fact
    return {symbol: list(facts_by_id.values()) for symbol, facts_by_id in by_symbol.items()}


def build_plan(
    facts: Sequence[Fact], keys: Sequence[str] = (), path_hint: str = ""
) -> list[Fact]:
    """Deriva o plano de validacao funcional dos Facts que o motor ja tem.

    `facts` e o que `analyze pyspark` e `analyze catalog` produziram -- um
    `pyspark.write` diz qual alvo o job escreve, um `catalog.table_schema` diz
    quais colunas e tipos aquele alvo declara. `keys` sao as chaves de negocio
    que o operador declarou no `--key`, cada elemento uma chave (composta quando
    tem virgula). `path_hint` ancora a procedencia e o subject dos unresolved
    que nao tem alvo.

    Sai um `funcval.plan` por alvo distinto, mais um `funcval.unresolved` para
    cada coisa que nao deu para derivar. Alvo nenhum nao produz plano vazio nem
    plano inventado: produz o unresolved que diz que nao havia alvo.

    Este modulo NAO executa nada e nao afirma nada sobre o dado: ele diz o que
    medir. Os valores vem do resultado que o operador produz, e a comparacao e
    sempre antes contra depois.
    """
    provenance = {
        "artifact": path_hint,
        "artifact_sha256": "",
        "extractor": EXTRACTOR_ID,
    }
    out: list[Fact] = []
    # detail -> attrs. O dicionario dedupe pelo detail, que e o mesmo criterio
    # que separa os `Fact.id`: dois unresolved com o mesmo detail seriam o mesmo
    # fact duas vezes.
    unresolved: dict[str, dict[str, Any]] = {}

    declared_keys, empty_keys = _normalize_keys(keys)
    for raw in empty_keys:
        unresolved[f"empty_key_declaration#{raw}"] = {
            "reason": "empty_key_declaration",
            "target": "",
            "declaration": raw,
        }

    by_target, mute_writes, write_count = _write_targets(facts)
    for detail, attrs in mute_writes:
        unresolved[detail] = attrs

    if not by_target:
        unresolved["no_write_target"] = {
            "reason": "no_write_target",
            "target": "",
            "write_fact_count": write_count,
        }

    catalog = _catalog_schemas(facts)
    catalog_symbols = sorted(catalog)

    for target in sorted(by_target):
        write_ids = sorted(set(by_target[target]))
        checks: dict[str, dict[str, Any]] = {
            "count": _check(_DERIVED, _COUNT_TYPE, write_ids)
        }
        # Eixo -> por que o plano nao pede check dele. Ausencia ESCRITA, na mesma
        # disciplina de `dq.unresolved` e `bench.unresolved`: o leitor nao pode
        # ter que deduzir de um campo que sumiu.
        undeclared: dict[str, str] = {}

        matches = catalog.get(target, [])
        if len(matches) > 1:
            reason = (
                f"dois catalog.table_schema distintos nomeiam '{target}'; "
                "escolher um seria chute com cara de derivacao"
            )
            undeclared[_AXIS_SCHEMA] = reason
            undeclared[_AXIS_AGGREGATES] = reason
            unresolved[f"{target}#catalog_schema_ambiguous"] = {
                "reason": "catalog_schema_ambiguous",
                "target": target,
                "schema_fact_ids": sorted(f.id for f in matches),
            }
        elif not matches:
            near = _near_symbols(target, catalog_symbols)
            reason = (
                f"nenhum catalog.table_schema com symbol identico a '{target}'; "
                "o casamento e por string, e casar por sufixo juntaria tabelas "
                "homonimas de catalogos diferentes"
            )
            undeclared[_AXIS_SCHEMA] = reason
            undeclared[_AXIS_AGGREGATES] = reason
            unresolved[f"{target}#catalog_schema_unmatched"] = {
                "reason": "catalog_schema_unmatched",
                "target": target,
                "near_symbols": near,
                "catalog_symbol_count": len(catalog_symbols),
            }
        else:
            schema_fact = matches[0]
            checks["schema"] = _check(_DERIVED, _SCHEMA_TYPE, [schema_fact.id])

            schema_attrs = schema_fact.attrs if isinstance(schema_fact.attrs, dict) else {}
            column_types = schema_attrs.get("column_types")
            if not isinstance(column_types, dict):
                column_types = {}

            numeric = 0
            for column in sorted(column_types):
                declared_type = column_types[column]
                if not isinstance(declared_type, str):
                    unresolved[f"{target}#{column}#column_type_unclassified"] = {
                        "reason": "column_type_unclassified",
                        "target": target,
                        "column": column,
                        "declared_type": "",
                    }
                    continue
                base = _base_type(declared_type)
                if base in _NUMERIC_BASE_TYPES:
                    numeric += 1
                    # O tipo vai VERBATIM: e ele que a Task 3 le para escolher
                    # exata contra tolerante, e normalizar aqui apagaria a
                    # precisao de `decimal(18,2)`.
                    checks[f"agg:sum:{column}"] = _check(
                        _DERIVED, declared_type, [schema_fact.id]
                    )
                elif base not in _NON_NUMERIC_BASE_TYPES:
                    unresolved[f"{target}#{column}#column_type_unclassified"] = {
                        "reason": "column_type_unclassified",
                        "target": target,
                        "column": column,
                        "declared_type": declared_type,
                    }

            if not numeric:
                undeclared[_AXIS_AGGREGATES] = (
                    f"o schema declarado de '{target}' nao tem coluna de tipo "
                    "numerico, entao nao ha agregado a derivar"
                )

        # O eixo de chaves. A declaracao do operador nao e por alvo -- ele
        # declarou a chave, nao "a chave de db.vendas" --, entao ela vale para
        # todos os alvos do corpus, e `origin: "declared"` deixa gravado de quem
        # e a afirmacao. Chave declarada errada produz P0 em dado correto; a
        # diferenca para o motor adivinhar e que aqui fica escrito quem disse.
        for columns in declared_keys:
            checks["key:" + "+".join(columns)] = _check(_DECLARED, _COUNT_TYPE, [])
        if not declared_keys:
            undeclared[_AXIS_KEYS] = _KEYS_UNDECLARED_REASON

        checks = dict(sorted(checks.items()))
        derived_ids = sorted(
            {fact_id for check in checks.values() for fact_id in check["derived_from"]}
        )
        declared_count = sum(1 for check in checks.values() if check["origin"] == _DECLARED)

        out.append(
            Fact(
                kind="funcval.plan",
                subject={"type": "table", "symbol": target},
                measures={
                    "check_count": len(checks),
                    "derived_check_count": len(checks) - declared_count,
                    "declared_check_count": declared_count,
                },
                attrs={
                    "target": target,
                    "checks": checks,
                    "derived_from": derived_ids,
                    "undeclared_axes": sorted(undeclared),
                    "undeclared_axes_reason": dict(sorted(undeclared.items())),
                },
                provenance=provenance,
            )
        )

    for detail in sorted(unresolved):
        out.append(
            Fact(
                kind="funcval.unresolved",
                subject=_unresolved_subject(path_hint, detail),
                attrs=unresolved[detail],
                provenance=provenance,
            )
        )

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)


# ---------------------------------------------------------------------------
# A comparacao antes/depois. Ver o bloco "A COMPARACAO (Task 3)" no topo.
# ---------------------------------------------------------------------------


def _axis_of(check: str) -> str:
    """O eixo do check, derivado do NOME que o plano fixou."""
    if check == "count":
        return _AXIS_COUNT
    if check == _AXIS_SCHEMA:
        return _AXIS_SCHEMA
    if check.startswith("key:"):
        return _AXIS_KEY
    if check.startswith("agg:"):
        return _AXIS_AGGREGATE
    return _AXIS_OTHER


def _mode_of(declared_type: str) -> tuple[str, str] | None:
    """(natureza do valor, rigor da comparacao), ou `None` quando este modulo nao
    classifica o tipo.

    Le a CABECA do tipo, como `build_plan`: `decimal(18,2)` classifica por
    `decimal`. Tipo nao classificado nao vira comparacao exata por omissao --
    exata seria o palpite conservador para um numero e o palpite errado para um
    float --, vira unresolved nomeado.
    """
    base = _base_type(declared_type)
    if base == _SCHEMA_TYPE:
        return (_VALUE_MAPPING, _COMPARISON_EXACT)
    if base in _FLOAT_BASE_TYPES:
        return (_VALUE_NUMBER, _COMPARISON_RELATIVE)
    if base in _NUMERIC_BASE_TYPES:
        return (_VALUE_NUMBER, _COMPARISON_EXACT)
    return None


def _round(value: Any) -> Any:
    """Corta o ruido de bit dos valores que entram em `measures`.

    Mesmo motivo que em `benchmark.py`: `Fact.id` e sha1 de (kind, subject,
    measures), entao float nao arredondado faria o id -- e o golden que o cita --
    depender dos ultimos bits de uma soma. Tres casas, e inteiro passa intacto.

    O `diverged` da comparacao exata e calculado sobre o valor CRU, nunca sobre
    este: arredondar antes de comparar transformaria o arredondamento em
    tolerancia disfarcada, que e exatamente o que a D-4 nao quer fora do ponto
    flutuante.
    """
    if isinstance(value, bool) or not isinstance(value, float):
        return value
    return round(value, 3)


def _round_relative(value: float) -> float:
    """O delta relativo com tres digitos SIGNIFICATIVOS.

    `round(x, 3)` serviria para um total e nao serve aqui: a grandeza que
    interessa vive perto de 1e-12, e tres casas decimais a zerariam -- o fact
    entregaria 0.0 para o catalogo comparar contra a tolerancia, e toda
    divergencia pequena passaria. Tres significativos preservam a ordem de
    grandeza em qualquer faixa e continuam estabilizando o `Fact.id`.
    """
    return float(f"{value:.3g}")


def _numeric(value: Any) -> float | None:
    """O valor como numero comparavel, ou `None` quando ele nao e um.

    `bool` fica de fora de proposito: `True` viraria 1 e uma flag mal colocada no
    resultado seria comparada como contagem. Mesma decisao de `benchmark._read`.

    `inf` e `nan` tambem ficam de fora, e nao e teoria: `json.loads` aceita
    `Infinity` e `NaN` por padrao, entao eles chegam de um resultado escrito a
    mao. `inf - inf` e `nan`, `nan != nan` faria todo check divergir, e um `nan`
    em `measures` sairia do `json.dumps` como JSON invalido -- o golden nao
    voltaria a ser lido. Vira `value_not_numeric`, que e a verdade: nao ha numero
    ali com que comparar.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _relative_difference(before: float, after: float) -> float:
    """`|depois - antes| / max(|antes|, |depois|)`, simetrica.

    Zero contra zero e 0.0 (identicos), e zero contra qualquer coisa e 1.0 --
    totalmente distintos --, entao nao ha o furo de base zero que obriga
    `benchmark._delta_pct` a omitir a chave. Aqui a pergunta e "quao longe um do
    outro", nao "para que lado andou": a direcao nao muda o veredito de
    equivalencia.
    """
    scale = max(abs(before), abs(after))
    if scale == 0:
        return 0.0
    return abs(after - before) / scale


def _side_check(checks: Any, check: str) -> tuple[str, Any, str]:
    """(estado, valor, detalhe) de um check em um lado.

    Presenca e por CHAVE. Os tres estados de cobertura ficam distintos aqui, e o
    quarto -- contrato violado -- nao e lido como nenhum deles.
    """
    if not isinstance(checks, dict) or check not in checks:
        return (_STATE_ABSENT, None, "")
    entry = checks[check]
    if not isinstance(entry, dict):
        return (_STATE_MALFORMED, None, "check_entry_not_object")
    if "value" not in entry:
        return (_STATE_MALFORMED, None, "check_without_value")
    value = entry["value"]
    if value is None:
        reason = entry.get("unavailable_reason")
        if isinstance(reason, str) and reason.strip():
            return (_STATE_UNAVAILABLE, None, reason)
        return (_STATE_MALFORMED, None, "null_without_unavailable_reason")
    return (_STATE_USABLE, value, "")


def _result_checks(result: Any) -> dict[str, Any]:
    checks = result.get("checks") if isinstance(result, dict) else None
    return checks if isinstance(checks, dict) else {}


def _declared_type(checks: dict[str, Any], check: str) -> str:
    """O `type` que o RESULTADO declara para um check. Lido so para check nao
    planejado -- no planejado quem manda e o plano, senao o operador escolheria o
    rigor com que o numero dele e julgado."""
    entry = checks.get(check)
    if not isinstance(entry, dict):
        return ""
    declared = entry.get("type")
    return declared.strip() if isinstance(declared, str) else ""


def _mapping_of(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _delta_measures_and_attrs(
    value_kind: str,
    comparison: str,
    before_value: Any,
    after_value: Any,
) -> tuple[dict[str, Any], dict[str, Any], bool | None] | None:
    """As measures, os attrs proprios e o veredito de um check comparavel.

    Devolve `None` quando o valor nao tem a natureza que a comparacao exige --
    texto onde precisa de numero, numero onde precisa de mapa. Ali nao ha
    substituto: zero seria observacao inventada, e mapa vazio afirmaria tabela sem
    coluna.

    O terceiro elemento e `None` quando o veredito NAO e deste modulo: e o caso da
    comparacao relativa, cujo limiar mora no catalogo.
    """
    if value_kind == _VALUE_MAPPING:
        before_map = _mapping_of(before_value)
        after_map = _mapping_of(after_value)
        if before_map is None or after_map is None:
            return None
        added = sorted(set(after_map) - set(before_map))
        removed = sorted(set(before_map) - set(after_map))
        # Verbatim, sem normalizar: `bigint` contra `BIGINT` sai como mudanca de
        # tipo porque este modulo nao sabe se os dois lados vieram do mesmo
        # dialeto, e normalizar aqui apagaria `decimal(18,2)` contra
        # `decimal(18,4)` pelo mesmo caminho.
        changed = sorted(
            column
            for column in set(before_map) & set(after_map)
            if before_map[column] != after_map[column]
        )
        measures = {
            "before_column_count": len(before_map),
            "after_column_count": len(after_map),
            "added_column_count": len(added),
            "removed_column_count": len(removed),
            "type_changed_column_count": len(changed),
        }
        attrs = {
            "added_columns": added,
            "removed_columns": removed,
            "type_changed_columns": changed,
        }
        return (measures, attrs, bool(added or removed or changed))

    before_number = _numeric(before_value)
    after_number = _numeric(after_value)
    if before_number is None or after_number is None:
        return None

    relative = _relative_difference(before_number, after_number)
    measures = {
        "value_before": _round(before_value),
        "value_after": _round(after_value),
        "abs_delta": _round(abs(after_number - before_number)),
        "relative_delta": _round_relative(relative),
    }
    if comparison == _COMPARISON_RELATIVE:
        return (measures, {"diverged_omitted_reason": _RELATIVE_JUDGED_BY_CATALOG}, None)
    # Exata sobre o valor CRU, nunca sobre o arredondado das measures.
    return (measures, {}, before_value != after_value)


def build_comparison(
    plan: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    path_hint: str = "",
) -> list[Fact]:
    """Compara os dois resultados do operador contra o plano e emite os `funcval.*`.

    `plan` e o `attrs` de um `funcval.plan` -- `target` e `checks` --, e `before` e
    `after` sao os resultados que o operador produziu de cada lado, no contrato
    minimo da Task 1: `target`, `checks` com a presenca por chave, cada check um
    objeto `{"value": <numero|mapa|null>}` e `value: null` exigindo
    `unavailable_reason`.

    Sai um `funcval.check_delta` por check comparado, um `funcval.unresolved` por
    coisa que impediu comparacao, e SEMPRE a sentinela `funcval.analyzed` -- que
    declara, em `attrs`, que os quatro eixos sao proxies.

    O modo de comparacao vem do plano. O limiar da comparacao relativa nao vem
    daqui: vem do catalogo.
    """
    provenance = {
        "artifact": path_hint,
        "artifact_sha256": "",
        "extractor": EXTRACTOR_ID,
    }
    out: list[Fact] = []
    unresolved: dict[str, dict[str, Any]] = {}

    plan_map = plan if isinstance(plan, dict) else {}
    target = str(plan_map.get("target", "") or "")
    planned = plan_map.get("checks")
    planned = planned if isinstance(planned, dict) else {}

    results = {"before": before, "after": after}
    side_checks = {side: _result_checks(results[side]) for side in _SIDES}

    def add_unresolved(detail: str, attrs: dict[str, Any]) -> None:
        unresolved[detail] = attrs

    # --- o que impede a comparacao inteira -------------------------------
    blocked: list[str] = []

    for side in _SIDES:
        result = results[side] if isinstance(results[side], dict) else {}
        result_target = str(result.get("target", "") or "")
        if result_target != target:
            blocked.append("target_mismatch")
            add_unresolved(
                f"{target}#{side}#target_mismatch",
                {
                    "reason": "target_mismatch",
                    "target": target,
                    "sides": [side],
                    "result_target": result_target,
                },
            )
        declared_side = result.get("side")
        if isinstance(declared_side, str) and declared_side.strip() and declared_side != side:
            blocked.append("side_mismatch")
            add_unresolved(
                f"{target}#{side}#side_mismatch",
                {
                    "reason": "side_mismatch",
                    "target": target,
                    "sides": [side],
                    "declared_side": declared_side,
                },
            )

    refs = {}
    for side in _SIDES:
        result = results[side] if isinstance(results[side], dict) else {}
        refs[side] = str(result.get("plan_ref", "") or "")
    if refs["before"] and refs["after"] and refs["before"] != refs["after"]:
        blocked.append("plan_ref_conflict")
        add_unresolved(
            f"{target}#plan_ref_conflict",
            {
                "reason": "plan_ref_conflict",
                "target": target,
                "sides": list(_SIDES),
                "plan_ref": dict(sorted(refs.items())),
            },
        )

    if not planned:
        add_unresolved(
            f"{target}#plan_without_checks",
            {
                "reason": "plan_without_checks",
                "target": target,
                "sides": [],
            },
        )

    reported = 0
    compared = 0
    diverged = 0
    relative = 0
    unplanned_count = 0

    # --- os checks que o plano pediu -------------------------------------
    if not blocked:
        for check in sorted(planned):
            spec = planned[check] if isinstance(planned[check], dict) else {}
            declared_type = spec.get("type")
            declared_type = declared_type if isinstance(declared_type, str) else ""
            axis = _axis_of(check)
            base_attrs = {
                "target": target,
                "check": check,
                "axis": axis,
                "type": declared_type,
                "planned": True,
            }

            states = {side: _side_check(side_checks[side], check) for side in _SIDES}
            bad = [side for side in _SIDES if states[side][0] != _STATE_USABLE]
            if bad:
                # "nao veio", "veio e nao deu" e "veio errado" sao problemas
                # diferentes, e o motivo diz qual predomina: so o primeiro e
                # cobertura faltante.
                kinds = {states[side][0] for side in bad}
                if _STATE_MALFORMED in kinds:
                    reason = "check_entry_malformed"
                elif _STATE_UNAVAILABLE in kinds:
                    reason = "check_value_unavailable"
                elif len(bad) == 2:
                    reason = "check_not_reported"
                else:
                    reason = "check_absent_one_side"
                add_unresolved(
                    f"{target}#{check}#{reason}",
                    {
                        **base_attrs,
                        "reason": reason,
                        "sides": bad,
                        "state": {side: states[side][0] for side in _SIDES},
                        "detail": {
                            side: states[side][2] for side in _SIDES if states[side][2]
                        },
                    },
                )
                continue

            reported += 1
            mode = _mode_of(declared_type)
            if mode is None:
                add_unresolved(
                    f"{target}#{check}#check_type_unclassified",
                    {
                        **base_attrs,
                        "reason": "check_type_unclassified",
                        "sides": list(_SIDES),
                    },
                )
                continue

            value_kind, comparison = mode
            built = _delta_measures_and_attrs(
                value_kind, comparison, states["before"][1], states["after"][1]
            )
            if built is None:
                reason = (
                    "schema_value_not_mapping"
                    if value_kind == _VALUE_MAPPING
                    else "value_not_numeric"
                )
                add_unresolved(
                    f"{target}#{check}#{reason}",
                    {
                        **base_attrs,
                        "reason": reason,
                        "sides": list(_SIDES),
                        "expected_value_kind": value_kind,
                    },
                )
                continue

            measures, extra, verdict = built
            compared += 1
            if verdict is None:
                relative += 1
            elif verdict:
                diverged += 1
            attrs = {**base_attrs, "comparison": comparison, **extra}
            if verdict is not None:
                attrs["diverged"] = verdict
            out.append(
                Fact(
                    kind="funcval.check_delta",
                    subject={"type": "table", "symbol": f"{target}#{check}"},
                    measures=measures,
                    attrs=dict(sorted(attrs.items())),
                    provenance=provenance,
                )
            )

        # --- o que o resultado trouxe e o plano nao pediu -----------------
        extra_checks = sorted(
            (set(side_checks["before"]) | set(side_checks["after"])) - set(planned)
        )
        for check in extra_checks:
            unplanned_count += 1
            states = {side: _side_check(side_checks[side], check) for side in _SIDES}
            types = {side: _declared_type(side_checks[side], check) for side in _SIDES}
            declared_type = types["before"] or types["after"]
            conflict = bool(
                types["before"] and types["after"] and types["before"] != types["after"]
            )
            mode = None if conflict or not declared_type else _mode_of(declared_type)
            usable = all(states[side][0] == _STATE_USABLE for side in _SIDES)

            built = None
            if usable and mode is not None:
                built = _delta_measures_and_attrs(
                    mode[0], mode[1], states["before"][1], states["after"][1]
                )

            add_unresolved(
                f"{target}#{check}#check_not_planned",
                {
                    "reason": "check_not_planned",
                    "target": target,
                    "check": check,
                    "axis": _axis_of(check),
                    "type": declared_type,
                    "planned": False,
                    "sides": [side for side in _SIDES if check in side_checks[side]],
                    "state": {side: states[side][0] for side in _SIDES},
                    "type_conflict": conflict,
                    "compared": built is not None,
                },
            )
            if built is None:
                continue

            measures, extra, verdict = built
            compared += 1
            if verdict is None:
                relative += 1
            elif verdict:
                diverged += 1
            attrs = {
                "target": target,
                "check": check,
                "axis": _axis_of(check),
                "type": declared_type,
                "planned": False,
                "comparison": mode[1],
                **extra,
            }
            if verdict is not None:
                attrs["diverged"] = verdict
            out.append(
                Fact(
                    kind="funcval.check_delta",
                    subject={"type": "table", "symbol": f"{target}#{check}"},
                    measures=measures,
                    attrs=dict(sorted(attrs.items())),
                    provenance=provenance,
                )
            )

    # --- a sentinela, SEMPRE ---------------------------------------------
    #
    # `reported_check_count` conta os checks que o PLANO pediu e que vieram
    # usaveis nos DOIS lados -- e a contagem que a `SF-FVAL-005` compara com
    # `planned_check_count`. Um lado so nao e comparacao, e check nao planejado
    # nao paga cobertura que o plano pediu.
    #
    # `compared_check_count` e diferente de `reported_check_count`: um check pode
    # vir dos dois lados e ainda assim nao ser comparavel (tipo que este modulo
    # nao classifica, valor de outra natureza), e ali o unresolved nomeia o
    # motivo.
    #
    # `relative_delta_check_count` conta os deltas cujo veredito NAO e deste
    # modulo. Sem ele, `diverged_check_count == 0` seria lido como "nada
    # divergiu", quando pode significar "ninguem aqui decidiu".
    analyzed_attrs: dict[str, Any] = {
        "target": target,
        "proxies": list(_PROXY_AXES),
        "proxy_limit": _PROXY_LIMIT,
        "blocked_by": sorted(set(blocked)),
        "plan_ref": refs["before"] or refs["after"],
    }
    undeclared = plan_map.get("undeclared_axes")
    if isinstance(undeclared, list):
        # O eixo que o plano nunca pediu e limite da comparacao tanto quanto o
        # check que nao veio, e quem le a sentinela nao tem o plano na mao.
        analyzed_attrs["undeclared_axes"] = sorted(str(axis) for axis in undeclared)

    out.append(
        Fact(
            kind="funcval.analyzed",
            subject={"type": "table", "symbol": target or (path_hint or "funcval")},
            measures={
                "planned_check_count": len(planned),
                "reported_check_count": reported,
                "compared_check_count": compared,
                "diverged_check_count": diverged,
                "relative_delta_check_count": relative,
                "unplanned_check_count": unplanned_count,
            },
            attrs=dict(sorted(analyzed_attrs.items())),
            provenance=provenance,
        )
    )

    for detail in sorted(unresolved):
        out.append(
            Fact(
                kind="funcval.unresolved",
                subject=_unresolved_subject(path_hint, detail),
                attrs=dict(sorted(unresolved[detail].items())),
                provenance=provenance,
            )
        )

    unknown = {f.kind for f in out} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(out)
