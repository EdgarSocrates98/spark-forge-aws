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

PLATAFORMA E OUTRA PERGUNTA, e por isso tem fact proprio.
`env.runtime_signal` responde "quais versoes?", e SF-ENV-001 conta
`distinct_versions`. Glue e EMR detectados juntos podem derivar exatamente a
mesma versao de Spark -- Glue 4.0 deriva 3.3.0, e ha release de EMR que roda
3.3.0 --, e nesse caso nao ha divergencia de versao alguma: a dupla deteccao
passava muda (spec da Fase 5, secao 3.3). A pergunta certa e "quantas
PLATAFORMAS?", que e identidade e nao versao, e nenhum ajuste em SF-ENV-001
alcanca isso. Dai `env.platform`, com `measures.distinct_platforms`, e
SF-ENV-005 sobre ele.

`env.platform` e emitido sempre que ha ao menos UMA plataforma observada, e
nao so quando ha duas. Com uma, a regra e AVALIADA e explicitamente nao
dispara; sem o fact, ela sumiria por `requires_facts` -- ausencia muda, que
para um agente autonomo le como "nada encontrado". E a mesma razao de
`_ALWAYS_EMIT` conter `spark`. Zero plataformas observadas continua sem fact:
ai nao ha identidade nenhuma para afirmar.
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
EMITTED_KINDS = frozenset({"env.runtime_signal", "env.platform"})

GLUE_MATRIX: dict[str, dict[str, str]] = {
    "5.1": {"spark": "3.5.6", "python": "3.11", "iceberg": "1.10.0"},
    "5.0": {"spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"},
    "4.0": {"spark": "3.3.0", "python": "3.10", "iceberg": "1.0.0"},
    "3.0": {"spark": "3.1.1", "python": "3.7", "iceberg": "0.13.1"},
}

# Precedencia de resolucao quando ha mais de uma fonte para o mesmo
# componente: event_log (Spark UI / event log do run) e o mais confiavel,
# depois cli (a flag que o operador digitou), depois terraform (glue_version,
# --datalake-formats), depois requirements (intencao do projeto, nao runtime
# observado). Ver knowledge/glue/runtime-matrix.md secao 5.
#
# `cli` estava FORA desta tupla e caia por ultimo por acidente de
# implementacao -- `_source_rank` empurra qualquer origem desconhecida para o
# fim --, nao por decisao. Declarada agora, e declarada ABAIXO de `event_log`:
# o event log e a unica fonte que OBSERVOU o runtime do run sob analise, com
# artefato, provenance e sha256; a flag e uma declaracao sem artefato. Quando o
# run reporta 3.5.4 e alguem digitou 3.3.0, quem sabe de si e o run. Acima de
# `terraform`/`requirements`, porem, porque esses tambem sao declaracao (a
# intencao registrada no repositorio) e a flag e a declaracao mais especifica e
# mais recente -- o operador pode saber de uma mudanca aplicada no console que
# o IaC ainda nao reflete.
#
# Isto NAO e resolucao silenciosa, e nao pode virar. Perder a precedencia nunca
# apaga a observacao: todo valor lido continua entrando em `observations`, e
# qualquer discordancia continua virando `divergences` no RuntimeContext e um
# fact `env.runtime_signal` com `observed` completo -- o gatilho de SF-ENV-001
# em P0. A precedencia so escolhe o que o contexto REPORTA como valor
# resolvido; ela nao decide quem esta certo, e nunca descarta o outro valor.
_PRECEDENCE: tuple[str, ...] = ("event_log", "cli", "terraform", "requirements")

# Chaves que identificam a PLATAFORMA de execucao em cada fonte, e o valor que
# elas carregam (versao de Glue, release label de EMR). O valor so alimenta
# `RuntimeContext`; a identidade -- a chave do dict -- e o que `env.platform`
# conta. Glue continua sendo lido por `glue_version` e por mais nada, porque a
# mesma leitura alimenta GLUE_MATRIX: platform detectada e versao derivada nao
# podem divergir por lerem chaves diferentes.
_PLATFORM_KEYS: dict[str, tuple[str, ...]] = {
    "emr": ("emr_release", "emr_version", "emr"),
    "glue": ("glue_version",),
}

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


def _platform_identity(platforms: dict[str, list[_Observation]]) -> list[_Observation]:
    """As observacoes de identidade, na forma `(nome_da_plataforma, fonte)`.

    Reusa `_Observation` de proposito: identidade e versao sao perguntas
    diferentes, mas a forma "alguem observou X na fonte Y" e a mesma, e com ela
    `_distinct_values`, `_divergence_text` e `_source_rank` valem sem duplicata.
    """
    return [
        (platform, origin)
        for platform in sorted(platforms)
        for _, origin in sorted(platforms[platform], key=lambda pair: pair[1])
    ]


