"""Coletor de RESOURCE LINK do Glue Data Catalog -- a perna do grafo que
`build_access_graph` devolvia `unresolved` porque nenhum coletor a produzia.

## Por que ele existe, medido

A §1 de `knowledge/glue/lakeformation-fgac.md` declara, de fonte T1, que consulta
cross-account sob Lake Formation so e suportada por resource link e que **o link
precisa ter o mesmo nome do recurso na conta de origem**. Ate 2026-09-10 essa
afirmacao vivia so em PROSA: nenhum kind carregava resource link, o indice de
conhecimento a listava como *"sem produtor de fact"*, e
`sparkforge/lakeformation/graph.py` emitia a perna `resource_link` como
`unresolved` com o texto *"destravaria: `glue:GetTable` sobre o link, comparando
o nome com o do recurso de origem"*.

Este modulo e esse `glue:GetTable`.

## Duas chamadas, dois status, e a razao de nao serem um so

    glue.get_table / get_database   o objeto na conta CONSUMIDORA -- e ele e
                                    link? para onde aponta?
    glue.get_table / get_database   o objeto na conta de ORIGEM, no catalogo que
                                    o link declara como alvo

Elas falham por motivos DIFERENTES: o link pode existir e o alvo nao ser
visivel, e o alvo pode existir e o link nao. Um `status` unico colapsaria isso,
e "nao consegui" viraria indistinguivel de "nao ha" -- a mesma razao pela qual o
coletor de permissao (`sparkforge/collect/lakeformation.py`) carrega um status
por bloco.

## Tabela ou banco: `--table` decide, e a distincao nao e cosmetica

Resource link existe para os DOIS. `TargetTable` mora em `Table`, `TargetDatabase`
mora em `Database`, e os campos nao tem o mesmo nome nem o mesmo shape --
`TargetTable` traz `Name`, `TargetDatabase` nao traz nenhum (o nome do recurso de
origem E o `DatabaseName`). Sem `--table`, o alvo e um banco.

## O que ele NAO faz

**Nao decide se o nome bate.** A comparacao e derivacao sobre dois campos que
saem daqui verbatim, e mora no extrator. Aqui sai o que a AWS respondeu.

**Nao le o estado do AWS RAM.** `ram:GetResourceShares` responde outra pergunta
-- se o convite de compartilhamento foi aceito --, falha por permissao propria, e
e coletor proprio. Um link que resolve NAO prova que o share foi aceito, e um
share aceito nao cria o link.

**Nao afirma que "nao encontrado" e ausencia.** Sob Lake Formation,
`EntityNotFoundException` sobre um recurso a que o principal nao tem permissao e
resposta legitima da API -- absence e denial chegam pelo mesmo codigo. O bloco
guarda o codigo que a AWS devolveu, e a ambiguidade sai nomeada no extrator,
nunca resolvida por chute.
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
STATUS_NAO_COLETADO = "nao_coletado"

TIPO_TABELA = "table"
TIPO_BANCO = "database"


def glue_resource_link_path(catalog_id: str, database: str, table: str = "") -> str:
    """Um artefato por (catalogo consumidor, banco, [tabela]).

    O catalogo entra no nome pela mesma razao do coletor de permissao: a MESMA
    `db.tabela` existe em contas diferentes sob cross-account, e colapsar as duas
    num arquivo so faria a segunda coleta sobrescrever a primeira -- o manifesto
    registraria um sha256 que muda sozinho.
    """
    catalogo = catalog_id or "local"
    alvo = f"{database}_{table}" if table else database
    return f".sparkforge/artifacts/glue_resource_link/{catalogo}_{alvo}.json"


def _codigo_de_erro(exc: BaseException) -> str:
    resposta = getattr(exc, "response", None)
    if isinstance(resposta, dict):
        return str((resposta.get("Error") or {}).get("Code") or "")
    return ""


def _classificar(exc: BaseException) -> str | None:
    """Codigo de erro da AWS -> status nomeado. `None` = nao e nosso, re-levanta.

    Por CODIGO e nunca por texto da mensagem, pela mesma razao do coletor de
    permissao: mensagem muda entre versoes do SDK e entre regioes, e casar por
    substring produz uma recusa que se renomeia sozinha.
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


