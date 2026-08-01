"""Extrator de Facts a partir de um dump JSON ja coletado de um cluster
Amazon EMR on EC2 (`describe-cluster`, `list-instance-groups`,
`list-instance-fleets`, `list-bootstrap-actions`, `get-managed-scaling-policy`,
`get-auto-termination-policy`).

Como `athena_workgroup.py`/`iceberg_metadata.py`, este modulo NAO coleta nada:
a coleta e responsabilidade de `sparkforge.collect.aws.collect_emr_cluster`
(ou de um `aws emr ...` rodado a mao). Este extrator so le o JSON ja salvo em
disco.

## Shape esperado do dump

E a UNIAO das saidas dos seis subcomandos, cada uma sob a chave que o proprio
CLI/boto3 devolve -- PascalCase, sem traducao. A escolha e deliberada: um
operador que rode os seis comandos e junte os objetos num JSO so produz um
artefato que este extrator le sem nenhuma etapa intermediaria, e nao ha camada
de renomeacao para apodrecer quando a API mudar.

```json
{
  "Cluster": {
    "Id": "j-1EXAMPLE",
    "Name": "etl",
    "ReleaseLabel": "emr-7.5.0",
    "Applications": [{"Name": "Spark", "Version": "3.5.2-amzn-1"}],
    "Configurations": [
      {"Classification": "spark-defaults", "Properties": {"spark.executor.cores": "4"}}
    ],
    "LogUri": "s3://bucket/elasticmapreduce/",
    "ScaleDownBehavior": "TERMINATE_AT_TASK_COMPLETION",
    "AutoTerminate": false,
    "InstanceCollectionType": "INSTANCE_GROUP",
    "Status": {"State": "RUNNING", "StateChangeReason": {"Code": "ALL_STEPS_COMPLETED"}},
    "UnhealthyNodeReplacement": true
  },
  "InstanceGroups": [
    {
      "Id": "ig-1", "InstanceGroupType": "TASK", "Market": "SPOT",
      "InstanceType": "r5.xlarge", "RequestedInstanceCount": 4,
      "Configurations": [...], "LastSuccessfullyAppliedConfigurations": [...],
      "ConfigurationsVersion": 3, "AutoScalingPolicy": {...},
      "EbsBlockDevices": [...]
    }
  ],
  "InstanceFleets": [
    {
      "Id": "if-1", "InstanceFleetType": "TASK",
      "TargetSpotCapacity": 8, "TargetOnDemandCapacity": 0,
      "InstanceTypeSpecifications": [{"InstanceType": "r5.xlarge", "Configurations": [...]}],
      "LaunchSpecifications": {"SpotSpecification": {"AllocationStrategy": "capacity-optimized"}}
    }
  ],
  "BootstrapActions": [
    {"Name": "instala", "ScriptBootstrapAction": {"Path": "s3://b/bootstrap.sh", "Args": []}}
  ],
  "ManagedScalingPolicy": {"ComputeLimits": {"UnitType": "InstanceFleetUnits",
                                             "MinimumCapacityUnits": 2,
                                             "MaximumCapacityUnits": 40}},
  "AutoTerminationPolicy": {"IdleTimeout": 3600}
}
```

**Duas formas para a mesma coisa, e as duas sao lidas.** O CLI parece embutir
`InstanceGroups`/`InstanceFleets`/`BootstrapActions` DENTRO de `Cluster`, o que
contradiz `API_Cluster.html`, onde esses campos nao existem -- provavel forma
legada. Este extrator le a embutida quando ela existe e a de nivel raiz quando
nao, sem depender de nenhuma das duas.

## Grupos e fleets viram UM kind, com atributo discriminante

Instance groups e instance fleets sao modelos alternativos e mutuamente
exclusivos, e a mesma pergunta tem forma diferente em cada um: "ha capacidade
Spot neste papel?" e `Market == "SPOT"` no grupo e `TargetSpotCapacity > 0` no
fleet. Normalizar essa diferenca e trabalho de extrator, nao de regra: se
fossem dois kinds, toda regra que pergunta por Spot precisaria ser escrita duas
vezes, e a que alguem esquecesse de duplicar ficaria calada exatamente na
metade dos clusters -- falso negativo por omissao de catalogo, invisivel.
Entao os dois viram `emr.instance_capacity`, com `attrs.collection_type`
dizendo de qual modelo aquele fact veio e `attrs.has_spot_capacity` /
`attrs.has_on_demand_capacity` respondendo a pergunta numa forma so. O que e
especifico de um modelo (`market`, `allocation_strategy`) continua no fact, sem
equivalente inventado no outro.

Dump com NENHUM dos dois e dump incompleto, nao cluster sem instancias: vira
`emr.unresolved` com `reason: missing_instance_model`. Dump com os DOIS
descreve um cluster impossivel (os modelos sao exclusivos) e vira
`conflicting_instance_models` -- os facts dos dois ainda saem, mas a
contradicao fica registrada.

## Os dois niveis de `Configurations`, e por que achatar seria mentira

As classificacoes (`spark-defaults`, `spark`, `yarn-site`, `spark-env`) chegam
por DOIS niveis: `Cluster.Configurations` e
`InstanceGroup.Configurations` / `InstanceTypeSpecification.Configurations`. A
distincao importa porque a propriedade do grupo SOBREPOE a do cluster para
aquele grupo -- achatar os dois num kind sem discriminante faria uma regra
afirmar sobre o cluster inteiro o que so vale para um grupo. Cada
`emr.configuration` carrega portanto `attrs.level`
(`cluster`/`instance_group`/`instance_fleet`) e `attrs.scope` (o id do grupo,
vazio no nivel cluster). Alem disso a sobreposicao e explicitada nos dois
sentidos: o fact de grupo traz `attrs.overrides_cluster` e
`attrs.cluster_value`; o de cluster traz `attrs.overridden_in` (os grupos que
o redefinem) e `measures.overriding_group_count`, para que uma regra sobre uma
propriedade de cluster possa exigir que ela esteja de fato valendo em todo
lugar.

## `emr.configuration.unapplied`: a qualidade da evidencia

`InstanceGroup` traz `Configurations`, `LastSuccessfullyAppliedConfigurations`
e `ConfigurationsVersion`. Divergencia entre os dois primeiros significa
reconfiguracao PEDIDA E NAO APLICADA: o cluster nao esta rodando com o que o
dump aparenta dizer. Toda regra que le `emr.configuration` de um grupo precisa
usar este fact como guarda (`absent:`), senao afirma sobre configuracao que nao
esta em vigor -- mesmo papel de `tf.observability.unknown` e `plan.unresolved`
no resto do projeto. Os facts `emr.configuration` de um grupo continuam vindo
de `Configurations` (o que foi pedido), nunca do que foi aplicado: o dump
descreve a intencao, e o guard e quem diz que ela ainda nao virou realidade.

## Segredo: mesmo mecanismo de `terraform.py`

Valor de propriedade e argumento de bootstrap action passam pelo mesmo teste de
`_looks_like_secret` que `facts/terraform.py` usa para SF-GLUE-006 -- as APIs
Describe/List devolvem esses valores em texto claro para quem tem permissao de
leitura. Quando casa, o valor NUNCA e escrito em `attrs`: vira `<redigido>`,
com `attrs.secret_pattern_match: true`. Um golden commitado com credencial real
seria o analisador causando o dano que a regra existe para prevenir. A funcao e
duplicada, e nao importada de `terraform.py`, pela mesma razao que
`iceberg_metadata._nearest_rank` e duplicada de `event_log`: extratores sao
modulos independentes por desenho.

Como os demais extratores: puro e deterministico. Nunca aplica limiar, nunca
atribui severidade, nunca infere o que o dump nao diz.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "emr_cluster@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "emr.cluster",
        "emr.application",
        "emr.instance_capacity",
        "emr.configuration",
        "emr.configuration.unapplied",
        "emr.bootstrap_action",
        "emr.managed_scaling",
        "emr.unresolved",
        "emr.analyzed",
    }
)

# Vocabulario fechado de papel, identico nos dois modelos de instancia
# (`InstanceGroupType` e `InstanceFleetType` usam as mesmas tres palavras).
# Valor fora daqui nao vira `emr.instance_capacity`: uma regra que pergunta
# "ha Spot no TASK?" precisa saber que o papel foi LIDO, nao adivinhado.
INSTANCE_ROLES = frozenset({"MASTER", "CORE", "TASK"})

# `emr-7.5.0` -> ("7.5.0", 7, 5). O label e o que a API devolve; a release
# numerica e o que `RuntimeContext.emr` guarda (ver
# `facts/runtime_detect._emr_key`) e o que uma regra consegue comparar.
_RELEASE_LABEL_RE = re.compile(r"^emr-(.+)$", re.IGNORECASE)
_RELEASE_NUMBER_RE = re.compile(r"^(\d+)\.(\d+)")

# Mesmos padroes de `facts/terraform.py` (SF-GLUE-006). Ver docstring do modulo
# para por que sao duplicados em vez de importados.
_AKIA_RE = re.compile(r"AKIA[0-9A-Z]{16}")
_URL_PASSWORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:@/]+:[^\s@/]+@")
_HIGH_ENTROPY_RE = re.compile(r"[A-Za-z0-9+/_=-]{20,}")
_SECRET_KEY_HINTS = ("secret", "password", "token", "key")

REDACTED = "<redigido>"


# --------------------------------------------------------------------------- #
# helpers de forma
# --------------------------------------------------------------------------- #


def _file_subject(path: str, line: int = 0) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _entity_subject(symbol: str) -> dict[str, Any]:
    """Subject de uma entidade do cluster.

    `job_run` e o membro do enum de `fact.schema.json` que descreve uma
    entidade de EXECUCAO (nao um ponto de codigo, nao uma tabela) -- o mesmo
    que `athena_workgroup` usa para um workgroup. O `symbol` e a identidade
    hierarquica (`<cluster>/<grupo>/...`), e e o que `same_subject` agrupa.
    """
    return {"type": "job_run", "symbol": symbol}


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _as_bool(value: Any) -> bool | None:
    """`True`/`False` quando o dump traz booleano; `None` quando nao traz nada
    ou traz outra coisa. Nunca um default: `False` inventado num `AutoTerminate`
    ausente mudaria a severidade de uma regra que le esse campo."""
    return value if isinstance(value, bool) else None


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _value_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _looks_like_secret(key: str, value: str) -> bool:
    if _AKIA_RE.search(value):
        return True
    if _URL_PASSWORD_RE.search(value):
        return True
    key_lower = key.lower()
    if any(hint in key_lower for hint in _SECRET_KEY_HINTS) and _HIGH_ENTROPY_RE.fullmatch(value):
        return True
    return False


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="emr.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


class _SymbolPool:
    """Garante `symbol` unico por entidade dentro de um dump.

    `Fact.id` e o hash de (kind, subject, measures): duas propriedades da mesma
    classificacao com o mesmo nome -- dado contraditorio, mas possivel num dump
    com duas entradas de mesma `Classification` -- teriam subject e measures
    identicos e colidiriam num id so, com `attrs` diferentes. Um sufixo `#N`
    deterministico mantem os dois facts distintos e rastreaveis, em vez de um
    sobrescrever o outro em silencio.
    """

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def take(self, symbol: str) -> str:
        count = self._seen.get(symbol, 0)
        self._seen[symbol] = count + 1
        return symbol if count == 0 else f"{symbol}#{count}"


# --------------------------------------------------------------------------- #
# configuracoes: parsing recursivo, sem emitir Fact
# --------------------------------------------------------------------------- #


def _collect_properties(
    entries: Any, trail: tuple[str, ...] = ()
) -> tuple[list[tuple[str, str, str]], list[dict[str, Any]]]:
    """Achata uma lista `Configurations` em `[(classification, key, value)]`.

    Recursivo: a API permite `Configurations` aninhado dentro de uma
    `Configuration`, e a classificacao do filho e a que vale para as
    propriedades dele. Devolve tambem os problemas encontrados, para o chamador
    transformar em `emr.unresolved` -- entrada malformada nunca e ignorada em
    silencio.
    """
    if entries is None:
        return [], []
    if not isinstance(entries, list):
        return [], [{"reason": "malformed_json", "section": "Configurations"}]

    props: list[tuple[str, str, str]] = []
    problems: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append({"reason": "malformed_json", "section": "Configurations[]"})
            continue
        classification = _as_str(entry.get("Classification"))
        if classification is None:
            problems.append({"reason": "missing_classification"})
            continue
        properties = entry.get("Properties")
        if properties is not None and not isinstance(properties, dict):
            problems.append(
                {"reason": "malformed_json", "section": f"{classification}.Properties"}
            )
        elif isinstance(properties, dict):
            for key, value in properties.items():
                if not isinstance(key, str) or not key.strip():
                    problems.append(
                        {"reason": "missing_property_key", "classification": classification}
                    )
                    continue
                props.append((classification, key.strip(), _value_to_str(value)))
        nested_props, nested_problems = _collect_properties(
            entry.get("Configurations"), (*trail, classification)
        )
        props.extend(nested_props)
        problems.extend(nested_problems)
    return props, problems


def _configuration_fact(
    *,
    classification: str,
    key: str,
    value: str,
    level: str,
    scope: str,
    symbol: str,
    extra_attrs: dict[str, Any],
    measures: dict[str, Any],
    provenance: dict[str, Any],
) -> Fact:
    attrs: dict[str, Any] = {
        "level": level,
        "scope": scope,
        "classification": classification,
        "key": key,
        "value": value,
        **extra_attrs,
    }
    if _looks_like_secret(key, value):
        attrs["value"] = REDACTED
        attrs["redacted"] = True
        attrs["secret_pattern_match"] = True
    return Fact(
        kind="emr.configuration",
        subject=_entity_subject(symbol),
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# cluster
# --------------------------------------------------------------------------- #


def _release_numbers(label: str | None) -> tuple[str | None, int | None, int | None]:
    """`emr-7.5.0` -> `("7.5.0", 7, 5)`. Label sem numero legivel -> `(None, ...)`.

    O par (major, minor) sai como measure para que uma regra possa perguntar
    "serie 6.x?" sem depender de a deteccao de runtime ter resolvido -- o
    proprio dump ja prova a release, e uma comparacao de string nao existe no
    avaliador de expressoes do catalogo.
    """
    if label is None:
        return None, None, None
    match = _RELEASE_LABEL_RE.match(label)
    release = match.group(1).strip() if match else label.strip()
    if not release:
        return None, None, None
    numbers = _RELEASE_NUMBER_RE.match(release)
    if numbers is None:
        return release, None, None
    return release, int(numbers.group(1)), int(numbers.group(2))


def _cluster_fact(
    cluster: dict[str, Any],
    cluster_id: str,
    payload: dict[str, Any],
    provenance: dict[str, Any],
) -> Fact:
    label = _as_str(cluster.get("ReleaseLabel"))
    release, major, minor = _release_numbers(label)

    status = cluster.get("Status") if isinstance(cluster.get("Status"), dict) else {}
    raw_reason = status.get("StateChangeReason")
    reason = raw_reason if isinstance(raw_reason, dict) else {}
    log_uri = _as_str(cluster.get("LogUri"))

    attrs: dict[str, Any] = {
        "cluster_id": cluster_id,
        "name": _as_str(cluster.get("Name")),
        "release_label": label,
        "release": release,
        "instance_collection_type": _as_str(cluster.get("InstanceCollectionType")),
        # `log_uri_present` existe porque `where:` do catalogo so compara
        # igualdade: `attrs.log_uri: null` casaria tambem um dump que nao
        # coletou o campo. O booleano diz "o dump respondeu, e a resposta e
        # nao ha destino de log".
        "log_uri": log_uri,
        "log_uri_present": log_uri is not None,
        "scale_down_behavior": _as_str(cluster.get("ScaleDownBehavior")),
        "auto_terminate": _as_bool(cluster.get("AutoTerminate")),
        "unhealthy_node_replacement": _as_bool(cluster.get("UnhealthyNodeReplacement")),
        "state": _as_str(status.get("State")),
        "state_change_reason_code": _as_str(reason.get("Code")),
    }

    measures: dict[str, Any] = {}
    if major is not None:
        measures["release_major"] = major
    if minor is not None:
        measures["release_minor"] = minor

    # `get-auto-termination-policy` e um dump proprio, mas o unico dado que
    # traz (`IdleTimeout`) e uma propriedade do cluster, e nenhuma regra desta
    # fase o consulta sozinho. Kind proprio seria capacidade sem consumidor;
    # vira measure do cluster, ausente quando o dump nao trouxe a secao.
    policy = payload.get("AutoTerminationPolicy")
    if isinstance(policy, dict) and _is_number(policy.get("IdleTimeout")):
        measures["idle_timeout_seconds"] = policy["IdleTimeout"]

    return Fact(
        kind="emr.cluster",
        subject=_entity_subject(cluster_id),
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )


def _application_facts(
    cluster: dict[str, Any], cluster_id: str, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    """Um fact por `Applications[]`, com a versao QUE O CLUSTER REPORTA.

    E o que torna a fonte `describe_cluster` de `runtime_detect._PRECEDENCE`
    alimentavel: a AWS diz qual Spark/Iceberg instalou naquele cluster, o que e
    estritamente melhor que derivar da matriz de release.
    """
    raw = cluster.get("Applications")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return [_unresolved(path, "malformed_json", provenance, section="Applications")]

    facts: list[Fact] = []
    pool = _SymbolPool()
    for entry in raw:
        if not isinstance(entry, dict):
            facts.append(_unresolved(path, "malformed_json", provenance, section="Applications[]"))
            continue
        name = _as_str(entry.get("Name"))
        if name is None:
            facts.append(_unresolved(path, "missing_application_name", provenance))
            continue
        facts.append(
            Fact(
                kind="emr.application",
                subject=_entity_subject(pool.take(f"{cluster_id}/application/{name}")),
                attrs={"name": name, "version": _as_str(entry.get("Version"))},
                provenance=provenance,
            )
        )
    return facts


# --------------------------------------------------------------------------- #
# instancias: grupos e fleets, normalizados no mesmo kind
# --------------------------------------------------------------------------- #


def _instance_group_facts(
    group: dict[str, Any],
    cluster_id: str,
    path: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    group_id = _as_str(group.get("Id"))
    if group_id is None:
        return [_unresolved(path, "missing_instance_group_id", provenance)]

    role = _as_str(group.get("InstanceGroupType"))
    role = role.upper() if role else None
    if role not in INSTANCE_ROLES:
        return [
            _unresolved(
                path, "missing_instance_role", provenance, id=group_id, observed_role=role
            )
        ]

    market = _as_str(group.get("Market"))
    market = market.upper() if market else None
    if market not in ("SPOT", "ON_DEMAND"):
        # Sem `Market` nao ha como responder "ha capacidade Spot neste papel?".
        # Um `has_spot_capacity: false` inventado apagaria em silencio as duas
        # regras que dependem dessa resposta.
        return [
            _unresolved(
                path, "missing_market", provenance, id=group_id, role=role, observed_market=market
            )
        ]

    instance_type = _as_str(group.get("InstanceType"))
    ebs = group.get("EbsBlockDevices")
    measures: dict[str, Any] = {}
    if _is_number(group.get("RequestedInstanceCount")):
        measures["requested_instance_count"] = group["RequestedInstanceCount"]
    if _is_number(group.get("RunningInstanceCount")):
        measures["running_instance_count"] = group["RunningInstanceCount"]
    if isinstance(ebs, list):
        measures["ebs_block_device_count"] = len(ebs)
    if _is_number(group.get("ConfigurationsVersion")):
        measures["configurations_version"] = group["ConfigurationsVersion"]

    attrs = {
        "id": group_id,
        "cluster_id": cluster_id,
        "role": role,
        "collection_type": "INSTANCE_GROUP",
        "market": market,
        "has_spot_capacity": market == "SPOT",
        "has_on_demand_capacity": market == "ON_DEMAND",
        "instance_types": [instance_type] if instance_type else [],
        "has_auto_scaling_policy": isinstance(group.get("AutoScalingPolicy"), dict),
        "allocation_strategy": None,
    }
    return [
        Fact(
            kind="emr.instance_capacity",
            subject=_entity_subject(f"{cluster_id}/{group_id}"),
            measures=measures,
            attrs=attrs,
            provenance=provenance,
        )
    ]


def _instance_fleet_facts(
    fleet: dict[str, Any],
    cluster_id: str,
    path: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    fleet_id = _as_str(fleet.get("Id"))
    if fleet_id is None:
        return [_unresolved(path, "missing_instance_group_id", provenance)]

    role = _as_str(fleet.get("InstanceFleetType"))
    role = role.upper() if role else None
    if role not in INSTANCE_ROLES:
        return [
            _unresolved(
                path, "missing_instance_role", provenance, id=fleet_id, observed_role=role
            )
        ]

    spot = fleet.get("TargetSpotCapacity")
    on_demand = fleet.get("TargetOnDemandCapacity")
    if not (_is_number(spot) and _is_number(on_demand)):
        # As duas capacidades sao a forma que o modelo de fleet tem de
        # responder "ha Spot?" e "ha On-Demand?". Faltando uma, a resposta e
        # desconhecida -- e desconhecido nunca vira `false`.
        return [
            _unresolved(
                path,
                "missing_fleet_capacity",
                provenance,
                id=fleet_id,
                role=role,
            )
        ]

    specs = fleet.get("InstanceTypeSpecifications")
    instance_types = (
        [
            t
            for t in (
                _as_str(spec.get("InstanceType"))
                for spec in specs
                if isinstance(spec, dict)
            )
            if t
        ]
        if isinstance(specs, list)
        else []
    )
    launch = fleet.get("LaunchSpecifications")
    spot_spec = launch.get("SpotSpecification") if isinstance(launch, dict) else None
    allocation = (
        _as_str(spot_spec.get("AllocationStrategy")) if isinstance(spot_spec, dict) else None
    )

    attrs = {
        "id": fleet_id,
        "cluster_id": cluster_id,
        "role": role,
        "collection_type": "INSTANCE_FLEET",
        # Fleet nao tem `Market`: a mesma frota pode ter as duas capacidades ao
        # mesmo tempo, o que nao tem equivalente no modelo de grupo. `None` diz
        # "a pergunta nao se aplica aqui", nunca "nao sei".
        "market": None,
        "has_spot_capacity": spot > 0,
        "has_on_demand_capacity": on_demand > 0,
        "instance_types": instance_types,
        "has_auto_scaling_policy": None,
        "allocation_strategy": allocation,
    }
    measures = {
        "target_spot_capacity": spot,
        "target_on_demand_capacity": on_demand,
    }
    return [
        Fact(
            kind="emr.instance_capacity",
            subject=_entity_subject(f"{cluster_id}/{fleet_id}"),
            measures=measures,
            attrs=attrs,
            provenance=provenance,
        )
    ]


# --------------------------------------------------------------------------- #
# bootstrap actions e managed scaling
# --------------------------------------------------------------------------- #


def _bootstrap_facts(
    entries: Any, cluster_id: str, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        return [_unresolved(path, "malformed_json", provenance, section="BootstrapActions")]

    facts: list[Fact] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            facts.append(
                _unresolved(path, "malformed_json", provenance, section="BootstrapActions[]")
            )
            continue
        name = _as_str(entry.get("Name"))
        if name is None:
            facts.append(_unresolved(path, "missing_bootstrap_name", provenance))
            continue
        script = entry.get("ScriptBootstrapAction")
        script = script if isinstance(script, dict) else {}
        raw_args = script.get("Args")
        args = [_value_to_str(a) for a in raw_args] if isinstance(raw_args, list) else []

        redacted_args: list[str] = []
        matched = False
        for position, arg in enumerate(args):
            # A "chave" de um argumento e a flag anterior (`--password valor`)
            # ou o proprio texto (`--password=valor`): as duas formas aparecem
            # em bootstrap script, e olhar so uma perderia metade dos casos.
            hint = args[position - 1] if position > 0 else arg
            if _looks_like_secret(hint, arg) or _looks_like_secret(arg, arg):
                matched = True
                redacted_args.append(REDACTED)
            else:
                redacted_args.append(arg)

        attrs: dict[str, Any] = {
            "name": name,
            "path": _as_str(script.get("Path")),
            "args": redacted_args,
        }
        if matched:
            attrs["redacted"] = True
            attrs["secret_pattern_match"] = True
        facts.append(
            Fact(
                kind="emr.bootstrap_action",
                subject=_entity_subject(f"{cluster_id}/bootstrap/{index}/{name}"),
                measures={"arg_count": len(args), "position": index},
                attrs=attrs,
                provenance=provenance,
            )
        )
    return facts


_COMPUTE_LIMIT_MEASURES = (
    ("MinimumCapacityUnits", "minimum_capacity_units"),
    ("MaximumCapacityUnits", "maximum_capacity_units"),
    ("MaximumOnDemandCapacityUnits", "maximum_on_demand_capacity_units"),
    ("MaximumCoreCapacityUnits", "maximum_core_capacity_units"),
)


def _managed_scaling_facts(
    payload: dict[str, Any], cluster_id: str, path: str, provenance: dict[str, Any]
) -> list[Fact]:
    """`get-managed-scaling-policy` e a UNICA fonte da politica: ela nao aparece
    em `describe-cluster`. Sem este fact, a regra que correlaciona managed
    scaling com alocacao dinamica desligada nao teria gatilho nenhum."""
    raw = payload.get("ManagedScalingPolicy")
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return [_unresolved(path, "malformed_json", provenance, section="ManagedScalingPolicy")]
    limits = raw.get("ComputeLimits")
    if not isinstance(limits, dict):
        # Politica presente no dump mas sem `ComputeLimits` e secao malformada,
        # nao ausencia de politica: dizer "nao ha managed scaling" aqui seria
        # inventar a resposta oposta a que o dump sugere.
        return [
            _unresolved(
                path, "malformed_json", provenance, section="ManagedScalingPolicy.ComputeLimits"
            )
        ]

    measures = {
        name: limits[api_name]
        for api_name, name in _COMPUTE_LIMIT_MEASURES
        if _is_number(limits.get(api_name))
    }
    return [
        Fact(
            kind="emr.managed_scaling",
            subject=_entity_subject(f"{cluster_id}/managed-scaling"),
            measures=measures,
            attrs={"cluster_id": cluster_id, "unit_type": _as_str(limits.get("UnitType"))},
            provenance=provenance,
        )
    ]


# --------------------------------------------------------------------------- #
# extracao
# --------------------------------------------------------------------------- #


def _section(payload: dict[str, Any], cluster: dict[str, Any], key: str) -> Any:
    """Secao lida da forma embutida (`Cluster.<key>`) OU da forma de nivel raiz.

    A embutida vem primeiro so porque, quando existe, ela e a que o dump
    daquele cluster carrega; nenhuma das duas e exigida.
    """
    if key in cluster:
        return cluster[key]
    return payload.get(key)


def _instance_facts(
    payload: dict[str, Any],
    cluster: dict[str, Any],
    cluster_id: str,
    path: str,
    provenance: dict[str, Any],
) -> tuple[list[Fact], list[tuple[str, dict[str, Any]]]]:
    """Facts de capacidade E a lista `(level, entrada_bruta)` cujos
    `Configurations` ainda precisam virar `emr.configuration`."""
    groups = _section(payload, cluster, "InstanceGroups")
    fleets = _section(payload, cluster, "InstanceFleets")

    facts: list[Fact] = []
    scopes: list[tuple[str, dict[str, Any]]] = []

    if groups is not None and not isinstance(groups, list):
        facts.append(_unresolved(path, "malformed_json", provenance, section="InstanceGroups"))
        groups = None
    if fleets is not None and not isinstance(fleets, list):
        facts.append(_unresolved(path, "malformed_json", provenance, section="InstanceFleets"))
        fleets = None

    if groups is None and fleets is None:
        facts.append(_unresolved(path, "missing_instance_model", provenance))
        return facts, scopes

    if groups is not None and fleets is not None:
        # Os dois modelos sao mutuamente exclusivos num cluster real. Os dois
        # presentes no mesmo dump descrevem um cluster que nao existe -- quase
        # sempre dois clusters colados no mesmo arquivo.
        facts.append(_unresolved(path, "conflicting_instance_models", provenance))

    for entry in groups or []:
        if not isinstance(entry, dict):
            facts.append(
                _unresolved(path, "malformed_json", provenance, section="InstanceGroups[]")
            )
            continue
        facts.extend(_instance_group_facts(entry, cluster_id, path, provenance))
        scopes.append(("instance_group", entry))

    for entry in fleets or []:
        if not isinstance(entry, dict):
            facts.append(
                _unresolved(path, "malformed_json", provenance, section="InstanceFleets[]")
            )
            continue
        facts.extend(_instance_fleet_facts(entry, cluster_id, path, provenance))
        scopes.append(("instance_fleet", entry))

    return facts, scopes


def _fleet_scoped_properties(
    fleet: dict[str, Any],
) -> tuple[list[tuple[str, str, str, str]], list[dict[str, Any]]]:
    """Propriedades de um fleet: elas vivem em `InstanceTypeSpecifications[]`,
    uma lista por tipo de instancia, nao num `Configurations` do fleet."""
    specs = fleet.get("InstanceTypeSpecifications")
    if specs is None:
        return [], []
    if not isinstance(specs, list):
        return [], [{"reason": "malformed_json", "section": "InstanceTypeSpecifications"}]

    props: list[tuple[str, str, str, str]] = []
    problems: list[dict[str, Any]] = []
    for spec in specs:
        if not isinstance(spec, dict):
            problems.append({"reason": "malformed_json", "section": "InstanceTypeSpecifications[]"})
            continue
        instance_type = _as_str(spec.get("InstanceType")) or ""
        spec_props, spec_problems = _collect_properties(spec.get("Configurations"))
        props.extend((instance_type, c, k, v) for c, k, v in spec_props)
        problems.extend(spec_problems)
    return props, problems


def _unapplied_fact(
    group: dict[str, Any],
    group_id: str,
    cluster_id: str,
    requested: list[tuple[str, str, str]],
    provenance: dict[str, Any],
) -> Fact | None:
    """`Configurations` != `LastSuccessfullyAppliedConfigurations` -> guarda.

    Comparacao por conteudo achatado, nunca por igualdade estrutural do JSON:
    ordem das entradas e aninhamento sao detalhe de serializacao, e trata-los
    como divergencia produziria um guard que dispara sempre -- guard ruidoso e
    guard ignorado.
    """
    if "LastSuccessfullyAppliedConfigurations" not in group:
        return None
    applied, _problems = _collect_properties(group["LastSuccessfullyAppliedConfigurations"])
    requested_map = {(c, k): v for c, k, v in requested}
    applied_map = {(c, k): v for c, k, v in applied}
    pending = sorted(
        f"{c}/{k}"
        for (c, k), value in requested_map.items()
        if applied_map.get((c, k)) != value
    )
    dropped = sorted(f"{c}/{k}" for (c, k) in applied_map if (c, k) not in requested_map)
    if not pending and not dropped:
        return None

    measures: dict[str, Any] = {
        "pending_property_count": len(pending),
        "dropped_property_count": len(dropped),
    }
    if _is_number(group.get("ConfigurationsVersion")):
        measures["configurations_version"] = group["ConfigurationsVersion"]
    return Fact(
        kind="emr.configuration.unapplied",
        subject=_entity_subject(f"{cluster_id}/{group_id}"),
        measures=measures,
        attrs={
            "cluster_id": cluster_id,
            "scope": group_id,
            "level": "instance_group",
            "reason": "configurations_not_applied",
            "pending": pending,
            "dropped": dropped,
        },
        provenance=provenance,
    )


def _configuration_facts(
    cluster: dict[str, Any],
    scopes: list[tuple[str, dict[str, Any]]],
    cluster_id: str,
    path: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    facts: list[Fact] = []
    pool = _SymbolPool()

    cluster_props, problems = _collect_properties(cluster.get("Configurations"))
    for problem in problems:
        facts.append(_unresolved(path, provenance=provenance, **problem))
    cluster_index = {(c, k): v for c, k, v in cluster_props}

    # Primeiro os niveis de grupo/fleet: eles definem quem SOBREPOE o cluster,
    # e o fact de cluster precisa dessa lista para dizer onde ele nao vale.
    scoped_facts: list[Fact] = []
    overriding: dict[tuple[str, str], list[str]] = {}

    for level, entry in scopes:
        scope_id = _as_str(entry.get("Id"))
        if scope_id is None:
            continue

        if level == "instance_group":
            props, scope_problems = _collect_properties(entry.get("Configurations"))
            typed_props = [("", c, k, v) for c, k, v in props]
        else:
            typed_props, scope_problems = _fleet_scoped_properties(entry)
            props = [(c, k, v) for _t, c, k, v in typed_props]

        for problem in scope_problems:
            facts.append(_unresolved(path, provenance=provenance, scope=scope_id, **problem))

        for instance_type, classification, key, value in typed_props:
            overrides = (classification, key) in cluster_index
            if overrides:
                overriding.setdefault((classification, key), []).append(scope_id)
            extra: dict[str, Any] = {
                "overrides_cluster": overrides,
                "cluster_value": cluster_index.get((classification, key)),
            }
            if level == "instance_fleet":
                extra["instance_type"] = instance_type or None
            symbol = pool.take(f"{cluster_id}/{scope_id}/configuration/{classification}/{key}")
            scoped_facts.append(
                _configuration_fact(
                    classification=classification,
                    key=key,
                    value=value,
                    level=level,
                    scope=scope_id,
                    symbol=symbol,
                    extra_attrs=extra,
                    measures={},
                    provenance=provenance,
                )
            )

        if level == "instance_group":
            unapplied = _unapplied_fact(entry, scope_id, cluster_id, props, provenance)
            if unapplied is not None:
                facts.append(unapplied)

    for classification, key, value in cluster_props:
        scopes_overriding = sorted(overriding.get((classification, key), []))
        symbol = pool.take(f"{cluster_id}/configuration/{classification}/{key}")
        facts.append(
            _configuration_fact(
                classification=classification,
                key=key,
                value=value,
                level="cluster",
                scope="",
                symbol=symbol,
                extra_attrs={"overridden_in": scopes_overriding},
                measures={"overriding_group_count": len(scopes_overriding)},
                provenance=provenance,
            )
        )

    facts.extend(scoped_facts)
    return facts


def extract_emr_cluster(
    payload: dict[str, Any], path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um dump ja carregado (`dict`) de um cluster EMR on EC2.

    Nunca levanta excecao por payload malformado: secao ausente, secao com o
    tipo errado, entrada sem id -- tudo vira `emr.unresolved` e a extracao segue
    com o que sobrar, mesma convencao de
    `athena_workgroup.extract_athena_workgroup`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        return _finish(facts, path, provenance)

    raw_cluster = payload.get("Cluster")
    if raw_cluster is None:
        # Sem `describe-cluster` nao ha release, nem LogUri, nem identidade para
        # ancorar os demais facts. Isso e dump incompleto, e o operador precisa
        # saber qual comando falta.
        facts.append(_unresolved(path, "missing_cluster", provenance))
        return _finish(facts, path, provenance)
    if not isinstance(raw_cluster, dict):
        facts.append(_unresolved(path, "malformed_json", provenance, section="Cluster"))
        return _finish(facts, path, provenance)

    cluster_id = _as_str(raw_cluster.get("Id"))
    if cluster_id is None:
        # Toda entidade deste extrator e ancorada em `<cluster>/...`. Sem o id,
        # nenhum fact tem identidade estavel, e dois dumps diferentes
        # colidiriam no mesmo subject.
        facts.append(_unresolved(path, "missing_cluster_id", provenance))
        return _finish(facts, path, provenance)

    facts.append(_cluster_fact(raw_cluster, cluster_id, payload, provenance))
    facts.extend(_application_facts(raw_cluster, cluster_id, path, provenance))

    instance_facts, scopes = _instance_facts(payload, raw_cluster, cluster_id, path, provenance)
    facts.extend(instance_facts)
    facts.extend(_configuration_facts(raw_cluster, scopes, cluster_id, path, provenance))
    facts.extend(
        _bootstrap_facts(
            _section(payload, raw_cluster, "BootstrapActions"), cluster_id, path, provenance
        )
    )
    facts.extend(_managed_scaling_facts(payload, cluster_id, path, provenance))

    return _finish(facts, path, provenance)


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho para todos os
    caminhos de saida, inclusive os que abortam cedo."""
    counts = {
        "cluster_count": sum(1 for f in facts if f.kind == "emr.cluster"),
        "instance_capacity_count": sum(1 for f in facts if f.kind == "emr.instance_capacity"),
        "configuration_count": sum(1 for f in facts if f.kind == "emr.configuration"),
        "bootstrap_action_count": sum(1 for f in facts if f.kind == "emr.bootstrap_action"),
        "unapplied_count": sum(1 for f in facts if f.kind == "emr.configuration.unapplied"),
        "unresolved_count": sum(1 for f in facts if f.kind == "emr.unresolved"),
    }
    # Sentinela: prova de que a extracao rodou sobre ESTE dump. Sem ela, uma
    # condicao `absent:` sobre fact de EMR seria vacuamente verdadeira quando o
    # extrator nunca rodou. Subject de arquivo, nao de cluster: ela fala do
    # dump, e existe mesmo quando nenhum cluster pode ser lido dele.
    facts.append(
        Fact(
            kind="emr.analyzed",
            subject=_file_subject(path),
            measures=counts,
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    return sort_facts(facts)


def extract_emr_cluster_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `emr.unresolved` com reason "read_error"; JSON invalido
    vira "malformed_json". Nunca uma excecao que derruba quem chamou -- mesma
    convencao de `athena_workgroup.extract_athena_workgroup_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    empty_provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return _finish(
            [_unresolved(anchor, "read_error", empty_provenance, detail=str(exc))],
            anchor,
            empty_provenance,
        )

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _finish([_unresolved(anchor, "malformed_json", provenance)], anchor, provenance)

    return extract_emr_cluster(parsed, anchor, artifact_sha256=sha)


def extract_emr_cluster_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico vira `emr.unresolved`
    para aquele arquivo e a travessia continua -- mesma convencao de
    `athena_workgroup.extract_athena_workgroup_tree`.
    """
    facts: list[Fact] = []
    for json_file in sorted(root.rglob("*.json")):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_emr_cluster_path(json_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
            facts.append(_unresolved(anchor, "read_error", provenance, detail=str(exc)))
    return sort_facts(facts)