def _collect(
    sources: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[_Observation]], dict[str, list[_Observation]], set[str]]:
    platforms: dict[str, list[_Observation]] = defaultdict(list)
    observations: dict[str, list[_Observation]] = defaultdict(list)
    detected_from: set[str] = set()

    for source_name in sorted(sources):
        data = sources[source_name]
        if not isinstance(data, dict):
            continue

        for platform, keys in _PLATFORM_KEYS.items():
            for key in keys:
                raw = data.get(key)
                if not raw:
                    continue
                value = str(raw)
                platforms[platform].append((value, source_name))
                detected_from.add(source_name)
                if platform == "glue":
                    derived = GLUE_MATRIX.get(value)
                    if derived:
                        origin = f"{source_name}:matrix"
                        for component, derived_value in derived.items():
                            observations[component].append((derived_value, origin))
                break

        for component, keys in _DIRECT_KEYS.items():
            for key in keys:
                value = data.get(key)
                if value:
                    observations[component].append((str(value), source_name))
                    detected_from.add(source_name)
                    break

    return platforms, observations, detected_from


def _build_context(
    platforms: dict[str, list[_Observation]],
    observations: dict[str, list[_Observation]],
    detected_from: set[str],
) -> RuntimeContext:
    all_components: dict[str, list[_Observation]] = {
        "glue": platforms.get("glue", []),
        "emr": platforms.get("emr", []),
        # Divergencia de IDENTIDADE, ao lado das de versao. `divergences` e o
        # canal que um humano le no relatorio: deixar a plataforma de fora dele
        # reproduziria, no contexto, o mesmo silencio que `env.platform` remove
        # do catalogo. O sinal acionavel continua sendo o fact e SF-ENV-005 --
        # isto aqui e a linha que o operador ve.
        "platform": _platform_identity(platforms),
    }
    all_components.update(observations)

    divergences = [
        _divergence_text(name, all_components[name])
        for name in sorted(all_components)
        if len(_distinct_values(all_components[name])) > 1
    ]

    return RuntimeContext(
        glue=_resolve(platforms.get("glue", [])),
        emr=_resolve(platforms.get("emr", [])),
        spark=_resolve(observations.get("spark", [])),
        python=_resolve(observations.get("python", [])),
        iceberg=_resolve(observations.get("iceberg", [])),
        athena=_resolve(observations.get("athena", [])),
        detected_from=sorted(detected_from),
        divergences=divergences,
    )


def _platform_fact(platforms: dict[str, list[_Observation]]) -> Fact | None:
    """`env.platform`: identidade, nunca versao.

    `measures.distinct_platforms` e a resposta direta a pergunta que SF-ENV-005
    faz -- "quantas plataformas?" -- e por isso a regra e um `expr` de uma
    linha, sem agregacao no motor (que ele nao sabe fazer: `where`/`expr`
    avaliam sempre contra UM fact). Emitir um fact por plataforma exigiria
    contar facts, que nao existe. `source_count` acompanha para separar "duas
    fontes concordando na mesma plataforma" de "duas plataformas" -- o mesmo
    falso positivo que `distinct_versions` versus `source_count` ja evita para
    versao.
    """
    detected = sorted(name for name in platforms if platforms[name])
    if not detected:
        return None

    origins = {
        name: sorted({origin for _, origin in platforms[name]}) for name in detected
    }
    sources = sorted({origin for name in detected for origin in origins[name]})
    resolved = sorted(
        detected, key=lambda name: (min(_source_rank(o) for o in origins[name]), name)
    )[0]

    return Fact(
        kind="env.platform",
        subject={"type": "job_run", "symbol": "platform"},
        measures={"distinct_platforms": len(detected), "source_count": len(sources)},
        attrs={
            "resolved": resolved,
            "observed": detected,
            "source": "resolved",
            "origins": origins,
        },
        provenance={"extractor": DETECTOR_ID},
    )


def _build_facts(
    platforms: dict[str, list[_Observation]],
    observations: dict[str, list[_Observation]],
) -> list[Fact]:
    facts: list[Fact] = []

    platform_fact = _platform_fact(platforms)
    if platform_fact is not None:
        facts.append(platform_fact)

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
    """Deriva RuntimeContext e Facts (`env.platform`, `env.runtime_signal`).

    `sources` mapeia nome da fonte (ex.: "event_log", "terraform",
    "requirements") para um dict com chaves cruas: `glue_version`,
    `emr_release`/`emr_version`/`emr`, `spark_version`/`spark`,
    `python_version`/`python`, `iceberg_version`/`iceberg`,
    `athena_version`/`athena`.

    Nao le nada do disco nem de rede -- `sources` ja vem coletado
    (coleta e Task 22). Entrada vazia ou com valores None/vazios nao
    levanta excecao: apenas produz um RuntimeContext vazio e nenhum fact.
    """
    platforms, observations, detected_from = _collect(sources or {})
    context = _build_context(platforms, observations, detected_from)
    facts = _build_facts(platforms, observations)
    return context, sort_facts(facts)
