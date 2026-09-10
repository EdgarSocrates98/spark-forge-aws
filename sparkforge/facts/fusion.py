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

from sparkforge.facts.lakeformation import EMITTED_KINDS as LF_EMITTED_KINDS
from sparkforge.facts.lakeformation import build_lakeformation
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "fusion@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sql.projection.enriched",
        "sql.predicate.enriched",
        "sql.predicate.partition_filter",
        "sql.write_statement.enriched",
        "iceberg.library_conflict",
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


# As tres superficies de conf, e o rotulo de procedencia de cada uma. Mesma
# tabela de `sparkforge/facts/lakeformation.py`, e por uma razao que vale
# repetir: quem responde "esta sessao declara a extensao do Iceberg?" nao e o
# texto SQL nem o dump de catalogo -- e a configuracao, e ela chega por tres
# caminhos diferentes.
_CONF_KINDS_FUSION = {
    "spark.conf_effective": "event_log",
    "tf.spark_conf": "terraform",
    "pyspark.conf_set": "code",
}

_EXTENSIONS_KEY = "spark.sql.extensions"
_ICEBERG_EXTENSIONS = "IcebergSparkSessionExtensions"

# As operacoes que a documentacao do Iceberg marca com "Requires Iceberg Spark
# extensions" na tabela de suporte de `spark-writes`. `insert_into` e
# `insert_overwrite` NAO estao aqui: a mesma tabela as marca so com
# `storeAssignmentPolicy=ANSI`, que e default desde o Spark 3.0.
_EXIGEM_EXTENSAO = frozenset({"merge_into", "update", "delete_from"})


def _extensoes_do_iceberg(facts: Sequence[Fact]) -> tuple[bool | None, str]:
    """`(declarada, procedencia)` para `spark.sql.extensions`.

    TERNARIO, e o terceiro estado e o que separa "ninguem declarou" de "ninguem
    mediu": `None` quando NENHUMA das tres superficies de conf apareceu no case
    -- ali o motor nao sabe nada sobre a sessao, e afirmar `False` seria inventar
    ausencia a partir de ausencia de artefato. `False` so quando alguma
    superficie foi lida e a chave nao estava nela.
    """
    viu_superficie = False
    for fact in facts:
        origem = _CONF_KINDS_FUSION.get(fact.kind)
        if origem is None:
            continue
        viu_superficie = True
        attrs = fact.attrs or {}
        if (attrs or {}).get("redacted"):
            continue
        if str(attrs.get("key", "")) != _EXTENSIONS_KEY:
            continue
        if _ICEBERG_EXTENSIONS in str(attrs.get("value", "")):
            return True, origem
    return (False, "conf_lida_sem_a_chave") if viu_superficie else (None, "sem_superficie_de_conf")


# A coordenada Maven do runtime do Iceberg, como ela aparece em
# `spark.jars.packages`. O grupo captura a VERSAO.
_ICEBERG_COORD = re.compile(
    r"org\.apache\.iceberg:iceberg-spark-runtime-[\d.]+_[\d.]+:([\w.\-]+)"
)

# A chave que declara a ordem do classpath no Glue. Sem ela o jar do usuario vem
# DEPOIS do embarcado, e qual das duas versoes vence deixa de ser adivinhavel.
_USER_JARS_FIRST = "--user-jars-first"


def _iceberg_declarado(facts: Sequence[Fact]) -> tuple[str, str, str]:
    """`(versao, origem, ancora)` da biblioteca Iceberg que o job DECLARA instalar.

    Le `spark.jars.packages` das tres superficies de conf. `("", "", "")` quando
    nenhuma o declara -- e isso NAO significa que o job usa a embarcada por
    escolha; significa que ninguem declarou nada.

    IMPORTANTE, e e o limite deste fact: `spark.jars.packages` e DECLARACAO, nao
    classpath em execucao. O veto `V-ICE-2` pedia a versao da biblioteca EM
    EXECUCAO, e essa continua sem produtor. O que este par fecha e a pergunta
    vizinha, e mais acionavel: "o job declara uma versao diferente da que o
    runtime embarca?"
    """
    for fact in facts:
        origem = _CONF_KINDS_FUSION.get(fact.kind)
        if origem is None:
            continue
        attrs = fact.attrs or {}
        if (attrs or {}).get("redacted"):
            continue
        if str(attrs.get("key", "")) != "spark.jars.packages":
            continue
        casou = _ICEBERG_COORD.search(str(attrs.get("value", "")))
        if casou:
            return casou.group(1), origem, str((fact.subject or {}).get("symbol", ""))
    return "", "", ""


