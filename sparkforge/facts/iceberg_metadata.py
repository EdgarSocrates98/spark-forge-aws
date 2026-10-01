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
  "sort_order": [{"column": "id", "direction": "asc"}],
  "default_sort_order_id": 2
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

## `written_before_sort_order`: onde a evidencia esta, e onde ela nao esta

`SF-ICE-004` (`rules/catalog/iceberg.yaml`) precisa saber se data files
existentes foram escritos ANTES do sort order atual da tabela. Tres caminhos
foram investigados; so um sobreviveu, e ele e mais estreito do que parece.

1. **Datar a mudanca de sort order pelo `metadata-log`: nao funciona.** A spec
   define cada entrada como EXATAMENTE `metadata-file` + `timestamp-ms`. Nao
   ha sort order nela -- so o ponteiro. Nem o snapshot ajuda: a spec registra
   `schema-id` por snapshot e NAO registra `sort-order-id`, uma assimetria
   real. Responder por esse caminho exigiria baixar e parsear cada
   metadata.json historico, artefatos que `write.metadata.previous-versions-max`
   e `write.metadata.delete-after-commit.enabled` podem ter apagado. Um dump
   nao responde; uma coleta muito maior talvez.

2. **`data_file.sort_order_id` (campo 140, `int` opcional, presente desde o
   formato v1): a evidencia certa, mas so num sentido.** Um id nao-zero so
   aparece quando um writer chamou `withSortOrder` com uma ordem registrada em
   `sort-orders`. Entao "id nao-zero e diferente do `default-sort-order-id`"
   prova que o arquivo foi escrito sob outra ordem, e "id igual ao default"
   prova o contrario. As duas afirmacoes valem em qualquer versao.

3. **`sort_order_id == 0` NAO prova nada, e e a armadilha.** `DataFiles.Builder`
   inicializa `sortOrderId = SortOrder.unsorted().orderId()` (0), e o writer do
   Spark so passou a sobrescrever isso no Iceberg **1.11.0**
   (`SparkWrite.java` ganhou `.dataSortOrder(...)` nessa versao; nao ha
   mencao nenhuma a sort order no mesmo arquivo em 1.7.1 nem em 1.10.0).
   Nenhum runtime Glue chega la: 4.0 traz 1.0.0, 5.0 traz 1.7.1, 5.1 traz
   1.10.0. Na pratica, portanto, TODO data file escrito por Glue sai com
   `sort_order_id = 0` -- inclusive os que acabaram de ser produzidos por um
   `rewrite_data_files` com estrategia sort que de fato ordenou os dados.

O efeito de (3) e que a regra so dispara em tabela com passivo escrito por um
writer que registra sort order (outro engine, ou Iceberg >= 1.11). Na tabela
Glue tipica ela fica calada -- e o silencio e contabilizado: os arquivos com
id 0 caem em `files_sort_order_unknown` e viram um `iceberg.unresolved` com
reason `sort_order_id_missing`, nunca um `false` que se leria como "sem
passivo". Ver `_sort_order_census` e `_written_before_sort_order`; a
disciplina `True`/`False`/`None` e a de `fusion._infer_type_mismatch`.

O dump ganha a chave escalar opcional `default_sort_order_id`; `files` ganha
`sort_order_id` por entrada (o coletor Athena ja o traz, porque consulta
`SELECT *` e a metadata table `files` expoe todo campo de `data_file`). Sem
uma das duas, o atributo simplesmente nao e emitido.

Fontes (retrieved 2026-07-30):
- https://github.com/apache/iceberg/blob/apache-iceberg-1.0.0/format/spec.md
  -- campo 140 `sort_order_id`, "Order id `0` is reserved for the unsorted
  order", e o `metadata-log` de dois campos. Tag 1.0.0 de proposito: e a
  versao mais ANTIGA do range Glue suportado.
- https://github.com/apache/iceberg/blob/apache-iceberg-1.10.0/core/src/main/java/org/apache/iceberg/DataFiles.java
  -- `private Integer sortOrderId = SortOrder.unsorted().orderId();`
- `spark/v3.5/spark/src/main/java/org/apache/iceberg/spark/source/SparkWrite.java`
  nas tags `apache-iceberg-1.7.1` e `apache-iceberg-1.10.0` (sem
  `dataSortOrder`) contra `apache-iceberg-1.11.0` (com).

Como `terraform.py`/`event_log.py`: extrator puro e deterministico. Nunca
aplica limiar, nunca atribui severidade, nunca infere o que o dump nao diz.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
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
        "iceberg.format_version",
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


