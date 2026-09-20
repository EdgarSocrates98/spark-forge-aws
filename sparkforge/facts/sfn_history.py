"""Extrator de Facts a partir do HISTORICO de execucao do AWS Step Functions.

Le a saida salva de `aws stepfunctions get-execution-history` ja em disco: o objeto
de resposta da API (`{"events": [...]}`, com `nextToken` opcional) ou a lista crua de
eventos. Como `stepfunctions.py` e `controlm_jobs.py`, NAO coleta nada e NUNCA levanta
excecao por payload malformado: o que nao consegue ler vira `sfn.unresolved` com
`attrs.reason`, e a sentinela `sfn.analyzed` sai sempre, uma por arquivo.

## Por que o MESMO prefixo `sfn.` do ASL

E o mesmo dominio, e o kind diz a natureza: `sfn.task` e DECLARACAO (o que o ASL diz
que deve acontecer) e `sfn.attempt` e MEDIDA (o que o historico registra que
aconteceu). Um prefixo proprio separaria em dois dominios o que o operador ve como um
(D1 de `docs/sdd/SFN_HISTORY/design.md`). A consequencia e aritmetica e esta declarada
no plano: `sfn.unresolved` e `sfn.analyzed` JA existem, e este modulo acrescenta tres
kinds, nao cinco.

## O que sai

- `sfn.execution` -- um por arquivo lido. `attrs.status` vem do evento terminal da
  execucao (`succeeded`, `failed`, `aborted`, `timed_out`) e e `unresolved` quando
  nenhum deles esta no arquivo -- NUNCA `succeeded` por suposicao. `attrs.arn` so
  existe quando a saida salva traz `executionArn`: a resposta de
  `get-execution-history` nao o traz, e inventa-lo seria afirmar leitura que nao houve.
- `sfn.attempt` -- um por TENTATIVA de Task: o par entre um `TaskScheduled` e o
  primeiro evento terminal do MESMO agendamento. O `subject.symbol` e
  `<nome do estado>#<ordem>`.
- `sfn.job_run` -- um por `JobRunId` lido do `output` do `TaskSubmitted`, ligado a
  tentativa pelo mesmo `subject.symbol`.
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`,
  `size_above_limit`, `invalid_json`, `json_too_deep`, `json_too_large`,
  `not_an_execution_history`, `truncated`, `event_not_an_object`,
  `event_type_unknown`, `event_id_duplicated`, `state_unresolved`, `attempt_unanchored`,
  `execution_terminal_absent`, `execution_data_absent` e `job_run_id_unrecognized`.
  O discriminador NUMERICO da recusa (`measures.event_id`, `measures.index`) fica em
  `measures`, e nao em `attrs`: `Fact.id` e sha1 de `kind + subject + measures`, e tres
  recusas iguais sobre o mesmo arquivo virariam o mesmo id -- `fusion.fuse` indexa por
  id e deixaria uma so.
- `sfn.analyzed` -- a sentinela, com as contagens.
- `sfn.retry_observado` -- DERIVADO, nunca lido de arquivo: `build_sfn_retry_observado`
  casa as tentativas de um estado NUMA EXECUCAO com o `sfn.task` de MESMO NOME que o
  ASL declara, e `fusion.fuse` a chama. As razoes de `sfn.unresolved` que so ela emite:
  `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`,
  `declared_ceiling_unreadable` e `glue_attempt_absent` (ha tentativa medida, e nenhuma
  delas e `glue:startJobRun` -- a unica integracao que o confronto sabe julgar).

## Como uma tentativa e PAREADA, e por que pela cadeia

A API publica `previousEventId` em todo evento, e o encadeamento e por RAMO: dentro de
`Parallel` e de `Map` os eventos de ramos diferentes se intercalam na ordem de `id`,
mas cada um aponta para o anterior DO SEU ramo. Por isso o pareamento sobe a cadeia a
partir do proprio evento ate o primeiro ancestral do tipo procurado, e nunca usa "o
ultimo visto ate aqui", que erraria exatamente nesses dois casos.

- de um `TaskScheduled` sobe-se ate o `TaskStateEntered` -> o NOME do estado;
- de um terminal (`TaskSucceeded`, `TaskFailed`, `TaskTimedOut`, `TaskStartFailed`,
  `TaskSubmitFailed`) sobe-se ate o `TaskScheduled` -> a TENTATIVA que ele fecha;
- de um `TaskSubmitted` sobe-se ate o `TaskScheduled` -> a tentativa que submeteu.

Cadeia que chega a raiz sem achar, evento referenciado ausente do arquivo, ou ciclo:
`sfn.unresolved` nomeado. NUNCA um chute -- atribuir a tentativa ao estado errado num
`Parallel` seria pior do que nao atribuir.

## Tres atributos DERIVADOS aqui (regra 33)

`sparkforge/rules/expr.py` tem seis comparadores e nenhuma funcao, e `where` so compara
por igualdade. Os tres predicados que as regras precisam sao derivados no extrator:

- `execution_outcome_class`: `stopped` para `ExecutionAborted` e `ExecutionTimedOut`,
  `finished` para `ExecutionSucceeded` e `ExecutionFailed`, `unresolved` sem terminal;
- `terminal_present`: a tentativa tem evento terminal proprio;
- `job_run_outcome_observed`: o desfecho do JobRun foi observado pelo Task. So e
  verdadeiro num `.sync` que terminou em `TaskSucceeded` ou `TaskFailed` -- num
  `TaskTimedOut` o Task expirou ANTES, e num Request Response o Task nunca acompanhou.

## O que este modulo NAO faz

- Nao chama a API. O operador salva a saida e aponta o `--path`.
- Nao le historico de EXPRESS: `get-execution-history` "is not supported by EXPRESS
  state machines", e o historico dele vai para o CloudWatch Logs.
- Nao atribui custo a tentativa nem estima economia (regras 13 e 25 do `CLAUDE.md`). O
  que ele entrega e o `JobRunId`, que e por onde o operador pergunta custo com
  `dpu_seconds` medido.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sparkforge.facts import scan
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "sfn_history@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sfn.execution",
        "sfn.attempt",
        "sfn.job_run",
        "sfn.unresolved",
        "sfn.analyzed",
        "sfn.retry_observado",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `sfn.attempt` no pool, o `fuse` sai byte
# a byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS` e do
# `stepfunctions.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"sfn.attempt"})

# https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html
# Os tipos de `HistoryEventType` que a pagina publica. Tipo fora desta lista nao e
# erro do artefato -- e a API que cresceu --, e por isso sai em `sfn.unresolved`
# `event_type_unknown` com o nome, em vez de ser ignorado em silencio.
_TIPOS_CONHECIDOS = frozenset(
    {
        "ActivityFailed",
        "ActivityScheduleFailed",
        "ActivityScheduled",
        "ActivityStarted",
        "ActivitySucceeded",
        "ActivityTimedOut",
        "ChoiceStateEntered",
        "ChoiceStateExited",
        "ExecutionAborted",
        "ExecutionFailed",
        "ExecutionStarted",
        "ExecutionSucceeded",
        "ExecutionTimedOut",
        "FailStateEntered",
        "LambdaFunctionFailed",
        "LambdaFunctionScheduleFailed",
        "LambdaFunctionScheduled",
        "LambdaFunctionStartFailed",
        "LambdaFunctionStarted",
        "LambdaFunctionSucceeded",
        "LambdaFunctionTimedOut",
        "MapIterationAborted",
        "MapIterationFailed",
        "MapIterationStarted",
        "MapIterationSucceeded",
        "MapRunAborted",
        "MapRunFailed",
        "MapRunStarted",
        "MapRunSucceeded",
        "MapStateAborted",
        "MapStateEntered",
        "MapStateExited",
        "MapStateFailed",
        "MapStateStarted",
        "MapStateSucceeded",
        "ParallelStateAborted",
        "ParallelStateEntered",
        "ParallelStateExited",
        "ParallelStateFailed",
        "ParallelStateStarted",
        "ParallelStateSucceeded",
        "PassStateEntered",
        "PassStateExited",
        "SucceedStateEntered",
        "SucceedStateExited",
        "TaskFailed",
        "TaskScheduled",
        "TaskStartFailed",
        "TaskStarted",
        "TaskStateAborted",
        "TaskStateEntered",
        "TaskStateExited",
        "TaskSubmitFailed",
        "TaskSubmitted",
        "TaskSucceeded",
        "TaskTimedOut",
        "WaitStateAborted",
        "WaitStateEntered",
        "WaitStateExited",
    }
)

# Evento terminal de UMA tentativa -> o `result` que sai no fact.
_RESULTADO_POR_TIPO = {
    "TaskSucceeded": "succeeded",
    "TaskFailed": "failed",
    "TaskTimedOut": "timed_out",
    "TaskStartFailed": "start_failed",
    "TaskSubmitFailed": "submit_failed",
}

# Evento terminal da EXECUCAO -> o `status` que sai no fact.
_STATUS_POR_TIPO = {
    "ExecutionSucceeded": "succeeded",
    "ExecutionFailed": "failed",
    "ExecutionAborted": "aborted",
    "ExecutionTimedOut": "timed_out",
}

# A execucao PAROU (alguem abortou, ou o relogio dela estourou) contra ela TERMINOU
# por conta propria. A distincao decide a SF-SFNX-003 e e derivada aqui (regra 33).
_PARADA = frozenset({"aborted", "timed_out"})

# O desfecho do JobRun so e observado pelo Task nestes dois terminais, e so sob `.sync`.
_OBSERVA_O_JOB_RUN = frozenset({"succeeded", "failed"})

_DETALHES_POR_TIPO = {
    "TaskScheduled": "taskScheduledEventDetails",
    "TaskStarted": "taskStartedEventDetails",
    "TaskSubmitted": "taskSubmittedEventDetails",
    "TaskSucceeded": "taskSucceededEventDetails",
    "TaskFailed": "taskFailedEventDetails",
    "TaskTimedOut": "taskTimedOutEventDetails",
    "TaskStartFailed": "taskStartFailedEventDetails",
    "TaskSubmitFailed": "taskSubmitFailedEventDetails",
    "ExecutionAborted": "executionAbortedEventDetails",
    "ExecutionFailed": "executionFailedEventDetails",
    "ExecutionTimedOut": "executionTimedOutEventDetails",
    "ExecutionSucceeded": "executionSucceededEventDetails",
    "ExecutionStarted": "executionStartedEventDetails",
}


@dataclass
class _Leitura:
    """O estado de UM arquivo sendo lido: onde, e o que ja saiu."""

    path: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _attempt_subject(path: str, simbolo: str) -> dict[str, Any]:
    subject = _file_subject(path)
    subject["symbol"] = simbolo
    return subject


def _provenance(path: str, sha: str) -> dict[str, Any]:
    return {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}


def _unresolved(
    subject: dict[str, Any],
    reason: str,
    provenance: dict[str, Any],
    measures: dict[str, Any] | None = None,
    **extra: Any,
) -> Fact:
    """A recusa nomeada. O discriminador NUMERICO vai em `measures`, e a razao e o id.

    `Fact.id` e sha1 de `kind + subject + measures`, e `attrs` nao entra. Tres recusas
    do mesmo tipo sobre o mesmo arquivo tem subject igual, e com o discriminador so em
    `attrs` elas viram o MESMO id -- `fusion.fuse` indexa por id e deixaria uma. Por
    isso `event_id`, `index` e afins moram em `measures`, que e numerico por schema e
    entra no hash.
    """
    return Fact(
        kind="sfn.unresolved",
        subject=subject,
        measures=dict(measures or {}),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _loads(texto: str) -> tuple[Any, str | None]:
    """(valor, None) ou (None, razao). Nunca levanta.

    Historico de execucao longa chega a megabytes, e o decodificador de JSON levanta
    `RecursionError` com aninhamento profundo e `MemoryError` com payload hostil. As
    tres formas de falha saem nomeadas, e nenhuma derruba quem chamou.
    """
    try:
        return json.loads(texto), None
    except RecursionError:
        return None, "json_too_deep"
    except MemoryError:
        return None, "json_too_large"
    except ValueError:  # inclui json.JSONDecodeError
        return None, "invalid_json"


def _instante(valor: Any) -> float | None:
    """Segundos desde a epoca, ou `None`. ISO 8601 e epoch, e nada mais.

    A CLI serializa `timestamp` como ISO 8601 com deslocamento; alguns dumps de SDK o
    gravam como numero. Milissegundo vira segundo pelo limiar de 1e11 -- qualquer
    epoch em SEGUNDOS ate o ano 5138 fica abaixo dele.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int | float):
        return float(valor) / 1000.0 if abs(valor) > 1e11 else float(valor)
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(texto).timestamp()
    except ValueError:
        return None


