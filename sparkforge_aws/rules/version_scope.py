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


def _specs(raw_spec: object) -> list[str]:
    """Uma chave de `runtime_scope` aceita UM spec ou uma LISTA deles, e a lista
    conjuga (`and`), como as chaves entre si.

    Existe porque uma faixa de UM minor -- "Spark 3.3.x, e so ele" -- nao e
    expressavel com um spec. `"==3.3"` compara segmento a segmento com padding
    (`_compare`), entao casa `3.3.0` e reprova `3.3.1` e `3.3.2`; escrever
    `">=3.3"` sozinho estenderia a regra a 3.4 e 3.5, onde a afirmacao e falsa.
    A alternativa seria enumerar release por release -- e ai a regra envelhece a
    cada release nova da nuvem, que e exatamente o que `runtime_scope` por
    VERSAO existe para evitar.

    O primeiro consumidor e SF-GRAPH-002 (`{spark: [">=3.3", "<3.4"]}`): nenhuma
    linhagem de GraphFrames publicou artefato para Spark 3.3, e 3.2 e 3.4 tem.

    LISTA VAZIA E ERRO, e nao "sem restricao". Uma chave que nao restringe nada
    passaria VACUAMENTE -- a regra parece guardada, o relatorio mostra um
    `runtime_scope` no achado, e o guarda nunca filtrou nada. E exatamente o modo
    de falha do curinga que a Fase 5a levou 20 regras para descobrir. Quem quer
    "sem restricao" escreve `runtime_scope: {}` e nao declara a chave.
    """
    if isinstance(raw_spec, (list, tuple)):
        if not raw_spec:
            raise ValueError(
                "runtime_scope com lista vazia nao restringe nada e passaria "
                "vacuamente; use `runtime_scope: {}` ou omita a chave"
            )
        return [str(item).strip() for item in raw_spec]
    return [str(raw_spec).strip()]


def in_scope(scope: dict[str, object], runtime: dict[str, str]) -> bool:
    """True se todas as restricoes de `scope` casam com `runtime`."""
    for key, raw_spec in (scope or {}).items():
        for spec in _specs(raw_spec):
            if not _one_matches(key, spec, runtime):
                return False
    return True


def _one_matches(key: str, spec: str, runtime: dict[str, str]) -> bool:
    """Um unico spec (`">=3.3"`, `"*"`, `"3.5.4"`) contra o runtime detectado."""
    if spec == "*":
        # `"*"` e "qualquer VERSAO deste componente", nao "qualquer runtime":
        # a chave precisa estar presente. Antes desta fase o ramo pulava a
        # checagem inteira e o curinga nunca filtrava nada -- foi essa
        # ambiguidade que fez 20 regras agnosticas serem etiquetadas como de
        # Glue, e as 5 de infra Glue avaliarem em silencio num job EMR.
        return bool(runtime.get(key))

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

    if op == ">=":
        return result >= 0
    if op == "<=":
        return result <= 0
    if op == ">":
        return result > 0
    if op == "<":
        return result < 0
    return result == 0
