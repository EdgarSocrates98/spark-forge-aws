"""Extrator estatico de codigo PySpark via `ast` da stdlib.

NUNCA importa nem executa o codigo do alvo: importar um modulo de job para
inspecionar executaria codigo arbitrario do repositorio analisado.

Duas passagens: (1) `_Context` mapeia cada no para seu pai, para a
funcao/metodo que o envolve e para a profundidade de loop em que esta;
(2) uma varredura sobre as chamadas (`ast.Call`) da arvore casa metodos
conhecidos e emite Facts diretamente. `_chain_methods` reconstroi a ordem de
escrita de uma cadeia fluente (`.select(...).join(...).filter(...)`) com um
`while`, nao recursao, pelo mesmo motivo do `_Context`.

Nao aplica limiar, nao atribui severidade, nao ordena por importancia.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "pyspark_ast@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "pyspark.read",
        "pyspark.write",
        "pyspark.action",
        "pyspark.driver_collect",
        "pyspark.udf",
        "pyspark.cache",
        "pyspark.partitioning",
        "pyspark.join",
        "pyspark.explode",
        "pyspark.window",
        "pyspark.chain",
        "pyspark.loop",
        "pyspark.withcolumn_run",
        "pyspark.conf_set",
        "pyspark.dedup",
        "pyspark.callgraph_edge",
        "pyspark.function_def",
        "pyspark.unresolved",
        "pyspark.module_analyzed",
        "pyspark.glue_context_init",
    }
)

_PARTITION_METHODS = frozenset({"coalesce", "repartition", "repartitionByRange"})
_REDUCTION_METHODS = frozenset({"select", "filter", "where", "drop", "selectExpr"})
_DRIVER_COLLECT = frozenset({"collect", "toPandas", "toLocalIterator"})
_BOUNDING_METHODS = frozenset({"limit", "take", "head", "first"})
_READ_TERMINALS = frozenset({"parquet", "csv", "json", "orc", "load", "table", "sql", "format"})
_WRITE_TERMINALS = frozenset(
    {
        "parquet",
        "csv",
        "json",
        "orc",
        "save",
        "saveAsTable",
        "insertInto",
        "append",
        "overwritePartitions",
        "overwrite",
        "create",
        "replace",
        "createOrReplace",
        "merge",
    }
)
_WRITE_MODE_NAMES = frozenset({"append", "overwrite", "overwritePartitions"})
_ACTIONS = frozenset(
    {
        "collect",
        "count",
        "show",
        "take",
        "first",
        "head",
        "toPandas",
        "foreach",
        "foreachPartition",
        "toLocalIterator",
        "isEmpty",
    }
)
_CACHE_METHODS = frozenset({"cache", "persist"})
_EXPLODE_FUNCS = frozenset({"explode", "posexplode", "explode_outer", "posexplode_outer"})
_DEDUP_METHODS = frozenset({"dropDuplicates", "distinct", "drop_duplicates"})
_UDF_FUNCS = frozenset({"udf", "pandas_udf"})


class _Context:
    """Mapa no -> pai, escopo de funcao, profundidade de loop.

    Percorre a arvore com uma pilha explicita, nao recursao Python: uma
    cadeia fluente longa (`df.filter(x).filter(x)...`) produz uma arvore
    profunda, e recursao por no estouraria o limite de pilha do interpretador
    nesse caso. Uma pilha explicita nao tem esse teto.
    """

    def __init__(self, tree: ast.AST) -> None:
        self.parent: dict[int, Any] = {}
        self.function: dict[int, str] = {}
        self.loop_depth: dict[int, int] = {}

        stack: list[tuple[ast.AST, ast.AST | None, str, int]] = [(tree, None, "", 0)]
        while stack:
            node, parent, symbol, depth = stack.pop()
            self.parent[id(node)] = parent
            self.function[id(node)] = symbol
            self.loop_depth[id(node)] = depth

            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                symbol = node.name
            if isinstance(node, ast.For | ast.AsyncFor | ast.While):
                depth += 1

            for child in ast.iter_child_nodes(node):
                stack.append((child, node, symbol, depth))


def _snippet(lines: list[str], node: ast.AST) -> str:
    lineno = getattr(node, "lineno", None)
    if lineno is None or lineno - 1 >= len(lines):
        return ""
    return lines[lineno - 1].strip()


def _subject(node: ast.AST, path: str, ctx: _Context, lines: list[str]) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": getattr(node, "lineno", 0),
        "col": getattr(node, "col_offset", 0),
        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
        "symbol": ctx.function.get(id(node), ""),
        "snippet": _snippet(lines, node),
    }


def _literal(node: ast.AST) -> Any | None:
    """Valor se o no e literal constante; None caso contrario.

    Desembrulha um unico nivel de +/- unario sobre constante numerica: `-5` e
    `+8` sao literais na fonte, mas o AST os representa como
    UnaryOp(USub|UAdd, Constant), nao como Constant direto. `--5` (dois
    niveis) permanece nao-literal de proposito. Bool continua excluido mesmo
    sob unario, ja que `-True` e `-1` em Python mas nao e uma contagem.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float | str | bool):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.UAdd | ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, int | float)
        and not isinstance(node.operand.value, bool)
    ):
        return node.operand.value if isinstance(node.op, ast.UAdd) else -node.operand.value
    return None


