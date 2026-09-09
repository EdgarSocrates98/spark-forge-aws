"""Coletor do LOG do Glue no CloudWatch Logs -- o caminho que o event log nao tem.

POR QUE ELE EXISTE, MEDIDO. O event log so carrega a excecao DO STAGE
(`spark.stage.failure` -> `spark.exception`). Das seis assinaturas de
`knowledge/errors/`, QUATRO sao trecho de mensagem de log e nao classe de
excecao, e por `spark.exception` nunca casam:

    ERR-ATH-001   Cannot read unsupported version 3
    ERR-GLUE-001  Container killed by YARN for exceeding memory limits
    ERR-ICE-001   CommitFailedException: Commit failed: Table was updated concurrently
    ERR-LF-001    Insufficient Lake Formation permission(s) on

O log tambem carrega o que o event log NAO tem: falha de driver antes do
primeiro stage (sem stage, sem `Failure Reason`), `Py4JJavaError` de codigo
Python, e o OOM de container que o YARN mata por fora do Spark.

## So le, e nunca decide o que e relevante

`logs.filter_log_events` e nada mais. A RELEVANCIA e DECLARADA pelo operador,
via `filter_pattern` (sintaxe de filtro do proprio CloudWatch Logs, aplicada no
servidor, onde ela corta bytes antes de eles virarem custo) e via a janela
`start`/`end`. Este modulo nao inventa um predicado de "linha interessante": um
predicado assim seria juizo disfarcado de coleta, e escolher quais linhas o
motor pode ver e escolher o diagnostico.

## Recusa tem NOME, e ela vira artefato em vez de excecao

Log group inexistente, sem permissao, janela vazia e sem credencial sao os
quatro estados que o operador precisa distinguir, e os quatro produzem o MESMO
`events: []` se a resposta for so uma lista. Por isso o artefato carrega
`status`, e `sparkforge/facts/cloudwatch_logs.py` o traduz em
`cloudwatch.logs.unresolved` com a razao (regra 20 do `CLAUDE.md`).

E por isso que os quatro nao levantam `CollectionFailed`: excecao mata o
artefato, e sem artefato nao ha fact, e sem fact a recusa vira silencio -- que
e exatamente o que a regra 20 proibe. `CollectionFailed` continua reservado
para o que impede ate a recusa ser gravada (paginacao que nao termina).

## Redacao

Este modulo NAO redige. O artefato bruto e o log como a AWS o devolveu, e
artefato bruto nunca e committado (ver `sparkforge/collect/base.py`). A redacao
acontece no extrator, antes de o texto virar fact, porque `facts.json` E
committado como barramento de handoff -- mesmo caminho de `spark.conf_effective`
e `spark.stage.failure`.

Mesma politica offline-first do resto de `sparkforge/collect/`: artefato
presente e integro no disco e no-op que nao toca boto3 nem rede. `now` e sempre
parametro, nunca lido do relogio.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import (
    CollectionFailed,
    _offline_hit,
    _write_and_register,
)
from sparkforge.collect.base import require_boto3

# Teto de paginas de `filter_log_events`. Existe pela mesma razao do teto de
# `get_metric_data`: uma janela absurda com um filtro largo pagina para sempre,
# e gravar o parcial produziria um log truncado indistinguivel do completo.
_MAX_PAGINAS_DE_LOG = 50

# Teto de eventos gravados no artefato. NAO e silencioso: quando ele morde, o
# artefato sai com `truncated: true` e o extrator carrega isso para o fact. Um
# corte que nao se declara e a mesma classe de defeito que a serie de metrica
# truncada da auditoria de 2026-09-03.
_MAX_EVENTOS_PADRAO = 500

# Grupos de log do Glue, de `knowledge/glue/observability.md`. Nao ha default:
# `logs-v2` (Glue 4.0+), `/aws-glue/jobs/error` e `/aws-glue/jobs/output` sao
# grupos DIFERENTES com conteudo diferente, e adivinhar qual o operador quer
# escolheria a evidencia por ele.
GLUE_LOG_GROUPS: tuple[str, ...] = (
    "/aws-glue/jobs/error",
    "/aws-glue/jobs/output",
    "/aws-glue/jobs/logs-v2",
)

STATUS_OK = "ok"
STATUS_VAZIO = "vazio"
STATUS_GRUPO_INEXISTENTE = "log_group_inexistente"
STATUS_SEM_PERMISSAO = "sem_permissao"
STATUS_SEM_CREDENCIAL = "sem_credencial"

# Codigos de erro da API mapeados para as razoes que o operador consegue agir.
# Sao nomes de `Error.Code` do botocore -- comparados como string porque
# botocore nunca e importado aqui (mesma disciplina de `require_boto3`).
_CODIGOS_INEXISTENTE = frozenset({"ResourceNotFoundException"})
_CODIGOS_SEM_PERMISSAO = frozenset(
    {
        "AccessDeniedException",
        "AccessDenied",
        "AuthorizationError",
        "UnauthorizedOperation",
    }
)
# Falha de credencial nao chega como `ClientError` -- ela e levantada pelo
# proprio botocore antes de a requisicao sair, e so tem o NOME da classe.
_EXCECOES_SEM_CREDENCIAL = frozenset(
    {
        "NoCredentialsError",
        "PartialCredentialsError",
        "CredentialRetrievalError",
        "TokenRetrievalError",
        "UnauthorizedSSOTokenError",
        "NoRegionError",
    }
)


def cloudwatch_logs_path(job_name: str, job_run_id: str, log_group: str) -> str:
    """Um artefato por (job, run, GRUPO). O grupo entra no nome porque
    `/aws-glue/jobs/error` e `/aws-glue/jobs/output` do mesmo run sao dois
    conteudos distintos -- colapsa-los num arquivo so faria a segunda coleta
    sobrescrever a primeira, e o manifesto registraria um sha256 que muda
    sozinho."""
    grupo = log_group.strip("/").replace("/", "_")
    return f".sparkforge/artifacts/cloudwatch_logs/{job_name}_{job_run_id}_{grupo}.json"


def _ms(iso: str) -> int:
    texto = iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(texto)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _codigo_de_erro(exc: BaseException) -> str:
    resposta = getattr(exc, "response", None)
    if isinstance(resposta, dict):
        erro = resposta.get("Error")
        if isinstance(erro, dict):
            return str(erro.get("Code") or "")
    return ""


def _classificar(exc: BaseException) -> str | None:
    """Traduz a excecao no `status` que o operador consegue agir, ou `None`
    quando ela nao e um dos quatro estados nomeados -- e ai ela sobe, porque
    engolir erro desconhecido e como um coletor mente."""
    if type(exc).__name__ in _EXCECOES_SEM_CREDENCIAL:
        return STATUS_SEM_CREDENCIAL
    codigo = _codigo_de_erro(exc)
    if codigo in _CODIGOS_INEXISTENTE:
        return STATUS_GRUPO_INEXISTENTE
    if codigo in _CODIGOS_SEM_PERMISSAO:
        return STATUS_SEM_PERMISSAO
    return None


def _buscar(
    client: Any,
    *,
    log_group: str,
    stream_prefix: str,
    inicio_ms: int,
    fim_ms: int,
    filter_pattern: str,
    max_events: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Pagina `filter_log_events` ate acabar, ate o teto de eventos, ou ate o
    teto de paginas -- nesta ordem. Devolve `(eventos, truncado)`.

    A PAGINACAO E O PONTO. Uma resposta de `filter_log_events` traz no maximo
    1 MB ou 10 000 eventos, e o resto atras de `nextToken`; ler uma so devolve
    um log parcial indistinguivel do completo, e a linha que casa a assinatura
    pode estar justamente na segunda pagina. `tests/test_collect_cloudwatch_logs.py`
    serve varias paginas com eventos DISTINTOS e cobra que todos apareçam --
    um fake de pagina unica nunca exercitaria este laco.
    """
    eventos: list[dict[str, Any]] = []
    token: str | None = None
    truncado = False
    for _ in range(_MAX_PAGINAS_DE_LOG):
        kwargs: dict[str, Any] = {
            "logGroupName": log_group,
            "startTime": inicio_ms,
            "endTime": fim_ms,
        }
        if stream_prefix:
            kwargs["logStreamNamePrefix"] = stream_prefix
        if filter_pattern:
            kwargs["filterPattern"] = filter_pattern
        if token:
            kwargs["nextToken"] = token
        pagina = client.filter_log_events(**kwargs)
        for evento in pagina.get("events") or []:
            if len(eventos) >= max_events:
                truncado = True
                break
            eventos.append(evento)
        if truncado:
            break
        token = pagina.get("nextToken")
        if not token:
            break
    else:
        raise CollectionFailed(
            f"`filter_log_events` ainda paginava depois de {_MAX_PAGINAS_DE_LOG} "
            f"paginas em {log_group}. Gravar o parcial produziria um log truncado "
            f"indistinguivel do completo -- reduza a janela ou aperte o "
            f"`--filter-pattern`."
        )
    return eventos, truncado


