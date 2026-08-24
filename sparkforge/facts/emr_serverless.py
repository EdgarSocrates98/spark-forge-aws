"""Extrator de Facts a partir da definicao de uma application Amazon EMR
Serverless (`aws emr-serverless get-application`).

Como `emr_cluster.py`/`athena_workgroup.py`, este modulo NAO coleta nada: le o
JSON ja salvo em disco, em camelCase, sem traducao. Nunca levanta excecao por
payload malformado -- o que nao consegue ler vira `emrs.unresolved` CONTADO, e a
sentinela `emrs.analyzed` sai sempre, inclusive quando nada pode ser lido.

## O limite que vale para TODOS os facts deste modulo

`get-application` devolve **o padrao da application**, nao o que qualquer job
efetivamente rodou. A documentacao declara a sobreposicao:

    "The priority of configurations that you provide at `StartJobRun` supersede
     the configurations that you provide at the application level."

E o merge do `StartJobRun` inclui **remocao**: `properties: {}` apaga uma
classificacao, `s3MonitoringConfiguration: {}` apaga o destino S3. Nenhum fact
desta area prova o que um job run executou. Toda regra que os cite precisa
redigir o achado como propriedade DA DEFINICAO da application. Dizer "os jobs
desta application nao gravam log em S3" seria o achado confiante e falso que
este pacote existe para evitar. Ver
`knowledge/emr-serverless/application-configuration.md` secao 0.

## Shape esperado do payload

A resposta de `GetApplication`, com a chave de topo `application`:

```json
{
  "application": {
    "applicationId": "00fabc", "name": "etl", "releaseLabel": "emr-7.5.0",
    "type": "Spark", "state": "STARTED", "architecture": "X86_64",
    "autoStartConfiguration": {"enabled": true},
    "autoStopConfiguration": {"enabled": true, "idleTimeoutMinutes": 15},
    "initialCapacity": {
      "DRIVER": {"workerCount": 1,
                 "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"}}
    },
    "maximumCapacity": {"cpu": "400vCPU", "memory": "3000GB", "disk": "20000GB"},
    "runtimeConfiguration": [
      {"classification": "spark-defaults", "properties": {"spark.executor.cores": "4"}}
    ],
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"}
    }
  }
}
```

`initialCapacity` e um **map**, nao uma lista, e a chave e o worker type
(`DRIVER`, `EXECUTOR`, `TEZ_TASK` nos exemplos oficiais). O *value pattern* da
chave -- `[a-zA-Z]+[-_]*[a-zA-Z]+` -- **nao fecha vocabulario**: qualquer
identificador passa, e tratar o conjunto como fechado descartaria capacidade
real. O maximo de 10 entradas, esse sim, e declarado.

## Chave omitida contra chave escrita `False`

`engine._where_matches` **rejeita caminho ausente**, e e assim que este motor diz
"nao sei". Escrever `False` diz "sei que nao", que e outra afirmacao. A distincao
decide regra, e este modulo a aplica campo a campo:

- campo ausente do payload -> **chave omitida** (`name`, `release_label`,
  `state`, `architecture`, `worker_count`, ...);
- `autoStopConfiguration.enabled: false` -> `auto_stop_enabled: False`, porque a
  application declarou o desligamento.

## O default de auto-stop NAO e materializado, e a razao importa

A AWS documenta `autoStopConfiguration.enabled` como *"defaults to true"* com
*"Defaults to 15 minutes"*. Este extrator **nao escreve esse default** quando o
bloco esta ausente. Tres razoes, e a terceira e a que decide:

1. Fact transcreve artefato. Um default materializado ficaria indistinguivel, no
   golden e na evidencia do achado, de um valor que a AWS realmente devolveu.
2. Se o default mudar, o fact vira mentira sem artefato a que atribui-la.
3. **A omissao ja produz o comportamento correto.** As duas regras que consomem
   estes campos acusam o estado PERIGOSO -- `auto_stop_enabled == false` e janela
   ociosa longa --, e o default da AWS e o estado SEGURO. Caminho ausente faz o
   `where` nao casar, e a application no default nao e acusada. Materializar o
   default seria trabalho extra para chegar ao mesmo silencio, correndo o risco
   de uma regra futura ler `auto_stop_enabled: true` como observacao.

Isso e o inverso do EMR on EC2, onde a politica de auto-terminacao precisa ser
ANEXADA e sua ausencia e o estado desprotegido. Transpor `SF-EMR-009` mudando
segundos para minutos transporia a pergunta errada.

Para que uma regra ainda consiga distinguir "a AWS nao devolveu o bloco" de
"o bloco veio", `emrs.application` carrega `auto_stop_declared`, no mesmo papel
que `log_uri_present` tem em `emr.cluster`: um booleano que responde sobre o
PAYLOAD, nao sobre a configuracao efetiva.

## `emrs.monitoring` e a unica excecao, e ela e derivada

Em monitoramento o default da AWS entra na conta, porque sem ele a pergunta nao
e expressavel. Os defaults documentados sao assimetricos:

| Destino | Campo | Default |
|---|---|---|
| managed storage | `managedPersistenceMonitoringConfiguration.enabled` | **`true`** |
| Amazon S3 | `s3MonitoringConfiguration.logUri` | ausente |
| CloudWatch | `cloudWatchLoggingConfiguration.enabled` | **`false`** |

`monitoringConfiguration` ausente significa managed persistence **LIGADA**, com
30 dias de retencao. Uma regra que dispare por ausencia acusaria toda application
no default seguro -- o pior tipo de defeito de regra segundo
`rules/catalog/README.md`. E o inverso tambem morde: se `cloudwatch_enabled`
fosse omitido quando o bloco nao vem, a regra "nenhum destino de log" nao
conseguiria casar justamente o caso mais comum do estado que ela acusa.

Entao `emrs.monitoring` responde **por destino**, com o default documentado
aplicado, e resume em `measures.log_destination_count` -- a correlacao dos tres
campos numa resposta so, mesmo padrao de `emr.yarn.am_node_label`. Cada destino
traz tambem `*_declared`, para o achado saber o que foi lido e o que foi
presumido. `prometheusMonitoringConfiguration` **nao conta**: carrega
`remoteWriteUrl`, nao `enabled`, e e destino de METRICA, nao de log.

## As unidades de capacidade, e por que `unresolved` continua necessario

A referencia de API restringe os tres campos por regex:

    cpu     [1-9][0-9]*(\\s)?(vCPU|vcpu|VCPU)?
    memory  [1-9][0-9]*(\\s)?(GB|gb|gB|Gb)?
    disk    [1-9][0-9]*(\\s)?(GB|gb|gB|Gb)

Quatro leituras que este parser implementa: o espaco e **opcional** e os exemplos
oficiais nao o usam (`"2vCPU"`, `"4GB"`); a unidade e **opcional** em `cpu` e
`memory` -- exigir sufixo emitiria `unresolved` para valor legitimo; o numero e
**inteiro positivo sem decimal**; e o conjunto de unidades e minusculo, com `MB`
**nao expressavel**. A armadilha `"16 GB"` contra `"16384 MB"` nao pode ocorrer
neste artefato.

**Mesmo assim o `unresolved` de unidade existe, e por outra razao:** os patterns
restringem o que a API aceita na ENTRADA. Nada na documentacao garante que
`get-application` so devolva valores que os satisfacam, nem que os patterns nao
mudem. Valor fora do conjunto vira `unknown_capacity_unit` -- nao e adivinhacao,
e o registro de que a fonte descreveu um conjunto e o artefato trouxe outra
coisa.

## A correlacao de capacidade mora aqui

`engine._condition_candidates` avalia **um fact por vez**, entao "initialCapacity
somada acima de maximumCapacity" nao e expressavel no catalogo (D-4 do spec).
Este modulo soma os tres eixos (`workerCount` x cpu, idem memoria e disco),
compara eixo a eixo -- *"No new resources will be created once any one of the
defined limits is hit"* autoriza tratar os eixos independentemente -- e emite
`attrs.initial_exceeds_maximum` mais `attrs.capacity_axes_exceeded`.

**As duas chaves sao OMITIDAS quando falta dado para decidir**: `maximumCapacity`
ausente (`Required: No` na referencia -- este caso e comum, nao excepcional), um
eixo ausente de um dos lados, unidade ilegivel em qualquer worker. Quando a causa
ja produziu `unresolved` proprio, o ponto cego nao e contado duas vezes.

O que o fact afirma e que **os numeros se contradizem**, nao que a configuracao
seja invalida: nao ha declaracao na documentacao de que a API aceite nem de que
rejeite esse estado. A reachability e nao documentada, e quem julgar precisa
dize-lo.

Pela mesma razao, `emrs.application` carrega
`measures.initial_capacity_worker_count`: a cobranca de worker so corre com
capacidade pre-inicializada, entao "auto-stop desligado" e "auto-stop desligado
COM pre-init" nao sao o mesmo defeito, e as duas perguntas precisam caber num
fact so. Duas condicoes em kinds diferentes casariam a application A com a
capacidade da application B num diretorio com varios payloads.

## O measure de pre-init conta WORKER, nao entrada do map

`initial_capacity_worker_count` e a SOMA dos `workerCount` LIDOS nas entradas de
`initialCapacity`. Ele ja foi a contagem de entradas do map, e a troca fecha um
falso positivo P0 medido: `{"DRIVER": {"workerCount": 0, ...}}` com auto-stop
desligado tem uma entrada e nenhum worker, e a `explanation` de `SF-EMRS-001`
fundamenta o achado em *"o que se cobra e worker existente"*. Zero workers nao e
worker existente. `SF-EMRS-005` tinha o mesmo termo e o mesmo defeito.

O caso irmao e pior: entrada **sem** `workerCount` produzia `unresolved`
`missing_worker_count` e, no MESMO julgamento, uma P0. Uma P0 erguida sobre um
ponto cego que o proprio extrator acabou de declarar e o achado confiante e falso
que este pacote existe para evitar. Entrada com contagem ilegivel nao soma nada,
e o buraco continua contado uma vez so, no `unresolved`.

Nada torna esses payloads inalcancaveis:
`knowledge/emr-serverless/application-configuration.md` registra `workerCount`
apenas como "(numero)" -- sem `Required`, sem minimo --, e vale aqui a mesma
doutrina que sustentou `unknown_capacity_unit`: nada na documentacao garante que
`get-application` so devolva valores que satisfacam os patterns de ENTRADA.

A contagem de ENTRADAS do map nao se perdeu: ela e
`emrs.analyzed.measures.initial_capacity_count`. Mante-la tambem em
`emrs.application` seria measure duplicado sem consumidor.

## `EMR.secret@` e o estado CORRETO, nao o defeito

O EMR Serverless tem anotacao propria de segredo:

    "spark.hadoop.javax.jdo.option.ConnectionPassword": "EMR.secret@{{NomeDoSegredo}}"

Um valor anotado e um **ID de segredo, nao um segredo**: o EMR resolve pelo
Secrets Manager na hora da execucao. Acusa-lo seria acusar exatamente a correcao
que o achado recomenda. Entao a anotacao e testada **antes** da heuristica de
segredo e vence: `attrs.secret_reference: True`, sem redacao e sem
`secret_pattern_match`. A precedencia nao e cosmetica -- o padrao de access key
da AWS em `facts/secrets.py` usa `search`, nao `fullmatch`, entao um nome de
segredo que pareca uma credencial casaria a heuristica se ela rodasse primeiro.

Isso nao existe no vocabulario de `emr_cluster.py` e e acrescimo desta area.

### LIMITE DECLARADO: a anotacao e bypass INCONDICIONAL da heuristica

`_is_secret_reference` e `startswith` puro. Entao
`"EMR.secret@AKIAIOSFODNN7EXAMPL"` e `"EMR.secret@jdbc://user:senha@host"` viram
`secret_reference: True` e o valor **inteiro e escrito em `attrs.value`, sem
redacao** -- e, num golden, commitado. A regra da secao seguinte ("quando casa, o
valor NUNCA e escrito") vale para a heuristica; ela **nao** vale quando a
anotacao vence antes.

O comportamento fica, e a razao e medida. A fonte declara **so o prefixo** --
*"add the `EMR.secret@` annotation to the configuration value"* --; o
`{{SecretName}}` aparece no EXEMPLO, nao como gramatica exigida. Validar a forma
`EMR.secret@{{nome}}` inventaria uma gramatica que a fonte nao declara, e toda
anotacao legitima fora dela seria redigida **e** marcada `secret_pattern_match`,
fazendo `SF-EMRS-002` acusar exatamente a correcao que recomenda -- o pior tipo
de defeito de regra segundo `rules/catalog/README.md`.

O que fecharia o buraco sem custo de falso positivo, se um dia valer a pena:
manter `secret_reference: True` (achado nenhum) e **ainda assim** redigir
`attrs.value` quando o valor anotado casa a heuristica. O custo e que a evidencia
deixa de dizer QUAL segredo e referenciado, que e a parte util dela. Registrado
em `docs/superpowers/STATUS.md`, em *Limites declarados*.

## Segredo: a heuristica vem de `facts/secrets.py`, fonte unica

Este modulo ja teve copia privada da heuristica, ao lado de outras duas em
`facts/terraform.py` e `facts/emr_cluster.py`, defendida como convencao do
pacote: extratores sao modulos independentes por desenho. A independencia vale
para EXTRACAO; nao vale para um controle de seguranca, onde uma copia que
diverge vaza segredo por um extrator e nao pelos demais sem que nada acuse. As
tres copias sairam e `tests/test_facts_secrets.py` tem gate estrutural contra a
proxima. Quando `facts.secrets.looks_like_secret` casa, o valor nao e escrito
em `attrs` -- vira `<redigido>`, com `attrs.secret_pattern_match: true`. Um
golden commitado com credencial real seria o analisador causando o dano que a
regra previne.

**A heuristica so roda quando a anotacao `EMR.secret@` nao venceu antes**, e essa
excecao esta declarada na secao anterior. Nao e "o valor NUNCA e escrito": e "o
valor nao e escrito quando a heuristica decide".

## Release label: tres formas, e duas nao tem serie

`emr-7.5.0` da `release_major=7`, `release_minor=5`. Mas `emr-spark-8.0.0` e
`emr-spark-8.0-preview` sao release labels **validos** do Serverless
(`knowledge/emr-serverless/runtime-matrix.md` secao 4), e nenhum casa
`emr-<major>.<minor>.<patch>`. Para eles as duas measures sao **omitidas** --
nunca forcadas. Um `8` extraido de `emr-spark-8.0-preview` por regex frouxo seria
numero inventado.

E `releaseLabel` **nao alimenta `RuntimeContext.emr`**. A AWS nao publica Hadoop,
Iceberg nem Python por release do Serverless: tres das quatro colunas de
`EMR_MATRIX` nao tem fonte deste lado, e derivar por uma matriz de EMR on EC2
produziria versao de Spark afirmada sem artefato. O label sai como `attrs` e a
serie como `measures`; o produtor nao existe, e a razao escrita e "sem fonte",
nao "matrizes divergentes".

Como os demais extratores: puro e deterministico. Nunca aplica limiar, nunca
atribui severidade, nunca infere o que o payload nao diz.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from sparkforge.facts.secrets import looks_like_secret as _looks_like_secret
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "emr_serverless@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "emrs.application",
        "emrs.initial_capacity",
        "emrs.configuration",
        "emrs.monitoring",
        "emrs.unresolved",
        "emrs.analyzed",
    }
)

# `emr-7.5.0` -> (7, 5). ESTRITO de proposito: qualquer coisa entre `emr-` e o
# primeiro numero derruba o match, e e o que impede `emr-spark-8.0.0` e
# `emr-spark-8.0-preview` de virarem uma serie `8` que ninguem afirmou.
_RELEASE_RE = re.compile(r"^emr-(\d+)\.(\d+)(?:\.\d+)?$", re.IGNORECASE)

# Inteiro positivo, espaco opcional, sufixo alfabetico opcional -- a forma que os
# patterns da referencia de API descrevem. A unidade LIDA e validada contra o
# conjunto fechado de cada campo (`_CAPACITY_UNITS`); o que sobra vira
# `unknown_capacity_unit`, nunca um numero presumido.
_QUANTITY_RE = re.compile(r"^\s*([1-9][0-9]*)\s*([A-Za-z]*)\s*$")

# Conjunto FECHADO por campo, em minusculas. `vCPU|vcpu|VCPU` e `GB|gb|gB|Gb` sao
# as grafias que a AWS declara; comparar em minusculas cobre as quatro sem
# alargar o conjunto. Unidade vazia e aceita: o pattern da AWS termina em `)?`
# para `cpu` e `memory`, e em `disk` o unico sufixo expressavel e `GB`, entao um
# valor cru nao e ambiguo em nenhum dos tres.
_CAPACITY_UNITS: dict[str, frozenset[str]] = {
    "cpu": frozenset({"", "vcpu"}),
    "memory": frozenset({"", "gb"}),
    "disk": frozenset({"", "gb"}),
}

# Os tres eixos comparaveis entre `initialCapacity` e `maximumCapacity`, na
# ordem em que aparecem no measure. A comparacao exige os TRES dos DOIS lados.
_CAPACITY_AXES: tuple[tuple[str, str], ...] = (
    ("cpu", "cpu"),
    ("memory", "memory_gb"),
    ("disk", "disk_gb"),
)

# A anotacao de segredo do EMR Serverless. Valor que COMECA com ela e um ID de
# segredo, nao um segredo -- ver a secao dedicada na docstring do modulo.
SECRET_REFERENCE_PREFIX = "EMR.secret@"  # noqa: S105 -- anotacao publica, nao credencial

# Os padroes de credencial moram em `facts/secrets.py`, fonte unica. Ver a
# secao "Segredo" da docstring do modulo para por que a copia local saiu.
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
    """Subject de uma entidade da application.

    `job_run` e o membro de `fact.schema.json` que descreve entidade de
    EXECUCAO -- o mesmo que `emr_cluster` e `athena_workgroup` usam. O `symbol`
    e a identidade hierarquica (`<application>/<parte>/...`).
    """
    return {"type": "job_run", "symbol": symbol}


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _as_bool(value: Any) -> bool | None:
    """`True`/`False` quando o payload traz booleano; `None` quando nao traz nada
    ou traz outra coisa. Nunca um default."""
    return value if isinstance(value, bool) else None


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _value_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _put(target: dict[str, Any], key: str, value: Any) -> None:
    """Escreve so quando ha valor. Chave omitida e como este motor diz "nao
    sei"; `None` gravado seria um caminho presente com conteudo vazio."""
    if value is not None:
        target[key] = value