def _user_jars_first(facts: Sequence[Fact]) -> bool | None:
    """Ternario: `True`/`False` quando `tf.attribute` foi lido, `None` sem ele."""
    viu = False
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        attrs = fact.attrs or {}
        if str(attrs.get("block", "")) != "default_arguments":
            continue
        viu = True
        if str(attrs.get("key", "")) == _USER_JARS_FIRST:
            return str(attrs.get("value", "")).lower() == "true"
    return False if viu else None


def _iceberg_embarcado(facts: Sequence[Fact]) -> str:
    """A versao de Iceberg que o runtime embarca, derivada de `glue_version`.

    DUAS TENTATIVAS FALHARAM ANTES DESTA, e as duas do mesmo jeito -- lendo um
    fact que nao existe:

      1. `env.runtime` -- kind que nunca existiu neste repositorio;
      2. `env.runtime_signal` com `component: iceberg` -- MEDIDO: `detect_runtime`
         emite sinal so para `spark`. A versao de Iceberg vive em
         `RuntimeContext.iceberg` e NAO vira fact.

    A terceira le a mesma FONTE que `detect_runtime` usa -- a `GLUE_MATRIX` --
    a partir do `glue_version` que `tf.attribute` ja traz. Sem mudar assinatura
    de `fuse` e sem mover golden nenhum.

    `""` quando o Terraform nao declara `glue_version`, quando o valor nao e
    literal (`var.gv`), ou quando a versao nao esta na matriz. Nos tres casos a
    comparacao NAO acontece -- comparar contra `""` produziria conflito com tudo.
    """
    from sparkforge.facts.runtime_matrix import load as load_matrix

    versoes = {
        str((f.attrs or {}).get("value", ""))
        for f in facts
        if f.kind == "tf.attribute" and str((f.attrs or {}).get("key", "")) == "glue_version"
    }
    versoes.discard("")
    if len(versoes) != 1:
        return ""
    try:
        matriz = load_matrix()
    except Exception:  # noqa: BLE001 - matriz indisponivel nao derruba a fusao (regra 27)
        return ""
    return str((matriz.get(versoes.pop()) or {}).get("iceberg", "") or "")


def _conflito_de_iceberg(facts: Sequence[Fact], runtime_iceberg: str) -> list[Fact]:
    """Um fact quando o job declara versao de Iceberg e o runtime embarca outra.

    Nao emite nada quando o job nao declara, nem quando a versao embarcada nao e
    conhecida -- comparar contra `""` produziria conflito com tudo.
    """
    declarada, origem, ancora = _iceberg_declarado(facts)
    if not declarada or not runtime_iceberg:
        return []
    if declarada == runtime_iceberg:
        return []
    return [
        Fact(
            kind="iceberg.library_conflict",
            subject={
                "type": "source_location" if origem == "code" else "tf_resource",
                "file": "",
                "line": 0,
                "col": 0,
                "symbol": ancora,
                "snippet": "",
            },
            attrs={
                "declared_version": declarada,
                "runtime_version": runtime_iceberg,
                "declared_in": origem,
                # TERNARIO. Sem `tf.attribute` lido, ninguem sabe a ordem -- e
                # dizer `False` ali seria afirmar que o embarcado vence.
                "user_jars_first": _user_jars_first(facts),
                # O PREDICADO DERIVADO, e a regra 33 do `CLAUDE.md` e por que ele
                # existe: `where` compara igualdade, e "a ordem NAO esta
                # declarada" precisa juntar dois estados do ternario -- `false`
                # (lido e a chave ausente) e `null` (nao lido). Os dois dizem a
                # mesma coisa para quem vai agir: o job nao declara qual jar
                # vence. Sem este campo a regra precisaria de `any` sobre dois
                # `where`, e a primeira versao dela disparava so no `null` --
                # deixando de fora o caso MAIS comum, que e o `false`.
                "order_declared": _user_jars_first(facts) is True,
                "extractor": EXTRACTOR_ID,
            },
            provenance={"artifact": "", "artifact_sha256": "", "extractor": EXTRACTOR_ID},
        )
    ]


