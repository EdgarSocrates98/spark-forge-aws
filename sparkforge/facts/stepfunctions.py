"""Extrator de Facts a partir da definicao de uma state machine do AWS Step Functions.

Le a definicao em Amazon States Language (ASL) ja em disco -- o `.asl.json`
versionado no repositorio (qualquer `.json` com `StartAt` e `States`) ou a saida
salva de `aws stepfunctions describe-state-machine` (objeto com `definition` como
STRING JSON e `type`). Como `controlm_jobs.py`, NAO coleta nada e NUNCA levanta
excecao por payload malformado: o que nao consegue ler vira `sfn.unresolved` com
`attrs.reason`, e a sentinela `sfn.analyzed` sai sempre, uma por arquivo.

## Por que `sfn.`

E o nome curto que a propria AWS usa para o servico (ARN `arn:aws:states`, CLI
`aws stepfunctions`), e nenhum kind existente comeca com ele (D1 de
`docs/sdd/STEP_FUNCTIONS/design.md`).

## O que sai

- `sfn.state_machine` -- um por definicao lida. `attrs.type` e `STANDARD`,
  `EXPRESS` ou `undeclared`: um `.asl.json` nao carrega o tipo, que so vem na saida
  de `describe-state-machine`. Sem ela o tipo e `undeclared`, NUNCA `STANDARD` por
  suposicao.
- `sfn.task` -- um por estado `Task`, inclusive dentro de `Parallel.Branches[]` e de
  `Map.ItemProcessor` (e do legado `Map.Iterator`). O `subject.symbol` e o CAMINHO do
  estado na definicao (`States/Cargas/Branches/0/States/Carga`): dois estados de
  mesmo nome em ramos diferentes sao duas entidades para `same_subject`. O tipo da
  state machine viaja em `attrs.state_machine_type` porque o motor avalia um fact
  por condicao (regra 33).
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`, `invalid_json`,
  `not_a_state_machine`, `definition_not_string`, `state_not_an_object`,
  `resource_absent` e `resource_dynamic`.
- `sfn.analyzed` -- a sentinela, com as contagens.

## Os defaults publicados moram AQUI, com a fonte ao lado

A regra nao sabe o default, e `rules/expr.py` nao tem funcao. O fact grava o valor
EFETIVO e a marca de que ele foi omitido (D2):

- `MaxAttempts` "(3 by default)" -- concepts-error-handling;
- `TimeoutSeconds` "The default value is 99,999,999" -- state-task.

## Qual retrier pega a falha do job

`States.TaskFailed` "matches any known error name except for States.Timeout", e
`States.ALL` casa tudo menos `States.Runtime` (concepts-error-handling). A leitura
adotada aqui: a falha do JobRun sob `.sync` e casada pelo PRIMEIRO retrier, na ordem
declarada, cujo `ErrorEquals` contem um dos dois; retrier so de erro nomeado
(`Glue.ConcurrentRunsExceededException`) nao casa a falha do job. O efetivo dele
sai em `measures.failure_retry_max_attempts`; sem retrier que case, `0`.

## JobName

Literal quando `JobName` e string sem `{% %}`; dinamico quando a chave e `JobName.$`
(JSONPath) ou o valor e expressao JSONata. So o literal liga o estado ao
`aws_glue_job` de mesmo nome.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "stepfunctions@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sfn.state_machine",
        "sfn.task",
        "sfn.unresolved",
        "sfn.analyzed",
    }
)

# https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
# MaxAttempts: "(3 by default)".
DEFAULT_MAX_ATTEMPTS = 3
# https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
# TimeoutSeconds: "The default value is 99,999,999".
DEFAULT_TIMEOUT_SECONDS = 99_999_999

_FAILURE_ERRORS = frozenset({"States.ALL", "States.TaskFailed"})
_DECLARED_TYPES = frozenset({"STANDARD", "EXPRESS"})
_UNDECLARED = "undeclared"


@dataclass
class _Leitura:
    """O estado de UMA definicao sendo lida: onde, com que tipo, e o que ja saiu."""

    path: str
    machine_type: str
    query_language: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)
    state_count: int = 0


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _state_subject(path: str, state_path: str) -> dict[str, Any]:
    subject = _file_subject(path)
    subject["symbol"] = state_path
    return subject


def _provenance(path: str, sha: str) -> dict[str, Any]:
    return {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="sfn.unresolved",
        subject=subject,
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _is_jsonata(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    texto = value.strip()
    return texto.startswith("{%") and texto.endswith("%}")


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _target(service: str, api: str, pattern: str, integration: str) -> dict[str, str]:
    return {"service": service, "api": api, "pattern": pattern, "integration": integration}


def _parse_resource(resource: str) -> dict[str, str]:
    """Servico, API, padrao e forma de integracao, lidos do ARN do `Resource`.

    `arn:aws:states:::glue:startJobRun.sync` -> glue, startJobRun, sync, optimized. O
    sufixo decide o padrao: `.sync` (inclusive `.sync:2`) e `sync`,
    `.waitForTaskToken` e `callback`, sem sufixo e `request_response`.
    """
    partes = resource.split(":")
    if len(partes) < 6 or partes[0] != "arn":
        return _target("", "", "request_response", "other")
    if partes[2] == "lambda":
        return _target("lambda", "invoke", "request_response", "function_arn")
    if partes[2] != "states":
        return _target(partes[2], "", "request_response", "other")
    cauda = partes[5:]
    integracao = "optimized"
    if cauda and cauda[0] == "aws-sdk":
        integracao = "sdk"
        cauda = cauda[1:]
    if cauda and cauda[0] == "activity":
        return _target("activity", "", "activity", "activity")
    if len(cauda) < 2:
        return _target(cauda[0] if cauda else "", "", "request_response", "other")
    chamada = ":".join(cauda[1:])
    if ".waitForTaskToken" in chamada:
        padrao = "callback"
    elif ".sync" in chamada:
        padrao = "sync"
    else:
        padrao = "request_response"
    return _target(cauda[0], chamada.split(".", 1)[0], padrao, integracao)


def _job_name(state: dict[str, Any]) -> tuple[str | None, str]:
    """(nome literal, origem): `literal`, `jsonpath`, `jsonata`, `unreadable` ou `absent`."""
    for bloco in ("Arguments", "Parameters"):
        argumentos = state.get(bloco)
        if _is_jsonata(argumentos):
            return None, "jsonata"
        if not isinstance(argumentos, dict):
            continue
        if "JobName.$" in argumentos:
            return None, "jsonpath"
        if "JobName" not in argumentos:
            continue
        valor = argumentos["JobName"]
        if _is_jsonata(valor):
            return None, "jsonata"
        if isinstance(valor, str) and valor.strip():
            return valor, "literal"
        return None, "unreadable"
    return None, "absent"


def _job_attrs(state: dict[str, Any], service: str) -> dict[str, Any]:
    if service != "glue":
        return {"job_name": None, "job_name_dynamic": False, "job_name_source": "not_applicable"}
    nome, origem = _job_name(state)
    return {"job_name": nome, "job_name_dynamic": origem != "literal", "job_name_source": origem}


def _retriers(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Cada retrier com o `MaxAttempts` EFETIVO e a marca de omitido (D2)."""
    bruto = state.get("Retry")
    saida: list[dict[str, Any]] = []
    for retrier in bruto if isinstance(bruto, list) else []:
        if not isinstance(retrier, dict):
            continue
        erros = retrier.get("ErrorEquals")
        nomes = [e for e in erros if isinstance(e, str)] if isinstance(erros, list) else []
        if "MaxAttempts" not in retrier:
            efetivo, omitido = DEFAULT_MAX_ATTEMPTS, True
        else:
            valor = retrier["MaxAttempts"]
            efetivo, omitido = (valor if _is_count(valor) else None), False
        saida.append(
            {"error_equals": nomes, "max_attempts": efetivo, "max_attempts_defaulted": omitido}
        )
    return saida


