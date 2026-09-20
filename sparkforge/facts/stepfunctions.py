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
  por condicao (regra 33). Pelo mesmo motivo, dois atributos derivados da state
  machine inteira: `polled_by_get_job_run` (a MESMA definicao tem um Task
  `glue:getJobRun`, o padrao de espera por consulta) e `effective_has_next` (o
  `Next` do proprio estado, ou -- quando o Task e `End` de um ramo de `Parallel` ou
  `Map` -- o `Next` efetivo do conteiner mais proximo, em `enclosing_has_next`).
- `sfn.unresolved` -- o que nao deu para ler. Razoes: `read_error`,
  `size_above_limit`, `invalid_json`, `json_too_deep`, `json_too_large`,
  `not_a_state_machine`, `definition_not_string`, `type_unrecognized`,
  `state_not_an_object`,
  `resource_absent`, `resource_dynamic` e `max_attempts_unreadable` (com o estado e
  o `retrier_index`).
- `sfn.analyzed` -- a sentinela, com as contagens.
- `sfn.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_sfn_glue_link` liga
  o Task do Glue ao `aws_glue_job` de mesmo `name` quando os dois estao no pool, e
  `fusion.fuse` a chama. So Task `.sync` liga: em Request Response o retrier cobre a
  chamada `StartJobRun`, nao a falha do job. As razoes de `sfn.unresolved` que so ela
  emite: `job_name_absent`, `job_name_dynamic`, `job_definition_absent`,
  `job_definition_ambiguous` e `glue_max_retries_not_literal`.

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
(JSONPath) ou o valor e expressao JSONata; ausente quando nao ha `JobName` ou ele nao
e texto. So o literal liga o estado ao `aws_glue_job` de mesmo nome.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.facts import scan
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "stepfunctions@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "sfn.state_machine",
        "sfn.task",
        "sfn.unresolved",
        "sfn.analyzed",
        "sfn.glue_job_link",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `sfn.task` no pool, o `fuse` sai byte a
# byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"sfn.task"})

# https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
# MaxAttempts: "(3 by default)".
DEFAULT_MAX_ATTEMPTS = 3
# https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
# TimeoutSeconds: "The default value is 99,999,999".
DEFAULT_TIMEOUT_SECONDS = 99_999_999

_FAILURE_ERRORS = frozenset({"States.ALL", "States.TaskFailed"})
_DECLARED_TYPES = frozenset({"STANDARD", "EXPRESS"})
_UNDECLARED = "undeclared"
# Origens de `JobName` que sao expressao avaliada em execucao, e nao ausencia.
_DYNAMIC_SOURCES = frozenset({"jsonpath", "jsonata"})


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
    return {
        "job_name": nome,
        "job_name_dynamic": origem in _DYNAMIC_SOURCES,
        "job_name_source": origem,
    }


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


def _task_fact(
    state: dict[str, Any], name: str, state_path: str, enclosing_has_next: bool, leitura: _Leitura
) -> Fact:
    recurso = state["Resource"]
    alvo = _parse_resource(recurso)
    retriers = _retriers(state)
    for indice, retrier in enumerate(retriers):
        if retrier["max_attempts"] is None:
            leitura.facts.append(
                _unresolved(
                    _state_subject(leitura.path, state_path),
                    "max_attempts_unreadable",
                    leitura.provenance,
                    retrier_index=indice,
                )
            )
    falha = _failure_retrier(retriers)
    has_next = isinstance(state.get("Next"), str)
    end = state.get("End") is True
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
        "has_next": has_next,
        "end": end,
        "enclosing_has_next": enclosing_has_next,
        "effective_has_next": has_next or (end and enclosing_has_next),
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


def _walk(
    states: dict[str, Any], base: str, leitura: _Leitura, enclosing_has_next: bool = False
) -> None:
    """Percorre `States`, descendo em `Parallel.Branches[]` e `Map.ItemProcessor`/`Iterator`.

    `enclosing_has_next` e o `Next` EFETIVO do conteiner mais proximo: o `End` de um
    ramo encerra o ramo, e o `Next` do `Parallel`/`Map` roda depois dele. No nivel de
    cima nao ha conteiner, e o valor e `False`.
    """
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
                leitura.facts.append(
                    _task_fact(corpo, str(nome), state_path, enclosing_has_next, leitura)
                )
            continue
        # O `Next` efetivo deste conteiner, para os estados dos ramos dele.
        seguinte = isinstance(corpo.get("Next"), str) or (
            corpo.get("End") is True and enclosing_has_next
        )
        if tipo == "Parallel":
            ramos = corpo.get("Branches")
            for indice, ramo in enumerate(ramos if isinstance(ramos, list) else []):
                if isinstance(ramo, dict) and isinstance(ramo.get("States"), dict):
                    _walk(ramo["States"], f"{state_path}/Branches/{indice}", leitura, seguinte)
        elif tipo == "Map":
            for chave in ("ItemProcessor", "Iterator"):
                processador = corpo.get(chave)
                if isinstance(processador, dict) and isinstance(processador.get("States"), dict):
                    _walk(processador["States"], f"{state_path}/{chave}", leitura, seguinte)


