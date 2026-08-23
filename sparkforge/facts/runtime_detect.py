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

from sparkforge.facts import runtime_matrix
from sparkforge.findings.models import Fact, RuntimeContext, sort_facts

DETECTOR_ID = "runtime_detect@0.1.0"

# Vocabulario fechado de kinds, como nos demais extratores. Serve de fonte
# unica para `tests/test_rules_catalog_reachability.py`: uma regra que exija um
# kind fora da uniao de todos os EMITTED_KINDS e inalcancavel e precisa declarar
# `blocked_on`, em vez de aparecer como "faltou coletar".
EMITTED_KINDS = frozenset({"env.runtime_signal", "env.platform"})

# GLUE_MATRIX morava aqui como constante compilada, sem fonte nem data de
# consulta. Versao de Glue e fato EXTERNO -- muda por decisao da AWS, nao
# deste repositorio --, entao a Task 1 da fase SF-MIG moveu o dado para
# `knowledge/glue/runtime-matrix.yaml`, ao lado dos demais fatos externos
# vigiados por `knowledge/sources.lock.json`. Ver o docstring de
# `sparkforge/facts/runtime_matrix.py` para o formato e as garantias do loader.
#
# `GLUE_MATRIX` continua existindo aqui como NOME, para nao quebrar os
# consumidores que ja importam `sparkforge.facts.runtime_detect.GLUE_MATRIX`
# (`tests/test_runtime_detect.py`, `tests/test_runtime_glue_versions.py`,
# `tests/test_rule_scope_by_nature.py`, `tests/test_runtime_emr_matrix.py`,
# `tests/test_runtime_inferred_from_facts.py`, `scripts/check_evals.py`) --
# mas o VALOR e derivado do loader a cada import, nunca escrito a mao. Filtra
# para `spark`/`python`/`iceberg` porque e a forma que este modulo sempre
# consumiu; `sources`/`retrieved`/`scala`/`java` que o YAML carrega ficam de
# fora daqui de proposito -- ver o comentario abaixo, no consumidor de
# `_DERIVABLE`, sobre por que uma chave sem consumidor nao deve vazar para
# `RuntimeContext` nem para golden.
GLUE_MATRIX: dict[str, dict[str, str]] = {
    versao: {chave: linha[chave] for chave in ("spark", "python", "iceberg") if chave in linha}
    for versao, linha in runtime_matrix.load().items()
}

