"""Guarda de versao do catalogo.

Regra fora do range nao dispara. Falha fechada: versao nao detectada significa
nao aplicar, porque aplicar limiar de versao errada invalida a recomendacao.
"""
from __future__ import annotations

_OPERATORS = (">=", "<=", ">", "<", "==")


def _parse(version: str) -> tuple[int, ...]:
    # So os digitos iniciais de cada segmento contam. Um build tag tipo
    # "3.5.4-amzn-0" nao pode virar (3, 5, 40): concatenar todos os digitos
    # do segmento ("4" + "0") produz um numero maior que o real e inverte
    # uma comparacao >=, que e exatamente o defeito que a guarda existe
    # para prevenir.
    parts = []
    for chunk in str(version).split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _compare(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    size = max(len(left), len(right))
    padded_left = left + (0,) * (size - len(left))
    padded_right = right + (0,) * (size - len(right))
    if padded_left < padded_right:
        return -1
    return 1 if padded_left > padded_right else 0


def in_scope(scope: dict[str, str], runtime: dict[str, str]) -> bool:
    """True se todas as restricoes de `scope` casam com `runtime`."""
    for key, raw_spec in (scope or {}).items():
        spec = str(raw_spec).strip()
        if spec == "*":
            continue

        actual = runtime.get(key)
        if not actual:
            return False

        found = None
        for candidate in _OPERATORS:
            if spec.startswith(candidate):
                found = candidate
                break

        target = spec[len(found) :].strip() if found else spec
        if not target or not target[0].isdigit():
            raise ValueError(f"runtime_scope invalido para {key}: {spec!r}")

        result = _compare(_parse(actual), _parse(target))
        op = found or "=="

        if op == ">=" and result < 0:
            return False
        if op == "<=" and result > 0:
            return False
        if op == ">" and result <= 0:
            return False
        if op == "<" and result >= 0:
            return False
        if op == "==" and result != 0:
            return False

    return True
