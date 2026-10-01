"""`glue.resource_link` -- a TOPOLOGIA do catalogo que a AWS respondeu.

Extrator do artefato de `sparkforge/collect/glue_resource_link.py`. Ele fecha a
perna que `sparkforge/lakeformation/graph.py` devolvia `unresolved` desde que o
grafo passou a ler fact, e da medida a uma afirmacao que vivia so em prosa: a §1
de `knowledge/glue/lakeformation-fgac.md` declara que o resource link **precisa
ter o mesmo nome do recurso na conta de origem**, e ate aqui nenhum kind
carregava nome de link nenhum para conferir isso.

## A unica derivacao deste modulo, e por que ela e derivacao e nao juizo

`name_matches_source` compara dois campos que o coletor guardou verbatim. Ela diz
que os nomes sao iguais ou diferentes -- nunca que a configuracao esta certa ou
errada. O juizo (a AWS declara suportado apenas o nome identico) mora na regra
`SF-XACC-002`, com fonte T1 ao lado.

A comparacao nao e a mesma nos dois tipos, e colapsa-la seria defeito:

    link de TABELA   nome do link  vs  `TargetTable.Name`
    link de BANCO    nome do link  vs  `TargetDatabase.DatabaseName`

`TargetDatabase` nao tem campo `Name` -- o nome do recurso de origem E o
`DatabaseName`. Comparar contra um campo que nao existe daria `False` em todo
link de banco correto.

## `resolved` e ternario, e o `False` dele e AMBIGUO

`True` o recurso de origem respondeu; `False` a AWS devolveu
`EntityNotFoundException`; `None` ninguem mediu -- sem permissao, sem credencial,
ou `verify_target` desligado.

E o `False` NAO quer dizer "nao existe". Sob Lake Formation, um recurso a que o
principal nao tem permissao responde `EntityNotFoundException` -- absence e
denial chegam pelo mesmo codigo. Por isso `target_absence_is_ambiguous` sai `True`
junto, e a regra que consome isso investiga em vez de acusar. Reduzir os dois
sentidos a um faria o motor afirmar "o link esta pendurado" sobre um link intacto
que o coletor so nao pode enxergar.

## O que ele NAO deriva

**Nao decide se ha cross-account.** `cross_account` compara os dois `CatalogId`
medidos e sai `None` quando algum deles falta. Preenche-lo com a conta da
credencial seria inventar o dado que a pergunta pede.

**Nao le grant nenhum.** Link intacto sobre tabela sem permissao e um estado
real, e e `lakeformation.grant` que o descreve. As duas pernas do grafo sao
independentes, e juntar as duas medidas num fact so apagaria qual delas falhou.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "glue_resource_link@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "glue.resource_link",
        "glue.resource_link.target",
        "glue.resource_link.unresolved",
        "glue.resource_link.analyzed",
    }
)

TIPO_TABELA = "table"
TIPO_BANCO = "database"


def _simbolo(payload: dict[str, Any]) -> str:
    banco = str(payload.get("database") or "")
    tabela = str(payload.get("table") or "")
    return f"{banco}.{tabela}" if tabela else banco


def _subject(payload: dict[str, Any], caminho: str) -> dict[str, Any]:
    # `table` pelos dois tipos, e pela mesma razao de `lakeformation_grants`: o
    # enum de `Fact.subject` e fechado, e o sujeito aqui E uma entidade do
    # catalogo. Um link de BANCO nao ganha tipo proprio -- inventar um faria o
    # motor tratar o mesmo catalogo como duas coisas.
    return {
        "type": "table",
        "file": caminho,
        "symbol": _simbolo(payload),
        "catalog_id": str(payload.get("catalog_id") or ""),
    }


def _provenance(caminho: str) -> dict[str, Any]:
    return {"extractor": EXTRACTOR_ID, "artifact": caminho}


def _unresolved(
    subject: dict[str, Any], prov: dict[str, Any], *, reason: str, block: str, unblocked_by: str
) -> Fact:
    return Fact(
        kind="glue.resource_link.unresolved",
        subject=dict(subject),
        measures={},
        attrs={
            "reason": reason,
            "block": block,
            "unblocked_by": unblocked_by,
            "extractor": EXTRACTOR_ID,
        },
        provenance=prov,
    )


def _nome_da_origem(bloco: dict[str, Any]) -> str:
    """O nome do recurso na conta de origem, pelo tipo do alvo.

    Link de banco nao tem `TargetDatabase.Name`; o nome do recurso e o proprio
    `DatabaseName`. Comparar contra o campo inexistente daria `False` em todo
    link de banco correto.
    """
    if str(bloco.get("target_type") or "") == TIPO_TABELA:
        return str(bloco.get("target_name") or "")
    return str(bloco.get("target_database") or "")


def _cross_account(bloco: dict[str, Any]) -> bool | None:
    consumidor = str(bloco.get("link_catalog_id") or "")
    origem = str(bloco.get("target_catalog_id") or "")
    if not consumidor or not origem:
        return None
    return consumidor != origem


def _link(payload: dict[str, Any], subject: dict[str, Any], prov: dict[str, Any]) -> list[Fact]:
    bloco = payload.get("link") or {}
    status = str(bloco.get("status") or "")
    if status != "ok":
        return [
            _unresolved(
                subject,
                prov,
                reason=status or "bloco_ausente",
                block="link",
                unblocked_by=(
                    "conceder `glue:GetTable` (ou `glue:GetDatabase`) ao principal que "
                    "coleta, no catalogo CONSUMIDOR, e reexecutar `sparkforge collect "
                    "glue-resource-link`"
                ),
            )
        ]

    e_link = bool(bloco.get("is_resource_link"))
    nome_do_link = str(bloco.get("link_name") or "")
    nome_da_origem = _nome_da_origem(bloco)
    return [
        Fact(
            kind="glue.resource_link",
            subject=dict(subject),
            measures={},
            attrs={
                "is_resource_link": e_link,
                "target_type": str(bloco.get("target_type") or ""),
                "link_catalog_id": str(bloco.get("link_catalog_id") or ""),
                "link_database": str(bloco.get("link_database") or ""),
                "link_name": nome_do_link,
                "target_catalog_id": str(bloco.get("target_catalog_id") or ""),
                "target_database": str(bloco.get("target_database") or ""),
                "target_name": str(bloco.get("target_name") or ""),
                "target_region": str(bloco.get("target_region") or ""),
                # A DERIVACAO deste modulo. `None` quando o objeto nao e link:
                # tabela comum nao tem recurso de origem, e responder `False`
                # ali seria acusar de nome divergente algo que nao tem nome com
                # o que divergir.
                "name_matches_source": (
                    (nome_do_link == nome_da_origem) if e_link else None
                ),
                "source_resource_name": nome_da_origem if e_link else "",
                "cross_account": _cross_account(bloco) if e_link else None,
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    ]


def _alvo(payload: dict[str, Any], subject: dict[str, Any], prov: dict[str, Any]) -> list[Fact]:
    bloco = payload.get("target") or {}
    status = str(bloco.get("status") or "")

    if status not in {"ok", "nao_encontrado"}:
        return [
            _unresolved(
                subject,
                prov,
                reason=str(bloco.get("reason") or status or "bloco_ausente"),
                block="target",
                unblocked_by=(
                    "conceder ao principal que coleta permissao de leitura no catalogo de "
                    "ORIGEM (`glue:GetTable`/`glue:GetDatabase` na conta dona), e coletar "
                    "com `--verify-target`"
                ),
            )
        ]

    resolvido = status == "ok"
    return [
        Fact(
            kind="glue.resource_link.target",
            subject=dict(subject),
            measures={},
            attrs={
                "resolved": resolvido,
                "catalog_id": str(bloco.get("catalog_id") or ""),
                "database": str(bloco.get("database") or ""),
                "name": str(bloco.get("name") or ""),
                "resolved_name": str(bloco.get("resolved_name") or ""),
                "aws_error_code": str(bloco.get("aws_error_code") or ""),
                # A ambiguidade sai NOMEADA, e nao resolvida. `EntityNotFound`
                # sobre recurso nao autorizado e a mesma resposta que sobre
                # recurso inexistente, e a regra que le isto investiga.
                "target_absence_is_ambiguous": not resolvido,
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    ]


def extract_glue_resource_link_path(
    path: Path | str, repo_root: Path | str | None = None
) -> list[Fact]:
    """Le UM artefato de `collect glue-resource-link` e devolve os facts dele."""
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
    saida.extend(_link(payload, subject, prov))
    saida.extend(_alvo(payload, subject, prov))
    # A sentinela sai SEMPRE, e e ela que distingue "o artefato foi lido e nao
    # tinha nada" de "ninguem leu artefato nenhum" -- o mesmo papel de
    # `lakeformation.grants.analyzed` e `tf.module_analyzed`.
    saida.append(
        Fact(
            kind="glue.resource_link.analyzed",
            subject=dict(subject),
            measures={"facts_emitted": len(saida)},
            attrs={"status": str(payload.get("status") or ""), "extractor": EXTRACTOR_ID},
            provenance=prov,
        )
    )
    return sort_facts(saida)


def extract_glue_resource_link_tree(
    root: Path | str, repo_root: Path | str | None = None
) -> list[Fact]:
    """Todos os artefatos `*.json` de um diretorio, na ordem do nome."""
    saida: list[Fact] = []
    for arquivo in iter_source_files(root, "*.json"):
        saida.extend(extract_glue_resource_link_path(arquivo, repo_root=repo_root))
    return sort_facts(saida)


def build_glue_resource_link(facts: Sequence[Fact]) -> list[Fact]:  # pragma: no cover - simetria
    """Este modulo LE artefato; nao ha derivacao pura aqui."""
    raise NotImplementedError(
        "glue_resource_link le ARTEFATO. A perna do grafo que consome estes facts e "
        "sparkforge.lakeformation.graph.build_access_graph"
    )


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_glue_resource_link_path",
    "extract_glue_resource_link_tree",
]
