"""Extrator de Facts a partir de um dump JSON ja coletado das metadata tables
do Iceberg (`db.tbl.files`, `.delete_files`, `.snapshots`, `.manifests`,
`.partitions`).

Como `event_log.py`, este modulo NAO coleta nada: a coleta (rodar
`SELECT * FROM db.tbl.files` etc. via Spark SQL ou Athena e salvar o
resultado) e responsabilidade de uma camada anterior, fora deste pacote. Este
extrator so le o JSON ja salvo em disco. O shape esperado do dump, por
tabela, e:

```json
{
  "table": "db.tabela",
  "format_version": 2,
  "properties": {"write.distribution-mode": "none", "format-version": "2"},
  "files": [{"file_path": "...", "file_size_in_bytes": 1234, "record_count": 10}],
  "delete_files": [{"file_path": "...", "file_size_in_bytes": 12}],
  "snapshots": [{"snapshot_id": 1, "committed_at": "2026-01-01T00:00:00Z", "operation": "append"}],
  "manifests": [{"path": "...", "length": 100, "added_data_files_count": 3}],
  "partitions": [{"partition": {"dt": "2026-01-01"}, "file_count": 3, "record_count": 30}],
  "partition_spec": [{"name": "dt", "transform": "identity"}],
  "sort_order": [{"column": "id", "direction": "asc"}]
}
```

Todas as chaves de nivel raiz sao opcionais: um dump pode trazer so `files`,
e a extracao ainda produz os Facts que consegue a partir disso, sem falhar.

`partition_spec` e `sort_order` NAO vem da metadata table `.files`/`.properties`
-- sao metadados estruturais da tabela (spec de particao e ordem de escrita),
nao um par chave/valor livre em `properties`. O catalogo (`rules/catalog/iceberg.yaml`,
SF-ICE-004 e SF-ICE-005) referencia esses dois como `iceberg.table_property`
com `attrs.key` "sort-order" / "partition-spec", entao este extrator os
sintetiza como tal a partir dessas duas chaves opcionais do dump -- desde que
o coletor as forneca. `attrs.present`/`attrs.non_empty` refletem exatamente o
que o dump trouxe: uma lista vazia e "definido, mas vazio", nao "desconhecido".

Como `terraform.py`/`event_log.py`: extrator puro e deterministico. Nunca
aplica limiar, nunca atribui severidade, nunca infere o que o dump nao diz.
Em particular, `SF-ICE-004` (`rules/catalog/iceberg.yaml`) precisa saber se
data files existentes foram escritos ANTES de um sort order ser definido --
um unico dump, tirado num unico instante, nao tem como saber isso (precisaria
de historico entre duas coletas). Este extrator nunca fabrica
`attrs.written_before_sort_order`; a regra fica marcada `blocked_on` no
catalogo ate existir um extrator de historico.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "iceberg_metadata@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "iceberg.files_summary",
        "iceberg.delete_files_summary",
        "iceberg.snapshots_summary",
        "iceberg.manifests_summary",
        "iceberg.partitions_summary",
        "iceberg.table_property",
        "iceberg.unresolved",
        "iceberg.table_analyzed",
    }
)


def _nearest_rank(sorted_values: list[int], pct: int) -> int:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank`, duplicada aqui em vez de
    importada: os dois extratores sao modulos independentes por design (ver
    docstring de `terraform.py`), e a formula e pequena o suficiente para nao
    justificar acoplar os dois so por isso.
    """
    n = len(sorted_values)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return sorted_values[rank - 1]


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


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="iceberg.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _get_list_section(
    payload: dict[str, Any], key: str, path: str, provenance: dict[str, Any]
) -> tuple[list[Any] | None, Fact | None]:
    """Le `payload[key]` se presente. Devolve `(lista, None)`, `(None, None)`
    se a chave nao existe (secao nao coletada -- nao e erro), ou
    `(None, fact_unresolved)` se a chave existe mas nao e uma lista."""
    if key not in payload:
        return None, None
    value = payload[key]
    if isinstance(value, list):
        return value, None
    return None, _unresolved(path, "malformed_json", provenance, section=key)