def _executar(chamada: Any) -> tuple[Any, str, str]:
    """Roda a chamada e devolve `(resultado, status, codigo_da_aws)`.

    O terceiro elemento existe porque `nao_encontrado` sob Lake Formation e
    ambiguo, e guardar o codigo verbatim e o que permite ao extrator NOMEAR a
    ambiguidade em vez de escolher um dos dois sentidos.
    """
    try:
        return chamada(), STATUS_OK, ""
    except CollectionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 -- reclassificado ou re-levantado
        status = _classificar(exc)
        if status is None:
            raise
        return None, status, _codigo_de_erro(exc) or type(exc).__name__


def _ler_tabela(client: Any, *, catalog_id: str, database: str, table: str) -> tuple[Any, str, str]:
    def _buscar() -> dict[str, Any]:
        argumentos: dict[str, Any] = {"DatabaseName": database, "Name": table}
        if catalog_id:
            argumentos["CatalogId"] = catalog_id
        return client.get_table(**argumentos)

    return _executar(_buscar)


def _ler_banco(client: Any, *, catalog_id: str, database: str) -> tuple[Any, str, str]:
    def _buscar() -> dict[str, Any]:
        argumentos: dict[str, Any] = {"Name": database}
        if catalog_id:
            argumentos["CatalogId"] = catalog_id
        return client.get_database(**argumentos)

    return _executar(_buscar)


def _alvo_de_tabela(resposta: dict[str, Any]) -> dict[str, Any]:
    tabela = (resposta or {}).get("Table") or {}
    alvo = tabela.get("TargetTable") or {}
    return {
        # `is_resource_link` sai da PRESENCA de `TargetTable`, que e como a API
        # do Glue distingue link de tabela comum -- nao ha campo booleano.
        "is_resource_link": bool(alvo),
        "link_name": str(tabela.get("Name") or ""),
        "link_database": str(tabela.get("DatabaseName") or ""),
        "link_catalog_id": str(tabela.get("CatalogId") or ""),
        "target_catalog_id": str(alvo.get("CatalogId") or ""),
        "target_database": str(alvo.get("DatabaseName") or ""),
        # So o link de TABELA tem nome de recurso de origem. Para banco, o nome
        # do recurso E o `DatabaseName`, e por isso o campo sai vazio la.
        "target_name": str(alvo.get("Name") or ""),
        "target_region": str(alvo.get("Region") or ""),
    }


def _alvo_de_banco(resposta: dict[str, Any]) -> dict[str, Any]:
    banco = (resposta or {}).get("Database") or {}
    alvo = banco.get("TargetDatabase") or {}
    return {
        "is_resource_link": bool(alvo),
        "link_name": str(banco.get("Name") or ""),
        "link_database": str(banco.get("Name") or ""),
        "link_catalog_id": str(banco.get("CatalogId") or ""),
        "target_catalog_id": str(alvo.get("CatalogId") or ""),
        "target_database": str(alvo.get("DatabaseName") or ""),
        "target_name": "",
        "target_region": str(alvo.get("Region") or ""),
    }


def _bloco_link(
    client: Any, *, catalog_id: str, database: str, table: str
) -> dict[str, Any]:
    if table:
        resposta, status, codigo = _ler_tabela(
            client, catalog_id=catalog_id, database=database, table=table
        )
        campos = _alvo_de_tabela(resposta or {}) if status == STATUS_OK else {}
    else:
        resposta, status, codigo = _ler_banco(client, catalog_id=catalog_id, database=database)
        campos = _alvo_de_banco(resposta or {}) if status == STATUS_OK else {}

    bloco: dict[str, Any] = {
        "status": status,
        "aws_error_code": codigo,
        "target_type": TIPO_TABELA if table else TIPO_BANCO,
        "requested_catalog_id": catalog_id,
        "requested_database": database,
        "requested_table": table,
    }
    bloco.update(campos)
    return bloco


