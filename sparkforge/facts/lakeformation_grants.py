"""`lakeformation.grant` -- a PERMISSAO que a AWS respondeu, e nada mais.

Extrator do artefato de `sparkforge/collect/lakeformation.py`. Ele fecha dois
dos tres itens que `lakeformation.unresolved` nomeia: o grant do Lake Formation
e o registro da localizacao S3. O terceiro -- a policy do runtime role -- e outro
coletor, e a razao esta no docstring do coletor.

## A distincao que este modulo existe para preservar

Tres estados produzem a MESMA lista vazia de grants, e so o `status` do artefato
os separa:

    vazio            a tabela nao tem grant nenhum
    sem_permissao    quem coletou nao pode LER os grants
    sem_credencial   a chamada nunca aconteceu

Uma regra que trate os tres como "nao ha permissao" acusa a tabela governada
corretamente e a tabela que ninguem conseguiu inspecionar do mesmo jeito. Por
isso `lakeformation.grants.unresolved` sai com a razao nomeada, e
`lakeformation.grant` so e emitido quando o bloco respondeu `ok`.

## `registered` e ternario, e o terceiro valor e o que importa

`True` a localizacao esta registrada; `False` a AWS respondeu que ela nao
existe; `None` ninguem mediu -- sem permissao, sem credencial, ou sem
`--resource-arn` informado. Tratar `None` como `False` faria o motor afirmar
"nao registrada" sobre uma pergunta que nao foi feita, e e exatamente sobre
localizacao registrada que a §6 do documento de conhecimento declara conflito.

## O que ele NAO deriva

**Nao decide se a permissao basta.** `SELECT` bastar ou nao depende da operacao
e do modelo de acesso. O fact carrega a lista verbatim, e o juizo mora na regra.

**Nao normaliza o principal.** `DataLakePrincipalIdentifier` vem como ARN de
role, de usuario, `IAM_ALLOWED_PRINCIPALS`, ou identificador de conta em
cross-account. Reduzi-los a um formato so apagaria a diferenca entre
"concedido a este role" e "concedido a qualquer principal do IAM", que e a
distincao mais importante desta area.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "lakeformation_grants@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "lakeformation.grant",
        "lakeformation.registered_location",
        "lakeformation.data_lake_settings",
        "lakeformation.grants.unresolved",
        "lakeformation.grants.analyzed",
    }
)

# O principal que a AWS usa para dizer "qualquer principal do IAM resolve pelo
# modelo antigo". Ele nao e um role: e a ausencia de governanca fina, e a regra
# que o ler precisa poder distingui-lo de um ARN.
IAM_ALLOWED_PRINCIPALS = "IAM_ALLOWED_PRINCIPALS"


def _subject(payload: dict[str, Any], caminho: str) -> dict[str, Any]:
    # `table` e nao um tipo proprio: o schema de `Fact.subject` tem um enum
    # fechado, e o sujeito aqui E uma tabela do catalogo -- a mesma entidade que
    # `catalog.table_schema` e `iceberg.*` descrevem por outras oticas. Inventar
    # `lakeformation_table` faria o motor tratar a mesma tabela como duas coisas.
    return {
        "type": "table",
        "file": caminho,
        "symbol": f"{payload.get('database', '')}.{payload.get('table', '')}",
        "catalog_id": str(payload.get("catalog_id") or ""),
    }


def _provenance(caminho: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": caminho}


def _grants(payload: dict[str, Any], subject: dict[str, Any], prov: dict[str, Any]) -> list[Fact]:
    bloco = payload.get("permissions") or {}
    status = str(bloco.get("status") or "")
    if status != "ok":
        return [
            Fact(
                kind="lakeformation.grants.unresolved",
                subject=dict(subject),
                measures={},
                attrs={
                    "reason": status or "bloco_ausente",
                    "block": "permissions",
                    "unblocked_by": (
                        "conceder ao principal que coleta a permissao de ler os grants "
                        "(`lakeformation:ListPermissions`) e reexecutar `sparkforge "
                        "collect lakeformation`"
                    ),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        ]

    saida: list[Fact] = []
    for entrada in bloco.get("principals") or []:
        principal = str(
            ((entrada.get("Principal") or {}).get("DataLakePrincipalIdentifier")) or ""
        )
        permissoes = [str(p) for p in (entrada.get("Permissions") or [])]
        com_grant = [str(p) for p in (entrada.get("PermissionsWithGrantOption") or [])]
        recurso = entrada.get("Resource") or {}
        tabela = recurso.get("Table") or {}
        saida.append(
            Fact(
                kind="lakeformation.grant",
                subject={**subject, "symbol": f"{subject['symbol']}#{principal}"},
                measures={"permission_count": len(permissoes)},
                attrs={
                    "principal": principal,
                    "is_iam_allowed_principals": principal == IAM_ALLOWED_PRINCIPALS,
                    "permissions": sorted(permissoes),
                    "permissions_with_grant_option": sorted(com_grant),
                    # Os tres booleanos que as regras desta area comparam. Eles
                    # sao DERIVACAO da lista, nao juizo: dizem que o token esta
                    # la, nunca que ele basta para a operacao.
                    "has_select": "SELECT" in permissoes,
                    "has_all": "ALL" in permissoes,
                    "has_describe": "DESCRIBE" in permissoes,
                    "resource_database": str(tabela.get("DatabaseName") or ""),
                    "resource_table": str(tabela.get("Name") or ""),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        )

    if bloco.get("truncated"):
        saida.append(
            Fact(
                kind="lakeformation.grants.unresolved",
                subject=dict(subject),
                measures={"grants_collected": int(bloco.get("grants_collected") or 0)},
                attrs={
                    "reason": "paginacao_truncada",
                    "block": "permissions",
                    "unblocked_by": (
                        "a tabela tem mais grants do que o teto de paginas do coletor; "
                        "os que sairam sao validos e a lista NAO e completa"
                    ),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        )
    return saida


def _localizacao(
    payload: dict[str, Any], subject: dict[str, Any], prov: dict[str, Any]
) -> list[Fact]:
    bloco = payload.get("registered_location") or {}
    status = str(bloco.get("status") or "")
    registrada = bloco.get("registered")

    if registrada is None:
        return [
            Fact(
                kind="lakeformation.grants.unresolved",
                subject=dict(subject),
                measures={},
                attrs={
                    "reason": status or "bloco_ausente",
                    "block": "registered_location",
                    "unblocked_by": (
                        "informar `--resource-arn` com a localizacao S3 da tabela e "
                        "conceder `lakeformation:DescribeResource` ao principal que coleta"
                    ),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        ]

    return [
        Fact(
            kind="lakeformation.registered_location",
            subject=dict(subject),
            measures={},
            attrs={
                "registered": bool(registrada),
                "resource_arn": str(bloco.get("resource_arn") or ""),
                "role_arn": str(bloco.get("role_arn") or ""),
                "hybrid_access_enabled": bloco.get("hybrid_access_enabled"),
                "with_federation": bloco.get("with_federation"),
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    ]


def _settings(payload: dict[str, Any], subject: dict[str, Any], prov: dict[str, Any]) -> list[Fact]:
    bloco = payload.get("data_lake_settings") or {}
    status = str(bloco.get("status") or "")
    if status != "ok":
        return [
            Fact(
                kind="lakeformation.grants.unresolved",
                subject=dict(subject),
                measures={},
                attrs={
                    "reason": status or "bloco_ausente",
                    "block": "data_lake_settings",
                    "unblocked_by": (
                        "conceder `lakeformation:GetDataLakeSettings` ao principal que "
                        "coleta -- e ele que revela o passo de CONTA que precede "
                        "qualquer grant sob Full Table Access"
                    ),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        ]

    return [
        Fact(
            kind="lakeformation.data_lake_settings",
            subject=dict(subject),
            measures={},
            attrs={
                "allow_full_table_external_data_access": bloco.get(
                    "allow_full_table_external_data_access"
                ),
                "allow_external_data_filtering": bloco.get("allow_external_data_filtering"),
                "external_data_filtering_allow_list": list(
                    bloco.get("external_data_filtering_allow_list") or []
                ),
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    ]


def extract_lakeformation_path(path: Path | str, repo_root: Path | str | None = None) -> list[Fact]:
    """Le UM artefato de `collect lakeformation` e devolve os facts dele."""
    alvo = Path(path)
    relativo = alvo.name
    if repo_root is not None:
        try:
            relativo = alvo.resolve().relative_to(Path(repo_root).resolve()).as_posix()
        except ValueError:
            relativo = alvo.name

    payload = json.loads(alvo.read_text(encoding="utf-8"))
    subject = _subject(payload, relativo)
    prov = _provenance(relativo)

    saida: list[Fact] = []
    saida.extend(_grants(payload, subject, prov))
    saida.extend(_localizacao(payload, subject, prov))
    saida.extend(_settings(payload, subject, prov))
    # A sentinela sai SEMPRE, e e ela que distingue "o artefato foi lido e nao
    # tinha nada" de "ninguem leu artefato nenhum" -- o mesmo papel de
    # `tf.module_analyzed` e `cloudwatch.logs.analyzed`.
    saida.append(
        Fact(
            kind="lakeformation.grants.analyzed",
            subject=dict(subject),
            measures={"facts_emitted": len(saida)},
            attrs={"status": str(payload.get("status") or ""), "extractor": EXTRACTOR_ID},
            provenance=prov,
        )
    )
    return sort_facts(saida)


def extract_lakeformation_tree(
    root: Path | str, repo_root: Path | str | None = None
) -> list[Fact]:
    """Todos os artefatos `*.json` de um diretorio, na ordem do nome."""
    saida: list[Fact] = []
    # `iter_source_files` e nao `glob` cru, pela mesma razao de `iam_access.py`:
    # `root` e diretorio que o operador aponta. Ver `tests/test_facts_scan.py`.
    for arquivo in iter_source_files(root, "*.json"):
        saida.extend(extract_lakeformation_path(arquivo, repo_root=repo_root))
    return sort_facts(saida)


def build_grants(facts: Sequence[Fact]) -> list[Fact]:  # pragma: no cover - simetria
    """Este modulo LE artefato; nao ha derivacao pura aqui. A funcao existe para
    que o nome nao seja confundido com `sparkforge/facts/lakeformation.py`, que
    e derivacao e nao le artefato nenhum."""
    raise NotImplementedError(
        "lakeformation_grants le ARTEFATO. Para a derivacao sobre facts, use "
        "sparkforge.facts.lakeformation.build_lakeformation"
    )


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "IAM_ALLOWED_PRINCIPALS",
    "extract_lakeformation_path",
    "extract_lakeformation_tree",
]