def _detalhes(evento: dict[str, Any]) -> dict[str, Any]:
    bloco = evento.get(_DETALHES_POR_TIPO.get(str(evento.get("type")), ""))
    return bloco if isinstance(bloco, dict) else {}


def _padrao(recurso: str) -> str:
    """`startJobRun.sync` -> sync; `.waitForTaskToken` -> callback; resto -> request_response.

    O historico publica `resourceType` (o servico) e `resource` (a API mais o sufixo)
    em campos SEPARADOS, e por isso aqui nao se parseia ARN nenhum -- diferente de
    `stepfunctions._parse_resource`, que le o `Resource` do ASL inteiro.
    """
    if ".waitForTaskToken" in recurso:
        return "callback"
    if ".sync" in recurso:
        return "sync"
    return "request_response"


def _ancestral(
    evento: dict[str, Any], por_id: dict[int, dict[str, Any]], tipos: frozenset[str]
) -> tuple[dict[str, Any] | None, str | None]:
    """O ancestral mais proximo, pela cadeia de `previousEventId`, cujo tipo esta em `tipos`.

    (evento, None), ou (None, razao). As razoes sao tres e diferentes de proposito:
    `chain_root` (a cadeia acabou sem achar), `chain_broken` (o id referenciado nao
    esta no arquivo -- historico truncado, ou pagina faltando) e `chain_cycle` (um
    arquivo montado a mao que se referencia). Confundi-las esconderia truncamento
    atras de "nao achei".
    """
    visitados: set[int] = set()
    atual = evento
    while True:
        anterior = atual.get("previousEventId")
        if isinstance(anterior, bool) or not isinstance(anterior, int) or anterior <= 0:
            return None, "chain_root"
        if anterior in visitados:
            return None, "chain_cycle"
        visitados.add(anterior)
        pai = por_id.get(anterior)
        if pai is None:
            return None, "chain_broken"
        if str(pai.get("type")) in tipos:
            return pai, None
        atual = pai


