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

import json
import re
from pathlib import Path
from typing import Any

from sparkforge.case import router, store
from sparkforge.case.playbook import build_playbook
from sparkforge.case.resume import render_handoff
from sparkforge.case.resume import resume as run_resume
from sparkforge.collect import aws as collect_aws
from sparkforge.collect.base import CollectorUnavailable, verify_all
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
from sparkforge.facts.consumers import extract_consumers_path, extract_consumers_tree
from sparkforge.facts.data_quality import (
    extract_data_quality_path,
    extract_data_quality_tree,
)
from sparkforge.facts.emr_cluster import extract_emr_cluster_path, extract_emr_cluster_tree
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.fusion import fuse as run_fuse
from sparkforge.facts.iceberg_metadata import (
    extract_iceberg_metadata_path,
    extract_iceberg_metadata_tree,
)
from sparkforge.facts.pyspark_ast import extract_path, extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.facts.s3_listing import extract_s3_listing_path, extract_s3_listing_tree
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.facts.sql_literal import extract_sql_from_pyspark, extract_sql_path
from sparkforge.facts.terraform import (
    extract_terraform_diff,
    extract_terraform_path,
    extract_terraform_tree,
)
from sparkforge.findings.models import Fact, RuntimeContext, sort_facts
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.knowledge_ref import KnowledgeError, knowledge_dir, safe_knowledge_file
from sparkforge.rules.engine import judge as run_judge
from sparkforge.rules.loader import CatalogError, load_catalog

