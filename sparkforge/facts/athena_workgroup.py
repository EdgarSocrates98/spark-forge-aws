"""Extrator de Facts a partir de um dump JSON já coletado de workgroups do
Amazon Athena (`athena.get_work_group`).

Como `catalog_schema.py`/`iceberg_metadata.py`, este modulo NAO coleta nada: a
coleta e responsabilidade de `sparkforge.collect.aws.collect_athena_workgroup`
(ou de uma coleta manual equivalente). Este extrator so le o JSON ja salvo em
disco. Modulo separado de `catalog_schema.py` -- em vez de mais um `kind`
dentro dele -- porque o dump de origem tem forma completamente diferente
(workgroups do Athena via `get_work_group`, nao tabelas do Glue Data Catalog
via `GetTables`/`GetTable`) e existe para desbloquear uma unica regra,
SF-ATH-004 (`rules/catalog/athena.yaml`). O shape esperado do dump, uma lista
de workgroups:

```json
{
  "workgroups": [
    {
      "name": "primary",
      "engine_version": {
        "effective_engine_version": "Athena engine version 3",
        "selected_engine_version": "AUTO"
      },
      "state": "ENABLED",
      "bytes_scanned_cutoff": 1099511627776,
      "output_location": "s3://bucket/results/"
    }
  ]
}
```

`engine_version.effective_engine_version` e uma string livre da API do Athena
("Athena engine version 3", "Athena engine version 2"), nunca um inteiro --
mas `measures.engine_version` (que `SF-ATH-004` compara com
`expr: "measures.engine_version < 3"`) so pode ser um numero, contrato de
`Fact.measures` (`sparkforge/findings/models.py`). Este extrator precisa
portanto extrair o inteiro do texto, e o fazer com seguranca e o unico
trabalho no de verdade deste modulo: se o parsing fabricasse um valor default
(0, por exemplo) para uma string que nao consegue interpretar, a regra
dispararia sobre um workgroup cuja engine version real e desconhecida --
exatamente a resposta autoritativa-porem-errada que este projeto existe para
evitar. Por isso uma string sem um inteiro reconhecivel NUNCA vira
`athena.workgroup`: vira `athena.unresolved` com
`attrs.reason = "unparseable_engine_version"`, e a regra simplesmente nao tem
fact para avaliar naquele workgroup (skip por `requires_facts`, nunca um falso
positivo nem um falso negativo silencioso). Mesmo raciocinio para um bloco
`engine_version` ausente ou malformado: vira `athena.unresolved` com
`attrs.reason = "missing_engine_version"`, nunca um fact com o campo omitido
silenciosamente.

Como `catalog_schema.py`/`iceberg_metadata.py`: extrator puro e
deterministico. Nunca aplica limiar, nunca atribui severidade, nunca infere o
que o dump nao diz.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "athena_workgroup@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "athena.workgroup",
        "athena.unresolved",
        "athena.analyzed",
    }
)

# "Athena engine version 3" -> 3. Casa "version" seguido de digitos em
# qualquer lugar da string -- nao so no final -- para tolerar variacoes que a
# API pode devolver ("Athena engine version 3 (PySpark on Athena preview)")
# sem exigir um formato exato. `re.IGNORECASE` porque a API nao garante
# capitalizacao estavel.
_ENGINE_VERSION_RE = re.compile(r"version\s+(\d+)", re.IGNORECASE)


def _file_subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _workgroup_subject(name: str) -> dict[str, Any]:
    return {"type": "job_run", "symbol": name}


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="athena.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _parse_engine_version(effective: str) -> int | None:
    """Extrai o inteiro de `"Athena engine version 3"` -> `3`. `None` quando
    nenhum inteiro reconhecivel aparece -- nunca um valor adivinhado."""
    match = _ENGINE_VERSION_RE.search(effective)
    if match is None:
        return None
    return int(match.group(1))


def _workgroup_facts(
    entry: dict[str, Any], name: str, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    subject = _workgroup_subject(name)
    engine_version_raw = entry.get("engine_version")

    effective: str | None = None
    selected: str | None = None
    if isinstance(engine_version_raw, dict):
        eff = engine_version_raw.get("effective_engine_version")
        effective = eff if isinstance(eff, str) else None
        sel = engine_version_raw.get("selected_engine_version")
        selected = sel if isinstance(sel, str) else None

    if effective is None:
        return [_unresolved(path, "missing_engine_version", provenance, name=name)]

    parsed = _parse_engine_version(effective)
    if parsed is None:
        return [
            _unresolved(
                path,
                "unparseable_engine_version",
                provenance,
                name=name,
                effective_engine_version=effective,
            )
        ]

    measures: dict[str, Any] = {"engine_version": parsed}
    cutoff = entry.get("bytes_scanned_cutoff")
    if _is_number(cutoff):
        measures["bytes_scanned_cutoff"] = cutoff

    state = entry.get("state")
    attrs: dict[str, Any] = {
        "name": name,
        "state": state if isinstance(state, str) else None,
        "effective_engine_version": effective,
        "selected_engine_version": selected,
    }

    return [
        Fact(
            kind="athena.workgroup",
            subject=subject,
            measures=measures,
            attrs=attrs,
            provenance=provenance,
        )
    ]


def extract_athena_workgroup(
    payload: dict[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um dump ja carregado (`dict`) de workgroups do Athena.

    Nunca levanta excecao por payload malformado: dict sem `workgroups`, uma
    entrada sem `name`, ou uma secao que nao e do tipo esperado, viram
    `athena.unresolved` e a extracao segue com o que sobrar -- mesma convencao
    de `catalog_schema.extract_catalog_schema`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}

    facts: list[Fact] = []
    workgroup_count = 0

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
    else:
        workgroups_raw = payload.get("workgroups")
        if workgroups_raw is not None and not isinstance(workgroups_raw, list):
            facts.append(_unresolved(path, "malformed_json", provenance, section="workgroups"))
        elif isinstance(workgroups_raw, list):
            for entry in workgroups_raw:
                if not isinstance(entry, dict):
                    facts.append(
                        _unresolved(path, "malformed_json", provenance, section="workgroups[]")
                    )
                    continue
                name = entry.get("name")
                if not isinstance(name, str) or not name.strip():
                    facts.append(_unresolved(path, "missing_workgroup_name", provenance))
                    continue
                workgroup_count += 1
                facts.extend(_workgroup_facts(entry, name, path, provenance))
            # `workgroups_raw is None`: chave ausente do payload -- nada foi
            # coletado neste dump, mas o dump em si e valido (nao e um erro).

    unresolved_count = sum(1 for f in facts if f.kind == "athena.unresolved")

    # Sentinela: prova de que a extracao rodou sobre este dump, mesma funcao
    # de `catalog.analyzed`/`iceberg.table_analyzed`. Subject de arquivo (nao
    # de workgroup): um dump pode descrever VARIOS workgroups.
    facts.append(
        Fact(
            kind="athena.analyzed",
            subject=_file_subject(path),
            measures={"workgroup_count": workgroup_count, "unresolved_count": unresolved_count},
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_athena_workgroup_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir o arquivo vira um unico Fact `athena.unresolved` com reason
    "read_error"; JSON invalido vira "malformed_json". Nunca uma excecao que
    derruba quem chamou -- mesma convencao de
    `catalog_schema.extract_catalog_schema_path`.
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

    return extract_athena_workgroup(payload, anchor, artifact_sha256=sha)


def extract_athena_workgroup_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico (permissao,
    encoding invalido, qualquer excecao inesperada) vira um unico Fact
    `athena.unresolved` para aquele arquivo, e a travessia continua -- mesma
    convencao de `catalog_schema.extract_catalog_schema_tree`.
    """
    facts: list[Fact] = []
    for json_file in sorted(root.rglob("*.json")):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_athena_workgroup_path(json_file, repo_root))
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
