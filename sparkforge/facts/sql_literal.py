"""Extrator de Facts a partir de texto SQL: literais `spark.sql("...")` em
codigo PySpark, e arquivos `.sql` avulsos.

Deliberadamente limitado: regex e varredura de token, NUNCA uma gramatica
SQL. Nao ha dependencia de parser SQL nas dependencias do projeto, e
adicionar uma nao se justifica para os poucos padroes que as cinco regras
`SF-ATH-*` (`rules/catalog/athena.yaml`) precisam -- mesma decisao de escopo
de `terraform.py` para HCL. O que este extrator entende:

  - `SELECT <projecao> FROM <resto>`: primeira ocorrencia de SELECT...FROM no
    texto. CTE (`WITH x AS (SELECT ...) SELECT ...`) ou subquery na propria
    lista de projecao casam no SELECT/FROM errado (o mais interno) -- residual
    conhecido de nao ter gramatica; o sintoma e um `column_count` ou `star`
    que descreve a subquery, nao a query externa.
  - `WHERE <clausula>` ate o proximo `GROUP BY`/`ORDER BY`/`HAVING`/`QUALIFY`/
    `LIMIT` ou fim do texto, dividida em fragmentos por `AND` de nivel
    superior (fora de parenteses/aspas). Cada fragmento que casa
    `coluna operador valor` (`=`, `!=`, `<>`, `<`, `<=`, `>`, `>=`) vira um
    `sql.predicate`. `OR`, subquery em predicado, `IN (...)`, `BETWEEN`,
    `LIKE` e qualquer outra forma nao suportada caem em `sql.unresolved`
    com `reason: unparsed_clause` -- nunca um predicado adivinhado.

O que este extrator NUNCA sabe, por nao ter acesso a nada alem do texto SQL:
se a tabela referenciada e colunar (Parquet/ORC) ou por linha (CSV/JSON); se
uma coluna filtrada e a coluna de particao da tabela; se o tipo do literal do
filtro bate com o tipo declarado da coluna. As tres exigem conhecimento de
schema do catalogo (Glue Data Catalog / Iceberg), que nenhum extrator desta
fase produz. `sql.projection.attrs.table_format_columnar`,
`sql.predicate.attrs.on_partition_column` e
`sql.predicate.attrs.type_mismatch` sao sempre `None` -- nunca adivinhados.
Ver `rules/catalog/athena.yaml`: SF-ATH-001, SF-ATH-002 e SF-ATH-005 estao
marcadas `blocked_on` por esse motivo exato (ver comentario no catalogo).

Como `pyspark_ast.py`/`terraform.py`: extrator puro e deterministico. Nunca
aplica limiar, nunca atribui severidade.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "sql_literal@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sql.projection",
        "sql.predicate",
        "sql.unresolved",
        "sql.analyzed",
    }
)

_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE_RE = re.compile(r"--[^\n]*")
_SELECT_FROM_RE = re.compile(r"\bSELECT\b(.*?)\bFROM\b", re.IGNORECASE | re.DOTALL)
_WHERE_RE = re.compile(
    r"\bWHERE\b(.*?)(?:\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b|\bQUALIFY\b|\bLIMIT\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)
_COMMA_RE = re.compile(r",")
_AND_RE = re.compile(r"\bAND\b", re.IGNORECASE)
_OR_RE = re.compile(r"\bOR\b", re.IGNORECASE)
_PRED_RE = re.compile(
    r'^\s*("[^"]+"|`[^`]+`|[A-Za-z_][\w.\[\]]*)\s*(<=|>=|<>|!=|=|<|>)\s*(.+?)\s*$'
)


def _strip_comments(sql: str) -> str:
    sql = _COMMENT_BLOCK_RE.sub(" ", sql)
    return _COMMENT_LINE_RE.sub("", sql)


def _split_top_level(text: str, sep_re: re.Pattern[str]) -> list[str]:
    """Divide `text` em `sep_re`, ignorando separador dentro de parenteses ou
    de string entre aspas. Sem isso, `SUM(a, b)` na lista de projecao ou
    `col = 'a AND b'` no predicado quebrariam em pontos que nao sao
    delimitadores reais."""
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    start = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0:
            match = sep_re.match(text, i)
            if match:
                parts.append(text[start:i])
                i = match.end()
                start = i
                continue
        i += 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _strip_identifier_quotes(column: str) -> str:
    return column.strip('"`')


def _sql_subject(path: str, line: int) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _scan_sql(
    sql: str, path: str, line: int
) -> tuple[list[Fact], dict[str, int], dict[str, Any]]:
    """Nucleo comum de `extract_sql` e `extract_sql_from_pyspark`: varre um
    unico texto SQL e devolve `(facts, counts, provenance)`, SEM o Fact
    sentinela `sql.analyzed` -- os dois chamadores publicos o constroem, um
    por unidade de analise (arquivo `.sql`, ou call `spark.sql(...)`
    individual para o primeiro; um agregado por arquivo inteiro para o
    segundo -- ver docstring de `extract_sql_from_pyspark`)."""
    provenance = {
        "artifact": path,
        "artifact_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }
    cleaned = _strip_comments(sql)
    subject = _sql_subject(path, line)

    facts: list[Fact] = []
    counts = {"projection_count": 0, "predicate_count": 0, "unresolved_count": 0}

    select_match = _SELECT_FROM_RE.search(cleaned)
    if select_match is None:
        facts.append(
            Fact(
                kind="sql.unresolved",
                subject=subject,
                attrs={"reason": "unparsed_clause", "detail": "SELECT ... FROM nao encontrado"},
                provenance=provenance,
            )
        )
        counts["unresolved_count"] += 1
    else:
        projection_text = select_match.group(1).strip()
        items = _split_top_level(projection_text, _COMMA_RE)
        star = projection_text == "*" or any(
            item == "*" or item.endswith(".*") for item in items
        )
        attrs: dict[str, Any] = {
            "star": star,
            "has_limit": bool(_LIMIT_RE.search(cleaned)),
            # Formato de armazenamento e propriedade da TABELA, nunca da
            # QUERY -- texto SQL nao carrega essa informacao. Ver docstring
            # do modulo e o `blocked_on` de SF-ATH-001 no catalogo.
            "table_format_columnar": None,
        }
        measures: dict[str, Any] = {}
        if not star and items:
            measures["column_count"] = len(items)
        facts.append(
            Fact(
                kind="sql.projection",
                subject=subject,
                attrs=attrs,
                measures=measures,
                provenance=provenance,
            )
        )
        counts["projection_count"] += 1

    where_match = _WHERE_RE.search(cleaned)
    if where_match is not None:
        clause_text = where_match.group(1).strip()
        for fragment in _split_top_level(clause_text, _AND_RE):
            # `OR` nao e suportado (sem gramatica booleana): um fragmento que
            # contem `OR` de nivel superior e uma expressao composta, nunca
            # uma unica comparacao -- cai em unparsed_clause em vez de vazar
            # como um predicado com valor contendo "... OR coluna = valor".
            has_or = len(_split_top_level(fragment, _OR_RE)) != 1
            pred_match = None if has_or else _PRED_RE.match(fragment)
            if pred_match is None:
                facts.append(
                    Fact(
                        kind="sql.unresolved",
                        subject=subject,
                        attrs={"reason": "unparsed_clause", "detail": fragment[:200]},
                        provenance=provenance,
                    )
                )
                counts["unresolved_count"] += 1
                continue
            column, operator, value = pred_match.groups()
            facts.append(
                Fact(
                    kind="sql.predicate",
                    subject=subject,
                    attrs={
                        "column": _strip_identifier_quotes(column),
                        "operator": operator,
                        "value": value.strip(),
                        # Precisam do schema da tabela (qual coluna e a
                        # particao; o tipo declarado da coluna), que este
                        # extrator nao tem. Ver docstring do modulo e o
                        # `blocked_on` de SF-ATH-002/SF-ATH-005 no catalogo.
                        "on_partition_column": None,
                        "type_mismatch": None,
                    },
                    provenance=provenance,
                )
            )
            counts["predicate_count"] += 1

    return facts, counts, provenance


def _sentinel(
    subject: dict[str, Any], measures: dict[str, int], provenance: dict[str, Any]
) -> Fact:
    return Fact(
        kind="sql.analyzed", subject=subject, measures=dict(measures), provenance=provenance
    )


def extract_sql(sql: str, path: str, line: int = 0) -> list[Fact]:
    """Extrai Facts de um unico texto SQL. `line` ancora onde esse texto
    comeca na fonte (0 quando desconhecido/nao aplicavel)."""
    facts, counts, provenance = _scan_sql(sql, path, line)
    facts.append(_sentinel(_sql_subject(path, line), {**counts, "statement_count": 1}, provenance))

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_sql_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.sql`, ancorando o path relativo a `repo_root`.

    Falha ao abrir o arquivo vira um unico Fact `sql.unresolved` com reason
    "read_error", nunca uma excecao que derruba quem chamou -- mesma
    convencao de `terraform.extract_terraform_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [
            Fact(
                kind="sql.unresolved",
                subject=_sql_subject(anchor, 0),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
            )
        ]
    return extract_sql(text, anchor, line=1)


def _is_spark_sql_call(node: ast.Call) -> bool:
    """True para `spark.sql(...)`, a forma literal que o enunciado pede.

    Deliberadamente restrito a um unico nivel (`spark.sql`, nao
    `self.spark.sql` ou `glueContext.spark_session.sql`): a variavel de
    sessao Spark chamada exatamente `spark` e a convencao dominante em
    codigo Glue/PySpark real. Uma variante com outro nome de raiz nao e
    reconhecida -- nao vira Fact nenhum (nem `sql.unresolved`), porque nem
    sequer identificamos que o call e uma execucao de SQL.
    """
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "sql"
        and isinstance(func.value, ast.Name)
        and func.value.id == "spark"
    )


def extract_sql_from_pyspark(source: str, path: str) -> list[Fact]:
    """Encontra chamadas `spark.sql("<literal>")` em codigo PySpark via `ast`,
    ancora cada uma na sua linha real, e roda `extract_sql` sobre o literal.

    Um argumento nao-literal (f-string, variavel, concatenacao) vira
    `sql.unresolved` com `reason: non_literal_sql` -- mesma honestidade de
    `pyspark.unresolved`: o extrator nunca segue uma referencia para
    descobrir o texto real.

    Emite um UNICO Fact `sql.analyzed` por arquivo, agregando todas as
    chamadas `spark.sql(...)` encontradas (cada uma podendo contribuir
    projection/predicate/unresolved proprios) -- nao um por chamada. Espelha
    `pyspark.module_analyzed`: a sentinela prova que o arquivo INTEIRO foi
    varrido, nao so uma chamada isolada dentro dele.
    """
    provenance = {
        "artifact": path,
        "artifact_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "extractor": EXTRACTOR_ID,
    }

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            Fact(
                kind="sql.unresolved",
                subject=_sql_subject(path, exc.lineno or 0),
                attrs={"reason": "read_error", "detail": str(exc.msg)},
                provenance=provenance,
            )
        ]

    facts: list[Fact] = []
    totals = {
        "statement_count": 0,
        "projection_count": 0,
        "predicate_count": 0,
        "unresolved_count": 0,
    }

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_spark_sql_call(node)):
            continue

        call_line = getattr(node, "lineno", 0)
        arg = node.args[0] if node.args else None
        literal = (
            arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None
        )

        if literal is None:
            facts.append(
                Fact(
                    kind="sql.unresolved",
                    subject=_sql_subject(path, call_line),
                    attrs={"reason": "non_literal_sql"},
                    provenance=provenance,
                )
            )
            totals["unresolved_count"] += 1
            continue

        sub_facts, counts, _ = _scan_sql(literal, path, call_line)
        facts.extend(sub_facts)
        totals["statement_count"] += 1
        for key in ("projection_count", "predicate_count", "unresolved_count"):
            totals[key] += counts[key]

    facts.append(_sentinel(_sql_subject(path, 0), totals, provenance))

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)
