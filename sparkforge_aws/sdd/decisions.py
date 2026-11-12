"""A arvore de decisoes do explore: `forge/DecisionTree/v1`.

A entrevista do `sdd-explore` pode gravar `docs/sdd/<FEATURE>/decisions.json`
(declarado em `decisions_ref` do explore). Cada decisao tem id, pergunta,
tipo, dependencias, estado, alternativas com recomendacao, evidencia, resposta,
ator, impacto e condicao de reabertura -- o contrato inteiro da Onda 4, sem
engine: o arquivo e JSON, a validacao e deterministica e quem decide e sempre
o operador. Decisao aberta e lacuna (`decision_open`), nunca recusa.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_ID = "forge/DecisionTree/v1"

ALTERNATIVA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "label"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "label": {"type": "string", "minLength": 1},
        "recommendation": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
}

DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "feature", "decisions"],
    "properties": {
        "schema": {"const": SCHEMA_ID},
        "feature": {"type": "string", "pattern": "^[A-Z0-9_]+$"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "question", "type", "status"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "question": {"type": "string", "minLength": 1},
                    "type": {"enum": ["human", "investigable", "technical"]},
                    "depends_on": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "status": {
                        "enum": ["open", "pending-approval", "decided", "rejected", "reopened"]
                    },
                    "alternatives": {"type": "array", "items": ALTERNATIVA_SCHEMA},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": ["string", "null"]},
                    "actor": {"type": "string"},
                    "impact": {"type": "string"},
                    "reopen_condition": {"type": "string"},
                },
            },
        },
    },
}

# estados em que a decisao ainda nao tem resposta do operador
ABERTAS = ("open", "pending-approval", "reopened")
# estados terminais: `decided` tem resposta, `rejected` nao sera decidida
TERMINAIS = ("decided", "rejected")


@dataclass(frozen=True)
class Finding:
    """Um problema da arvore; `kind` e traduzido para o codigo do contrato no gate."""

    kind: str  # invalid | dep_unknown | cycle | contradicts | open
    decision: str | None
    detail: str


def load_decisions(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """(arvore, erro). O erro e texto legivel, nunca excecao."""
    try:
        texto = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None, "arquivo nao e UTF-8"
    except OSError:
        return None, "arquivo ilegivel"
    try:
        dado = json.loads(texto)
    except ValueError as exc:
        return None, f"JSON invalido: {exc}"
    if not isinstance(dado, dict):
        return None, "o arquivo precisa ser um objeto JSON"
    return dado, None


def _ciclos(por_id: dict[str, dict[str, Any]]) -> set[str]:
    """Os ids presos em ciclo de `depends_on` (DFS com pilha, iterativo)."""
    em_ciclo: set[str] = set()
    for origem in por_id:
        pilha = [origem]
        vistos: set[str] = set()
        while pilha:
            atual = pilha.pop()
            if atual in vistos:
                continue
            vistos.add(atual)
            for dep in por_id.get(atual, {}).get("depends_on") or []:
                if dep == origem:
                    em_ciclo.add(origem)
                elif dep in por_id:
                    pilha.append(dep)
    return em_ciclo


def validate_decisions(
    tree: dict[str, Any], feature: str | None = None
) -> list[Finding]:
    """Os problemas da arvore, na ordem deterministica em que aparecem.

    Estrutura (schema, id duplicado, `decided` sem `answer`, `answer` fora das
    alternativas, feature de outro dono) e dependencia desconhecida viram
    `invalid`/`dep_unknown`; ciclo e decisao tomada sobre premissa rejeitada
    viram `cycle`/`contradicts`; o que ainda espera o operador vira `open`.
    """
    achados: list[Finding] = []
    erros = sorted(
        Draft202012Validator(DECISION_SCHEMA).iter_errors(tree),
        key=lambda erro: [str(parte) for parte in erro.absolute_path],
    )
    for erro in erros:
        campo = "/".join(str(parte) for parte in erro.absolute_path)
        achados.append(
            Finding("invalid", None, f"{campo}: {erro.message}" if campo else erro.message)
        )
    if erros:
        return achados
    if feature is not None and tree["feature"] != feature:
        achados.append(Finding(
            "invalid", None,
            f"a arvore declara feature {tree['feature']} e mora na feature {feature}",
        ))
    por_id: dict[str, dict[str, Any]] = {}
    for decisao in tree["decisions"]:
        ident = decisao["id"]
        if ident in por_id:
            achados.append(Finding("invalid", ident, f"id {ident} duplicado na arvore"))
            continue
        por_id[ident] = decisao
    for decisao in tree["decisions"]:
        ident = decisao["id"]
        status = decisao["status"]
        alternativas = {a["id"] for a in decisao.get("alternatives") or []}
        if status == "decided" and not decisao.get("answer"):
            achados.append(Finding(
                "invalid", ident,
                f"{ident} esta decided sem answer; responda ou reabra",
            ))
        resposta = decisao.get("answer")
        if resposta and alternativas and resposta not in alternativas:
            achados.append(Finding(
                "invalid", ident,
                f"answer {resposta} nao e uma das alternativas de {ident}",
            ))
        for dep in decisao.get("depends_on") or []:
            if dep not in por_id:
                achados.append(Finding(
                    "dep_unknown", ident,
                    f"{ident} depende de {dep}, que nao existe na arvore",
                ))
            elif status == "decided" and por_id[dep]["status"] == "rejected":
                achados.append(Finding(
                    "contradicts", ident,
                    f"{ident} esta decided mas depende de {dep}, que foi rejeitada; "
                    "a premissa da resposta caiu",
                ))
        if status in ABERTAS:
            achados.append(Finding(
                "open", ident,
                f"{ident} esta {status}; quem decide e o operador",
            ))
    for ident in sorted(_ciclos(por_id)):
        achados.append(Finding(
            "cycle", ident,
            f"{ident} esta num ciclo de depends_on; corte a dependencia que fecha o laco",
        ))
    return achados


def next_open(tree: dict[str, Any]) -> list[str]:
    """As decisoes abertas em ordem topologica: primeiro quem nao espera ninguem.

    Decisao `decided`/`rejected` nao segura ninguem. Ciclo nao derruba: os ids
    de fora do ciclo saem na ordem, e os do ciclo entram no fim, ordenados.
    """
    por_id = {d["id"]: d for d in tree.get("decisions") or [] if isinstance(d, dict)}
    abertas = {i for i, d in por_id.items() if d.get("status") in ABERTAS}
    em_ciclo = _ciclos(por_id)
    ordem: list[str] = []
    vistos: set[str] = set()

    def visita(ident: str) -> None:
        if ident in vistos:
            return
        vistos.add(ident)
        for dep in sorted(por_id.get(ident, {}).get("depends_on") or []):
            if dep in abertas and dep not in em_ciclo:
                visita(dep)
        if ident in abertas:
            ordem.append(ident)

    for ident in sorted(abertas - em_ciclo):
        visita(ident)
    ordem.extend(sorted(abertas & em_ciclo))
    return ordem


def reopen(tree: dict[str, Any], decision_id: str) -> dict[str, Any]:
    """Copia da arvore com `decision_id` em `reopened`; a resposta fica registrada.

    Funcao pura: quem chama decide se grava (`dump_decisions`). Reabrir uma
    decisao que dependem dela nao propaga aqui -- a validacao acusa os
    `contradicts` na proxima passada.
    """
    nova = {**tree, "decisions": [dict(d) for d in tree.get("decisions") or []]}
    for decisao in nova["decisions"]:
        if decisao.get("id") == decision_id and decisao.get("status") not in ("rejected",):
            decisao["status"] = "reopened"
    return nova


def dump_decisions(tree: dict[str, Any]) -> str:
    """Serializacao canonica da arvore (mesma forma para todos os escritores)."""
    return json.dumps(tree, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