def _is_secret_reference(value: str) -> bool:
    """`startswith` puro, e isso e BYPASS INCONDICIONAL da heuristica.

    `EMR.secret@<credencial real>` sai com o valor inteiro em `attrs.value`, sem
    redacao. Limite declarado, com a razao, na secao "LIMITE DECLARADO" da
    docstring do modulo -- nao endurecer sem ler.
    """
    return value.startswith(SECRET_REFERENCE_PREFIX)


def _unresolved(path: str, reason: str, provenance: dict[str, Any], **extra: Any) -> Fact:
    return Fact(
        kind="emrs.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


class _SymbolPool:
    """Garante `symbol` unico por entidade dentro de um payload.

    `Fact.id` e o hash de (kind, subject, measures): duas propriedades da mesma
    classificacao com o mesmo nome -- dado contraditorio, mas possivel com duas
    entradas de mesma `classification` -- colidiriam num id so, com `attrs`
    diferentes. Um sufixo `#N` deterministico mantem os dois rastreaveis.
    """

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def take(self, symbol: str) -> str:
        count = self._seen.get(symbol, 0)
        self._seen[symbol] = count + 1
        return symbol if count == 0 else f"{symbol}#{count}"


# --------------------------------------------------------------------------- #
# release label
# --------------------------------------------------------------------------- #


def _release_numbers(label: str | None) -> tuple[int | None, int | None]:
    """`emr-7.5.0` -> `(7, 5)`; qualquer outra forma -> `(None, None)`.

    O par sai como measure para que uma regra possa perguntar "serie 6.x?" sem
    depender da deteccao de runtime -- o proprio payload prova a release, e
    comparacao de string nao existe no avaliador de expressoes do catalogo.
    """
    if label is None:
        return None, None
    match = _RELEASE_RE.match(label)
    if match is None:
        return None, None
    return int(match.group(1)), int(match.group(2))


# --------------------------------------------------------------------------- #
# capacidade
# --------------------------------------------------------------------------- #


def _parse_quantity(raw: Any, field: str) -> tuple[int | None, bool]:
    """`("4vCPU", "cpu")` -> `(4, False)`. Devolve `(valor, ilegivel)`.

    `ilegivel` distingue "o campo nao veio" (`(None, False)`, silencio legitimo:
    `disk` e opcional nos dois lados) de "o campo veio e nao esta no conjunto
    documentado" (`(None, True)`, ponto cego que precisa ser contado).
    """
    if raw is None:
        return None, False
    if not isinstance(raw, str):
        return None, True
    match = _QUANTITY_RE.match(raw)
    if match is None:
        return None, True
    if match.group(2).lower() not in _CAPACITY_UNITS[field]:
        return None, True
    return int(match.group(1)), False


def _quantities(
    source: dict[str, Any], path: str, provenance: dict[str, Any], **extra: Any
) -> tuple[dict[str, int], list[Fact]]:
    """Le `cpu`/`memory`/`disk` de um `WorkerResourceConfig` ou de um
    `MaximumAllowedResources` -- os dois usam exatamente os mesmos patterns."""
    values: dict[str, int] = {}
    problems: list[Fact] = []
    for field, measure in _CAPACITY_AXES:
        parsed, unreadable = _parse_quantity(source.get(field), field)
        if unreadable:
            problems.append(
                _unresolved(
                    path,
                    "unknown_capacity_unit",
                    provenance,
                    field=field,
                    value=_value_to_str(source.get(field)),
                    **extra,
                )
            )
        elif parsed is not None:
            values[measure] = parsed
    return values, problems


def _initial_capacity_facts(
    raw: Any,
    application_id: str,
    path: str,
    provenance: dict[str, Any],
) -> tuple[list[Fact], list[dict[str, int]], bool]:
    """Um fact por entrada do map `initialCapacity`.

    Devolve tambem os totais legiveis por entrada e se algum ponto cego ja foi
    contado -- a correlacao de capacidade usa os dois para nao contar o mesmo
    buraco duas vezes.
    """
    if raw is None:
        return [], [], False
    if not isinstance(raw, dict):
        return (
            [_unresolved(path, "malformed_json", provenance, section="initialCapacity")],
            [],
            True,
        )

    facts: list[Fact] = []
    totals: list[dict[str, int]] = []
    blind = False
    for worker_type in sorted(raw):
        entry = raw[worker_type]
        if not isinstance(entry, dict):
            facts.append(
                _unresolved(
                    path,
                    "malformed_json",
                    provenance,
                    section="initialCapacity[]",
                    worker_type=worker_type,
                )
            )
            blind = True
            continue

        config = _as_dict(entry.get("workerConfiguration"))
        values, problems = _quantities(config, path, provenance, worker_type=worker_type)
        facts.extend(problems)
        blind = blind or bool(problems)

        measures: dict[str, Any] = {}
        count = entry.get("workerCount")
        if _is_number(count):
            measures["worker_count"] = count
        else:
            facts.append(
                _unresolved(path, "missing_worker_count", provenance, worker_type=worker_type)
            )
            blind = True
        measures.update(values)

        attrs: dict[str, Any] = {"worker_type": worker_type}
        _put(attrs, "disk_type", _as_str(config.get("diskType")))

        facts.append(
            Fact(
                kind="emrs.initial_capacity",
                subject=_entity_subject(f"{application_id}/initial_capacity/{worker_type}"),
                measures=measures,
                attrs=attrs,
                provenance=provenance,
            )
        )
        totals.append(measures)
    return facts, totals, blind


def _capacity_decision(
    totals: list[dict[str, int]],
    maximum: Any,
    path: str,
    provenance: dict[str, Any],
    blind: bool,
) -> tuple[dict[str, Any], list[Fact]]:
    """Soma os eixos da capacidade inicial e compara com o teto.

    Devolve `({}, ...)` -- as duas chaves omitidas -- sempre que faltar dado para
    decidir. O `unresolved` so sai quando o buraco AINDA NAO foi contado: se um
    worker ja produziu `unknown_capacity_unit`, contar de novo inflaria o ponto
    cego do mesmo defeito.
    """
    if not totals:
        # Sem capacidade pre-inicializada nao ha o que comparar. Isso nao e
        # ponto cego: e a ausencia da pergunta.
        return {}, []

    if not isinstance(maximum, dict):
        if maximum is not None:
            return {}, [
                _unresolved(path, "malformed_json", provenance, section="maximumCapacity")
            ]
        if blind:
            return {}, []
        return {}, [
            _unresolved(
                path,
                "capacity_comparison_undecidable",
                provenance,
                detail="missing_maximum_capacity",
            )
        ]

    ceiling, problems = _quantities(maximum, path, provenance, section="maximumCapacity")
    if problems:
        return {}, problems

    axes = [measure for _, measure in _CAPACITY_AXES]
    missing = [axis for axis in axes if axis not in ceiling]
    for entry in totals:
        missing.extend(axis for axis in axes if axis not in entry)
        if "worker_count" not in entry:
            missing.append("worker_count")
    if missing:
        if blind:
            return {}, []
        return {}, [
            _unresolved(
                path,
                "capacity_comparison_undecidable",
                provenance,
                detail="missing_capacity_axis",
                axes=sorted(set(missing)),
            )
        ]

    exceeded = [
        axis
        for axis in axes
        if sum(entry["worker_count"] * entry[axis] for entry in totals) > ceiling[axis]
    ]
    return {
        "initial_exceeds_maximum": bool(exceeded),
        "capacity_axes_exceeded": sorted(exceeded),
    }, []


# --------------------------------------------------------------------------- #
# runtimeConfiguration
# --------------------------------------------------------------------------- #


def _collect_properties(entries: Any) -> tuple[list[tuple[str, str, str]], list[dict[str, Any]]]:
    """Achata `runtimeConfiguration` em `[(classification, key, value)]`.

    Recursivo: `Configuration.configurations` e aninhado e declarado na
    referencia de API, e a classificacao do filho e a que vale para as
    propriedades dele. Devolve tambem os problemas, para o chamador transformar
    em `emrs.unresolved` -- entrada malformada nunca e ignorada em silencio.
    """
    if entries is None:
        return [], []
    if not isinstance(entries, list):
        return [], [{"reason": "malformed_json", "section": "runtimeConfiguration"}]

    props: list[tuple[str, str, str]] = []
    problems: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append({"reason": "malformed_json", "section": "runtimeConfiguration[]"})
            continue
        classification = _as_str(entry.get("classification"))
        if classification is None:
            problems.append({"reason": "missing_classification"})
            continue
        properties = entry.get("properties")
        if properties is not None and not isinstance(properties, dict):
            problems.append(
                {"reason": "malformed_json", "section": f"{classification}.properties"}
            )
        elif isinstance(properties, dict):
            for key, value in properties.items():
                if not isinstance(key, str) or not key.strip():
                    problems.append(
                        {"reason": "missing_property_key", "classification": classification}
                    )
                    continue
                props.append((classification, key.strip(), _value_to_str(value)))
        nested_props, nested_problems = _collect_properties(entry.get("configurations"))
        props.extend(nested_props)
        problems.extend(nested_problems)
    return props, problems


def _configuration_facts(
    raw: Any,
    application_id: str,
    path: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    props, problems = _collect_properties(raw)
    facts: list[Fact] = [
        _unresolved(path, problem.pop("reason"), provenance, **problem) for problem in problems
    ]

    pool = _SymbolPool()
    for classification, key, value in props:
        # `emrs.configuration` NAO carrega `level` nem `scope` (D-3 do spec):
        # Serverless nao tem grupo de instancia, logo nao ha override entre
        # niveis, logo nao ha nivel a declarar. Chave ausente e como este motor
        # diz "nao se aplica".
        attrs: dict[str, Any] = {"classification": classification, "key": key, "value": value}
        if _is_secret_reference(value):
            # ANTES da heuristica, e a ordem e o teste: o padrao de access key
            # da AWS em `facts/secrets.py` usa `search`, nao `fullmatch`,
            # entao um nome de segredo que pareca uma credencial seria acusado
            # se a heuristica rodasse primeiro -- e o achado acusaria a propria
            # correcao que recomenda.
            attrs["secret_reference"] = True
        elif _looks_like_secret(key, value):
            attrs["value"] = REDACTED
            attrs["redacted"] = True
            attrs["secret_pattern_match"] = True
        facts.append(
            Fact(
                kind="emrs.configuration",
                subject=_entity_subject(
                    pool.take(f"{application_id}/configuration/{classification}/{key}")
                ),
                attrs=attrs,
                provenance=provenance,
            )
        )
    return facts


# --------------------------------------------------------------------------- #
# monitoring
# --------------------------------------------------------------------------- #


def _monitoring_facts(
    raw: Any,
    application_id: str,
    path: str,
    provenance: dict[str, Any],
) -> list[Fact]:
    """`emrs.monitoring` sai SEMPRE que a application e lida.

    Ver a secao dedicada na docstring do modulo para por que este e o unico fact
    do modulo que aplica default documentado.
    """
    problems: list[Fact] = []
    if raw is not None and not isinstance(raw, dict):
        problems.append(
            _unresolved(path, "malformed_json", provenance, section="monitoringConfiguration")
        )
        raw = None
    config = _as_dict(raw)

    s3 = _as_dict(config.get("s3MonitoringConfiguration"))
    log_uri = _as_str(s3.get("logUri"))

    managed_raw = config.get("managedPersistenceMonitoringConfiguration")
    managed_declared = isinstance(managed_raw, dict)
    managed_enabled = _as_bool(_as_dict(managed_raw).get("enabled"))
    # Default documentado: `true`. So o `false` EXPLICITO desliga.
    managed = managed_enabled is not False

    cloudwatch_raw = config.get("cloudWatchLoggingConfiguration")
    cloudwatch_declared = isinstance(cloudwatch_raw, dict)
    # Default documentado: `false`. So o `true` EXPLICITO liga.
    cloudwatch = _as_bool(_as_dict(cloudwatch_raw).get("enabled")) is True

    attrs: dict[str, Any] = {
        "monitoring_declared": isinstance(raw, dict),
        "s3_log_uri_present": log_uri is not None,
        "managed_persistence_enabled": managed,
        "managed_persistence_declared": managed_declared,
        "cloudwatch_enabled": cloudwatch,
        "cloudwatch_declared": cloudwatch_declared,
    }
    _put(attrs, "s3_log_uri", log_uri)

    return [
        *problems,
        Fact(
            kind="emrs.monitoring",
            subject=_entity_subject(f"{application_id}/monitoring"),
            measures={
                "log_destination_count": sum((log_uri is not None, managed, cloudwatch)),
            },
            attrs=attrs,
            provenance=provenance,
        ),
    ]


# --------------------------------------------------------------------------- #
# application
# --------------------------------------------------------------------------- #


def _application_fact(
    application: dict[str, Any],
    application_id: str,
    capacity: dict[str, Any],
    worker_count: int | float,
    provenance: dict[str, Any],
) -> Fact:
    label = _as_str(application.get("releaseLabel"))
    major, minor = _release_numbers(label)

    auto_start = application.get("autoStartConfiguration")
    auto_stop = application.get("autoStopConfiguration")

    attrs: dict[str, Any] = {"application_id": application_id}
    _put(attrs, "name", _as_str(application.get("name")))
    _put(attrs, "release_label", label)
    _put(attrs, "type", _as_str(application.get("type")))
    _put(attrs, "state", _as_str(application.get("state")))
    _put(attrs, "architecture", _as_str(application.get("architecture")))
    # Os dois `*_declared` respondem sobre o PAYLOAD -- "a AWS devolveu o bloco?"
    # --, nunca sobre a configuracao efetiva. Sao o que permite a uma regra
    # distinguir default da AWS de configuracao explicita sem que o extrator
    # precise materializar o default.
    attrs["auto_start_declared"] = isinstance(auto_start, dict)
    attrs["auto_stop_declared"] = isinstance(auto_stop, dict)
    _put(attrs, "auto_start_enabled", _as_bool(_as_dict(auto_start).get("enabled")))
    _put(attrs, "auto_stop_enabled", _as_bool(_as_dict(auto_stop).get("enabled")))
    attrs.update(capacity)

    # Quantos workers pre-inicializados o payload DECLARA: a soma dos
    # `workerCount` lidos nas entradas de `initialCapacity`. Sai sempre, zero
    # incluso, pela mesma razao que os contadores da sentinela saem: e contagem
    # do que a extracao produziu, nao afirmacao sobre a AWS.
    #
    # Existe porque duas regras da area precisam de "ha worker pre-inicializado?"
    # e "auto-stop desligado?" NO MESMO fact: a cobranca de worker so corre com
    # pre-init, entao auto-stop desligado sem pre-init nao e o mesmo defeito.
    # Como `engine._condition_candidates` avalia um fact por vez, duas condicoes
    # em kinds diferentes casariam a application A com a capacidade da
    # application B num diretorio com varios payloads -- acusando duas
    # configuracoes corretas. Correlacionar aqui e o padrao da D-4.
    #
    # WORKER, nao entrada do map: `{"DRIVER": {"workerCount": 0}}` tem uma
    # entrada e nenhum worker, e uma entrada sem `workerCount` nao tem worker
    # PROVADO -- ela ja saiu como `missing_worker_count`. Ver a secao dedicada na
    # docstring do modulo. A contagem de entradas continua existindo, em
    # `emrs.analyzed.measures.initial_capacity_count`.
    #
    # Zero significa que o payload nao provou worker nenhum -- por nao trazer
    # `initialCapacity`, por trazer contagem zero, ou por trazer contagem
    # ilegivel. Uma regra que leia zero como "nao ha pre-init" esta afirmando a
    # partir do silencio do payload, e a `explanation` precisa dize-lo.
    measures: dict[str, Any] = {"initial_capacity_worker_count": worker_count}
    if major is not None:
        measures["release_major"] = major
    if minor is not None:
        measures["release_minor"] = minor
    timeout = _as_dict(auto_stop).get("idleTimeoutMinutes")
    if _is_number(timeout):
        measures["idle_timeout_minutes"] = timeout

    return Fact(
        kind="emrs.application",
        subject=_entity_subject(application_id),
        measures=measures,
        attrs=attrs,
        provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# entrada
# --------------------------------------------------------------------------- #


def extract_emr_serverless(
    payload: Any, path: str, artifact_sha256: str = ""
) -> list[Fact]:
    """Extrai Facts de um payload ja carregado (`dict`) de `get-application`.

    Nunca levanta excecao por payload malformado: chave ausente, secao com o
    tipo errado, unidade fora do conjunto documentado -- tudo vira
    `emrs.unresolved` e a extracao segue com o que sobrar, mesma convencao de
    `emr_cluster.extract_emr_cluster`.
    """
    provenance = {"artifact": path, "artifact_sha256": artifact_sha256, "extractor": EXTRACTOR_ID}
    facts: list[Fact] = []

    if not isinstance(payload, dict):
        facts.append(_unresolved(path, "malformed_json", provenance))
        return _finish(facts, path, provenance)

    raw = payload.get("application")
    if raw is None:
        # Sem `get-application` nao ha release, nem capacidade, nem identidade
        # para ancorar os demais facts. O operador precisa saber qual comando
        # falta.
        facts.append(_unresolved(path, "missing_application", provenance))
        return _finish(facts, path, provenance)
    if not isinstance(raw, dict):
        facts.append(_unresolved(path, "malformed_json", provenance, section="application"))
        return _finish(facts, path, provenance)

    application_id = _as_str(raw.get("applicationId"))
    if application_id is None:
        # Toda entidade deste extrator e ancorada em `<application>/...`. Sem o
        # id, nenhum fact tem identidade estavel e dois payloads diferentes
        # colidiriam no mesmo subject.
        facts.append(_unresolved(path, "missing_application_id", provenance))
        return _finish(facts, path, provenance)

    capacity_facts, totals, blind = _initial_capacity_facts(
        raw.get("initialCapacity"), application_id, path, provenance
    )
    decision, decision_problems = _capacity_decision(
        totals, raw.get("maximumCapacity"), path, provenance, blind
    )

    facts.append(
        _application_fact(
            raw,
            application_id,
            decision,
            # Entrada com `workerCount` ilegivel nao esta em `totals` com a
            # chave, e por isso nao soma nada: o ponto cego ja saiu como
            # `missing_worker_count` e somar um valor presumido o apagaria.
            sum(entry.get("worker_count", 0) for entry in totals),
            provenance,
        )
    )
    facts.extend(capacity_facts)
    facts.extend(decision_problems)
    facts.extend(
        _configuration_facts(raw.get("runtimeConfiguration"), application_id, path, provenance)
    )
    facts.extend(
        _monitoring_facts(raw.get("monitoringConfiguration"), application_id, path, provenance)
    )

    return _finish(facts, path, provenance)


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho para todos os
    caminhos de saida, inclusive os que abortam cedo."""
    counts = {
        "application_count": sum(1 for f in facts if f.kind == "emrs.application"),
        "initial_capacity_count": sum(1 for f in facts if f.kind == "emrs.initial_capacity"),
        "configuration_count": sum(1 for f in facts if f.kind == "emrs.configuration"),
        "unresolved_count": sum(1 for f in facts if f.kind == "emrs.unresolved"),
    }
    # Sentinela: prova de que a extracao rodou sobre ESTE payload. Sem ela, uma
    # condicao `absent:` sobre fact de Serverless seria vacuamente verdadeira
    # quando o extrator nunca rodou. Subject de arquivo, nao de application: ela
    # fala do payload, e existe mesmo quando nenhuma application pode ser lida.
    facts.append(
        Fact(
            kind="emrs.analyzed",
            subject=_file_subject(path),
            measures=counts,
            provenance=provenance,
        )
    )

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")
    return sort_facts(facts)


def extract_emr_serverless_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.json`, ancorando o path relativo a `repo_root`.

    Falha ao abrir vira `emrs.unresolved` com reason "read_error"; JSON invalido
    vira "malformed_json". Nunca uma excecao que derruba quem chamou.
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

    return extract_emr_serverless(parsed, anchor, artifact_sha256=sha)


def extract_emr_serverless_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `*.json` sob `root`, em ordem deterministica de path.

    Falha por arquivo nao e fatal: um arquivo problematico vira
    `emrs.unresolved` para aquele arquivo e a travessia continua.
    """
    facts: list[Fact] = []
    for json_file in sorted(root.rglob("*.json")):
        rel = str(json_file.relative_to(repo_root)) if repo_root else str(json_file)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_emr_serverless_path(json_file, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            provenance = {"artifact": anchor, "artifact_sha256": "", "extractor": EXTRACTOR_ID}
            facts.append(_unresolved(anchor, "read_error", provenance, detail=str(exc)))
    return sort_facts(facts)
