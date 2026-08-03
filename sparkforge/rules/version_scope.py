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
    #
    # E a leitura PARA no primeiro segmento que carrega sufixo de vendor. Sem
    # isso, a forma de dois niveis que so existe em EMR 6.x --
    # "3.3.2-amzn-0.1", em emr-6.11.1, 6.10.1, 6.9.1 e 6.8.1 -- era partida em
    # ["3", "3", "2-amzn-0", "1"] e virava (3, 3, 2, 1): MAIOR que (3, 3, 2),
    # com "==3.3.2" e "<=3.3.2" falsos. Quatro releases inteiras tinham toda
    # regra de range exato pulada em silencio, que e a perda de cobertura muda
    # que as Fases 5a e 5a.2 fecharam. A versao Apache termina onde o sufixo
    # comeca; o que vem depois e numero de patch da AWS, nao segmento de versao.
    parts = []
    for chunk in str(version).split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        parts.append(int(digits) if digits else 0)
        if digits != chunk:
            break
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
            # `"*"` e "qualquer VERSAO deste componente", nao "qualquer runtime":
            # a chave precisa estar presente. Antes desta fase o ramo pulava a
            # checagem inteira e o curinga nunca filtrava nada -- foi essa
            # ambiguidade que fez 20 regras agnosticas serem etiquetadas como de
            # Glue, e as 5 de infra Glue avaliarem em silencio num job EMR.
            if not runtime.get(key):
                return False
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