def _bloco_alvo(client: Any, link: dict[str, Any]) -> dict[str, Any]:
    """Confere o recurso de ORIGEM que o link declara. Nunca adivinha o alvo.

    Sem `TargetCatalogId` medido no bloco anterior nao ha o que conferir, e o
    bloco sai `nao_coletado` em vez de sumir -- bloco ausente e indistinguivel de
    bloco vazio, e essa distincao e o que separa "nao ha origem" de "ninguem
    perguntou".
    """
    if link.get("status") != STATUS_OK or not link.get("is_resource_link"):
        return {"status": STATUS_NAO_COLETADO, "reason": "sem_alvo_medido_no_link"}

    catalogo = str(link.get("target_catalog_id") or "")
    banco = str(link.get("target_database") or "")
    nome = str(link.get("target_name") or "")
    if not catalogo or not banco:
        return {"status": STATUS_NAO_COLETADO, "reason": "alvo_sem_catalogo_ou_banco"}

    if link.get("target_type") == TIPO_TABELA:
        if not nome:
            return {"status": STATUS_NAO_COLETADO, "reason": "alvo_sem_nome_de_tabela"}
        resposta, status, codigo = _ler_tabela(
            client, catalog_id=catalogo, database=banco, table=nome
        )
        existente = str(((resposta or {}).get("Table") or {}).get("Name") or "")
    else:
        resposta, status, codigo = _ler_banco(client, catalog_id=catalogo, database=banco)
        existente = str(((resposta or {}).get("Database") or {}).get("Name") or "")

    return {
        "status": status,
        # Guardado VERBATIM porque, sob Lake Formation, `EntityNotFoundException`
        # sobre recurso nao autorizado e a mesma resposta que sobre recurso
        # inexistente. Quem le o fact precisa ver o codigo, nao a nossa leitura
        # dele.
        "aws_error_code": codigo,
        "catalog_id": catalogo,
        "database": banco,
        "name": nome,
        "resolved_name": existente,
    }


_ORDEM_DE_GRAVIDADE = (
    STATUS_SEM_CREDENCIAL,
    STATUS_SEM_PERMISSAO,
    STATUS_NAO_ENCONTRADO,
    STATUS_NAO_COLETADO,
    STATUS_OK,
)


def _pior(*status: str) -> str:
    """O status de topo e o PIOR dos dois, nunca o primeiro.

    Um artefato cujo topo diga `ok` porque o link resolveu esconderia o alvo que
    nao resolveu -- e e o alvo que a §1 do documento de conhecimento cobra.
    """
    for candidato in _ORDEM_DE_GRAVIDADE:
        if candidato in status:
            return candidato
    return STATUS_OK


def collect_glue_resource_link(
    database: str,
    root: Path,
    *,
    now: str,
    table: str = "",
    catalog_id: str = "",
    verify_target: bool = True,
) -> Any:
    """Le o objeto na conta consumidora e, opcionalmente, o recurso de origem.

    `catalog_id` e o catalogo CONSUMIDOR -- onde o link mora --, e nao o da conta
    de origem: o alvo sai medido do proprio link, e passa-lo a mao produziria uma
    conferencia contra o catalogo que o operador SUPOE, e nao contra o que o link
    declara.

    `verify_target=False` pula a segunda chamada. Ele existe porque o principal
    que coleta pode nao ter permissao nenhuma na conta de origem, e nesse caso a
    segunda chamada so acrescenta um `sem_permissao` previsivel -- mas o default
    e conferir, porque link que aponta para lugar nenhum e o defeito que este
    coletor existe para achar.
    """
    if not database:
        raise ValueError("database e obrigatorio")

    rel_path = glue_resource_link_path(catalog_id, database, table)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("glue")

    link = _bloco_link(client, catalog_id=catalog_id, database=database, table=table)
    if verify_target:
        alvo = _bloco_alvo(client, link)
    else:
        alvo = {"status": STATUS_NAO_COLETADO, "reason": "verify_target_desligado"}

    payload = {
        "catalog_id": catalog_id,
        "database": database,
        "table": table,
        "target_type": TIPO_TABELA if table else TIPO_BANCO,
        "status": _pior(link["status"], alvo["status"]),
        "link": link,
        "target": alvo,
    }
    content = json.dumps(
        payload, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    comando = f"sparkforge collect glue-resource-link --database {database}"
    if table:
        comando += f" --table {table}"
    if catalog_id:
        comando += f" --catalog-id {catalog_id}"
    if not verify_target:
        comando += " --no-verify-target"
    fonte = "glue:GetTable" if table else "glue:GetDatabase"
    if verify_target:
        fonte += "+target"
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="glue_resource_link",
        source=fonte,
        collect_command=comando,
        now=now,
    )


__all__ = [
    "STATUS_NAO_COLETADO",
    "STATUS_NAO_ENCONTRADO",
    "STATUS_OK",
    "STATUS_SEM_CREDENCIAL",
    "STATUS_SEM_PERMISSAO",
    "TIPO_BANCO",
    "TIPO_TABELA",
    "collect_glue_resource_link",
    "glue_resource_link_path",
]