def _job_run(saida: Any) -> tuple[str | None, str | None, str | None, list[str]]:
    """(job_run_id, job_name, chave lida, chaves de topo). U1 mora aqui.

    A forma exata do `output` do `TaskSubmitted` do Glue NAO esta na pagina da API: a
    pagina de integracao so diz que o `JobName` e inserido na resposta. Por isso o
    extrator le defensivamente -- objeto, ou string com JSON dentro -- e tenta tres
    chaves, na ordem. O que nao casa sai nomeado COM as chaves de topo, porque e delas
    que um historico real fecha a lacuna.
    """
    if isinstance(saida, str):
        saida, _ = _loads(saida)
    if not isinstance(saida, dict):
        return None, None, None, []
    chaves = sorted(str(k) for k in saida)
    nome = saida.get("JobName")
    nome = nome if isinstance(nome, str) and nome.strip() else None
    for chave in ("JobRunId", "Id"):
        valor = saida.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor, nome, chave, chaves
    aninhado = saida.get("JobRun")
    if isinstance(aninhado, dict):
        valor = aninhado.get("Id")
        if isinstance(valor, str) and valor.strip():
            if nome is None and isinstance(aninhado.get("JobName"), str):
                nome = aninhado["JobName"]
            return valor, nome, "JobRun.Id", chaves
    return None, nome, None, chaves