def _mark_polling(leitura: _Leitura) -> None:
    """`polled_by_get_job_run` em cada Task: a MESMA definicao consulta o JobRun?

    O padrao de espera sem `.sync` e `startJobRun` -> `Wait` -> `glue:getJobRun` ->
    `Choice`. O predicado e sobre a state machine inteira, e o motor avalia um fact
    por condicao: por isso ele e derivado aqui (regra 33). Nao confere se a consulta
    e do MESMO job -- o `RunId` e dinamico por natureza.
    """
    tasks = [f for f in leitura.facts if f.kind == "sfn.task"]
    consulta = any(
        f.attrs.get("service") == "glue" and f.attrs.get("api") == "getJobRun" for f in tasks
    )
    for fact in tasks:
        fact.attrs["polled_by_get_job_run"] = consulta


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


def _loads(texto: str) -> tuple[Any, str | None]:
    """(valor, None) ou (None, razao). Nunca levanta.

    O decodificador de JSON levanta `RecursionError` com aninhamento profundo e
    `MemoryError` com payload hostil -- o mesmo payload em arquivo e no `definition` do
    `describe-state-machine`. As tres formas de falha saem nomeadas, e nenhuma derruba
    quem chamou: `extract_stepfunctions_path` chamado direto fica fora do
    `except Exception` de `_tree`, e o modulo promete NUNCA levantar por payload
    malformado. Gemeo de `sfn_history._loads`, e as duas tratam as mesmas tres.
    """
    try:
        return json.loads(texto), None
    except RecursionError:
        return None, "json_too_deep"
    except MemoryError:
        return None, "json_too_large"
    except ValueError:  # inclui json.JSONDecodeError
        return None, "invalid_json"


