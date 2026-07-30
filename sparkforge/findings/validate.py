"""Validacao de saida contra JSON Schema.

Gate de saida, rigido. Nao trava investigacao; trava alucinacao. A regra que
mais importa nao e expressavel em JSON Schema puro: efeito quantificado sem
benchmark_ref e rejeitado por _reject_unbacked_gain.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# "40%", "40 %", "2x", "2 vezes" -- numero seguido de unidade de ganho.
# Lookbehind negativo evita casar o "2x" embutido em "v2x" (ex.: caminho
# s3://bucket/v2x/) ou em qualquer token alfanumerico -- o digito precisa
# comecar isolado, nao ser sufixo de uma palavra.
_QUANTIFIED = re.compile(
    r"(?<![a-zA-Z0-9_])\d+(?:[.,]\d+)?\s*(?:%|x\b|vezes\b)", re.IGNORECASE
)


class ValidationFailed(ValueError):
    """Payload rejeitado pelo schema ou pela regra de ganho sem benchmark."""


@lru_cache(maxsize=8)
def _schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    if not path.is_file():
        raise ValidationFailed(f"schema ausente: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _check(payload: dict[str, Any], schema_name: str) -> None:
    try:
        jsonschema.validate(payload, _schema(schema_name))
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "<raiz>"
        raise ValidationFailed(f"{location}: {exc.message}") from exc


def validate_fact(payload: dict[str, Any]) -> None:
    _check(payload, "fact.schema.json")


def _reject_unbacked_gain(payload: dict[str, Any]) -> None:
    effect = payload.get("expected_effect") or ""
    if not effect:
        return
    if not _QUANTIFIED.search(effect):
        return
    if payload.get("benchmark_ref"):
        return
    raise ValidationFailed(
        f"expected_effect quantifica ganho ({effect!r}) sem benchmark_ref. "
        "Ganho previsto sem benchmark e invencao."
    )


def validate_finding(payload: dict[str, Any]) -> None:
    _check(payload, "finding.schema.json")
    _reject_unbacked_gain(payload)