def _failure_retrier(retriers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """O PRIMEIRO retrier, na ordem declarada, que casa a falha do job."""
    for retrier in retriers:
        if _FAILURE_ERRORS & set(retrier["error_equals"]):
            return retrier
    return None


def _timeout(state: dict[str, Any]) -> tuple[bool, bool, int | None]:
    """(declarado, dinamico, segundos efetivos). `TimeoutSecondsPath` e dinamico."""
    if "TimeoutSecondsPath" in state:
        return True, True, None
    if "TimeoutSeconds" not in state:
        return False, False, DEFAULT_TIMEOUT_SECONDS
    valor = state["TimeoutSeconds"]
    if _is_count(valor) and valor > 0:
        return True, False, valor
    return True, True, None


def _task_fact(state: dict[str, Any], name: str, state_path: str, leitura: _Leitura) -> Fact:
    recurso = state["Resource"]
    alvo = _parse_resource(recurso)
    retriers = _retriers(state)
    falha = _failure_retrier(retriers)
    declarado, dinamico, segundos = _timeout(state)
    linguagem = state.get("QueryLanguage")
    attrs: dict[str, Any] = {
        "state_name": name,
        "resource": recurso,
        **alvo,
        **_job_attrs(state, alvo["service"]),
        "retriers": retriers,
        "failure_retry_matched": falha is not None,
        "failure_retry_defaulted": falha is not None and falha["max_attempts_defaulted"],
        "has_catch": bool(state.get("Catch")),
        "has_next": isinstance(state.get("Next"), str),
        "end": state.get("End") is True,
        "timeout_declared": declarado,
        "timeout_dynamic": dinamico,
        "state_machine_type": leitura.machine_type,
        "query_language": linguagem if isinstance(linguagem, str) else leitura.query_language,
    }
    measures: dict[str, Any] = {"retrier_count": len(retriers)}
    if falha is None:
        measures["failure_retry_max_attempts"] = 0
    elif falha["max_attempts"] is not None:
        measures["failure_retry_max_attempts"] = falha["max_attempts"]
    if segundos is not None:
        measures["timeout_seconds"] = segundos
    return Fact(
        kind="sfn.task",
        subject=_state_subject(leitura.path, state_path),
        measures=measures,
        attrs=attrs,
        provenance=leitura.provenance,
    )


def _walk(states: dict[str, Any], base: str, leitura: _Leitura) -> None:
    """Percorre `States`, descendo em `Parallel.Branches[]` e `Map.ItemProcessor`/`Iterator`."""
    for nome, corpo in states.items():
        state_path = f"{base}/States/{nome}" if base else f"States/{nome}"
        leitura.state_count += 1
        subject = _state_subject(leitura.path, state_path)
        if not isinstance(corpo, dict):
            leitura.facts.append(_unresolved(subject, "state_not_an_object", leitura.provenance))
            continue
        tipo = corpo.get("Type")
        if tipo == "Task":
            recurso = corpo.get("Resource")
            if recurso is None:
                leitura.facts.append(_unresolved(subject, "resource_absent", leitura.provenance))
            elif not isinstance(recurso, str) or not recurso.strip() or _is_jsonata(recurso):
                leitura.facts.append(_unresolved(subject, "resource_dynamic", leitura.provenance))
            else:
                leitura.facts.append(_task_fact(corpo, str(nome), state_path, leitura))
        elif tipo == "Parallel":
            ramos = corpo.get("Branches")
            for indice, ramo in enumerate(ramos if isinstance(ramos, list) else []):
                if isinstance(ramo, dict) and isinstance(ramo.get("States"), dict):
                    _walk(ramo["States"], f"{state_path}/Branches/{indice}", leitura)
        elif tipo == "Map":
            for chave in ("ItemProcessor", "Iterator"):
                processador = corpo.get(chave)
                if isinstance(processador, dict) and isinstance(processador.get("States"), dict):
                    _walk(processador["States"], f"{state_path}/{chave}", leitura)


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="sfn.analyzed",
            subject=_file_subject(path),
            measures={
                "state_machine_count": sum(1 for f in facts if f.kind == "sfn.state_machine"),
                "task_count": sum(1 for f in facts if f.kind == "sfn.task"),
                "unresolved_count": sum(1 for f in facts if f.kind == "sfn.unresolved"),
            },
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def extract_stepfunctions(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado: ASL, ou a saida de `describe-state-machine`."""
    provenance = _provenance(path, artifact_sha256)
    if not isinstance(payload, dict):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([falha], path, provenance)
    origem, tipo, nome, definicao = "asl", _UNDECLARED, None, payload
    if "definition" in payload:
        origem = "describe_state_machine"
        bruto = payload["definition"]
        if not isinstance(bruto, str):
            falha = _unresolved(_file_subject(path), "definition_not_string", provenance)
            return _finish([falha], path, provenance)
        try:
            definicao = json.loads(bruto)
        except json.JSONDecodeError:
            falha = _unresolved(_file_subject(path), "invalid_json", provenance, at="definition")
            return _finish([falha], path, provenance)
        declarado = payload.get("type")
        if isinstance(declarado, str) and declarado in _DECLARED_TYPES:
            tipo = declarado
        if isinstance(payload.get("name"), str):
            nome = payload["name"]
    if not (
        isinstance(definicao, dict)
        and isinstance(definicao.get("StartAt"), str)
        and isinstance(definicao.get("States"), dict)
    ):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([falha], path, provenance)
    linguagem = definicao.get("QueryLanguage")
    leitura = _Leitura(
        path=path,
        machine_type=tipo,
        query_language=linguagem if isinstance(linguagem, str) else "JSONPath",
        provenance=provenance,
    )
    _walk(definicao["States"], "", leitura)
    attrs: dict[str, Any] = {
        "type": tipo,
        "type_declared": tipo != _UNDECLARED,
        "query_language": leitura.query_language,
        "source": origem,
    }
    if nome is not None:
        attrs["name"] = nome
    leitura.facts.append(
        Fact(
            kind="sfn.state_machine",
            subject=_file_subject(path),
            measures={
                "state_count": leitura.state_count,
                "task_count": sum(1 for f in leitura.facts if f.kind == "sfn.task"),
            },
            attrs=attrs,
            provenance=provenance,
        )
    )
    return _finish(leitura.facts, path, provenance)


def extract_stepfunctions_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `sfn.unresolved` com `read_error`; JSON invalido,
    `invalid_json`. Nunca uma excecao que derruba quem chamou.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = _provenance(anchor, sha)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        falha = _unresolved(_file_subject(anchor), "invalid_json", provenance)
        return _finish([falha], anchor, provenance)
    return extract_stepfunctions(parsed, anchor, artifact_sha256=sha)


def extract_stepfunctions_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: vira `sfn.unresolved` daquele arquivo e a
    travessia continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.json"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_stepfunctions_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_TIMEOUT_SECONDS",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_stepfunctions",
    "extract_stepfunctions_path",
    "extract_stepfunctions_tree",
]
