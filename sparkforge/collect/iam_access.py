"""Coletor de DECISAO de IAM -- a resposta da AWS, nao a nossa leitura da policy.

## Simular, e nao parsear, e a decisao de desenho desta entrega

O terceiro item que `lakeformation.unresolved` nomeia e a policy do runtime
role. O caminho obvio seria `iam:GetRolePolicy` mais `GetPolicyVersion`, ler o
JSON e decidir se a acao esta autorizada. **Esse caminho erra exatamente nos
casos que importam:**

  * permission boundary anexado ao role recorta o que a policy concede, e a
    policy nao o menciona;
  * service control policy da organizacao nega acima do role, e nada no
    documento do role aparece;
  * `Deny` explicito em QUALQUER policy anexada vence todo `Allow`, e achar
    todas exige enumerar inline, managed e boundary;
  * `Condition` depende de contexto de requisicao que um parser nao tem.

`iam:SimulatePrincipalPolicy` avalia tudo isso do lado da AWS e devolve o
veredito. O que sai daqui e **medida**, nao inferencia -- e e essa a diferenca
entre este coletor e um leitor de policy.

## O que a simulacao NAO e

**Nao e a execucao.** A AWS avalia as policies; ela nao tenta a chamada. Uma
condicao que dependa de contexto de requisicao (IP de origem, tag de sessao,
MFA) e avaliada com o contexto que o simulador tem, que nao e o do job. O fact
carrega `decision` verbatim e nunca promete que a operacao real vai passar.

**Nao inclui a policy do BUCKET nem a key policy do KMS.** `SimulatePrincipalPolicy`
avalia as policies baseadas em IDENTIDADE (as do principal) mais o boundary e a
SCP. Policy de recurso -- bucket policy, key policy, Glue resource policy -- e
outra avaliacao. Um `allowed` aqui com bucket policy negando ainda falha, e a
recusa nomeada diz isso em vez de esconder.

**Nao decide qual acao importa.** A lista default vem da documentacao da AWS
para Lake Formation e Glue, e e SUBSTITUIVEL: o operador que sabe qual operacao
falhou passa as acoes dela.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import (
    CollectionFailed,
    _offline_hit,
    _write_and_register,
)
from sparkforge.collect.base import require_boto3

STATUS_OK = "ok"
STATUS_NAO_ENCONTRADO = "nao_encontrado"
STATUS_SEM_PERMISSAO = "sem_permissao"
STATUS_SEM_CREDENCIAL = "sem_credencial"

# As acoes que a documentacao da AWS nomeia para Lake Formation e Glue, na
# ordem em que uma operacao as atravessa: primeiro resolver a tabela no
# catalogo (`glue:Get*`), depois obter a credencial (`lakeformation:*`), e so
# entao tocar o dado (`s3:*`, `kms:*`).
#
# A lista e DEFAULT e nao dogma. Quem sabe qual operacao falhou passa as acoes
# dela -- e passar a lista inteira quando a pergunta e sobre uma escrita
# produz 14 decisoes das quais 10 nao dizem nada sobre o caso.
ACOES_PADRAO = (
    "glue:GetDatabase",
    "glue:GetTable",
    "glue:GetPartitions",
    "glue:CreateTable",
    "glue:UpdateTable",
    "lakeformation:GetDataAccess",
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket",
    "s3:AbortMultipartUpload",
    "kms:Decrypt",
    "kms:Encrypt",
    "kms:GenerateDataKey",
)

# Teto de paginas. `simulate_principal_policy` pagina por resultado, e uma lista
# grande de acoes cruzada com varios recursos cresce depressa.
_MAX_PAGINAS = 10


def iam_access_path(role_arn: str) -> str:
    """Um artefato por ROLE. A chave e o nome do role, e nao o ARN inteiro:
    o ARN carrega o id da conta, e o nome de arquivo com `:` e `/` nao sobrevive
    a todo sistema de arquivos."""
    nome = role_arn.rsplit("/", 1)[-1] or "role"
    conta = ""
    partes = role_arn.split(":")
    if len(partes) > 4:
        conta = partes[4]
    prefixo = f"{conta}_" if conta else ""
    return f".sparkforge/artifacts/iam_access/{prefixo}{nome}.json"


def _codigo_de_erro(exc: BaseException) -> str:
    resposta = getattr(exc, "response", None)
    if isinstance(resposta, dict):
        return str((resposta.get("Error") or {}).get("Code") or "")
    return ""


def _classificar(exc: BaseException) -> str | None:
    nome = type(exc).__name__
    if nome in {"NoCredentialsError", "PartialCredentialsError", "NoRegionError"}:
        return STATUS_SEM_CREDENCIAL
    codigo = _codigo_de_erro(exc)
    if codigo in {"NoSuchEntity", "NoSuchEntityException"}:
        return STATUS_NAO_ENCONTRADO
    if codigo in {"AccessDenied", "AccessDeniedException", "UnauthorizedException"}:
        return STATUS_SEM_PERMISSAO
    if codigo in {"ExpiredTokenException", "InvalidClientTokenId", "UnrecognizedClientException"}:
        return STATUS_SEM_CREDENCIAL
    return None


def _simular(
    client: Any, *, role_arn: str, acoes: list[str], recursos: list[str]
) -> tuple[list[dict[str, Any]], str, bool]:
    resultados: list[dict[str, Any]] = []
    truncado = False
    try:
        marker = None
        for _ in range(_MAX_PAGINAS):
            argumentos: dict[str, Any] = {
                "PolicySourceArn": role_arn,
                "ActionNames": acoes,
            }
            if recursos:
                argumentos["ResourceArns"] = recursos
            if marker:
                argumentos["Marker"] = marker
            resposta = client.simulate_principal_policy(**argumentos)
            for item in resposta.get("EvaluationResults") or []:
                org = item.get("OrganizationsDecisionDetail") or {}
                boundary = item.get("PermissionsBoundaryDecisionDetail") or {}
                resultados.append(
                    {
                        "action": str(item.get("EvalActionName") or ""),
                        "resource": str(item.get("EvalResourceName") or ""),
                        "decision": str(item.get("EvalDecision") or ""),
                        "matched_statements": len(item.get("MatchedStatements") or []),
                        "missing_context_values": [
                            str(v) for v in (item.get("MissingContextValues") or [])
                        ],
                        # Os dois detalhes que separam "a policy nao concede" de
                        # "algo acima dela nega". Sao os campos que um parser de
                        # documento NUNCA teria.
                        "allowed_by_organizations": org.get("AllowedByOrganizations"),
                        "allowed_by_permissions_boundary": boundary.get(
                            "AllowedByPermissionsBoundary"
                        ),
                    }
                )
            if not resposta.get("IsTruncated"):
                return resultados, STATUS_OK, truncado
            marker = resposta.get("Marker")
        truncado = True
        return resultados, STATUS_OK, truncado
    except CollectionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 -- reclassificado ou re-levantado
        status = _classificar(exc)
        if status is None:
            raise
        return [], status, truncado


def collect_iam_access(
    role_arn: str,
    root: Path,
    *,
    now: str,
    actions: tuple[str, ...] | list[str] | None = None,
    resource_arns: tuple[str, ...] | list[str] | None = None,
) -> Any:
    """Simula as acoes contra o role e grava a DECISAO da AWS.

    `resource_arns` e opcional: sem ele a AWS simula contra `*`, o que responde
    "a policy concede a acao em algum lugar" e NAO "concede neste recurso". A
    diferenca sai no fact, em `resource`.
    """
    if not role_arn:
        raise ValueError("role_arn e obrigatorio")

    acoes = list(actions) if actions else list(ACOES_PADRAO)
    recursos = list(resource_arns) if resource_arns else []

    rel_path = iam_access_path(role_arn)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("iam")
    resultados, status, truncado = _simular(
        client, role_arn=role_arn, acoes=acoes, recursos=recursos
    )

    payload = {
        "role_arn": role_arn,
        "status": status,
        "actions_requested": acoes,
        "resource_arns": recursos,
        # `scoped_to_resource` e o que impede a leitura errada mais provavel
        # deste artefato: sem recurso, a simulacao responde sobre `*`, e
        # "allowed" ali nao significa "allowed naquela tabela".
        "scoped_to_resource": bool(recursos),
        "results": resultados,
        "results_collected": len(resultados),
        "truncated": truncado,
    }
    content = json.dumps(
        payload, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    comando = f"sparkforge collect iam-access --role-arn {role_arn}"
    for recurso in recursos:
        comando += f" --resource-arn {recurso}"
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="iam_access",
        source="iam:SimulatePrincipalPolicy",
        collect_command=comando,
        now=now,
    )


__all__ = [
    "ACOES_PADRAO",
    "STATUS_NAO_ENCONTRADO",
    "STATUS_OK",
    "STATUS_SEM_CREDENCIAL",
    "STATUS_SEM_PERMISSAO",
    "collect_iam_access",
    "iam_access_path",
]