def _eventos(payload: Any) -> tuple[list[Any] | None, bool, str | None, str]:
    """(eventos, truncado, arn, origem) ou (None, ...) quando nao e historico."""
    if isinstance(payload, list):
        return payload, False, None, "event_list"
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        return None, False, None, ""
    token = payload.get("nextToken")
    arn = payload.get("executionArn")
    return (
        payload["events"],
        bool(isinstance(token, str) and token.strip()),
        arn if isinstance(arn, str) and arn.strip() else None,
        "get_execution_history",
    )


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="sfn.analyzed",
            subject=_file_subject(path),
            measures={
                "execution_count": sum(1 for f in facts if f.kind == "sfn.execution"),
                "attempt_count": sum(1 for f in facts if f.kind == "sfn.attempt"),
                "job_run_count": sum(1 for f in facts if f.kind == "sfn.job_run"),
                "unresolved_count": sum(1 for f in facts if f.kind == "sfn.unresolved"),
            },
            attrs={"extractor": EXTRACTOR_ID},
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def _valida_eventos(
    brutos: list[Any], leitura: _Leitura
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(limpos, com_id). O resto sai nomeado.

    `limpos` sao os eventos que o extrator LE: objeto, com `id` inteiro, e de tipo
    conhecido. `com_id` e mais amplo de proposito -- objeto com `id` inteiro, inclusive
    o de tipo desconhecido --, e serve SO para a travessia da cadeia de
    `previousEventId`. Um tipo que a lista publicada nao tem e a API que cresceu, nao o
    artefato que quebrou: descarta-lo da travessia partiria a cadeia num
    `chain_broken` e apagaria as tentativas do ramo inteiro. Ele continua fora de
    `ordenados`, das contagens e de todo fact -- e a recusa continua saindo.

    `id` REPETIDO nao entra em nenhum dos dois. Ele e unico na execucao pela propria
    API, e repeti-lo e arquivo montado a mao, paginas concatenadas ou colagem errada.
    Antes, `por_id` e `tentativas` (dict por `id`) deixavam o ultimo vencer enquanto
    `ordem_por_estado` ja tinha contado os dois -- saia UMA tentativa afirmando um
    indice que o arquivo nao sustenta, e nenhuma recusa. Agora vence a PRIMEIRA
    ocorrencia, na ordem do arquivo, e cada repeticao sai em `event_id_duplicated`.
    """
    limpos: list[dict[str, Any]] = []
    com_id: list[dict[str, Any]] = []
    vistos: set[int] = set()
    for indice, bruto in enumerate(brutos):
        if not isinstance(bruto, dict):
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_not_an_object",
                    leitura.provenance,
                    measures={"index": indice},
                )
            )
            continue
        identificador = bruto.get("id")
        if isinstance(identificador, bool) or not isinstance(identificador, int):
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_not_an_object",
                    leitura.provenance,
                    measures={"index": indice},
                )
            )
            continue
        if identificador in vistos:
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_id_duplicated",
                    leitura.provenance,
                    measures={"event_id": identificador, "index": indice},
                    type=str(bruto.get("type")),
                )
            )
            continue
        vistos.add(identificador)
        com_id.append(bruto)
        if str(bruto.get("type")) not in _TIPOS_CONHECIDOS:
            leitura.facts.append(
                _unresolved(
                    _file_subject(leitura.path),
                    "event_type_unknown",
                    leitura.provenance,
                    measures={"event_id": identificador},
                    type=str(bruto.get("type")),
                )
            )
            continue
        limpos.append(bruto)
    return limpos, com_id


def _desfecho_da_execucao(eventos: list[dict[str, Any]]) -> tuple[str, str]:
    """(status, classe). `unresolved`/`unresolved` quando nao ha evento terminal."""
    for evento in reversed(eventos):
        status = _STATUS_POR_TIPO.get(str(evento.get("type")))
        if status is not None:
            return status, ("stopped" if status in _PARADA else "finished")
    return "unresolved", "unresolved"


def extract_sfn_history(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado: resposta da API, ou lista de eventos."""
    provenance = _provenance(path, artifact_sha256)
    brutos, truncado, arn, origem = _eventos(payload)
    if brutos is None:
        falha = _unresolved(_file_subject(path), "not_an_execution_history", provenance)
        return _finish([falha], path, provenance)

    leitura = _Leitura(path=path, provenance=provenance)
    eventos, com_id = _valida_eventos(brutos, leitura)
    # `por_id` e a travessia, e leva TODO evento com `id` -- inclusive o de tipo
    # desconhecido, para que ele nao parta a cadeia. `ordenados` e a leitura, e leva so
    # os de tipo conhecido.
    por_id = {int(e["id"]): e for e in com_id}
    ordenados = sorted(eventos, key=lambda e: int(e["id"]))
    status, classe = _desfecho_da_execucao(ordenados)

    if truncado:
        leitura.facts.append(
            _unresolved(_file_subject(path), "truncated", provenance, read_events=len(ordenados))
        )
    if status == "unresolved" and ordenados:
        leitura.facts.append(
            _unresolved(_file_subject(path), "execution_terminal_absent", provenance)
        )

    # 1. Um agendamento -> uma tentativa. O estado vem da cadeia, nunca da ordem.
    tentativas: dict[int, dict[str, Any]] = {}
    ordem_por_estado: dict[str, int] = {}
    for evento in ordenados:
        if str(evento.get("type")) != "TaskScheduled":
            continue
        entrada, razao = _ancestral(evento, por_id, frozenset({"TaskStateEntered"}))
        nome = None
        if entrada is not None:
            detalhes = entrada.get("stateEnteredEventDetails")
            if isinstance(detalhes, dict) and isinstance(detalhes.get("name"), str):
                nome = detalhes["name"]
        if nome is None:
            leitura.facts.append(
                _unresolved(
                    _file_subject(path),
                    "state_unresolved",
                    provenance,
                    measures={"event_id": int(evento["id"])},
                    detail=razao or "state_name_absent",
                )
            )
            continue
        ordem_por_estado[nome] = ordem_por_estado.get(nome, 0) + 1
        tentativas[int(evento["id"])] = {
            "state_name": nome,
            "index": ordem_por_estado[nome],
            "scheduled": evento,
            "terminal": None,
            "submitted": None,
        }

    # 2. Terminal e submissao sobem ate o agendamento DELES.
    for evento in ordenados:
        tipo = str(evento.get("type"))
        if tipo not in _RESULTADO_POR_TIPO and tipo != "TaskSubmitted":
            continue
        agendamento, razao = _ancestral(evento, por_id, frozenset({"TaskScheduled"}))
        alvo = tentativas.get(int(agendamento["id"])) if agendamento is not None else None
        if alvo is None:
            leitura.facts.append(
                _unresolved(
                    _file_subject(path),
                    "attempt_unanchored",
                    provenance,
                    measures={"event_id": int(evento["id"])},
                    type=tipo,
                    detail=razao or "scheduled_not_an_attempt",
                )
            )
            continue
        if tipo == "TaskSubmitted":
            alvo["submitted"] = evento
        elif alvo["terminal"] is None:
            alvo["terminal"] = evento

    # 3. Os facts, em ordem de agendamento.
    for identificador in sorted(tentativas):
        estado = tentativas[identificador]
        leitura.facts.extend(_fatos_da_tentativa(estado, status, classe, leitura))

    inicio = _instante(ordenados[0].get("timestamp")) if ordenados else None
    fim = _instante(ordenados[-1].get("timestamp")) if ordenados else None
    medidas: dict[str, Any] = {
        "event_count": len(ordenados),
        "attempt_count": sum(1 for f in leitura.facts if f.kind == "sfn.attempt"),
        "job_run_count": sum(1 for f in leitura.facts if f.kind == "sfn.job_run"),
    }
    if inicio is not None and fim is not None:
        medidas["duration_seconds"] = round(fim - inicio, 3)
    atributos: dict[str, Any] = {
        "status": status,
        "status_class": classe,
        "source": origem,
        "truncated": truncado,
        "arn_declared": arn is not None,
    }
    if arn is not None:
        atributos["arn"] = arn
    leitura.facts.append(
        Fact(
            kind="sfn.execution",
            subject=_file_subject(path),
            measures=medidas,
            attrs=atributos,
            provenance=provenance,
        )
    )
    return _finish(leitura.facts, path, provenance)


def _fatos_da_tentativa(
    estado: dict[str, Any], status: str, classe: str, leitura: _Leitura
) -> list[Fact]:
    """O `sfn.attempt` e, quando o `output` o sustenta, o `sfn.job_run` dele."""
    agendamento = estado["scheduled"]
    detalhes = _detalhes(agendamento)
    recurso = detalhes.get("resource")
    recurso = recurso if isinstance(recurso, str) else ""
    servico = detalhes.get("resourceType")
    servico = servico if isinstance(servico, str) else ""
    padrao = _padrao(recurso)
    simbolo = f"{estado['state_name']}#{estado['index']}"
    subject = _attempt_subject(leitura.path, simbolo)

    terminal = estado["terminal"]
    resultado = _RESULTADO_POR_TIPO.get(str(terminal.get("type"))) if terminal else None
    detalhes_terminais = _detalhes(terminal) if terminal else {}
    submetido = estado["submitted"]

    atributos: dict[str, Any] = {
        "state_name": estado["state_name"],
        "service": servico,
        "api": recurso.split(".", 1)[0],
        "resource": recurso,
        "pattern": padrao,
        "result": resultado or "none",
        "terminal_present": terminal is not None,
        "submitted": submetido is not None,
        "execution_outcome": status,
        "execution_outcome_class": classe,
        "job_run_outcome_observed": bool(
            padrao == "sync" and resultado in _OBSERVA_O_JOB_RUN
        ),
    }
    for campo in ("error", "cause"):
        valor = detalhes_terminais.get(campo)
        if isinstance(valor, str) and valor:
            atributos[campo] = valor

    medidas: dict[str, Any] = {"attempt_index": estado["index"]}
    inicio = _instante(agendamento.get("timestamp"))
    fim = _instante(terminal.get("timestamp")) if terminal else None
    if inicio is not None and fim is not None:
        medidas["duration_seconds"] = round(fim - inicio, 3)
    limite = detalhes.get("timeoutInSeconds")
    if isinstance(limite, int) and not isinstance(limite, bool):
        medidas["timeout_seconds"] = limite

    saida: list[Fact] = [
        Fact(
            kind="sfn.attempt",
            subject=subject,
            measures=medidas,
            attrs=atributos,
            provenance=leitura.provenance,
        )
    ]
    if submetido is None:
        return saida
    bruto = _detalhes(submetido)
    if "output" not in bruto:
        saida.append(
            _unresolved(
                dict(subject),
                "execution_data_absent",
                leitura.provenance,
                state_name=estado["state_name"],
            )
        )
        return saida
    corrida, nome, chave, chaves = _job_run(bruto["output"])
    if corrida is None:
        saida.append(
            _unresolved(
                dict(subject),
                "job_run_id_unrecognized",
                leitura.provenance,
                state_name=estado["state_name"],
                output_keys=chaves,
            )
        )
        return saida
    saida.append(
        Fact(
            kind="sfn.job_run",
            subject=dict(subject),
            measures={"attempt_index": estado["index"]},
            attrs={
                "job_run_id": corrida,
                "job_name": nome,
                "state_name": estado["state_name"],
                "read_from": chave,
                "source": "task_submitted_output",
            },
            provenance=leitura.provenance,
        )
    )
    return saida


def extract_sfn_history_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `sfn.unresolved` com `read_error`; arquivo acima do teto de
    `scan._teto_para` (o mesmo que a varredura aplica), `size_above_limit` -- e ele
    importa mais aqui do que no ASL, porque historico de execucao longa chega a
    megabytes. Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        tamanho, teto = path.stat().st_size, scan._teto_para(path)
        if tamanho > teto:
            falha = _unresolved(
                _file_subject(anchor), "size_above_limit", vazio, size=tamanho, limit=teto
            )
            return _finish([falha], anchor, vazio)
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = _provenance(anchor, sha)
    parsed, razao = _loads(text)
    if razao is not None:
        falha = _unresolved(_file_subject(anchor), razao, provenance)
        return _finish([falha], anchor, provenance)
    return extract_sfn_history(parsed, anchor, artifact_sha256=sha)


def extract_sfn_history_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: vira `sfn.unresolved` daquele arquivo e a travessia
    continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.json"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_sfn_history_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


def _glue_de_kind(facts: Sequence[Fact], kind: str) -> list[tuple[str, Fact]]:
    """(nome do estado, fact) dos facts daquele kind que chamam `glue:startJobRun`.

    Serve para os dois lados do confronto: `sfn.attempt` (medido) e `sfn.task`
    (declarado). O `subject` dos dois e diferente -- o do ASL e o CAMINHO do estado na
    definicao, o do historico e `<nome>#<ordem>` --, e por isso `same_subject` nao os
    junta e a derivacao existe (o mesmo motivo de `bridge.py` e de
    `build_sfn_glue_link`).
    """
    casados: list[tuple[str, Fact]] = []
    for fact in facts:
        if fact.kind != kind:
            continue
        attrs = fact.attrs or {}
        if attrs.get("service") != "glue" or attrs.get("api") != "startJobRun":
            continue
        nome = attrs.get("state_name")
        if not isinstance(nome, str) or not nome:
            continue
        casados.append((nome, fact))
    return casados


def _glue_por_estado(facts: Sequence[Fact], kind: str) -> dict[str, list[Fact]]:
    """Nome do estado -> facts DECLARADOS daquele kind. So o nome, porque so ele existe.

    O ASL e outro artefato, e nada nele diz de que execucao ele e: o pareamento pelo
    nome e o unico que o historico permite.
    """
    por_nome: dict[str, list[Fact]] = {}
    for nome, fact in _glue_de_kind(facts, kind):
        por_nome.setdefault(nome, []).append(fact)
    return por_nome


def _glue_por_execucao(facts: Sequence[Fact]) -> dict[tuple[str, str], list[Fact]]:
    """(artefato, nome do estado) -> as tentativas MEDIDAS daquela execucao.

    A chave leva o artefato porque cada EXECUCAO tem o seu proprio orcamento de retry.
    Agrupar so pelo nome somaria as tentativas de execucoes diferentes, e a
    `SF-SFNX-001` acusaria de estourar o teto dois runs que CABEM no retry declarado.
    O artefato e a unidade que o historico da: um arquivo de `get-execution-history` e
    uma execucao. Duas execucoes salvas no MESMO arquivo continuariam somando, e nao ha
    campo que as separe -- `executionArn` so existe quando quem salvou o acrescentou, e
    ele nao viaja por evento.
    """
    por_chave: dict[tuple[str, str], list[Fact]] = {}
    for nome, fact in _glue_de_kind(facts, "sfn.attempt"):
        artefato = str((fact.provenance or {}).get("artifact") or "")
        por_chave.setdefault((artefato, nome), []).append(fact)
    return por_chave


def _glue_attempt_absent(facts: Sequence[Fact]) -> list[Fact]:
    """A recusa de quando ha tentativa medida e NENHUMA delas e `glue:startJobRun`.

    O confronto de retry so sabe julgar essa integracao, e o filtro nao alcanca as
    outras formas de chamar o mesmo servico -- a integracao `aws-sdk`, por exemplo,
    publica `resourceType: "aws-sdk:glue"` e `resource: "startJobRun"`. Devolver `[]`
    em silencio deixaria o operador com um case sem confronto e sem uma linha dizendo
    por que, e a regra 20 pede o contrario: "nao sei julgar esta integracao" e diferente
    de "esta tudo bem". Uma recusa por ARTEFATO, que e a unidade que o operador aponta,
    NOMEANDO `<servico>:<api>` de cada tentativa daquele arquivo -- e dai que sai o
    proximo passo, porque e a lista do que o filtro teria de alcancar.
    """
    por_artefato: dict[str, list[Fact]] = {}
    for fact in facts:
        if fact.kind != "sfn.attempt":
            continue
        artefato = str((fact.provenance or {}).get("artifact") or "")
        por_artefato.setdefault(artefato, []).append(fact)
    saida: list[Fact] = []
    for artefato in sorted(por_artefato):
        grupo = por_artefato[artefato]
        observados = sorted(
            {
                f"{(f.attrs or {}).get('service') or ''}:{(f.attrs or {}).get('api') or ''}"
                for f in grupo
            }
        )
        saida.append(
            _unresolved(
                _file_subject(artefato),
                "glue_attempt_absent",
                {
                    "artifact": artefato,
                    "artifact_sha256": "",
                    "extractor": EXTRACTOR_ID,
                    "derived_from": sorted(f.id for f in grupo),
                },
                measures={"attempt_count": len(grupo)},
                observed=observados,
            )
        )
    return saida


def build_sfn_retry_observado(facts: Sequence[Fact]) -> list[Fact]:
    """Confronta o retry DECLARADO no ASL com o OBSERVADO no historico (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `bridge.py`: o motor avalia um
    fact por condicao, e o que ele precisa comparar -- quantas vezes o Task foi
    agendado contra quantas vezes ele PODIA ser -- mora em dois facts de `subject`
    diferente.

    O pareamento e pelo NOME do estado, porque o historico so publica o nome: o
    `stateEnteredEventDetails.name`. Nao ha caminho de estado no historico, e por isso
    dois estados de mesmo nome em ramos de um `Parallel` sao AMBIGUIDADE, nao escolha.

    Os DOIS LADOS SAO CHAVEADOS DIFERENTE, e a assimetria e deliberada. O lado MEDIDO
    e por `(artefato, nome do estado)`: retry e orcamento de UMA execucao, e somar as
    tentativas de duas acusaria de estourar o teto dois runs que cabem nele. O lado
    DECLARADO continua so pelo nome, porque o ASL e outro artefato e nada nele diz de
    que execucao ele e -- e um `sfn.task` pode, legitimamente, parear com varias
    execucoes. Sai um `sfn.retry_observado` por execucao e por estado.

    O `teto_declarado` e `1 + failure_retry_max_attempts` do `sfn.task`: o Step
    Functions agenda o Task uma vez, mais `MaxAttempts` reagendamentos. O efetivo, a
    marca de `MaxAttempts` omitido e a regra de qual retrier casa a falha do job moram
    em `stepfunctions.py`, com a frase citada ao lado -- aqui so se LE o que ele mediu.

    Nada aqui atribui custo (regras 13 e 25): o fact diz quantas vezes, e o `JobRunId`
    de cada tentativa esta em `sfn.job_run`, que e por onde `finops` responde custo com
    `dpu_seconds` medido.
    """
    tentativas = _glue_por_execucao(facts)
    if not tentativas:
        # Ha `sfn.attempt` no pool (o `fuse` so chama esta funcao quando ha), e nenhum
        # deles e `glue:startJobRun`. A lacuna sai com nome, nunca uma lista vazia.
        return sort_facts(_glue_attempt_absent(facts))
    declaradas = _glue_por_estado(facts, "sfn.task")
    ha_asl = any(f.kind == "sfn.task" for f in facts)
    saida: list[Fact] = []
    for artefato, nome in sorted(tentativas):
        # Pelo INDICE da tentativa, com `f.id` so como desempate estavel. `Fact.id` e
        # sha1 do conteudo -- ordem de hash, nao ordem de tentativa --, e com ele
        # sozinho `grupo[-1]` (de onde sai `execution_outcome`) era escolha arbitraria.
        grupo = sorted(
            tentativas[(artefato, nome)],
            key=lambda f: ((f.measures or {}).get("attempt_index", 0), f.id),
        )
        subject = _attempt_subject(artefato, nome)
        proveniencia = {
            "artifact": artefato,
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": sorted(f.id for f in grupo),
        }
        if not ha_asl:
            saida.append(
                _unresolved(dict(subject), "asl_absent", proveniencia, state_name=nome)
            )
            continue
        candidatas = declaradas.get(nome) or []
        if not candidatas:
            saida.append(
                _unresolved(
                    dict(subject), "state_name_absent_in_asl", proveniencia, state_name=nome
                )
            )
            continue
        if len(candidatas) > 1:
            saida.append(
                _unresolved(
                    dict(subject),
                    "state_name_ambiguous",
                    proveniencia,
                    state_name=nome,
                    declared_count=len(candidatas),
                )
            )
            continue
        tarefa = candidatas[0]
        teto = (tarefa.measures or {}).get("failure_retry_max_attempts")
        if isinstance(teto, bool) or not isinstance(teto, int):
            saida.append(
                _unresolved(
                    dict(subject),
                    "declared_ceiling_unreadable",
                    proveniencia,
                    state_name=nome,
                )
            )
            continue
        attrs_da_tarefa = tarefa.attrs or {}
        saida.append(
            Fact(
                kind="sfn.retry_observado",
                subject=dict(subject),
                measures={"tentativas_observadas": len(grupo), "teto_declarado": 1 + teto},
                attrs={
                    "state_name": nome,
                    "job_name": attrs_da_tarefa.get("job_name"),
                    "pattern": attrs_da_tarefa.get("pattern"),
                    "declared_retry_matched": bool(
                        attrs_da_tarefa.get("failure_retry_matched")
                    ),
                    "declared_retry_defaulted": bool(
                        attrs_da_tarefa.get("failure_retry_defaulted")
                    ),
                    "execution_outcome": (grupo[-1].attrs or {}).get("execution_outcome"),
                },
                provenance={
                    **proveniencia,
                    "derived_from": sorted({*proveniencia["derived_from"], tarefa.id}),
                },
            )
        )
    return sort_facts(saida)


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_sfn_retry_observado",
    "extract_sfn_history",
    "extract_sfn_history_path",
    "extract_sfn_history_tree",
]