def collect_cloudwatch_logs(
    job_name: str,
    job_run_id: str,
    root: Path,
    *,
    now: str,
    log_group: str,
    start: str,
    end: str,
    filter_pattern: str = "",
    max_events: int = _MAX_EVENTOS_PADRAO,
) -> Any:
    """Baixa o log do run via `logs.filter_log_events` e registra no manifesto.

    `start`/`end` sao ISO 8601 do chamador -- este modulo nunca le o relogio.
    O stream do Glue e prefixado pelo `job_run_id` (o driver e `<run-id>`, os
    executores `<run-id>_<algo>`), entao `logStreamNamePrefix` restringe a busca
    ao run sem precisar listar stream nenhum antes.
    """
    if max_events < 1:
        raise ValueError(f"max_events precisa ser >= 1, recebido {max_events!r}")

    rel_path = cloudwatch_logs_path(job_name, job_run_id, log_group)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit

    boto3 = require_boto3()
    client = boto3.client("logs")

    eventos: list[dict[str, Any]] = []
    truncado = False
    status = STATUS_OK
    try:
        eventos, truncado = _buscar(
            client,
            log_group=log_group,
            stream_prefix=job_run_id,
            inicio_ms=_ms(start),
            fim_ms=_ms(end),
            filter_pattern=filter_pattern,
            max_events=max_events,
        )
    except CollectionFailed:
        raise
    except Exception as exc:  # noqa: BLE001 -- reclassificado ou re-levantado logo abaixo
        classificado = _classificar(exc)
        if classificado is None:
            raise
        status = classificado

    if status == STATUS_OK and not eventos:
        # Janela sem evento NAO e o mesmo estado que grupo inexistente ou
        # permissao negada, e os tres produzem a mesma lista vazia. O `status`
        # e o unico lugar onde a diferenca sobrevive ate o fact.
        status = STATUS_VAZIO

    payload = {
        "job_name": job_name,
        "job_run_id": job_run_id,
        "log_group": log_group,
        "log_stream_prefix": job_run_id,
        "start": start,
        "end": end,
        "filter_pattern": filter_pattern,
        "status": status,
        "events": eventos,
        "events_collected": len(eventos),
        "max_events": max_events,
        "truncated": truncado,
    }
    content = json.dumps(
        payload, indent=2, sort_keys=True, default=str, ensure_ascii=False
    ).encode("utf-8")
    comando = (
        f"sparkforge collect cloudwatch-logs --job-name {job_name} "
        f"--job-run {job_run_id} --log-group {log_group} --start {start} --end {end}"
    )
    if filter_pattern:
        comando += f" --filter-pattern {filter_pattern!r}"
    return _write_and_register(
        root,
        rel_path,
        content,
        kind="cloudwatch_logs",
        source=f"logs:filter_log_events:{log_group}:{job_name}/{job_run_id}",
        collect_command=comando,
        now=now,
    )


__all__ = [
    "GLUE_LOG_GROUPS",
    "STATUS_GRUPO_INEXISTENTE",
    "STATUS_OK",
    "STATUS_SEM_CREDENCIAL",
    "STATUS_SEM_PERMISSAO",
    "STATUS_VAZIO",
    "cloudwatch_logs_path",
    "collect_cloudwatch_logs",
]