# Espelha knowledge/emr/runtime-matrix.md, secoes 2 e 3. Chave sem o prefixo
# `emr-`; `_emr_key` aceita as duas grafias.
#
# QUATRO DECISOES DE DESENHO, todas justificadas na pagina de knowledge:
#
# 1. `-amzn-N` E GUARDADO CRU. `3.5.6-amzn-2` nao e o `3.5.6` da Apache: e um
#    fork com patches da AWS, e descartar o sufixo esconderia que o cluster
#    roda um fork -- a unica pista de um NoSuchMethodError que so existe la.
#    A comparacao de `runtime_scope` continua sendo contra versao Apache
#    porque `version_scope._parse` trunca no sufixo. Isso ja valia para a forma
#    de um nivel; a forma de dois niveis de 6.x (`3.3.2-amzn-0.1`) quebrava, e
#    foi corrigida na mesma entrega desta matriz.
#
# 2. `python` E O DEFAULT DO PYSPARK, e so existe onde a AWS o documenta.
#    A coluna `Python` da pagina oficial lista os interpretadores INSTALADOS
#    (`3.9, 3.11`), nao o que o PySpark executa -- isso e `PYSPARK_PYTHON`, na
#    classificacao `spark-env`. A release note de 7.13.0 declara a virada para
#    3.11; antes dela 3.9 e o default de sistema desde 7.0.0. Para 6.x a AWS
#    nao reafirma o default do PySpark por release, entao a chave e OMITIDA:
#    `RuntimeContext.python` fica vazio e regra com `python` em `runtime_scope`
#    e pulada por ausencia. Escolher o maior da lista em silencio seria
#    inventar. `python_installed` fica registrado porque e fato conferido, mas
#    NAO deriva (ver `_DERIVABLE`).
#
# 3. ICEBERG NAO EXISTE ANTES DE 6.5.0, e a chave e OMITIDA em 6.4.0 --
#    nem `"0.0.0"` (afirma versao que nao existe) nem `""` (afirma leitura que
#    nao aconteceu). `in_scope` reprova chave ausente, entao SF-ICE-* ali e
#    pulada por AUSENCIA, nao por range.
#
# 4. `hadoop` E GUARDADO E NAO DERIVA. Nenhuma regra do catalogo tem `hadoop`
#    em `runtime_scope`, e `_DIRECT_KEYS` nao o coleta de fonte nenhuma -- um
#    campo em `RuntimeContext` so poderia receber valor de matriz, a forma mais
#    fraca do dado, e `to_dict()` passaria a emiti-lo em TODO golden com
#    `runtime` no payload. Custo sem consumidor. Fica na matriz porque e fato
#    conferido e porque o guard de drift compara a matriz contra a pagina de
#    knowledge, que tem a coluna.
EMR_MATRIX: dict[str, dict[str, Any]] = {
    "7.13.0": {
        "spark": "3.5.6-amzn-2",
        "hadoop": "3.4.2-amzn-0",
        "iceberg": "1.10.0-amzn-1",
        "python_installed": ("3.9", "3.11"),
        "python": "3.11",
    },
    "7.12.0": {
        "spark": "3.5.6-amzn-1",
        "hadoop": "3.4.1-amzn-4",
        "iceberg": "1.10.0-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.11.0": {
        "spark": "3.5.6-amzn-0",
        "hadoop": "3.4.1-amzn-3",
        "iceberg": "1.9.1-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.10.0": {
        "spark": "3.5.5-amzn-1",
        "hadoop": "3.4.1-amzn-2",
        "iceberg": "1.8.1-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.9.0": {
        "spark": "3.5.5-amzn-0",
        "hadoop": "3.4.1-amzn-1",
        "iceberg": "1.7.1-amzn-2",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.8.0": {
        "spark": "3.5.4-amzn-0",
        "hadoop": "3.4.1-amzn-0",
        "iceberg": "1.7.1-amzn-1",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.7.0": {
        "spark": "3.5.3-amzn-1",
        "hadoop": "3.4.0-amzn-3",
        "iceberg": "1.7.1-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.6.0": {
        "spark": "3.5.3-amzn-0",
        "hadoop": "3.4.0-amzn-2",
        "iceberg": "1.6.1-amzn-2",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.5.0": {
        "spark": "3.5.2-amzn-1",
        "hadoop": "3.4.0-amzn-1",
        "iceberg": "1.6.1-amzn-1",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.4.0": {
        "spark": "3.5.2-amzn-0",
        "hadoop": "3.4.0-amzn-0",
        "iceberg": "1.6.1-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.3.0": {
        "spark": "3.5.1-amzn-1",
        "hadoop": "3.3.6-amzn-5",
        "iceberg": "1.5.2-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.2.0": {
        "spark": "3.5.1-amzn-0",
        "hadoop": "3.3.6-amzn-4",
        "iceberg": "1.5.0-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.1.0": {
        "spark": "3.5.0-amzn-1",
        "hadoop": "3.3.6-amzn-3",
        "iceberg": "1.4.3-amzn-0",
        "python_installed": ("3.9", "3.11"),
        "python": "3.9",
    },
    "7.0.0": {
        "spark": "3.5.0-amzn-0",
        "hadoop": "3.3.6-amzn-2",
        "iceberg": "1.4.2-amzn-0",
        "python_installed": ("3.9",),
        "python": "3.9",
    },
    "6.15.0": {
        "spark": "3.4.1-amzn-2",
        "hadoop": "3.3.6-amzn-1",
        "iceberg": "1.4.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.14.0": {
        "spark": "3.4.1-amzn-1",
        "hadoop": "3.3.3-amzn-6",
        "iceberg": "1.3.1-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.13.0": {
        "spark": "3.4.1-amzn-0",
        "hadoop": "3.3.3-amzn-5",
        "iceberg": "1.3.0-amzn-1",
        "python_installed": ("2.7", "3.7"),
    },
    "6.12.0": {
        "spark": "3.4.0-amzn-0",
        "hadoop": "3.3.3-amzn-4",
        "iceberg": "1.3.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.11.1": {
        "spark": "3.3.2-amzn-0.1",
        "hadoop": "3.3.3-amzn-3.1",
        "iceberg": "1.2.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.11.0": {
        "spark": "3.3.2-amzn-0",
        "hadoop": "3.3.3-amzn-3",
        "iceberg": "1.2.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.10.1": {
        "spark": "3.3.1-amzn-0.1",
        "hadoop": "3.3.3-amzn-2.1",
        "iceberg": "1.1.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.10.0": {
        "spark": "3.3.1-amzn-0",
        "hadoop": "3.3.3-amzn-2",
        "iceberg": "1.1.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.9.1": {
        "spark": "3.3.0-amzn-1.1",
        "hadoop": "3.3.3-amzn-1.1",
        "iceberg": "0.14.1-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.9.0": {
        "spark": "3.3.0-amzn-1",
        "hadoop": "3.3.3-amzn-1",
        "iceberg": "0.14.1-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.8.1": {
        "spark": "3.3.0-amzn-0.1",
        "hadoop": "3.2.1-amzn-8.1",
        "iceberg": "0.14.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.8.0": {
        "spark": "3.3.0-amzn-0",
        "hadoop": "3.2.1-amzn-8",
        "iceberg": "0.14.0-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.7.0": {
        "spark": "3.2.1-amzn-0",
        "hadoop": "3.2.1-amzn-7",
        "iceberg": "0.13.1-amzn-0",
        "python_installed": ("2.7", "3.7"),
    },
    "6.6.0": {
        "spark": "3.2.0-amzn-0",
        "hadoop": "3.2.1-amzn-6",
        "iceberg": "0.13.1",
        "python_installed": ("2.7", "3.7"),
    },
    "6.5.0": {
        "spark": "3.1.2-amzn-1",
        "hadoop": "3.2.1-amzn-5",
        "iceberg": "0.12.0",
        "python_installed": ("2.7", "3.7"),
    },
    # Sem chave `iceberg`: a celula da pagina oficial e vazia. Ver decisao 3.
    "6.4.0": {
        "spark": "3.1.2-amzn-0",
        "hadoop": "3.2.1-amzn-4",
        "python_installed": ("2.7", "3.7"),
    },
}

# Precedencia de resolucao quando ha mais de uma fonte para o mesmo
# componente: event_log (Spark UI / event log do run) e o mais confiavel,
# depois cli (a flag que o operador digitou), depois terraform (glue_version,
# --datalake-formats). Ver knowledge/glue/runtime-matrix.md secao 5.
#
# `cli` estava FORA desta tupla e caia por ultimo por acidente de
# implementacao -- `_source_rank` empurra qualquer origem desconhecida para o
# fim --, nao por decisao. Declarada agora, e declarada ABAIXO de `event_log`:
# o event log e a unica fonte que OBSERVOU o runtime do run sob analise, com
# artefato, provenance e sha256; a flag e uma declaracao sem artefato. Quando o
# run reporta 3.5.4 e alguem digitou 3.3.0, quem sabe de si e o run. Acima de
# `terraform`, porem, porque ele tambem e declaracao (a intencao registrada no
# repositorio) e a flag e a declaracao mais especifica e mais recente -- o
# operador pode saber de uma mudanca aplicada no console que o IaC ainda nao
# reflete.
#
# Isto NAO e resolucao silenciosa, e nao pode virar. Perder a precedencia nunca
# apaga a observacao: todo valor lido continua entrando em `observations`, e
# qualquer discordancia continua virando `divergences` no RuntimeContext e um
# fact `env.runtime_signal` com `observed` completo -- o gatilho de SF-ENV-001
# em P0. A precedencia so escolhe o que o contexto REPORTA como valor
# resolvido; ela nao decide quem esta certo, e nunca descarta o outro valor.
#
# `describe_cluster` entrou na Fase 5b, ABAIXO de `event_log` e ACIMA de `cli`,
# espelhando exatamente a decisao ja tomada para `event_log` vs `terraform`:
# `Cluster.Applications[].Version` e a AWS reportando o que INSTALOU no cluster
# -- observacao com artefato, nao declaracao --, mas quem observou o RUN sob
# analise continua sendo so o event log. Acima de `cli`/`terraform` porque os
# dois sao declaracao de intencao.
#
# O extrator que produz esse dump e a Task 3 desta fase. A fonte fica declarada
# e funcionando desde ja, sem alimentador -- e esperado.
#
# `get_work_group` e o dump de `athena.get_work_group`, e entra COLADO em
# `describe_cluster` porque e a mesma classe de evidencia: uma API da AWS
# reportando o que esta em vigor, com artefato e sha256 atras --
# `engine_version.effective_engine_version` e a engine EFETIVA do workgroup,
# nao a pedida (`selected_engine_version`, que pode ser `AUTO`). Fica abaixo de
# `event_log` pela mesma razao que `describe_cluster`: quem observou o RUN sob
# analise e so o event log. Acima de `cli`/`terraform` porque os dois sao
# declaracao de intencao.
#
# A ordem RELATIVA entre `describe_cluster` e `get_work_group` nunca decide
# nada: os dois nunca disputam o mesmo componente. `describe_cluster` produz
# `emr_release`/`spark_version`/`iceberg_version`/`python_version` e jamais
# `athena_version`; `get_work_group` produz `athena_version` e mais nada. A
# adjacencia e agrupamento por natureza da evidencia, nao afirmacao de que um
# vence o outro.
#
# `requirements` ESTAVA AQUI, NO FIM, E SAIU -- decisao, nao esquecimento.
#
# Ela entrou na Fase 0 como produtor PREVISTO: `knowledge/glue/runtime-matrix.md`
# secao 5 lista `requirements.txt`/`pyproject.toml` como a fonte de MENOR
# confiabilidade ("indica intencao, nao runtime"), e a tupla foi desenhada com
# ela no fim por isso. Sobreviveu quatro fases sem extrator -- nenhum modulo de
# `sparkforge/facts/` le manifesto de dependencia --, e a triagem de dividas
# mediu os dois caminhos antes de escolher.
#
# O QUE DECIDIU, e e medicao, nao gosto. Com
# `{"terraform": {"glue_version": "4.0"}, "requirements": {"spark_version": "3.5.1"}}`
# o motor devolve `RuntimeContext.spark == "3.5.1"` e uma divergencia. As duas
# metades estao erradas, e nenhuma delas se conserta com um extrator:
#
# 1. A POSICAO NO FIM DA TUPLA NAO PROTEGE NADA. `_resolve` prefere observacao
#    DIRETA a derivacao `:matrix`, e so DEPOIS desempata por `_source_rank`.
#    Uma leitura de manifesto e direta por construcao, entao a fonte de menor
#    confiabilidade do projeto vence a derivacao da matriz oficial a partir de
#    um `glue_version` observado no Terraform -- e alimenta `runtime_scope` de
#    toda regra versionada. E o oposto exato da disciplina que a Fase 5b
#    declarou ("observacao direta vence a matriz"): aqui o que vence a matriz e
#    declaracao sem artefato.
# 2. `distinct_versions` sai 2, e isso e SF-ENV-001 em P0 sobre `pyspark==3.5.1`
#    fixado para teste local num job que roda em Glue 4.0 -- configuracao
#    NORMAL, nao contradicao. E o mesmo P0 falso que `_UNANIMOUS_SOURCES`
#    recusou para multiplos workgroups do Athena, e falso P0 treina o operador
#    a ignorar o canal de divergencia.
#
# E o que sobraria de honesto para ler e quase nada: `pyspark` no manifesto e a
# versao de teste local (o runtime embarca a sua, e instala-la pelo
# `--additional-python-modules` e defeito, nao declaracao de runtime),
# `requires-python` e FAIXA e nao versao, e `pyiceberg` e outro artefato que nao
# o jar de Iceberg do cluster.
#
# PARA VOLTAR sao tres capacidades independentes, e o extrator e a menor delas:
# (a) o extrator; (b) uma classe de rank nova em `_resolve` -- "declaracao de
# intencao nunca vence derivacao de observacao" --, que mexe na resolucao de
# TODAS as fontes; (c) supressao de divergencia para essa classe, no molde de
# `_UNANIMOUS_SOURCES`. A secao 5 do knowledge continua listando o manifesto, e
# ali ele e o que sempre foi: orientacao para um HUMANO, que sabe pesar "indica
# intencao". O motor nao tem classe de rank para intencao, e inventar uma para
# uma fonte que quase nada pode dizer e custo sem consumidor.
#
# Sair da tupla NAO e recriar o acidente que a Fase 5a.2 fechou com `cli`
# (origem desconhecida caindo por ultimo por implementacao, nao por decisao):
# `_source_rank` de fato continua jogando nome desconhecido para o fim, mas a
# decisao registrada aqui nao e "ela ranqueia por ultimo" -- e que ela nao
# existe como fonte. `TestNoPrecedenceSourceIsAnUndeclaredProducerGap` trava:
# nome nesta tupla exige alguem que o emita.
_PRECEDENCE: tuple[str, ...] = (
    "event_log",
    "describe_cluster",
    "get_work_group",
    "cli",
    "terraform",
)

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

# O que uma matriz pode virar observacao. `hadoop` e `python_installed` estao
# na EMR_MATRIX como fato conferido e ficam de fora daqui de proposito: nao ha
# campo em `RuntimeContext` nem chave em `_DIRECT_KEYS` para eles, e derivar
# valor que nada consome so acrescentaria ruido ao contexto e a todo golden.
_DERIVABLE = frozenset(_DIRECT_KEYS)

# (valor, origem). origem e o nome da fonte, ou "<fonte>:matrix" quando o
# valor foi inferido de GLUE_MATRIX/EMR_MATRIX em vez de lido diretamente.
_Observation = tuple[str, str]


def _emr_key(value: str) -> str:
    """`emr-7.5.0` e `7.5.0` sao a mesma release. Chave da matriz e a segunda.

    O release label e o que o `describe-cluster` e o Terraform carregam; o
    numero solto e o que alguem digita. As duas grafias tem que achar a mesma
    linha, senao metade das deteccoes cai no fallback vazio em silencio.
    """
    text = str(value).strip()
    lowered = text.lower()
    return text[4:] if lowered.startswith("emr-") else text


def _apache_version(version: str) -> str:
    """`3.3.2-amzn-0.1` -> `3.3.2`. So para COMPARAR; nunca para reportar.

    Espelha o truncamento de `sparkforge.rules.version_scope._parse` sem
    importa-lo -- `facts/` nao depende de `rules/`. O teste
    `test_apache_version_agrees_with_version_scope` percorre a EMR_MATRIX
    inteira e falha se as duas implementacoes divergirem em qualquer celula.

    O valor CRU nunca e substituido por este: ele continua em
    `RuntimeContext.spark`, em `attrs.observed` e no texto de divergencia,
    porque o sufixo `-amzn-N` e informacao real sobre o runtime -- descarta-la
    esconderia que o cluster roda um fork da AWS, nao o artefato da Apache.
    """
    return str(version).split("-", 1)[0].strip()


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


# Como comparar DUAS GRAFIAS da mesma identidade antes de chamar a diferenca de
# divergencia. So `emr` precisa: `emr-7.5.0` (o que o dump e o Terraform
# carregam) e `7.5.0` (o que alguem digita em `--emr`) sao a MESMA release, e
# contar as duas strings como identidades distintas transformaria uma flag que
# CONCORDA com o dump num SF-ENV-005 em P0 -- ruido que treina o operador a
# ignorar o canal de divergencia, que e o oposto do que ele existe para fazer.
# `glue` nao entra porque nao tem segunda grafia; `platform` compara nomes de
# plataforma, que ja sao vocabulario fechado.
#
# A normalizacao vale so para CONTAR. `_divergence_text` continua imprimindo o
# valor cru de cada fonte: quando ha divergencia de verdade, o operador precisa
# ver exatamente o que cada fonte disse, nao a forma normalizada.
_IDENTITY_NORMALIZE: dict[str, Any] = {"emr": _emr_key}


def _distinct_identities(component: str, observations: list[_Observation]) -> list[str]:
    normalize = _IDENTITY_NORMALIZE.get(component)
    if normalize is None:
        return _distinct_values(observations)
    return sorted({normalize(value) for value, _ in observations})


def _divergent_count(
    component: str,
    observations: list[_Observation],
    derived: dict[str, dict[str, list[_Observation]]],
) -> int:
    """Quantas VERSOES distintas as fontes atribuem a este componente.

    Duas diferencas em relacao a `len(_distinct_values(...))`, e as duas
    existem para nao transformar um defeito ja reportado num segundo P0 com o
    remedio errado:

    1. CONTA VERSAO APACHE, nao string crua. `3.3.0` (derivado de Glue 4.0) e
       `3.3.0-amzn-1` (derivado de emr-6.9.0) sao o mesmo Spark com patches
       diferentes, nao duas versoes divergentes. `attrs.observed` continua
       listando as duas strings cruas -- e por isso que `observed` pode ter
       mais entradas do que `distinct_versions`: uma responde "o que foi
       lido", a outra "quantas versoes sao".

    2. COMPARA POR PLATAFORMA. Quando Glue e EMR sao detectados juntos, as duas
       matrizes derivam valores para o mesmo componente e eles quase sempre
       discordam -- nao ha release de EMR que case com Glue 4.0 em Spark E
       Iceberg. Contar isso como divergencia de versao mandaria o operador
       "alinhar o Terraform a versao efetiva" quando o remedio e remover o
       artefato que nao e deste job. Multiplicidade de plataforma tem regra
       propria, SF-ENV-005, tambem P0. Entao cada plataforma e conferida
       contra as observacoes DIRETAS e contra as derivacoes dela mesma, nunca
       contra as da outra -- e observacao direta nunca e excluida, porque ela
       nao depende de nenhuma matriz para existir.
    """
    direct = {
        _apache_version(value)
        for value, origin in observations
        if not origin.endswith(":matrix")
    }
    views = [
        direct | {_apache_version(value) for value, _ in rows[component]}
        for rows in derived.values()
        if rows.get(component)
    ]
    return max(len(view) for view in views) if views else len(direct)


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


def _matrix_row(platform: str, value: str) -> dict[str, Any] | None:
    if platform == "glue":
        return GLUE_MATRIX.get(value)
    if platform == "emr":
        return EMR_MATRIX.get(_emr_key(value))
    return None


def _collect(
    sources: dict[str, dict[str, Any]],
) -> tuple[
    dict[str, list[_Observation]],
    dict[str, list[_Observation]],
    set[str],
    dict[str, dict[str, list[_Observation]]],
]:
    platforms: dict[str, list[_Observation]] = defaultdict(list)
    observations: dict[str, list[_Observation]] = defaultdict(list)
    detected_from: set[str] = set()
    # plataforma -> componente -> observacoes derivadas DAQUELA matriz.
    # Existe so para `_divergent_count`: sem saber de qual matriz cada valor
    # derivado veio, nao ha como comparar cada plataforma consigo mesma.
    derived: dict[str, dict[str, list[_Observation]]] = defaultdict(
        lambda: defaultdict(list)
    )

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
                row = _matrix_row(platform, value)
                if row:
                    origin = f"{source_name}:matrix"
                    for component in sorted(_DERIVABLE & set(row)):
                        pair = (str(row[component]), origin)
                        observations[component].append(pair)
                        derived[platform][component].append(pair)
                break

        for component, keys in _DIRECT_KEYS.items():
            for key in keys:
                value = data.get(key)
                if value:
                    observations[component].append((str(value), source_name))
                    detected_from.add(source_name)
                    break

    return platforms, observations, detected_from, derived


def _build_context(
    platforms: dict[str, list[_Observation]],
    observations: dict[str, list[_Observation]],
    detected_from: set[str],
    derived: dict[str, dict[str, list[_Observation]]],
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

    # `glue`, `emr` e `platform` nao passam por matriz nenhuma: sao a propria
    # identidade lida da fonte, e ali string crua distinta E divergencia.
    identity = {"glue", "emr", "platform"}
    divergences = [
        _divergence_text(name, all_components[name])
        for name in sorted(all_components)
        if (
            len(_distinct_identities(name, all_components[name])) > 1
            if name in identity
            else _divergent_count(name, all_components[name], derived) > 1
        )
    ]

    # `emr` guarda a release NUMERICA, nao o label. `RuntimeContext` existe para
    # ser comparado: `in_scope({"emr": ">=7.0"}, ...)` roda `_parse` sobre este
    # valor, e `_parse("emr-7.5.0")` le `emr` como 0 -- o range nunca casa, a
    # regra e pulada, e a cobertura some em silencio. E o mesmo modo de falha que
    # as Fases 5a e 5a.2 fecharam, e o curinga `"*"` nao o revela porque so checa
    # presenca. `glue` ja faz assim: guarda `5.0`, nunca `Glue 5.0`.
    # O label observado nao se perde -- sobrevive em `env.platform.attrs.observed`,
    # que e onde artefato bruto pertence.
    emr_resolvido = _resolve(platforms.get("emr", []))

    return RuntimeContext(
        glue=_resolve(platforms.get("glue", [])),
        emr=_emr_key(emr_resolvido) if emr_resolvido else "",
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
    derived: dict[str, dict[str, list[_Observation]]],
) -> list[Fact]:
    facts: list[Fact] = []

    platform_fact = _platform_fact(platforms)
    if platform_fact is not None:
        facts.append(platform_fact)

    for component in sorted(observations):
        obs = observations[component]
        distinct = _distinct_values(obs)
        count = _divergent_count(component, obs, derived)
        has_direct = any(not origin.endswith(":matrix") for _, origin in obs)
        # A condicao de emissao usa a MESMA contagem que a medida. Usar
        # `len(distinct)` aqui faria duas matrizes de plataformas diferentes
        # emitirem um fact de iceberg cujo `distinct_versions` e 1 -- um fact
        # que nao dispara nada e que ninguem sabe ler.
        if component not in _ALWAYS_EMIT and not has_direct and count <= 1:
            continue

        resolved = _resolve(obs)
        source_count = len({origin.split(":", 1)[0] for _, origin in obs})
        measures = {"distinct_versions": count, "source_count": source_count}
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

    `sources` mapeia nome da fonte (ex.: "event_log", "describe_cluster",
    "get_work_group", "terraform") para um dict com chaves cruas: `glue_version`,
    `emr_release`/`emr_version`/`emr`, `spark_version`/`spark`,
    `python_version`/`python`, `iceberg_version`/`iceberg`,
    `athena_version`/`athena`.

    `glue_version` deriva spark/python/iceberg por `GLUE_MATRIX`;
    `emr_release` deriva spark/iceberg -- e python so em 7.x -- por
    `EMR_MATRIX`. Derivacao sempre perde para leitura direta, e o
    `PYSPARK_PYTHON` da classificacao `spark-env` chega como `python_version`.

    Nao le nada do disco nem de rede -- `sources` ja vem coletado
    (coleta e Task 22). Entrada vazia ou com valores None/vazios nao
    levanta excecao: apenas produz um RuntimeContext vazio e nenhum fact.
    """
    platforms, observations, detected_from, derived = _collect(sources or {})
    context = _build_context(platforms, observations, detected_from, derived)
    facts = _build_facts(platforms, observations, derived)
    return context, sort_facts(facts)
