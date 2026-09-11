"""Scorecard de uma execucao: cada pergunta da suite contra o transcript dela.

Funcao PURA sobre `Suite` e `Fact`: nao le arquivo, nao executa agente. A
entrada e o que `sparkforge.facts.host_transcript` ja extraiu de cada
transcript, indexado pelo id da pergunta (o stem do arquivo).

Quatro medidas, uma coluna cada, e NENHUMA nota composta: peso entre elas seria
convencao vestida de medida, o mesmo problema dos pesos de `assess_claim`.

  * resposta -- `correct`, `wrong`, `answer_absent` (sem linha `ANSWER:`) ou
    `over_abstention` (respondeu `unresolved` onde havia valor). Igualdade de
    string exata depois de tirar espaco das pontas, sem normalizar formatacao:
    o protocolo da suite pede o valor puro, e perdoar crase aqui esconderia um
    protocolo que o agente nao seguiu.
  * abstencao -- so em `expects_abstention`: `abstained` ou `false_certainty`.
  * tools -- `required_tools` por verbo canonico e `order` como ordem parcial
    sobre a PRIMEIRA ocorrencia de cada verbo. Tool extra nao reprova; conta.
  * custo -- chamadas, bytes de resultado vistos no transcript e tokens do
    usage do host. Byte e token em campos separados, nunca somados (regra 22).
    Sem usage, `tokens_unresolved` (regra 24).

Pergunta sem transcript, ou com transcript que nao e deste host, ou sem nenhuma
mensagem de assistente, sai `ungraded` com a razao -- nunca `wrong`: medicao
que falha nao pode virar nota ruim (regra 27).

Agregados de custo usam `median_low`: com N par, a mediana comum publicaria a
media dos dois do meio, um valor que nenhuma pergunta teve (regra 12).
"""
from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from sparkforge.evals.suite import Question, Suite
from sparkforge.findings.models import Fact

SCHEMA_VERSION = 1
UNRESOLVED_ANSWER = "unresolved"
_TOKENS = (
    ("input", "input_tokens"),
    ("output", "output_tokens"),
    ("cache_read", "cache_read_tokens"),
    ("cache_creation", "cache_creation_tokens"),
)


def _of(facts: Sequence[Fact], kind: str) -> list[Fact]:
    return [f for f in facts if f.kind == kind]


def _unresolved(facts: Sequence[Fact]) -> list[dict[str, Any]]:
    return [
        {"reason": str(f.attrs.get("reason")), "count": int(f.measures.get("count", 0))}
        for f in _of(facts, "host.transcript.unresolved")
    ]


def _ungraded(qid: str, unresolved: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": qid,
        "status": "ungraded",
        "answer": None,
        "abstention": None,
        "tools": None,
        "cost": None,
        "unresolved": unresolved,
    }


def _answer_verdict(question: Question, final: str | None) -> tuple[str | None, str | None]:
    if final is None:
        return "answer_absent", None
    recusou = final.lower() == UNRESOLVED_ANSWER
    if question.expects_abstention:
        return None, ("abstained" if recusou else "false_certainty")
    if recusou:
        return "over_abstention", None
    return ("correct" if final == question.expected else "wrong"), None


def _tools_verdict(question: Question, calls: Sequence[Fact]) -> dict[str, Any]:
    verbos = [c.attrs.get("verb") for c in calls if c.attrs.get("channel") in ("mcp", "bash")]
    primeira: dict[str, int] = {}
    for posicao, verbo in enumerate(verbos):
        if isinstance(verbo, str):
            primeira.setdefault(verbo, posicao)
    faltando = [
        t if isinstance(t, str) else "|".join(t)
        for t in question.required_tools
        if not (t in primeira if isinstance(t, str) else any(a in primeira for a in t))
    ]
    violada = [
        f"{antes}<{depois}"
        for antes, depois in question.order
        if antes in primeira and depois in primeira and primeira[antes] > primeira[depois]
    ]
    return {
        "verdict": "ok" if not faltando and not violada else "failed",
        "missing": faltando,
        "order_violated": violada,
    }


