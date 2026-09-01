"""Logica compartilhada entre a CLI (`cli.py`) e a superficie MCP (`tools.py`).

Adaptador fino: nenhuma funcao aqui decide limiar, severidade ou rota. Tudo
delega para `sparkforge.facts`, `sparkforge.rules`, `sparkforge.case` e
`sparkforge.findings`. Isto existe para que a CLI e o servidor MCP nunca
divirjam -- os dois chamam exatamente as mesmas funcoes deste modulo.

`AdapterError` e o unico tipo de erro que atravessa a fronteira do adaptador:
`cli.py` o traduz em (stderr, exit code); `tools.py` o traduz em um dict
`{"error": ...}`. Erros de baixo nivel (`CaseError`, `CatalogError`,
`ValidationFailed`) sao capturados aqui e reembalados, nunca vazam crus.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from sparkforge.capacity import build_capacity_plan
from sparkforge.case import router, store
from sparkforge.case.playbook import build_playbook
from sparkforge.case.resume import render_handoff
from sparkforge.case.resume import resume as run_resume
from sparkforge.codeintel import budget as _codeintel_budget
from sparkforge.codeintel import context as _codeintel_context
from sparkforge.codeintel import db as _codeintel_db
from sparkforge.codeintel import graph as _codeintel_graph
from sparkforge.codeintel import ranking as _codeintel_ranking
from sparkforge.codeintel import search as _codeintel_search
from sparkforge.codeintel import security as _codeintel_security
from sparkforge.codeintel import staleness as _codeintel_staleness
from sparkforge.collect import aws as collect_aws
from sparkforge.collect.base import CollectorUnavailable, verify_all
from sparkforge.controlm.descriptor import (
    UnknownVersion as UnknownControlMVersion,
)
from sparkforge.controlm.descriptor import (
    describe as describe_controlm,
)
from sparkforge.controlm.descriptor import (
    known_versions as known_controlm_versions,
)
from sparkforge.controlm.matrix import (
    BOUNDARIES as _CONTROLM_BOUNDARIES,
)
from sparkforge.controlm.matrix import (
    covers as controlm_covered_range,
)
from sparkforge.economy.report import build_context_report
from sparkforge.facts.athena_workgroup import (
    extract_athena_workgroup_path,
    extract_athena_workgroup_tree,
)
from sparkforge.facts.benchmark import build_benchmark
from sparkforge.facts.call_graph import build_call_graph
from sparkforge.facts.catalog_schema import (
    extract_catalog_schema_path,
    extract_catalog_schema_tree,
)
from sparkforge.facts.cloudwatch import extract_cloudwatch_path
from sparkforge.facts.consumers import extract_consumers_path, extract_consumers_tree
from sparkforge.facts.controlm_jobs import (
    extract_controlm_jobs_path,
    extract_controlm_jobs_tree,
)
from sparkforge.facts.data_quality import (
    extract_data_quality_path,
    extract_data_quality_tree,
)
from sparkforge.facts.emr_cluster import extract_emr_cluster_path, extract_emr_cluster_tree
from sparkforge.facts.emr_eks import extract_emr_eks_path, extract_emr_eks_tree
from sparkforge.facts.emr_serverless import (
    extract_emr_serverless_path,
    extract_emr_serverless_tree,
)
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.funcval import build_comparison, build_plan
from sparkforge.facts.fusion import fuse as run_fuse
from sparkforge.facts.glue_job_run import extract_glue_job_runs_path
from sparkforge.facts.graph import extract_graph_path, extract_graph_tree
from sparkforge.facts.iceberg_metadata import (
    extract_iceberg_metadata_path,
    extract_iceberg_metadata_tree,
)
from sparkforge.facts.pyspark_ast import extract_path, extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.s3_listing import extract_s3_listing_path, extract_s3_listing_tree
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.facts.sql_literal import extract_sql_from_pyspark, extract_sql_path
from sparkforge.facts.sql_metrics import extract_sql_metrics_path
from sparkforge.facts.terraform import (
    extract_terraform_diff,
    extract_terraform_path,
    extract_terraform_tree,
)
from sparkforge.findings import signature as _signature
from sparkforge.findings.models import Fact, RuntimeContext, sort_facts
from sparkforge.findings.signature import SIGNATURE_RE, compute_signature
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.finops import build_finops_report
from sparkforge.knowledge_ref import KnowledgeError, knowledge_dir, safe_knowledge_file
from sparkforge.migration.assessment import assess as assess_migration
from sparkforge.migration.collect import collect as collect_migration
from sparkforge.migration.release_descriptor import (
    PLATFORMS as RELEASE_PLATFORMS,
)
from sparkforge.migration.release_descriptor import (
    UNRESOLVED_KINDS as _RELEASE_UNRESOLVED_KINDS,
)
from sparkforge.migration.release_descriptor import (
    ReleaseDescriptor,
    UnknownPlatform,
    UnknownRelease,
)
from sparkforge.migration.release_descriptor import (
    describe as describe_release,
)
from sparkforge.migration.release_descriptor import (
    known_releases as known_releases_of,
)
from sparkforge.migration.release_diff import diff as diff_releases
from sparkforge.migration.version_path import (
    DEFAULT_PLATFORM as MIGRATION_DEFAULT_PLATFORM,
)
from sparkforge.observability.context_ledger import shared_ledger
from sparkforge.rules.engine import judge as run_judge
from sparkforge.rules.loader import CatalogError, load_catalog
from sparkforge.storage.upgrade import assess_upgrade as assess_iceberg_upgrade
from sparkforge.tuning import build_conf_advice
from sparkforge.workload import build_fingerprint

DEFAULT_LIMIT = 50

# Reexportado para que `tools.py` derive o `enum` do schema DO MODELO, e nunca
# de uma lista escrita a mao ao lado -- que e a familia de defeito que este
# repositorio ja mediu em duas listas paralelas de extrator.
RELEASE_UNRESOLVED_KINDS: frozenset[str] = _RELEASE_UNRESOLVED_KINDS

# Pela MESMA razao, e num caso em que a lista paralela seria especialmente
# convidativa: as quatro fronteiras do Control-M sao curtas e faceis de
# redigitar no `enum` do schema, e uma quinta que entrasse no modelo nunca
# chegaria la. `matrix.BOUNDARIES` e a unica lista.
CONTROLM_BOUNDARIES: tuple[str, ...] = _CONTROLM_BOUNDARIES


class AdapterError(Exception):
    """Erro acionavel de fronteira: mensagem pronta para stderr ou para um
    dict `{"error": ...}`, mais o exit code que a CLI deve devolver."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def _count_by(items: list[Any], keyfn: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = keyfn(item)
        counts[key] = counts.get(key, 0) + 1
    return counts


def paginate_items(
    items: list[Any], limit: int | None, cursor: str | None
) -> tuple[list[Any], str | None]:
    """Fatia `items` (ja filtrado) em uma pagina. `limit=None` devolve tudo.

    Cursor e um offset inteiro codificado como string -- suficiente porque a
    ordenacao upstream (sort_facts/sort_findings/ordem do catalogo) ja e
    deterministica, entao o mesmo cursor sempre reproduz a mesma pagina.
    """
    try:
        start = int(cursor) if cursor else 0
    except ValueError as exc:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2) from exc
    if start < 0:
        raise AdapterError(f"cursor invalido: {cursor!r}", exit_code=2)

    if limit is None:
        return items[start:], None

    end = start + limit
    page = items[start:end]
    next_cursor = str(end) if end < len(items) else None
    return page, next_cursor


NIVEIS_DE_DETALHE: tuple[str, ...] = ("summary", "normal", "full")

# Campos do fact que sobrevivem a `summary` sem mudar de forma. `subject` NAO
# esta aqui: ele e reduzido a `at` (arquivo:linha) e `symbol` logo abaixo.
_CAMPOS_DE_SUMARIO: tuple[str, ...] = ("id", "kind", "measures")

# Quantos hex chars do digest viram a chave de procedencia. Isto e FORMATO DE
# FIO, nao detalhe interno: `provenance_ref` cita esta chave, e encurtar
# aumenta a chance de duas procedencias diferentes caírem na mesma. Esta
# constante existe para que um teste possa fixá-la.
TAMANHO_DA_CHAVE_DE_PROCEDENCIA = 16