def _chain_methods(node: ast.Call) -> tuple[list[str], ast.AST]:
    """Caminha a espinha Attribute/Call e devolve os metodos em ordem de escrita.

    Passe 2. A ordem e o que permite transformar 'join antes de filter' em
    predicado sobre indices, em vez de leitura subjetiva.
    """
    methods: list[str] = []
    current: ast.AST = node

    while True:
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            methods.append(current.func.attr)
            current = current.func.value
        elif isinstance(current, ast.Attribute):
            methods.append(current.attr)
            current = current.value
        else:
            break

    methods.reverse()
    return methods, current


def _chain_root_call(node: ast.Call, ctx: _Context) -> bool:
    """True se `node` e o topo da cadeia, para nao emitir um fact por elo."""
    parent = ctx.parent.get(id(node))
    if isinstance(parent, ast.Attribute):
        return False
    if isinstance(parent, ast.Call) and parent.func is node:
        return False
    return True


def extract_source(source: str, path: str) -> list[Fact]:
    """Extrai Facts de `source`. `path` e usado como ancora e procedencia."""
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    provenance = {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    lines = source.splitlines()

    # `ast.parse` e a travessia seguinte compartilham um unico try: qualquer
    # um dos dois pode estourar em codigo pathologico (parse profundo demais
    # em construtos aninhados, ou uma travessia futura que reintroduza
    # recursao Python). Em ambos os casos o resultado deve ser "nao consegui
    # ler este arquivo" (um Fact honesto), nunca uma excecao vazando e
    # derrubando quem chamou `extract_source`.
    try:
        tree = ast.parse(source)
        ctx = _Context(tree)
        facts: list[Fact] = []

        # Pre-varredura: escopos (simbolo de funcao, "" para nivel de modulo)
        # que contem pelo menos um `.unpersist()`. `pyspark.cache` precisa
        # disso mesmo quando o unpersist aparece depois do cache no texto
        # fonte, entao nao da para descobrir em uma unica passagem left-to-right.
        unpersist_scopes = {
            ctx.function.get(id(n), "")
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "unpersist"
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Dispatch dinamico: cobertura honesta em vez de silencio.
            if isinstance(node.func, ast.Name) and node.func.id == "getattr":
                facts.append(
                    Fact(
                        kind="pyspark.unresolved",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"reason": "getattr"},
                        provenance=provenance,
                    )
                )
                continue

            if isinstance(node.func, ast.Name) and node.func.id == "GlueContext":
                facts.append(
                    Fact(
                        kind="pyspark.glue_context_init",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"form": "call"},
                        provenance=provenance,
                    )
                )
                continue

            if isinstance(node.func, ast.Name) and node.func.id in _UDF_FUNCS:
                facts.append(_udf_call_fact(node, path, ctx, lines, provenance))
                continue

            if isinstance(node.func, ast.Name) and node.func.id in _EXPLODE_FUNCS:
                facts.append(_explode_fact(node, path, ctx, lines, provenance))
                continue

            if not isinstance(node.func, ast.Attribute):
                continue

            method = node.func.attr
            # Espinha e raiz locais a `node`. Calculadas uma vez por no e
            # reusadas por todos os detectores abaixo, inclusive os que nao
            # exigem `node` seja a raiz de toda a cadeia fluente (read/write:
            # ver comentario junto a `_is_chain_terminal`).
            methods, root = _chain_methods(node)

            if method == "GlueContext":
                facts.append(
                    Fact(
                        kind="pyspark.glue_context_init",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"form": "call"},
                        provenance=provenance,
                    )
                )

            if method in _PARTITION_METHODS:
                facts.append(_partitioning_fact(node, method, path, ctx, lines, provenance))

            if method in _DRIVER_COLLECT:
                bounded = any(m in _BOUNDING_METHODS for m in methods[:-1])
                facts.append(
                    Fact(
                        kind="pyspark.driver_collect",
                        subject=_subject(node, path, ctx, lines),
                        attrs={
                            "method": method,
                            "bounded": bounded,
                            "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
                        },
                        provenance=provenance,
                    )
                )

            if method in _ACTIONS:
                facts.append(
                    Fact(
                        kind="pyspark.action",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"method": method},
                        provenance=provenance,
                    )
                )

            if method in _CACHE_METHODS:
                facts.append(
                    _cache_fact(node, method, path, ctx, lines, provenance, unpersist_scopes)
                )

            if method == "join":
                facts.append(_join_fact(node, path, ctx, lines, provenance))

            if method in _DEDUP_METHODS:
                facts.append(
                    Fact(
                        kind="pyspark.dedup",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"has_explicit_columns": bool(node.args)},
                        provenance=provenance,
                    )
                )

            # read/write NAO sao gateados por `_chain_root_call`: ao contrario de
            # `pyspark.chain` (que descreve a expressao fluente inteira e por isso
            # so faz sentido na raiz), o call terminal de leitura/escrita
            # frequentemente e seguido de mais metodos na mesma cadeia
            # (`spark.read.parquet(x).select(...).filter(...)`), o que o torna
            # nao-raiz. Gatear pela raiz atribuiria o fact ao ULTIMO metodo da
            # cadeia (ex.: "filter"), nao ao call de leitura real. Em vez disso,
            # `_is_chain_terminal` evita a contagem duplicada quando dois nos
            # terminal-elegiveis se sucedem direto (ex.: `.format(x).load(y)`).
            is_read = (
                method in _READ_TERMINALS
                and _is_chain_terminal(node, _READ_TERMINALS, ctx)
                and (
                    "read" in methods
                    or (
                        method in ("table", "sql")
                        and isinstance(root, ast.Name)
                        and root.id == "spark"
                    )
                )
            )
            if is_read:
                facts.append(_read_fact(node, method, path, ctx, lines, provenance))

            is_write = (
                method in _WRITE_TERMINALS
                and _is_chain_terminal(node, _WRITE_TERMINALS, ctx)
                and ("write" in methods or "writeTo" in methods)
            )
            if is_write:
                facts.append(_write_fact(node, method, path, ctx, lines, provenance))

            # Quatro formas de fixar configuracao de Spark no codigo, nao uma.
            #
            # Ate 2026-08-07 so `<algo>.conf.set(k, v)` era vista. Medido: das
            # quatro formas que aparecem em job real, TRES nao emitiam fact
            # nenhum -- nem `pyspark.conf_set`, nem `pyspark.unresolved`. Isso e
            # pior que nao extrair: "nenhum conf_set neste arquivo" era
            # indistinguivel de "o arquivo configura por uma forma que ninguem
            # le", e uma regra com condicao `absent:` sobre a chave seria
            # vazamente verdadeira. E o falso negativo silencioso do item 4 do
            # README do catalogo.
            #
            #   spark.conf.set(k, v)                  -> "conf" em methods
            #   SparkConf().set(k, v)                 -> raiz e Name("SparkConf")
            #   sc._conf.set(k, v)                    -> "_conf" em methods
            #   SparkSession.builder.config(k, v)     -> metodo "config"
            #
            # `builder.config(conf=objeto)` cai no ramo sem argumento posicional
            # e vira `non_literal_conf` -- ponto cego registrado, que e o
            # resultado correto: o valor esta noutro objeto e o AST nao o segue.
            # `SparkConf().set(...)`: a raiz e a CHAMADA do construtor, nao um
            # Name. `SparkConf.set(...)` (sem instanciar) tambem existe em
            # codigo real e a raiz ali e Name -- os dois casos entram.
            raiz_sparkconf = (isinstance(root, ast.Name) and root.id == "SparkConf") or (
                isinstance(root, ast.Call)
                and isinstance(root.func, ast.Name)
                and root.func.id == "SparkConf"
            )
            eh_conf_set = method == "set" and (
                "conf" in methods or "_conf" in methods or raiz_sparkconf
            )
            eh_builder_config = method == "config" and "builder" in methods
            if eh_conf_set or eh_builder_config:
                facts.append(_conf_set_fact(node, path, ctx, lines, provenance))

            if not _chain_root_call(node, ctx):
                continue

            if isinstance(root, ast.Name) and root.id == "Window":
                facts.append(_window_fact(node, methods, path, ctx, lines, provenance))


            if len(methods) < 2:
                continue

            facts.append(_chain_fact(node, methods, path, ctx, lines, provenance))

            run = _longest_withcolumn_run(methods)
            if run >= 2:
                facts.append(
                    Fact(
                        kind="pyspark.withcolumn_run",
                        subject=_subject(node, path, ctx, lines),
                        measures={"run_length": run},
                        attrs={"inside_loop": ctx.loop_depth.get(id(node), 0) > 0},
                        provenance=provenance,
                    )
                )

        facts.extend(_udf_decorator_facts(tree, path, ctx, lines, provenance))
        facts.extend(_function_def_facts(tree, path, ctx, lines, provenance))
        facts.extend(_loop_and_callgraph_facts(tree, path, ctx, lines, provenance))

        # Sentinela: prova de que a extracao PySpark rodou sobre este arquivo.
        # Sem isso, uma condicao `absent: X` do catalogo e vazamente verdadeira
        # quando o extrator nunca rodou (nenhum Fact de kind nenhum foi
        # produzido), nao so quando genuinamente nao encontrou X. So emitido no
        # caminho de sucesso: SyntaxError/RecursionError/MemoryError abaixo
        # devolvem cedo e nunca chegam aqui, porque esses arquivos nao foram
        # de fato analisados.
        resolved_calls = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Call))
        unresolved_count = sum(1 for f in facts if f.kind == "pyspark.unresolved")
        facts.append(
            Fact(
                kind="pyspark.module_analyzed",
                subject={
                    "type": "source_location",
                    "file": path,
                    "line": 0,
                    "col": 0,
                    "symbol": "",
                    "snippet": "",
                },
                measures={
                    "resolved_calls": resolved_calls,
                    "unresolved_count": unresolved_count,
                },
                # `referenced_names` e o que permite a um consumidor multi-arquivo
                # (call_graph) saber que o nome de uma funcao definida AQUI e lido
                # LA. Sem isso, toda funcao usada so entre modulos -- o caso normal
                # de uma biblioteca -- pareceria orfa.
                attrs={"parsed": True, "referenced_names": _referenced_names(tree)},
                provenance=provenance,
            )
        )

        unknown = {f.kind for f in facts} - EMITTED_KINDS
        if unknown:
            raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    except SyntaxError as exc:
        return [
            Fact(
                kind="pyspark.unresolved",
                subject={
                    "type": "source_location",
                    "file": path,
                    "line": exc.lineno or 0,
                    "col": exc.offset or 0,
                    "symbol": "",
                    "snippet": "",
                },
                attrs={"reason": "syntax_error", "detail": str(exc.msg)},
                provenance=provenance,
            )
        ]
    # MemoryError entra aqui porque o parser do CPython levanta
    # "Parser stack overflowed" em vez de RecursionError para aninhamento extremo
    # (ex.: "-" * 10000 + "1"), e a versao exata varia por interpretador. Ambos
    # significam a mesma coisa para o operador: o analisador nao conseguiu ver.
    except (RecursionError, MemoryError) as exc:
        return [
            Fact(
                kind="pyspark.unresolved",
                subject={
                    "type": "source_location",
                    "file": path,
                    "line": 0,
                    "col": 0,
                    "symbol": "",
                    "snippet": "",
                },
                attrs={
                    "reason": "too_deep",
                    "detail": f"{type(exc).__name__}: fonte complexa demais para parsear",
                },
                provenance=provenance,
            )
        ]

    return sort_facts(facts)


