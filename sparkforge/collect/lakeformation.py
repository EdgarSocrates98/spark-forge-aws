"""Coletor de PERMISSAO do Lake Formation -- a lacuna que `lakeformation.unresolved` nomeia.

## Por que ele existe, medido

O motor derivou o modelo de acesso que a definicao do job DECLARA
(`sparkforge/facts/lakeformation.py`, 2026-09-09), e seis regras `SF-LF` mais
cinco `SF-ERR` julgam sobre ele. Nenhuma delas diz QUAL permissao falta -- todas
dizem em qual PLANO a operacao parou. `lakeformation.unresolved` publica essa
distancia em todo case que declara modelo de acesso, e nomeia os tres artefatos
que faltam: grant do Lake Formation, policy do runtime role, e registro da
localizacao S3.

Este modulo coleta DOIS dos tres. O terceiro -- a policy do runtime role -- e
outro coletor, e a razao de nao ser este esta na secao seguinte.

## Tres chamadas, tres status, e a razao de nao serem um so

    lakeformation.list_permissions      quem tem o que sobre a tabela
    lakeformation.describe_resource     a localizacao S3 esta REGISTRADA, e com
                                        qual role
    lakeformation.get_data_lake_settings  se a conta permite query engine de
                                        terceiro sem validacao de session tag

As tres falham por motivos DIFERENTES e independentes: um principal pode ter
permissao de ler grant e nao de ler data lake settings, uma tabela pode existir
sem localizacao registrada, e a conta pode negar as tres. Um `status` unico
colapsaria isso, e "nao consegui" viraria indistinguivel de "nao ha" -- que e
exatamente o defeito que a recusa nomeada existe para evitar neste repositorio.

Por isso cada bloco do artefato carrega o SEU `status`, e o payload tem um
`status` de topo que e apenas o pior dos tres.

## O que ele NAO faz

**Nao le policy de IAM.** Ler o documento e formar opiniao sobre ele erra
exatamente nos casos que importam -- permission boundary, service control
policy, deny explicito e condicao. O caminho para a pergunta "esta acao esta
autorizada?" e `iam:SimulatePrincipalPolicy`, que devolve a resposta da AWS em
vez de uma leitura da nossa, e ele e coletor proprio.

**Nao decide se a permissao e suficiente.** `SELECT` bastar ou nao depende da
operacao e do modelo de acesso, e isso e juizo -- mora na regra. Aqui sai o que
a AWS respondeu, verbatim.

**Nao lista permissao de toda a conta.** `list_permissions` sem recurso devolve
o inventario inteiro do data lake, que e dado de governanca de terceiros e nao
tem por que entrar num `facts.json` committado. O recurso e obrigatorio.
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
STATUS_VAZIO = "vazio"
STATUS_NAO_ENCONTRADO = "nao_encontrado"
STATUS_SEM_PERMISSAO = "sem_permissao"
STATUS_SEM_CREDENCIAL = "sem_credencial"
STATUS_NAO_COLETADO = "nao_coletado"

# Teto de paginas de `list_permissions`. Mesma razao do teto do coletor de log:
# uma tabela com centenas de grants pagina longamente, e gravar o parcial
# produziria um inventario truncado indistinguivel do completo. Quando ele
# morde, o bloco sai com `truncated: true`.
_MAX_PAGINAS = 20


def lakeformation_path(catalog_id: str, database: str, table: str) -> str:
    """Um artefato por (catalogo, banco, tabela).

    O catalogo entra no nome porque a MESMA `db.tabela` existe em contas
    diferentes sob cross-account, e colapsar as duas num arquivo so faria a
    segunda coleta sobrescrever a primeira -- o manifesto registraria um sha256
    que muda sozinho.
    """
    catalogo = catalog_id or "local"
    return f".sparkforge/artifacts/lakeformation/{catalogo}_{database}_{table}.json"


def _codigo_de_erro(exc: BaseException) -> str:
    resposta = getattr(exc, "response", None)
    if isinstance(resposta, dict):
        return str((resposta.get("Error") or {}).get("Code") or "")
    return ""


def _classificar(exc: BaseException) -> str | None:
    """Codigo de erro da AWS -> status nomeado. `None` = nao e nosso, re-levanta.

    A classificacao e por CODIGO e nunca por texto da mensagem: mensagem muda
    entre versoes do SDK e entre regioes, e casar por substring produziria uma
    recusa que se renomeia sozinha.
    """
    nome = type(exc).__name__
    if nome in {"NoCredentialsError", "PartialCredentialsError", "NoRegionError"}:
        return STATUS_SEM_CREDENCIAL
    codigo = _codigo_de_erro(exc)
    if codigo in {"EntityNotFoundException", "ResourceNotFoundException"}:
        return STATUS_NAO_ENCONTRADO
    if codigo in {"AccessDeniedException", "AccessDeniedError", "UnauthorizedException"}:
        return STATUS_SEM_PERMISSAO
    if codigo in {"ExpiredTokenException", "InvalidClientTokenId", "UnrecognizedClientException"}:
        return STATUS_SEM_CREDENCIAL
    return None


def _executar(chamada: Any) -> tuple[Any, str]:
    """Roda a chamada e devolve `(resultado, status)`. Nunca deixa passar
    excecao que este modulo nao sabe nomear."""
    try:
        return chamada(), STATUS_OK
    except CollectionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 -- reclassificado ou re-levantado
        status = _classificar(exc)
        if status is None:
            raise
        return None, status


def _permissoes(client: Any, *, catalog_id: str, database: str, table: str) -> dict[str, Any]:
    recurso = {"Table": {"DatabaseName": database, "Name": table}}
    if catalog_id:
        recurso["Table"]["CatalogId"] = catalog_id

    itens: list[dict[str, Any]] = []
    truncado = False

    def _buscar() -> None:
        nonlocal truncado
        token = None
        for _ in range(_MAX_PAGINAS):
            argumentos: dict[str, Any] = {"Resource": recurso}
            if catalog_id:
                argumentos["CatalogId"] = catalog_id
            if token:
                argumentos["NextToken"] = token
            resposta = client.list_permissions(**argumentos)
            itens.extend(resposta.get("PrincipalResourcePermissions") or [])
            token = resposta.get("NextToken")
            if not token:
                return
        truncado = True

    _, status = _executar(_buscar)
    if status == STATUS_OK and not itens:
        # Tabela sem grant nenhum NAO e o mesmo estado que permissao negada para
        # LER os grants, e os dois produzem a mesma lista vazia.
        status = STATUS_VAZIO
    return {
        "status": status,
        "principals": itens,
        "grants_collected": len(itens),
        "truncated": truncado,
    }


def _localizacao(client: Any, resource_arn: str) -> dict[str, Any]:
    if not resource_arn:
        return {"status": STATUS_NAO_COLETADO, "reason": "resource_arn_nao_informado"}

    def _buscar() -> dict[str, Any]:
        return client.describe_resource(ResourceArn=resource_arn)

    resposta, status = _executar(_buscar)
    info = (resposta or {}).get("ResourceInfo") or {}
    return {
        "status": status,
        "resource_arn": resource_arn,
        # `registered` sai do STATUS e nao da presenca do campo: uma localizacao
        # nao registrada devolve `EntityNotFoundException`, e tratar isso como
        # "nao registrada" e leitura correta -- mas so quando a chamada
        # ACONTECEU. Sem permissao ou sem credencial, `registered` fica `None`,
        # porque ninguem mediu.
        "registered": (
            True
            if status == STATUS_OK
            else (False if status == STATUS_NAO_ENCONTRADO else None)
        ),
        "role_arn": info.get("RoleArn", ""),
        "hybrid_access_enabled": info.get("HybridAccessEnabled"),
        "with_federation": info.get("WithFederation"),
    }


def _data_lake_settings(client: Any, catalog_id: str) -> dict[str, Any]:
    def _buscar() -> dict[str, Any]:
        argumentos = {"CatalogId": catalog_id} if catalog_id else {}
        return client.get_data_lake_settings(**argumentos)

    resposta, status = _executar(_buscar)
    settings = (resposta or {}).get("DataLakeSettings") or {}
    return {
        "status": status,
        # E este campo que a documentacao de Full Table Access chama de
        # "application integration for full table access" -- o passo de CONTA
        # que precede qualquer grant, e que nenhum artefato do job revela.
        "allow_full_table_external_data_access": settings.get(
            "AllowFullTableExternalDataAccess"
        ),
        "allow_external_data_filtering": settings.get("AllowExternalDataFiltering"),
        "external_data_filtering_allow_list": [
            entrada.get("DataLakePrincipalIdentifier", "")
            for entrada in (settings.get("ExternalDataFilteringAllowList") or [])
        ],
    }


_ORDEM_DE_GRAVIDADE = (
    STATUS_SEM_CREDENCIAL,
    STATUS_SEM_PERMISSAO,
    STATUS_NAO_ENCONTRADO,
    STATUS_NAO_COLETADO,
    STATUS_VAZIO,
    STATUS_OK,
)


def _pior(*status: str) -> str:
    """O status de topo e o PIOR dos tres, nunca a media nem o primeiro.

    Um artefato cujo topo diga `ok` porque duas das tres chamadas funcionaram
    esconderia a terceira -- e a terceira e justamente a que o operador precisa
    saber que falhou.
    """
    for candidato in _ORDEM_DE_GRAVIDADE:
        if candidato in status:
            return candidato
    return STATUS_OK


def collect_lakeformation(
    database: str,
    table: str,
    root: Path,
    *,
    now: str,
    catalog_id: str = "",
    resource_arn: str = "",
) -> Any:
    """Coleta grant, registro de localizacao e data lake settings de UMA tabela.

    `resource_arn` e a localizacao S3 a conferir -- opcional, porque nem todo
    caso tem a localizacao a mao, e sem ela o bloco sai `nao_coletado` em vez de
    sumir. Bloco ausente e indistinguivel de bloco vazio, e essa distincao e o
    que separa "nao ha registro" de "ninguem perguntou".
    """
    if not database or not table:
        raise ValueError("database e table sao obrigatorios")

    rel_path = lakeformation_path(catalog_id, database, table)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("lakeformation")

    permissoes = _permissoes(client, catalog_id=catalog_id, database=database, table=table)
    localizacao = _localizacao(client, resource_arn)
    settings = _data_lake_settings(client, catalog_id)

    payload = {
        "catalog_id": catalog_id,
        "database": database,
        "table": table,
        "status": _pior(permissoes["status"], localizacao["status"], settings["status"]),
        "permissions": permissoes,
        "registered_location": localizacao,
        "data_lake_settings": settings,
    }
    content = json.dumps(
        payload, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    comando = f"sparkforge collect lakeformation --database {database} --table {table}"
    if catalog_id:
        comando += f" --catalog-id {catalog_id}"
    if resource_arn:
        comando += f" --resource-arn {resource_arn}"
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="lakeformation",
        source="lakeformation:ListPermissions+DescribeResource+GetDataLakeSettings",
        collect_command=comando,
        now=now,
    )


__all__ = [
    "STATUS_NAO_COLETADO",
    "STATUS_NAO_ENCONTRADO",
    "STATUS_OK",
    "STATUS_SEM_CREDENCIAL",
    "STATUS_SEM_PERMISSAO",
    "STATUS_VAZIO",
    "collect_lakeformation",
    "lakeformation_path",
]