def _canonico(valor: Any) -> str:
    return json.dumps(valor, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def chave_de_procedencia(prov: dict[str, Any]) -> str:
    """Chave de `prov`, derivada SO do conteudo de `prov`.

    Ser funcao pura do conteudo e o ponto inteiro, e a versao anterior errava
    exatamente aqui. Ela derivava a chave do `artifact_sha256` e desempatava
    com um sufixo numerado quando duas procedencias colidiam -- mas a projecao
    roda DEPOIS de paginar, sobre UMA pagina, entao o desempate so valia dentro
    daquela pagina. Reproduzido com `fuse` de py+sql em paginas de 9: a chave
    `7322f5e505a6` apontava para `pyspark_ast` na pagina 1 e para `sql_literal`
    na pagina 2. Quem pagina pelo `next_cursor` e une os mapas -- que e o unico
    jeito de consumir resultado paginado -- atribuia o fato ao extrator errado,
    sem erro nenhum.

    Derivando do conteudo, a mesma procedencia recebe a mesma chave em qualquer
    pagina, em qualquer execucao e em qualquer verbo, por construcao. Nao ha
    estado entre paginas para manter coerente, porque nao ha estado.

    O digest e truncado em `TAMANHO_DA_CHAVE_DE_PROCEDENCIA` (16 hex chars, 64
    bits) porque a chave inteira apareceria uma vez por item em
    `provenance_ref` e comeria a economia que `normal` existe para dar. Duas
    procedencias diferentes so colidem se os 64 primeiros bits do sha256
    coincidirem; DENTRO de uma pagina isso e detectado e vira erro
    (`project_items`), ENTRE paginas nao ha como detectar -- e o risco residual
    declarado desta escolha.

    sha256 aqui e content-addressing, nao uso criptografico: identifica de que
    artefato o fato veio para que a mesma procedencia produza a mesma chave.
    """
    digest = hashlib.sha256(_canonico(prov).encode("utf-8")).hexdigest()
    return digest[:TAMANHO_DA_CHAVE_DE_PROCEDENCIA]


def _resumir(item: dict[str, Any]) -> dict[str, Any]:
    """Reduz um fact ao que responde "o que" e "onde".

    `symbol` e campo proprio, e nao concatenado dentro de `at`, porque os dois
    respondem coisas diferentes e nem sempre existem juntos. Medido nas
    fixtures: todo fact de `catalog.table_*` tem `subject.symbol` (o nome da
    tabela) e NENHUM tem `subject.line` -- num dump com varias tabelas, tres
    facts do mesmo kind teriam o mesmo `at` (`dump.json`) e so `symbol` os
    distingue. Enfiar o simbolo dentro de `at` produziria `dump.json db.eventos`,
    string sem gramatica, que o consumidor teria de adivinhar onde corta.
    """
    sujeito = item.get("subject") or {}
    novo = {c: item[c] for c in _CAMPOS_DE_SUMARIO if item.get(c)}
    local = f"{sujeito.get('file', '')}:{sujeito.get('line', '')}".strip(":")
    if local:
        novo["at"] = local
    if sujeito.get("symbol"):
        novo["symbol"] = sujeito["symbol"]
    return novo


def project_items(
    items: list[dict[str, Any]], detail_level: str
) -> tuple[list[dict[str, Any]], dict[str, Any], int | None]:
    """`(itens_projetados, procedencias, schema_version)` para o nivel pedido.

    `full` devolve exatamente o que sempre devolveu. Todo chamador (CLI, MCP,
    as funcoes deste modulo) passa `full` por default, e isso e DE PROPOSITO:
    outro default mudaria a saida de todo chamador existente e de todo golden
    test de uma vez so, e isso e decisao de contrato, separada desta fase.
    `full` tambem e o modo de reauditoria -- quem confere um finding precisa do
    fato inteiro, nao de um resumo.

    `normal` tira do item o que se REPETE e declara uma vez no envelope: a
    procedencia (referenciada por `provenance_ref`) e o `schema_version`. Os
    dois sao repeticao pela mesma razao, e por isso saem pelo mesmo caminho --
    tirar so um e chamar isso de "declarar a procedencia uma vez" seria
    descrever mal a propria economia. Medido na fixture `clean_job`: a
    procedencia inline respondia por 25,1% do payload.

    `summary` reduz o item ao que responde "o que" e "onde" (ver `_resumir`).

    Nada e apagado em silencio. A procedencia continua no envelope nos dois
    niveis, e o `schema_version` tambem -- QUANDO todos os itens da pagina
    concordam. Se divergirem (possivel em `fuse`, que le facts de arquivos
    gerados em momentos diferentes), cada item mantem o proprio e o envelope
    nao declara nenhum: um numero so no envelope estaria mentindo sobre metade
    da pagina. Economia que apaga rastreabilidade e defeito, nao compressao.

    Esta projecao e definida sobre o shape de FACT (`Fact.to_dict`). Findings
    (`judge`) e regras (`rules_lookup`) tem outro shape -- sem `provenance`,
    e sem `id`/`kind`/`measures` no caso do finding -- e por isso nao passam
    por aqui: aplicar `summary` a um finding devolveria um dict vazio.
    """
    if detail_level not in NIVEIS_DE_DETALHE:
        raise AdapterError(
            f"detail_level invalido: {detail_level!r}; use um de {NIVEIS_DE_DETALHE}",
            exit_code=2,
        )
    if detail_level == "full":
        return items, {}, None

    versoes = {item.get("schema_version") for item in items}
    versao_comum = versoes.pop() if len(versoes) == 1 else None
    if not isinstance(versao_comum, int):
        versao_comum = None

    procedencias: dict[str, Any] = {}
    projetados: list[dict[str, Any]] = []
    for item in items:
        prov = item.get("provenance")
        chave = ""
        if prov:
            chave = chave_de_procedencia(prov)
            anterior = procedencias.get(chave)
            if anterior is not None and anterior != prov:
                raise AdapterError(
                    "colisao de chave de procedencia: "
                    f"{chave!r} ja aponta para {_canonico(anterior)} e "
                    f"tambem seria a chave de {_canonico(prov)}",
                    exit_code=1,
                )
            procedencias[chave] = prov

        if detail_level == "normal":
            descartar = {"provenance"} if versao_comum is None else {"provenance", "schema_version"}
            novo = {k: v for k, v in item.items() if k not in descartar}
        else:
            novo = _resumir(item)
            if versao_comum is None and item.get("schema_version") is not None:
                novo["schema_version"] = item["schema_version"]
        if chave:
            novo["provenance_ref"] = chave
        projetados.append(novo)
    return projetados, procedencias, versao_comum


def declarar_no_envelope(
    envelope: dict[str, Any], procedencias: dict[str, Any], schema_version: int | None
) -> dict[str, Any]:
    """Escreve no envelope o que `project_items` tirou de dentro dos itens.

    Existe para que os cinco pontos de envelope (os quatro deste modulo mais o
    da CLI) nao repitam a decisao de QUAIS chaves sobem. Acrescentar uma coisa
    que sai do item e passar a esquecer de declara-la em um dos cinco foi
    exatamente como o `schema_version` sumiu em silencio da primeira versao.
    """
    if procedencias:
        envelope["provenance"] = procedencias
    if schema_version is not None:
        envelope["schema_version"] = schema_version
    return envelope


# --------------------------------------------------------------------------- #
# runtime a partir dos facts
# --------------------------------------------------------------------------- #

# FRONTEIRA NEGATIVA -- o coracao deste modulo, e nao negociavel.
#
# Derivar runtime dos facts e LER o que um extrator ja OBSERVOU, com artefato,
# linha e sha256 atras. Nada aqui adivinha versao a partir de sinal indireto:
# nem sintaxe de API ("usou `df.observe`, logo Spark >= 3.3"), nem nome de
# bucket, nem presenca de import, nem heuristica de qualquer outra especie.
# Se nenhum fact carrega a versao, o campo fica VAZIO e a regra versionada e
# pulada com `reason: runtime_scope` -- isso e o comportamento correto, nao uma
# lacuna a ser preenchida por palpite. Inferir versao de sintaxe seria
# julgamento entrando na camada de fato, que e o inimigo declarado da secao 1
# do spec da Fase 0: fato e o que tem artefato; o resto precisa de mecanismo
# proprio, com garantia declarada.
#
# A unica inferencia permitida e a que `detect_runtime` ja faz e ja documenta:
# `GLUE_MATRIX`, a matriz oficial de compatibilidade. Sabendo `glue_version`
# (observado no Terraform), spark/python/iceberg saem da tabela publicada da
# AWS, nao de palpite -- e ficam marcados como `:matrix` para nunca vencerem
# uma leitura direta.

# `python3.11`, e SO essa forma. O nome do executavel do CPython carrega o
# minor por construcao -- `python3.11` e o binario do 3.11 em `/usr/bin`, no
# `bin/` de um venv (criado com o nome do interpretador base) e no de um env
# conda. Ler dai nao e inferir de sinal indireto; e decodificar um nome que
# JA declara a versao.
#
# O que esta regex NAO casa, de proposito, porque emitir errado aqui e pior que
# nao emitir -- a leitura entra como `describe_cluster`, ACIMA da matriz e da
# flag em `_PRECEDENCE`, e versao errada com precedencia alta alimenta
# `runtime_scope`:
#
#   `/usr/bin/python3`   -- so o MAJOR. `"3"` seria lido por `version_scope`
#                           como 3.0.0, afirmando um Python que nao existe em
#                           EMR nenhum. Em 6.x pode ser 3.7, em 7.x 3.9 ou
#                           3.11, e o caminho nao distingue.
#   `/usr/bin/python`    -- nem o major.
#   `/opt/venv/bin/run`  -- wrapper com nome arbitrario: o nome nao afirma nada.
#   `/usr/bin/env python3.11` -- forma com argumento; o nome do executavel e
#                           `env`, e o resto e parsing de linha de comando.
#
# Nesses casos `RuntimeContext.python` continua vazio e regra com `python` em
# `runtime_scope` e pulada por ausencia -- falha fechada, que e a semantica do
# projeto para "nao detectada", e o que a fixture `emr/*/input/cluster.json`
# (com `/usr/bin/python3`) exercita.
_PYSPARK_INTERPRETER_RE = re.compile(r"^python(\d+\.\d+)$")


def _python_minor_from_interpreter(value: str) -> str:
    """`/usr/bin/python3.11` -> `3.11`. Qualquer forma ambigua -> `""`."""
    name = value.strip().rsplit("/", 1)[-1]
    match = _PYSPARK_INTERPRETER_RE.match(name)
    return match.group(1) if match else ""


# fact -> (fonte de `detect_runtime`, chave crua, valor). Uma entrada nova aqui
# exige LER o extrator que emite o kind: o mapeamento e um contrato com o
# formato exato dos attrs, nao um palpite sobre o nome do campo.
def _runtime_reading(fact: Fact) -> tuple[str, str, str] | None:
    """Leitura de versao que ESTE fact carrega, ou None.

    `spark.runtime_version` vem de `SparkListenerLogStart`, a primeira linha do
    event log, escrita pelo proprio EventLoggingListener -- ver
    `sparkforge/facts/event_log.py`. `attrs.component` espelha o vocabulario de
    `env.runtime_signal` de proposito, entao a checagem e direta.

    `tf.attribute` com `key == "glue_version"` so conta quando e literal e esta
    na raiz do `resource "aws_glue_job"`. Nao-literal significa `var.x` /
    `local.x`: o extrator guarda o TEXTO da referencia em `attrs.value`, e
    trata-lo como versao gravaria "var.glue_version" no contexto. Fora da raiz
    significa uma chave homonima dentro de `default_arguments`, que e argumento
    de job, nao a versao do runtime.
    """
    if fact.kind == "spark.runtime_version":
        if fact.attrs.get("component") != "spark":
            return None
        version = str(fact.attrs.get("version") or "").strip()
        return ("event_log", "spark_version", version) if version else None

    if fact.kind == "tf.attribute" and fact.attrs.get("key") == "glue_version":
        if not fact.attrs.get("literal") or fact.attrs.get("block") != "root":
            return None
        value = str(fact.attrs.get("value") or "").strip()
        return ("terraform", "glue_version", value) if value else None

    # `emr.cluster` carrega o `ReleaseLabel` que a AWS reporta para AQUELE
    # cluster. E a chave de plataforma de `_PLATFORM_KEYS` e a entrada da
    # EMR_MATRIX ao mesmo tempo: sem ela, `RuntimeContext.emr` fica vazio e
    # toda regra com `emr` em `runtime_scope` e pulada num cluster que o dump
    # descreve inteiro.
    if fact.kind == "emr.cluster":
        label = str(fact.attrs.get("release_label") or "").strip()
        return ("describe_cluster", "emr_release", label) if label else None

    # `Applications[].Version` e a AWS dizendo o que INSTALOU -- observacao com
    # artefato, nao derivacao. Por isso `describe_cluster` esta acima da matriz
    # em `_PRECEDENCE`: a matriz e fallback e guard de drift, e uma versao
    # observada que discorde dela vira divergencia registrada, nunca um valor
    # substituido em silencio. So Spark e Iceberg entram: Hadoop e Hive nao tem
    # campo em `RuntimeContext`, e inventar um so para guardar o valor seria
    # custo sem consumidor (mesma decisao de `hadoop` na EMR_MATRIX).
    if fact.kind == "emr.application":
        component = str(fact.attrs.get("name") or "").strip().lower()
        version = str(fact.attrs.get("version") or "").strip()
        # A chave crua e NOMEADA, nao montada por `f"{component}_version"`. As
        # duas formas produzem exatamente as mesmas duas strings, mas so esta
        # deixa `spark_version` e `iceberg_version` VISIVEIS no corpo da funcao
        # -- e `TestNoRuntimeAxisIsAnUndeclaredProducerGap` deriva os eixos com
        # produtor exatamente dai. Chave montada em tempo de execucao e um eixo
        # que o invariante nao consegue ver.
        key = {"spark": "spark_version", "iceberg": "iceberg_version"}.get(component)
        if not version or key is None:
            return None
        return ("describe_cluster", key, version)

    # `spark-env`/`PYSPARK_PYTHON` e o UNICO lugar do dump onde o Python que o
    # PySpark executa aparece. A coluna `Python` da pagina de release lista os
    # interpretadores INSTALADOS (`2.7, 3.7` em 6.x), e por isso a EMR_MATRIX
    # omite `python` na serie 6.x inteira -- escolher um dos dois seria
    # inventar. Existia o dado e existia o consumidor, e nada ligava os dois.
    #
    # SO NIVEL CLUSTER. Uma propriedade de instance group vale para AQUELE
    # grupo, e `emr.configuration.unapplied` existe justamente porque a
    # configuracao de grupo no dump e a PEDIDA, que pode nao estar em vigor.
    # Leitura de runtime a partir de configuracao que talvez nao vigore seria
    # afirmar sobre o cluster o que nao se sabe nem sobre o grupo.
    if fact.kind == "emr.configuration":
        if fact.attrs.get("key") != "PYSPARK_PYTHON" or fact.attrs.get("level") != "cluster":
            return None
        version = _python_minor_from_interpreter(str(fact.attrs.get("value") or ""))
        return ("describe_cluster", "python_version", version) if version else None

    # `athena.workgroup.measures.engine_version` e a geracao da engine que o
    # workgroup EXECUTA -- `effective_engine_version`, nunca a pedida
    # (`selected_engine_version`, que pode ser `AUTO`) --, ja convertida em
    # inteiro por `athena_workgroup._parse_engine_version`, que nunca fabrica
    # default: string que ele nao entende vira `athena.unresolved`, nao um
    # numero. Existia o dado, com artefato e sha256, e existia o consumidor
    # (`RuntimeContext.athena`, so preenchivel pela flag `--athena` ate aqui).
    #
    # O VALOR VAI COMO INTEIRO EM TEXTO -- `"3"`, nunca `"3.0"`. A engine do
    # Athena e uma geracao, nao uma versao pontuada: a AWS publica "Athena
    # engine version 2" e "version 3" e nada entre elas. `"3.0"` inventaria um
    # segmento que a API nao afirma, e `version_scope._parse` compara
    # `(3,)` com `(3, 0)` como iguais de qualquer forma (`_compare` preenche com
    # zeros) -- o segmento inventado nao compraria comparacao nenhuma, so
    # afirmaria mais do que foi lido.
    if fact.kind == "athena.workgroup":
        engine = fact.measures.get("engine_version")
        if not isinstance(engine, int) or isinstance(engine, bool):
            return None
        return ("get_work_group", "athena_version", str(engine))

    return None


# UM DUMP DE ATHENA DESCREVE VARIOS WORKGROUPS, E ISSO NAO E DIVERGENCIA.
#
# `get_work_group` e por conta; uma conta tem muitos workgroups, e dois deles em
# geracoes diferentes -- `legacy-etl` na 2, `primary` na 3 -- e um fato NORMAL
# de conta, nao uma contradicao sobre "qual e o runtime". Deixar isso cair no
# caminho generico de multiplos valores produziria SF-ENV-001 em P0 sobre uma
# configuracao correta, e falso P0 treina o operador a ignorar o canal de
# divergencia -- o oposto do que ele existe para fazer. (Pior: o caminho
# generico qualifica a origem por `provenance.artifact`, e os workgroups de um
# mesmo dump COMPARTILHAM o artefato; as duas leituras colidiriam na mesma
# chave e uma sobrescreveria a outra em silencio, que e resolucao arbitraria.)
#
# A resposta honesta e UNANIMIDADE OU NADA. So existe "a engine version desta
# conta" quando todo workgroup lido diz o mesmo numero; discordando, nao ha um
# valor para reportar, o campo fica vazio e regra com `athena` em
# `runtime_scope` e pulada por ausencia -- falha fechada, a semantica do projeto
# para "nao detectada". Nada se perde: o numero de CADA workgroup continua em
# seu proprio `athena.workgroup`, e `SF-ATH-004` avalia workgroup a workgroup,
# que e a granularidade onde a pergunta tem resposta.
#
# O conjunto de kinds ANULA a fonte pela mesma logica: `athena.unresolved`
# significa que o extrator viu um workgroup e nao conseguiu ler a engine dele
# (ou o dump inteiro). Com um workgroup ilegivel, "todos dizem 3" deixa de ser
# demonstravel, entao a leitura nao sai. O ponto cego nao fica sem registro --
# ele ja tem fact proprio e entra em `athena.analyzed.measures.unresolved_count`
# --, e aqui ele faz o que ponto cego deve fazer: impedir a afirmacao, em vez de
# ser ignorado por ela.
_UNANIMOUS_SOURCES: dict[str, frozenset[str]] = {
    "get_work_group": frozenset({"athena.unresolved"}),
}


def _observation_origin(source: str, fact: Fact) -> str:
    """`<fonte>:<artefato>` -- nome de fonte que diz DE ONDE veio a leitura.

    O sufixo depois de `:` e ignorado por `_source_rank` (que corta em `:`),
    entao a origem qualificada herda exatamente a precedencia da fonte base.
    Isso e o que permite duas leituras discordantes da MESMA fonte coexistirem
    em `detect_runtime`, em vez de uma sobrescrever a outra num dict.
    """
    anchor = str(fact.provenance.get("artifact") or fact.subject.get("symbol") or "").strip()
    return f"{source}:{anchor}" if anchor else source


def runtime_sources_from_facts(facts: list[Fact] | None) -> dict[str, dict[str, Any]]:
    """Fontes para `detect_runtime` derivadas do que os extratores observaram.

    Dois facts do mesmo kind com valores DIFERENTES -- dois modulos Terraform
    declarando `glue_version` distintos, dois event logs de runs diferentes --
    nao sao colapsados aqui, e nenhum e escolhido. Viram duas OBSERVACOES, sob
    origens qualificadas pelo artefato de cada uma, e `detect_runtime` faz o
    que existe para fazer: registra a divergencia em `RuntimeContext.divergences`
    e no fact `env.runtime_signal`, que e o gatilho de SF-ENV-001 em P0.
    Resolver aqui, em silencio, seria esconder do operador exatamente o defeito
    de configuracao que ele precisa ver -- e a versao errada invalida toda
    recomendacao versionada que vier depois.

    Valores repetidos NAO sao divergencia: o mesmo `glue_version` em tres
    arquivos e uma observacao, nao tres. Por isso a deduplicacao e por valor, e
    a qualificacao por artefato so aparece quando ha mais de um valor distinto
    -- caso contrario `detected_from` do contexto encheria de caminhos de
    arquivo onde o operador espera ler "terraform".
    """
    observed: dict[tuple[str, str], dict[str, Fact]] = {}
    voided: set[str] = set()
    for fact in facts or []:
        for source, blinding in _UNANIMOUS_SOURCES.items():
            if fact.kind in blinding:
                voided.add(source)
        reading = _runtime_reading(fact)
        if reading is None:
            continue
        source, key, value = reading
        observed.setdefault((source, key), {}).setdefault(value, fact)

    sources: dict[str, dict[str, Any]] = {}
    for (source, key), by_value in sorted(observed.items()):
        # Ver `_UNANIMOUS_SOURCES`: nestas fontes multiplicidade nao e
        # divergencia e ilegibilidade nao e ausencia. Discordancia ou ponto cego
        # apagam a leitura, em vez de virarem um SF-ENV-001 falso ou uma escolha
        # arbitraria entre valores igualmente verdadeiros.
        if source in _UNANIMOUS_SOURCES and (source in voided or len(by_value) > 1):
            continue
        if len(by_value) == 1:
            sources.setdefault(source, {})[key] = next(iter(by_value))
            continue
        for value, fact in sorted(by_value.items()):
            sources.setdefault(_observation_origin(source, fact), {})[key] = value
    return sources


_EKS_NAMESPACE = "emrc."
_EC2_NAMESPACE = "emr."
_SERVERLESS_NAMESPACE = "emrs."


def _e_so_de_serverless(facts: list[Fact] | None) -> bool:
    """True quando o conjunto tem fact `emrs.*` e nenhum `emr.*` de EC2.

    ESTREITA pelo mesmo motivo que `_recusar_emr_sobre_eks` e: um conjunto com
    os dois artefatos fundidos (`get-application` + `describe-cluster`) tem o
    lado de EC2 de fato presente, e ali a flag declara aquele lado -- com o
    fork `-amzn-N`, que a fonte de EC2 publica. Trocar a matriz tambem naquele
    caso apagaria um dado verdadeiro.

    `emrc.*` (EKS) nao precisa ser testado aqui: `_recusar_emr_sobre_eks` roda
    ANTES e ja estourou se ele estiver presente sem `emr.*`.
    """
    if not facts:
        return False
    kinds = {f.kind for f in facts}
    if not any(k.startswith(_SERVERLESS_NAMESPACE) for k in kinds):
        return False
    return not any(k.startswith(_EC2_NAMESPACE) for k in kinds)


def _recusar_emr_sobre_eks(emr: str | None, facts: list[Fact] | None) -> None:
    """A flag `--emr` e de EMR on EC2, e sobre facts de EMR on EKS ela INVENTA.

    `--emr` alimenta a chave `emr_release`, e `detect_runtime` deriva dela
    `spark`, `python` e `iceberg` pela `EMR_MATRIX` -- que e a matriz de EMR on
    EC2. Sobre um conjunto de facts `emrc.*` os tres eixos sairiam preenchidos
    sem que um unico fact de EC2 estivesse presente.

    Para EMR on EKS isso nao e imprecisao, e erro medido. A AWS PUBLICA matriz
    de release para o EKS, e ela DIVERGE da de EC2 em celulas reais: em 26
    releases comparaveis, Iceberg diverge em 6 e Spark em 4 -- `emr-6.5.0` nao
    publica Iceberg nenhum no EKS enquanto o EC2 publica `0.12.0`, e `emr-7.7.0`
    roda `1.6.1-amzn-2` no EKS contra `1.7.1-amzn-0` no EC2, minor diferente.
    Python nao e publicado por familia em lugar nenhum do EKS. Ver
    `knowledge/emr-eks/runtime-matrix.md` §2 e a DV-1 da spec da fase.

    Recusar, e nao apenas deixar de derivar, porque o proprio eixo `emr` e uma
    afirmacao sobre a plataforma errada: com ele preenchido, regra `SF-EMR-*`
    guardada por `runtime_scope: {emr: ...}` entraria em escopo sobre um
    artefato que nao e um cluster.

    A recusa e ESTREITA de proposito. Um conjunto que tenha `emr.*` ao lado de
    `emrc.*` -- dois artefatos fundidos -- passa, porque ali a flag declara o
    lado de EC2 que esta de fato presente. O `RuntimeContext` e um so para os
    dois lados, e isso e limite estrutural anterior a esta guarda.

    A mesma invencao acontece com facts `emrs.*` de EMR Serverless, e ela
    continua aberta: la a AWS nao publica matriz nenhuma, entao a de EC2 e
    inaplicavel por FALTA DE FONTE, e nao por divergencia medida. Fechar aquele
    lado exige decidir o que fazer sem fonte, e essa decisao nao foi tomada
    aqui.
    """
    if not emr or not facts:
        return
    kinds = {f.kind for f in facts}
    if not any(k.startswith(_EKS_NAMESPACE) for k in kinds):
        return
    if any(k.startswith(_EC2_NAMESPACE) for k in kinds):
        return
    raise AdapterError(
        f"`--emr {emr}` e release de EMR on EC2, e este conjunto de facts e de "
        f"EMR on EKS (kinds `{_EKS_NAMESPACE}*`, nenhum `{_EC2_NAMESPACE}*`).\n"
        f"  A matriz de release do EMR on EKS existe e DIVERGE da de EC2 -- "
        f"Iceberg em 6 de 26 releases comparaveis, Spark em 4 --, entao derivar "
        f"`spark`, `python` e `iceberg` do release de EC2 gravaria versao que "
        f"nunca rodou.\n"
        f"  Julgue sem a flag; a area SF-EMRK nao restringe por versao:\n"
        f"    sparkforge judge --facts <arquivo>\n"
        f"  Ver `knowledge/emr-eks/runtime-matrix.md` (secao 2).",
        exit_code=2,
    )


def build_runtime(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    facts: list[Fact] | None = None,
    emr: str | None = None,
) -> tuple[RuntimeContext, list[Fact]]:
    """Contexto de runtime E os facts `env.runtime_signal` que o justificam.

    `facts` e opcional e o default (`None`) reproduz exatamente o comportamento
    anterior -- so as flags. Quando informado, as versoes JA OBSERVADAS pelos
    extratores entram como fontes proprias, e o operador deixa de precisar
    saber de cor a versao do Glue para que as regras versionadas avaliem.

    `emr` entra DEPOIS de `facts` na assinatura, e nao ao lado de `glue`, onde
    pertenceria por semantica: os chamadores existentes passam as cinco
    primeiras posicionalmente, e inserir um parametro no meio trocaria
    silenciosamente o significado de cada argumento deles. Ordem de assinatura e
    compatibilidade, nao taxonomia.
    """
    _recusar_emr_sobre_eks(emr, facts)
    # A MESMA flag, a MESMA release, e OUTRA matriz. Sobre um conjunto so de
    # facts `emrs.*` a derivacao passa pela matriz do EMR Serverless, que
    # publica `spark` sem o sufixo do fork e NAO publica `python` nem
    # `iceberg` -- os dois eixos que a matriz de EC2 preenchia do nada. O eixo
    # `emr` continua sendo lido da flag nos dois caminhos: o release label e o
    # mesmo namespace nas duas plataformas, e apaga-lo trocaria invencao por
    # perda de informacao. Ver `knowledge/emr-serverless/runtime-matrix.md`.
    chave_do_release = (
        "emr_serverless_release" if _e_so_de_serverless(facts) else "emr_release"
    )
    raw = {
        "glue_version": glue,
        # `emr_release` e a primeira chave de `_PLATFORM_KEYS["emr"]`, e
        # `_emr_key` aceita `emr-7.5.0` e `7.5.0` indiferentemente -- a flag nao
        # obriga o operador a saber qual das duas grafias o projeto guarda.
        # A flag e uma DECLARACAO, e por isso a fonte e `cli`, abaixo de
        # `event_log` e de `describe_cluster` em `_PRECEDENCE`: discordar de um
        # dump vira divergencia registrada, nunca resolucao silenciosa.
        chave_do_release: emr,
        "spark_version": spark,
        "python_version": python,
        "iceberg_version": iceberg,
        "athena_version": athena,
    }
    cleaned = {k: v for k, v in raw.items() if v}
    sources = runtime_sources_from_facts(facts)
    if cleaned:
        sources["cli"] = cleaned
    return detect_runtime(sources)


def build_runtime_context(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    facts: list[Fact] | None = None,
    emr: str | None = None,
) -> RuntimeContext:
    context, _facts = build_runtime(
        glue, spark, python, iceberg, athena, facts=facts, emr=emr
    )
    return context


# --------------------------------------------------------------------------- #
# analyze pyspark
# --------------------------------------------------------------------------- #


def _extract_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        # Erro traz causa E o comando que resolve. Dizer so o que esta errado
        # deixa o operador (ou o agente) adivinhando o proximo passo, que e a
        # forma mais barata de fazer uma ferramenta parecer quebrada.
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio da biblioteca ou para um arquivo .py:\n"
            f"    sparkforge analyze pyspark --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_tree(target, repo_root=target)
    return extract_path(target, repo_root=target.parent)


def analyze_pyspark(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)
    page, procedencias, versao_do_schema = project_items(page, detail_level)

    # `unresolved` e contado sobre `facts`, nao sobre `filtered`: um filtro por
    # kind nao pode fazer o ponto cego desaparecer do relatorio. A regra 7 do
    # AGENT_PROTOCOL.md exige reportar sempre — no nao resolvido e ponto cego,
    # nao ausencia de problema, e omiti-lo deixa o operador confundir "nao achei"
    # com "nao ha".
    unresolved = sum(1 for f in facts if f.kind == "pyspark.unresolved")
    unresolved_at = [
        {
            "file": f.subject.get("file", ""),
            "line": f.subject.get("line", 0),
            "reason": f.attrs.get("reason", ""),
        }
        for f in facts
        if f.kind == "pyspark.unresolved"
    ]

    resultado: dict[str, Any] = {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "unresolved": unresolved,
        "unresolved_at": unresolved_at,
        "items": page,
    }
    declarar_no_envelope(resultado, procedencias, versao_do_schema)
    return resultado


# --------------------------------------------------------------------------- #
# analyze catalog-schema
# --------------------------------------------------------------------------- #


def _extract_catalog_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps do Glue Data Catalog ou para um "
            f"arquivo .json:\n"
            f"    sparkforge analyze catalog-schema --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_catalog.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_catalog_schema_tree(target, repo_root=target)
    return extract_catalog_schema_path(target, repo_root=target.parent)


def analyze_catalog_schema(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_catalog_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)
    page, procedencias, versao_do_schema = project_items(page, detail_level)

    # Mesmo raciocinio de `analyze_pyspark`: `unresolved` conta sobre `facts`,
    # nao sobre `filtered`, para um filtro por kind nao esconder o ponto cego.
    unresolved = sum(1 for f in facts if f.kind == "catalog.unresolved")
    unresolved_at = [
        {"file": f.subject.get("file", ""), "reason": f.attrs.get("reason", "")}
        for f in facts
        if f.kind == "catalog.unresolved"
    ]

    resultado: dict[str, Any] = {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "unresolved": unresolved,
        "unresolved_at": unresolved_at,
        "items": page,
    }
    declarar_no_envelope(resultado, procedencias, versao_do_schema)
    return resultado


def _facts_page(
    facts: list[Fact],
    unresolved_kind: str | None,
    kind: list[str] | None,
    limit: int | None,
    cursor: str | None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Pagina uma lista de Facts ja extraida, no mesmo shape de
    `analyze_pyspark`/`analyze_catalog_schema`: total/pagina/by_kind, mais
    `unresolved`/`unresolved_at` quando `unresolved_kind` e informado.

    `unresolved_kind` e `None` para extratores derivados que nao tem ponto
    cego proprio (`analyze_call_graph`: deriva de Facts ja resolvidos por
    `pyspark_ast`, nunca falha em interpretar algo por si so) -- as duas
    chaves ficam simplesmente ausentes do resultado, em vez de zeradas, para
    nao alegar uma garantia que o extrator nao da.

    Compartilhado pelos extratores adicionados apos `analyze_pyspark`/
    `analyze_catalog_schema` (que ja tinham a logica inline antes deste
    helper existir e continuam como estao, para nao arriscar o golden test
    dos dois por um refactor que nao muda comportamento).
    """
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)
    page, procedencias, versao_do_schema = project_items(page, detail_level)

    result: dict[str, Any] = {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "items": page,
    }
    declarar_no_envelope(result, procedencias, versao_do_schema)

    if unresolved_kind is not None:
        # Mesmo raciocinio de `analyze_pyspark`/`analyze_catalog_schema`:
        # contado sobre `facts` (o conjunto completo), nao sobre `filtered`,
        # para um filtro por kind nao fazer o ponto cego desaparecer do
        # relatorio. Regra 7 do AGENT_PROTOCOL.md.
        unresolved = sum(1 for f in facts if f.kind == unresolved_kind)
        unresolved_at = [
            {
                "file": f.subject.get("file", ""),
                "line": f.subject.get("line", 0),
                "reason": f.attrs.get("reason", ""),
            }
            for f in facts
            if f.kind == unresolved_kind
        ]
        result["unresolved"] = unresolved
        result["unresolved_at"] = unresolved_at

    return result


# --------------------------------------------------------------------------- #
# analyze event-log
# --------------------------------------------------------------------------- #


def _extract_event_log_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o arquivo de Spark event log (.jsonl):\n"
            f"    sparkforge analyze event-log --path <arquivo> "
            f"--out .sparkforge/facts_eventlog.json",
            exit_code=2,
        )
    return extract_event_log_path(target, repo_root=target.parent)


def analyze_event_log(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_event_log_facts(path)
    return _facts_page(facts, "spark.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze sql-metrics
# --------------------------------------------------------------------------- #


def analyze_sql_metrics(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um Spark event log (JSON Lines):\n"
            f"    sparkforge analyze sql-metrics "
            f"--path .sparkforge/artifacts/eventlog/app.jsonl",
            exit_code=2,
        )
    facts = extract_sql_metrics_path(target)
    return _facts_page(facts, "spark.sql.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze cloudwatch / glue-job-runs
# --------------------------------------------------------------------------- #


def _extract_cloudwatch_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um artefato gravado por `sparkforge collect cloudwatch`:\n"
            f"    sparkforge analyze cloudwatch "
            f"--path .sparkforge/artifacts/cloudwatch/<job>_<run>.json",
            exit_code=2,
        )
    return extract_cloudwatch_path(target)


def analyze_cloudwatch(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_cloudwatch_facts(path)
    return _facts_page(facts, "glue.metric.unresolved", kind, limit, cursor, detail_level)


def analyze_glue_job_runs(
    path: str,
    job_name: str,
    cloudwatch: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_dir():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o DIRETORIO de artefatos de run, nao para um arquivo:\n"
            f"    sparkforge analyze glue-job-runs "
            f"--path .sparkforge/artifacts/glue_job_run/ --job-name <job>",
            exit_code=2,
        )
    cw_dir = Path(cloudwatch) if cloudwatch else None
    if cw_dir is not None and not cw_dir.is_dir():
        raise AdapterError(
            f"--cloudwatch aponta para {cloudwatch}, que nao e um diretorio existente.",
            exit_code=2,
        )
    facts = extract_glue_job_runs_path(target, job_name, cloudwatch_dir=cw_dir)
    return _facts_page(facts, "glue.job_run.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze plan
# --------------------------------------------------------------------------- #


def _extract_plan_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um arquivo de texto com a saida de "
            f"`df.explain(\"formatted\")` (um plano por arquivo):\n"
            f"    sparkforge analyze plan --path <arquivo> "
            f"--out .sparkforge/facts_plan.json",
            exit_code=2,
        )
    return extract_plan_path(target, repo_root=target.parent)


def analyze_plan(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Extrai Facts do texto de um plano fisico ja salvo em disco.

    Um arquivo por chamada, nunca um diretorio: cada arquivo e UM plano, e
    concatenar planos de queries diferentes na mesma analise misturaria nos com
    a mesma numeracao `(N)` vindos de arvores distintas.
    """
    facts = _extract_plan_facts(path)
    return _facts_page(facts, "plan.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze terraform
# --------------------------------------------------------------------------- #


def _extract_terraform_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com arquivos .tf ou para um arquivo .tf:\n"
            f"    sparkforge analyze terraform --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_terraform.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_terraform_tree(target, repo_root=target)
    return extract_terraform_path(target, repo_root=target.parent)


def analyze_terraform(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_terraform_facts(path)
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze iceberg
# --------------------------------------------------------------------------- #


def _extract_iceberg_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps das metadata tables Iceberg ou para "
            f"um arquivo .json:\n"
            f"    sparkforge analyze iceberg --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_iceberg.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_iceberg_metadata_tree(target, repo_root=target)
    return extract_iceberg_metadata_path(target, repo_root=target.parent)


def analyze_iceberg(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_iceberg_facts(path)
    return _facts_page(facts, "iceberg.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze sql
# --------------------------------------------------------------------------- #


def _extract_sql_facts(path: str | None, from_pyspark: str | None) -> list[Fact]:
    if from_pyspark:
        target = Path(from_pyspark)
        if not target.is_file():
            raise AdapterError(
                f"Caminho nao encontrado para analise: {from_pyspark}\n"
                f'  Aponte para um arquivo .py com chamadas spark.sql("..."):\n'
                f"    sparkforge analyze sql --from-pyspark <arquivo> "
                f"--out .sparkforge/facts_sql.json",
                exit_code=2,
            )
        try:
            source = target.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise AdapterError(f"{from_pyspark}: erro de leitura: {exc}", exit_code=2) from exc
        return extract_sql_from_pyspark(source, target.name)

    if not path:
        raise AdapterError(
            "informe --path <arquivo.sql> ou --from-pyspark <arquivo.py>.",
            exit_code=2,
        )
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um arquivo .sql:\n"
            f"    sparkforge analyze sql --path <arquivo> --out .sparkforge/facts_sql.json",
            exit_code=2,
        )
    return extract_sql_path(target, repo_root=target.parent)


def analyze_sql(
    path: str | None = None,
    from_pyspark: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_sql_facts(path, from_pyspark)
    return _facts_page(facts, "sql.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze athena-workgroup
# --------------------------------------------------------------------------- #


def _extract_athena_workgroup_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de workgroups do Athena ou para um "
            f"arquivo .json:\n"
            f"    sparkforge analyze athena-workgroup --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_athena.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_athena_workgroup_tree(target, repo_root=target)
    return extract_athena_workgroup_path(target, repo_root=target.parent)


def analyze_athena_workgroup(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_athena_workgroup_facts(path)
    return _facts_page(facts, "athena.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze emr-cluster
# --------------------------------------------------------------------------- #


def _extract_emr_cluster_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de cluster EMR ou para um arquivo .json:\n"
            f"    sparkforge collect emr-cluster --repo . --cluster-id j-XXXX --now <iso>\n"
            f"    sparkforge analyze emr-cluster --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_emr.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_emr_cluster_tree(target, repo_root=target)
    return extract_emr_cluster_path(target, repo_root=target.parent)


def analyze_emr_cluster(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_emr_cluster_facts(path)
    return _facts_page(facts, "emr.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze emr-serverless
# --------------------------------------------------------------------------- #
#
# NAO ha produtor de `RuntimeContext` para `emrs.application.release_label`, e a
# ausencia e decidida, nao esquecida. `emr.cluster` vira produtor logo acima
# porque a AWS publica, por release do EMR on EC2, as versoes de Spark, Hadoop,
# Python e Iceberg -- as quatro colunas que `EMR_MATRIX` compara. A pesquisa da
# Fase 5d mediu que a documentacao do EMR Serverless publica **so** Spark, Hive e
# Tez por release, e ainda sem o sufixo `-amzn-N`: tres das quatro colunas nao
# tem fonte do lado do Serverless, e ha `releaseLabel` em uso (`emr-spark-8.0.0`)
# que nao tem sequer chave na matriz. Derivar runtime dai falharia calada
# justamente na release mais nova. Ver `knowledge/emr-serverless/runtime-matrix.md`
# secao 6 e o desvio D-5d-5 do plano da fase: a razao registrada e "sem fonte",
# nao "as matrizes divergem".


def _extract_emr_serverless_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de application EMR Serverless ou para "
            f"um arquivo .json:\n"
            f"    sparkforge collect emr-serverless --repo . --application-id 00fXXXX "
            f"--now <iso>\n"
            f"    sparkforge analyze emr-serverless --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_emr_serverless.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_emr_serverless_tree(target, repo_root=target)
    return extract_emr_serverless_path(target, repo_root=target.parent)


def analyze_emr_serverless(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_emr_serverless_facts(path)
    return _facts_page(facts, "emrs.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze emr-eks
# --------------------------------------------------------------------------- #
#
# NAO ha produtor de `RuntimeContext` aqui, pela razao do irmao Serverless
# levada um passo adiante: `releaseLabel` do EMR on EKS (`emr-6.15.0-latest`)
# carrega um sufixo de canal que a matriz de release do EMR on EC2 nao tem
# chave para casar, e o que roda de fato vem da imagem do container, que este
# extrator NAO le. Derivar versao de Spark, Python ou Iceberg daqui seria
# afirmar sobre a imagem a partir do rotulo -- exatamente a inferencia que a
# area recusa.
#
# A fronteira da area inteira, repetida onde a superficie a expoe: os facts
# `emrc.*` descrevem o que UMA EXECUCAO PEDIU (`DescribeJobRun` mais
# `DescribeVirtualCluster`), nunca o que o pod recebeu. O pod template
# referenciado pela configuracao nao e lido -- ele sai como recusa com o path,
# porque le-lo exigiria um `GetObject` no S3 que este caminho nao faz. E o lado
# EKS (nodegroup, autoscaling, pod pendente) nao existe neste dump: outro
# servico, outro IAM, outra matriz de versao.


def _extract_emr_eks_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com dumps de execucao EMR on EKS ou para "
            f"um arquivo .json:\n"
            f"    sparkforge collect emr-eks --repo . --virtual-cluster-id 0abcXXXX "
            f"--job-run-id 0runXXXX --now <iso>\n"
            f"    sparkforge analyze emr-eks --path <dir-ou-arquivo> "
            f"--out .sparkforge/facts_emr_eks.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_emr_eks_tree(target, repo_root=target)
    return extract_emr_eks_path(target, repo_root=target.parent)


def analyze_emr_eks(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_emr_eks_facts(path)
    return _facts_page(facts, "emrc.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze data-quality
# --------------------------------------------------------------------------- #


def _extract_data_quality_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio do codigo PySpark ou para um arquivo .py:\n"
            f"    sparkforge analyze data-quality --path src/ "
            f"--out .sparkforge/facts_dq.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_data_quality_tree(target, repo_root=target)
    return extract_data_quality_path(target, repo_root=target.parent)


def analyze_data_quality(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_data_quality_facts(path)
    return _facts_page(facts, "dq.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze graph
# --------------------------------------------------------------------------- #


def _extract_graph_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio do codigo PySpark ou para um arquivo .py:\n"
            f"    sparkforge analyze graph --path src/ "
            f"--out .sparkforge/facts_graph.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_graph_tree(target, repo_root=target)
    return extract_graph_path(target, repo_root=target.parent)


def analyze_graph(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_graph_facts(path)
    return _facts_page(facts, "graph.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze s3-listing
# --------------------------------------------------------------------------- #


def _extract_s3_listing_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com paginas de listagem ou para um arquivo .json:\n"
            f"    aws s3api list-objects-v2 --bucket <b> --prefix <p> > listing.json\n"
            f"    sparkforge analyze s3-listing --path listing.json "
            f"--out .sparkforge/facts_s3.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_s3_listing_tree(target, repo_root=target)
    return extract_s3_listing_path(target, repo_root=target.parent)


def analyze_s3_listing(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_s3_listing_facts(path)
    return _facts_page(facts, "s3.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze consumers
# --------------------------------------------------------------------------- #


def _extract_consumers_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o inventario declarado de consumidores:\n"
            f"    sparkforge analyze consumers --path .sparkforge/consumers.yaml "
            f"--out .sparkforge/facts_consumers.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_consumers_tree(target, repo_root=target)
    return extract_consumers_path(target, repo_root=target.parent)


def analyze_consumers(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_consumers_facts(path)
    return _facts_page(facts, "env.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze terraform-diff
# --------------------------------------------------------------------------- #


def analyze_terraform_diff(
    before: str,
    after: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    before_path = Path(before)
    after_path = Path(after)
    for label, target in (("--before", before_path), ("--after", after_path)):
        if not target.is_dir():
            raise AdapterError(
                f"Diretorio nao encontrado para {label}: {target}\n"
                f"  Aponte para dois estados do mesmo modulo Terraform (dois checkouts,\n"
                f"  dois `git worktree`, o main e o branch do PR):\n"
                f"    sparkforge analyze terraform-diff --before ./infra-main "
                f"--after ./infra-pr",
                exit_code=2,
            )
    facts = extract_terraform_diff(before_path, after_path, repo_root=after_path)
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze call-graph
# --------------------------------------------------------------------------- #


def analyze_call_graph(
    facts_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Deriva Facts de grafo de chamadas a partir de um arquivo de facts ja
    extraido (tipicamente `analyze pyspark --out`). Funcao pura sobre Facts:
    nunca reparseia fonte -- ver docstring de `sparkforge.facts.call_graph`.
    Sem `unresolved` proprio: o grafo so deriva do que `pyspark_ast` ja
    resolveu, nunca falha em interpretar algo por si so.
    """
    fact_list = _load_facts_file(facts_path)
    derived = build_call_graph(fact_list, path_hint=facts_path)
    return _facts_page(derived, None, kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# migration assess
# --------------------------------------------------------------------------- #


def migration_assess(
    path: str, source: str, target: str, platform: str = MIGRATION_DEFAULT_PLATFORM
) -> dict[str, Any]:
    """Julga a migracao de um job entre um par de versoes, pelo catalogo.

    PARAMETRO NOVO, TOOL A MESMA (D-4 da spec de EMR). Medido antes de decidir:
    `sparkforge_migration_assess` ja compunha os artefatos, ja expandia o par em
    degraus e ja agregava com gates; o que ela nao aceitava era a PLATAFORMA.
    Uma tool nova duplicaria as tres coisas para trocar uma matriz, e cada tool
    nova entra em quatro gates de paridade e la fica -- a §70 manda expandir em
    vez de multiplicar. `platform` tem default `glue` porque essa era a unica
    resposta possivel antes, e mudar o default silenciosamente trocaria a
    resposta de quem ja chamava.

    A COBERTURA SAI JUNTO, SEMPRE. Para EMR o catalogo tem ZERO regras por
    `emr`: sem o campo `coverage`, este verbo devolveria um assessment sem
    achado que o operador leria como "nada quebra". Ver a DECISAO 3 no
    docstring de `sparkforge/migration/assessment.py`.

    Composicao, nao motor novo: `sparkforge.migration.assessment.assess()` ja
    expande o par em degraus, julga cada degrau com o `judge` e agrega com
    gates fail-closed. O que faltava era a porta de entrada -- ate esta funcao
    existir, o catalogo `SF-MIG`/`SF-SPARK4`/`SF-LF` so era alcancavel por
    quem chamasse `assess()` em Python.

    DIRETORIO **ou** ARQUIVO, a mesma convencao de todo `analyze_*` deste
    modulo. Um diretorio e o caso que interessa -- uma migracao e julgada
    sobre o conjunto de artefatos do job, e `requirements*.txt` e `.jar` nao
    tem linha de fonte Python para varrer --, mas um `.py` sozinho continua
    respondido: recusa-lo quebraria a interface publicada de
    `forge migrate glue` sem que nada de util fosse ganho.

    `source` e `target` nao tem default, aqui nem em quem chama. Um par
    embutido no codigo responde sobre um alvo que ninguem declarou, e o
    veredito sai com a mesma cara de qualquer outro.
    """
    target_path = Path(path)
    if not target_path.exists():
        raise AdapterError(
            f"Caminho nao encontrado: {target_path}\n"
            f"  Aponte para o diretorio do job (codigo, requirements*.txt e .jar)\n"
            f"  ou para um arquivo .py:\n"
            f"    sparkforge migrate glue ./meu-job --from 4.0 --to 6.0",
            exit_code=2,
        )
    facts = collect_migration(target_path)

    try:
        return assess_migration(
            facts, source=source, target=target, platform=platform
        ).to_dict()
    except ValueError as exc:
        # `version_path.steps` ja nomeia o defeito ("alvo anterior a origem",
        # "versao fora da matriz de <plataforma>; conhecidas: ...", "rotulo
        # fora do padrao de versao"). Traduzir para um erro generico perderia
        # a unica informacao util da falha.
        raise AdapterError(
            f"{exc}\n"
            f"  As quatro plataformas: {', '.join(RELEASE_PLATFORMS)}.\n"
            f"  Confira o par contra a matriz daquela plataforma:\n"
            f"    sparkforge release describe --platform {platform} "
            f"--release <release>",
            exit_code=2,
        ) from exc


# --------------------------------------------------------------------------- #
# glue dependency-audit / iceberg assess-upgrade
# --------------------------------------------------------------------------- #

# Os dois kinds que carregam dependencia declarada. Nao ha terceiro: o extrator
# de migracao nomeia `mig.python_dep` (uma linha pinada de `requirements*.txt`,
# com `major` ja separado) e `mig.jar_binary` (um `.jar`, com `scala_minor` ja
# separado do resto da versao).
_KINDS_DE_DEPENDENCIA = ("mig.python_dep", "mig.jar_binary")


def glue_dependency_audit(path: str, glue: str) -> dict[str, Any]:
    """Pins declarados, e o que o catalogo diz sobre eles NUM runtime.

    `glue` nao tem default e nao e opcional. Risco de ABI nao existe em
    abstrato: um `.jar` de Scala 2.12 e correto sob Glue 5.1 e quebra sob 6.0,
    e um piso de `pyarrow` so e piso a partir da versao de Spark que o exige.
    Auditar dependencia sem dizer contra qual runtime produziria uma lista de
    versoes com cara de veredito.

    Composicao, nao motor: `collect()` extrai, `judge` julga com o mesmo
    catalogo de sempre. O que este comando acrescenta e a VISAO -- a
    dependencia observada ao lado do achado que ela produziu.
    """
    alvo = Path(path)
    if not alvo.exists():
        raise AdapterError(
            f"Caminho nao encontrado: {alvo}\n"
            "  Aponte para o diretorio do job (codigo, requirements*.txt e .jar):\n"
            "    sparkforge glue dependency-audit ./meu-job --glue 6.0",
            exit_code=2,
        )

    facts = collect_migration(alvo)
    context = build_runtime_context(glue=glue, facts=facts)
    runtime = context.to_dict()
    findings = run_judge(facts, load_catalog(), runtime)

    dependencias = [
        {
            "kind": fact.kind,
            # `package` para dependencia Python; para um `.jar` a identidade e
            # o proprio artefato, porque o extrator nao le nome de artefato de
            # dentro do binario e inventa-lo a partir do nome do arquivo seria
            # afirmar o que ninguem observou.
            "name": fact.attrs.get("package") or fact.provenance.get("artifact", ""),
            # Os attrs INTEIROS, e nao um subconjunto escolhido aqui: sao eles
            # que as regras comparam contra um piso (`major`, `scala_minor`),
            # e recorta-los faria o achado deixar de ser conferivel sem
            # reabrir os facts.
            "attrs": dict(fact.attrs),
            "artifact": fact.provenance.get("artifact", ""),
        }
        for fact in facts
        if fact.kind in _KINDS_DE_DEPENDENCIA
    ]

    return {
        "path": str(alvo),
        "runtime": runtime,
        "dependencies": dependencias,
        "findings": [f.to_dict() for f in findings],
        "by_severity": _count_by([f.to_dict() for f in findings], lambda f: f["severity"]),
    }


def iceberg_assess_upgrade(path: str, source: int, target: int) -> dict[str, Any]:
    """Veredito de subir o format version de uma tabela, dado quem a consome.

    NUNCA executa o upgrade -- a secao 94 do prompt e explicita, e a garantia e
    estrutural: `sparkforge/storage/upgrade.py` nao importa cliente de AWS nem
    Spark. Ver o teste que mede isso pelos imports do modulo.

    `source` entra para RECUSAR o que nao e upgrade (alvo anterior a origem, ou
    igual). Ele nao muda o veredito: quem decide e a matriz de suporte da
    versao ALVO, porque a pergunta e o que as engines conseguem ler depois da
    mudanca, nao o que liam antes.
    """
    if target <= source:
        raise AdapterError(
            f"alvo {target} nao e upgrade de {source}: informe um alvo maior que a origem",
            exit_code=2,
        )

    alvo = Path(path)
    if not alvo.exists():
        raise AdapterError(
            f"Caminho nao encontrado: {alvo}\n"
            "  Aponte para o diretorio do job, com o inventario em "
            "`.sparkforge/consumers.yaml`:\n"
            "    sparkforge iceberg assess-upgrade ./meu-job --from 2 --to 3",
            exit_code=2,
        )

    facts = collect_migration(alvo)
    engines = sorted(
        {
            str(f.attrs.get("service", ""))
            for f in facts
            if f.kind == "env.consumer" and f.attrs.get("service")
        }
    )
    # `release` e opcional no inventario. Quando o operador declara DUAS
    # releases para o mesmo servico, a ultima em ordem NAO vence por sorteio:
    # duas releases da mesma plataforma sao dois consumidores, e escolher uma
    # responderia pela outra. O caso e raro e a saida honesta e a mais simples
    # possivel -- fica sem release, e a resposta cai para a da engine sem
    # recorte de versao, que e mais fraca e nao errada.
    declaradas: dict[str, set[str]] = {}
    for fato in facts:
        if fato.kind != "env.consumer":
            continue
        servico = str(fato.attrs.get("service", ""))
        release = str(fato.attrs.get("release", "")).strip()
        if servico and release:
            declaradas.setdefault(servico, set()).add(release)
    releases = {s: next(iter(r)) for s, r in declaradas.items() if len(r) == 1}
    try:
        resultado = assess_iceberg_upgrade(engines, target_spec_version=target, releases=releases)
    except ValueError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    payload = resultado.to_dict()
    payload["source_spec_version"] = source
    payload["path"] = str(alvo)
    return payload


# --------------------------------------------------------------------------- #
# release describe / release diff
# --------------------------------------------------------------------------- #

# VERBOS DE TOPO, e nao `analyze release`: tudo sob `analyze` le um ARTEFATO do
# operador e para ali. Estes dois nao leem artefato nenhum -- eles compoem sobre
# as quatro matrizes de `knowledge/`, que e a mesma linha que separa `benchmark`,
# `workload` e `fuse` dos extratores.
#
# E os dois NAO JULGAM. A D-6 da spec de `ReleaseDiff` e explicita: este
# sub-projeto entrega dado, modelo e verbo, e nenhuma regra. Nenhum `Finding`
# nasce aqui, e nenhuma linha da saida diz se algo quebra -- essa pergunta e do
# `MigrationAssessment` (`migration_assess`, hoje so Glue).
#
# O UNICO trabalho desta camada e traduzir a recusa NOMEADA do modelo
# (`UnknownPlatform`, `UnknownRelease`) para `AdapterError` com exit 2, no molde
# dos `_extract_*_facts`: a mensagem ensina o que existe. Ela precisa ensinar
# porque as quatro matrizes tem fronteiras DIFERENTES -- `6.3.0` existe no EMR
# on EKS (que desce ate `5.32.0`) e nao no EC2 (que comeca em `6.4.0`), e
# `spark-8.0-preview` so existe no Serverless. Um `KeyError` nao diria qual das
# quatro fronteiras foi cruzada.


def _release_descriptor(platform: str, release: str) -> ReleaseDescriptor:
    """`describe()` com a recusa vestida de erro de fronteira acionavel."""
    try:
        return describe_release(platform, release)
    except UnknownPlatform as exc:
        raise AdapterError(
            f"{exc}\n"
            f"  As quatro plataformas: {', '.join(RELEASE_PLATFORMS)}.\n"
            f"    sparkforge release describe --platform emr_ec2 --release 7.7.0",
            exit_code=2,
        ) from exc
    except UnknownRelease as exc:
        raise AdapterError(
            f"{exc}\n"
            f"  Cada plataforma tem a sua matriz, e as fronteiras nao coincidem:\n"
            f"  uma release conhecida por uma pode nao existir na outra.\n"
            f"    sparkforge release describe --platform {platform} "
            f"--release {(known_releases_of(platform) or ('<release>',))[0]}",
            exit_code=2,
        ) from exc


def release_describe(platform: str, release: str) -> dict[str, Any]:
    """O que uma release E, segundo a fonte daquela plataforma e so ela.

    Componente que a fonte daquela plataforma NAO publica sai em `unresolved`
    NOMEADO -- nunca string vazia, nunca chave ausente em silencio. As quatro
    plataformas publicam conjuntos diferentes (o EMR on EKS nao publica Hadoop
    em release nenhuma: 0 de 34 paginas), e um descritor que apagasse essa
    diferenca mentiria por omissao. `unresolved_detail` carrega o tipo da
    recusa e a medida que a destravaria, porque `platform_source_does_not_publish`
    destrava com uma FONTE nova e `release_cell_absent` com uma LEITURA daquela
    pagina -- colapsar as duas faria o operador procurar no lugar errado.
    """
    return _release_descriptor(platform, release).to_dict()


def release_diff(
    left_platform: str,
    left_release: str,
    right_platform: str,
    right_release: str,
) -> dict[str, Any]:
    """O que mudou entre duas releases, com o EIXO da comparacao declarado.

    QUATRO argumentos e nao tres, e a razao esta na D-4 da spec: comparar
    `emr-7.7.0` no EC2 com o MESMO rotulo no EKS e comparacao legitima -- e onde
    mora o achado medido, que o mesmo rotulo publica Iceberg `1.7.1-amzn-0` num
    e `1.6.1-amzn-2` no outro. Um verbo que recebesse UMA plataforma e duas
    releases nao teria como fazer essa pergunta.

    `axis` sai com as dimensoes que EFETIVAMENTE variam (`platform`, `release`,
    ou as duas, nessa ordem). Com as duas variando a ATRIBUICAO sai em
    `unresolved`: nenhuma linha de `changed` pode ser creditada a release ou a
    plataforma isoladamente.

    Cinco das sete dimensoes do §8.2 saem em `unresolved` com a razao --
    `deprecated`, `default_changes`, `compatibility_changes`, `security_changes`
    e `performance_changes` --, porque as matrizes sustentam versao de componente
    e nada mais. Lista vazia seria lida como "nao mudou nada".
    """
    return diff_releases(
        _release_descriptor(left_platform, left_release),
        _release_descriptor(right_platform, right_release),
    ).to_dict()


# --------------------------------------------------------------------------- #
# controlm describe
# --------------------------------------------------------------------------- #

# VERBO DE TOPO PROPRIO, e nao uma quinta `platform` de `release describe`.
# `release describe` recebe `(platform, release)` e responde componente ->
# versao para as QUATRO plataformas de Spark. Control-M nao e uma delas em
# nenhum sentido util: nao tem Spark, nao tem release label, e a resposta dele
# tem DOIS eixos (capacidade com fronteira, e componente com exigencia) onde a
# daquele verbo tem um. Enfia-lo ali obrigaria `ReleaseDescriptor` a carregar um
# eixo que nenhuma das quatro plataformas tem, e `release diff` -- que consome o
# mesmo modelo -- passaria a comparar campos que so existem para uma delas.
#
# E ele NAO JULGA, pela mesma razao dos dois vizinhos: nao ha artefato de
# Control-M para extrair e nao ha corpus que sustente regra. Este verbo entrega
# DADO e CONSULTA.


def controlm_covers() -> tuple[str, str]:
    """O intervalo `(from, to)` que a matriz do Control-M sustenta.

    Funcao e nao constante de modulo: uma constante leria o YAML na IMPORTACAO
    de `_core`, que e o modo de falha que `sparkforge/facts/runtime_matrix.py`
    documenta ter transformado um bug latente em `import` quebrado num wheel
    instalado. As duas superficies (CLI e MCP) a chamam quando montam a ajuda,
    e ai o `knowledge_dir` ja esta resolvido.
    """
    return controlm_covered_range()


# `full`/`compact`/`minimal`, e NAO os mesmos tres nomes de `NIVEIS_DE_DETALHE`
# (`summary`/`normal`/`full`) que as 27 tools de FACT usam. A razao e o shape:
# aquele mecanismo projeta `payload["items"]` -- uma LISTA de facts, cada um
# com `provenance` proprio -- e `controlm describe` nao devolve items, devolve
# DOIS dicionarios (`capabilities`, `deprecated`) mais um terceiro
# (`unresolved_detail`) sem `provenance` nenhuma. `project_items` aplicado a
# este payload devolveria dict vazio -- ver o aviso na docstring dele.
# `code_symbol`/`code_status` reaproveitam os nomes `summary`/`normal`/`full`
# para um shape tambem proprio; aqui o nome ficou distinto de proposito, para
# nao description prometer "reduz a id/kind/measures" (o que `summary`
# significa nas 27 tools) quando o corte real e outro.
NIVEIS_DE_DETALHE_CONTROLM: tuple[str, ...] = ("minimal", "compact", "full")


def _project_controlm_describe(payload: dict[str, Any], detail_level: str) -> dict[str, Any]:
    """Projeta a saida de `controlm_describe` para o nivel pedido.

    Medido antes desta fase: `capabilities` e `unresolved_detail` somavam 84%
    dos 9.844 bytes do payload em `full` (62% e 22%). Os dois sao os unicos
    campos que mudam de forma; nada mais e tocado.

    `full` -- o dict inteiro de `VersionDescriptor.to_dict()`, sem mudanca.

    `compact` -- `capabilities` vira LISTA de slugs (ja ordenada -- `to_dict`
    ordena o dict antes de serializar) em vez do dict com `summary`/
    `boundary`/`declared_at`/`replaced_by` por item. `unresolved_detail` sai
    inteiro: `unresolved` (a mesma lista de slugs, sem a razao) ja fica.
    `deprecated` fica INTEIRO de proposito -- e a resposta direta a "o que eu
    nao posso mais usar", e cortar obrigaria uma segunda chamada em `full` para
    responder a MESMA pergunta que motivou a primeira. `components`, `covers`,
    `declared_here`, `domain`, `sources`, `version` e `retrieved` nao mudam:
    nenhum deles foi medido como caro.

    `minimal` -- so o que responde "o que vale nesta versao" sem a lista
    inteira: `version`, `covers`, a CONTAGEM de `capabilities`, os SLUGS de
    `deprecated` (sem o resumo de cada um) e a CONTAGEM de `unresolved`.
    `unresolved_count` nunca sai, mesmo quando e zero -- e a recusa nomeada da
    matriz (9 das 31 versoes da faixa nao tem afirmacao propria, medido na
    Fase 1) tem que sobreviver a QUALQUER nivel, ou o operador le silencio como
    aprovacao. A LISTA de slugs e a razao de cada recusa exigem `compact`/
    `full` -- so a contagem basta para saber que ela existe.
    """
    if detail_level == "full":
        return payload
    if detail_level == "compact":
        projetado = dict(payload)
        projetado["capabilities"] = sorted(payload["capabilities"])
        del projetado["unresolved_detail"]
        return projetado
    # minimal
    return {
        "version": payload["version"],
        "covers": payload["covers"],
        "capabilities_count": len(payload["capabilities"]),
        "deprecated": sorted(payload["deprecated"]),
        "unresolved_count": len(payload["unresolved"]),
    }


def controlm_describe(version: str, detail_level: str = "full") -> dict[str, Any]:
    """O que vale numa versao do Control-M Automation API, segundo a pagina
    What's New da BMC e so ela.

    Responde a pergunta do operador que atua em varios clientes -- *"estou na
    `9.0.21.300`, o que posso usar?"* -- com as capacidades cuja fronteira ja
    passou, as que ja foram depreciadas ou descontinuadas, e as exigencias de
    componente em vigor. Cada item carrega `declared_at`, a versao onde a
    fronteira foi LIDA, para que a resposta sobre Java em `9.0.22.060` diga na
    propria linha que vem de `9.0.21.325`.

    VERSAO FORA DA FAIXA E RECUSA NOMEADA, com o intervalo que a matriz
    sustenta, e ha DUAS: `version_outside_covered_range` (a faixa e passado
    fechado -- a fonte publica ate `9.0.22.125`, e trazer isso exige LER, nao
    extrapolar) e `version_not_published_by_source` (dentro da faixa, e a fonte
    anda de 5 em 5: `9.0.21.301` nao existe, e responder pelo degrau de baixo
    seria interpolar entre duas versoes observadas).

    `detail_level` e proprio deste verbo -- ver `_project_controlm_describe` e
    o comentario acima de `NIVEIS_DE_DETALHE_CONTROLM` para a razao do shape
    nao caber em `NIVEIS_DE_DETALHE`/`project_items`, o mecanismo das outras 27
    tools de FACT.
    """
    if detail_level not in NIVEIS_DE_DETALHE_CONTROLM:
        raise AdapterError(
            f"detail_level invalido: {detail_level!r}; use um de "
            f"{NIVEIS_DE_DETALHE_CONTROLM}",
            exit_code=2,
        )
    try:
        payload = describe_controlm(version).to_dict()
    except UnknownControlMVersion as exc:
        conhecidas = known_controlm_versions()
        raise AdapterError(
            f"{exc}\n"
            f"  A matriz e do Control-M AUTOMATION API, nao do produto Control-M:\n"
            f"  as duas coisas usam a grafia `9.0.2x.yyy` e nao sao a mesma.\n"
            f"    sparkforge controlm describe --version "
            f"{(conhecidas or ('<versao>',))[0]}",
            exit_code=2,
        ) from exc
    return _project_controlm_describe(payload, detail_level)


# --------------------------------------------------------------------------- #
# analyze controlm-jobs
# --------------------------------------------------------------------------- #
#
# A VERSAO E PARAMETRO, E ELA E OPCIONAL DE PROPOSITO. `--version` ausente NAO e
# erro: o extrator le o artefato do mesmo jeito, emite folder, job, agendamento,
# dependencia, acao e variavel, e devolve as capacidades observadas em
# `ctm.capability_unresolved` com `reason: version_not_declared` e a medida que
# as destrava. Exigir a versao faria o operador que so quer INVENTARIAR os jobs
# ter de inventar um numero -- e um numero inventado atravessaria o cruzamento e
# viraria achado.
#
# A FRONTEIRA DESTE VERBO, repetida onde a superficie a expoe: ele le DEFINICAO
# de job, que e codigo-fonte, e nunca execucao. Nada aqui diz se o job rodou, em
# quanto tempo, ou se a dependencia foi satisfeita -- isso e `run jobs:status`,
# outra API, e exige a instancia do Control-M que este caminho nao tem.


def _extract_controlm_jobs_facts(path: str, version: str | None) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o diretorio com definicoes `Jobs-as-Code` ou para um "
            f"arquivo .json:\n"
            f"    sparkforge analyze controlm-jobs --path jobs/ --version 9.0.21.300 "
            f"--out .sparkforge/facts_controlm.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_controlm_jobs_tree(target, repo_root=target, declared_version=version)
    return extract_controlm_jobs_path(
        target, repo_root=target.parent, declared_version=version
    )


def analyze_controlm_jobs(
    path: str,
    version: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_controlm_jobs_facts(path, version)
    return _facts_page(facts, "ctm.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# benchmark
# --------------------------------------------------------------------------- #


def benchmark_runs(
    before_path: str,
    after_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    before_runtime: str = "",
    after_runtime: str = "",
    detail_level: str = "full",
) -> dict[str, Any]:
    """Compara DOIS arquivos de facts de event log (`analyze event-log --out`)
    e emite os fatos `bench.*`. Funcao pura sobre Facts: nao executa Spark, nao
    le event log cru, nao mede relogio -- ver docstring de
    `sparkforge.facts.benchmark`.

    Verbo de TOPO, e nao `analyze benchmark`: os verbos sob `analyze` extraem
    facts de um artefato, e este nao extrai nada -- ele compara dois conjuntos
    ja extraidos. Mesma razao pela qual `fuse` e verbo proprio.

    COM `unresolved` proprio, ao contrario de `analyze_call_graph`: este modulo
    TEM ponto cego para reportar. `bench.unresolved` sai quando falta o
    `spark.log_analyzed` de um lado, quando uma medida esta ausente ou
    incompleta num lado, ou quando um simbolo casado perdeu a medida -- casos em
    que a comparacao nao se sustenta e o silencio seria indistinguivel de
    "nenhuma diferenca". O `path_hint` e `"<antes>..<depois>"` porque o fato
    afirma sobre o PAR, nao sobre um dos dois arquivos.

    `before_runtime`/`after_runtime` sao os rotulos da secao 52. Opcionais: uma
    comparacao entre duas execucoes no MESMO runtime continua valendo, e e o
    caso de medir uma mudanca de codigo. O que eles acrescentam e o eixo que
    distingue "ficou mais rapido" de "ficou mais rapido AO TROCAR DE RUNTIME".
    """
    before = _load_facts_file(before_path, _FACTS_FROM_EVENT_LOG, "--before")
    after = _load_facts_file(after_path, _FACTS_FROM_EVENT_LOG, "--after")
    facts = build_benchmark(
        before,
        after,
        path_hint=f"{before_path}..{after_path}",
        before_runtime=before_runtime,
        after_runtime=after_runtime,
    )
    return _facts_page(facts, "bench.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# workload
# --------------------------------------------------------------------------- #

_FACTS_FROM_SQL_METRICS = (
    "sparkforge analyze sql-metrics --path <event-log.jsonl> --out {path}"
)
_FACTS_FROM_GLUE_JOB_RUNS = (
    "sparkforge analyze glue-job-runs --path <dir> --job-name <job> --out {path}"
)


def workload_fingerprint(
    facts_path: str,
    job_name: str,
    job_run_id: str,
    history_path: str = "",
) -> dict[str, Any]:
    """Monta o WorkloadFingerprint a partir de facts ja extraidos.

    Verbo de TOPO, e nao `analyze workload`, pela mesma razao de `benchmark` e
    `fuse`: os verbos sob `analyze` extraem facts de um artefato, e este nao
    extrai nada -- ele classifica o que outros verbos ja extrairam.

    `history_path` e um DIRETORIO, e nao um arquivo: um arquivo de facts por
    run anterior. A separacao por ARQUIVO e o que identifica cada run --
    `execution_id` e por aplicacao, e dois event logs diferentes colidem
    nele, entao uniar tudo num conjunto so apagaria a fronteira entre runs
    que a escala do historico precisa. Cada `*.json` do diretorio vira UM
    elemento da sequencia `history` que `build_fingerprint` espera (uma
    sequencia de conjuntos de facts, um por run anterior) -- nunca um unico
    conjunto fundido.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_SQL_METRICS, "--facts")
    history: list[list[Fact]] = []
    if history_path:
        history = _load_facts_dir(history_path, _FACTS_FROM_GLUE_JOB_RUNS, "--history")
    fingerprint = build_fingerprint(
        facts, job_name=job_name, job_run_id=job_run_id, history=history
    )
    return fingerprint.to_dict()


# --------------------------------------------------------------------------- #
# capacity
# --------------------------------------------------------------------------- #

_FACTS_FROM_RUN_AND_SCAN = (
    "por run anterior: sparkforge analyze glue-job-runs --path <dir> --job-name <job> "
    "--out {path}\n"
    "    e sparkforge analyze sql-metrics --path <event-log-do-run>.jsonl --out {path}"
)


def capacity_plan(
    facts_path: str,
    job_name: str,
    job_run_id: str,
    history_path: str = "",
) -> dict[str, Any]:
    """Escolhe a capacidade mais barata que cumpre o SLA, entre as observadas.

    Verbo de TOPO, e nao `analyze capacity`, pela mesma razao de `benchmark`,
    `fuse` e `workload`: nao extrai nada de artefato -- decide sobre o que
    outros verbos ja extrairam.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_RUN_AND_SCAN, "--facts")
    historico: list[list[Fact]] = []
    if history_path:
        historico = _load_facts_dir(history_path, _FACTS_FROM_RUN_AND_SCAN, "--history")
    plano = build_capacity_plan(
        facts, job_name=job_name, job_run_id=job_run_id, history=historico
    )
    return plano.to_dict()


# --------------------------------------------------------------------------- #
# finops
# --------------------------------------------------------------------------- #


def finops_report(facts_path: str, job_name: str) -> dict[str, Any]:
    """Reune o financeiro: custo, a troca recurso-tempo, e onde a alavanca esta.

    Verbo de TOPO pela mesma razao de `benchmark`, `fuse`, `workload` e
    `capacity`: consome facts ja extraidos e nao le artefato nenhum.

    Os achados vem do `judge` sobre os MESMOS facts -- `build_finops_report`
    nao escreve regra nenhuma, so agrupa o que o motor ja produz sob o eixo
    financeiro.

    O runtime para o `judge` e montado exatamente como em `judge_findings`:
    `build_runtime_context` com as flags de versao ausentes e `facts=facts`,
    para que um `env.runtime_signal` ja extraido baste. Este verbo nao expoe
    flag de runtime propria -- a superficie que o Step 1 cobre e so
    `--facts`/`--job-name` -- entao "so opcional" aqui significa "so vem dos
    facts", a mesma forma que `judge_findings` usa quando quem chama nao
    informa nenhuma flag.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_RUN_AND_SCAN, "--facts")
    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc
    runtime = build_runtime_context(facts=facts).to_dict()
    findings, _skipped = run_judge(facts, rules, runtime, return_skipped=True)
    return build_finops_report(facts, job_name=job_name, findings=findings)


# --------------------------------------------------------------------------- #
# tune
# --------------------------------------------------------------------------- #


def tune_conf(facts_path: str) -> dict[str, Any]:
    """Deriva configuracao Spark do que foi medido, com procedencia por chave.

    Verbo de TOPO pela mesma razao de `benchmark`, `fuse`, `workload`,
    `capacity` e `finops`: consome facts ja extraidos e nao le artefato nenhum.

    O runtime e montado como em `finops_report` -- `build_runtime_context` com
    `facts=facts` --, porque a versao decide o SIGNIFICADO do numero derivado:
    com AQE default, `spark.sql.shuffle.partitions` e piso inicial; sem AQE, e
    o numero final de particoes.

    Nada aqui aplica configuracao. O relatorio nomeia o nivel de seguranca de
    cada proposta, e `REVIEW` significa que alguem olha antes.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_RUN_AND_SCAN, "--facts")
    runtime = build_runtime_context(facts=facts).to_dict()
    return build_conf_advice(facts, runtime=runtime)


# --------------------------------------------------------------------------- #
# economy
# --------------------------------------------------------------------------- #


def economy_report(run_id: str, host_transcript: str = "") -> dict[str, Any]:
    """O que esta execucao poe na janela de contexto.

    Verbo de TOPO pela mesma razao de `capacity`, `finops` e `tune`: compoe
    sobre o ledger e nao le artefato nenhum.

    `host_transcript` e opcional porque o token de provider e do HOST: sem ele,
    o relatorio traz byte medido e `tokens_unresolved` -- nunca uma estimativa
    com nome de token.

    `shared_ledger()`, E NAO UM `ContextLedger()` PROPRIO. Achado do revisor:
    uma instancia independente aqui so enxergava o que ja tinha ido para o
    disco -- e dentro do MESMO processo que `adapters/tools.py:call_tool`
    acabou de gravar, nada tinha ido para o disco ainda (o unico gatilho
    automatico e o `atexit`, que so dispara quando o processo morre). Numa
    sessao MCP de vida longa isso deixava este relatorio sempre vazio ATE o
    processo terminar. Compartilhar a instancia com `call_tool` faz este
    verbo enxergar o buffer em memoria tambem, sem esperar flush nenhum.
    """
    return build_context_report(
        shared_ledger(),
        run_id=run_id,
        host_transcript=host_transcript or None,
    )


# --------------------------------------------------------------------------- #
# funcval
# --------------------------------------------------------------------------- #


def _write_facts_artifact(
    out_path: str, facts: list[Fact], label: str, example: str
) -> None:
    """Grava a lista COMPLETA de facts (nunca a pagina) no caminho pedido.

    A escrita mora aqui, e nao na CLI como nos verbos de `analyze`, porque
    nenhum dos dois arquivos de `funcval` e so uma saida legivel: o plano e o
    ARTEFATO que `funcval compare --plan` rele e que o gate
    `functional_validation_defined` cobra, e a comparacao e o arquivo que
    `judge --facts` le (D-4c-26). Um cliente MCP que so recebesse
    `structuredContent` teria a capacidade pela CLI e nao pelo MCP -- a
    assimetria que `parity.yaml` existe para pegar, e a mesma razao pela qual
    `report sign` escreve em vez de devolver o bloco para alguem colar.

    `example` e o comando do verbo QUE CHAMOU, e nao um exemplo fixo: mandar
    quem errou o diretorio no `compare` rodar um `plan` seria o motor sugerindo
    o passo errado no unico momento em que a pessoa esta seguindo a sugestao.
    """
    target = Path(out_path)
    if not target.parent.exists():
        raise AdapterError(
            f"Diretorio nao encontrado para {label}: {target.parent}\n"
            f"  Crie o diretorio antes, ou aponte para um caminho existente:\n"
            f"    {example}",
            exit_code=2,
        )
    target.write_text(
        json.dumps([f.to_dict() for f in facts], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def funcval_plan(
    facts_paths: list[str] | None,
    out_path: str,
    keys: list[str] | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Deriva o plano de validacao funcional dos facts ja extraidos e o grava.

    Verbo de TOPO, como `benchmark` e `fuse`, e nao `analyze funcval`: tudo sob
    `analyze` extrai facts de um artefato, e este nao extrai nada -- deriva de
    facts que outro verbo ja produziu. Funcao pura sobre Facts: nunca executa
    consulta, nunca le a tabela, nunca chama AWS. Ver a docstring de
    `sparkforge.facts.funcval` para o que o plano pode e nao pode afirmar.

    `facts_paths` e REPETIVEL, e isso e medido e nao estetico: o alvo sai de
    `pyspark.write` (`analyze pyspark --out`) e o schema e os agregados saem de
    `catalog.table_schema` (`analyze catalog-schema --out`). Nenhum verbo produz
    os dois no mesmo arquivo, entao com `--facts` unico os eixos de schema e de
    agregado seriam inalcancaveis -- a mesma razao que ja tornou `judge --facts`
    e `fuse --facts` repetiveis, e o mesmo passo manual de concatenar dois
    arrays JSON que, quando ninguem faz, so faz a capacidade nunca disparar.

    `keys` sao as chaves de negocio DECLARADAS pelo operador (`--key`), cada
    elemento uma chave (composta quando tem virgula). Elas entram declaradas
    porque nenhum kind que os extratores emitem nomeia chave de negocio
    (D-4c-1, D-4c-2); sem elas o plano nao inventa o eixo -- ele o escreve como
    ausente em `undeclared_axes`.

    `out_path` e OBRIGATORIO, ao contrario do `--out` opcional dos verbos de
    `analyze`: la o arquivo e conveniencia, aqui ele e a entrada do proximo
    verbo e a evidencia do gate. Plano que so passa pelo stdout nao e artefato,
    e a Task 1 recusou `.sparkforge/keys.yaml` justamente porque este arquivo ja
    da ao declarado um registro auditavel.
    """
    if not facts_paths:
        raise AdapterError(
            "informe ao menos um --facts (arquivo gerado por `analyze pyspark --out` "
            "ou `analyze catalog-schema --out`). Repetivel de proposito: o alvo vem do "
            "`pyspark.write` e o schema/os agregados vem do `catalog.table_schema`, e "
            "nenhum verbo produz os dois no mesmo arquivo.",
            exit_code=2,
        )
    facts = _merge_facts_files(list(facts_paths), _FACTS_FROM_PYSPARK_OR_CATALOG)
    derived = build_plan(
        facts, keys=tuple(keys or ()), path_hint="+".join(facts_paths)
    )
    _write_facts_artifact(
        out_path,
        derived,
        "--out",
        "sparkforge funcval plan --facts <facts.json> --out .sparkforge/plan.json",
    )
    return _facts_page(derived, "funcval.unresolved", kind, limit, cursor, detail_level)


def _load_result_file(result_path: str, label: str) -> dict[str, Any]:
    """Um dos dois resultados que o OPERADOR mediu, no contrato minimo da fase.

    Nao e um arquivo de facts: e o objeto `{"target", "checks"}` que quem rodou
    a consulta escreveu. O motor nunca produz este arquivo -- se produzisse,
    estaria medindo, e a fase inteira afirma que quem mede e o operador.
    """
    path = Path(result_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de resultado nao encontrado para {label}: {result_path}\n"
            f"  O resultado e MEDIDO POR VOCE em cada lado -- o sparkforge nunca executa\n"
            f"  consulta. Derive o que medir e escreva um JSON por lado:\n"
            f"    sparkforge funcval plan --facts <facts.json> --out <plano.json>\n"
            f'    {{"target": "db.vendas", "checks": {{"count": {{"value": 1000}}}}}}',
            exit_code=2,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{result_path}: JSON invalido: {exc}", exit_code=2) from exc
    if not isinstance(payload, dict):
        raise AdapterError(
            f"{result_path}: o resultado de {label} precisa ser um OBJETO com `target` e "
            f"`checks`, nao {type(payload).__name__}. Rode "
            f"`sparkforge funcval plan --help` para o contrato.",
            exit_code=2,
        )
    return payload


def _pick_plan(
    plans: list[Fact], before: dict[str, Any], after: dict[str, Any], plan_path: str
) -> Fact:
    """O plano contra o qual comparar, quando o arquivo carrega mais de um.

    `funcval plan` emite UM plano por alvo distinto (D-4c-4), e o resultado do
    operador descreve UM alvo. Com varios planos no arquivo, alguem tem que
    escolher, e escolher errado e comparar numeros de tabelas diferentes -- pior
    do que nao comparar. Entao a escolha e por casamento exato de alvo, e a
    ambiguidade vira erro de fronteira em vez de palpite: comparar contra TODOS
    produziria N-1 sentinelas bloqueadas, e `SF-FVAL-005` leria cada uma delas
    como cobertura faltante de um alvo que o operador nunca quis comparar.
    """
    if len(plans) == 1:
        return plans[0]
    wanted = {str(result.get("target", "") or "") for result in (before, after)}
    matches = [plan for plan in plans if str(plan.attrs.get("target", "")) in wanted]
    if len(matches) == 1:
        return matches[0]
    targets = sorted(str(plan.attrs.get("target", "")) for plan in plans)
    raise AdapterError(
        f"{plan_path} tem {len(plans)} planos (um por alvo: {targets}), e o par de "
        f"resultados nomeia {sorted(wanted)}.\n"
        f"  Um resultado descreve UM alvo, e escolher por conta seria comparar numeros "
        f"de tabelas diferentes.\n"
        f"  Informe resultados do mesmo alvo, ou gere o plano do alvo que voce mediu:\n"
        f"    sparkforge funcval plan --facts <facts.json> --out <plano.json>",
        exit_code=2,
    )


def _reject_foreign_plan_ref(
    plan_fact: Fact, before: dict[str, Any], after: dict[str, Any], plan_path: str
) -> None:
    """O ponto cego que `build_comparison` nao consegue enxergar sozinho.

    O modulo recebe o `attrs` do plano, nunca o Fact, entao ele so acusa
    `plan_ref` quando os DOIS lados discordam ENTRE SI (D-4c-13). Os dois lados
    citando o MESMO `plan_ref` de um plano ANTIGO passam batido: a comparacao
    sairia inteira, sob checks que ninguem pediu, com cara de comparacao valida.
    Quem tem o `Fact.id` real e este chamador, entao a verificacao e dele.

    Recusa em vez de emitir fact: um `funcval.unresolved` construido aqui seria
    o adaptador afirmando sobre o dominio, e nenhum adaptador deste repositorio
    constroi Fact. O precedente do lado da validacao e o mesmo -- `validate
    --facts` so cobra a PERTINENCIA do `benchmark_ref` quando tem o arquivo em
    maos, e reprova quando o `fact_id` citado nao esta la dentro.

    Silencio quando os dois discordam entre si: ali o modulo JA bloqueia com
    `plan_ref_conflict`, e roubar esse caso dele apagaria a sentinela bloqueada
    que a `SF-FVAL-005` precisa ver.
    """
    refs = {str(result.get("plan_ref", "") or "") for result in (before, after)}
    refs.discard("")
    if len(refs) != 1:
        return
    ref = next(iter(refs))
    if ref == plan_fact.id:
        return
    raise AdapterError(
        f"Os resultados citam plan_ref {ref}, e o plano de "
        f"'{plan_fact.attrs.get('target', '')}' em {plan_path} e {plan_fact.id}.\n"
        f"  Os dois lados foram medidos contra OUTRO plano: compara-los contra este "
        f"seria julga-los sob checks que ninguem pediu.\n"
        f"  Informe o plano contra o qual eles foram medidos, ou refaca a medicao:\n"
        f"    sparkforge funcval plan --facts <facts.json> --out <plano.json>",
        exit_code=2,
    )


def funcval_compare(
    plan_path: str,
    before_path: str,
    after_path: str,
    out_path: str | None = None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Compara os DOIS resultados do operador contra o plano, e emite `funcval.*`.

    `plan_path` e o arquivo escrito por `funcval plan --out`; `before_path` e
    `after_path` sao os resultados que o operador mediu de cada lado, no
    contrato minimo (`target`, `checks` com presenca por chave, cada check um
    objeto `{"value": ...}` e `value: null` exigindo `unavailable_reason`).

    A comparacao e sempre ANTES contra DEPOIS, nunca observado contra catalogo
    (D-4c-3): o schema declarado serve para saber QUAIS colunas existem, e nada
    mais. E o veredito de ponto flutuante nao sai daqui nem do modulo -- ele sai
    de `SF-FVAL-004` contra `threshold.relative_tolerance`, porque um `diverged`
    de float seria um limiar dentro de um Fact.

    COM `unresolved` proprio, como `benchmark`: check que veio de um lado so,
    check que rodou e nao deu, check que o plano pediu e nao veio, e os tres
    bloqueios de comparacao inteira sao pontos cegos de verdade, e silencio ali
    seria indistinguivel de "nenhuma divergencia".

    `out_path` e OPCIONAL, ao contrario do `--out` do plano, e a diferenca nao e
    esquecimento: o plano e a ENTRADA deste verbo e a evidencia do gate, entao
    plano sem arquivo nao serve para nada; a comparacao e saida terminal, e o
    arquivo dela e a mesma conveniencia que `benchmark` e `fuse` oferecem. O que
    ele conserta e a D-4c-26: `judge --facts` le ARQUIVO, e sem `--out` o
    operador tinha que extrair `items` do envelope com `jq` ou `python -c` entre
    os dois passos. Pior que o passo a mais: o envelope PAGINA (`--limit` vale
    50 por default), entao quem extrai `items` sem conferir `next_cursor` julga a
    primeira pagina e chama aquilo de comparacao -- o defeito que a
    `SF-FVAL-005` acusa no dado do operador, cometido pelo fluxo do motor.

    Por isso o arquivo traz a lista COMPLETA e nao a pagina: a escrita acontece
    ANTES de `_facts_page`, sobre `facts`. Um `--out` que gravasse a pagina seria
    a mesma armadilha com o nome trocado.

    A escrita mora aqui e nao na CLI pelo mesmo motivo do plano: um cliente MCP
    que so recebesse `structuredContent` teria pela CLI uma capacidade que nao
    tem pelo MCP, e a assimetria entre as duas superficies e defeito por si so.
    """
    plan_facts = _load_facts_file(plan_path, _FACTS_FROM_FUNCVAL_PLAN, "--plan")
    plans = [fact for fact in plan_facts if fact.kind == "funcval.plan"]
    if not plans:
        raise AdapterError(
            f"{plan_path} nao tem nenhum fact `funcval.plan`.\n"
            f"  Sem alvo derivado nao ha o que comparar -- o arquivo pode ser so os\n"
            f"  `funcval.unresolved` de um corpus sem `pyspark.write`. Produza o plano:\n"
            f"    sparkforge funcval plan --facts <facts.json> --out {plan_path}",
            exit_code=2,
        )
    before = _load_result_file(before_path, "--before")
    after = _load_result_file(after_path, "--after")

    chosen = _pick_plan(plans, before, after, plan_path)
    _reject_foreign_plan_ref(chosen, before, after, plan_path)

    facts = build_comparison(
        chosen.attrs, before, after, path_hint=f"{before_path}..{after_path}"
    )
    if out_path:
        _write_facts_artifact(
            out_path,
            facts,
            "--out",
            "sparkforge funcval compare --plan <plano.json> --before <antes.json> "
            "--after <depois.json> --out .sparkforge/funcval.json",
        )
    return _facts_page(facts, "funcval.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# fuse
# --------------------------------------------------------------------------- #


def fuse_facts(
    facts_paths: list[str] | None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """Combina um ou mais arquivos de facts (`analyze pyspark --out`,
    `analyze catalog-schema --out`, ou qualquer outro produtor de facts) e
    roda `sparkforge.facts.fusion.fuse` sobre a uniao.

    `--facts` e repetivel de proposito: fusao so tem o que correlacionar
    quando ve facts de mais de uma fonte na MESMA chamada (texto SQL de um
    lado, schema do catalogo do outro) -- diferente de `judge --facts`, que
    aceita um unico arquivo porque so julga o que ja esta combinado. A saida
    de `fuse` (facts originais + `.enriched` + `fusion.summary`, ver docstring
    de `sparkforge/facts/fusion.py`) e desenhada para alimentar `judge --facts`
    direto, sem outro passo de combinacao no meio.
    """
    if not facts_paths:
        raise AdapterError(
            "informe ao menos um --facts (arquivo gerado por `analyze pyspark --out` "
            "ou `analyze catalog-schema --out`). Repetivel para combinar as fontes "
            "que a fusao precisa correlacionar.",
            exit_code=2,
        )

    combined: list[Fact] = []
    for facts_path in facts_paths:
        combined.extend(_load_facts_file(facts_path))

    fused = run_fuse(combined)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in fused if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)
    page, procedencias, versao_do_schema = project_items(page, detail_level)

    summary = next((f for f in fused if f.kind == "fusion.summary"), None)

    resultado: dict[str, Any] = {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "kind": list(kind) if kind else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_kind": by_kind,
        "summary": summary.to_dict() if summary is not None else None,
        "items": page,
    }
    declarar_no_envelope(resultado, procedencias, versao_do_schema)
    return resultado


# --------------------------------------------------------------------------- #
# judge
# --------------------------------------------------------------------------- #


def _facts_from_dicts(payload: Any) -> list[Fact]:
    if not isinstance(payload, list):
        raise AdapterError("facts precisa ser uma lista de objetos fact.", exit_code=2)

    facts: list[Fact] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise AdapterError(f"facts[{index}] nao e um objeto.", exit_code=2)
        try:
            kwargs: dict[str, Any] = {"kind": entry["kind"], "subject": entry["subject"]}
        except KeyError as exc:
            raise AdapterError(
                f"facts[{index}] esta sem o campo obrigatorio {exc}. O arquivo de facts "
                "pode ter sido gerado por uma versao antiga do schema. Rode "
                "`sparkforge analyze pyspark --path <dir> --out <arquivo>` novamente.",
                exit_code=2,
            ) from exc
        for optional in ("measures", "attrs", "provenance", "schema_version"):
            if optional in entry:
                kwargs[optional] = entry[optional]
        facts.append(Fact(**kwargs))
    return facts


# O verbo que produz o arquivo de facts DEPENDE do chamador, e cravar um so
# produzia mensagem inacionavel: `benchmark` le a saida de `analyze event-log`,
# nunca a de `analyze pyspark`. `label` existe pela mesma razao que em
# `analyze_terraform_diff` -- com dois arquivos na linha de comando, "arquivo nao
# encontrado" nao diz qual dos dois refazer.
_FACTS_FROM_PYSPARK = "sparkforge analyze pyspark --path <dir> --out {path}"
_FACTS_FROM_EVENT_LOG = "sparkforge analyze event-log --path <event-log.jsonl> --out {path}"
_FACTS_FROM_BENCHMARK = "sparkforge benchmark --before <antes> --after <depois> --out {path}"

# `funcval plan` come de DOIS verbos, e o hint diz os dois: o alvo sai de
# `pyspark.write` e o schema/os agregados saem de `catalog.table_schema`. Cravar
# so o primeiro mandaria o operador refazer a extracao que ele ja tem.
_FACTS_FROM_PYSPARK_OR_CATALOG = (
    "sparkforge analyze pyspark --path <dir> --out {path}\n"
    "    sparkforge analyze catalog-schema --path <dump.json> --out {path}"
)
_FACTS_FROM_FUNCVAL_PLAN = "sparkforge funcval plan --facts <facts.json> --out {path}"


def _load_facts_file(
    facts_path: str,
    producer: str = _FACTS_FROM_PYSPARK,
    label: str | None = None,
) -> list[Fact]:
    path = Path(facts_path)
    if not path.is_file():
        side = f" para {label}" if label else ""
        raise AdapterError(
            f"Arquivo de facts nao encontrado{side}: {facts_path}\n"
            f"  Rode o verbo que produz este lado:\n"
            f"    {producer.format(path=facts_path)}",
            exit_code=2,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{facts_path}: JSON invalido: {exc}", exit_code=2) from exc
    return _facts_from_dicts(raw)


def _load_facts_dir(
    dir_path: str,
    producer: str = _FACTS_FROM_GLUE_JOB_RUNS,
    label: str = "--history",
) -> list[list[Fact]]:
    """Carrega um DIRETORIO de historico: um arquivo de facts por run anterior.

    Compartilhado por `workload_fingerprint` e `capacity_plan` -- os dois
    esperam a mesma forma de historico (uma sequencia de conjuntos de facts,
    um por run) e a mesma razao de separar por ARQUIVO: `execution_id` e por
    aplicacao, e dois event logs diferentes colidem nele, entao uniar tudo
    num conjunto so apagaria a fronteira entre runs que a escala do historico
    precisa. Cada `*.json` do diretorio vira UM elemento da sequencia
    devolvida, nunca um unico conjunto fundido.
    """
    hist_dir = Path(dir_path)
    if not hist_dir.is_dir():
        raise AdapterError(
            f"Diretorio de historico nao encontrado: {dir_path}\n"
            f"  Rode o verbo que produz os facts de cada run e grave um "
            f"arquivo por run neste diretorio:\n"
            f"    {producer.format(path='<um-arquivo-por-run>.json')}",
            exit_code=2,
        )
    return [
        _load_facts_file(str(run_file), producer, label)
        for run_file in sorted(hist_dir.glob("*.json"))
    ]


def _merge_facts_files(
    facts_paths: list[str], producer: str = _FACTS_FROM_PYSPARK
) -> list[Fact]:
    """Une varios arquivos de facts numa lista unica, sem duplicata e ordenada.

    `producer` existe pelo mesmo motivo que em `_load_facts_file`: quem une os
    arquivos decide qual verbo os produz, e `funcval plan` une a saida de
    `analyze pyspark` com a de `analyze catalog-schema`. O default preserva o
    comportamento de `judge`, o unico chamador anterior.

    `judge` correlaciona facts de extratores diferentes (`SF-GLUE-004` cruza
    `tf.attribute` com `pyspark.write`), e cada extrator escreve o seu proprio
    arquivo. Sem uniao aqui, avaliar essa classe de regra exigia concatenar
    dois arrays JSON na mao -- passo manual que, quando ninguem faz, apenas
    faz a regra nunca disparar.

    A deduplicacao e por conteudo do que o fact AFIRMA (kind + subject +
    measures + attrs), nao por provenance: dois arquivos que se sobrepoem
    descrevem a mesma observacao uma vez so. Sem isso, o mesmo fact viraria
    duas entradas em `Finding.evidence` e o achado pareceria duas vezes mais
    sustentado do que e. `sort_facts` no fim e a mesma normalizacao que
    `judge` ja aplica -- a ordem passa a depender do conteudo, nunca da ordem
    em que os arquivos foram informados na linha de comando.
    """
    seen: set[str] = set()
    merged: list[Fact] = []
    for facts_path in facts_paths:
        for fact in _load_facts_file(facts_path, producer):
            key = json.dumps(
                {
                    "kind": fact.kind,
                    "subject": fact.subject,
                    "measures": fact.measures,
                    "attrs": fact.attrs,
                },
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(fact)
    return sort_facts(merged)


def judge_findings(
    facts: list[dict[str, Any]] | None = None,
    facts_path: str | list[str] | None = None,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    emr: str | None = None,
    severity: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    show_skipped: bool = False,
) -> dict[str, Any]:
    if facts is not None:
        fact_list = _facts_from_dicts(facts)
    elif facts_path is not None:
        # `facts_path` aceita um caminho ou uma lista deles: uma regra pode
        # exigir facts de mais de um extrator (SF-GLUE-004) e cada extrator
        # escreve o seu arquivo. Um caminho unico continua valendo -- e a forma
        # que toda skill documenta.
        paths = [facts_path] if isinstance(facts_path, str) else list(facts_path)
        if not paths:
            raise AdapterError(
                "informe ao menos um `facts_path` (arquivo gerado por "
                "`sparkforge analyze pyspark --out <arquivo>`).",
                exit_code=2,
            )
        fact_list = _merge_facts_files(paths)
    else:
        raise AdapterError(
            "informe `facts` (lista inline de facts) ou `facts_path` (arquivo gerado por "
            "`sparkforge analyze pyspark --out <arquivo>`).",
            exit_code=2,
        )

    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    # O contexto e montado DEPOIS de `fact_list` existir e ANTES de `run_judge`
    # -- e `run_judge` que chama `in_scope`. Os facts que serao julgados sao os
    # mesmos que alimentam a deteccao: uma regra guardada por `glue: "*"` passa
    # a avaliar quando o Terraform ja disse qual e a versao, sem flag nenhuma.
    context = build_runtime_context(
        glue, spark, python, iceberg, athena, facts=fact_list, emr=emr
    )
    runtime = context.to_dict()

    findings, skipped = run_judge(fact_list, rules, runtime, return_skipped=True)
    finding_dicts = [f.to_dict() for f in findings]

    if severity:
        wanted = set(severity)
        finding_dicts = [f for f in finding_dicts if f["severity"] in wanted]

    by_severity = _count_by(finding_dicts, lambda f: f["severity"])
    page, next_cursor = paginate_items(finding_dicts, limit, cursor)

    result: dict[str, Any] = {
        "total_count": len(finding_dicts),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "severity": list(severity) if severity else None,
            "limit": limit,
            "cursor": cursor,
        },
        "by_severity": by_severity,
        # O runtime EFETIVAMENTE usado para filtrar por versao, sempre -- nao
        # so quando `show_skipped`. Agora que ele pode vir dos facts e nao so
        # das flags, omiti-lo tornaria invisivel a unica coisa que explica por
        # que uma regra avaliou ou foi pulada. E carrega `divergences`: com
        # flag e fact discordando, a precedencia escolhe o valor reportado, mas
        # a discordancia aparece aqui em vez de ser resolvida em silencio.
        "runtime": runtime,
        "items": page,
    }
    if show_skipped:
        result["skipped"] = skipped
    return result


# --------------------------------------------------------------------------- #
# runtime detect
# --------------------------------------------------------------------------- #


def _facts_for_runtime(facts_path: str | list[str] | None) -> list[Fact] | None:
    """Facts opcionais para alimentar a deteccao de runtime.

    Mesma forma de `judge_findings`: um caminho ou varios. Ausente devolve
    `None`, que preserva o comportamento so-de-flags para quem nao informa
    nada.
    """
    if facts_path is None:
        return None
    paths = [facts_path] if isinstance(facts_path, str) else list(facts_path)
    return _merge_facts_files(paths) if paths else None


def runtime_detect(
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    facts_path: str | list[str] | None = None,
    emr: str | None = None,
) -> dict[str, Any]:
    return build_runtime_context(
        glue,
        spark,
        python,
        iceberg,
        athena,
        facts=_facts_for_runtime(facts_path),
        emr=emr,
    ).to_dict()


# --------------------------------------------------------------------------- #
# rules lookup
# --------------------------------------------------------------------------- #

# Citacao de knowledge no catalogo tem sempre a forma `knowledge/<caminho>.<ext>`.
# A revisao da Task 5 achou um falso positivo real: sem exigir um limite de
# token antes de `knowledge/`, o trecho "https://exemplo.com/knowledge/glue/x.md"
# tambem casava, porque o prefixo `knowledge/` aparece embutido numa URL alheia.
# O resultado virava uma citacao fantasma com `path: None` -- indistinguivel de
# uma citacao quebrada de verdade (o caso que `path: None` existe para sinalizar).
# `(?:^|(?<=[\s"'(]))` exige que `knowledge/` comece a citacao (inicio da string)
# ou venha logo apos espaco, aspas ou abre-parenteses -- nunca no meio de outro
# caminho ou URL. E zero-width (nao entra no texto casado), entao `ref` continua
# comecando exatamente em `knowledge/`.
_KNOWLEDGE_REF = re.compile(r"(?:^|(?<=[\s\"'(]))knowledge/[A-Za-z0-9_\-/]+\.(?:md|sql)")

# Campos-texto onde a citacao aparece hoje. `sources` fica de fora desta lista
# porque e uma lista de objetos, nao uma string/lista de strings como os demais
# -- precisa de tratamento proprio (ver `_source_notes_of`), nao porque nao
# tenha citacao: `SF-PY-002` cita `knowledge/spark/memory-and-oom.md` dentro de
# `sources[0].note`, e a Task 5 original omitia essa regra por varrer so estes
# campos. O que continua de fora, de proposito, e `sources[].url`: link externo,
# nunca caminho local.
_KNOWLEDGE_FIELDS = ("explanation", "proposed_change", "validation", "risks", "tradeoffs")


def _source_notes_of(rule: dict[str, Any]) -> list[str]:
    """`note` de cada entrada de `sources` -- texto livre que pode citar
    knowledge, ao contrario de `url` (link externo, nunca escaneado)."""
    return [
        str(source["note"])
        for source in rule.get("sources") or []
        if isinstance(source, dict) and source.get("note")
    ]


def _citations_of(rule: dict[str, Any]) -> list[str]:
    """Citacoes `knowledge/...` da regra, unicas e ordenadas, varrendo
    `_KNOWLEDGE_FIELDS` mais `sources[].note`."""
    parts = [str(rule.get(field, "")) for field in _KNOWLEDGE_FIELDS]
    parts.extend(_source_notes_of(rule))
    blob = " ".join(parts)
    return sorted(set(_KNOWLEDGE_REF.findall(blob)))


def _resolve_knowledge_refs(
    citations: list[str], root: Path | None, resolved: dict[str, str | None]
) -> list[dict[str, Any]]:
    """Resolve cada citacao contra `root`, reaproveitando `resolved` como cache
    entre chamadas (ver `rules_lookup`, que compartilha o mesmo dict por todas
    as regras da pagina): das citacoes do catalogo inteiro, so 11 arquivos sao
    unicos, entao a maioria das resolucoes repete um arquivo ja resolvido.

    O cache e um dict local passado pelo chamador, nunca um `lru_cache` de
    modulo: `root` pode mudar entre chamadas de processo longo (servidor MCP
    com `SPARKFORGE_KNOWLEDGE` trocada, ou uma reinstalacao no meio da sessao),
    e um cache de processo teria que ser invalidado manualmente para nao
    devolver `path` obsoleto. Escopar o cache a uma unica chamada de
    `rules_lookup` (ou de `knowledge_refs_of`, que cria o seu proprio) elimina
    esse risco de estale sem abrir mao do reaproveitamento -- o ganho medido
    (~12ms, ~10% de `rules_lookup(limit=100)`) nao justifica a complexidade
    extra de invalidacao que um cache mais longevo exigiria.
    """
    refs: list[dict[str, Any]] = []
    for ref in citations:
        if ref not in resolved:
            path: str | None = None
            if root is not None:
                try:
                    path = str(safe_knowledge_file(root, ref[len("knowledge/") :]))
                except KnowledgeError:
                    path = None
            resolved[ref] = path
        refs.append({"ref": ref, "path": resolved[ref]})
    return refs


def knowledge_refs_of(rule: dict[str, Any]) -> list[dict[str, Any]]:
    """Citacoes de knowledge da regra, com o caminho resolvido de cada uma.

    `path: None` significa citacao que nao resolve -- defeito de catalogo, e o
    relatorio precisa mostra-lo em vez de sumir com a citacao.

    `knowledge_dir()` e resolvido uma unica vez aqui fora do laco: a raiz nao
    muda entre citacoes da mesma regra, e repetir a chamada por citacao seria
    trabalho redundante sem nenhum ganho de corretude. `rules_lookup` vai alem
    disso e resolve a raiz uma unica vez para a pagina inteira, via
    `_resolve_knowledge_refs` direto -- ver a docstring dela.

    Ao contrario de `knowledge_path` (que devolve `_knowledge_root_missing`,
    um AdapterError, quando a raiz esta ausente ou invalida), aqui a raiz
    ausente vira `path: None` em cada citacao, nao uma excecao: `rules_lookup`
    tem que continuar respondendo o resto da regra (id, severidade, sources,
    ...) mesmo sem `knowledge/` instalado -- so a citacao especifica fica
    sem caminho, exatamente como uma citacao quebrada dentro de uma raiz
    valida.

    Uma imprecisao da primeira versao desta docstring: no cenario mais comum
    de raiz ausente -- pacote instalado por pip sem `knowledge/` embarcado --
    o `path: None` NAO vem deste `except KnowledgeError` em torno de
    `knowledge_dir()`. `knowledge_dir()` so levanta quando `SPARKFORGE_KNOWLEDGE`
    aponta para um caminho invalido; o fallback para o pacote (linha final de
    `knowledge_dir()`) devolve um `Path` sem checar `is_dir()`, entao `root`
    fica preenchido mesmo sem o diretorio existir. O `None` nesse caso vem do
    `except KnowledgeError` dentro de `_resolve_knowledge_refs`, por
    `safe_knowledge_file` falhar no `target.exists()`. O resultado observavel
    e o mesmo (`path: None`), mas a causa e outra -- e por isso `rules_lookup`
    nunca aponta o operador para `pip install --force-reinstall sparkforge-aws`
    do jeito que `knowledge_path` aponta: essa mensagem acionavel e
    responsabilidade de `knowledge_path`/`sparkforge knowledge path`, que o
    AGENT_PROTOCOL ja manda consultar antes de desistir de uma citacao. Duplicar
    o diagnostico aqui, por citacao, quebraria o contrato `{ref, path}` que os
    testes ja travam (`test_a_citation_pointing_nowhere_is_reported_not_silently_dropped`)
    por um ganho que o consumidor ja tem em outra tool.
    """
    citations = _citations_of(rule)
    if not citations:
        return []

    try:
        root = knowledge_dir()
    except KnowledgeError:
        root = None

    return _resolve_knowledge_refs(citations, root, {})


def rules_lookup(
    id: list[str] | None = None,  # noqa: A002 -- nome do parametro espelha o flag --id
    category: str | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    try:
        rules = load_catalog()
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    filtered = rules
    if id:
        wanted_ids = set(id)
        filtered = [r for r in filtered if r["id"] in wanted_ids]
    if category:
        filtered = [r for r in filtered if r.get("category") == category]

    by_category = _count_by(filtered, lambda r: r.get("category", ""))

    # Raiz resolvida uma vez para a pagina inteira (nao uma vez por regra) e
    # cache de resolucao compartilhado entre regras -- ver docstring de
    # `_resolve_knowledge_refs`.
    try:
        knowledge_root = knowledge_dir()
    except KnowledgeError:
        knowledge_root = None
    resolved_paths: dict[str, str | None] = {}

    clean = []
    for rule in filtered:
        entry = {k: v for k, v in rule.items() if k != "_source_file"}
        entry["knowledge_refs"] = _resolve_knowledge_refs(
            _citations_of(rule), knowledge_root, resolved_paths
        )
        clean.append(entry)
    page, next_cursor = paginate_items(clean, limit, cursor)

    return {
        "total_count": len(filtered),
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {
            "id": list(id) if id else None,
            "category": category,
            "limit": limit,
            "cursor": cursor,
        },
        "by_category": by_category,
        "rules": page,
    }


# --------------------------------------------------------------------------- #
# knowledge path
# --------------------------------------------------------------------------- #


def _knowledge_root_missing(cause: str) -> AdapterError:
    """Erro acionavel unico para toda causa de raiz de knowledge ausente ou
    invalida (env var errada, ou pacote sem knowledge/ embarcado). `cause` e a
    frase especifica (o que esta errado); as duas linhas de comando abaixo sao
    o que fazer a respeito -- sem elas o operador so sabe que algo esta
    errado, nao o proximo passo.
    """
    return AdapterError(
        f"{cause}\n"
        f"  Se voce tem o repositorio sparkforge-aws clonado, aponte para a "
        f"pasta knowledge/ dele:\n"
        f"    SPARKFORGE_KNOWLEDGE=<caminho-do-repo>/knowledge\n"
        f"  Sem o repositorio, reinstale o pacote -- a wheel >=0.5.0 embarca "
        f"knowledge/ dentro do site-packages:\n"
        f"    pip install --force-reinstall sparkforge-aws",
        exit_code=2,
    )


def knowledge_path(file: str | None = None) -> dict[str, Any]:
    """Resolve a raiz de knowledge, e opcionalmente um arquivo dentro dela.

    Sem `file`, devolve a raiz e a lista do que ha. Um consumidor instalado por
    pip nao tem como adivinhar o caminho dentro do site-packages, e listar e o
    que torna o verbo utilizavel sem tentativa e erro.

    `available` nao pagina, diferente de `rules_lookup`/`analyze_*`: sao 19
    arquivos estaticos, curados via `knowledge/INDEX.md` e embarcados no wheel
    -- nao cresce por acao do usuario como uma lista de findings ou regras.
    Paginar aqui seria complexidade sem consumidor. Revisite se `knowledge/`
    crescer para dezenas de arquivos por diretorio (o teste
    `test_available_list_stays_small_enough_to_not_need_pagination` em
    `tests/test_adapters_knowledge.py` falha propositalmente antes disso virar
    surpresa). Pelo mesmo motivo o `rglob` abaixo roda mesmo quando so `file`
    foi pedido: nao vale complicar o caminho feliz para evitar percorrer 19
    arquivos.
    """
    # `knowledge_dir()` espelha `catalog_dir()` e nao valida o fallback (ver a
    # docstring dela): a checagem tem que morar no consumidor, assim como
    # `load_catalog()` e quem valida `catalog_dir()`. Duas origens convergem
    # aqui -- `KnowledgeError` de `knowledge_dir()` (env var aponta para path
    # invalido) e o fallback sem validacao (pacote instalado sem knowledge/
    # embarcado) -- e as duas passam por `_knowledge_root_missing` para sair
    # com o mesmo comando de saida, como em `_extract_facts`: a causa sozinha
    # deixa o operador adivinhando entre corrigir a env var, reinstalar ou
    # clonar o repositorio, que e a forma mais barata de a ferramenta parecer
    # quebrada.
    try:
        root = knowledge_dir()
    except KnowledgeError as exc:
        raise _knowledge_root_missing(str(exc)) from exc

    if not root.is_dir():
        raise _knowledge_root_missing(f"diretorio de knowledge nao encontrado em {root}.")

    available = sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )

    resolved: str | None = None
    if file:
        try:
            resolved = str(safe_knowledge_file(root, file))
        except KnowledgeError as exc:
            raise AdapterError(str(exc), exit_code=2) from exc

    return {"root": str(root), "file": resolved, "available": available}


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #


def validate_output(
    finding: dict[str, Any], facts_path: str | None = None
) -> dict[str, Any]:
    """Valida um finding. Com `facts_path`, valida tambem a PERTINENCIA do
    `benchmark_ref`.

    Sem o arquivo, `validate_finding` so consegue cobrar a FORMA do
    `benchmark_ref` (`f_` + 6 hex) -- ele nao ve fact nenhum. Informando o
    arquivo de facts (tipicamente a saida de `sparkforge benchmark --out`), o
    `fact_id` citado passa a precisar existir la dentro. Opcional porque quem
    valida um achado avulso, sem os facts em mao, ainda merece a primeira
    camada.
    """
    fact_ids: set[str] | None = None
    if facts_path is not None:
        # O mesmo defeito do lado do benchmark: o `fact_id` que este caminho
        # procura e o de um `bench.run_delta`, e mandar rodar `analyze pyspark`
        # produziria um arquivo onde ele nunca vai estar.
        fact_ids = {fact.id for fact in _load_facts_file(facts_path, _FACTS_FROM_BENCHMARK)}
    try:
        validate_finding(finding, fact_ids)
        return {"valid": True, "errors": []}
    except ValidationFailed as exc:
        return {"valid": False, "errors": [str(exc)]}


# --------------------------------------------------------------------------- #
# assinatura de correspondencia do relatorio
# --------------------------------------------------------------------------- #

# O bloco fica FORA do corpo que ele cobre: o corpo assinado e tudo que vem
# antes do delimitador de abertura. Se ele entrasse no hash, o hash mudaria ao
# ser escrito, e nenhuma assinatura fecharia consigo mesma.
_SIGNATURE_OPEN = "<!-- sparkforge:signature -->"
_SIGNATURE_CLOSE = "<!-- /sparkforge:signature -->"

_FINDINGS_FROM_JUDGE = "sparkforge judge --facts <facts.json> --out {path}"
_REPORT_SIGN_HINT = (
    "sparkforge report sign --report {report} --findings <findings.json>"
)

# As linhas legiveis por maquina do bloco usam chave ASCII de proposito -- a
# prosa em volta e acentuada, mas o que o `verify` faz parsing precisa casar
# byte-a-byte em qualquer console.
_BLOCK_SIGNATURE = re.compile(r"^- assinatura: (\S+)\s*$", re.MULTILINE)
_BLOCK_SIGNATURE_VERSION = re.compile(r"^- signature_version: (\d+)\s*$", re.MULTILINE)
_BLOCK_FACT_IDS = re.compile(r"^- fact_ids: (.*)$", re.MULTILINE)
_BLOCK_RULE_IDS = re.compile(r"^- rule_ids: (.*)$", re.MULTILINE)
_BLOCK_CATALOG_VERSION = re.compile(r"^- catalog_version: (\d+)\s*$", re.MULTILINE)
_BLOCK_SCHEMA_VERSION = re.compile(r"^- schema_version: (\d+)\s*$", re.MULTILINE)

# Ordem fixa, e nao a de um `set`: `diverged` e lida por humano, e a mesma
# divergencia sairia em ordem diferente entre execucoes se viesse de conjunto.
# `version` vem primeiro porque ela QUALIFICA as outras: quando a regra de
# normalizacao mudou, "o corpo nao fecha" deixa de significar "o corpo mudou".
_SIGNATURE_PARTS = ("version", "evidence", "catalog", "body")

# Bloco sem a linha de versao so pode ter saido da unica versao que nunca a
# escreveu -- a 1, a primeira. Nao e default silencioso, e nao serve para forjar
# validade: a versao entra DENTRO do hash, entao declarar 1 num corpo assinado
# sob 2 faz a assinatura nao fechar. O que ela evita e o oposto: um relatorio
# assinado antes desta linha existir sendo lido como bloco malformado.
_SIGNATURE_VERSION_IMPLICITA = 1


def _load_findings_file(findings_path: str) -> list[dict[str, Any]]:
    path = Path(findings_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de findings nao encontrado: {findings_path}\n"
            f"  Rode o verbo que produz este arquivo:\n"
            f"    {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
            exit_code=2,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{findings_path}: JSON invalido: {exc}", exit_code=2) from exc
    if not isinstance(raw, list):
        raise AdapterError(
            f"{findings_path}: esperado uma lista de findings.\n"
            f"  Rode: {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
            exit_code=2,
        )
    return raw


def _signature_parts(findings_path: str) -> dict[str, Any]:
    """As quatro entradas nao-corpo da assinatura, todas do MESMO arquivo.

    Medido antes de escolher a flag do verbo, em vez de herdar `--facts` do
    plano: o arquivo de **facts** carrega `id`, `kind`, `subject`, `measures` e
    `provenance` -- e nenhum `rule_id`, nenhum `catalog_version` e nenhum
    `schema_version` de julgamento. O arquivo de **findings** carrega os
    quatro: `evidence` e a lista de `fact_id` que o achado cita
    (`models.Finding.evidence`), `rule_id` e a regra que disparou, e
    `catalog_version`/`schema_version` viajam em cada achado
    (`Finding.to_dict`, alimentados por `loader.py:212` a partir do cabecalho
    do arquivo de catalogo). Um verbo com `--facts` precisaria dos dois
    arquivos para responder tres dos quatro campos; com `--findings` ele
    responde os quatro com um so, e nenhum terceiro formato e inventado.

    `catalog_version` divergente entre achados e RECUSADO em vez de resolvido
    por maioria ou por maximo: `compute_signature` recebe um inteiro, e
    escolher um dos dois faria a assinatura afirmar que o relatorio foi julgado
    por um catalogo que nao foi o unico usado -- mentira por omissao, no valor
    cuja razao de existir e pegar exatamente isso.
    """
    findings = _load_findings_file(findings_path)
    if not findings:
        raise AdapterError(
            f"{findings_path}: nenhum finding.\n"
            "  Assinar aqui afirmaria correspondencia com evidencia nenhuma: a "
            "assinatura cobriria so o corpo, e o leitor leria como prova de que "
            "o texto vem dos facts.\n"
            f"  Rode: {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
            exit_code=2,
        )

    fact_ids: set[str] = set()
    rule_ids: set[str] = set()
    catalog_versions: set[int] = set()
    schema_versions: set[int] = set()

    for index, finding in enumerate(findings):
        where = f"{findings_path}: finding[{index}]"
        if not isinstance(finding, dict):
            raise AdapterError(
                f"{where}: esperado um objeto de finding.\n"
                f"  Rode: {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
                exit_code=2,
            )
        rule_id = finding.get("rule_id")
        evidence = finding.get("evidence")
        catalog_version = finding.get("catalog_version")
        schema_version = finding.get("schema_version")
        missing = [
            name
            for name, value in (
                ("rule_id", rule_id),
                ("evidence", evidence),
                ("catalog_version", catalog_version),
                ("schema_version", schema_version),
            )
            if value is None or value == [] or value == ""
        ]
        if missing:
            raise AdapterError(
                f"{where} ({rule_id or '?'}): campos ausentes para assinar: "
                f"{', '.join(missing)}.\n"
                f"  Rode: {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
                exit_code=2,
            )
        rule_ids.add(str(rule_id))
        fact_ids.update(str(fact_id) for fact_id in evidence or [])
        catalog_versions.add(int(catalog_version))
        schema_versions.add(int(schema_version))

    for name, values in (
        ("catalog_version", catalog_versions),
        ("schema_version", schema_versions),
    ):
        if len(values) > 1:
            listed = ", ".join(str(value) for value in sorted(values))
            raise AdapterError(
                f"{findings_path}: {name} divergente entre os findings ({listed}).\n"
                "  A assinatura declara UM catalogo; escolher um dos valores "
                "afirmaria que o relatorio foi julgado so por ele.\n"
                "  Separe os findings por versao, ou rejulgue tudo com o mesmo "
                f"catalogo: {_FINDINGS_FROM_JUDGE.format(path=findings_path)}",
                exit_code=2,
            )

    return {
        "fact_ids": sorted(fact_ids),
        "rule_ids": sorted(rule_ids),
        "catalog_version": catalog_versions.pop(),
        "schema_version": schema_versions.pop(),
    }


def _read_report(report_path: str) -> str:
    path = Path(report_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de relatorio nao encontrado: {report_path}\n"
            "  Escreva o relatorio a partir de `templates/performance-report.md` e "
            "rode:\n"
            f"    {_REPORT_SIGN_HINT.format(report=report_path)}",
            exit_code=2,
        )
    return path.read_text(encoding="utf-8")


def _split_report(text: str) -> tuple[str, str | None, str | None]:
    """Separa (corpo assinado, bloco, problema).

    O corpo e tudo que vem ANTES do delimitador de abertura -- e so isso. Texto
    DEPOIS do delimitador de fechamento e recusado como problema em vez de
    ignorado: ignorar abriria a porta exata que a assinatura fecha, um paragrafo
    apendado ao fim do arquivo que nenhuma assinatura cobre e que o leitor le
    como parte do relatorio verificado.
    """
    opens = text.count(_SIGNATURE_OPEN)
    closes = text.count(_SIGNATURE_CLOSE)
    if opens == 0 and closes == 0:
        return text, None, None
    if opens != 1 or closes != 1:
        return text, None, (
            f"bloco malformado: {opens} delimitador(es) de abertura e {closes} de "
            "fechamento; o esperado e exatamente um de cada"
        )
    start = text.index(_SIGNATURE_OPEN)
    end = text.index(_SIGNATURE_CLOSE)
    if end < start:
        return text, None, (
            "bloco malformado: o delimitador de fechamento aparece antes do de abertura"
        )
    body = text[:start]
    block = text[start : end + len(_SIGNATURE_CLOSE)]
    tail = text[end + len(_SIGNATURE_CLOSE) :]
    if tail.strip():
        return body, block, (
            "ha conteudo depois do bloco de assinatura; o corpo assinado e tudo que "
            "vem ANTES do delimitador de abertura, entao esse trecho ficaria de fora "
            "da assinatura sem que nada dissesse isso ao leitor"
        )
    return body, block, None


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _render_signature_block(signature: str, parts: dict[str, Any]) -> str:
    """O bloco, com o limite escrito dentro dele (D-6 do spec da Fase 4b).

    As linhas de `fact_ids` e `rule_ids` nao sao enfeite: sao o que o `verify`
    usa para isolar QUAL das tres partes divergiu. Sem elas, um arquivo de
    findings diferente do assinado e um corpo editado produzem a mesma falha
    unica -- "nao bate" --, que e a resposta que o criterio 8 do spec recusa.

    `signature_version` esta aqui pela mesma razao, uma casa acima. Ela ja
    entrava DENTRO do hash -- e era o que garantia que duas normalizacoes
    diferentes produzissem assinaturas diferentes --, mas o bloco nao a
    declarava, e sem a declaracao `verify` nao tinha como dizer POR QUE nao
    fechou: um relatorio assinado sob a regra anterior saia identico a um corpo
    adulterado. A versao no hash garante que as assinaturas DIFEREM; a versao no
    bloco e o que permite atribuir a diferenca.
    """
    fact_ids = ", ".join(parts["fact_ids"])
    rule_ids = ", ".join(parts["rule_ids"])
    evidencia = (
        f"{_plural(len(parts['fact_ids']), 'fact', 'facts')}, "
        f"{_plural(len(parts['rule_ids']), 'regra', 'regras')}"
    )
    return "\n".join(
        [
            _SIGNATURE_OPEN,
            f"- assinatura: {signature}",
            f"- signature_version: {_signature.SIGNATURE_VERSION}",
            f"- evidência: {evidencia}",
            f"- fact_ids: {fact_ids}",
            f"- rule_ids: {rule_ids}",
            f"- catalog_version: {parts['catalog_version']}",
            f"- schema_version: {parts['schema_version']}",
            "- verifique com: `sparkforge report verify --report <este arquivo> "
            "--findings <findings.json>`",
            "",
            "Esta assinatura prova **correspondência**, não autoria: que este texto foi",
            "derivado desta evidência com este catálogo. Não há chave e não há segredo —",
            "qualquer pessoa com os mesmos findings produz exatamente a mesma assinatura,",
            "então ela não diz quem emitiu o relatório e não o autoriza. O corpo assinado",
            "é tudo que vem antes do delimitador acima; este bloco fica de fora dele.",
            _SIGNATURE_CLOSE,
        ]
    )


def report_sign(report_path: str, findings_path: str) -> dict[str, Any]:
    """Escreve o bloco de assinatura no fim do relatorio, e devolve o que assinou.

    Idempotente por construcao: assinar de novo recorta o bloco anterior antes
    de hashear, entao o corpo e o mesmo, a assinatura e a mesma e o arquivo sai
    byte-identico. Sem isso, a segunda assinatura hashearia a primeira e o
    relatorio nunca mais fecharia consigo mesmo.
    """
    text = _read_report(report_path)
    body, _block, problem = _split_report(text)
    if problem is not None:
        raise AdapterError(
            f"{report_path}: {problem}.\n"
            f"  Corrija o arquivo e rode: {_REPORT_SIGN_HINT.format(report=report_path)}",
            exit_code=2,
        )

    parts = _signature_parts(findings_path)
    signature = compute_signature(
        body,
        parts["fact_ids"],
        parts["rule_ids"],
        parts["catalog_version"],
        parts["schema_version"],
    )
    block = _render_signature_block(signature, parts)
    Path(report_path).write_text(
        body.rstrip("\n") + "\n\n" + block + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "report": report_path,
        "findings": findings_path,
        "signature": signature,
        "fact_ids": parts["fact_ids"],
        "rule_ids": parts["rule_ids"],
        "catalog_version": parts["catalog_version"],
        "schema_version": parts["schema_version"],
        "proves": (
            "correspondencia entre este corpo, esta evidencia e este catalogo -- "
            "nunca autoria: nao ha chave, e quem tiver os mesmos findings produz "
            "a mesma assinatura"
        ),
    }


def _parse_signature_block(block: str) -> tuple[dict[str, Any] | None, str | None]:
    """Le o que o bloco DECLARA ter assinado. `(declarado, problema)`."""
    signature_match = _BLOCK_SIGNATURE.search(block)
    if signature_match is None:
        return None, "bloco sem a linha `- assinatura: sig_...`"
    signature = signature_match.group(1)
    if not SIGNATURE_RE.match(signature):
        return None, (
            f"assinatura `{signature}` fora da forma esperada (`sig_` + 64 hex)"
        )

    version_match = _BLOCK_SIGNATURE_VERSION.search(block)
    fields: dict[str, Any] = {
        "signature": signature,
        "signature_version": (
            int(version_match.group(1))
            if version_match
            else _SIGNATURE_VERSION_IMPLICITA
        ),
    }
    for key, pattern in (
        ("fact_ids", _BLOCK_FACT_IDS),
        ("rule_ids", _BLOCK_RULE_IDS),
    ):
        match = pattern.search(block)
        if match is None:
            return None, f"bloco sem a linha `- {key}:`"
        fields[key] = sorted(
            {item.strip() for item in match.group(1).split(",") if item.strip()}
        )
    for key, pattern in (
        ("catalog_version", _BLOCK_CATALOG_VERSION),
        ("schema_version", _BLOCK_SCHEMA_VERSION),
    ):
        match = pattern.search(block)
        if match is None:
            return None, f"bloco sem a linha `- {key}:`"
        fields[key] = int(match.group(1))
    return fields, None


def _blank_checks(detail: str) -> dict[str, dict[str, Any]]:
    return {part: {"ok": False, "detail": detail} for part in _SIGNATURE_PARTS}


def report_verify(report_path: str, findings_path: str) -> dict[str, Any]:
    """Diz QUAL das partes divergiu -- versao, evidencia, catalogo ou corpo.

    Criterio 8 do spec da Fase 4b. Elas sao recomputadas separadamente, e a
    isolacao vem de segurar as outras no valor DECLARADO pelo bloco:

    - `version`: o `signature_version` declarado contra o desta build. Ele vem
      primeiro porque QUALIFICA os demais: `SIGNATURE_VERSION` entra dentro do
      hash justamente para que duas normalizacoes diferentes nunca produzam a
      mesma assinatura -- so que ate a linha existir no bloco, o efeito disso
      era um relatorio de versao anterior saindo identico a um corpo adulterado
      (`status: diverged`, `diverged: ["body"]`, "o corpo foi editado depois da
      emissao"). A versao no hash garante que as assinaturas DIFEREM; a versao
      no bloco e o que permite dizer por que;
    - `evidence`: os `fact_ids`/`rule_ids` declarados contra os do arquivo de
      findings informado agora;
    - `catalog`: idem para `catalog_version`/`schema_version`;
    - `body`: `compute_signature` do corpo atual com a evidencia e o catalogo
      **declarados** -- se ela bate, o corpo esta intacto mesmo que os findings
      de agora sejam outros; se nao bate, o corpo (ou o proprio bloco) mudou.

    Com a versao divergente, `body` sai como **nao avaliavel** e fica fora de
    `diverged`: esta build so sabe normalizar sob a versao dela, entao
    recomputar responderia sobre a regra de agora e nunca sobre o corpo de
    entao. `evidence` e `catalog` continuam sendo comparados, porque nenhum dos
    dois passa pela normalizacao.

    O bloco e dado auto-declarado e editavel -- ele mora fora do hash por
    construcao. Por isso o veredito `valid` nunca sai dele: sai das tres
    checagens juntas, que so passam quando o declarado casa com os findings
    reais E a assinatura fecha com o corpo. A atribuicao das tres e diagnostico,
    e a de `body` diz as duas leituras possiveis em vez de escolher uma.
    """
    text = _read_report(report_path)
    body, block, problem = _split_report(text)

    if block is None and problem is None:
        return {
            "report": report_path,
            "findings": findings_path,
            "valid": False,
            "status": "missing_block",
            "signature": None,
            "expected_signature": None,
            "diverged": [],
            "checks": _blank_checks("bloco de assinatura ausente: nada a comparar"),
            "reason": (
                f"{report_path} nao tem bloco de assinatura (`{_SIGNATURE_OPEN}`). "
                "Relatorio nao assinado nao e relatorio invalido -- e relatorio sem "
                f"prova. Assine com: {_REPORT_SIGN_HINT.format(report=report_path)}"
            ),
        }

    if problem is not None:
        return {
            "report": report_path,
            "findings": findings_path,
            "valid": False,
            "status": "malformed_block",
            "signature": None,
            "expected_signature": None,
            "diverged": [],
            "checks": _blank_checks(problem),
            "reason": (
                f"{report_path}: {problem}. Reassine para normalizar: "
                f"{_REPORT_SIGN_HINT.format(report=report_path)}"
            ),
        }

    declared, block_problem = _parse_signature_block(block or "")
    if declared is None:
        return {
            "report": report_path,
            "findings": findings_path,
            "valid": False,
            "status": "malformed_block",
            "signature": None,
            "expected_signature": None,
            "diverged": [],
            "checks": _blank_checks(block_problem or "bloco malformado"),
            "reason": (
                f"{report_path}: {block_problem}. Reassine para normalizar: "
                f"{_REPORT_SIGN_HINT.format(report=report_path)}"
            ),
        }

    parts = _signature_parts(findings_path)

    declared_version = declared["signature_version"]
    corrente = _signature.SIGNATURE_VERSION
    version_ok = declared_version == corrente

    evidence_ok = (
        declared["fact_ids"] == parts["fact_ids"]
        and declared["rule_ids"] == parts["rule_ids"]
    )
    catalog_ok = (
        declared["catalog_version"] == parts["catalog_version"]
        and declared["schema_version"] == parts["schema_version"]
    )
    body_signature = compute_signature(
        body,
        declared["fact_ids"],
        declared["rule_ids"],
        declared["catalog_version"],
        declared["schema_version"],
    )
    body_ok = body_signature == declared["signature"]

    checks = {
        "version": {
            "ok": version_ok,
            "detail": (
                f"o bloco foi assinado sob signature_version {declared_version}, a "
                f"mesma que esta build calcula"
                if version_ok
                else (
                    f"o bloco foi assinado sob signature_version {declared_version} e "
                    f"esta build assina sob {corrente}: a regra de normalizacao "
                    "mudou entre as duas, e assinatura diferente aqui significa "
                    "REGRA diferente, nao corpo adulterado"
                )
            ),
        },
        "evidence": {
            "ok": evidence_ok,
            "detail": (
                "os fact_ids e rule_ids declarados no bloco sao os do arquivo de "
                "findings informado"
                if evidence_ok
                else (
                    "o bloco declara "
                    f"{_plural(len(declared['fact_ids']), 'fact', 'facts')} e "
                    f"{_plural(len(declared['rule_ids']), 'regra', 'regras')}; "
                    f"{findings_path} tem "
                    f"{_plural(len(parts['fact_ids']), 'fact', 'facts')} e "
                    f"{_plural(len(parts['rule_ids']), 'regra', 'regras')}. "
                    "So no bloco: "
                    f"{sorted(set(declared['fact_ids']) - set(parts['fact_ids'])) or '[]'} "
                    f"{sorted(set(declared['rule_ids']) - set(parts['rule_ids'])) or '[]'}; "
                    "so nos findings: "
                    f"{sorted(set(parts['fact_ids']) - set(declared['fact_ids'])) or '[]'} "
                    f"{sorted(set(parts['rule_ids']) - set(declared['rule_ids'])) or '[]'}"
                )
            ),
        },
        "catalog": {
            "ok": catalog_ok,
            "detail": (
                "catalog_version e schema_version declarados sao os dos findings"
                if catalog_ok
                else (
                    f"o bloco declara catalog_version {declared['catalog_version']} e "
                    f"schema_version {declared['schema_version']}; {findings_path} diz "
                    f"catalog_version {parts['catalog_version']} e schema_version "
                    f"{parts['schema_version']}"
                )
            ),
        },
        "body": {
            "ok": body_ok,
            "detail": (
                "a assinatura fecha com o corpo atual sob a evidencia declarada"
                if body_ok
                else (
                    "a assinatura nao fecha com o corpo atual sob a evidencia e o "
                    "catalogo DECLARADOS no bloco: o corpo foi editado depois da "
                    "emissao, ou o proprio bloco foi"
                )
                if version_ok
                else (
                    "nao avaliavel: esta build so sabe normalizar sob "
                    f"signature_version {corrente}, e o bloco foi assinado sob "
                    f"{declared_version}. Recomputar aqui responderia sobre a regra "
                    "de agora, nunca sobre o corpo de entao"
                )
            ),
        },
    }

    # Com a versao divergente, `body` fica FORA de `diverged` mesmo com `ok`
    # falso: atribuir a divergencia ao corpo seria exatamente a afirmacao que
    # esta build nao pode sustentar. `evidence` e `catalog` continuam entrando,
    # porque nenhum dos dois depende da normalizacao -- eles comparam o que o
    # bloco declara com o arquivo de findings, e essa comparacao segue valendo.
    avaliaveis = _SIGNATURE_PARTS if version_ok else ("version", "evidence", "catalog")
    diverged = [part for part in avaliaveis if not checks[part]["ok"]]
    expected_signature = compute_signature(
        body,
        parts["fact_ids"],
        parts["rule_ids"],
        parts["catalog_version"],
        parts["schema_version"],
    )
    if not diverged:
        reason = (
            "corresponde: este corpo foi derivado desta evidencia com este catalogo. "
            "Correspondencia, nunca autoria -- nao ha chave, e quem tiver os mesmos "
            "findings produz a mesma assinatura."
        )
    else:
        nomes = {
            "version": "versao da assinatura",
            "evidence": "evidencia",
            "catalog": "catalogo",
            "body": "corpo",
        }
        # Cada parte divergente sai rotulada e terminada: as tres frases coladas
        # sem separador viravam um paragrafo unico em que nao se via onde uma
        # acabava e a outra comecava -- e a resposta que o criterio 8 pede e
        # justamente "qual", nao "quanto texto".
        reason = (
            "divergiu em: "
            + ", ".join(nomes[part] for part in diverged)
            + ". "
            + " ".join(f"{nomes[part]}: {checks[part]['detail']}." for part in diverged)
            + f" Reassine com: {_REPORT_SIGN_HINT.format(report=report_path)}"
        )

    if not version_ok:
        status = "version_mismatch"
    elif diverged:
        status = "diverged"
    else:
        status = "signed"

    return {
        "report": report_path,
        "findings": findings_path,
        "valid": not diverged,
        "status": status,
        "signature": declared["signature"],
        "expected_signature": expected_signature,
        "diverged": diverged,
        "checks": checks,
        "reason": reason,
    }


# --------------------------------------------------------------------------- #
# case lifecycle
# --------------------------------------------------------------------------- #


def _case_open_recusa(path: Path, existing: dict[str, Any]) -> str:
    """O que seria apagado, e as duas saidas -- continuar ou reabrir de fato."""
    perdas = [f"fase `{existing.get('phase') or '?'}`"]
    if existing.get("strict_gates"):
        perdas.append("`strict_gates` ligado")
    overrides = existing.get("gate_overrides") or []
    if overrides:
        gates = ", ".join(sorted({str(o.get("gate")) for o in overrides}))
        perdas.append(f"{len(overrides)} override(s) de gate ({gates})")
    return (
        f"ja existe um case em {path}, e abrir por cima dele apagaria: "
        + "; ".join(perdas)
        + ".\n"
        "  Para continuar a investigacao: `sparkforge case get --repo <raiz>` "
        "e `sparkforge case update ...`.\n"
        "  Para recomecar do zero mesmo assim: acrescente `--reopen` "
        "(`reopen: true` na tool MCP).\n"
        "  `--reopen` **herda** o `strict_gates` do case atual: o rigor e do "
        "case e vale pela investigacao inteira (D-3), entao ele sobe com "
        "`--strict-gates` e nunca desce por omissao de flag."
    )


def case_open(
    repo: str,
    case_id: str,
    now: str,
    glue: str | None = None,
    spark: str | None = None,
    python: str | None = None,
    iceberg: str | None = None,
    athena: str | None = None,
    facts_path: str | list[str] | None = None,
    emr: str | None = None,
    strict_gates: bool = False,
    reopen: bool = False,
) -> dict[str, Any]:
    """Cria o case. Sobre um case que ja existe, recusa -- a menos de `reopen`.

    Medido na revisao final da Fase 4b: sobre um case estrito com override
    gravado, `case open` sem flag nenhuma reescrevia o arquivo com
    `strict_gates: false`, `gate_overrides: []` e `phase: intake`, e a transicao
    seguinte passava. O D-3 diz que *quem retoma herda o rigor de quem abriu*, e
    uma invocacao sem a flag apagava exatamente isso -- a familia de defeito que
    o D-3 evitou ao tirar a escolha de rigor da invocacao.

    Reabrir do zero e caso legitimo (o mesmo repositorio, outra investigacao),
    entao o caminho fica -- **com nome**, nunca por omissao. E `reopen` nao
    baixa o rigor: ele herda o `strict_gates` do case atual, e `strict_gates`
    explicito so pode subi-lo. Baixar exigiria apagar o arquivo a mao, que e
    deliberado o bastante para nao acontecer por engano.
    """
    path = store.case_path(repo)
    if path.is_file():
        try:
            existing = store.load_case(repo)
        except store.CaseError:
            # Case que `load_case` recusa (schema divergente, YAML quebrado)
            # ainda e um case ocupando o lugar. Sobrescreve-lo em silencio
            # apagaria o estado que alguem precisa ver antes de decidir.
            existing = {}
        if not reopen:
            raise AdapterError(_case_open_recusa(path, existing), exit_code=2)
        strict_gates = bool(strict_gates or existing.get("strict_gates"))

    # O case guarda o runtime da investigacao inteira. Aceitar facts aqui e o
    # que evita abrir um case com runtime vazio quando o repositorio ja diz a
    # versao -- toda skill que ler o case depois herda a deteccao.
    context = build_runtime_context(
        glue,
        spark,
        python,
        iceberg,
        athena,
        facts=_facts_for_runtime(facts_path),
        emr=emr,
    )
    case = store.new_case(
        case_id, now, context.to_dict(), repo=repo, strict_gates=strict_gates
    )
    store.save_case(case, root=repo)
    return case


def case_get(repo: str) -> dict[str, Any]:
    try:
        return store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def _fact_kinds_for_gates(facts_path: str | list[str] | None) -> set[str] | None:
    """Kinds presentes nos facts informados — o que satisfaz gate sob rigor.

    `None` quando nada e informado, que e o que preserva a chamada antiga: sem
    rigor, `set_phase` ignora o parametro; com rigor e sem facts, o gate morde e
    a mensagem diz o comando que produz o fact.

    O case tem `facts_index.by_kind`, mas nenhum verbo o preenche hoje (desvio
    D-4b-5), entao ler dali seria ler um indice sempre vazio -- rigor que nunca
    destrava por evidencia. A fonte e o arquivo de facts, o mesmo que `judge` e
    `case open` ja aceitam.
    """
    if facts_path is None:
        return None
    paths = [facts_path] if isinstance(facts_path, str) else list(facts_path)
    if not paths:
        return None
    return {fact.kind for fact in _merge_facts_files(paths)}


def case_update(
    repo: str,
    phase: str | None = None,
    gate: str | None = None,
    gate_value: bool = True,
    skill: str | None = None,
    now: str | None = None,
    outcome: str | None = None,
    override_gate: str | None = None,
    reason: str | None = None,
    facts_path: str | list[str] | None = None,
    hypothesis: str | None = None,
    prediction: str | None = None,
    experiment: str | None = None,
    close_hypothesis: str | None = None,
    hypothesis_outcome: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    if reason is not None and override_gate is None:
        raise AdapterError(
            "`--reason` so faz sentido com `--override-gate`: sem o gate, o "
            "motivo nao tem sujeito e nao seria gravado em lugar nenhum. Rode "
            "`sparkforge case update --override-gate <gate> --reason \"<motivo>\"`.",
            exit_code=2,
        )
    partes = [hypothesis, prediction, experiment]
    if any(partes) and not all(partes):
        raise AdapterError(
            "hipotese exige as TRES partes: `--hypothesis`, `--prediction` e "
            "`--experiment`. Afirmacao sem previsao nao e testavel, e previsao "
            "sem experimento nao diz quem a testa -- gravar so uma delas "
            "registraria um palpite com cara de hipotese.",
            exit_code=2,
        )
    if hypothesis_outcome is not None and close_hypothesis is None:
        raise AdapterError(
            "`--hypothesis-outcome` so faz sentido com `--close-hypothesis`: "
            "sem o id, o desfecho nao tem sujeito. Rode `sparkforge case update "
            "--close-hypothesis h1 --hypothesis-outcome confirmed`.",
            exit_code=2,
        )
    if close_hypothesis is not None and hypothesis_outcome is None:
        raise AdapterError(
            "fechar hipotese exige `--hypothesis-outcome`: um de "
            f"{', '.join(store.HYPOTHESIS_OUTCOMES)}. Fechar sem desfecho "
            "apagaria a pergunta sem responder nenhuma.",
            exit_code=2,
        )
    fact_kinds = _fact_kinds_for_gates(facts_path)
    try:
        case = store.load_case(repo)
        # Override antes da fase, de proposito: quem passa os dois na mesma
        # chamada quer transitar COM o override valendo. A ordem inversa faria
        # `--override-gate X --phase Y` falhar sempre, e o operador teria que
        # descobrir sozinho que precisava de duas chamadas.
        if override_gate is not None:
            case = store.override_gate(
                case, override_gate, reason or "", at=now or ""
            )
        if phase is not None:
            case = store.set_phase(case, phase, fact_kinds=fact_kinds)
        if gate is not None:
            case = store.set_gate(case, gate, bool(gate_value))
        if skill is not None:
            case = store.record_skill_use(case, skill, now or "", outcome or "")
        if hypothesis is not None:
            case = store.add_hypothesis(
                case, hypothesis, prediction or "", experiment or ""
            )
        if close_hypothesis is not None:
            case = store.close_hypothesis(
                case,
                close_hypothesis,
                hypothesis_outcome or "",
                at=now or "",
                evidence=evidence or "",
            )
        store.save_case(case, root=repo)
        return case
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def next_step(repo: str, findings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    finding_ids = [
        f.get("rule_id") for f in (findings or []) if isinstance(f, dict) and f.get("rule_id")
    ]
    try:
        return router.next_step(case, finding_ids)
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def resume_case(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    try:
        return run_resume(
            case, findings or [], unresolved_count=unresolved, in_flight=in_flight, root=root
        )
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def handoff(
    repo: str,
    findings: list[dict[str, Any]] | None = None,
    unresolved: int = 0,
    in_flight: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    payload = resume_case(repo, findings, unresolved, in_flight, root=root)
    markdown = render_handoff(payload)
    path = Path(repo) / ".sparkforge" / "handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    result = dict(payload)
    result["handoff_path"] = str(path)
    return result


def playbook(
    coordinator: str, repo: str = ".", findings: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Decomposicao do coordenador, com o estado do case quando existir.

    Case ausente e caso normal, nao erro: a plataforma sem despacho de
    subagente pode consultar os passos antes mesmo de abrir um case --
    `case={}` so faz `phase` sair vazio no payload.

    `findings`, quando informado, alimenta o `next_step` embutido no playbook
    (ver `build_playbook`) do mesmo jeito que `next_step()` acima: cada item e
    um dict de finding, e so o `rule_id` importa aqui.
    """
    try:
        case = store.load_case(repo)
    except store.CaseError:
        case = {}
    finding_ids = [
        f.get("rule_id") for f in (findings or []) if isinstance(f, dict) and f.get("rule_id")
    ]
    try:
        return build_playbook(coordinator, case, finding_ids)
    except ValueError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc
    except CatalogError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


# --------------------------------------------------------------------------- #
# collect (coletores AWS)
# --------------------------------------------------------------------------- #


def _collect_error(exc: Exception, repo: str, rel_path: str) -> AdapterError:
    """Reembala falha de coleta com o caminho exato onde o artefato coletado
    manualmente precisa ficar -- sem isto, "colete manualmente e registre"
    (a mensagem generica de `require_boto3`) deixa o operador adivinhando
    onde. Perder acesso a AWS nao pode deixar a ferramenta inutilizavel."""
    message = str(exc)
    if isinstance(exc, CollectorUnavailable):
        expected = Path(repo) / rel_path
        message += (
            f"\n  Alternativa manual: baixe o artefato (AWS CLI ou console), salve em "
            f"{expected}, e registre com `sparkforge.collect.register_artifact` "
            f"(kind, sha256, source e o collect_command acima)."
        )
    return AdapterError(message, exit_code=2)


def _collect_payload(entry: Any, now: str) -> dict[str, Any]:
    payload = entry.to_dict()
    # `collected_at != now` prova que a chamada foi um cache hit local (o
    # sha256 ja batia) -- nenhuma rede, nenhuma credencial AWS tocada. Sem
    # este campo, "no-op" e um fato que so existe nos logs internos do
    # coletor, invisivel para quem le a saida da CLI/MCP.
    payload["cache_hit"] = entry.collected_at != now
    return payload


def collect_event_log(
    repo: str, *, job_run_id: str, bucket: str, prefix: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.event_log_path(job_run_id)
    try:
        entry = collect_aws.collect_event_log(
            job_run_id, Path(repo), bucket=bucket, prefix=prefix, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_glue_job(repo: str, *, job_name: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.glue_job_path(job_name)
    try:
        entry = collect_aws.collect_glue_job(job_name, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_cloudwatch(
    repo: str, *, job_name: str, job_run_id: str, start: str, end: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.cloudwatch_path(job_name, job_run_id)
    try:
        entry = collect_aws.collect_cloudwatch(
            job_name, job_run_id, Path(repo), now=now, start=start, end=end
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_glue_job_runs(
    repo: str, *, job_name: str, max_runs: int, now: str
) -> dict[str, Any]:
    try:
        return collect_aws.collect_glue_job_runs(
            job_name, Path(repo), max_runs=max_runs, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(
            exc, repo, collect_aws.glue_job_run_path(job_name, "<run-id>")
        ) from exc


def collect_iceberg_metadata(
    repo: str, *, table: str, workgroup: str, output_location: str, now: str
) -> dict[str, Any]:
    rel_path = collect_aws.iceberg_metadata_path(table)
    try:
        entry = collect_aws.collect_iceberg_metadata(
            table, Path(repo), workgroup=workgroup, output_location=output_location, now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_athena_workgroup(repo: str, *, workgroup: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.athena_workgroup_path(workgroup)
    try:
        entry = collect_aws.collect_athena_workgroup(workgroup, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_emr_cluster(repo: str, *, cluster_id: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.emr_cluster_path(cluster_id)
    try:
        entry = collect_aws.collect_emr_cluster(cluster_id, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_emr_serverless(repo: str, *, application_id: str, now: str) -> dict[str, Any]:
    rel_path = collect_aws.emr_serverless_path(application_id)
    try:
        entry = collect_aws.collect_emr_serverless(application_id, Path(repo), now=now)
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_emr_eks(
    repo: str, *, virtual_cluster_id: str, job_run_id: str, now: str
) -> dict[str, Any]:
    # Os DOIS ids sao obrigatorios porque `DescribeJobRun` exige
    # `virtualClusterId` junto do `id` -- ver o docstring do coletor.
    rel_path = collect_aws.emr_eks_path(virtual_cluster_id, job_run_id)
    try:
        entry = collect_aws.collect_emr_eks(
            virtual_cluster_id, job_run_id, Path(repo), now=now
        )
    except (CollectorUnavailable, collect_aws.CollectionFailed) as exc:
        raise _collect_error(exc, repo, rel_path) from exc
    return _collect_payload(entry, now)


def collect_verify(repo: str) -> dict[str, Any]:
    results = verify_all(repo)
    missing = [r for r in results if not r["present"]]
    mismatched = [r for r in results if r["present"] and not r["hash_matches"]]
    ok = [r for r in results if r["present"] and r["hash_matches"]]
    return {
        "total_count": len(results),
        "ok_count": len(ok),
        "missing_count": len(missing),
        "mismatched_count": len(mismatched),
        "artifacts": results,
    }


# --------------------------------------------------------------------------- #
# Code Intelligence -- SPEC 56 a 77                                            #
# --------------------------------------------------------------------------- #
#
# ESTE MODULO E A IMPLEMENTACAO DE DOMINIO DA SUPERFICIE, E `tools.py` SO
# COMPOE O CONTRATO. A SPEC secao 72 pede o modulo em
# `sparkforge/codeintel/tools.py`; ele mora AQUI, e o desvio esta registrado
# em vez de escondido: a fase que escreveu esta superficie nao e dona do
# pacote `sparkforge/codeintel/` (outro agente trabalhava dentro dele no mesmo
# commit), e criar um arquivo novo la seria escrever num pacote que a fase nao
# pode reverificar. A propriedade que a secao 72 protege -- `adapters/tools.py`
# sem SQLite, sem AST, sem grafo, sem seguranca -- fica INTEIRA: nada disso
# atravessa para la, e a cadeia continua MCP -> tools.py -> _core.py ->
# codeintel. Mover as funcoes abaixo para `codeintel/tools.py` depois e um
# recorte mecanico, e nenhum contrato de tool muda com ele.

# SPEC 16.3 e INV-014. O rotulo e CONSTANTE deste codigo -- INV-013 proibe
# derivar descricao ou rotulo de arquivo do repositorio analisado -- e ele
# acompanha TODO trecho de fonte que sai daqui, dentro de objeto estruturado.
# Nunca ha prosa com codigo embutido: quem le recebe `{"trust": ..., "code":
# ...}` e sabe, pelo campo, que aquilo e amostra e nao instrucao.
CODE_TRUST = "untrusted_repository_content"

# SPEC 60. Tetos DUROS da leitura de fonte. Eles nao sao configuraveis por
# argumento: `max_tokens` do chamador so consegue APERTAR (ver `code_read`).
# Um teto que o chamador pudesse afrouxar seria o mesmo que nao ter teto --
# "leia o repositorio inteiro" e exatamente o pedido que a secao 60 proibe.
CODE_READ_MAX_LINES = 250
CODE_READ_MAX_BYTES = 32 * 1024
CODE_READ_MAX_TOKENS = 4096
CODE_READ_DEFAULT_TOKENS = 1200
CODE_READ_MAX_CONTEXT_LINES = 20

# SPEC 58. Teto do numero de simbolos por busca.
CODE_SEARCH_MAX_LIMIT = 200
CODE_SEARCH_DEFAULT_LIMIT = 20

# SPEC 61. Profundidade maxima do raio de impacto.
CODE_MAX_DEPTH = 5

# SPEC 63. Teto de arquivos alterados que viram simbolo + chamador na resposta
# de `code_status`. Acima disto a resposta diz `changes_truncated: true` em vez
# de crescer sem limite -- uma arvore com 400 arquivos mexidos produziria um
# payload maior que o proprio diff.
CODE_CHANGED_MAX_FILES = 25

# SPEC 16.4. Detector de padrao com cara de instrucao. Ele NUNCA torna o
# conteudo confiavel e NUNCA apaga nada: acrescenta um booleano ao lado do
# trecho, para aumentar a cautela de quem le. Apagar do trecho o que parece
# instrucao apagaria a evidencia, e evidencia apagada e defeito, nao seguranca
# -- e a mesma regra que `docs/harness/UNTRUSTED-CONTENT.md` ja fixa para
# `subject.snippet`.
_PADROES_DE_INSTRUCAO = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "new instructions",
    "important instructions",
    "send this",
    "exfiltrate",
    "read credentials",
)

# SPEC 77. A ponte entre o vocabulario de dominio da consulta (os clusters de
# `codeintel/domain_terms.yaml`) e as categorias do catalogo de regras. E LISTA
# LITERAL, e nao derivacao de nome: `parquet` casaria por acaso e
# `parquet-layout` nao, `udf` nunca casaria com `pyspark-code`, e uma heuristica
# de nome faria a relevancia depender de como alguem batizou um arquivo YAML.
# Cluster sem categoria mapeada NAO produz regra -- ausencia declarada, nunca
# palpite.
CODE_CLUSTER_PARA_CATEGORIA: dict[str, str] = {
    "iceberg": "iceberg",
    "parquet": "parquet-layout",
    "small_files": "parquet-layout",
    "glue": "glue-infra",
    "athena": "athena",
    "udf": "pyspark-code",
    "skew": "pyspark-code",
    "join": "pyspark-code",
    "shuffle": "pyspark-code",
    "particionamento": "pyspark-code",
    "memoria": "pyspark-code",
    "cache": "pyspark-code",
    "catalogo": "cross-account-catalog",
}

# SPEC 57. As secoes do ContextPack que este motor sabe PREENCHER.
#
# `lineage` ESTAVA na lista de recusadas, com a razao "`context.montar` nao
# consulta `codeintel.lineage`, e o DataGraph daquele modulo e construido do
# FONTE por arquivo, nunca persistido no indice". A razao deixou de valer:
# `data_flow` e `data_flow_blind_spots` entraram em `db.py`, a indexacao as
# grava e `montar` as consulta. A recusa sai daqui porque manter uma recusa
# cuja razao e falsa e pior que nao ter recusa nenhuma -- ela ensina o chamador
# a nao pedir uma secao que ja existe.
#
# O QUE NAO MUDA: dentro da secao, o que o indice nao soube nomear continua
# saindo como recusa nomeada (`DYNAMIC_TABLE_IDENTIFIER` e as irmas), com o
# template de buracos preservados. A recusa mudou de NIVEL -- era da secao
# inteira, agora e do item --, e nao desapareceu.
#
# `snippets` continua recusado: trecho de fonte sai por `sparkforge_code_read`,
# que tem os tetos duros da secao 60. Aceitar o valor e devolver vazio ensinaria
# o chamador que a arvore nao tem trecho, que e afirmacao diferente de "este
# pacote nao o carrega".
CODE_CONTEXT_INCLUDE = ("symbols", "relationships", "lineage", "rules", "unresolved")
CODE_CONTEXT_INCLUDE_NAO_IMPLEMENTADO = {
    "snippets": (
        "trecho de fonte sai por `sparkforge_code_read`, que aplica os tetos "
        "duros de 250 linhas / 32 KiB / 4096 tokens"
    ),
}


class CodeIndexError(AdapterError):
    """Recusa do indice de codigo, com o payload da SPEC 43 junto da mensagem.

    Existe porque a SPEC 43 exige um corpo de erro MAQUINAVEL -- `STALE_INDEX`,
    `changed_files`, `action` -- e este repositorio ja tem um envelope de erro
    uniforme (`{"error", "exit_code"}`) que a CLI e o MCP compartilham. Herdar
    de `AdapterError` mantem o envelope; `detalhes` acrescenta os campos da SPEC
    ao lado dele, sem sobrescrever a mensagem acionavel -- por isso o codigo sai
    em `error_code` e nao em `error`. Um cliente que so le `error` continua
    recebendo a frase que diz o que fazer; um que le `error_code` decide sozinho.
    """

    def __init__(self, message: str, detalhes: dict[str, Any], exit_code: int = 2) -> None:
        super().__init__(message, exit_code)
        self.detalhes = dict(detalhes)


def _code_raiz(repo: str) -> Path:
    """A raiz resolvida, ou recusa. Nenhuma leitura acontece fora dela (INV-002)."""
    base = Path(repo).expanduser()
    try:
        resolvida = base.resolve()
    except OSError as exc:  # pragma: no cover -- caminho invalido no SO
        raise AdapterError(f"raiz invalida: {repo!r} ({exc})", exit_code=2) from exc
    if not resolvida.is_dir():
        raise AdapterError(
            f"raiz inexistente ou nao e diretorio: {resolvida.as_posix()}", exit_code=2
        )
    return resolvida


def _code_banco(raiz: Path, db: str | None) -> Path:
    """O caminho do indice. Sem `db`, o default versionado sob a raiz.

    O default vem de `codeintel.db.BANCO_PADRAO` e nao de um literal repetido
    aqui: o dia em que ele mudar, dois lugares diriam coisas diferentes e o
    operador procuraria o arquivo errado.
    """
    return Path(db) if db else raiz / _codeintel_db.BANCO_PADRAO


def _code_erro_de_frescor(exc: _codeintel_staleness.NegadoPorFrescor) -> CodeIndexError:
    """Traduz a recusa fail-closed em erro de fronteira, preservando o payload.

    `payload` da excecao ja tem a forma da SPEC 43 (`error`, `action`, e o que o
    caso exigir). Aqui `error` vira `error_code` para nao competir com a
    mensagem acionavel, e o resto passa inteiro.
    """
    detalhes = dict(exc.payload)
    detalhes["error_code"] = detalhes.pop("error", exc.codigo)
    return CodeIndexError(str(exc), detalhes)


def _code_frescor(raiz: Path, banco: Path, *, auto_sync: bool = True) -> dict[str, Any]:
    """SPEC 43: confere staleness ANTES de responder, e recusa quando nao cabe.

    Toda query passa por aqui. Nao ha caminho que consulte o grafo sem esta
    porta, e essa e a exigencia literal da ultima linha da secao 43 -- "nunca
    responder silenciosamente com grafo antigo". Devolve o bloco `index` que
    entra na resposta, para que a resposta DIGA se conferiu, se sincronizou, e
    de que arvore o indice e.
    """
    try:
        frescor = _codeintel_staleness.garantir_frescor(raiz, banco, auto_sync=auto_sync)
    except _codeintel_staleness.NegadoPorFrescor as exc:
        raise _code_erro_de_frescor(exc) from exc
    estado = _codeintel_staleness.estado_da_arvore(raiz)
    return {
        "fresh": True,
        "checked": frescor.verificou,
        "synced": frescor.sincronizou,
        "changed_files": frescor.mudancas.quantidade if frescor.mudancas else 0,
        # `identidade` e digest, nunca caminho: o arquivo de indice pode ser
        # copiado e nao deve nomear a maquina de quem o construiu.
        "worktree": estado.identidade,
        "head": estado.head,
        "ref": estado.ref,
    }


def _code_contagens(banco: Path) -> dict[str, int]:
    """`edges` e `unresolved_refs` contados no banco.

    As duas metades andam juntas de proposito: 100 arestas sobre 120 chamadas e
    outra coisa que 100 sobre 3000, e so a segunda metade distingue as duas.
    `search.resumo` nao as devolve, e por isso a contagem acontece aqui.
    """
    conexao = _codeintel_db.abrir(banco)
    try:
        (arestas,) = conexao.execute("SELECT COUNT(*) FROM edges").fetchone()
        (nao_resolvidas,) = conexao.execute(
            "SELECT COUNT(*) FROM unresolved_refs"
        ).fetchone()
    finally:
        conexao.close()
    return {"edges": int(arestas), "unresolved": int(nao_resolvidas)}


def _code_no(banco: Path, node_id: str) -> dict[str, Any]:
    """O no de `node_id`, ou recusa nomeando a busca que o encontraria.

    Recusa em vez de devolver vazio porque `node_id` nao e texto de busca: ele
    ou existe no indice ou o chamador esta usando um id de antes de reindexar, e
    os dois casos precisam de acao diferente da que uma lista vazia sugere.
    """
    conexao = _codeintel_db.abrir(banco)
    try:
        linha = conexao.execute(
            "SELECT nodes.id, nodes.kind, nodes.name, nodes.qualified_name,"
            " nodes.start_line, nodes.end_line, nodes.normalized_signature,"
            " files.path, files.language"
            " FROM nodes JOIN files ON files.id = nodes.file_id"
            " WHERE nodes.id = ?",
            (node_id,),
        ).fetchone()
    finally:
        conexao.close()
    if linha is None:
        raise AdapterError(
            f"node_id inexistente no indice: {node_id!r}. "
            "Use `sparkforge_code_search` para obter um id atual.",
            exit_code=2,
        )
    return {
        "node_id": linha[0],
        "kind": linha[1],
        "name": linha[2],
        "qualified_name": linha[3],
        "start_line": linha[4],
        "end_line": linha[5],
        "signature": linha[6],
        "path": linha[7],
        "language": linha[8],
    }


def _code_nos_do_arquivo(banco: Path, caminho: str) -> list[dict[str, Any]]:
    """Os simbolos declarados em `caminho`, em ordem estavel."""
    conexao = _codeintel_db.abrir(banco)
    try:
        linhas = conexao.execute(
            "SELECT nodes.id, nodes.kind, nodes.name, nodes.qualified_name,"
            " nodes.start_line"
            " FROM nodes JOIN files ON files.id = nodes.file_id"
            " WHERE files.path = ?"
            " ORDER BY nodes.start_line, nodes.id",
            (caminho,),
        ).fetchall()
    finally:
        conexao.close()
    return [
        {
            "node_id": linha[0],
            "kind": linha[1],
            "name": linha[2],
            "qualified_name": linha[3],
            "path": caminho,
            "start_line": linha[4],
        }
        for linha in linhas
    ]


def _code_vizinho(no: Any) -> dict[str, Any]:
    """Um `NoDoGrafo` na forma que sai na resposta."""
    return {
        "node_id": no.node_id,
        "name": no.name,
        "qualified_name": no.qualified_name,
        "kind": no.kind,
        "path": no.path,
        "start_line": no.start_line,
        "depth": no.depth,
    }


def _code_parece_instrucao(texto: str) -> bool:
    """SPEC 16.4. Verdadeiro quando o trecho tem padrao com cara de instrucao.

    Isto NUNCA torna o conteudo confiavel -- o rotulo `trust` continua o mesmo
    -- e nunca muda o trecho. E um sinal a mais, e so.
    """
    baixo = texto.lower()
    return any(padrao in baixo for padrao in _PADROES_DE_INSTRUCAO)


def _code_arquivo_confinado(raiz: Path, relativo: str) -> Path:
    """Resolve `relativo` DENTRO de `raiz`, ou recusa (INV-002, SPEC 12/13).

    Tres portas, e a ordem importa: caminho absoluto e recusado antes de
    resolver, o resultado da resolucao tem que continuar sob a raiz (pega
    `../` e junction), e symlink e recusado depois disso (pega o link que
    aponta para dentro hoje e para fora amanha). Fail-closed em todas.
    """
    candidato = Path(relativo)
    if candidato.is_absolute() or ".." in candidato.parts:
        raise AdapterError(
            f"caminho fora da raiz indexada: {relativo!r}; use caminho relativo a raiz.",
            exit_code=2,
        )
    alvo = (raiz / candidato).resolve()
    try:
        alvo.relative_to(raiz)
    except ValueError as exc:
        raise AdapterError(
            f"caminho fora da raiz indexada: {relativo!r}.", exit_code=2
        ) from exc
    if not alvo.is_file():
        raise AdapterError(f"arquivo inexistente sob a raiz: {relativo!r}.", exit_code=2)
    if alvo.is_symlink() or (raiz / candidato).is_symlink():
        raise AdapterError(
            f"symlink recusado: {relativo!r}; o indice le somente arquivo real.",
            exit_code=2,
        )
    return alvo


def _code_trecho(
    raiz: Path,
    relativo: str,
    inicio: int,
    fim: int,
    *,
    max_tokens: int,
    language: str = "python",
) -> dict[str, Any]:
    """O objeto estruturado da SPEC 16.3, ja dentro dos tetos duros da secao 60.

    Devolve SEMPRE objeto, nunca prosa com codigo dentro: `trust`, `language`,
    `file`, `start_line`, `end_line`, `code`. `truncated_by` diz qual teto
    cortou -- linhas, bytes ou tokens -- porque um trecho cortado em silencio
    faria o leitor concluir que a funcao acaba onde o corte aconteceu.
    """
    alvo = _code_arquivo_confinado(raiz, relativo)
    try:
        linhas = alvo.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise AdapterError(f"arquivo ilegivel: {relativo!r} ({exc})", exit_code=2) from exc

    total = len(linhas)
    inicio = max(1, min(inicio, max(total, 1)))
    fim = max(inicio, min(fim, total))

    cortes: list[str] = []
    if fim - inicio + 1 > CODE_READ_MAX_LINES:
        fim = inicio + CODE_READ_MAX_LINES - 1
        cortes.append("lines")

    corpo = "\n".join(linhas[inicio - 1 : fim])
    if len(corpo.encode("utf-8")) > CODE_READ_MAX_BYTES:
        corpo = corpo.encode("utf-8")[:CODE_READ_MAX_BYTES].decode("utf-8", "ignore")
        cortes.append("bytes")

    teto_tokens = max(1, min(int(max_tokens), CODE_READ_MAX_TOKENS))
    while _codeintel_budget.estimar_tokens(corpo) > teto_tokens and "\n" in corpo:
        corpo = corpo[: corpo.rfind("\n")]
        if "tokens" not in cortes:
            cortes.append("tokens")

    fim_real = inicio + max(0, corpo.count("\n"))
    return {
        "trust": CODE_TRUST,
        "language": language,
        "file": relativo,
        "start_line": inicio,
        "end_line": fim_real,
        "code": corpo,
        "estimated_tokens": _codeintel_budget.estimar_tokens(corpo),
        "truncated_by": cortes,
        "instruction_like_content_detected": _code_parece_instrucao(corpo),
    }


def _code_regras_relevantes(clusters: tuple[str, ...]) -> list[dict[str, str]]:
    """SPEC 77: so os IDs relevantes, com a razao. Nenhum julgamento.

    A razao acompanha cada id porque uma lista de regras sem procedencia obriga
    quem le a adivinhar por que aquela regra apareceu -- e adivinhacao aqui vira
    recomendacao sem evidencia, que e o defeito que este repositorio inteiro
    existe para nao cometer.
    """
    categorias = [
        (cluster, CODE_CLUSTER_PARA_CATEGORIA[cluster])
        for cluster in clusters
        if cluster in CODE_CLUSTER_PARA_CATEGORIA
    ]
    if not categorias:
        return []
    try:
        catalogo = load_catalog()
    except CatalogError:
        # Catalogo ausente nao derruba a consulta de codigo: a regra e enfeite
        # de contexto aqui, e a pergunta era sobre simbolo.
        return []
    vistos: set[str] = set()
    relevantes: list[dict[str, str]] = []
    for cluster, categoria in categorias:
        for regra in catalogo:
            if regra.get("category") != categoria or regra["id"] in vistos:
                continue
            vistos.add(regra["id"])
            relevantes.append(
                {"rule_id": regra["id"], "reason": f"cluster de dominio `{cluster}` na consulta"}
            )
    return relevantes


def _code_gitignorado(raiz: Path) -> bool:
    """Se `.gitignore` da raiz cobre o diretorio de estado local.

    Confere o TEXTO e nao chama `git check-ignore`: a SPEC 45 proibe executar
    git, e o que interessa aqui e se alguem declarou a linha, nao o veredito de
    um subprocesso que este motor nao pode rodar.
    """
    arquivo = raiz / ".gitignore"
    if not arquivo.is_file():
        return False
    try:
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
    except OSError:  # pragma: no cover -- .gitignore ilegivel
        return False
    alvos = (".sparkforge/local", ".sparkforge/local/", ".sparkforge/")
    return any(linha.strip() in alvos for linha in texto.splitlines())


def _code_integridade(banco: Path) -> str:
    """`PRAGMA integrity_check` do indice recem-construido, lido de volta.

    "Nao levantou" nao e medicao: um banco truncado abre sem erro e so denuncia
    na primeira consulta. A validacao da secao 74 e esta.
    """
    conexao = _codeintel_db.abrir(banco)
    try:
        (veredito,) = conexao.execute("PRAGMA integrity_check").fetchone()
    finally:
        conexao.close()
    return str(veredito)


def _code_seguranca(raiz: Path, banco: Path) -> dict[str, Any]:
    """SPEC 67. So o que este processo consegue MEDIR, e a lista do que nao.

    `sensitive_files_skipped`, `symlinks_skipped` e `oversized_files_skipped`
    saem em `not_measured` e nao como zero: `facts/scan.py` PULA os tres casos
    (`_e_sensivel`, `_e_atalho`, teto de tamanho) e nao CONTA nenhum deles.
    Publicar zero seria afirmar que nada foi pulado, que e o oposto do que se
    sabe. Contador zerado e a pior das tres saidas possiveis -- pior que a
    ausencia, porque ausencia nao mente.
    """
    violacoes = _codeintel_security.imports_proibidos()
    ambiente = dict(os.environ)
    removidas = _codeintel_security.sanitize_environment(ambiente)
    return {
        # `offline-strict` e afirmacao DERIVADA da varredura, nao rotulo fixo:
        # o perfil so e estrito enquanto nenhum modulo do motor importa rede.
        "network_policy": "offline-strict" if not violacoes else "violated",
        "forbidden_imports": len(violacoes),
        "audit_hook_installed": _codeintel_security.hook_instalado(),
        "secret_policy": "environment_sanitized",
        "secret_variables_stripped": len(removidas),
        # Impressao, nunca a raiz: ver `db.impressao_da_raiz`.
        "source_root": _codeintel_db.impressao_da_raiz(raiz),
        "db": banco.as_posix(),
        "not_measured": [
            "sensitive_files_skipped",
            "symlinks_skipped",
            "oversized_files_skipped",
        ],
    }


def code_init(repo: str, *, db: str | None = None) -> dict[str, Any]:
    """SPEC 74. Prepara o indice local e relata o que ficou de pe.

    A ordem das oito etapas e o contrato, e cada uma existe porque a ausencia
    dela ja seria defeito: raiz resolvida (nada e lido fora dela), preflight de
    seguranca (INV-001 antes de qualquer varredura), diretorio, conferencia do
    `.gitignore`, banco, indexacao, `PRAGMA integrity_check` e relatorio.

    Nao instala hook, nao acessa rede, nao muda o fonte e nao le fora da raiz.
    A conferencia do `.gitignore` REPORTA e nao corrige: escrever no
    `.gitignore` de quem chamou seria mudar arquivo versionado do repositorio
    analisado a partir de um verbo de leitura.

    A indexacao passa por `staleness.sincronizar` e nao por `index.indexar`
    porque a primeira grava o `EstadoDaArvore` -- sem ele, a proxima query
    conferiria a arvore contra um estado inexistente e sincronizaria de novo,
    para sempre.
    """
    raiz = _code_raiz(repo)
    violacoes = _codeintel_security.imports_proibidos()
    if violacoes:
        # INV-015: na duvida entre permitir e bloquear, bloquear. Um motor que
        # importa rede nao indexa nada ate alguem olhar.
        nomes = ", ".join(sorted({v.modulo for v in violacoes}))
        raise AdapterError(
            f"preflight de seguranca recusou: import de rede no motor ({nomes}).",
            exit_code=1,
        )

    banco = _code_banco(raiz, db)
    banco.parent.mkdir(parents=True, exist_ok=True)
    resultado = _codeintel_staleness.sincronizar(raiz, banco)
    integridade = _code_integridade(banco)
    if integridade != "ok":
        raise AdapterError(
            f"indice construido mas integrity_check devolveu {integridade!r}: "
            f"{banco.as_posix()}",
            exit_code=1,
        )
    return {
        "db": banco.as_posix(),
        "files": resultado.arquivos,
        "nodes": resultado.nos,
        "unreadable": resultado.ilegiveis,
        "edges": resultado.arestas,
        "unresolved": resultado.nao_resolvidas,
        "duration_s": round(resultado.duracao_s, 3),
        "full_rebuild": resultado.completa,
        "gitignored": _code_gitignorado(raiz),
        "integrity": integridade,
        "security": _code_seguranca(raiz, banco),
    }


def code_sync(repo: str, *, db: str | None = None) -> dict[str, Any]:
    """SPEC 65. A UNICA tool de mutacao do Code Intelligence.

    Escreve somente em `.sparkforge/local/codeintel/**`. Nunca toca o fonte do
    repositorio analisado -- a indexacao le, e o que ela escreve e banco.

    `reresolvidos` sai na resposta porque e o custo escondido do incremental:
    arquivos INALTERADOS que precisaram de um parse novo so porque a resolucao
    deles podia ter mudado. Somar esses arquivos aos alterados esconderia
    exatamente o numero que decide se o incremental se paga nesta arvore.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    banco.parent.mkdir(parents=True, exist_ok=True)
    resultado = _codeintel_staleness.sincronizar(raiz, banco)
    mudancas = resultado.mudancas
    return {
        "db": banco.as_posix(),
        "full_rebuild": resultado.completa,
        "changed_files": mudancas.quantidade,
        "added": list(mudancas.novos),
        "modified": list(mudancas.alterados),
        "removed": list(mudancas.removidos),
        "rereresolved_count": len(resultado.reresolvidos),
        "files": resultado.arquivos,
        "nodes": resultado.nos,
        "unreadable": resultado.ilegiveis,
        "edges": resultado.arestas,
        "unresolved": resultado.nao_resolvidas,
        "duration_s": round(resultado.duracao_s, 3),
    }


def _code_mudancas_no_grafo(raiz: Path, banco: Path) -> dict[str, Any]:
    """SPEC 63: o que mudou na arvore, lido como simbolo e como chamador.

    Isto NAO e uma tool propria, e a razao e de medida e nao de economia:
    `code_status` ja tem que conferir a arvore contra o indice para responder
    `fresh` e `changed_files` (secoes 43 e 64). "Quais simbolos moram nesses
    arquivos, e quem os chama" e a MESMA medicao um salto adiante -- nao uma
    capacidade nova. Uma tool separada duplicaria a conferencia de frescor e
    somaria um contrato ao catalogo para sempre.

    Nunca gera commit nem altera Git: le `.git/HEAD` e faz `stat`, e so.
    """
    conexao = _codeintel_db.abrir(banco)
    try:
        mudancas = _codeintel_staleness.detectar(raiz, conexao)
    finally:
        conexao.close()

    tocados = sorted(set(mudancas.alterados) | set(mudancas.novos))
    truncado = len(tocados) > CODE_CHANGED_MAX_FILES
    tocados = tocados[:CODE_CHANGED_MAX_FILES]

    simbolos: list[dict[str, Any]] = []
    for caminho in tocados:
        simbolos.extend(_code_nos_do_arquivo(banco, caminho))

    chamadores: list[dict[str, Any]] = []
    vistos = {s["node_id"] for s in simbolos}
    for simbolo in simbolos:
        for vizinho in _codeintel_graph.chamadores(banco, simbolo["node_id"]):
            if vizinho.node_id in vistos:
                continue
            vistos.add(vizinho.node_id)
            chamadores.append(_code_vizinho(vizinho))

    return {
        "changed_files": list(tocados),
        "removed_files": list(mudancas.removidos),
        "changed_symbols": simbolos,
        "affected_callers": chamadores,
        # Testes sao os chamadores cujo caminho e de teste -- derivado dos
        # mesmos chamadores, nunca de uma varredura propria: uma segunda
        # varredura poderia discordar da primeira sobre o mesmo arquivo.
        "affected_tests": [c for c in chamadores if _code_e_teste(c["path"])],
        "truncated": truncado,
    }


def _code_e_teste(caminho: str) -> bool:
    """Heuristica de caminho de teste, dita em vez de escondida numa condicao."""
    nome = Path(caminho).name
    return nome.startswith("test_") or nome.endswith("_test.py") or "/tests/" in caminho


def code_status(
    repo: str, *, db: str | None = None, detail_level: str = "full"
) -> dict[str, Any]:
    """SPEC 64 + 67 + 63. O estado do indice, e nenhum fonte.

    Esta e a UNICA consulta que NAO recusa quando o indice esta velho ou
    ausente, e isso nao contradiz a secao 43: ela nao responde COM o grafo, ela
    responde SOBRE o grafo. Recusar aqui deixaria o operador sem o unico verbo
    que diz por que as outras recusaram. Por isso ela roda com
    `auto_sync=False` (perguntar o estado nao pode escrever no indice) e
    converte a recusa em campo -- `fresh: false` com `stale_reason`.

    `detail_level` e o mesmo mecanismo das outras 20 tools deste catalogo:
    `full` acrescenta o bloco de seguranca da secao 67 e o de mudancas da secao
    63; `normal` e `summary` param no estado do indice. Nada e apagado em
    silencio -- o que `summary` nao traz, `full` traz com o mesmo nome.
    """
    if detail_level not in NIVEIS_DE_DETALHE:
        raise AdapterError(
            f"detail_level invalido: {detail_level!r}; use um de {NIVEIS_DE_DETALHE}",
            exit_code=2,
        )
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)

    if not banco.is_file():
        return {
            "db": banco.as_posix(),
            "initialized": False,
            "fresh": False,
            "stale_reason": "INDEX_MISSING",
            "action": _codeintel_staleness.ACAO_DE_SYNC,
            "files": 0,
            "symbols": 0,
            "edges": 0,
            "unresolved": 0,
            "schema_version": 0,
            "engine_version": "",
            "created_at": "",
            "root_fingerprint": "",
            "worktree": "",
        }

    fresco = True
    motivo = ""
    mudou = 0
    try:
        # `cooldown_s=0` DESLIGA a porta de 30 s da SPEC 43, e so aqui. O
        # cooldown existe para manter a varredura de disco fora do caminho de
        # uma RESPOSTA; neste verbo a varredura E a resposta. Honra-lo faria
        # `code status` dizer "fresco" por 30 s depois de um `git checkout` --
        # exatamente a pergunta que alguem faz o `status` para responder.
        _codeintel_staleness.garantir_frescor(
            raiz, banco, auto_sync=False, cooldown_s=0
        )
    except _codeintel_staleness.NegadoPorFrescor as exc:
        fresco = False
        motivo = exc.codigo
        mudou = int(exc.payload.get("changed_files", 0) or 0)

    indice = _codeintel_search.resumo(banco)
    estado = _codeintel_staleness.estado_da_arvore(raiz)
    corpo: dict[str, Any] = {
        "db": banco.as_posix(),
        "initialized": True,
        "fresh": fresco,
        "stale_reason": motivo,
        "action": "" if fresco else _codeintel_staleness.ACAO_DE_SYNC,
        "changed_files": mudou,
        "files": indice["files"],
        "symbols": indice["nodes"],
        **_code_contagens(banco),
        "schema_version": indice["schema_version"],
        "engine_version": indice["engine_version"],
        # A secao 64 pede `last_sync`, e o motor NAO grava esse carimbo: ele
        # grava `created_at` (nascimento do schema) e o veredito de frescor.
        # Sair com os dois medidos e melhor que sair com um inventado.
        "created_at": indice["created_at"],
        "root_fingerprint": indice["root_fingerprint"],
        "db_bytes": banco.stat().st_size,
        "worktree": estado.identidade,
        "head": estado.head,
        "ref": estado.ref,
    }
    if detail_level == "full":
        corpo["security"] = _code_seguranca(raiz, banco)
        corpo["changes"] = _code_mudancas_no_grafo(raiz, banco)
    return corpo


def code_search(
    repo: str,
    *,
    query: str,
    kind: str | None = None,
    path_prefix: str | None = None,
    limit: int = CODE_SEARCH_DEFAULT_LIMIT,
    db: str | None = None,
) -> dict[str, Any]:
    """SPEC 58. Busca simbolo por nome. Nenhum regex, nenhum SQL do chamador.

    O termo NUNCA vira MATCH direto: passa por `search.construir_consulta`, que
    tokeniza e escapa (SPEC 30, INV-008). Operador de FTS digitado pelo
    chamador vira texto literal em vez de mudar a consulta.

    `kind` e `path_prefix` sao filtrados AQUI e nao no SQL, e isso e desvio
    registrado: `search.buscar` nao aceita os dois, e esta fase nao e dona de
    `sparkforge/codeintel/`. O custo esta medido no teto: busca-se ate
    `CODE_SEARCH_MAX_LIMIT` linhas para filtrar depois, entao um filtro muito
    seletivo pode devolver menos que `limit` mesmo havendo mais no indice --
    e `filtered_from` sai na resposta para que isso seja legivel, nunca
    silencioso.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    indice = _code_frescor(raiz, banco)

    pedido = max(1, min(int(limit), CODE_SEARCH_MAX_LIMIT))
    bruto = _codeintel_search.buscar(banco, query, limite=CODE_SEARCH_MAX_LIMIT)
    filtrados = [
        achado
        for achado in bruto
        if (kind is None or achado.kind == kind)
        and (path_prefix is None or achado.path.startswith(path_prefix))
    ]
    pagina = filtrados[:pedido]
    return {
        "index": indice,
        "returned_count": len(pagina),
        "filtered_from": len(bruto),
        "results": [
            {
                "node_id": a.node_id,
                "name": a.name,
                "qualified_name": a.qualified_name,
                "kind": a.kind,
                "path": a.path,
                "start_line": a.start_line,
            }
            for a in pagina
        ],
    }


def code_symbol(
    repo: str,
    *,
    node_id: str,
    depth: int = 1,
    detail_level: str = "full",
    db: str | None = None,
) -> dict[str, Any]:
    """SPEC 59 + 61. Metadado, vizinhanca e raio de impacto de um simbolo.

    UMA tool para as duas secoes porque a entrada e a mesma (`node_id`) e a
    diferenca e de PROFUNDIDADE, nao de pergunta: `chamadores` e o raio de
    impacto com `depth=1`. Duas tools cobrariam o mesmo contrato duas vezes nos
    gates de paridade, para sempre.

    CORPO DE FONTE NUNCA SAI DAQUI, em nenhum `detail_level` -- a secao 59 e
    literal ("Source body nao vem por default") e este modulo le isso como
    "nao vem, ponto": fonte sai por `sparkforge_code_read`, que e a unica
    superficie com os tetos duros da secao 60 e com o objeto de confianca da
    16.3. Fonte atras de uma flag de verbosidade seria conteudo nao confiavel
    chegando por um caminho que nao carrega o rotulo.

    `detail_level` e o mesmo mecanismo das outras 20 tools: `summary` para no
    metadado, `normal` acrescenta chamadores e chamados diretos, `full`
    acrescenta o raio de impacto ate `depth`.
    """
    if detail_level not in NIVEIS_DE_DETALHE:
        raise AdapterError(
            f"detail_level invalido: {detail_level!r}; use um de {NIVEIS_DE_DETALHE}",
            exit_code=2,
        )
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    indice = _code_frescor(raiz, banco)

    profundidade = max(0, min(int(depth), CODE_MAX_DEPTH))
    corpo: dict[str, Any] = {
        "index": indice,
        "symbol": _code_no(banco, node_id),
        "callers": [],
        "callees": [],
        "impact": [],
        # A lista vazia de `callees` significa "nenhuma chamada RESOLVIDA", nao
        # "nenhuma chamada": `df.filtrar()` com tipo desconhecido vira
        # `unresolved_refs` e nao aresta. Sem este campo, um simbolo cheio de
        # chamadas dinamicas pareceria uma folha.
        "unresolved_note": (
            "callees traz somente chamadas resolvidas pelo indice; chamada com "
            "receptor de tipo desconhecido vive em unresolved_refs"
        ),
    }
    if detail_level in ("normal", "full"):
        corpo["callers"] = [
            _code_vizinho(n) for n in _codeintel_graph.chamadores(banco, node_id)
        ]
        corpo["callees"] = [
            _code_vizinho(n) for n in _codeintel_graph.chamados(banco, node_id)
        ]
    if detail_level == "full":
        corpo["impact"] = [
            _code_vizinho(n)
            for n in _codeintel_graph.impacto(banco, node_id, profundidade)
        ]
        corpo["tests"] = [item for item in corpo["impact"] if _code_e_teste(item["path"])]
    return corpo


def code_read(
    repo: str,
    *,
    node_id: str | None = None,
    file: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    context_lines: int = 3,
    max_tokens: int = CODE_READ_DEFAULT_TOKENS,
    db: str | None = None,
) -> dict[str, Any]:
    """SPEC 60. Leitura de fonte, limitada e SEMPRE dentro de objeto de confianca.

    Duas formas de entrada, e exatamente uma por chamada: `node_id` (o motor
    resolve arquivo e linhas) ou `file` + `start_line` + `end_line`. As duas
    juntas seriam duas fontes de verdade para a mesma resposta, e a ausencia das
    duas nao tem resposta -- ler o repositorio inteiro e o pedido que a secao 60
    proibe por escrito.

    Os tetos sao DUROS: 250 linhas, 32 KiB, 4096 tokens estimados. `max_tokens`
    do chamador so aperta. O que foi cortado sai em `truncated_by`.

    INV-014: o trecho vem em objeto com `trust`, nunca em prosa. INV-013: o
    rotulo e constante deste codigo, nao lido do repositorio analisado.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    indice = _code_frescor(raiz, banco)

    por_no = node_id is not None
    por_arquivo = file is not None
    if por_no == por_arquivo:
        raise AdapterError(
            "informe `node_id` OU `file` com `start_line`/`end_line`, nunca os dois "
            "nem nenhum: sem alvo, ler seria varrer o repositorio inteiro.",
            exit_code=2,
        )

    janela = max(0, min(int(context_lines), CODE_READ_MAX_CONTEXT_LINES))
    if por_no:
        no = _code_no(banco, node_id or "")
        inicio = max(1, int(no["start_line"]) - janela)
        fim = int(no["end_line"]) + janela
        relativo = no["path"]
        linguagem = no["language"] or "python"
        alvo = {"node_id": no["node_id"], "qualified_name": no["qualified_name"]}
    else:
        if start_line is None or end_line is None:
            raise AdapterError(
                "`file` exige `start_line` e `end_line`; faixa aberta seria o "
                "arquivo inteiro.",
                exit_code=2,
            )
        inicio, fim = int(start_line), int(end_line)
        if inicio < 1 or fim < inicio:
            raise AdapterError(
                f"faixa invalida: {inicio}..{fim}; start_line >= 1 e end_line >= start_line.",
                exit_code=2,
            )
        relativo = file or ""
        linguagem = "python"
        alvo = {"node_id": "", "qualified_name": ""}

    trecho = _code_trecho(raiz, relativo, inicio, fim, max_tokens=max_tokens, language=linguagem)
    return {"index": indice, "target": alvo, "snippet": trecho}


def code_context(
    repo: str,
    *,
    task: str,
    max_tokens: int | None = None,
    include: list[str] | None = None,
    db: str | None = None,
) -> dict[str, Any]:
    """SPEC 57. A tool principal: o `ContextPack` da secao 55 para uma tarefa.

    `task` NAO e ecoado de volta. Ele e a unica string do pacote que veio de
    fora sem normalizacao, e devolve-la seria carregar conteudo nao sanitizado
    num objeto que outro agente vai ler. O que sai e a EXPANSAO dela, derivada
    do dicionario versionado e auditavel.

    `graph_depth` da secao 57 NAO e aceito, e a ausencia e decisao: o
    `context.montar` deste repositorio nao tem manopla de profundidade -- ele
    ancora em sementes e usa a distancia como componente de escore. Aceitar o
    parametro e ignora-lo seria uma superficie que mente sobre o que controla.
    Quem quer profundidade tem `sparkforge_code_symbol` com `depth`.

    `include` seleciona entre as secoes que este motor sabe PREENCHER
    (`CODE_CONTEXT_INCLUDE`), `lineage` agora entre elas. So `snippets` continua
    RECUSADO com a razao em vez de devolvido vazio -- ver
    `CODE_CONTEXT_INCLUDE_NAO_IMPLEMENTADO`.

    `rules` e a secao 77: os ids relevantes ao vocabulario de dominio da
    consulta, com a razao de cada um. Nunca julgamento -- julgar e `judge`, e
    ele come FATO, nao simbolo.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    indice = _code_frescor(raiz, banco)

    pedidas = list(include) if include is not None else list(CODE_CONTEXT_INCLUDE)
    for secao in pedidas:
        if secao in CODE_CONTEXT_INCLUDE_NAO_IMPLEMENTADO:
            raise AdapterError(
                f"include {secao!r} recusado: "
                f"{CODE_CONTEXT_INCLUDE_NAO_IMPLEMENTADO[secao]}.",
                exit_code=2,
            )
        if secao not in CODE_CONTEXT_INCLUDE:
            raise AdapterError(
                f"include invalido: {secao!r}; use um de {list(CODE_CONTEXT_INCLUDE)}",
                exit_code=2,
            )

    if not task.strip():
        raise AdapterError("`task` vazia: nao ha o que expandir nem o que buscar.", exit_code=2)

    orcamento = None if max_tokens is None else int(max_tokens) * _codeintel_budget.BYTES_POR_TOKEN
    expansao = _codeintel_ranking.expandir(task)
    regras = (
        tuple(_code_regras_relevantes(expansao.clusters)) if "rules" in pedidas else ()
    )
    try:
        pacote = _codeintel_context.montar(banco, task, max_bytes=orcamento, regras=regras)
    except _codeintel_budget.OrcamentoImpossivel as exc:
        raise AdapterError(
            f"orcamento impossivel para esta consulta: {exc}", exit_code=2
        ) from exc

    corpo = pacote.para_dicionario()
    # O bloco `index` do pacote nasce com `fresh: None` porque `montar` nao
    # confere frescor -- quem confere e a fronteira. Preencher aqui e o que
    # torna `fresh: true` uma AFIRMACAO MEDIDA e nao um default otimista.
    corpo["index"].update(indice)
    omitidas = [s for s in CODE_CONTEXT_INCLUDE if s not in pedidas]
    for secao in omitidas:
        corpo[secao] = []
    corpo["omitted"] = omitidas
    return corpo


def code_doctor(repo: str, *, db: str | None = None) -> dict[str, Any]:
    """SPEC 75. Diagnostico local. Nao testa conectividade de internet.

    Cada verificacao devolve `(ok, detalhe)` e NENHUMA delas e derivada de
    outra: um doctor que concluisse "schema ok porque o banco abriu" estaria
    afirmando duas coisas com uma medicao so.

    `mcp_registration` e `tool_manifest` conferem a superficie desta CLI contra
    o catalogo declarado -- e o gate de drift da secao 69, que existe para que
    uma tool trocada de contrato nao passe despercebida.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    checagens: list[dict[str, Any]] = []

    def anotar(nome: str, ok: bool, detalhe: str) -> None:
        checagens.append({"check": nome, "ok": ok, "detail": detalhe})

    existe = banco.is_file()
    anotar("db_present", existe, banco.as_posix())
    if existe:
        integridade = _code_integridade(banco)
        anotar("db_integrity", integridade == "ok", integridade)
        indice = _codeintel_search.resumo(banco)
        anotar(
            "schema_version",
            indice["schema_version"] == _codeintel_db.SCHEMA_VERSION,
            f"indice={indice['schema_version']} motor={_codeintel_db.SCHEMA_VERSION}",
        )
        try:
            _codeintel_staleness.garantir_frescor(raiz, banco, auto_sync=False)
            anotar("staleness", True, "fresco")
        except _codeintel_staleness.NegadoPorFrescor as exc:
            anotar("staleness", False, f"{exc.codigo}: {exc}")
    else:
        anotar("db_integrity", False, "indice ausente")
        anotar("schema_version", False, "indice ausente")
        anotar("staleness", False, "INDEX_MISSING")

    anotar(
        "filesystem_writable",
        os.access(banco.parent if banco.parent.exists() else raiz, os.W_OK),
        (banco.parent if banco.parent.exists() else raiz).as_posix(),
    )
    anotar("gitignore", _code_gitignorado(raiz), ".sparkforge/local sob .gitignore")

    violacoes = _codeintel_security.imports_proibidos()
    anotar(
        "network_guard",
        not violacoes,
        "nenhum import de rede no motor"
        if not violacoes
        else ", ".join(sorted({v.modulo for v in violacoes})),
    )
    anotar("security_profile", True, "offline-strict")
    anotar("source_root", True, _codeintel_db.impressao_da_raiz(raiz))

    from sparkforge.adapters import tools as _tools

    faltando = [n for n in CODE_TOOLS if n not in _tools.TOOLS]
    anotar(
        "mcp_registration",
        not faltando,
        "todas as tools de codigo no catalogo"
        if not faltando
        else "ausentes: " + ", ".join(faltando),
    )
    manifesto = tool_manifest()
    anotar(
        "tool_manifest",
        manifesto["tool_count"] == len(_tools.TOOLS),
        f"{manifesto['tool_count']} tools, digest {manifesto['catalog_digest']}",
    )

    falhas = [c for c in checagens if not c["ok"]]
    return {
        "db": banco.as_posix(),
        "ok": not falhas,
        "failed_count": len(falhas),
        "checks": checagens,
    }


def code_purge(repo: str, *, db: str | None = None) -> dict[str, Any]:
    """SPEC 76. Apaga SOMENTE `.sparkforge/local/codeintel/`.

    O alvo e resolvido e comparado com o esperado ANTES de qualquer remocao, e
    qualquer outro diretorio e recusado. Sem essa porta, um `--db` apontando
    para o home apagaria o home: a diferenca entre um verbo de limpeza e um
    `rm -rf` com nome bonito e exatamente esta comparacao.
    """
    raiz = _code_raiz(repo)
    banco = _code_banco(raiz, db)
    alvo = banco.parent.resolve()
    esperado = (raiz / _codeintel_db.BANCO_PADRAO).parent.resolve()
    if alvo != esperado:
        raise AdapterError(
            f"purge recusado: {alvo.as_posix()} nao e o diretorio de codeintel "
            f"esperado ({esperado.as_posix()}).",
            exit_code=2,
        )
    if not alvo.is_dir():
        return {"purged": False, "path": alvo.as_posix(), "removed_files": 0}
    arquivos = [p for p in alvo.rglob("*") if p.is_file()]
    shutil.rmtree(alvo)
    return {"purged": True, "path": alvo.as_posix(), "removed_files": len(arquivos)}


# Os nomes das tools de Code Intelligence, num lugar so. `doctor` confere o
# catalogo contra esta lista, e ela e literal de proposito: derivar por prefixo
# faria o gate afirmar `sparkforge_code_* == sparkforge_code_*`.
CODE_TOOLS = (
    "sparkforge_code_context",
    "sparkforge_code_search",
    "sparkforge_code_symbol",
    "sparkforge_code_read",
    "sparkforge_code_status",
    "sparkforge_code_sync",
)


def tool_manifest() -> dict[str, Any]:
    """SPEC 69. Nome, hash de schema e hash de descricao, em ordem deterministica.

    O manifesto e DERIVADO do catalogo vivo, e nao um arquivo escrito a mao: um
    arquivo a mao registra o que alguem lembrou de atualizar, e o que a secao 69
    quer detectar e justamente a divergencia entre o que o catalogo diz e o que
    o servidor entrega. Quem quiser um gate de drift compara dois manifestos
    derivados em dois commits.

    A ordem e `sorted(TOOLS)` e nao a ordem de insercao do dict: catalogo de
    tool cacheavel exige ordem estavel, e ordem de insercao muda com edicao de
    arquivo sem que nenhum contrato tenha mudado.
    """
    from sparkforge.adapters import tools as _tools

    def _digest(valor: Any) -> str:
        texto = json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]

    entradas = [
        {
            "name": nome,
            "input_schema_sha256": _digest(_tools.TOOLS[nome]["inputSchema"]),
            "output_schema_sha256": _digest(_tools.TOOLS[nome]["outputSchema"]),
            "description_sha256": _digest(_tools.TOOLS[nome]["description"]),
        }
        for nome in sorted(_tools.TOOLS)
    ]
    return {
        "schema_version": 1,
        "tool_count": len(entradas),
        "catalog_digest": _digest(entradas),
        "tools": entradas,
    }