def _files_summary_fact(
    files: list[Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> tuple[Fact, int]:
    sizes: list[int] = []
    records: list[int] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        size = entry.get("file_size_in_bytes")
        if isinstance(size, int | float) and not isinstance(size, bool):
            sizes.append(int(size))
        rec = entry.get("record_count")
        if isinstance(rec, int | float) and not isinstance(rec, bool):
            records.append(int(rec))

    data_file_count = len(files)
    measures: dict[str, Any] = {"data_file_count": data_file_count}
    if sizes:
        sorted_sizes = sorted(sizes)
        total = sum(sorted_sizes)
        measures["total_bytes"] = total
        measures["avg_file_bytes"] = total / len(sorted_sizes)
        measures["p50_file_bytes"] = _nearest_rank(sorted_sizes, 50)
        measures["p95_file_bytes"] = _nearest_rank(sorted_sizes, 95)
        measures["min_file_bytes"] = sorted_sizes[0]
        measures["max_file_bytes"] = sorted_sizes[-1]
    if records:
        measures["total_records"] = sum(records)

    fact = Fact(
        kind="iceberg.files_summary", subject=subject, measures=measures, provenance=provenance
    )
    return fact, data_file_count


def _delete_files_summary_fact(
    delete_files: list[Any],
    data_file_count: int | None,
    subject: dict[str, Any],
    provenance: dict[str, Any],
) -> Fact:
    sizes: list[int] = []
    for entry in delete_files:
        if not isinstance(entry, dict):
            continue
        size = entry.get("file_size_in_bytes")
        if isinstance(size, int | float) and not isinstance(size, bool):
            sizes.append(int(size))

    # `data_file_count` so entra na fact se a secao `files` tambem foi lida
    # neste mesmo dump: SF-ICE-002 divide `delete_file_count / data_file_count`
    # dentro de uma UNICA condicao `expr`, e o motor de regras avalia `expr`
    # contra o contexto de um unico fact (ver `rules/engine.py::_fact_context`)
    # -- nunca combina measures de dois facts diferentes. Sem `files` no dump,
    # fabricar `data_file_count = 0` mentiria "a tabela nao tem data files"
    # quando a verdade e "esta secao nao foi coletada"; omitir a chave faz o
    # `expr` da regra levantar `ExprError` (caminho ausente), que o motor trata
    # como "nao casa" -- silencioso e seguro, nunca um falso positivo.
    measures: dict[str, Any] = {"delete_file_count": len(delete_files)}
    if data_file_count is not None:
        measures["data_file_count"] = data_file_count
    if sizes:
        measures["total_bytes"] = sum(sizes)

    return Fact(
        kind="iceberg.delete_files_summary",
        subject=subject,
        measures=measures,
        provenance=provenance,
    )


def _snapshots_summary_fact(
    snapshots: list[Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> Fact:
    operations: set[str] = set()
    timestamps: list[datetime] = []
    for entry in snapshots:
        if not isinstance(entry, dict):
            continue
        op = entry.get("operation")
        if isinstance(op, str) and op:
            operations.add(op)
        ts = entry.get("committed_at")
        if isinstance(ts, str):
            parsed = _parse_iso(ts)
            if parsed is not None:
                timestamps.append(parsed)

    measures: dict[str, Any] = {"snapshot_count": len(snapshots)}
    attrs: dict[str, Any] = {"operations": sorted(operations)}
    if timestamps:
        oldest, newest = min(timestamps), max(timestamps)
        attrs["oldest"] = oldest.isoformat()
        attrs["newest"] = newest.isoformat()
        measures["span_hours"] = (newest - oldest).total_seconds() / 3600

    return Fact(
        kind="iceberg.snapshots_summary",
        subject=subject,
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )


def _manifests_summary_fact(
    manifests: list[Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> Fact:
    lengths: list[int] = []
    added_counts: list[int] = []
    for entry in manifests:
        if not isinstance(entry, dict):
            continue
        length = entry.get("length")
        if isinstance(length, int | float) and not isinstance(length, bool):
            lengths.append(int(length))
        added = entry.get("added_data_files_count")
        if isinstance(added, int | float) and not isinstance(added, bool):
            added_counts.append(int(added))

    measures: dict[str, Any] = {"manifest_count": len(manifests)}
    if lengths:
        measures["total_bytes"] = sum(lengths)
    if added_counts:
        measures["avg_data_files_per_manifest"] = sum(added_counts) / len(added_counts)

    return Fact(
        kind="iceberg.manifests_summary", subject=subject, measures=measures, provenance=provenance
    )


def _partitions_summary_fact(
    partitions: list[Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> Fact:
    file_counts: list[int] = []
    record_counts: list[int] = []
    for entry in partitions:
        if not isinstance(entry, dict):
            continue
        fc = entry.get("file_count")
        if isinstance(fc, int | float) and not isinstance(fc, bool):
            file_counts.append(int(fc))
        rc = entry.get("record_count")
        if isinstance(rc, int | float) and not isinstance(rc, bool):
            record_counts.append(int(rc))

    measures: dict[str, Any] = {"partition_count": len(partitions)}
    if file_counts:
        measures["avg_files_per_partition"] = sum(file_counts) / len(file_counts)
        measures["max_files_per_partition"] = max(file_counts)
    if record_counts:
        measures["avg_records_per_partition"] = sum(record_counts) / len(record_counts)

    return Fact(
        kind="iceberg.partitions_summary",
        subject=subject,
        measures=measures,
        provenance=provenance,
    )


def _property_facts(
    properties: dict[str, Any], subject: dict[str, Any], provenance: dict[str, Any]
) -> list[Fact]:
    facts: list[Fact] = []
    for key in sorted(properties):
        value_str = _value_to_str(properties[key])
        facts.append(
            Fact(
                kind="iceberg.table_property",
                subject=subject,
                attrs={
                    "key": key,
                    "value": value_str,
                    "present": True,
                    "non_empty": bool(value_str.strip()),
                },
                provenance=provenance,
            )
        )
    return facts


def _structural_property_fact(
    key: str, non_empty: bool, subject: dict[str, Any], provenance: dict[str, Any]
) -> Fact:
    """`sort-order` / `partition-spec`: nao sao entradas de `properties`, sao
    campos estruturais do dump (ver docstring do modulo). `present` e
    `non_empty` sao o mesmo valor aqui de proposito: para estes dois, "a
    tabela tem um X definido" so e verdade quando a lista tem pelo menos um
    elemento -- uma chave presente com lista vazia significa "definido como
    vazio", que para o proposito de SF-ICE-004/SF-ICE-005 e equivalente a
    "nao definido"."""
    return Fact(
        kind="iceberg.table_property",
        subject=subject,
        attrs={"key": key, "present": non_empty, "non_empty": non_empty},
        provenance=provenance,
    )


def extract_iceberg_metadata(
    payload: dict[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um dump ja carregado (`dict`) de metadata tables Iceberg.

    Nunca levanta excecao por payload malformado: dict sem `table`, ou com
    uma secao que nao e lista, vira `iceberg.unresolved` e a extracao segue
    com o que sobrar. `artifact_sha256` e opcional -- quem chama direto com um
    `dict` ja desserializado (ex.: testes) normalmente nao tem o hash do texto
    original; `extract_iceberg_metadata_path` o calcula a partir do arquivo.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}

    if not isinstance(payload, dict):
        return [_unresolved(path, "malformed_json", provenance)]

    table = payload.get("table")
    if not isinstance(table, str) or not table.strip():
        return [_unresolved(path, "missing_table_name", provenance)]

    subject = _table_subject(path, table)
    facts: list[Fact] = []
    sections_present = 0

    files, files_error = _get_list_section(payload, "files", path, provenance)
    if files_error is not None:
        facts.append(files_error)
    data_file_count: int | None = None
    if files is not None:
        sections_present += 1
        fact, data_file_count = _files_summary_fact(files, subject, provenance)
        facts.append(fact)

    delete_files, delete_error = _get_list_section(payload, "delete_files", path, provenance)
    if delete_error is not None:
        facts.append(delete_error)
    if delete_files is not None:
        sections_present += 1
        facts.append(
            _delete_files_summary_fact(delete_files, data_file_count, subject, provenance)
        )

    snapshots, snapshots_error = _get_list_section(payload, "snapshots", path, provenance)
    if snapshots_error is not None:
        facts.append(snapshots_error)
    if snapshots is not None:
        sections_present += 1
        facts.append(_snapshots_summary_fact(snapshots, subject, provenance))

    manifests, manifests_error = _get_list_section(payload, "manifests", path, provenance)
    if manifests_error is not None:
        facts.append(manifests_error)
    if manifests is not None:
        sections_present += 1
        facts.append(_manifests_summary_fact(manifests, subject, provenance))

    partitions, partitions_error = _get_list_section(payload, "partitions", path, provenance)
    if partitions_error is not None:
        facts.append(partitions_error)
    if partitions is not None:
        sections_present += 1
        facts.append(_partitions_summary_fact(partitions, subject, provenance))

    properties = payload.get("properties")
    if isinstance(properties, dict):
        sections_present += 1
        facts.extend(_property_facts(properties, subject, provenance))
    elif "properties" in payload:
        facts.append(_unresolved(path, "malformed_json", provenance, section="properties"))

    sort_order, sort_order_error = _get_list_section(payload, "sort_order", path, provenance)
    if sort_order_error is not None:
        facts.append(sort_order_error)
    if sort_order is not None:
        facts.append(_structural_property_fact("sort-order", bool(sort_order), subject, provenance))

    partition_spec, partition_spec_error = _get_list_section(
        payload, "partition_spec", path, provenance
    )
    if partition_spec_error is not None:
        facts.append(partition_spec_error)
    if partition_spec is not None:
        facts.append(
            _structural_property_fact("partition-spec", bool(partition_spec), subject, provenance)
        )

    unresolved_count = sum(1 for f in facts if f.kind == "iceberg.unresolved")

    # Sentinela: prova de que a extracao rodou sobre este dump. Mesma funcao
    # que `pyspark.module_analyzed` / `spark.log_analyzed` / `tf.module_analyzed`:
    # sem isso, uma condicao `absent: iceberg.X` do catalogo seria vazamente
    # verdadeira quando o extrator nunca rodou sobre nenhum dump, nao so
    # quando genuinamente nao encontrou X.
    facts.append(
        Fact(
            kind="iceberg.table_analyzed",
            subject=subject,
            measures={"section_count": sections_present, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_iceberg_metadata_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir o arquivo vira um unico Fact `iceberg.unresolved` com
    reason "read_error"; JSON invalido vira "malformed_json". Nunca uma
    excecao que derruba quem chamou -- mesma convencao de
    `event_log.extract_event_log_path` / `terraform.extract_terraform_path`.
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

    return extract_iceberg_metadata(payload, anchor, artifact_sha256=sha)


def extract_iceberg_metadata_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico (permissao,
    encoding invalido, qualquer excecao inesperada) vira um unico Fact
    `iceberg.unresolved` para aquele arquivo, e a travessia continua -- mesma
    convencao de `pyspark_ast.extract_tree` / `terraform.extract_terraform_tree`.
    """
    facts: list[Fact] = []
    for json_file in sorted(root.rglob("*.json")):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_iceberg_metadata_path(json_file, repo_root))
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