UNSORTED_ORDER_ID = 0
"""Sentinela da spec: "Order id `0` is reserved for the unsorted order."
(https://github.com/apache/iceberg/blob/apache-iceberg-1.0.0/format/spec.md)"""


def _sort_order_census(files: list[Any], default_order_id: int) -> dict[str, int]:
    """Classifica cada data file pelo `sort_order_id` que ele carrega.

    Tres baldes mutuamente exclusivos, cuja soma e sempre o numero de entradas
    da secao `files` (`data_file_count`):

    - `files_current_sort_order`: `sort_order_id == default-sort-order-id`.
      Um id nao-zero so e gravado quando um writer chamou `withSortOrder` com
      uma ordem registrada, entao isto e evidencia POSITIVA de escrita sob a
      ordem vigente.
    - `files_stale_sort_order`: `sort_order_id` inteiro, diferente de 0 e do
      default. Mesma logica ao contrario: alguem gravou deliberadamente OUTRA
      ordem registrada, logo o arquivo e anterior a ordem atual.
    - `files_sort_order_unknown`: `0`, ausente, nulo, ou de tipo que nao e
      `int`.

    Por que `0` cai em "unknown" e nao em "comprovadamente sem ordenacao":
    `DataFiles.Builder` inicializa `sortOrderId = SortOrder.unsorted().orderId()`
    (isto e, 0), e o writer do Spark so passou a sobrescrever isso no Iceberg
    1.11.0 -- `SparkWrite.java` ganhou `.dataSortOrder(table.sortOrders().get(
    sortOrderId))` nessa versao, e nao tem nenhuma mencao a sort order em
    1.7.1 nem em 1.10.0 (verificado nas tres tags). Em TODO runtime Glue de
    hoje (4.0/1.0.0, 5.0/1.7.1, 5.1/1.10.0), portanto, todo data file escrito
    pelo Spark sai com `sort_order_id = 0`, inclusive logo depois de um
    `rewrite_data_files` com estrategia sort que de fato ordenou os dados. Ler
    esse 0 como "arquivo nao ordenado" faria SF-ICE-004 disparar em toda
    tabela Iceberg escrita por Glue -- inclusive nas recem-compactadas -- e
    cada disparo desses e um `rewrite_data_files` caro sobre tabela grande sem
    motivo. A spec diz "If sort order ID is missing or unknown, then the order
    is assumed to be unsorted"; esta e uma divergencia deliberada dessa
    suposicao, porque na pratica 0 significa "o writer nao registrou", nao
    "nao ordenado".

    O `bool` e excluido de proposito: `False` e `int` em Python.
    """
    census = {
        "files_current_sort_order": 0,
        "files_stale_sort_order": 0,
        "files_sort_order_unknown": 0,
    }
    for entry in files:
        if not isinstance(entry, dict):
            # Entrada que nem e objeto tem sort order desconhecido como
            # qualquer outra. Pular em silencio (como as agregacoes de tamanho
            # fazem) deixaria uma secao `files` inteiramente corrompida com o
            # censo zerado, e censo zerado se le como "todo arquivo sob a ordem
            # vigente" -- um `false` afirmado a partir de nada.
            census["files_sort_order_unknown"] += 1
            continue
        order_id = entry.get("sort_order_id")
        if not isinstance(order_id, int) or isinstance(order_id, bool):
            census["files_sort_order_unknown"] += 1
        elif order_id == default_order_id:
            census["files_current_sort_order"] += 1
        elif order_id == UNSORTED_ORDER_ID:
            census["files_sort_order_unknown"] += 1
        else:
            census["files_stale_sort_order"] += 1
    return census


def _written_before_sort_order(census: dict[str, int], default_order_id: int) -> bool | None:
    """`True`/`False`/`None`, na disciplina de `fusion._infer_type_mismatch`.

    `True` so com pelo menos um arquivo carregando outra ordem REGISTRADA --
    id inteiro, nao-zero, diferente do default. `False` so quando todo arquivo
    carrega o default, o que tambem exige id nao-zero. `None` (atributo ausente
    da fact) para todo o resto, e `where: {attrs.written_before_sort_order:
    true}` de SF-ICE-004 nao casa com atributo ausente.

    Um `True` errado manda alguem rodar `rewrite_data_files` sobre uma tabela
    grande por nada; um `False` errado esconde o passivo. `None` nao faz nem
    um nem outro.
    """
    if default_order_id == UNSORTED_ORDER_ID:
        # A tabela nao declara sort order nenhum. "Arquivo escrito antes do
        # sort order" e vacuo aqui, e a resposta e um `False` bem fundamentado,
        # nao desconhecimento: nao ha ordem para nenhum arquivo preceder.
        return False
    if census["files_stale_sort_order"]:
        return True
    if census["files_sort_order_unknown"]:
        return None
    return False