def extract_stepfunctions(payload: Any, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts de um payload ja carregado: ASL, ou a saida de `describe-state-machine`."""
    provenance = _provenance(path, artifact_sha256)
    if not isinstance(payload, dict):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([falha], path, provenance)
    origem, tipo, nome, definicao = "asl", _UNDECLARED, None, payload
    desconhecido: list[Fact] = []
    if "definition" in payload:
        origem = "describe_state_machine"
        bruto = payload["definition"]
        if not isinstance(bruto, str):
            falha = _unresolved(_file_subject(path), "definition_not_string", provenance)
            return _finish([falha], path, provenance)
        definicao, razao = _loads(bruto)
        if razao is not None:
            falha = _unresolved(_file_subject(path), razao, provenance, at="definition")
            return _finish([falha], path, provenance)
        declarado = payload.get("type")
        if isinstance(declarado, str) and declarado in _DECLARED_TYPES:
            tipo = declarado
        elif "type" in payload:
            desconhecido.append(
                _unresolved(
                    _file_subject(path), "type_unrecognized", provenance, value=str(declarado)
                )
            )
        if isinstance(payload.get("name"), str):
            nome = payload["name"]
    if not (
        isinstance(definicao, dict)
        and isinstance(definicao.get("StartAt"), str)
        and isinstance(definicao.get("States"), dict)
    ):
        falha = _unresolved(_file_subject(path), "not_a_state_machine", provenance)
        return _finish([*desconhecido, falha], path, provenance)
    linguagem = definicao.get("QueryLanguage")
    leitura = _Leitura(
        path=path,
        machine_type=tipo,
        query_language=linguagem if isinstance(linguagem, str) else "JSONPath",
        provenance=provenance,
        facts=desconhecido,
    )
    _walk(definicao["States"], "", leitura)
    _mark_polling(leitura)
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

    Falha ao abrir vira `sfn.unresolved` com `read_error`; arquivo acima do teto de
    `scan._teto_para` (o mesmo que a varredura aplica), `size_above_limit`; JSON
    invalido, `invalid_json`; aninhamento que estoura a pilha do decodificador,
    `json_too_deep`; payload hostil que estoura a memoria dele, `json_too_large`. Nunca
    uma excecao que derruba quem chamou.
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


def _glue_jobs_por_nome(facts: Sequence[Fact]) -> dict[str, list[tuple[str, str, str]]]:
    """Nome literal do job -> [(arquivo, endereco, id do fact)], de `tf.attribute` `name`."""
    nomes: dict[str, list[tuple[str, str, str]]] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        subject = fact.subject or {}
        attrs = fact.attrs or {}
        simbolo = str(subject.get("symbol") or "")
        if not simbolo.startswith("aws_glue_job."):
            continue
        if attrs.get("key") != "name" or attrs.get("block") != "root" or not attrs.get("literal"):
            continue
        arquivo = str(subject.get("file") or "")
        nomes.setdefault(str(attrs.get("value")), []).append((arquivo, simbolo, fact.id))
    return nomes


def _max_retries(
    facts: Sequence[Fact], arquivo: str, simbolo: str
) -> tuple[str, int | None, str | None]:
    """(`literal`, n, id), (`absent`, 0, None) ou (`not_literal`, None, id|None).

    O terceiro elemento e o id do `tf.attribute` lido, que entra em `derived_from`.

    `absent` vale 0 porque o atributo nao declarado nao pede retry. Valor interpolado
    vira `tf.unresolved` sem o endereco do recurso (`terraform.py`); por isso qualquer
    `tf.unresolved` de `max_retries` no MESMO arquivo torna a resposta `not_literal` --
    conservador de proposito: nunca um zero que ninguem leu.
    """
    for fact in facts:
        subject = fact.subject or {}
        if fact.kind != "tf.attribute" or subject.get("symbol") != simbolo:
            continue
        if subject.get("file") != arquivo:
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != "max_retries" or attrs.get("block") != "root":
            continue
        valor = (fact.measures or {}).get("value")
        if attrs.get("literal") and isinstance(valor, int | float) and not isinstance(valor, bool):
            return "literal", int(valor), fact.id
        return "not_literal", None, fact.id
    interpolado = any(
        f.kind == "tf.unresolved"
        and (f.attrs or {}).get("key") == "max_retries"
        and (f.subject or {}).get("file") == arquivo
        for f in facts
    )
    return ("not_literal", None, None) if interpolado else ("absent", 0, None)


def build_sfn_glue_link(facts: Sequence[Fact]) -> list[Fact]:
    """Liga cada `sfn.task` do Glue ao `aws_glue_job` de mesmo `name` literal (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `lakeformation.build_lakeformation`:
    o motor avalia um fact por condicao, e os dois lados tem `subject` diferente -- o
    estado da state machine e o recurso do Terraform --, entao `same_subject` nao os
    junta. Nao liga por substring: nome de job e chave exata na API do Glue.

    `sfn_retry_effective` e o `failure_retry_max_attempts` do Task: o efetivo do
    PRIMEIRO retrier que casa a falha do job (ver o docstring do modulo). O que nao liga
    sai nomeado em `sfn.unresolved`, nunca como vinculo.

    So Task `.sync`: sob Request Response o estado termina quando o Glue aceita o
    pedido, e o retrier cobre a chamada `StartJobRun`, nao a falha do JobRun -- nao ha
    retry do Step Functions sobre o job para compor com o do Glue.
    """
    nomes = _glue_jobs_por_nome(facts)
    saida: list[Fact] = []
    for task in facts:
        attrs = task.attrs or {}
        if task.kind != "sfn.task" or attrs.get("service") != "glue":
            continue
        if attrs.get("api") != "startJobRun" or attrs.get("pattern") != "sync":
            continue
        proveniencia = {
            "artifact": str((task.provenance or {}).get("artifact", "")),
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": [task.id],
        }
        nome = attrs.get("job_name")
        if attrs.get("job_name_dynamic") or not isinstance(nome, str):
            dinamico = attrs.get("job_name_source") in _DYNAMIC_SOURCES
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "job_name_dynamic" if dinamico else "job_name_absent",
                    proveniencia,
                    job_name_source=attrs.get("job_name_source", ""),
                    unblocked_by="JobName literal no estado Task",
                )
            )
            continue
        candidatos = nomes.get(nome, [])
        if len(candidatos) != 1:
            razao = "job_definition_absent" if not candidatos else "job_definition_ambiguous"
            saida.append(
                _unresolved(
                    dict(task.subject),
                    razao,
                    proveniencia,
                    job_name=nome,
                    resources=[simbolo for _, simbolo, _ in candidatos],
                    unblocked_by="sparkforge analyze terraform no aws_glue_job, e fuse",
                )
            )
            continue
        arquivo, simbolo, nome_id = candidatos[0]
        origem, retries, retries_id = _max_retries(facts, arquivo, simbolo)
        usados = [nome_id] + ([retries_id] if retries_id is not None else [])
        proveniencia = {**proveniencia, "derived_from": [task.id, *usados]}
        measures: dict[str, Any] = {}
        efetivo = (task.measures or {}).get("failure_retry_max_attempts")
        if efetivo is not None:
            measures["sfn_retry_effective"] = efetivo
        if retries is not None:
            measures["glue_max_retries"] = retries
        saida.append(
            Fact(
                kind="sfn.glue_job_link",
                subject=dict(task.subject),
                measures=measures,
                attrs={
                    "job_name": nome,
                    "resource": simbolo,
                    "resource_file": arquivo,
                    "glue_max_retries_source": origem,
                    "sfn_retry_defaulted": bool(attrs.get("failure_retry_defaulted")),
                },
                provenance=proveniencia,
            )
        )
        if origem == "not_literal":
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "glue_max_retries_not_literal",
                    proveniencia,
                    job_name=nome,
                    resource=simbolo,
                )
            )
    return sort_facts(saida)


__all__ = [
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_TIMEOUT_SECONDS",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_sfn_glue_link",
    "extract_stepfunctions",
    "extract_stepfunctions_path",
    "extract_stepfunctions_tree",
]
