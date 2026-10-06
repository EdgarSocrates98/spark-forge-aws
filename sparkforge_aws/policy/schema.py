"""Schema da policy, e a validacao que o hook consegue pagar.

`SCHEMA` e o JSON Schema formal (documentacao e teste de concordancia).
`validar()` confere as mesmas regras sem importar `jsonschema`, que custa
0,139 s de import (medido 2026-09-13) -- e o hook roda em todo Bash.
"""
from __future__ import annotations

from typing import Any

CLASSES = ("READ_ONLY", "LOCAL_MUTATION", "CLOUD_READ", "CLOUD_MUTATION", "DESTRUCTIVE")
DECISOES = ("ask", "deny")
_CHAVES = {"version", "tools", "extra_roots", "bash", "paths"}
_CHAVES_TOOLS = {"denied", "approvals", "ask"}
_CHAVES_ASK = {"classes", "names"}
_CHAVES_REGRA = {"rule", "decision", "reason"}

_REGRA = {
    "type": "object",
    "required": ["rule", "decision"],
    "additionalProperties": False,
    "properties": {
        "rule": {"type": "string", "minLength": 1},
        "decision": {"enum": list(DECISOES)},
        "reason": {"type": "string"},
    },
}
_TEXTOS = {"type": "array", "items": {"type": "string"}}
_CLASSES = {"type": "array", "items": {"enum": list(CLASSES)}}
SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["version"],
    "additionalProperties": False,
    "properties": {
        "version": {"const": 1},
        "tools": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "denied": _TEXTOS,
                "approvals": _CLASSES,
                "ask": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"classes": _CLASSES, "names": _TEXTOS},
                },
            },
        },
        "extra_roots": _TEXTOS,
        "bash": {"type": "array", "items": _REGRA},
        "paths": {"type": "array", "items": _REGRA},
    },
}


def _mapa(valor: Any, onde: str, permitidas: set[str], erros: list[str]) -> dict[str, Any]:
    if valor is None:
        return {}
    if not isinstance(valor, dict):
        erros.append(f"{onde} precisa ser um mapa")
        return {}
    extras = sorted(set(valor) - permitidas)
    if extras:
        erros.append(f"{onde}: chaves desconhecidas {extras}")
    return valor


def _textos(valor: Any, onde: str, erros: list[str]) -> list[str]:
    if valor is None:
        return []
    if not isinstance(valor, list) or not all(isinstance(v, str) for v in valor):
        erros.append(f"{onde} precisa ser uma lista de textos")
        return []
    return valor


def _classes(valor: Any, onde: str, erros: list[str]) -> None:
    for classe in _textos(valor, onde, erros):
        if classe not in CLASSES:
            erros.append(f"{onde}: classe desconhecida {classe!r} (use {', '.join(CLASSES)})")


def _regras(valor: Any, onde: str, erros: list[str]) -> None:
    if valor is None:
        return
    if not isinstance(valor, list):
        erros.append(f"{onde} precisa ser uma lista de regras")
        return
    for i, regra in enumerate(valor):
        aqui = f"{onde}[{i}]"
        if not isinstance(regra, dict):
            erros.append(f"{aqui} precisa ser um mapa")
            continue
        extras = sorted(set(regra) - _CHAVES_REGRA)
        if extras:
            erros.append(f"{aqui}: chaves desconhecidas {extras}")
        if not isinstance(regra.get("rule"), str) or not regra.get("rule"):
            erros.append(f"{aqui}.rule precisa ser texto nao vazio")
        if regra.get("decision") not in DECISOES:
            erros.append(f"{aqui}.decision precisa ser ask ou deny, veio {regra.get('decision')!r}")
        if "reason" in regra and not isinstance(regra["reason"], str):
            erros.append(f"{aqui}.reason precisa ser texto")


def validar(dados: Any) -> list[str]:
    """Os erros de schema, em ordem estavel; lista vazia quando valida."""
    erros: list[str] = []
    if not isinstance(dados, dict):
        return ["a policy precisa ser um mapa YAML"]
    extras = sorted(set(dados) - _CHAVES)
    if extras:
        erros.append(f"chaves desconhecidas {extras}")
    if dados.get("version") != 1:
        erros.append(f"version precisa ser 1, veio {dados.get('version')!r}")
    tools = _mapa(dados.get("tools"), "tools", _CHAVES_TOOLS, erros)
    _textos(tools.get("denied"), "tools.denied", erros)
    _classes(tools.get("approvals"), "tools.approvals", erros)
    ask = _mapa(tools.get("ask"), "tools.ask", _CHAVES_ASK, erros)
    _classes(ask.get("classes"), "tools.ask.classes", erros)
    _textos(ask.get("names"), "tools.ask.names", erros)
    _textos(dados.get("extra_roots"), "extra_roots", erros)
    _regras(dados.get("bash"), "bash", erros)
    _regras(dados.get("paths"), "paths", erros)
    return erros
