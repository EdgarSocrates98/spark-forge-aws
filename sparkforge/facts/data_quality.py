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
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

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

# Metodos que constroem um DataFrame A PARTIR da raiz da cadeia. Quando o
# primeiro elo e um destes, a raiz e a sessao (ou o reader), NAO o dado
# validado: em `spark.table("t").filter(...).count()` o alvo do check e um
# DataFrame anonimo, e `spark` seria um alvo adivinhado -- `SF-DQ-001` passaria
# a comparar a linha deste check com o write de qualquer outro dado que tambem
# saia de `spark`. Por isso a cadeia que comeca aqui vira `dq.unresolved`,
# contada, e nunca um `dq.check` com alvo errado. Mesma disciplina de nomeacao
# por forma que `_READ_TERMINALS` usa em `pyspark_ast.py`.
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
    }
)


def _subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _unresolved(
    path: str, line: int, reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="dq.unresolved",
        subject=_subject(path, line),
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


def _handmade_check(node: ast.Call, path: str, provenance: dict[str, Any]) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "count":
        return None
    target, methods = _chain_root(node)
    if not any(m in _HANDMADE_GATES for m in methods):
        return None
    if target is None or (methods and methods[0] in _SOURCE_TERMINALS):
        return _unresolved(
            path, node.lineno, "unresolved_target", provenance, check_type="count_of_violations"
        )
    return Fact(
        kind="dq.check",
        subject=_subject(path, node.lineno),
        measures={"line": node.lineno},
        attrs={"framework": "handmade", "check_type": "count_of_violations", "target": target},
        provenance=provenance,
    )


def extract_data_quality(tree: ast.AST, path: str, artifact_sha256: str = "") -> list[Fact]:
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fact = _handmade_check(node, path, provenance)
            if fact is not None:
                facts.append(fact)

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
        return [
            Fact(
                kind="dq.unresolved",
                subject=_subject(anchor),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance=empty,
            )
        ]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance_sha = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            Fact(
                kind="dq.unresolved",
                subject=_subject(anchor, exc.lineno or 0),
                attrs={"reason": "syntax_error", "detail": str(exc.msg)},
                provenance=provenance_sha,
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
                Fact(
                    kind="dq.unresolved",
                    subject=_subject(anchor),
                    attrs={"reason": "read_error", "detail": str(exc)},
                    provenance={
                        "artifact": anchor,
                        "artifact_sha256": "",
                        "extractor": EXTRACTOR_ID,
                    },
                )
            )
    return sort_facts(facts)
