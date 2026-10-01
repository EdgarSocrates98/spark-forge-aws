"""`iam.access_decision` -- QUEM negou, e nao apenas que negou.

Extrator do artefato de `sparkforge/collect/iam_access.py`. Ele fecha o terceiro
item que `lakeformation.unresolved` nomeia: a policy do runtime role. E ele o
fecha por SIMULACAO e nao por parse, pela razao que o docstring do coletor
mede -- boundary, SCP, deny explicito e condicao nao aparecem no documento do
role.

## As quatro respostas, e as tres primeiras exigem consertos DIFERENTES

`EvalDecision` da AWS tem quatro valores, e colapsa-los num booleano
`autorizado` apagaria a informacao que decide o conserto:

    allowed          a acao passa
    implicitDeny     nenhuma policy concede -- o conserto e ACRESCENTAR
    explicitDeny     alguma policy nega -- acrescentar nao resolve, e preciso
                     achar o `Deny` e decidir se ele sai
    (boundary/SCP)   a decisao veio de CIMA do role, e mexer na policy dele nao
                     muda nada

`attrs.denied_by` nomeia a camada, e ele e a razao de este extrator existir:
"adicione a permissao" e conselho errado em tres dos quatro casos.

## O que ele NAO afirma

**Nao afirma que a operacao real vai passar.** A AWS avalia policies; ela nao
tenta a chamada. Condicao que dependa de contexto de requisicao e avaliada com o
contexto do simulador, que nao e o do job -- e `missing_context_values` carrega
exatamente as chaves que faltaram.

**Nao cobre policy de RECURSO.** `SimulatePrincipalPolicy` avalia as policies de
identidade mais boundary e SCP. Bucket policy, key policy do KMS e Glue resource
policy sao outra avaliacao, e um `allowed` aqui com bucket policy negando ainda
falha. `iam.access.unresolved` publica esse limite em todo artefato.

**`allowed` sem recurso nao e `allowed` naquele recurso.** Sem `--resource-arn`
a simulacao responde sobre `*`. `attrs.scoped_to_resource` diz qual das duas
perguntas foi feita, e sem ele as duas seriam indistinguiveis no fact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "iam_access@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "iam.access_decision",
        "iam.access.unresolved",
        "iam.access.analyzed",
    }
)

DECISAO_PERMITIDA = "allowed"
DECISAO_NEGADA_IMPLICITA = "implicitDeny"
DECISAO_NEGADA_EXPLICITA = "explicitDeny"


def _denied_by(item: dict[str, Any], decisao: str) -> str:
    """A CAMADA que decidiu, e ela e o que separa tres consertos diferentes.

    A ordem importa: uma negacao de SCP ou de boundary vence a policy do role, e
    reportar `explicit`/`implicit` nesse caso mandaria o operador editar um
    documento que nao decide nada.
    """
    if decisao == DECISAO_PERMITIDA:
        return ""
    if item.get("allowed_by_organizations") is False:
        return "service_control_policy"
    if item.get("allowed_by_permissions_boundary") is False:
        return "permissions_boundary"
    if decisao == DECISAO_NEGADA_EXPLICITA:
        return "explicit_deny"
    if decisao == DECISAO_NEGADA_IMPLICITA:
        return "implicit_deny"
    return "desconhecida"


def _subject(payload: dict[str, Any], caminho: str) -> dict[str, Any]:
    return {
        "type": "job_run",
        "file": caminho,
        "symbol": str(payload.get("role_arn") or ""),
    }


def extract_iam_access_path(path: Path | str, repo_root: Path | str | None = None) -> list[Fact]:
    alvo = Path(path)
    relativo = alvo.name
    if repo_root is not None:
        try:
            relativo = alvo.resolve().relative_to(Path(repo_root).resolve()).as_posix()
        except ValueError:
            relativo = alvo.name

    payload = json.loads(alvo.read_text(encoding="utf-8"))
    subject = _subject(payload, relativo)
    prov = {"extractor": EXTRACTOR_ID, "artifact": relativo}
    status = str(payload.get("status") or "")
    escopado = bool(payload.get("scoped_to_resource"))

    saida: list[Fact] = []

    if status != "ok":
        saida.append(
            Fact(
                kind="iam.access.unresolved",
                subject=dict(subject),
                measures={},
                attrs={
                    "reason": status or "status_ausente",
                    "unblocked_by": (
                        "conceder `iam:SimulatePrincipalPolicy` ao principal que coleta, "
                        "e conferir que o role existe na conta simulada"
                    ),
                    "extractor": EXTRACTOR_ID,
                },
                provenance=prov,
            )
        )
    else:
        for item in payload.get("results") or []:
            decisao = str(item.get("decision") or "")
            acao = str(item.get("action") or "")
            recurso = str(item.get("resource") or "")
            saida.append(
                Fact(
                    kind="iam.access_decision",
                    subject={**subject, "symbol": f"{subject['symbol']}#{acao}@{recurso}"},
                    measures={"matched_statements": int(item.get("matched_statements") or 0)},
                    attrs={
                        "role_arn": subject["symbol"],
                        "action": acao,
                        "resource": recurso,
                        "decision": decisao,
                        "allowed": decisao == DECISAO_PERMITIDA,
                        "denied_by": _denied_by(item, decisao),
                        # A pergunta que foi feita. Sem ele, "allowed sobre `*`"
                        # e "allowed naquela tabela" seriam o mesmo fact.
                        "scoped_to_resource": escopado,
                        "missing_context_values": list(
                            item.get("missing_context_values") or []
                        ),
                        "extractor": EXTRACTOR_ID,
                    },
                    provenance=prov,
                )
            )

        if payload.get("truncated"):
            saida.append(
                Fact(
                    kind="iam.access.unresolved",
                    subject=dict(subject),
                    measures={"results_collected": int(payload.get("results_collected") or 0)},
                    attrs={
                        "reason": "paginacao_truncada",
                        "unblocked_by": (
                            "reduzir a lista de acoes ou de recursos; as decisoes que "
                            "sairam sao validas e a lista NAO e completa"
                        ),
                        "extractor": EXTRACTOR_ID,
                    },
                    provenance=prov,
                )
            )

    # O limite estrutural sai SEMPRE, inclusive quando tudo respondeu `ok`: a
    # simulacao nao avalia policy de RECURSO, e um `allowed` aqui com bucket
    # policy negando ainda falha. Publicar isso e o que impede o achado de
    # prometer mais do que mediu.
    saida.append(
        Fact(
            kind="iam.access.unresolved",
            subject=dict(subject),
            measures={},
            attrs={
                "reason": "policy_de_recurso_nao_avaliada",
                "unblocked_by": (
                    "bucket policy do S3, key policy do KMS e Glue resource policy sao "
                    "avaliacao SEPARADA, e nenhum artefato deste motor as coleta hoje"
                ),
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    )

    saida.append(
        Fact(
            kind="iam.access.analyzed",
            subject=dict(subject),
            measures={"decisions": len([f for f in saida if f.kind == "iam.access_decision"])},
            attrs={
                "status": status,
                "scoped_to_resource": escopado,
                "extractor": EXTRACTOR_ID,
            },
            provenance=prov,
        )
    )
    return sort_facts(saida)


def extract_iam_access_tree(root: Path | str, repo_root: Path | str | None = None) -> list[Fact]:
    saida: list[Fact] = []
    # `iter_source_files` e nao `glob` cru: `root` e diretorio que o OPERADOR
    # aponta, e a varredura compartilhada aplica denylist e teto. Este modulo
    # nasceu com `glob` direto e o gate estrutural de `tests/test_facts_scan.py`
    # o pegou -- ele varre `sparkforge/` inteiro por AST, e as duas formas
    # (`glob` e `rglob`) contam.
    for arquivo in iter_source_files(root, "*.json"):
        saida.extend(extract_iam_access_path(arquivo, repo_root=repo_root))
    return sort_facts(saida)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_iam_access_path",
    "extract_iam_access_tree",
]