DEFAULT_LIMIT = 50


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
    raw = {
        "glue_version": glue,
        # `emr_release` e a primeira chave de `_PLATFORM_KEYS["emr"]`, e
        # `_emr_key` aceita `emr-7.5.0` e `7.5.0` indiferentemente -- a flag nao
        # obriga o operador a saber qual das duas grafias o projeto guarda.
        # A flag e uma DECLARACAO, e por isso a fonte e `cli`, abaixo de
        # `event_log` e de `describe_cluster` em `_PRECEDENCE`: discordar de um
        # dump vira divergencia registrada, nunca resolucao silenciosa.
        "emr_release": emr,
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
) -> dict[str, Any]:
    facts = _extract_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

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

    return {
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
) -> dict[str, Any]:
    facts = _extract_catalog_facts(path)
    wanted_kinds = set(kind) if kind else None
    filtered = [f for f in facts if wanted_kinds is None or f.kind in wanted_kinds]

    by_kind = _count_by(filtered, lambda f: f.kind)
    items = [f.to_dict() for f in filtered]
    page, next_cursor = paginate_items(items, limit, cursor)

    # Mesmo raciocinio de `analyze_pyspark`: `unresolved` conta sobre `facts`,
    # nao sobre `filtered`, para um filtro por kind nao esconder o ponto cego.
    unresolved = sum(1 for f in facts if f.kind == "catalog.unresolved")
    unresolved_at = [
        {"file": f.subject.get("file", ""), "reason": f.attrs.get("reason", "")}
        for f in facts
        if f.kind == "catalog.unresolved"
    ]

    return {
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


def _facts_page(
    facts: list[Fact],
    unresolved_kind: str | None,
    kind: list[str] | None,
    limit: int | None,
    cursor: str | None,
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
) -> dict[str, Any]:
    facts = _extract_event_log_facts(path)
    return _facts_page(facts, "spark.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    """Extrai Facts do texto de um plano fisico ja salvo em disco.

    Um arquivo por chamada, nunca um diretorio: cada arquivo e UM plano, e
    concatenar planos de queries diferentes na mesma analise misturaria nos com
    a mesma numeracao `(N)` vindos de arvores distintas.
    """
    facts = _extract_plan_facts(path)
    return _facts_page(facts, "plan.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_terraform_facts(path)
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_iceberg_facts(path)
    return _facts_page(facts, "iceberg.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_sql_facts(path, from_pyspark)
    return _facts_page(facts, "sql.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_athena_workgroup_facts(path)
    return _facts_page(facts, "athena.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_emr_cluster_facts(path)
    return _facts_page(facts, "emr.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_data_quality_facts(path)
    return _facts_page(facts, "dq.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_s3_listing_facts(path)
    return _facts_page(facts, "s3.unresolved", kind, limit, cursor)


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
) -> dict[str, Any]:
    facts = _extract_consumers_facts(path)
    return _facts_page(facts, "env.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze terraform-diff
# --------------------------------------------------------------------------- #


def analyze_terraform_diff(
    before: str,
    after: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
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
    return _facts_page(facts, "tf.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# analyze call-graph
# --------------------------------------------------------------------------- #


def analyze_call_graph(
    facts_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Deriva Facts de grafo de chamadas a partir de um arquivo de facts ja
    extraido (tipicamente `analyze pyspark --out`). Funcao pura sobre Facts:
    nunca reparseia fonte -- ver docstring de `sparkforge.facts.call_graph`.
    Sem `unresolved` proprio: o grafo so deriva do que `pyspark_ast` ja
    resolveu, nunca falha em interpretar algo por si so.
    """
    fact_list = _load_facts_file(facts_path)
    derived = build_call_graph(fact_list, path_hint=facts_path)
    return _facts_page(derived, None, kind, limit, cursor)


# --------------------------------------------------------------------------- #
# benchmark
# --------------------------------------------------------------------------- #


def benchmark_runs(
    before_path: str,
    after_path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
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
    """
    before = _load_facts_file(before_path)
    after = _load_facts_file(after_path)
    facts = build_benchmark(before, after, path_hint=f"{before_path}..{after_path}")
    return _facts_page(facts, "bench.unresolved", kind, limit, cursor)


# --------------------------------------------------------------------------- #
# fuse
# --------------------------------------------------------------------------- #


def fuse_facts(
    facts_paths: list[str] | None,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
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

    summary = next((f for f in fused if f.kind == "fusion.summary"), None)

    return {
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


def _load_facts_file(facts_path: str) -> list[Fact]:
    path = Path(facts_path)
    if not path.is_file():
        raise AdapterError(
            f"Arquivo de facts nao encontrado: {facts_path}. Rode "
            f"`sparkforge analyze pyspark --path <dir> --out {facts_path}` para gera-lo.",
            exit_code=2,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AdapterError(f"{facts_path}: JSON invalido: {exc}", exit_code=2) from exc
    return _facts_from_dicts(raw)


def _merge_facts_files(facts_paths: list[str]) -> list[Fact]:
    """Une varios arquivos de facts numa lista unica, sem duplicata e ordenada.

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
        for fact in _load_facts_file(facts_path):
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
        fact_ids = {fact.id for fact in _load_facts_file(facts_path)}
    try:
        validate_finding(finding, fact_ids)
        return {"valid": True, "errors": []}
    except ValidationFailed as exc:
        return {"valid": False, "errors": [str(exc)]}


# --------------------------------------------------------------------------- #
# case lifecycle
# --------------------------------------------------------------------------- #


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
) -> dict[str, Any]:
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
    case = store.new_case(case_id, now, context.to_dict(), repo=repo)
    store.save_case(case, root=repo)
    return case


def case_get(repo: str) -> dict[str, Any]:
    try:
        return store.load_case(repo)
    except store.CaseError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc


def case_update(
    repo: str,
    phase: str | None = None,
    gate: str | None = None,
    gate_value: bool = True,
    skill: str | None = None,
    now: str | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    try:
        case = store.load_case(repo)
        if phase is not None:
            case = store.set_phase(case, phase)
        if gate is not None:
            case = store.set_gate(case, gate, bool(gate_value))
        if skill is not None:
            case = store.record_skill_use(case, skill, now or "", outcome or "")
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
