"""Extrator de Facts a partir de um dump ja coletado de `s3api list-objects-v2`.

Como `catalog_schema.py`/`athena_workgroup.py`, este modulo NAO coleta nada --
nao importa boto3, nao toca rede. A coleta e um comando que o operador roda:

    aws s3api list-objects-v2 --bucket <bucket> --prefix <prefixo> > listing.json

Nao ha coletor `collect_s3_listing` no pacote de proposito: listar um prefixo
grande custa uma chamada por 1000 objetos, e quem paga essa conta precisa
decidir o escopo (e a paginacao) com o proprio olho no bucket, nao por um
default nosso. O shape esperado e a saida crua do comando:

```json
{
  "Name": "lake",
  "Prefix": "analytics/pedidos/",
  "IsTruncated": false,
  "Contents": [
    {"Key": "analytics/pedidos/dt=2026-07-30/part-0.snappy.parquet",
     "Size": 4194304, "StorageClass": "STANDARD"}
  ]
}
```

Este extrator desbloqueia SF-PQ-001 (small files), SF-PQ-003 (texto comprimido
nao splitavel) e SF-PQ-005 (cardinalidade de particao). Nenhuma dessas
perguntas pode ser respondida a partir de codigo, plano ou event log: elas sao
sobre o que EXISTE no armazenamento, e a unica fonte e a listagem.

DUAS decisoes carregam quase todo o valor do modulo:

**Agrupamento por (formato, compressao).** Um prefixo real mistura Parquet com
`_SUCCESS`, log em `.gz` e as vezes CSV de carga inicial. Um unico sumario por
prefixo faria a media de bytes de Parquet ser puxada por arquivos de controle
de 0 byte, e SF-PQ-003 (`where: {format: text, compression: gzip}`) nunca
casaria num prefixo majoritariamente Parquet -- mesmo havendo um `.gz` de 4 GB
ali, que e exatamente o achado que a regra existe para dar. Cada grupo vira um
`s3.prefix_summary` proprio.

**Listagem truncada nao vira sumario.** `IsTruncated: true` significa que o
dump tem no maximo 1000 objetos de um prefixo que pode ter milhoes.
`file_count` sairia menor, `avg_file_bytes` sairia enviesado e `max_file_bytes`
seria o maximo da PRIMEIRA pagina, nao do prefixo. As tres measures alimentam
limiar direto, entao o modulo nao emite sumario nenhum nesse caso: emite
`s3.unresolved` com reason `truncated_listing`. Mesma decisao de
`spark_plan.py` para `... N more fields`. Ver
`knowledge/storage/parquet-layout.md` para o porque dos limiares.

Extrator puro e deterministico: nunca aplica limiar, nunca atribui severidade,
nunca infere o que a listagem nao diz.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "s3_listing@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "s3.prefix_summary",
        "s3.unresolved",
        "s3.analyzed",
    }
)

# Extensao -> (formato, compressao). A ordem importa: `.snappy.parquet` casa
# antes de `.parquet`, e `.json.gz` antes de `.json`. Um sufixo desconhecido
# NAO vira "parquet por default" -- vira `unknown`, e SF-PQ-003, que exige
# `format: text`, simplesmente nao avalia o grupo.
_SUFFIXES: tuple[tuple[str, str, str], ...] = (
    (".snappy.parquet", "parquet", "snappy"),
    (".gz.parquet", "parquet", "gzip"),
    (".zstd.parquet", "parquet", "zstd"),
    (".parquet", "parquet", "unknown"),
    (".orc", "orc", "unknown"),
    (".avro", "avro", "unknown"),
    (".json.gz", "text", "gzip"),
    (".jsonl.gz", "text", "gzip"),
    (".csv.gz", "text", "gzip"),
    (".tsv.gz", "text", "gzip"),
    (".txt.gz", "text", "gzip"),
    (".log.gz", "text", "gzip"),
    (".json.bz2", "text", "bzip2"),
    (".csv.bz2", "text", "bzip2"),
    (".json.zst", "text", "zstd"),
    (".csv.zst", "text", "zstd"),
    (".json", "text", "none"),
    (".jsonl", "text", "none"),
    (".csv", "text", "none"),
    (".tsv", "text", "none"),
    (".txt", "text", "none"),
    (".log", "text", "none"),
    (".gz", "unknown", "gzip"),
    (".bz2", "unknown", "bzip2"),
    (".zst", "unknown", "zstd"),
)

# Chaves que o Spark e o Hadoop escrevem como marcador de controle, nao como
# dado. Contar `_SUCCESS` (0 byte) junto com os arquivos de dados derrubaria a
# media e faria SF-PQ-001 disparar em prefixo saudavel.
_CONTROL_BASENAMES = frozenset({"_SUCCESS", "_committed", "_started", ".DS_Store"})


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _prefix_subject(uri: str, fmt: str, compression: str) -> dict[str, Any]:
    """Subject de um GRUPO, nao do prefixo.

    O prefixo sozinho nao identifica a entidade do achado: um mesmo prefixo
    pode disparar SF-PQ-001 pelo Parquet e SF-PQ-003 pelo `.gz` de carga
    inicial, e dois findings dizendo `s3://lake/analytics/pedidos/` mandariam
    o operador olhar o mesmo lugar para dois problemas em arquivos diferentes.
    """
    return {"type": "table", "symbol": f"{uri} [{fmt}/{compression}]"}


def _classify(key: str) -> tuple[str, str]:
    """`(formato, compressao)` a partir do sufixo da chave, sem adivinhar."""
    lowered = key.lower()
    for suffix, fmt, compression in _SUFFIXES:
        if lowered.endswith(suffix):
            return fmt, compression
    return "unknown", "unknown"


def _is_control_object(key: str, size: int) -> bool:
    basename = key.rsplit("/", 1)[-1]
    if basename in _CONTROL_BASENAMES:
        return True
    # Marcador de "diretorio" do console da AWS: chave terminada em `/` com 0
    # byte. Nao e arquivo, e contá-lo inflaria `file_count`.
    return key.endswith("/") and size == 0


def _percentile(ordered: list[int], fraction: float) -> int:
    """Percentil por indice, sem interpolacao -- o valor devolvido e sempre o
    tamanho de um arquivo que existe, nao uma media entre dois."""
    index = min(len(ordered) - 1, int(fraction * len(ordered)))
    return ordered[index]


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="s3.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _summary_fact(
    uri: str,
    fmt: str,
    compression: str,
    sizes: list[int],
    provenance: dict[str, Any],
) -> Fact:
    ordered = sorted(sizes)
    total = sum(ordered)
    return Fact(
        kind="s3.prefix_summary",
        subject=_prefix_subject(uri, fmt, compression),
        measures={
            "file_count": len(ordered),
            "total_bytes": total,
            "avg_file_bytes": total / len(ordered),
            "min_file_bytes": ordered[0],
            "p50_file_bytes": _percentile(ordered, 0.50),
            "p95_file_bytes": _percentile(ordered, 0.95),
            "max_file_bytes": ordered[-1],
        },
        attrs={"prefix": uri, "format": fmt, "compression": compression},
        provenance=provenance,
    )


def extract_s3_listing(
    payload: dict[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um dump ja carregado (`dict`) de `list-objects-v2`.

    Nunca levanta excecao por payload malformado: `Contents` ausente ou de tipo
    errado, entrada sem `Key`, `Size` nao numerico -- tudo vira `s3.unresolved`
    e a extracao segue com o que sobrar.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}

    facts: list[Fact] = []
    groups: dict[tuple[str, str], list[int]] = {}
    object_count = 0
    control_count = 0

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        payload = {}

    bucket = payload.get("Name")
    prefix = payload.get("Prefix")
    uri = "s3://{}/{}".format(
        bucket if isinstance(bucket, str) and bucket else "desconhecido",
        prefix if isinstance(prefix, str) else "",
    )

    truncated = payload.get("IsTruncated") is True
    contents = payload.get("Contents")

    if contents is not None and not isinstance(contents, list):
        facts.append(_unresolved(path, "malformed_json", provenance, section="Contents"))
        contents = None

    for entry in contents or []:
        if not isinstance(entry, dict):
            facts.append(_unresolved(path, "malformed_json", provenance, section="Contents[]"))
            continue
        key = entry.get("Key")
        if not isinstance(key, str) or not key.strip():
            facts.append(_unresolved(path, "missing_key", provenance))
            continue
        size = entry.get("Size")
        if not _is_number(size):
            facts.append(_unresolved(path, "missing_size", provenance, key=key))
            continue
        size = int(size)
        object_count += 1
        if _is_control_object(key, size):
            control_count += 1
            continue
        groups.setdefault(_classify(key), []).append(size)

    if truncated:
        # A listagem parou antes do fim: `file_count`, `avg_file_bytes` e
        # `max_file_bytes` seriam calculados sobre uma amostra apresentada como
        # total. As tres alimentam limiar de SF-PQ-001 e SF-PQ-003 direto.
        facts.append(
            _unresolved(
                path,
                "truncated_listing",
                provenance,
                prefix=uri,
                detail=(
                    "IsTruncated=true: a listagem tem no maximo uma pagina do prefixo. "
                    "Colete as paginas seguintes com NextContinuationToken antes de "
                    "julgar small files ou tamanho maximo de arquivo."
                ),
                listed_object_count=object_count,
            )
        )
    else:
        for (fmt, compression), sizes in sorted(groups.items()):
            facts.append(_summary_fact(uri, fmt, compression, sizes, provenance))

    facts.append(
        Fact(
            kind="s3.analyzed",
            subject=_file_subject(path),
            measures={
                "object_count": object_count,
                "control_object_count": control_count,
                "group_count": 0 if truncated else len(groups),
                "unresolved_count": sum(1 for f in facts if f.kind == "s3.unresolved"),
            },
            attrs={"prefix": uri, "truncated": truncated},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_s3_listing_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `s3.unresolved` com reason `read_error`; JSON invalido
    vira `malformed_json`. Nunca uma excecao que derruba quem chamou.
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
        return sort_facts(
            [
                _unresolved(anchor, "malformed_json", provenance),
                Fact(
                    kind="s3.analyzed",
                    subject=_file_subject(anchor),
                    measures={
                        "object_count": 0,
                        "control_object_count": 0,
                        "group_count": 0,
                        "unresolved_count": 1,
                    },
                    attrs={"prefix": "", "truncated": False},
                    provenance=provenance,
                ),
            ]
        )

    return extract_s3_listing(payload, anchor, sha)


def extract_s3_listing_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Uma listagem paginada chega como varios arquivos (`page-1.json`,
    `page-2.json`...), e cada um deles e um dump valido por si so. Falha em um
    arquivo nao interrompe os outros -- mesma convencao de
    `catalog_schema.extract_catalog_schema_tree`.
    """
    facts: list[Fact] = []
    for listing in sorted(root.rglob("*.json")):
        facts.extend(extract_s3_listing_path(listing, repo_root or root))
    return sort_facts(facts)
