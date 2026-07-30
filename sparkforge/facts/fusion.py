"""Fusao de facts: correlaciona `sql.projection`/`sql.predicate`
(`sparkforge/facts/sql_literal.py`) com `catalog.table_schema`
(`sparkforge/facts/catalog_schema.py`) pelo nome da tabela.

Isto NAO e um extrator no sentido dos outros modulos deste pacote: nao le
arquivo nenhum, nao faz parsing de texto SQL nem de JSON. E uma funcao pura
sobre Facts ja extraidos -- `fuse(facts) -> facts`. A razao de existir e o
motor de regras (`sparkforge/rules/engine.py::_condition_candidates`) so
avaliar `where`/`expr` contra o contexto de UM fact por vez, nunca combinar
`attrs` de dois facts diferentes numa condicao. `SF-ATH-001`, `SF-ATH-002` e
`SF-ATH-005` (`rules/catalog/athena.yaml`) precisam de uma resposta que
metade vem da query (texto SQL) e metade vem do catalogo (schema da tabela);
nenhum extrator sozinho tem as duas metades. Este modulo produz um fact NOVO
que junta as duas metades, para que o motor continue avaliando UM fact por
condicao -- a correlacao acontece aqui, antes do `judge`, nao dentro dele.
Ver `rules/engine.py::_evaluate_when` (docstring de `same_subject`) para o
precedente mais proximo: escopar condicoes por subject em vez de fundir facts
e a mesma filosofia -- o motor nunca aprende a combinar, quem combina e uma
etapa anterior.

## Design de `fuse`

`fuse(facts)` devolve a lista completa: os facts de entrada, MAIS os facts
`.enriched` (e `fusion.summary`) que consegue derivar, deduplicados por
`Fact.id` (que ja e content-addressed -- ver `findings/models.py::Fact.id`).
Devolver so os novos obrigaria quem chama a re-concatenar manualmente antes de
`judge`; devolver a uniao inteira significa que
`judge(fuse(facts), catalogo, runtime)` funciona direto, no mesmo lugar onde
facts de multiplas fontes ja se combinam antes do julgamento.

Dedup por id tambem e o que torna `fuse` idempotente: `fuse` so lê facts de
kind exatamente `sql.projection` / `sql.predicate` (nunca `.enriched`) para
gerar os enriquecidos, entao rodar `fuse` sobre a propria saida de `fuse`
recalcula os MESMOS facts (mesmo conteudo => mesmo id) a partir dos mesmos
originais, e a deduplicacao os funde num so. `fuse(fuse(facts))` nao produz
nenhum fact `.enriched` A MAIS que `fuse(facts)` -- ver teste dedicado em
`tests/test_facts_fusion.py::TestIdempotent`.

## Casamento de nome de tabela

SQL pode dizer `eventos` enquanto o catalogo diz `db.eventos`. A correlacao
tenta, em ordem:

1. Nome totalmente qualificado identico (case-insensitive) a uma tabela do
   catalogo.
2. Se isso falhar, o ULTIMO segmento (nome sem qualificador de banco) contra
   o ultimo segmento de cada nome do catalogo -- SOMENTE quando exatamente uma
   tabela do catalogo tem aquele nome sem qualificador. Se duas tabelas do
   catalogo compartilham o mesmo nome sem qualificador (`vendas.eventos` e
   `analytics.eventos`), o nome curto e ambiguo: NAO adivinha, conta como nao
   fundido. Adivinhar aqui correlacionaria uma query com a tabela errada e
   produziria um finding sobre uma tabela que a query nem toca -- pior que
   silencio.

## `type_mismatch`: conservador por desenho

So afirma `True` quando o literal do filtro e (a) uma string entre aspas
comparada com coluna de tipo numerico (`bigint`/`int`/`double`/etc.), ou (b)
um numero sem aspas comparado com coluna de tipo string (`string`/`varchar`/
`char`). Fora desses dois casos -- tipo da coluna desconhecido, ou o literal
nao se classifica claramente como string/numero (ex.: `TRUE`, uma subquery,
uma chamada de funcao) -- fica `None`. Um `type_mismatch: True` errado manda o
operador procurar um bug que nao existe; `None` e sempre a resposta segura
quando a evidencia e insuficiente.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "fusion@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sql.projection.enriched",
        "sql.predicate.enriched",
        "sql.predicate.partition_filter",
        "fusion.summary",
    }
)

_NUMERIC_TYPES = frozenset(
    {
        "bigint", "int", "integer", "smallint", "tinyint", "long",
        "double", "float", "decimal", "real", "numeric",
    }
)
_STRING_TYPES = frozenset({"string", "varchar", "char"})

_QUOTED_RE = re.compile(r"^'([^']*)'$|^\"([^\"]*)\"$")
_NUMERIC_LITERAL_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def _norm(name: str) -> str:
    return name.strip().lower()


def _is_quoted_string_literal(value: str) -> bool:
    return bool(_QUOTED_RE.match(value.strip()))


def _is_unquoted_numeric_literal(value: str) -> bool:
    return bool(_NUMERIC_LITERAL_RE.match(value.strip()))


def _infer_type_mismatch(value: str, declared_type: str | None) -> bool | None:
    """Ver secao "type_mismatch: conservador por desenho" na docstring do modulo."""
    if not declared_type:
        return None
    declared = declared_type.strip().lower()
    if _is_quoted_string_literal(value):
        if declared in _NUMERIC_TYPES:
            return True
        if declared in _STRING_TYPES:
            return False
        return None
    if _is_unquoted_numeric_literal(value):
        if declared in _STRING_TYPES:
            return True
        if declared in _NUMERIC_TYPES:
            return False
        return None
    return None


def _catalog_lookup(facts: Sequence[Fact]) -> tuple[dict[str, Fact], dict[str, list[str]]]:
    """`(por_nome_completo, por_nome_curto)`. `por_nome_curto[bare]` lista as
    chaves de nome completo (deduplicadas) que compartilham aquele ultimo
    segmento -- mais de uma entrada e o sinal de ambiguidade que
    `_resolve_table` usa para recusar adivinhar."""
    by_full: dict[str, Fact] = {}
    by_bare: dict[str, list[str]] = {}
    for fact in facts:
        if fact.kind != "catalog.table_schema":
            continue
        table = fact.attrs.get("table")
        if not isinstance(table, str) or not table.strip():
            continue
        key = _norm(table)
        by_full.setdefault(key, fact)
        bare = _norm(table.rsplit(".", 1)[-1])
        bucket = by_bare.setdefault(bare, [])
        if key not in bucket:
            bucket.append(key)
    return by_full, by_bare


def _resolve_table(
    sql_table: str | None, by_full: dict[str, Fact], by_bare: dict[str, list[str]]
) -> Fact | None:
    if not sql_table:
        return None
    key = _norm(sql_table)
    if key in by_full:
        return by_full[key]
    bare = _norm(sql_table.rsplit(".", 1)[-1])
    candidates = by_bare.get(bare, [])
    if len(candidates) == 1:
        return by_full[candidates[0]]
    return None


def _fused_provenance(fact: Fact) -> dict[str, Any]:
    return {
        "artifact": fact.provenance.get("artifact", ""),
        "artifact_sha256": "",
        "extractor": EXTRACTOR_ID,
    }


def _fused_from(*facts: Fact) -> list[str]:
    return sorted({f.id for f in facts})


def _enrich_projection(fact: Fact, catalog_fact: Fact) -> Fact:
    attrs = dict(fact.attrs)
    attrs["table_format_columnar"] = catalog_fact.attrs.get("columnar")
    attrs["fused_from"] = _fused_from(fact, catalog_fact)
    return Fact(
        kind="sql.projection.enriched",
        subject=fact.subject,
        measures=dict(fact.measures),
        attrs=attrs,
        provenance=_fused_provenance(fact),
    )


def _enrich_predicate(fact: Fact, catalog_fact: Fact) -> tuple[Fact, Fact | None]:
    column = fact.attrs.get("column", "")
    partition_keys = {_norm(pk) for pk in (catalog_fact.attrs.get("partition_keys") or [])}
    on_partition = _norm(column) in partition_keys
    declared_type = (catalog_fact.attrs.get("column_types") or {}).get(column)
    mismatch = _infer_type_mismatch(fact.attrs.get("value", ""), declared_type)

    attrs = dict(fact.attrs)
    attrs["on_partition_column"] = on_partition
    attrs["type_mismatch"] = mismatch
    attrs["fused_from"] = _fused_from(fact, catalog_fact)
    enriched = Fact(
        kind="sql.predicate.enriched",
        subject=fact.subject,
        measures=dict(fact.measures),
        attrs=attrs,
        provenance=_fused_provenance(fact),
    )

    partition_filter = None
    if on_partition:
        partition_filter = Fact(
            kind="sql.predicate.partition_filter",
            subject=fact.subject,
            attrs={
                "column": column,
                "table": catalog_fact.attrs.get("table"),
                "fused_from": _fused_from(fact, catalog_fact),
            },
            provenance=_fused_provenance(fact),
        )
    return enriched, partition_filter


def _summary_subject() -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": "<fusion>",
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def fuse(facts: Sequence[Fact]) -> list[Fact]:
    """Correlaciona `sql.projection`/`sql.predicate` com `catalog.table_schema`
    pelo nome da tabela e devolve `facts` mais o que conseguiu derivar. Ver
    docstring do modulo para o design completo (por que devolve a uniao, como
    a idempotencia e garantida, como a ambiguidade de nome curto e tratada).
    """
    facts = list(facts)
    by_full, by_bare = _catalog_lookup(facts)

    new_facts: list[Fact] = []
    enriched_count = 0
    unmatched_projection = 0
    unmatched_predicate = 0

    for fact in facts:
        if fact.kind == "sql.projection":
            catalog_fact = _resolve_table(fact.attrs.get("table"), by_full, by_bare)
            if catalog_fact is None:
                unmatched_projection += 1
                continue
            new_facts.append(_enrich_projection(fact, catalog_fact))
            enriched_count += 1

        elif fact.kind == "sql.predicate":
            catalog_fact = _resolve_table(fact.attrs.get("table"), by_full, by_bare)
            if catalog_fact is None:
                unmatched_predicate += 1
                continue
            enriched, partition_filter = _enrich_predicate(fact, catalog_fact)
            new_facts.append(enriched)
            enriched_count += 1
            if partition_filter is not None:
                new_facts.append(partition_filter)

    summary = Fact(
        kind="fusion.summary",
        subject=_summary_subject(),
        measures={
            "enriched_count": enriched_count,
            "unmatched_projection_count": unmatched_projection,
            "unmatched_predicate_count": unmatched_predicate,
            "tables_known": len(by_full),
        },
        provenance={"artifact": "", "artifact_sha256": "", "extractor": EXTRACTOR_ID},
    )
    new_facts.append(summary)

    # Dedup por id (content-addressed): garante a uniao sem duplicata e e a
    # base da idempotencia -- ver docstring do modulo.
    combined: dict[str, Fact] = {f.id: f for f in facts}
    for fact in new_facts:
        combined[fact.id] = fact

    unknown = {f.kind for f in new_facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(combined.values())