def _files_summary_fact(
    files: list[Any],
    subject: dict[str, Any],
    provenance: dict[str, Any],
    default_sort_order_id: int | None = None,
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

    attrs: dict[str, Any] = {}
    if default_sort_order_id is not None:
        census = _sort_order_census(files, default_sort_order_id)
        measures.update(census)
        verdict = _written_before_sort_order(census, default_sort_order_id)
        if verdict is not None:
            attrs["written_before_sort_order"] = verdict
            # So sai junto com o veredito. Com o veredito ausente, um
            # `files_written_before_sort_order: 0` ao lado de tres arquivos
            # desconhecidos se leria como "nenhum arquivo antigo" -- a
            # afirmacao que o extrator acabou de se recusar a fazer. Os tres
            # contadores do censo ficam de qualquer forma: cada um e observacao
            # crua, nao resposta. Com `files_sort_order_unknown > 0` e veredito
            # `True`, este numero e um piso confirmado, nao um total.
            measures["files_written_before_sort_order"] = census["files_stale_sort_order"]

    fact = Fact(
        kind="iceberg.files_summary",
        subject=subject,
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )
    return fact, data_file_count


# `content` na metadata table `.delete_files`, com os codigos que a Table
# Specification publica. A coluna existe desde a v2 e e a UNICA forma de
# distinguir position delete de equality delete sem abrir o arquivo Avro.
#
# Em v3 o DELETION VECTOR aparece com `content = 1` -- ele SUBSTITUI o
# position delete, e nao se soma a ele. Contar os dois juntos como
# "position" e o que a spec sustenta; separa-los exigiria ler o
# `content_offset`/`content_size_in_bytes` do Puffin, que o dump nao traz.
_CONTENT_DE_DELETE = {1: "position", 2: "equality"}


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
    # Censo por `content`. A coluna e OPCIONAL no dump: um coletor que nao a
    # traga produz `content_unresolved`, e nunca zero -- zero se leria como "nao
    # ha delete de posicao", quando a verdade e "ninguem perguntou".
    censo: dict[str, int] = {}
    sem_content = 0
    for entry in delete_files:
        if not isinstance(entry, dict):
            continue
        bruto = entry.get("content")
        if isinstance(bruto, int) and not isinstance(bruto, bool):
            nome = _CONTENT_DE_DELETE.get(bruto)
            if nome is None:
                # Codigo fora do que a spec publica: nomeado, nao somado a
                # nenhum dos dois. Uma spec futura pode acrescentar codigo, e
                # empurra-lo para "position" seria adivinhar.
                censo["content_unknown"] = censo.get("content_unknown", 0) + 1
            else:
                censo[f"{nome}_delete_count"] = censo.get(f"{nome}_delete_count", 0) + 1
        else:
            sem_content += 1

    measures: dict[str, Any] = {"delete_file_count": len(delete_files)}
    if data_file_count is not None:
        measures["data_file_count"] = data_file_count
    if sizes:
        measures["total_bytes"] = sum(sizes)
    measures.update(censo)
    if sem_content:
        measures["content_unresolved"] = sem_content

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


# As tres versoes que a spec publica. `feature_support.SPEC_VERSIONS` vale
# `{2, 3}` e NAO e a mesma coisa: aquela constante governa UPGRADE de spec, e
# ninguem faz upgrade PARA v1. Aqui a pergunta e outra -- de que versao a
# tabela E --, e v1 e resposta legitima.
_VERSOES_DA_SPEC = (1, 2, 3)


def _format_version_fact(
    payload: dict[str, Any],
    subject: dict[str, Any],
    path: str,
    provenance: dict[str, Any],
) -> Fact:
    """A versao que a tabela E, contra a que a propriedade DECLARA.

    ## Duas coisas diferentes, e por isso dois campos

    `format_version` no topo do dump vem do `metadata.json` e e AUTORITATIVO.
    `properties['format-version']` e um par chave/valor que pode estar
    ausente, ficar para tras de um upgrade, ou nao ter sido propagado pelo
    coletor.

    Colapsa-los num campo escolheria por conta propria qual dos dois e a
    verdade -- e o caso em que divergem e exatamente o que vale reportar.

    ## A ausencia do topo NAO e suprida pela propriedade

    Inferir da propriedade transformaria "o coletor nao me deu" em "a tabela
    e v2". A recusa sai nomeada, com a medida que a destrava: incluir o campo
    e uma linha do `metadata.json`.

    ## v1 nao e defeito

    Uma tabela v1 e valida. O defeito so existe quando a matriz diz que o
    engine do consumidor suporta mais E ha motivo para subir -- e isso e
    julgamento, que mora em regra e nao aqui.
    """
    propriedades = payload.get("properties")
    da_propriedade: str | None = None
    if isinstance(propriedades, dict) and "format-version" in propriedades:
        da_propriedade = _value_to_str(propriedades["format-version"])

    attrs: dict[str, Any] = {"resolved": False}
    if da_propriedade is not None:
        attrs["property"] = da_propriedade

    if "format_version" not in payload:
        attrs["reason"] = "format_version_ausente_no_dump"
        attrs["unblocked_by"] = (
            "o coletor precisa incluir `format_version` no dump -- e uma linha "
            "do `metadata.json` da tabela, e sem ela a versao so poderia ser "
            "inferida da propriedade, que e outra coisa"
        )
        return Fact(
            kind="iceberg.format_version",
            subject=subject,
            attrs=attrs,
            provenance=provenance,
        )

    bruto = payload["format_version"]
    if not isinstance(bruto, int) or isinstance(bruto, bool):
        attrs["reason"] = "format_version_nao_numerico"
        attrs["observed"] = _value_to_str(bruto)
        attrs["unblocked_by"] = (
            "o dump trouxe `format_version` como algo que nao e inteiro; a "
            "spec publica 1, 2 e 3"
        )
        return Fact(
            kind="iceberg.format_version",
            subject=subject,
            attrs=attrs,
            provenance=provenance,
        )

    if bruto not in _VERSOES_DA_SPEC:
        attrs["reason"] = "format_version_fora_da_spec"
        attrs["observed"] = str(bruto)
        attrs["unblocked_by"] = (
            f"a spec publica {', '.join(str(v) for v in _VERSOES_DA_SPEC)}; "
            f"um valor fora disso e do coletor ou de uma spec futura que este "
            f"extrator nao conhece"
        )
        return Fact(
            kind="iceberg.format_version",
            subject=subject,
            attrs=attrs,
            provenance=provenance,
        )

    attrs["resolved"] = True
    attrs["declared"] = str(bruto)
    # `diverges` so existe quando HA os dois lados para comparar. Sem a
    # propriedade, `false` se leria como "conferido e concorda", que e
    # afirmacao sobre um lado que nao existe.
    if da_propriedade is not None:
        attrs["diverges"] = da_propriedade.strip() != str(bruto)
    return Fact(
        kind="iceberg.format_version",
        subject=subject,
        measures={"version": bruto},
        attrs=attrs,
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

    # `default_sort_order_id` e escalar, nao secao de lista: e lido antes de
    # `files` porque o censo de sort order vive dentro de `iceberg.files_summary`
    # (SF-ICE-004 avalia `where` contra UM fact, e o motor nunca combina attrs
    # de dois facts -- mesma restricao documentada em `_delete_files_summary_fact`).
    default_sort_order_id: int | None = None
    if "default_sort_order_id" in payload:
        raw = payload["default_sort_order_id"]
        if isinstance(raw, int) and not isinstance(raw, bool):
            default_sort_order_id = raw
        else:
            facts.append(
                _unresolved(path, "malformed_json", provenance, section="default_sort_order_id")
            )

    files, files_error = _get_list_section(payload, "files", path, provenance)
    if files_error is not None:
        facts.append(files_error)
    data_file_count: int | None = None
    if files is not None:
        sections_present += 1
        fact, data_file_count = _files_summary_fact(
            files, subject, provenance, default_sort_order_id
        )
        facts.append(fact)
        # Ponto cego explicito (AGENT_PROTOCOL regra 7): a pergunta de
        # SF-ICE-004 foi feita (a tabela declara sort order) e o dump nao tem
        # `sort_order_id` em parte dos data files. Silencio aqui leria como
        # "nenhum problema", que e exatamente o que o protocolo proibe.
        unknown = fact.measures.get("files_sort_order_unknown") or 0
        if default_sort_order_id not in (None, UNSORTED_ORDER_ID) and unknown:
            facts.append(
                _unresolved(
                    path,
                    "sort_order_id_missing",
                    provenance,
                    section="files",
                    file_count=unknown,
                )
            )

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

    # SEMPRE, inclusive quando o dump nao traz `format_version`: ali como
    # recusa nomeada. Ausencia do fact se leria como "ninguem perguntou".
    facts.append(_format_version_fact(payload, subject, path, provenance))

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
    for json_file in iter_source_files(root, "*.json"):
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