def _cost(calls: Sequence[Fact], usage: Sequence[Fact]) -> dict[str, Any]:
    custo: dict[str, Any] = {
        "tool_calls": len(calls),
        "other_calls": sum(1 for c in calls if c.attrs.get("channel") == "other"),
        "tool_errors": sum(1 for c in calls if c.attrs.get("is_error") is True),
        "tool_result_bytes": sum(int(c.measures.get("result_bytes", 0)) for c in calls),
    }
    if usage:
        medidas = usage[0].measures
        custo["tokens"] = {nome: int(medidas.get(chave, 0)) for nome, chave in _TOKENS}
        custo["tokens_unresolved"] = False
    else:
        custo["tokens"] = None
        custo["tokens_unresolved"] = True
    return custo


def grade_question(question: Question, facts: Sequence[Fact] | None) -> dict[str, Any]:
    if facts is None:
        return _ungraded(question.id, [{"reason": "transcript_not_found", "count": 1}])
    lacunas = _unresolved(facts)
    transcript = _of(facts, "host.transcript")
    if not transcript:
        return _ungraded(question.id, lacunas)
    if int(transcript[0].measures.get("assistant_message_count", 0)) == 0:
        return _ungraded(question.id, [*lacunas, {"reason": "no_assistant_message", "count": 1}])

    finais = _of(facts, "host.final_answer")
    final = str(finais[0].attrs.get("answer")) if finais else None
    resposta, abstencao = _answer_verdict(question, final)
    calls = sorted(_of(facts, "host.tool_call"), key=lambda c: int(c.measures["ordinal"]))
    return {
        "id": question.id,
        "status": "graded",
        "answer": resposta,
        "abstention": abstencao,
        "tools": _tools_verdict(question, calls),
        "cost": _cost(calls, _of(facts, "host.usage")),
        "unresolved": lacunas,
    }


def _spread(valores: list[int]) -> dict[str, int] | None:
    if not valores:
        return None
    return {"median_low": statistics.median_low(valores), "max": max(valores)}


def _totals(suite: Suite, perguntas: list[dict[str, Any]]) -> dict[str, Any]:
    pontuadas = [p for p in perguntas if p["status"] == "graded"]

    def conta(campo: str, valor: str) -> int:
        return sum(1 for p in pontuadas if p[campo] == valor)

    com_tokens = [p for p in pontuadas if not p["cost"]["tokens_unresolved"]]
    return {
        "questions": len(perguntas),
        "graded": len(pontuadas),
        "ungraded": len(perguntas) - len(pontuadas),
        "correct": conta("answer", "correct"),
        "wrong": conta("answer", "wrong"),
        "answer_absent": conta("answer", "answer_absent"),
        "over_abstention": conta("answer", "over_abstention"),
        "abstention_total": sum(1 for q in suite.questions if q.expects_abstention),
        "abstained": conta("abstention", "abstained"),
        "false_certainty": conta("abstention", "false_certainty"),
        "tools_ok": sum(1 for p in pontuadas if p["tools"]["verdict"] == "ok"),
        "tokens_unresolved_questions": len(pontuadas) - len(com_tokens),
        "cost": {
            "tool_calls": _spread([p["cost"]["tool_calls"] for p in pontuadas]),
            "tool_result_bytes": _spread([p["cost"]["tool_result_bytes"] for p in pontuadas]),
            "output_tokens": _spread([p["cost"]["tokens"]["output"] for p in com_tokens]),
        },
    }


def grade(
    suite: Suite,
    transcripts: Mapping[str, Sequence[Fact]],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Scorecard de UMA execucao: uma entrada por pergunta da suite, na ordem dela."""
    perguntas = [grade_question(q, transcripts.get(q.id)) for q in suite.questions]
    ids = {q.id for q in suite.questions}
    modelos: set[str] = set()
    versoes: set[str] = set()
    for qid, facts in transcripts.items():
        if qid not in ids:
            continue
        for f in _of(facts, "host.transcript"):
            modelos.update(str(m) for m in f.attrs.get("models") or [])
            versoes.update(str(v) for v in f.attrs.get("host_versions") or [])
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": {"id": suite.id, "sha256": suite.sha256},
        "run": {"id": run_id, "models": sorted(modelos), "host_versions": sorted(versoes)},
        "questions": perguntas,
        "unmatched_transcripts": sorted(qid for qid in transcripts if qid not in ids),
        "totals": _totals(suite, perguntas),
    }
