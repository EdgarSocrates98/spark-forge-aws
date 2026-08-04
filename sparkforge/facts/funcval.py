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
"""
from __future__ import annotations

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