def _enrich_write_statement(
    fact: Fact, declarada: bool | None, procedencia: str
) -> Fact:
    attrs = dict(fact.attrs or {})
    attrs["iceberg_extensions_declared"] = declarada
    attrs["iceberg_extensions_source"] = procedencia
    attrs["requires_iceberg_extensions"] = attrs.get("operation") in _EXIGEM_EXTENSAO
    attrs["extractor"] = EXTRACTOR_ID
    return Fact(
        kind="sql.write_statement.enriched",
        subject=dict(fact.subject or {}),
        attrs=attrs,
        measures=dict(fact.measures or {}),
        provenance=dict(fact.provenance or {}),
    )


def fuse(facts: Sequence[Fact]) -> list[Fact]:
    """Correlaciona `sql.projection`/`sql.predicate` com `catalog.table_schema`
    pelo nome da tabela e devolve `facts` mais o que conseguiu derivar. Ver
    docstring do modulo para o design completo (por que devolve a uniao, como
    a idempotencia e garantida, como a ambiguidade de nome curto e tratada).
    """
    facts = list(facts)
    by_full, by_bare = _catalog_lookup(facts)
    extensoes, extensoes_origem = _extensoes_do_iceberg(facts)

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

        elif fact.kind == "sql.write_statement":
            # Nao depende de catalogo: o que falta ao statement e propriedade da
            # SESSAO, e por isso ele nao entra na contagem de `unmatched_*` nem
            # pode ficar de fora quando a tabela e desconhecida.
            new_facts.append(_enrich_write_statement(fact, extensoes, extensoes_origem))
            enriched_count += 1

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
    # A versao embarcada vem de um fact de deteccao de runtime quando ele existe
    # no case. Sem ele, `_conflito_de_iceberg` nao emite -- comparar contra `""`
    # produziria conflito com tudo.
    new_facts.extend(_conflito_de_iceberg(facts, _iceberg_embarcado(facts)))

    combined: dict[str, Fact] = {f.id: f for f in facts}
    for fact in new_facts:
        combined[fact.id] = fact

    unknown = {f.kind for f in new_facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    # `lakeformation.*` deriva AQUI pela mesma razao que este modulo existe, e a
    # razao esta no primeiro paragrafo do docstring: o motor de regras avalia UM
    # fact por condicao e nunca combina `attrs` de dois. "Este catalogo Iceberg e
    # o session catalog?" mora em `spark.sql.catalog.<nome>`, onde o `<nome>` e o
    # DADO -- e `rules/expr.py` compara igualdade e mais nada. Quem combina e uma
    # etapa anterior, que e esta.
    #
    # O namespace continua sendo do modulo que o declara: os kinds saem de
    # `lakeformation.EMITTED_KINDS`, nao de `EMITTED_KINDS` daqui, e a asserção
    # acima segue guardando so o que a fusao de SQL e catalogo produz. Misturar
    # os dois namespaces faria `fusion` responder por kind que ela nao escreve.
    derivados_lf = build_lakeformation(facts)
    desconhecidos_lf = {f.kind for f in derivados_lf} - LF_EMITTED_KINDS
    if desconhecidos_lf:
        raise AssertionError(
            f"kind fora do namespace de lakeformation: {sorted(desconhecidos_lf)}"
        )
    for fact in derivados_lf:
        combined[fact.id] = fact

    return sort_facts(combined.values())
