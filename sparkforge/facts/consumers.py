"""Extrator do inventario DECLARADO de consumidores de tabela.

Diferente de todo outro extrator do pacote, este nao le um artefato produzido
por uma ferramenta: le um arquivo que uma pessoa escreveu. E deliberado. Quem
consome uma tabela nao esta no codigo do job que a escreve, nao esta no plano
fisico, nao esta no event log e nao esta no metadata Iceberg -- e conhecimento
da organizacao. Derivar do historico de queries do Athena veria so o Athena, e
com janela de retencao limitada: um consumidor Redshift, EMR ou QuickSight
ficaria invisivel, e invisivel viraria "sem consumidor", que e a resposta
errada com cara de resposta certa.

Shape esperado (`.sparkforge/consumers.yaml`, versionado com o repositorio):

```yaml
consumers:
  - table: glue_catalog.curated.pedidos
    service: athena
    owner: squad-analytics          # opcional
    note: dashboard executivo       # opcional
```

Este extrator desbloqueia SF-ENV-002, a armadilha mais cara documentada em
`knowledge/glue/runtime-matrix.md` secao 3: Glue 5.1 escreve Iceberg format
V3, o Athena nao le V3, e o modo de falha aparece no CONSUMIDOR, nao no job
que fez a migracao.

O silencio e explicito. Tabela ausente do inventario nao produz fact nenhum, e
por isso SF-ENV-002 nao dispara para ela -- ausencia de declaracao nao e
declaracao de ausencia. `env.consumers_analyzed` prova que o inventario foi
lido, e `measures.table_count` diz quantas tabelas ele cobre: um inventario
vazio e distinguivel de um inventario que nunca foi lido.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "consumers@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "env.consumer",
        "env.unresolved",
        "env.consumers_analyzed",
    }
)

# Servicos reconhecidos. Um valor fora desta lista NAO e rejeitado -- vira fact
# com o texto normalizado que o operador escreveu -- mas os daqui sao os que as
# regras do catalogo referenciam por nome, entao errar a grafia ("Athena",
# "athena-sql") faria SF-ENV-002 silenciosamente nao casar. Por isso a
# normalizacao e minima e previsivel: minusculas, sem espaco nas bordas.
KNOWN_SERVICES = frozenset(
    {"athena", "redshift", "emr", "quicksight", "sagemaker", "glue", "spark", "trino"}
)


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _table_subject(table: str) -> dict[str, Any]:
    return {"type": "table", "symbol": table}


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="env.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def extract_consumers(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um inventario ja carregado.

    Entrada malformada nunca levanta excecao: vira `env.unresolved` e a
    extracao segue com o que sobrar -- mesma convencao dos demais extratores.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}

    facts: list[Fact] = []
    tables: set[str] = set()

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_inventory", provenance))
        payload = {}

    entries = payload.get("consumers")
    if entries is not None and not isinstance(entries, list):
        facts.append(_unresolved(path, "malformed_inventory", provenance, section="consumers"))
        entries = None

    seen: set[tuple[str, str]] = set()
    for entry in entries or []:
        if not isinstance(entry, dict):
            facts.append(
                _unresolved(path, "malformed_inventory", provenance, section="consumers[]")
            )
            continue

        table = entry.get("table")
        if not isinstance(table, str) or not table.strip():
            facts.append(_unresolved(path, "missing_table", provenance))
            continue
        table = table.strip()

        service = entry.get("service")
        if not isinstance(service, str) or not service.strip():
            facts.append(_unresolved(path, "missing_service", provenance, table=table))
            continue
        service = service.strip().lower()

        tables.add(table)
        # Declarar o mesmo par duas vezes e erro de edicao, nao dois
        # consumidores: emitir dois facts identicos faria SF-ENV-002 produzir
        # dois findings para o mesmo problema.
        if (table, service) in seen:
            continue
        seen.add((table, service))

        attrs: dict[str, Any] = {
            "table": table,
            "service": service,
            "known_service": service in KNOWN_SERVICES,
        }
        for optional in ("owner", "note"):
            value = entry.get(optional)
            if isinstance(value, str) and value.strip():
                attrs[optional] = value.strip()

        facts.append(
            Fact(
                kind="env.consumer",
                subject=_table_subject(table),
                attrs=attrs,
                provenance=provenance,
            )
        )

    facts.append(
        Fact(
            kind="env.consumers_analyzed",
            subject=_file_subject(path),
            measures={
                "table_count": len(tables),
                "consumer_count": len(seen),
                "unresolved_count": sum(1 for f in facts if f.kind == "env.unresolved"),
            },
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_consumers_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um `.yaml`/`.yml`, ancorando o path relativo a `repo_root`."""
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [_unresolved(anchor, "read_error", empty_provenance, detail=str(exc))]

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return sort_facts(
            [
                _unresolved(anchor, "malformed_inventory", provenance, detail=str(exc).strip()),
                Fact(
                    kind="env.consumers_analyzed",
                    subject=_file_subject(anchor),
                    measures={"table_count": 0, "consumer_count": 0, "unresolved_count": 1},
                    provenance=provenance,
                ),
            ]
        )

    return extract_consumers(payload, anchor, sha)


def extract_consumers_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.yaml`/`*.yml` sob `root`.

    Um inventario pode ser dividido por dominio (`vendas.yaml`, `logistica.yaml`)
    sem que nada mude para as regras: o conjunto de facts e a uniao.
    """
    facts: list[Fact] = []
    seen: set[Path] = set()
    for pattern in ("*.yaml", "*.yml"):
        for inventory in sorted(root.rglob(pattern)):
            if inventory in seen:
                continue
            seen.add(inventory)
            facts.extend(extract_consumers_path(inventory, repo_root or root))
    return sort_facts(facts)
