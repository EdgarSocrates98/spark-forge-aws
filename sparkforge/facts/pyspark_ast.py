"""Extrator estatico de codigo PySpark.

NUNCA importa nem executa o codigo do alvo: `ast` da stdlib apenas. Importar um
modulo de job para inspecionar executaria codigo arbitrario do repositorio
analisado.

Tres passes: (1) mapa pai/escopo, (2) reconstrucao de cadeia, (3) emissao.
Nao aplica limiar, nao atribui severidade, nao ordena por importancia.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "pyspark_ast@0.1.0"

_PARTITION_METHODS = frozenset({"coalesce", "repartition", "repartitionByRange"})


class _Context:
    """Passe 1: mapa filho -> pai, escopo de funcao, profundidade de loop."""

    def __init__(self, tree: ast.AST) -> None:
        self.parent: dict[int, Any] = {}
        self.function: dict[int, str] = {}
        self.loop_depth: dict[int, int] = {}
        self._walk(tree, None, "", 0)

    def _walk(self, node: ast.AST, parent: ast.AST | None, symbol: str, depth: int) -> None:
        self.parent[id(node)] = parent
        self.function[id(node)] = symbol
        self.loop_depth[id(node)] = depth

        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol = node.name
        if isinstance(node, ast.For | ast.AsyncFor | ast.While):
            depth += 1

        for child in ast.iter_child_nodes(node):
            self._walk(child, node, symbol, depth)


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


def extract_source(source: str, path: str) -> list[Fact]:
    """Extrai Facts de `source`. `path` e usado como ancora e procedencia."""
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    provenance = {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
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

    ctx = _Context(tree)
    facts: list[Fact] = []

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

        if not isinstance(node.func, ast.Attribute):
            continue

        method = node.func.attr
        if method in _PARTITION_METHODS:
            facts.append(_partitioning_fact(node, method, path, ctx, lines, provenance))

    return sort_facts(facts)


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


def extract_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo, ancorando o path relativo a `repo_root`."""
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    return extract_source(text, rel.replace("\\", "/"))


def extract_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os .py sob `root`, em ordem deterministica de path."""
    facts: list[Fact] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        facts.extend(extract_path(py, repo_root))
    return sort_facts(facts)