def _chain_fact(
    node: ast.Call,
    methods: list[str],
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    measures: dict[str, Any] = {"length": len(methods)}

    join_index = next((i for i, m in enumerate(methods) if m == "join"), None)
    if join_index is not None:
        measures["join_index"] = join_index

    reduction_index = next(
        (i for i, m in enumerate(methods) if m in _REDUCTION_METHODS), None
    )
    if reduction_index is not None:
        measures["first_reduction_index"] = reduction_index

    return Fact(
        kind="pyspark.chain",
        subject=_subject(node, path, ctx, lines),
        measures=measures,
        attrs={"methods": methods},
        provenance=provenance,
    )


def _longest_withcolumn_run(methods: list[str]) -> int:
    best = 0
    current = 0
    for method in methods:
        current = current + 1 if method == "withColumn" else 0
        best = max(best, current)
    return best


def _partitioning_fact(
    node: ast.Call,
    method: str,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    first = node.args[0] if node.args else None
    target = _literal(first) if first is not None else None
    literal_arg = isinstance(target, int) and not isinstance(target, bool)

    # repartition(200, "col") ou repartition("col"): ha expressao de particao.
    has_partition_expr = len(node.args) > 1 or (first is not None and not literal_arg)

    measures: dict[str, Any] = {}
    if literal_arg:
        measures["target_count"] = target

    return Fact(
        kind="pyspark.partitioning",
        subject=_subject(node, path, ctx, lines),
        measures=measures,
        attrs={
            "method": method,
            "literal_arg": literal_arg,
            "has_partition_expr": has_partition_expr,
            "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
        },
        provenance=provenance,
    )


def _chain_calls(node: ast.Call) -> list[ast.Call]:
    """Como `_chain_methods`, mas devolve os nos Call da espinha, em ordem de escrita."""
    calls: list[ast.Call] = []
    current: ast.AST = node
    while True:
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            calls.append(current)
            current = current.func.value
        elif isinstance(current, ast.Attribute):
            current = current.value
        else:
            break
    calls.reverse()
    return calls


def _first_literal_str_arg(calls: list[ast.Call]) -> str | None:
    for call in calls:
        for arg in call.args:
            val = _literal(arg)
            if isinstance(val, str):
                return val
    return None


def _target_literal(node: ast.Call) -> str | None:
    """Primeiro literal string: primeiro nos args do proprio no; senao na cadeia."""
    direct = _first_literal_str_arg([node])
    if direct is not None:
        return direct
    return _first_literal_str_arg(_chain_calls(node))


def _dotted_name(node: ast.AST) -> str | None:
    """`StorageLevel.MEMORY_AND_DISK` -> "StorageLevel.MEMORY_AND_DISK"; None se nao for
    cadeia de nomes."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return ".".join(parts)
    return None


def _is_chain_terminal(node: ast.Call, terminals: frozenset[str], ctx: _Context) -> bool:
    """True se nenhuma chamada seguinte na mesma cadeia tambem for terminal deste
    mesmo conjunto -- evita contar um builder intermediario (ex.: `.format(x)`
    antes de `.load(y)`) como uma segunda operacao terminal separada."""
    # O pai de um no numa espinha de atributo e sempre o ast.Attribute
    # intermediario, nunca o ast.Call que o envolve. Checar `isinstance(parent,
    # ast.Call)` direto daria sempre falso e nunca deduplicaria. Por isso subimos
    # a espinha inteira, e nao um hop: `.format(x).option(y).load(z)` tem um elo
    # nao-terminal no meio, e uma checagem de um hop deixaria `format` e `load`
    # emitirem dois facts para a mesma operacao.
    current: ast.AST = node
    while True:
        parent = ctx.parent.get(id(current))
        if isinstance(parent, ast.Attribute) and parent.value is current:
            grandparent = ctx.parent.get(id(parent))
            if isinstance(grandparent, ast.Call) and grandparent.func is parent:
                if parent.attr in terminals:
                    return False
                current = grandparent
                continue
        return True


def _read_fact(
    node: ast.Call,
    method: str,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    attrs: dict[str, Any] = {"format": method}
    target = _target_literal(node)
    if target is not None:
        attrs["target"] = target
    return Fact(
        kind="pyspark.read",
        subject=_subject(node, path, ctx, lines),
        attrs=attrs,
        provenance=provenance,
    )


def _write_fact(
    node: ast.Call,
    method: str,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    attrs: dict[str, Any] = {}

    mode_call = next(
        (
            c
            for c in _chain_calls(node)
            if isinstance(c.func, ast.Attribute) and c.func.attr == "mode"
        ),
        None,
    )
    mode = _first_literal_str_arg([mode_call]) if mode_call is not None else None
    if mode is None and method in _WRITE_MODE_NAMES:
        mode = method
    if mode is not None:
        attrs["mode"] = mode

    # Alvo procurado excluindo o elo `.mode(...)`: seu literal ("append",
    # "overwrite"...) nao e um destino e nao pode vazar para `target` quando o
    # argumento do call terminal (ex.: `.parquet(caminho_var)`) nao e literal.
    non_mode_calls = [c for c in _chain_calls(node) if c is not mode_call]
    target = _first_literal_str_arg([node]) or _first_literal_str_arg(non_mode_calls)
    if target is not None:
        attrs["target"] = target

    return Fact(
        kind="pyspark.write",
        subject=_subject(node, path, ctx, lines),
        attrs=attrs,
        provenance=provenance,
    )


def _cache_fact(
    node: ast.Call,
    method: str,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
    unpersist_scopes: set[str],
) -> Fact:
    attrs: dict[str, Any] = {
        "has_unpersist_in_scope": ctx.function.get(id(node), "") in unpersist_scopes,
    }

    if node.args:
        first = node.args[0]
        lit = _literal(first)
        if lit is not None:
            attrs["storage_level"] = str(lit)
        else:
            dotted = _dotted_name(first)
            if dotted is not None:
                attrs["storage_level"] = dotted

    return Fact(
        kind="pyspark.cache",
        subject=_subject(node, path, ctx, lines),
        attrs=attrs,
        provenance=provenance,
    )


def _join_fact(
    node: ast.Call,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    how = "inner"
    for kw in node.keywords:
        if kw.arg == "how":
            lit = _literal(kw.value)
            if isinstance(lit, str):
                how = lit

    has_broadcast_hint = any(
        isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "broadcast"
        for arg in node.args
    )

    measures: dict[str, Any] = {}
    if len(node.args) > 1:
        on_arg = node.args[1]
        lit = _literal(on_arg)
        if isinstance(lit, str):
            measures["on_arity"] = 1
        elif isinstance(on_arg, ast.List):
            measures["on_arity"] = len(on_arg.elts)

    return Fact(
        kind="pyspark.join",
        subject=_subject(node, path, ctx, lines),
        measures=measures,
        attrs={"how": how, "has_broadcast_hint": has_broadcast_hint},
        provenance=provenance,
    )


def _explode_fact(
    node: ast.Call,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    assert isinstance(node.func, ast.Name)  # garantido pelo dispatch em extract_source
    variant = node.func.id

    has_prior_reduction = False
    parent = ctx.parent.get(id(node))
    while parent is not None and not (
        isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute)
    ):
        parent = ctx.parent.get(id(parent))
    if parent is not None:
        methods, _ = _chain_methods(parent)
        has_prior_reduction = any(m in _REDUCTION_METHODS for m in methods[:-1])

    return Fact(
        kind="pyspark.explode",
        subject=_subject(node, path, ctx, lines),
        attrs={"variant": variant, "has_prior_reduction": has_prior_reduction},
        provenance=provenance,
    )


def _window_fact(
    node: ast.Call,
    methods: list[str],
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    return Fact(
        kind="pyspark.window",
        subject=_subject(node, path, ctx, lines),
        attrs={
            "has_partition_by": "partitionBy" in methods,
            "has_order_by": "orderBy" in methods,
            "has_frame": "rowsBetween" in methods or "rangeBetween" in methods,
        },
        provenance=provenance,
    )


def _conf_set_fact(
    node: ast.Call,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    key = _literal(node.args[0]) if len(node.args) > 0 else None
    value = _literal(node.args[1]) if len(node.args) > 1 else None

    if key is None or value is None:
        return Fact(
            kind="pyspark.unresolved",
            subject=_subject(node, path, ctx, lines),
            attrs={"reason": "non_literal_conf"},
            provenance=provenance,
        )

    return Fact(
        kind="pyspark.conf_set",
        subject=_subject(node, path, ctx, lines),
        attrs={"key": str(key), "value": str(value)},
        provenance=provenance,
    )


def _udf_call_fact(
    node: ast.Call,
    path: str,
    ctx: _Context,
    lines: list[str],
    provenance: dict[str, Any],
) -> Fact:
    assert isinstance(node.func, ast.Name)  # garantido pelo dispatch em extract_source
    udf_type = "pandas" if node.func.id == "pandas_udf" else "python"

    return_type = _literal(node.args[0]) if node.args else None
    if not isinstance(return_type, str):
        return_type = None
        for kw in node.keywords:
            if kw.arg == "returnType":
                lit = _literal(kw.value)
                if isinstance(lit, str):
                    return_type = lit

    attrs: dict[str, Any] = {"udf_type": udf_type}
    if return_type is not None:
        attrs["return_type"] = return_type

    return Fact(
        kind="pyspark.udf",
        subject=_subject(node, path, ctx, lines),
        attrs=attrs,
        provenance=provenance,
    )


def _udf_decorator_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> list[Fact]:
    """`@udf` ou `@pandas_udf` sem parenteses: referencia nua no decorator_list.

    A forma com chamada (`@udf(...)`) ja e um `ast.Call` comum e e coberta pelo
    dispatch de `Call` em `extract_source`; aqui so tratamos a forma nua para
    nao emitir o fact em duplicidade.
    """
    facts: list[Fact] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id in _UDF_FUNCS:
                udf_type = "pandas" if decorator.id == "pandas_udf" else "python"
                facts.append(
                    Fact(
                        kind="pyspark.udf",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"udf_type": udf_type},
                        provenance=provenance,
                    )
                )
    return facts


def _decorator_name(node: ast.expr) -> str:
    """Nome pontilhado do decorator (`functools.lru_cache`), ou "" se nao for nome."""
    target: ast.AST = node.func if isinstance(node, ast.Call) else node
    parts: list[str] = []
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
        return ".".join(reversed(parts))
    return ""


def _module_all(tree: ast.AST) -> frozenset[str]:
    """Nomes declarados em `__all__` no nivel do modulo.

    So le a forma literal (`__all__ = ["a", "b"]`): `__all__ += outra_lista` ou
    construcao dinamica ficam de fora, e ficam de fora em silencio de proposito
    -- inventar o conteudo de um `__all__` calculado seria julgamento, nao
    observacao. O efeito de nao ver um nome exportado e conservador na direcao
    certa: ele apenas deixa de ganhar o marcador `exported`.
    """
    names: set[str] = set()
    for stmt in getattr(tree, "body", []):
        if isinstance(stmt, ast.Assign):
            targets: list[ast.expr] = list(stmt.targets)
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            targets = [stmt.target]
            value = stmt.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        if isinstance(value, ast.List | ast.Tuple):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.add(elt.value)
    return frozenset(names)


def _referenced_names(tree: ast.AST) -> list[str]:
    """Todo identificador LIDO no modulo: `ast.Name` em Load e `ast.Attribute.attr`.

    Serve a uma pergunta so: o nome de uma funcao definida em OUTRO arquivo do
    corpus aparece aqui? Depois de `from lib import limpa`, a chamada e
    `limpa(df)` -- um `Name` em Load; depois de `import lib`, e `lib.limpa(df)`
    -- um `Attribute.attr`. Sem as duas formas, toda funcao usada apenas
    entre modulos pareceria nao referenciada, que e o falso positivo em massa
    que `rules/catalog/README.md` trata como o pior defeito possivel.

    Deliberadamente um SUPERCONJUNTO: `.count()` de DataFrame entra na lista e
    faz uma funcao local chamada `count` parecer referenciada. O erro cai para
    o lado de nao acusar, que e o lado certo -- deixar de apontar um simbolo
    orfao custa uma informacao; apontar um simbolo vivo custa a confianca no
    relatorio inteiro.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return sorted(names)


def _enclosing_def_kind(node: ast.AST, ctx: _Context) -> tuple[str, str]:
    """Onde a funcao foi definida: modulo, corpo de classe, ou dentro de outra funcao.

    Nao e classificacao estetica: decide se a AUSENCIA de chamador diz alguma
    coisa. Metodo e chamado por `self.x()`/`obj.x()`, que e `ast.Attribute` e
    nunca vira aresta; funcao aninhada e chamada de dentro de um fechamento.
    Nos dois casos "ninguem chama" e artefato do extrator, nao propriedade do
    codigo -- e o consumidor precisa saber disso pelo fact, nao por folclore.
    """
    parent = ctx.parent.get(id(node))
    while parent is not None:
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            return "nested", parent.name
        if isinstance(parent, ast.ClassDef):
            return "method", parent.name
        parent = ctx.parent.get(id(parent))
    return "module", ""


def _function_def_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> list[Fact]:
    """Um fact por funcao DEFINIDA, com ou sem chamada.

    `pyspark.callgraph_edge` so existe quando ha chamada; uma funcao definida e
    nunca chamada nao aparecia em lugar nenhum, e por isso
    `callgraph.summary.unreachable_function_count` devolvia zero para o caso
    exato que ele parecia medir (divida da Fase 1, registrada em
    `docs/superpowers/STATUS.md`). Zero indistinguivel de "nao ha nada" e a
    forma de silencio que este repositorio persegue.

    `measures.name_reference_count` conta as leituras do nome DENTRO deste
    modulo, fora do corpo da propria funcao -- o que cobre callback
    (`rdd.foreach(trata)`), tabela de despacho (`{"a": trata}`) e chamada de
    nivel de modulo (`main()` sob `if __name__`), nenhuma das quais produz
    aresta. Chamada por string (`getattr(mod, nome)`) continua invisivel, e ja
    tem seu proprio `pyspark.unresolved`.
    """
    exported = _module_all(tree)

    loads: dict[tuple[str, str], int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            key = (node.id, ctx.function.get(id(node), ""))
            loads[key] = loads.get(key, 0) + 1

    facts: list[Fact] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        def_kind, enclosing = _enclosing_def_kind(node, ctx)
        subject = _subject(node, path, ctx, lines)
        # `_subject` ancora no escopo QUE CONTEM o no; para a propria definicao
        # o simbolo tem que ser o nome dela, senao o no do grafo de chamadas
        # nasceria com a chave da funcao de fora.
        subject["symbol"] = node.name
        # Referencia de dentro do proprio corpo e recursao, nao uso externo:
        # sem excluir, toda funcao recursiva morta pareceria viva.
        references = sum(
            count
            for (name, scope), count in loads.items()
            if name == node.name and scope != node.name
        )
        facts.append(
            Fact(
                kind="pyspark.function_def",
                subject=subject,
                measures={"name_reference_count": references},
                attrs={
                    "def_kind": def_kind,
                    "enclosing": enclosing,
                    "decorators": [
                        name for name in map(_decorator_name, node.decorator_list) if name
                    ],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "exported": node.name in exported,
                },
                provenance=provenance,
            )
        )
    return facts


def _loop_and_callgraph_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: list[str], provenance: dict[str, Any]
) -> list[Fact]:
    facts: list[Fact] = []
    local_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.For | ast.AsyncFor | ast.While):
            contains_action = False
            contains_write = False
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                    if inner.func.attr in _ACTIONS:
                        contains_action = True
                    methods, _ = _chain_methods(inner)
                    if "write" in methods or "writeTo" in methods:
                        contains_write = True
            if contains_action or contains_write:
                facts.append(
                    Fact(
                        kind="pyspark.loop",
                        subject=_subject(node, path, ctx, lines),
                        measures={"loop_depth": ctx.loop_depth.get(id(node), 0) + 1},
                        attrs={
                            "contains_action": contains_action,
                            "contains_write": contains_write,
                        },
                        provenance=provenance,
                    )
                )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            callee = node.func.id
            caller = ctx.function.get(id(node), "")
            if caller and callee in local_functions and callee != caller:
                facts.append(
                    Fact(
                        kind="pyspark.callgraph_edge",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"caller": caller, "callee": callee},
                        provenance=provenance,
                    )
                )

    return facts


