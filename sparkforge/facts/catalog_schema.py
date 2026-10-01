"""Extrator de Facts a partir de um dump JSON ja coletado do Glue Data Catalog
(`GetTables`/`GetTable` da API do Glue, ou equivalente).

Como `iceberg_metadata.py`, este modulo NAO coleta nada: a coleta (chamar a API
do Glue Data Catalog e salvar o resultado) e responsabilidade de uma camada
anterior, fora deste pacote. Este extrator so le o JSON ja salvo em disco. O
shape esperado do dump e uma lista de tabelas:

```json
{
  "tables": [
    {
      "name": "db.eventos",
      "storage_format": "parquet",
      "partition_keys": [{"name": "dt", "type": "string"}],
      "columns": [{"name": "cliente_id", "type": "bigint"}, {"name": "valor", "type": "double"}],
      "properties": {"projection.enabled": "true"},
      "partition_count": 1200
    }
  ]
}
```

Todas as chaves de uma entrada de tabela, alem de `name`, sao opcionais: um
dump com so `name` e `columns` ainda produz o que consegue a partir disso, sem
falhar -- mesma tolerancia de `iceberg_metadata.py` com as secoes do dump
Iceberg.

`attrs.column_types` funde os tipos de `columns` E de `partition_keys`: o Glue
Data Catalog trata coluna de particao como uma coluna normal para fins de tipo
declarado, e `sql.predicate.attrs.on_partition_column`/`type_mismatch`
(resolvidos em `fusion.py`) precisam do tipo declarado de QUALQUER coluna
filtrada, inclusive quando ela e a propria coluna de particao -- exatamente o
caso que SF-ATH-005 (`rules/catalog/athena.yaml`) verifica. Manter dois mapas
separados obrigaria `fusion.py` a consultar dois lugares para a mesma pergunta
("qual o tipo declarado desta coluna?"); fundir aqui, na extracao, e mais
simples e nao perde informacao (uma entrada de `columns` com o mesmo nome
sempre vence sobre a de `partition_keys`, ja que particao normalmente ja vem
listada em `columns` tambem nos dumps reais do Glue -- `setdefault` so cobre o
caso raro de dump que lista a particao SOMENTE em `partition_keys`).

`catalog.table_property.projection_enabled` e uma acomodacao deliberada, nao um
acidente: `rules/catalog/athena.yaml` (SF-ATH-003) usa
`absent: catalog.table_property.projection_enabled`, e o operador `absent:` do
motor de regras (`rules/engine.py::_absent_satisfied`) so checa auxencia de um
`fact.kind` inteiro -- nunca um `where` sobre `attrs`. Sem um kind proprio para
"esta tabela tem `projection.enabled` truthy", `absent:` nao teria como
expressar essa pergunta: `absent: catalog.table_property` seria verdadeiro
mesmo quando a tabela tem `properties` cheio de outras chaves (so nao esta), e
qualquer `where` dentro de `all`/`any` casa facts independentemente, nunca
nega. Este extrator sintetiza esse kind pontual (alem do `catalog.table_property`
generico, sempre emitido, um por entrada de `properties`) sempre que a chave
literal `projection.enabled` existir com valor truthy. Ver `rules/catalog/README.md`
secao "`absent:` exige um fact sentinela".

Como `iceberg_metadata.py`/`terraform.py`: extrator puro e deterministico.
Nunca aplica limiar, nunca atribui severidade, nunca infere o que o dump nao
diz. Em particular, este extrator NUNCA correlaciona uma tabela com texto SQL
-- essa correlacao (por nome de tabela, com o cuidado de ambiguidade que nome
nao-qualificado exige) e o unico trabalho de `fusion.py`, que consome os facts
`catalog.table_schema` produzidos aqui junto dos facts `sql.projection`/
`sql.predicate` de `sql_literal.py`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "catalog_schema@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "catalog.table_schema",
        "catalog.table_partitions",
        "catalog.table_property",
        "catalog.table_property.projection_enabled",
        "catalog.unresolved",
        "catalog.analyzed",
    }
)

_COLUMNAR_FORMATS = frozenset({"parquet", "orc"})
_TRUTHY_STRINGS = frozenset({"true", "1", "yes"})


def _file_subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _table_subject(path: str, table: str) -> dict[str, Any]:
    return {"type": "table", "file": path, "symbol": table}


def _value_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in _TRUTHY_STRINGS
    if isinstance(value, int | float):
        return value != 0
    return False


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="catalog.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _column_types(
    columns_raw: list[Any] | None, partition_keys_raw: list[Any] | None
) -> dict[str, str]:
    types: dict[str, str] = {}
    if isinstance(columns_raw, list):
        for col in columns_raw:
            if (
                isinstance(col, dict)
                and isinstance(col.get("name"), str)
                and isinstance(col.get("type"), str)
            ):
                types[col["name"]] = col["type"]
    if isinstance(partition_keys_raw, list):
        for pk in partition_keys_raw:
            if (
                isinstance(pk, dict)
                and isinstance(pk.get("name"), str)
                and isinstance(pk.get("type"), str)
            ):
                # setdefault: uma entrada de `columns` com o mesmo nome ja
                # declarou o tipo -- ver docstring do modulo.
                types.setdefault(pk["name"], pk["type"])
    return types


def _partition_key_names(partition_keys_raw: list[Any] | None) -> list[str]:
    if not isinstance(partition_keys_raw, list):
        return []
    return [
        pk["name"]
        for pk in partition_keys_raw
        if isinstance(pk, dict) and isinstance(pk.get("name"), str)
    ]


def _schema_fact(entry: dict[str, Any], table: str, subject: dict[str, Any]) -> Fact:
    storage_format = entry.get("storage_format")
    storage_format = storage_format if isinstance(storage_format, str) else None
    columnar = storage_format.strip().lower() in _COLUMNAR_FORMATS if storage_format else None

    columns_raw = entry.get("columns")
    partition_keys_raw = entry.get("partition_keys")

    attrs: dict[str, Any] = {
        "table": table,
        "storage_format": storage_format,
        "columnar": columnar,
        "partition_keys": _partition_key_names(partition_keys_raw),
        "column_types": _column_types(columns_raw, partition_keys_raw),
    }

    measures: dict[str, Any] = {}
    if isinstance(columns_raw, list):
        measures["column_count"] = len(columns_raw)
    if isinstance(partition_keys_raw, list):
        measures["partition_key_count"] = len(attrs["partition_keys"])

    return Fact(kind="catalog.table_schema", subject=subject, attrs=attrs, measures=measures)


def _partitions_fact(entry: dict[str, Any], subject: dict[str, Any]) -> Fact | None:
    partition_count = entry.get("partition_count")
    if not _is_number(partition_count):
        return None
    count = int(partition_count)

    # `distinct_values`: no Glue Data Catalog, cada entrada de particao JA e
    # uma combinacao distinta de valores das colunas de particao -- nao ha
    # duplicata possivel. `partition_count` e `distinct_values` sao portanto
    # o mesmo numero por definicao, nao uma inferencia; mantidos como duas
    # measures porque SF-ATH-003 le `partition_count` e um consumidor futuro
    # pode preferir o nome `distinct_values` sem precisar saber da equivalencia.
    measures: dict[str, Any] = {"partition_count": count, "distinct_values": count}

    total_bytes = entry.get("total_size_bytes")
    if _is_number(total_bytes) and count > 0:
        measures["avg_bytes_per_partition"] = float(total_bytes) / count

    return Fact(kind="catalog.table_partitions", subject=subject, measures=measures)


def _property_facts(properties: dict[str, Any], subject: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    for key in sorted(properties):
        value_str = _value_to_str(properties[key])
        facts.append(
            Fact(
                kind="catalog.table_property",
                subject=subject,
                attrs={"key": key, "value": value_str, "present": True},
            )
        )
        if key == "projection.enabled" and _is_truthy(properties[key]):
            facts.append(
                Fact(
                    kind="catalog.table_property.projection_enabled",
                    subject=subject,
                    attrs={"key": key, "value": value_str, "present": True},
                )
            )
    return facts


def _with_provenance(facts: list[Fact], provenance: dict[str, Any]) -> list[Fact]:
    return [
        Fact(
            kind=f.kind,
            subject=f.subject,
            measures=f.measures,
            attrs=f.attrs,
            provenance=provenance,
        )
        for f in facts
    ]


def _table_facts(entry: dict[str, Any], table: str, path: str) -> list[Fact]:
    subject = _table_subject(path, table)
    facts = [_schema_fact(entry, table, subject)]

    partitions_fact = _partitions_fact(entry, subject)
    if partitions_fact is not None:
        facts.append(partitions_fact)

    properties = entry.get("properties")
    if isinstance(properties, dict):
        facts.extend(_property_facts(properties, subject))

    return facts


def extract_catalog_schema(
    payload: dict[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um dump ja carregado (`dict`) do Glue Data Catalog.

    Nunca levanta excecao por payload malformado: dict sem `tables`, uma
    entrada sem `name`, ou uma secao que nao e do tipo esperado, viram
    `catalog.unresolved` e a extracao segue com o que sobrar -- mesma
    convencao de `iceberg_metadata.extract_iceberg_metadata`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}

    facts: list[Fact] = []
    table_count = 0

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
    else:
        tables_raw = payload.get("tables")
        if tables_raw is not None and not isinstance(tables_raw, list):
            facts.append(_unresolved(path, "malformed_json", provenance, section="tables"))
        elif isinstance(tables_raw, list):
            for entry in tables_raw:
                if not isinstance(entry, dict):
                    facts.append(
                        _unresolved(path, "malformed_json", provenance, section="tables[]")
                    )
                    continue
                name = entry.get("name")
                if not isinstance(name, str) or not name.strip():
                    facts.append(_unresolved(path, "missing_table_name", provenance))
                    continue
                table_count += 1
                facts.extend(_with_provenance(_table_facts(entry, name, path), provenance))
            # `tables_raw is None`: chave ausente do payload -- nada foi
            # coletado neste dump, mas o dump em si e valido (nao e um erro).

    unresolved_count = sum(1 for f in facts if f.kind == "catalog.unresolved")

    # Sentinela: prova de que a extracao rodou sobre este dump, mesma funcao
    # de `iceberg.table_analyzed`/`sql.analyzed`. Subject de arquivo (nao de
    # tabela): um dump de catalogo descreve VARIAS tabelas, entao nao ha um
    # unico `symbol` de tabela ao qual ancorar a sentinela.
    facts.append(
        Fact(
            kind="catalog.analyzed",
            subject=_file_subject(path),
            measures={"table_count": table_count, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_catalog_schema_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir o arquivo vira um unico Fact `catalog.unresolved` com
    reason "read_error"; JSON invalido vira "malformed_json". Nunca uma
    excecao que derruba quem chamou -- mesma convencao de
    `iceberg_metadata.extract_iceberg_metadata_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [_unresolved(anchor, "read_error", empty_provenance, detail=str(exc))]

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
        return [_unresolved(anchor, "malformed_json", provenance)]

    return extract_catalog_schema(payload, anchor, artifact_sha256=sha)


def extract_catalog_schema_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico (permissao,
    encoding invalido, qualquer excecao inesperada) vira um unico Fact
    `catalog.unresolved` para aquele arquivo, e a travessia continua -- mesma
    convencao de `iceberg_metadata.extract_iceberg_metadata_tree`.
    """
    facts: list[Fact] = []
    for json_file in iter_source_files(root, "*.json"):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_catalog_schema_path(json_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            facts.append(
                _unresolved(
                    anchor,
                    "read_error",
                    {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID},
                    detail=str(exc),
                )
            )
    return sort_facts(facts)
