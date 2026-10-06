"""Avaliador de expressões do catálogo de regras.

Fronteira de segurança. O catálogo é dado editável, portanto é superfície de
execução. Whitelist de nós AST; nunca `eval`.
"""
from __future__ import annotations

import ast
import operator
from typing import Any

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

ALLOWED_ROOTS = frozenset({"measures", "attrs", "threshold"})

# O catalogo e dado editavel (YAML de terceiros pode ser colado nele), entao a
# recursao de _eval precisa de um teto explicito: sem isso, uma expressao com
# encadeamento profundo (ex.: milhares de "+ measures.a") estoura RecursionError
# em vez de ExprError, derrubando o processo chamador que so trata ExprError.
# 100 e bem acima do necessario: a regra mais profunda do catalogo real e uma
# unica divisao comparada a um limiar, profundidade bem abaixo de 10.
MAX_DEPTH = 100


class ExprError(ValueError):
    """Expressão inválida, insegura, ou com caminho ausente no contexto."""


def evaluate(expr: str, context: dict[str, Any]) -> Any:
    """Avalia `expr` contra `context`. Levanta ExprError em qualquer desvio."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ExprError(f"expressao invalida: {expr!r}: {exc}") from exc
    return _eval(tree.body, context, 0)


def _eval(node: ast.AST, ctx: dict[str, Any], depth: int) -> Any:
    if depth > MAX_DEPTH:
        raise ExprError(f"expressao aninhada demais (limite {MAX_DEPTH})")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str, bool)) or node.value is None:
            return node.value
        raise ExprError(f"constante nao permitida: {node.value!r}")

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _eval(node.operand, ctx, depth + 1)
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand, ctx, depth + 1)
        if isinstance(node.op, ast.UAdd):
            return +_eval(node.operand, ctx, depth + 1)
        raise ExprError("operador unario nao permitido")

    if isinstance(node, ast.BoolOp):
        values = [_eval(v, ctx, depth + 1) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)

    if isinstance(node, ast.BinOp):
        func = _BIN_OPS.get(type(node.op))
        if func is None:
            raise ExprError(f"operador binario nao permitido: {type(node.op).__name__}")
        left = _eval(node.left, ctx, depth + 1)
        right = _eval(node.right, ctx, depth + 1)
        try:
            return func(left, right)
        except ZeroDivisionError as exc:
            raise ExprError(f"divisao por zero em: {ast.dump(node)}") from exc

    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx, depth + 1)
        for op_node, comparator in zip(node.ops, node.comparators, strict=True):
            func = _CMP_OPS.get(type(op_node))
            if func is None:
                raise ExprError(f"comparador nao permitido: {type(op_node).__name__}")
            right = _eval(comparator, ctx, depth + 1)
            if not func(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Attribute):
        return _resolve_path(node, ctx)

    raise ExprError(f"no nao permitido: {type(node).__name__}")


def _resolve_path(node: ast.Attribute, ctx: dict[str, Any]) -> Any:
    parts = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        if current.attr.startswith("__"):
            raise ExprError(f"atributo dunder proibido: {current.attr}")
        parts.append(current.attr)
        current = current.value

    if not isinstance(current, ast.Name):
        raise ExprError(f"base de atributo nao permitida: {type(current).__name__}")
    if current.id not in ALLOWED_ROOTS:
        allowed = ", ".join(sorted(ALLOWED_ROOTS))
        raise ExprError(f"raiz nao permitida: {current.id} (permitidas: {allowed})")

    parts.append(current.id)
    parts.reverse()

    value: Any = ctx
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            path = ".".join(parts)
            raise ExprError(f"caminho ausente no contexto: {path}")
        value = value[part]
    return value
