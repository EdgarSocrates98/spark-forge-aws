"""Deteccao de runtime a partir de multiplas fontes.

Divergencia entre fontes NAO e resolvida escolhendo uma: e registrada, e gera
SF-ENV-001 em P0. Aplicar limiar ou API da versao errada invalida qualquer
recomendacao seguinte.

A matriz espelha knowledge/glue/runtime-matrix.md.

`glue_version` e lido de cada fonte apenas para derivar spark/python/iceberg
via GLUE_MATRIX -- ele proprio nao vira um fact `env.runtime_signal`, so
popula `RuntimeContext.glue` e `detected_from`. Os componentes rastreados
como sinal (e portanto candidatos a fact e a SF-ENV-001) sao spark, python,
iceberg e athena. `spark` e sempre emitido quando ha qualquer observacao,
porque SF-ENV-004 depende dele mesmo sem divergencia; python/iceberg/athena
so geram fact quando ha leitura direta (nao so inferida da matriz) ou quando
divergem -- um unico valor inferido da matriz, sem mais nenhuma fonte, nao
e informacao nova o suficiente para merecer fact proprio.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sparkforge.findings.models import Fact, RuntimeContext, sort_facts

DETECTOR_ID = "runtime_detect@0.1.0"

# Vocabulario fechado de kinds, como nos demais extratores. Serve de fonte
# unica para `tests/test_rules_catalog_reachability.py`: uma regra que exija um
# kind fora da uniao de todos os EMITTED_KINDS e inalcancavel e precisa declarar
# `blocked_on`, em vez de aparecer como "faltou coletar".
EMITTED_KINDS = frozenset({"env.runtime_signal"})

GLUE_MATRIX: dict[str, dict[str, str]] = {
    "5.1": {"spark": "3.5.6", "python": "3.11", "iceberg": "1.10.0"},
    "5.0": {"spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"},
    "4.0": {"spark": "3.3.0", "python": "3.10", "iceberg": "1.0.0"},
    "3.0": {"spark": "3.1.1", "python": "3.7", "iceberg": "0.13.1"},
}

# Precedencia de resolucao quando ha mais de uma fonte para o mesmo
# componente: event_log (Spark UI / event log do run) e o mais confiavel,
# depois terraform (glue_version, --datalake-formats), depois requirements
# (intencao do projeto, nao runtime observado). Ver
# knowledge/glue/runtime-matrix.md secao 5.
_PRECEDENCE: tuple[str, ...] = ("event_log", "terraform", "requirements")

_DIRECT_KEYS: dict[str, tuple[str, ...]] = {
    "spark": ("spark_version", "spark"),
    "python": ("python_version", "python"),
    "iceberg": ("iceberg_version", "iceberg"),
    "athena": ("athena_version", "athena"),
}

_ALWAYS_EMIT = frozenset({"spark"})

# (valor, origem). origem e o nome da fonte, ou "<fonte>:matrix" quando o
# valor foi inferido de GLUE_MATRIX em vez de lido diretamente.
_Observation = tuple[str, str]


def _source_rank(origin: str) -> tuple[int, str]:
    source = origin.split(":", 1)[0]
    if source in _PRECEDENCE:
        return (_PRECEDENCE.index(source), source)
    return (len(_PRECEDENCE), source)


def _resolve(observations: list[_Observation]) -> str:
    """Valor reportado: observado diretamente vence inferido da matriz;
    empate quebrado pela precedencia de fonte."""
    if not observations:
        return ""
    direct = [pair for pair in observations if not pair[1].endswith(":matrix")]
    candidates = direct or observations
    return sorted(candidates, key=lambda pair: _source_rank(pair[1]))[0][0]


def _distinct_values(observations: list[_Observation]) -> list[str]:
    return sorted({value for value, _ in observations})


def _divergence_text(component: str, observations: list[_Observation]) -> str:
    detail = ", ".join(
        f"{origin}={value}" for value, origin in sorted(observations, key=lambda pair: pair[1])
    )
    return f"{component}: valores divergentes entre fontes ({detail})"


def _spark_minor(version: str) -> float | None:
    """'3.5.4' -> 3.5. Usado por SF-ENV-004 (attrs.spark_minor < 3.2)."""
    parts = version.split(".")
    if len(parts) < 2:
        return None
    digits: list[str] = []
    for part in parts[:2]:
        chunk = ""
        for char in part:
            if not char.isdigit():
                break
            chunk += char
        if not chunk:
            return None
        digits.append(chunk)
    return float(f"{digits[0]}.{digits[1]}")


def _collect(
    sources: dict[str, dict[str, Any]],
) -> tuple[list[_Observation], dict[str, list[_Observation]], set[str]]:
    glue_observations: list[_Observation] = []
    observations: dict[str, list[_Observation]] = defaultdict(list)
    detected_from: set[str] = set()

    for source_name in sorted(sources):
        data = sources[source_name]
        if not isinstance(data, dict):
            continue

        glue_version = data.get("glue_version")
        if glue_version:
            glue_str = str(glue_version)
            glue_observations.append((glue_str, source_name))
            detected_from.add(source_name)
            derived = GLUE_MATRIX.get(glue_str)
            if derived:
                origin = f"{source_name}:matrix"
                for component, value in derived.items():
                    observations[component].append((value, origin))

        for component, keys in _DIRECT_KEYS.items():
            for key in keys:
                value = data.get(key)
                if value:
                    observations[component].append((str(value), source_name))
                    detected_from.add(source_name)
                    break

    return glue_observations, observations, detected_from


def _build_context(
    glue_observations: list[_Observation],
    observations: dict[str, list[_Observation]],
    detected_from: set[str],
) -> RuntimeContext:
    all_components: dict[str, list[_Observation]] = {"glue": glue_observations}
    all_components.update(observations)

    divergences = [
        _divergence_text(name, all_components[name])
        for name in sorted(all_components)
        if len(_distinct_values(all_components[name])) > 1
    ]

    return RuntimeContext(
        glue=_resolve(glue_observations),
        spark=_resolve(observations.get("spark", [])),
        python=_resolve(observations.get("python", [])),
        iceberg=_resolve(observations.get("iceberg", [])),
        athena=_resolve(observations.get("athena", [])),
        detected_from=sorted(detected_from),
        divergences=divergences,
    )


def _build_facts(observations: dict[str, list[_Observation]]) -> list[Fact]:
    facts: list[Fact] = []

    for component in sorted(observations):
        obs = observations[component]
        distinct = _distinct_values(obs)
        has_direct = any(not origin.endswith(":matrix") for _, origin in obs)
        if component not in _ALWAYS_EMIT and not has_direct and len(distinct) <= 1:
            continue

        resolved = _resolve(obs)
        source_count = len({origin.split(":", 1)[0] for _, origin in obs})
        measures = {"distinct_versions": len(distinct), "source_count": source_count}
        attrs: dict[str, Any] = {
            "component": component,
            "resolved": resolved,
            "observed": distinct,
            "source": "resolved",
        }
        if component == "spark" and resolved:
            minor = _spark_minor(resolved)
            if minor is not None:
                attrs["spark_minor"] = minor

        facts.append(
            Fact(
                kind="env.runtime_signal",
                subject={"type": "job_run", "symbol": component},
                measures=measures,
                attrs=attrs,
                provenance={"extractor": DETECTOR_ID},
            )
        )

    return facts


def detect_runtime(sources: dict[str, dict[str, Any]]) -> tuple[RuntimeContext, list[Fact]]:
    """Deriva RuntimeContext e Facts `env.runtime_signal` a partir de `sources`.

    `sources` mapeia nome da fonte (ex.: "event_log", "terraform",
    "requirements") para um dict com chaves cruas: `glue_version`,
    `spark_version`/`spark`, `python_version`/`python`,
    `iceberg_version`/`iceberg`, `athena_version`/`athena`.

    Nao le nada do disco nem de rede -- `sources` ja vem coletado
    (coleta e Task 22). Entrada vazia ou com valores None/vazios nao
    levanta excecao: apenas produz um RuntimeContext vazio e nenhum fact.
    """
    glue_observations, observations, detected_from = _collect(sources or {})
    context = _build_context(glue_observations, observations, detected_from)
    facts = _build_facts(observations)
    return context, sort_facts(facts)