def extract_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo, ancorando o path relativo a `repo_root`.

    Le com `utf-8-sig`: remove um BOM UTF-8 se presente, e e no-op caso
    contrario. Sem isso um arquivo salvo com BOM falha o parse e o codigo
    PySpark valido dentro dele e reportado como blind spot por engano.
    """
    text = path.read_text(encoding="utf-8-sig")
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    return extract_source(text, rel.replace("\\", "/"))


def extract_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os .py sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico (permissao,
    encoding invalido, qualquer excecao inesperada) vira um unico Fact
    `pyspark.unresolved` para aquele arquivo, e a travessia continua. Perder
    os fatos de toda uma arvore por causa de um unico arquivo ruim seria o
    pior modo de falha possivel para um analisador.
    """
    facts: list[Fact] = []
    for py in iter_source_files(root, "*.py"):
        rel = str(py.relative_to(repo_root)) if repo_root else str(py)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_path(py, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            facts.append(
                Fact(
                    kind="pyspark.unresolved",
                    subject={
                        "type": "source_location",
                        "file": anchor,
                        "line": 0,
                        "col": 0,
                        "symbol": "",
                        "snippet": "",
                    },
                    attrs={"reason": "extraction_error", "detail": str(exc)},
                    provenance={
                        "artifact": anchor,
                        "artifact_sha256": "",
                        "extractor": EXTRACTOR_ID,
                    },
                )
            )
    return sort_facts(facts)
