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


class _ModuleIndex(NamedTuple):
    """Linhas, por variavel-alvo, dos eventos que datam um check.

    O motor de regras nao correlaciona dois facts -- `engine._condition_candidates`
    avalia um fact por vez e `engine._absent_satisfied` compara so `kind` -- entao
    quem enxerga o modulo inteiro e quem responde. Este indice e o que o extrator
    enxerga e o catalogo nao enxergaria.
    """

    writes: dict[str, set[int]]
    persists: dict[str, set[int]]
    actions: dict[str, set[int]]


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


def _lines_by_target(
    tree: ast.AST, attrs: frozenset[str], methods: frozenset[str]
) -> dict[str, set[int]]:
    """Linhas em que cada variavel-alvo aparece na raiz de `df.<attr>` ou de
    `df....<method>()`.

    Guarda o CONJUNTO de linhas, nao a primeira encontrada: `ast.walk` percorre
    por nivel, entao um write dentro de um laco e visitado depois de um write no
    corpo do modulo, e "a primeira linha vista" nao e a primeira linha do
    arquivo. Quem consome escolhe o extremo que lhe interessa.
    """
    found: dict[str, set[int]] = {}
    for node in ast.walk(tree):
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


def _module_index(tree: ast.AST) -> _ModuleIndex:
    return _ModuleIndex(
        writes=_lines_by_target(tree, _WRITE_ATTRS, frozenset()),
        persists=_lines_by_target(tree, frozenset(), _PERSIST_METHODS),
        # `.write` tambem e action: e o que dispara o trabalho de publicar.
        actions=_lines_by_target(tree, _WRITE_ATTRS, _ACTION_METHODS),
    )


def _position_vs_write(target: str, line: int, writes: dict[str, set[int]]) -> str:
    """Tres valores, nunca um booleano.

    `no_write_in_module` e o modulo que valida e nao escreve -- uma biblioteca de
    validacao, um job de auditoria. Achatar isso em `before_write` afirmaria uma
    ordem que o arquivo nao contem.
    """
    lines = writes.get(target)
    if not lines:
        return "no_write_in_module"
    return "after_write" if line > min(lines) else "before_write"


def _handmade_check(
    node: ast.Call, path: str, index: _ModuleIndex, provenance: dict[str, Any]
) -> Fact | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "count":
        return None
    target, methods = _chain_root(node)
    if not any(m in _HANDMADE_GATES for m in methods):
        return None
    if target is None or any(m in _SOURCE_TERMINALS for m in methods):
        return _unresolved(
            path, node.lineno, "unresolved_target", provenance, check_type="count_of_violations"
        )
    line = node.lineno
    return Fact(
        kind="dq.check",
        subject=_subject(path, line),
        measures={"line": line},
        attrs={
            "framework": "handmade",
            "check_type": "count_of_violations",
            "target": target,
            "position_vs_write": _position_vs_write(target, line, index.writes),
            "target_persisted": any(n < line for n in index.persists.get(target, ())),
            # Estritamente posterior: a linha do proprio check tem a action que
            # o define -- o `count()` -- e o check nao e action depois de si.
            "action_after_check": any(n > line for n in index.actions.get(target, ())),
            # Todo check artesanal paga varredura propria: cada `count()` e uma
            # passada sobre o alvo, sem compartilhamento com os outros checks do
            # modulo. So a `VerificationSuite` do Deequ agrupa agregacoes
            # (knowledge/dq/validation-frameworks.md, §2.3).
            "shares_scan": False,
        },
        provenance=provenance,
    )


def extract_data_quality(tree: ast.AST, path: str, artifact_sha256: str = "") -> list[Fact]:
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    index = _module_index(tree)
    facts: list[Fact] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fact = _handmade_check(node, path, index, provenance)
            if fact is not None:
                facts.append(fact)

    # Segundo passe: quantos checks ha sobre o mesmo alvo so e conhecido depois
    # de a travessia terminar.
    per_target = Counter(f.attrs["target"] for f in facts if f.kind == "dq.check")
    facts = [
        replace(f, measures={**f.measures, "checks_on_target": per_target[f.attrs["target"]]})
        if f.kind == "dq.check"
        else f
        for f in facts
    ]

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
        return [_unresolved(anchor, 0, "read_error", empty, detail=str(exc))]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance_sha = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            _unresolved(
                anchor, exc.lineno or 0, "syntax_error", provenance_sha, detail=str(exc.msg)
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
                    "read_error",
                    {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                    detail=str(exc),
                )
            )
    return sort_facts(facts)
