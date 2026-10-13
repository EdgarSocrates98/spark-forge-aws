"""Chave estavel de um subject, para a obrigacao de resolucao.

Comparar o subject inteiro entre antes e depois daria resolucao falsa: `line`,
`col`, `snippet`, `stage_id`, `job_run_id` e `event` mudam sem que o problema
tenha sido resolvido. A chave usa so os campos que a politica declara por tipo,
e devolve `None` quando o tipo nao tem chave ou quando um campo da chave falta
-- a resolucao entao sai `inconclusive`, em vez de comparar menos do que diz.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def stable_key(
    subject: Mapping[str, Any], stable_keys: Mapping[str, list[str]]
) -> dict[str, Any] | None:
    tipo = str(subject.get("type") or "")
    campos = stable_keys.get(tipo)
    if not campos or any(subject.get(campo) in (None, "") for campo in campos):
        return None
    return {"type": tipo, **{campo: subject[campo] for campo in campos}}
