"""Adaptador de linha de comando. Casca fina sobre `sparkforge.adapters._core`.

Nenhuma logica de dominio mora aqui: nenhum limiar, nenhuma severidade,
nenhuma decisao de rota. `analyze` e `judge` sao verbos separados de proposito
-- extracao e julgamento sao passos independentes, o que permite rejulgar
facts antigos com um catalogo novo sem reprocessar o codigo-fonte.

Toda saida e JSON em stdout (`json.dumps(..., indent=2, ensure_ascii=False)`).
Erros nunca sao genericos: cada um carrega a causa e o comando que resolve,
via `_core.AdapterError`, tratado uma unica vez em `main()`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sparkforge import __version__ as _pkg_fallback
from sparkforge.adapters import _core

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        __version__ = _pkg_version("sparkforge-aws")
    except PackageNotFoundError:
        # Repo nao instalado (Devin CLI, sandbox, `python -m`). O fallback vem do
        # pacote, nunca de um literal repetido aqui: tres copias do numero e tres
        # chances de a CLI reportar uma versao que nao existe.
        __version__ = _pkg_fallback
except ImportError:  # pragma: no cover -- importlib.metadata sempre existe em py>=3.10
    __version__ = _pkg_fallback


def _ensure_utf8_streams() -> None:
    """Forca stdout/stderr para UTF-8.

    `json.dumps(..., ensure_ascii=False)` emite acentos e caracteres nao-ASCII
    crus de proposito (o catalogo e escrito em portugues). Sem isto, `print()`
    usa a codificacao padrao do stream, que no Windows segue a code page do
    console -- nao UTF-8 -- e corrompe a saida sempre que ela e capturada por
    outro processo (pipe, subprocess, MCP host) em vez de exibida num terminal
    ja configurado para UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except ValueError:  # pragma: no cover -- stream que nao aceita reconfigure
                pass


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _load_json_list(path: str) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.is_file():
        raise _core.AdapterError(f"Arquivo nao encontrado: {path}", exit_code=2)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _core.AdapterError(f"{path}: JSON invalido: {exc}", exit_code=2) from exc
    if not isinstance(data, list):
        raise _core.AdapterError(f"{path}: esperado uma lista.", exit_code=2)
    return data


_DETAIL_LEVEL_HELP = (
    "Verbosidade da saida. `full` (default) devolve o fato inteiro, com a "
    "procedencia dentro de cada item -- e o modo de reauditoria. `normal` "
    "declara procedencia e schema_version UMA VEZ no envelope e referencia a "
    "procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, "
    "medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um "
    "fato por id: para ter o fato inteiro de volta, reexecute em `full` e "
    "pague o payload inteiro outra vez."
)

# NOMES PROPRIOS (`full`/`compact`/`minimal`), e nao os de `_DETAIL_LEVEL_HELP`
# acima: `controlm describe` nao devolve `items` de fact, devolve dois
# dicionarios (`capabilities`, `deprecated`) e um terceiro so de recusa
# (`unresolved_detail`) sem `provenance`. Ver o comentario ao lado de
# `NIVEIS_DE_DETALHE_CONTROLM` em `_core.py` para a razao completa.
_CONTROLM_DETAIL_LEVEL_HELP = (
    "Verbosidade da saida. `full` (default) devolve o descritor inteiro -- e o "
    "modo de reauditoria. `compact` reduz `capabilities` a lista de slugs e "
    "tira `unresolved_detail` (`unresolved`, a mesma lista sem a razao, fica); "
    "`deprecated` continua INTEIRO, porque e a resposta direta a `o que eu nao "
    "posso mais usar` e cortar obrigaria uma segunda chamada para a MESMA "
    "pergunta. `minimal` reduz a `version`, `covers`, a CONTAGEM de "
    "`capabilities`, os SLUGS de `deprecated` e a CONTAGEM de `unresolved` -- "
    "a contagem nunca some, mesmo em zero, porque e a recusa nomeada da "
    "matriz; a lista de slugs e a razao de cada uma exigem `compact`/`full`."
)


def _add_detail_level(parser: argparse.ArgumentParser) -> None:
    """Acrescenta `--detail-level` a um subcomando que devolve FACTS.

    Os niveis vem de `_core.NIVEIS_DE_DETALHE`, nao de uma lista literal aqui:
    a projecao mora no `_core`, e duplicar os niveis no parser criaria duas
    fontes para a mesma verdade -- uma delas destinada a ficar desatualizada.

    So os verbos que devolvem facts recebem a flag. `judge` devolve findings e
    `rules lookup` devolve regras: nenhum dos dois tem `provenance`, e o
    `summary` de fato (`id`/`kind`/`measures`) nao existe nesses shapes.
    """
    parser.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=_DETAIL_LEVEL_HELP,
    )


def _apply_detail_level(payload: dict[str, Any], detail_level: str) -> dict[str, Any]:
    """Projeta `payload["items"]` e declara no envelope o que saiu dos itens.

    A CLI repagina por conta propria (`_core.analyze_*` e chamado com
    `limit=None` para o `--out` sair completo), entao a projecao tem que ser
    aplicada aqui tambem -- o `detail_level` que o `_core` recebe nao alcanca
    esta pagina.
    """
    payload["items"], procedencias, versao = _core.project_items(payload["items"], detail_level)
    return _core.declarar_no_envelope(payload, procedencias, versao)


# Uma unica redacao para os tres verbos que aceitam a flag. Repetir o texto tres
# vezes e como uma delas fica desatualizada.
_EMR_FLAG_HELP = (
    "Release do EMR. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. "
    "E DECLARACAO, nao observacao: perde para o event log e para um dump de "
    "`describe-cluster`, e discordar de um deles vira divergencia reportada, "
    "nunca valor substituido em silencio. Serve a quem sabe a release e nao tem "
    "o dump -- com o dump, `--facts` ja resolve sozinho. A MATRIZ consultada "
    "segue o conjunto de facts: num conjunto so de `emrs.*` (EMR Serverless) "
    "deriva da matriz do Serverless, que publica `spark` sem o sufixo do fork e "
    "nao publica `python` nem `iceberg` -- os dois saem vazios. Sobre facts "
    "`emrc.*` (EMR on EKS) a flag e RECUSADA com exit 2: la a matriz de EC2 e "
    "medidamente errada."
)

_CODE_DB_HELP = (
    "Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` "
    "sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora "
    "dali e escolha de quem chama, e o arquivo passa a ser candidato a commit."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sparkforge",
        description=(
            "Analise deterministica de jobs AWS Glue PySpark: extracao de facts, "
            "julgamento contra o catalogo de regras, e o ciclo de vida do case "
            "que atravessa sessoes."
        ),
    )
    parser.add_argument("--version", action="version", version=f"sparkforge {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # analyze pyspark ------------------------------------------------------
    analyze_p = sub.add_parser("analyze", help="Extrai facts deterministicos de codigo-fonte.")
    analyze_sub = analyze_p.add_subparsers(dest="analyze_target", required=True)
    pyspark_p = analyze_sub.add_parser(
        "pyspark", help="Extrai facts de PySpark via AST estatico (nunca importa o codigo)."
    )
    pyspark_p.add_argument("--path", required=True, help="Arquivo ou diretorio a analisar.")
    pyspark_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    pyspark_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    pyspark_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    pyspark_p.add_argument("--cursor")
    _add_detail_level(pyspark_p)

    catalog_p = analyze_sub.add_parser(
        "catalog-schema", help="Extrai facts de um dump JSON do Glue Data Catalog."
    )
    catalog_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps do catalogo."
    )
    catalog_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    catalog_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    catalog_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    catalog_p.add_argument("--cursor")
    _add_detail_level(catalog_p)

    event_log_analyze_p = analyze_sub.add_parser(
        "event-log", help="Extrai facts de um Spark event log (.jsonl) ja coletado."
    )
    event_log_analyze_p.add_argument("--path", required=True, help="Arquivo de event log.")
    event_log_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    event_log_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    event_log_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    event_log_analyze_p.add_argument("--cursor")
    _add_detail_level(event_log_analyze_p)

    sqlm_p = analyze_sub.add_parser(
        "sql-metrics",
        help="Extrai metrica por no do plano de um Spark event log ja coletado.",
    )
    sqlm_p.add_argument("--path", required=True, help="Event log em JSON Lines.")
    sqlm_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    sqlm_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sqlm_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sqlm_p.add_argument("--cursor")
    _add_detail_level(sqlm_p)

    cw_analyze_p = analyze_sub.add_parser(
        "cloudwatch",
        help="Extrai facts de um artefato de metricas do CloudWatch ja coletado.",
    )
    cw_analyze_p.add_argument("--path", required=True, help="Artefato JSON do CloudWatch.")
    cw_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    cw_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    cw_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    cw_analyze_p.add_argument("--cursor")
    _add_detail_level(cw_analyze_p)

    cwlog_analyze_p = analyze_sub.add_parser(
        "cloudwatch-logs",
        help="Extrai facts do LOG do run ja coletado do CloudWatch Logs.",
    )
    cwlog_analyze_p.add_argument(
        "--path",
        required=True,
        help="Artefato JSON de `collect cloudwatch-logs`, ou o DIRETORIO deles.",
    )
    cwlog_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    cwlog_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    cwlog_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    cwlog_analyze_p.add_argument("--cursor")
    _add_detail_level(cwlog_analyze_p)

    rlink_analyze_p = analyze_sub.add_parser(
        "glue-resource-link",
        help="Extrai a topologia do catalogo ja coletada: link, alvo e nome.",
    )
    rlink_analyze_p.add_argument(
        "--path", required=True,
        help="Artefato JSON de `collect glue-resource-link`, ou o DIRETORIO deles.",
    )
    rlink_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    rlink_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    rlink_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    rlink_analyze_p.add_argument("--cursor")
    _add_detail_level(rlink_analyze_p)

    iam_analyze_p = analyze_sub.add_parser(
        "iam-access",
        help="Extrai a DECISAO de IAM ja simulada, com a camada que decidiu.",
    )
    iam_analyze_p.add_argument(
        "--path", required=True,
        help="Artefato JSON de `collect iam-access`, ou o DIRETORIO deles.",
    )
    iam_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    iam_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    iam_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    iam_analyze_p.add_argument("--cursor")
    _add_detail_level(iam_analyze_p)

    lfg_analyze_p = analyze_sub.add_parser(
        "lakeformation-grants",
        help="Extrai a PERMISSAO do Lake Formation ja coletada (grant, registro, settings).",
    )
    lfg_analyze_p.add_argument(
        "--path",
        required=True,
        help="Artefato JSON de `collect lakeformation`, ou o DIRETORIO deles.",
    )
    lfg_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    lfg_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    lfg_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    lfg_analyze_p.add_argument("--cursor")
    _add_detail_level(lfg_analyze_p)

    sig_analyze_p = analyze_sub.add_parser(
        "error-signatures",
        help="Casa knowledge/errors/ contra os facts do case. Derivacao pura.",
    )
    sig_analyze_p.add_argument(
        "--facts",
        required=True,
        help=(
            "Arquivo de facts com a UNIAO do case -- `spark.exception` do event log E "
            "`cloudwatch.log_event` do log. Metade dos facts nao produz metade das "
            "respostas: produz ponto cego que nao aparece."
        ),
    )
    sig_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    sig_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sig_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sig_analyze_p.add_argument("--cursor")
    _add_detail_level(sig_analyze_p)

    pqf_analyze_p = analyze_sub.add_parser(
        "parquet-footer",
        help="Extrai facts do FOOTER do Parquet ja coletado.",
    )
    pqf_analyze_p.add_argument(
        "--path",
        required=True,
        help="Artefato JSON de `collect parquet-footer`, ou o DIRETORIO deles.",
    )
    pqf_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    pqf_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    pqf_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    pqf_analyze_p.add_argument("--cursor")
    _add_detail_level(pqf_analyze_p)

    runs_analyze_p = analyze_sub.add_parser(
        "glue-job-runs",
        help="Extrai facts de historico do diretorio de artefatos de run Glue.",
    )
    runs_analyze_p.add_argument(
        "--path", required=True, help="DIRETORIO de artefatos glue_job_run."
    )
    runs_analyze_p.add_argument("--job-name", required=True)
    runs_analyze_p.add_argument(
        "--cloudwatch",
        help="Diretorio de artefatos cloudwatch, para correlacionar por job_run_id.",
    )
    runs_analyze_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    runs_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    runs_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    runs_analyze_p.add_argument("--cursor")
    _add_detail_level(runs_analyze_p)

    plan_p = analyze_sub.add_parser(
        "plan",
        help=(
            "Extrai facts do texto de um plano fisico "
            '(`df.explain("formatted")` / EXPLAIN FORMATTED).'
        ),
    )
    plan_p.add_argument("--path", required=True, help="Arquivo de texto com a saida de explain.")
    plan_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    plan_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    plan_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    plan_p.add_argument("--cursor")
    _add_detail_level(plan_p)

    terraform_p = analyze_sub.add_parser(
        "terraform", help="Extrai facts de blocos aws_glue_job em HCL Terraform."
    )
    terraform_p.add_argument("--path", required=True, help="Arquivo ou diretorio .tf a analisar.")
    terraform_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    terraform_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    terraform_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    terraform_p.add_argument("--cursor")
    _add_detail_level(terraform_p)

    iceberg_p = analyze_sub.add_parser(
        "iceberg", help="Extrai facts de um dump JSON das metadata tables Iceberg."
    )
    iceberg_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps das metadata tables."
    )
    iceberg_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    iceberg_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    iceberg_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    iceberg_p.add_argument("--cursor")
    _add_detail_level(iceberg_p)

    sql_p = analyze_sub.add_parser(
        "sql", help="Extrai facts de texto SQL: arquivo .sql ou literal spark.sql(...) em PySpark."
    )
    sql_p.add_argument("--path", help="Arquivo .sql a analisar.")
    sql_p.add_argument(
        "--from-pyspark",
        help='Arquivo .py: extrai texto de chamadas spark.sql("...") em vez de ler --path.',
    )
    sql_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    sql_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sql_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sql_p.add_argument("--cursor")
    _add_detail_level(sql_p)

    athena_wg_analyze_p = analyze_sub.add_parser(
        "athena-workgroup", help="Extrai facts de um dump JSON de workgroups do Athena."
    )
    athena_wg_analyze_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps de workgroups."
    )
    athena_wg_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    athena_wg_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    athena_wg_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    athena_wg_analyze_p.add_argument("--cursor")
    _add_detail_level(athena_wg_analyze_p)

    emr_analyze_p = analyze_sub.add_parser(
        "emr-cluster",
        help="Extrai facts de um dump JSON de cluster EMR on EC2 (describe-cluster e os "
        "cinco dumps que o completam).",
    )
    emr_analyze_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps de cluster EMR."
    )
    emr_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    emr_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    emr_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    emr_analyze_p.add_argument("--cursor")
    _add_detail_level(emr_analyze_p)

    emrs_analyze_p = analyze_sub.add_parser(
        "emr-serverless",
        help="Extrai facts de um dump JSON de application EMR Serverless "
        "(get-application). Descreve o PADRAO da application, nunca o que um job run "
        "executou -- StartJobRun sobrepoe.",
    )
    emrs_analyze_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps de application."
    )
    emrs_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    emrs_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    emrs_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    emrs_analyze_p.add_argument("--cursor")
    _add_detail_level(emrs_analyze_p)

    emrc_analyze_p = analyze_sub.add_parser(
        "emr-eks",
        help="Extrai facts de um dump JSON de execucao Amazon EMR on EKS "
        "(describe-virtual-cluster e describe-job-run no mesmo arquivo). Descreve o "
        "que a EXECUCAO PEDIU, nunca o que o pod recebeu -- o pod template nao e "
        "lido e sai como recusa, e o lado EKS (nodegroup, autoscaling) nao existe "
        "neste dump.",
    )
    emrc_analyze_p.add_argument(
        "--path", required=True, help="Arquivo ou diretorio com dumps de execucao EMR on EKS."
    )
    emrc_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    emrc_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    emrc_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    emrc_analyze_p.add_argument("--cursor")
    _add_detail_level(emrc_analyze_p)

    ctm_analyze_p = analyze_sub.add_parser(
        "controlm-jobs",
        help="Extrai facts de uma definicao `Jobs-as-Code` do Control-M (BMC): folder, "
        "job com Type/Name/RunAs/Application, agendamento (When), dependencia por "
        "evento e por Flow, acao condicional (Type: If) e variavel. Le CODIGO-FONTE "
        "versionado, nunca execucao. Com --version, cruza as capacidades observadas "
        "com a matriz do Automation API e diz quais a versao declarada nao tem.",
    )
    ctm_analyze_p.add_argument(
        "--path", required=True, help="Arquivo .json ou diretorio com definicoes Jobs-as-Code."
    )
    # OPCIONAL, e a razao esta em `_core.analyze_controlm_jobs`: exigir a versao
    # faria quem so quer inventariar os jobs ter de inventar um numero, e numero
    # inventado atravessa o cruzamento e vira achado. Sem ela o cruzamento nao
    # acontece e sai recusa NOMEADA -- `version_not_declared` -- em vez de
    # silencio.
    ctm_analyze_p.add_argument(
        "--version",
        help="A versao do Control-M Automation API do ambiente ALVO "
        f"({_core.controlm_covers()[0]}--{_core.controlm_covers()[1]}). E DECLARACAO "
        "do operador: o JSON de Jobs-as-Code nao a carrega, e deduzi-la do conteudo "
        "seria adivinhar. Sem ela o cruzamento com a matriz nao acontece e a regra "
        "SF-CTM-001 fica pulada por `requires_facts`.",
    )
    ctm_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    ctm_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    ctm_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    ctm_analyze_p.add_argument("--cursor")
    _add_detail_level(ctm_analyze_p)

    dq_p = analyze_sub.add_parser(
        "data-quality",
        help="Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great "
        "Expectations e validacao artesanal): onde o check roda, se tem consequencia, "
        "e quantas passadas custa.",
    )
    dq_p.add_argument("--path", required=True, help="Arquivo .py ou diretorio com codigo PySpark.")
    dq_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    dq_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    dq_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    dq_p.add_argument("--cursor")
    _add_detail_level(dq_p)

    graph_p = analyze_sub.add_parser(
        "graph",
        help="Extrai facts de processamento de grafo (GraphFrames) no codigo PySpark: "
        "import e versao declarada, construcao do GraphFrame e persistencia dos dois "
        "DataFrames, algoritmo chamado com seus argumentos, e se o algoritmo exige "
        "checkpoint sem que o modulo o configure.",
    )
    graph_p.add_argument(
        "--path", required=True, help="Arquivo .py ou diretorio com codigo PySpark."
    )
    graph_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    graph_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    graph_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    graph_p.add_argument("--cursor")
    _add_detail_level(graph_p)

    s3_p = analyze_sub.add_parser(
        "s3-listing",
        help="Extrai facts de um dump de `aws s3api list-objects-v2` (small files, "
        "compressao nao splitavel).",
    )
    s3_p.add_argument(
        "--path", required=True, help="Arquivo .json ou diretorio com paginas da listagem."
    )
    s3_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    s3_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    s3_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    s3_p.add_argument("--cursor")
    _add_detail_level(s3_p)

    consumers_p = analyze_sub.add_parser(
        "consumers",
        help="Extrai facts do inventario declarado de consumidores de tabela.",
    )
    consumers_p.add_argument(
        "--path", required=True, help="Arquivo .yaml do inventario, ou diretorio com varios."
    )
    consumers_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    consumers_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    consumers_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    consumers_p.add_argument("--cursor")
    _add_detail_level(consumers_p)

    tf_diff_p = analyze_sub.add_parser(
        "terraform-diff",
        help="Compara dois estados de um modulo Terraform e marca o que mudou.",
    )
    tf_diff_p.add_argument("--before", required=True, help="Diretorio do estado anterior.")
    tf_diff_p.add_argument("--after", required=True, help="Diretorio do estado proposto.")
    tf_diff_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    tf_diff_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    tf_diff_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    tf_diff_p.add_argument("--cursor")
    _add_detail_level(tf_diff_p)

    call_graph_p = analyze_sub.add_parser(
        "call-graph",
        help="Deriva grafo de chamadas e alcance de trabalho Spark a partir de facts ja extraidos.",
    )
    call_graph_p.add_argument(
        "--facts", required=True, help="Arquivo de facts gerado por `analyze pyspark --out`."
    )
    call_graph_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    call_graph_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    call_graph_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    call_graph_p.add_argument("--cursor")
    _add_detail_level(call_graph_p)

    # migrate --------------------------------------------------------------
    # Verbo de TOPO, nao `analyze migrate`: tudo sob `analyze` extrai facts de
    # um artefato e para ali. Este extrai E julga, uma vez por degrau do
    # caminho -- mesma razao de `judge` e `fuse` serem verbos proprios.
    migrate_p = sub.add_parser(
        "migrate", help="Avalia migracao entre versoes de runtime com o catalogo."
    )
    migrate_sub = migrate_p.add_subparsers(dest="migrate_action", required=True)
    migrate_glue_p = migrate_sub.add_parser(
        "glue",
        help="Julga a migracao de um job Glue entre um par de versoes, degrau a degrau.",
    )
    migrate_glue_p.add_argument(
        "path",
        help=(
            "Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando "
            "existem e o inventario de consumidores em .sparkforge/consumers.yaml "
            "--, ou um .py sozinho."
        ),
    )
    # Sem default, os dois: um par embutido no codigo responde sobre um alvo
    # que ninguem declarou, e o veredito sai com a mesma cara de qualquer outro.
    migrate_glue_p.add_argument(
        "--from", dest="from_runtime", required=True, help="Versao de Glue de origem."
    )
    migrate_glue_p.add_argument(
        "--to", dest="to_runtime", required=True, help="Versao de Glue alvo."
    )
    migrate_glue_p.add_argument("--out", help="Escreve o assessment completo (JSON) neste arquivo.")

    # DOIS VERBOS, E NAO UM `--platform` EM `migrate glue`.
    #
    # `migrate glue` foi publicado com a plataforma NO NOME, e um `--platform`
    # ali criaria a combinacao absurda `migrate glue --platform emr_eks`. As
    # tres de EMR, ao contrario, dividem tudo o que importa aqui -- o mesmo
    # vocabulario de rotulo de release, a mesma normalizacao do prefixo `emr-`,
    # e o mesmo eixo `emr` valendo zero no catalogo --, e o que as separa e
    # exatamente qual matriz responde. Isso e um parametro, nao tres verbos:
    # `release describe` ja nomeia a plataforma por flag pela mesma razao.
    #
    # A uniao dos dois verbos cobre as quatro plataformas que
    # `sparkforge_migration_assess` aceita, que e o que a paridade CLI/MCP
    # cobra.
    migrate_emr_p = migrate_sub.add_parser(
        "emr",
        help=(
            "Julga a migracao de um job EMR entre um par de releases, degrau a "
            "degrau, na matriz da plataforma escolhida."
        ),
    )
    migrate_emr_p.add_argument(
        "path",
        help=(
            "Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando "
            "existem e o inventario de consumidores em .sparkforge/consumers.yaml "
            "--, ou um .py sozinho."
        ),
    )
    # Sem default, e nao `emr_ec2`: a matriz de EC2 NAO descreve EKS nem
    # Serverless, e o sub-projeto 1 mediu que elas divergem (Iceberg em 6 de 26
    # releases comparaveis). Um default aqui responderia sobre a plataforma
    # errada com a mesma cara de qualquer outra resposta.
    migrate_emr_p.add_argument(
        "--platform",
        required=True,
        choices=[p for p in _core.RELEASE_PLATFORMS if p.startswith("emr")],
        help="Qual matriz de EMR ordena o caminho e da o runtime de cada degrau.",
    )
    migrate_emr_p.add_argument(
        "--from",
        dest="from_runtime",
        required=True,
        help="Release de origem, com ou sem o prefixo `emr-`.",
    )
    migrate_emr_p.add_argument(
        "--to",
        dest="to_runtime",
        required=True,
        help="Release alvo, com ou sem o prefixo `emr-`.",
    )
    migrate_emr_p.add_argument("--out", help="Escreve o assessment completo (JSON) neste arquivo.")

    # TERCEIRO VERBO, pela mesma logica que separou `glue` de `emr`.
    #
    # Control-M nao divide vocabulario com nenhuma das quatro: a versao e
    # `9.0.2x.yyy` e nao `7.5.0`, nao ha prefixo a normalizar, e o eixo nao e
    # runtime -- e capacidade com fronteira. Um `--platform controlm` em
    # `migrate emr` seria a combinacao absurda que o comentario acima recusa
    # para `migrate glue --platform emr_eks`.
    migrate_controlm_p = migrate_sub.add_parser(
        "controlm",
        help=(
            "Julga a migracao de um job Control-M entre um par de versoes, "
            "degrau a degrau, por CAPACIDADE e nao por runtime."
        ),
    )
    migrate_controlm_p.add_argument(
        "path",
        help=(
            "Diretorio com as definicoes de `Jobs-as-Code` (`*.json`), ou um "
            "arquivo sozinho. E o mesmo artefato que o `ctm build` valida."
        ),
    )
    migrate_controlm_p.add_argument(
        "--from",
        dest="from_runtime",
        required=True,
        help="Versao de Control-M de origem, na grafia da matriz (`9.0.21.300`).",
    )
    # SEM a recusa de alvo anterior a origem, ao contrario dos dois verbos
    # acima: descer de versao e caso legitimo aqui -- um job pode estar indo
    # para um ambiente mais antigo --, e e exatamente onde `introduced_in`
    # morde. Recusar a descida esconderia metade dos casos.
    migrate_controlm_p.add_argument(
        "--to",
        dest="to_runtime",
        required=True,
        help="Versao alvo. Pode ser ANTERIOR a origem: descer e caso legitimo.",
    )
    migrate_controlm_p.add_argument(
        "--out", help="Escreve o assessment completo (JSON) neste arquivo."
    )

    # glue / iceberg -------------------------------------------------------
    # Verbos de TOPO por SERVICO, e nao mais um degrau sob `analyze`: os dois
    # comandos abaixo extraem E julgam, e `analyze` para na extracao. Cada um
    # nasce com um subcomando so; o parser fica assim para que o proximo
    # comando do mesmo servico entre sem renomear o que ja foi publicado.
    glue_p = sub.add_parser("glue", help="Comandos especificos do runtime AWS Glue.")
    glue_sub = glue_p.add_subparsers(dest="glue_action", required=True)
    dep_p = glue_sub.add_parser(
        "dependency-audit",
        help="Audita dependencia Python e binario Scala do job contra um runtime.",
    )
    dep_p.add_argument("path", help="Diretorio do job (requirements*.txt e .jar).")
    # Sem default: risco de ABI nao existe em abstrato. Um `.jar` de Scala 2.12
    # e correto sob Glue 5.1 e quebra sob 6.0.
    dep_p.add_argument(
        "--glue", required=True, dest="glue_version", help="Versao de Glue a auditar."
    )

    iceberg_p = sub.add_parser("iceberg", help="Comandos especificos de Apache Iceberg.")
    iceberg_sub = iceberg_p.add_subparsers(dest="iceberg_action", required=True)
    upgrade_p = iceberg_sub.add_parser(
        "assess-upgrade",
        help="Avalia subir o format version da tabela contra quem a consome. NAO executa.",
    )
    upgrade_p.add_argument(
        "path", help="Diretorio do job, com o inventario em .sparkforge/consumers.yaml."
    )
    upgrade_p.add_argument(
        "--from", dest="from_spec", type=int, required=True, help="Format version de origem."
    )
    upgrade_p.add_argument(
        "--to", dest="to_spec", type=int, required=True, help="Format version alvo."
    )

    # release --------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `benchmark` e `fuse`: nao le artefato do
    # operador -- compoe sobre as quatro matrizes de `knowledge/`.
    release_p = sub.add_parser(
        "release",
        help=(
            "O que uma release publica, e o que muda entre duas. Le matriz de "
            "versao; NAO avalia se algo quebra."
        ),
    )
    release_sub = release_p.add_subparsers(dest="release_action", required=True)

    release_describe_p = release_sub.add_parser(
        "describe",
        help=(
            "O que a fonte daquela plataforma publica para uma release. "
            "Componente nao publicado sai em `unresolved` NOMEADO."
        ),
    )
    release_describe_p.add_argument(
        "--platform",
        required=True,
        help=f"Uma das quatro: {', '.join(_core.RELEASE_PLATFORMS)}.",
    )
    release_describe_p.add_argument(
        "--release",
        required=True,
        help="O rotulo da release, com ou sem o prefixo `emr-` (ex.: 7.7.0, emr-7.7.0, 5.1).",
    )

    # controlm ---------------------------------------------------------------
    # VERBO PROPRIO, e nao uma quinta `--platform` de `release describe`: a
    # resposta tem DOIS eixos (capacidade com fronteira, componente com
    # exigencia) onde a daquele verbo tem um, e Control-M nao e plataforma de
    # Spark. A razao inteira mora ao lado de `_core.controlm_describe`.
    controlm_p = sub.add_parser(
        "controlm",
        help=(
            "Conhecimento versionado do Control-M Automation API. Le matriz de "
            "versao; NAO le artefato, NAO chama BMC e NAO julga."
        ),
    )
    controlm_sub = controlm_p.add_subparsers(dest="controlm_action", required=True)

    controlm_describe_p = controlm_sub.add_parser(
        "describe",
        help=(
            "O que vale numa versao do Automation API. Versao fora da faixa "
            "coberta sai como recusa NOMEADA, com o intervalo."
        ),
    )
    controlm_describe_p.add_argument(
        "--version",
        required=True,
        help=(
            "A versao do Automation API (ex.: 9.0.21.300). A faixa coberta e "
            f"{_core.controlm_covers()[0]}--{_core.controlm_covers()[1]}."
        ),
    )
    controlm_describe_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE_CONTROLM,
        default="full",
        help=_CONTROLM_DETAIL_LEVEL_HELP,
    )

    # OS QUATRO ARGUMENTOS, e nao `--platform` mais `--from`/`--to`.
    #
    # Os verbos irmaos que comparam dois lados nomeiam a direcao: `benchmark` e
    # `analyze terraform-diff` usam `--before`/`--after`, `migrate glue` e
    # `iceberg assess-upgrade` usam `--from`/`--to`. Os dois pares carregam uma
    # promessa que este verbo NAO pode cumprir: que o eixo da comparacao e o
    # tempo (ou o degrau de migracao) e que ele e ENTRADA. Aqui o eixo e
    # RESULTADO -- `axis` sai calculado das dimensoes que efetivamente variam --,
    # e ele pode ser `platform`, o que nenhum `--before/--after` descreveria.
    #
    # Por isso dois PARES `(plataforma, release)` explicitos, com os prefixos
    # `--left-`/`--right-` que sao os nomes que `release_diff.diff(left, right)`
    # ja usa no modelo. Um `--platform` unico com duas releases tornaria a
    # pergunta que motiva o verbo -- `emr-7.7.0` no EC2 contra o MESMO rotulo no
    # EKS -- inexprimivel.
    release_diff_p = release_sub.add_parser(
        "diff",
        help=(
            "O que muda entre duas releases, com o eixo (`release`, `platform` ou "
            "os dois) DECLARADO na saida."
        ),
    )
    release_diff_p.add_argument(
        "--left-platform",
        dest="left_platform",
        required=True,
        help="Plataforma do lado de ONDE o operador sai.",
    )
    release_diff_p.add_argument(
        "--left-release",
        dest="left_release",
        required=True,
        help="Release do lado de ONDE o operador sai.",
    )
    release_diff_p.add_argument(
        "--right-platform",
        dest="right_platform",
        required=True,
        help="Plataforma do lado PARA ONDE o operador vai.",
    )
    release_diff_p.add_argument(
        "--right-release",
        dest="right_release",
        required=True,
        help="Release do lado PARA ONDE o operador vai.",
    )

    # benchmark ------------------------------------------------------------
    # Verbo de TOPO, nao `analyze benchmark`: tudo sob `analyze` extrai facts de
    # um artefato, e este nao extrai nada -- compara dois conjuntos de facts ja
    # extraidos. Mesma razao de `fuse` ser verbo proprio.
    benchmark_p = sub.add_parser(
        "benchmark",
        help=(
            "Compara duas execucoes a partir dos facts de event log de cada uma. "
            "Nao executa nada e nao mede relogio."
        ),
    )
    benchmark_p.add_argument(
        "--before",
        required=True,
        help="Arquivo de facts gerado por `analyze event-log --out` da execucao ANTES.",
    )
    benchmark_p.add_argument(
        "--after",
        required=True,
        help="Arquivo de facts gerado por `analyze event-log --out` da execucao DEPOIS.",
    )
    benchmark_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    # Secao 52. Opcionais os dois: comparar duas execucoes no MESMO runtime
    # continua valendo -- e o caso de medir mudanca de codigo. Rotular um lado
    # so devolve `missing_runtime_label` nomeando o que falta, e rotular os dois
    # com o mesmo valor devolve `same_runtime_label`, porque comparar um runtime
    # consigo mesmo nao prova nada sobre trocar de runtime.
    benchmark_p.add_argument(
        "--before-runtime",
        dest="before_runtime",
        default="",
        help="Versao de runtime em que a execucao ANTES rodou (ex.: 5.1).",
    )
    benchmark_p.add_argument(
        "--after-runtime",
        dest="after_runtime",
        default="",
        help="Versao de runtime em que a execucao DEPOIS rodou (ex.: 6.0).",
    )
    benchmark_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    benchmark_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    benchmark_p.add_argument("--cursor")
    _add_detail_level(benchmark_p)

    # workload ---------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `benchmark` e `fuse`: nao extrai de
    # artefato -- classifica o que outros verbos ja extrairam.
    workload_p = sub.add_parser(
        "workload",
        help="Perfil de workload por eixos, a partir de facts ja extraidos.",
    )
    workload_p.add_argument("--facts", required=True, help="Arquivo de facts (--out de analyze).")
    workload_p.add_argument("--job-name", required=True)
    workload_p.add_argument("--job-run", required=True, help="Id do run que este perfil descreve.")
    workload_p.add_argument(
        "--history",
        help=(
            "Diretorio com um arquivo de facts por run anterior "
            "(`analyze glue-job-runs --out`), para a escala."
        ),
    )
    workload_p.add_argument("--out", help="Escreve o fingerprint completo (JSON) neste arquivo.")

    # capacity -----------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `benchmark`, `fuse` e `workload`: nao
    # extrai de artefato -- decide sobre o que outros verbos ja extrairam.
    capacity_p = sub.add_parser(
        "capacity",
        help=(
            "Escolhe a capacidade mais barata que cumpre o SLA, entre as capacidades "
            "que o job JA rodou. Nunca aplica a mudanca."
        ),
    )
    capacity_p.add_argument("--facts", required=True, help="Arquivo de facts (--out de analyze).")
    capacity_p.add_argument("--job-name", required=True)
    capacity_p.add_argument("--job-run", required=True, help="Id do run que este plano descreve.")
    capacity_p.add_argument(
        "--history",
        help=(
            "Diretorio com um arquivo de facts por run anterior "
            "(`analyze glue-job-runs --out`), para as capacidades observadas."
        ),
    )
    capacity_p.add_argument("--out", help="Escreve o plano completo (JSON) neste arquivo.")

    # finops -------------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `benchmark`, `fuse`, `workload` e
    # `capacity`: nao extrai de artefato -- reune o que outros verbos ja
    # extrairam sob o eixo financeiro.
    finops_p = sub.add_parser(
        "finops",
        help=(
            "O relatorio financeiro: custo, a troca recurso-tempo, e onde a "
            "alavanca esta -- capacidade ou codigo."
        ),
    )
    finops_p.add_argument("--facts", required=True, help="Arquivo de facts (--out de analyze).")
    finops_p.add_argument("--job-name", required=True)
    finops_p.add_argument("--out", help="Escreve o relatorio completo (JSON) neste arquivo.")

    # tune ---------------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `capacity` e `finops`: nao extrai de
    # artefato -- deriva configuracao do que outros verbos ja mediram. Nao
    # aplica nada, e nunca aplicara: o relatorio nomeia o nivel de seguranca de
    # cada proposta.
    tune_p = sub.add_parser(
        "tune",
        help=(
            "Configuracao Spark derivada da medida, com a procedencia de cada "
            "propriedade. Nunca aplica a mudanca."
        ),
    )
    tune_p.add_argument("--facts", required=True, help="Arquivo de facts (--out de analyze).")
    tune_p.add_argument("--out", help="Escreve o relatorio completo (JSON) neste arquivo.")

    # economy ------------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `capacity`, `finops` e `tune`: compoe
    # sobre o ledger e nao le artefato nenhum.
    economy_p = sub.add_parser(
        "economy",
        help="O que a execucao poe na janela de contexto: byte medido, nunca token estimado.",
    )
    economy_sub = economy_p.add_subparsers(dest="subcommand", required=True)
    economy_report_p = economy_sub.add_parser(
        "report", help="Agrupa os spans de um run e poe a superficie ao lado."
    )
    economy_report_p.add_argument("--run-id", required=True)
    economy_report_p.add_argument(
        "--host-transcript",
        default="",
        help=(
            "Transcript JSONL do host, quando houver. Sem ele o relatorio traz "
            "`tokens_unresolved` -- token de provider e do host, nao deste processo."
        ),
    )
    economy_report_p.add_argument("--out", help="Escreve o relatorio (JSON) neste arquivo.")

    # agentic: agents -------------------------------------------------------
    agents_p = sub.add_parser(
        "agents",
        help="Lista e inspeciona agentes do runtime agêntico.",
    )
    agents_sub = agents_p.add_subparsers(dest="agents_action", required=True)
    agents_list_p = agents_sub.add_parser("list", help="Lista agentes disponíveis.")
    agents_list_p.add_argument("--repo", default=".")
    agents_inspect_p = agents_sub.add_parser("inspect", help="Inspeciona um agente.")
    agents_inspect_p.add_argument("--repo", default=".")
    agents_inspect_p.add_argument("--id", required=True, help="ID do agente.")

    # agentic: blackboard ---------------------------------------------------
    bb_p = sub.add_parser(
        "blackboard",
        help="Lê o shared blackboard (.sparkforge/blackboard/).",
    )
    bb_sub = bb_p.add_subparsers(dest="blackboard_action", required=True)
    bb_summary_p = bb_sub.add_parser("summary", help="Resumo contável do blackboard.")
    bb_summary_p.add_argument("--repo", default=".")
    bb_list_p = bb_sub.add_parser("list", help="Lista entidades de um tipo.")
    bb_list_p.add_argument("--repo", default=".")
    bb_list_p.add_argument(
        "--type",
        required=True,
        choices=[
            "claims",
            "evidence",
            "hypotheses",
            "objections",
            "rebuttals",
            "contradictions",
            "experiments",
            "decisions",
            "unknowns",
        ],
    )

    # agentic: decisions ----------------------------------------------------
    decisions_p = sub.add_parser(
        "decisions",
        help="Lista e explica decisões registradas.",
    )
    decisions_sub = decisions_p.add_subparsers(dest="decisions_action", required=True)
    decisions_list_p = decisions_sub.add_parser("list", help="Lista decisões.")
    decisions_list_p.add_argument("--repo", default=".")
    decisions_explain_p = decisions_sub.add_parser("explain", help="Explica uma decisão.")
    decisions_explain_p.add_argument("--repo", default=".")
    decisions_explain_p.add_argument("--id", required=True, help="ID da decisão.")

    # agentic: budget -------------------------------------------------------
    budget_p = sub.add_parser(
        "budget",
        help="Mostra estado do budget do case.",
    )
    budget_sub = budget_p.add_subparsers(dest="budget_action", required=True)
    budget_show_p = budget_sub.add_parser("show", help="Mostra budget do case.")
    budget_show_p.add_argument("--repo", default=".")
    budget_show_p.add_argument(
        "--template",
        action="store_true",
        help=(
            "Mostra os valores PADRAO do codigo, rotulados como template. "
            "Nao e o estado do case -- sem esta flag, budget nao declarado "
            "sai como unresolved."
        ),
    )

    # agentic: autonomy -----------------------------------------------------
    autonomy_p = sub.add_parser(
        "autonomy",
        help="Mostra níveis de autonomia L0-L5.",
    )
    autonomy_sub = autonomy_p.add_subparsers(dest="autonomy_action", required=True)
    autonomy_show_p = autonomy_sub.add_parser("show", help="Mostra perfil de um nível.")
    autonomy_show_p.add_argument(
        "--level",
        required=True,
        choices=["L0", "L1", "L2", "L3", "L4", "L5"],
    )

    # funcval ---------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `benchmark`: nao extrai de artefato --
    # `plan` deriva de facts ja extraidos, `compare` le o resultado que o
    # operador mediu. O motor nunca executa consulta em nenhum dos dois.
    funcval_p = sub.add_parser(
        "funcval",
        help=(
            "Validacao funcional: deriva o que medir nos dois lados de uma mudanca "
            "e compara antes contra depois. Nao executa nada."
        ),
    )
    funcval_sub = funcval_p.add_subparsers(dest="funcval_action", required=True)

    funcval_plan_p = funcval_sub.add_parser(
        "plan",
        help=(
            "Deriva o plano de validacao (contagem, schema, agregados) dos facts "
            "ja extraidos, e grava o artefato que `funcval compare` rele."
        ),
    )
    funcval_plan_p.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Arquivo de facts (JSON) gerado por `analyze pyspark --out` ou "
            "`analyze catalog-schema --out`. Repetivel, e precisa ser: o alvo vem do "
            "`pyspark.write` e o schema/os agregados vem do `catalog.table_schema`, "
            "que nenhum verbo produz no mesmo arquivo."
        ),
    )
    funcval_plan_p.add_argument(
        "--key",
        action="append",
        help=(
            "Chave de negocio DECLARADA, repetivel. Virgula faz chave COMPOSTA "
            "(`--key loja_id,pedido_id` e uma chave de duas colunas, nao duas chaves). "
            "Nenhum fact do repositorio nomeia chave de negocio, entao o eixo so "
            "existe se voce o declarar -- e o check sai com `origin: declared`. Sem "
            "`--key`, o plano escreve o eixo como ausente em `undeclared_axes`."
        ),
    )
    funcval_plan_p.add_argument(
        "--out",
        required=True,
        help=(
            "Escreve o plano (JSON de facts) neste arquivo. OBRIGATORIO, ao contrario "
            "do `--out` dos verbos de `analyze`: o plano e a entrada de "
            "`funcval compare --plan` e a evidencia do gate, nao uma conveniencia."
        ),
    )
    funcval_plan_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    funcval_plan_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    funcval_plan_p.add_argument("--cursor")
    _add_detail_level(funcval_plan_p)

    funcval_compare_p = funcval_sub.add_parser(
        "compare",
        help=(
            "Compara os dois resultados que VOCE mediu contra o plano. Antes contra "
            "depois, nunca observado contra catalogo."
        ),
    )
    funcval_compare_p.add_argument(
        "--plan", required=True, help="Arquivo gerado por `funcval plan --out`."
    )
    funcval_compare_p.add_argument(
        "--before",
        required=True,
        help=(
            "Resultado medido ANTES da mudanca: JSON com `target` e `checks`, um "
            "objeto por check. `value: null` exige `unavailable_reason`; check que "
            "voce nao mediu fica AUSENTE, nunca zero."
        ),
    )
    funcval_compare_p.add_argument(
        "--after", required=True, help="Resultado medido DEPOIS, no mesmo contrato."
    )
    funcval_compare_p.add_argument(
        "--out",
        help=(
            "Escreve a comparacao (JSON de facts) neste arquivo, que e o que "
            "`judge --facts` le. Opcional, ao contrario do `--out` do `plan`: o plano e "
            "a entrada do proximo verbo, esta e uma saida terminal. Grava a lista "
            "COMPLETA, nunca a pagina -- `--limit` corta o stdout e nao o arquivo."
        ),
    )
    funcval_compare_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    funcval_compare_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    funcval_compare_p.add_argument("--cursor")
    _add_detail_level(funcval_compare_p)

    # fuse ---------------------------------------------------------------
    fuse_p = sub.add_parser(
        "fuse",
        help=(
            "Correlaciona facts de SQL com schema do catalogo "
            "(sparkforge.facts.fusion), antes de judge."
        ),
    )
    fuse_p.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Arquivo de facts (JSON) gerado por `analyze`. Repetivel: fusao precisa "
            "ver as fontes que quer correlacionar na mesma chamada."
        ),
    )
    fuse_p.add_argument(
        "--out", help="Escreve a lista completa de facts fundidos (JSON) neste arquivo."
    )
    fuse_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    fuse_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    fuse_p.add_argument("--cursor")
    _add_detail_level(fuse_p)

    # judge ------------------------------------------------------------
    judge_p = sub.add_parser(
        "judge", help="Aplica o catalogo de regras versionado sobre facts ja extraidos."
    )
    judge_p.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Arquivo de facts (JSON) gerado por `analyze`. Repetivel: regra que "
            "correlaciona extratores diferentes (SF-GLUE-004 cruza tf.attribute com "
            "pyspark.write) so dispara com as duas fontes na mesma chamada."
        ),
    )
    judge_p.add_argument("--glue")
    judge_p.add_argument("--emr", help=_EMR_FLAG_HELP)
    judge_p.add_argument("--spark")
    judge_p.add_argument("--python")
    judge_p.add_argument("--iceberg")
    judge_p.add_argument("--athena")
    judge_p.add_argument("--severity", action="append", help="Filtra por severidade. Repetivel.")
    judge_p.add_argument("--out", help="Escreve a lista completa de findings (JSON) neste arquivo.")
    judge_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    judge_p.add_argument("--cursor")
    judge_p.add_argument("--show-skipped", action="store_true")
    judge_p.add_argument(
        "--source-freshness",
        action="store_true",
        help=(
            "Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), "
            "calculado sobre knowledge/sources.lock.json. Depende do lock e do dia."
        ),
    )
    judge_p.add_argument(
        "--as-of", help="Dia de referencia do estado das fontes (AAAA-MM-DD)."
    )

    # arbitrate --------------------------------------------------------
    # Verbo de TOPO, e nao um `agentic arbitrate`: ele nao extrai de artefato
    # (roda sobre findings que `judge` ja produziu) e nao e inspecao de estado
    # como `blackboard` e `decisions`. A forma dos argumentos segue os verbos
    # agenticos -- `--repo`, nunca `--case <id>` --, porque o blackboard mora
    # em `<repo>/.sparkforge/blackboard/` e nao ha id de case em CLI nenhuma
    # deste pacote.
    arbitrate_p = sub.add_parser(
        "arbitrate",
        help=(
            "Executor agentico deterministico: arbitra findings ja julgados e grava "
            "claim, evidencia, contradicao, lacuna e decisao no blackboard do case. "
            "Nao estima ganho, nao publica score, nao executa debate."
        ),
    )
    arbitrate_p.add_argument(
        "--findings",
        required=True,
        help=(
            "Arquivo de findings (JSON) gerado por `judge --out`. Aceita a lista nua "
            "e o objeto com a chave `findings` (ou `items`)."
        ),
    )
    arbitrate_p.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Arquivo de facts (JSON). Repetivel, e a repeticao e o ponto: o executor "
            "recebe a UNIAO dos facts do case -- o MESMO conjunto que `judge` recebeu "
            "para produzir aqueles findings. Alimenta-lo com um subconjunto fabrica "
            "claim desancorada que a execucao real nao produz. Aceita a lista nua e o "
            "objeto com a chave `facts` (ou `items`); fact sem `id` tem o id computado "
            "pelo conteudo."
        ),
    )
    arbitrate_p.add_argument(
        "--repo",
        default=".",
        help="Raiz do case. O blackboard fica em <repo>/.sparkforge/blackboard/.",
    )
    arbitrate_p.add_argument("--glue")
    arbitrate_p.add_argument("--emr", help=_EMR_FLAG_HELP)
    arbitrate_p.add_argument("--spark")
    arbitrate_p.add_argument("--python")
    arbitrate_p.add_argument("--iceberg")
    arbitrate_p.add_argument("--athena")

    # case ------------------------------------------------------------
    case_p = sub.add_parser("case", help="Gerencia o estado do case em .sparkforge/case.yaml.")
    case_sub = case_p.add_subparsers(dest="case_action", required=True)

    open_p = case_sub.add_parser("open", help="Cria um case novo, em fase intake.")
    open_p.add_argument("--repo", required=True)
    open_p.add_argument("--case-id", required=True)
    open_p.add_argument(
        "--now", required=True, help="Timestamp ISO 8601. Nunca lido do relogio pela CLI."
    )
    open_p.add_argument("--glue")
    open_p.add_argument("--emr", help=_EMR_FLAG_HELP)
    open_p.add_argument("--spark")
    open_p.add_argument("--python")
    open_p.add_argument("--iceberg")
    open_p.add_argument("--athena")
    open_p.add_argument(
        "--facts",
        action="append",
        help=(
            "Arquivo de facts (JSON) gerado por `analyze`. Repetivel. O runtime "
            "do case passa a sair do que os extratores observaram, nao so das "
            "flags."
        ),
    )
    open_p.add_argument(
        "--strict-gates",
        action="store_true",
        help=(
            "Grava no case que gate com produtor declarado passa a bloquear a "
            "transicao de fase. A escolha e do case, nao da invocacao: vale "
            "pela investigacao inteira, e quem retoma noutra maquina herda o "
            "rigor de quem abriu. Sem a flag, o comportamento e o de sempre "
            "(gate advisory)."
        ),
    )
    open_p.add_argument(
        "--reopen",
        action="store_true",
        help=(
            "Recomeca do zero por cima de um case que ja existe. Sem esta flag, "
            "abrir sobre um case existente e RECUSADO: sobrescrever apagaria a "
            "fase, o rigor e os overrides gravados. O `strict_gates` do case "
            "atual e herdado -- `--strict-gates` sobe o rigor, e nada o baixa "
            "por omissao de flag."
        ),
    )

    get_p = case_sub.add_parser("get", help="Le o case atual.")
    get_p.add_argument("--repo", required=True)

    update_p = case_sub.add_parser(
        "update", help="Atualiza fase, gate ou registra uso de skill no case."
    )
    update_p.add_argument("--repo", required=True)
    update_p.add_argument("--phase")
    update_p.add_argument("--gate")
    update_p.add_argument("--gate-value", choices=["true", "false"], default="true")
    update_p.add_argument("--skill")
    update_p.add_argument("--now")
    update_p.add_argument("--outcome")
    update_p.add_argument(
        "--hypothesis",
        help=(
            "Afirmacao testavel a registrar no case. Exige `--prediction` e "
            "`--experiment`: afirmacao sem previsao nao e testavel, e previsao "
            "sem experimento nao diz quem a testa."
        ),
    )
    update_p.add_argument("--prediction", help="O que muda no numero se a hipotese valer.")
    update_p.add_argument("--experiment", help="Como medir a previsao.")
    update_p.add_argument(
        "--close-hypothesis",
        metavar="ID",
        help=(
            "Fecha a hipotese com este id. Exige `--hypothesis-outcome`. O "
            "registro e acrescimo: a afirmacao original fica onde esta."
        ),
    )
    update_p.add_argument(
        "--hypothesis-outcome",
        choices=list(_core.store.HYPOTHESIS_OUTCOMES),
        help=(
            "Desfecho do experimento. `abandoned` existe porque a terceira "
            "coisa que acontece de verdade e o experimento nunca rodar."
        ),
    )
    update_p.add_argument(
        "--evidence",
        help="Onde ler o que fechou a hipotese (stage, run, arquivo de facts).",
    )
    update_p.add_argument(
        "--override-gate",
        help=(
            "Passa por cima de um gate num case estrito, quando o dado "
            "genuinamente nao existe (job descontinuado, ambiente que sumiu). "
            "Exige `--reason`. Fica gravado no case como lista: dois overrides "
            "do mesmo gate sao dois fatos, e nenhum apaga o outro."
        ),
    )
    update_p.add_argument(
        "--reason",
        help="Motivo do `--override-gate`. Sem ele o override e recusado.",
    )
    update_p.add_argument(
        "--facts",
        action="append",
        help=(
            "Arquivo de facts (JSON) que comprova os gates da fase pedida. "
            "Repetivel. Num case estrito, e daqui que sai a evidencia que "
            "destrava `--phase`."
        ),
    )

    # next-step / resume / handoff ------------------------------------
    next_p = sub.add_parser(
        "next-step",
        help="Rota deterministica a partir de routing.yaml (nunca julgamento do agente).",
    )
    next_p.add_argument("--repo", required=True)
    next_p.add_argument("--findings", help="Arquivo de findings (JSON) usado para casar condicoes.")

    resume_p = sub.add_parser("resume", help="Payload de rehidratacao do case.")
    resume_p.add_argument("--repo", required=True)
    resume_p.add_argument("--findings")
    resume_p.add_argument("--unresolved", type=int, default=0)
    resume_p.add_argument("--in-flight", default="")

    handoff_p = sub.add_parser(
        "handoff", help="Escreve .sparkforge/handoff.md e imprime o payload."
    )
    handoff_p.add_argument("--repo", required=True)
    handoff_p.add_argument("--findings")
    handoff_p.add_argument("--unresolved", type=int, default=0)
    handoff_p.add_argument("--in-flight", default="")

    playbook_p = sub.add_parser(
        "playbook",
        help=(
            "Decomposicao de um coordenador em passos sequenciais -- o PISO de "
            "orquestracao das cinco plataformas: unico caminho em Codex e Copilot CI, "
            "e o caminho em Claude Code, Devin CLI e Devin Local agent quando o "
            "despacho de subagente esta desligado -- e, no Devin, tambem quando ele "
            "esta ligado, porque subagente nao gera subagente por default. Le "
            "agents/, nunca repete a lista de executores."
        ),
    )
    playbook_p.add_argument("coordinator")
    playbook_p.add_argument("--repo", default=".")
    playbook_p.add_argument(
        "--findings",
        help="Arquivo de findings (JSON) usado para resolver o next_step embutido (AGENT-*).",
    )

    # runtime detect ----------------------------------------------------
    runtime_p = sub.add_parser(
        "runtime", help="Deteccao de runtime Glue/EMR/Spark/Python/Iceberg/Athena."
    )
    runtime_sub = runtime_p.add_subparsers(dest="runtime_action", required=True)
    detect_p = runtime_sub.add_parser(
        "detect", help="Deriva a matriz de runtime a partir de facts ja extraidos e de flags."
    )
    detect_p.add_argument("--glue")
    detect_p.add_argument("--emr", help=_EMR_FLAG_HELP)
    detect_p.add_argument("--spark")
    detect_p.add_argument("--python")
    detect_p.add_argument("--iceberg")
    detect_p.add_argument("--athena")
    detect_p.add_argument(
        "--facts",
        action="append",
        help=(
            "Arquivo de facts (JSON) gerado por `analyze`. Repetivel. A versao "
            "OBSERVADA pelos extratores (`tf.attribute` glue_version, "
            "`spark.runtime_version`) entra como fonte propria -- sem isto, so "
            "as flags alimentam a deteccao."
        ),
    )

    # code --------------------------------------------------------
    # O PAYLOAD deste verbo agora VEM de `_core`, como o de todos os outros --
    # a excecao que existia aqui caiu com a fase da superficie MCP (SPEC 56-77).
    # A razao dela nao era errada e continua registrada: o indice responde ONDE
    # um simbolo esta, e nao produz fato nem achado, entao ele nao atravessa o
    # envelope de FACT (`project_items`, `provenance_ref`, paginacao). O que
    # mudou e o motivo de estar fora: enquanto nao havia tool MCP, ter o payload
    # aqui custava uma duplicacao so; com as seis tools de `sparkforge_code_*`,
    # cada linha de payload que nascesse aqui seria uma linha que a CLI e o MCP
    # poderiam divergir -- que e exatamente o que `parity.yaml` existe para
    # pegar. `_core` recebeu as funcoes; ele nao ganhou envelope de fato por
    # causa disso.
    code_p = sub.add_parser(
        "code",
        help=(
            "Indice local de codigo: prepara, sincroniza, busca simbolo, monta "
            "contexto e diagnostica."
        ),
    )
    code_sub = code_p.add_subparsers(dest="code_action", required=True)

    def _code_comum(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """`--root` e `--db` nos nove subcomandos, de um lugar so.

        Repetidos em cada um, bastaria um divergir para `init` gravar num lugar
        e `search` ler noutro -- e o sintoma seria "nenhum simbolo", nao um
        erro. Falha calada e a unica que este verbo nao pode ter.
        """
        parser.add_argument("--root", default=".")
        parser.add_argument("--db", help=_CODE_DB_HELP)
        return parser

    _code_comum(
        code_sub.add_parser(
            "init",
            aliases=["index"],
            help=(
                "Prepara o indice sob --root: preflight de seguranca, diretorio, "
                "conferencia do .gitignore, banco, indexacao e integridade. "
                "`index` e o nome antigo do mesmo comando."
            ),
        )
    )

    _code_comum(
        code_sub.add_parser(
            "sync", help="Poe o indice em dia com a arvore. Unica escrita do verbo."
        )
    )

    code_status_p = _code_comum(
        code_sub.add_parser(
            "status",
            help="Estado do indice: frescor, contagens, seguranca e o que mudou na arvore.",
        )
    )
    code_status_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=(
            "Mesmos niveis das tools de fact, conteudo proprio deste verbo: "
            "`full` acrescenta o bloco de seguranca (SPEC 67) e o de mudancas "
            "(SPEC 63); `normal` e `summary` param no estado do indice."
        ),
    )

    code_search_p = _code_comum(
        code_sub.add_parser("search", help="Busca simbolo por parte do nome.")
    )
    code_search_p.add_argument("term")
    code_search_p.add_argument("--kind", help="Filtra por tipo de no: function, class, method.")
    code_search_p.add_argument("--path-prefix", help="Filtra por prefixo do caminho relativo.")
    code_search_p.add_argument("--limit", type=int, default=_core.CODE_SEARCH_DEFAULT_LIMIT)

    code_export_p = _code_comum(
        code_sub.add_parser(
            "export",
            help="Exporta o grafo no formato de extracao que a fonte publica.",
        )
    )
    code_export_p.add_argument(
        "--no-communities",
        dest="communities",
        action="store_false",
        default=True,
        help="Nao calcula comunidade. `algorithm` sai `null`, que diz 'nao calculei'.",
    )
    code_export_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=(
            "`summary` para as contagens e a declaracao de compatibilidade; "
            "`normal` e `full` trazem nos e arestas."
        ),
    )

    code_shape_p = _code_comum(
        code_sub.add_parser(
            "shape",
            help="Comunidades e nos de maior grau. Nao e julgamento, e forma.",
        )
    )
    code_shape_p.add_argument(
        "--top",
        type=int,
        default=_core.CODE_SHAPE_DEFAULT_TOP,
        help="Quantas comunidades e quantos nos por grau. Satura no teto.",
    )
    code_shape_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=(
            "`summary` para as contagens e o metodo; `normal` e `full` "
            "acrescentam os membros e a lista por grau."
        ),
    )

    code_path_p = _code_comum(
        code_sub.add_parser(
            "path",
            help="O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo.",
        )
    )
    code_path_p.add_argument("origem")
    code_path_p.add_argument("destino")
    code_path_p.add_argument(
        "--depth",
        type=int,
        default=_core.CODE_MAX_PATH_DEPTH,
        help="Teto de saltos. Satura no maximo; atingi-lo sai como `depth_exhausted`.",
    )
    code_path_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=(
            "`summary` para o veredito e as contagens do grafo; `normal` e `full` "
            "acrescentam os nos do caminho."
        ),
    )

    code_symbol_p = _code_comum(
        code_sub.add_parser(
            "symbol",
            help="Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo.",
        )
    )
    code_symbol_p.add_argument("node_id")
    code_symbol_p.add_argument("--depth", type=int, default=1)
    code_symbol_p.add_argument(
        "--detail-level",
        choices=_core.NIVEIS_DE_DETALHE,
        default="full",
        help=(
            "`summary` para no metadado; `normal` acrescenta vizinhanca direta; "
            "`full` acrescenta o raio de impacto e os testes nele."
        ),
    )

    code_read_p = _code_comum(
        code_sub.add_parser(
            "read",
            help=(
                "Le um trecho do repositorio, por --node-id OU por --file com faixa. "
                "Tetos duros: 250 linhas, 32 KiB, 4096 tokens."
            ),
        )
    )
    code_read_p.add_argument("--node-id")
    code_read_p.add_argument("--file", help="Caminho RELATIVO a --root.")
    code_read_p.add_argument("--start-line", type=int)
    code_read_p.add_argument("--end-line", type=int)
    code_read_p.add_argument("--context-lines", type=int, default=3)
    code_read_p.add_argument("--max-tokens", type=int, default=_core.CODE_READ_DEFAULT_TOKENS)

    code_context_p = _code_comum(
        code_sub.add_parser(
            "context",
            help="Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento.",
        )
    )
    code_context_p.add_argument("task")
    code_context_p.add_argument("--max-tokens", type=int)
    code_context_p.add_argument(
        "--include",
        action="append",
        choices=list(_core.CODE_CONTEXT_INCLUDE),
        help="Repetivel. Omitido, todas as secoes que este motor sabe preencher.",
    )

    _code_comum(
        code_sub.add_parser(
            "doctor",
            help=(
                "Diagnostico local do indice e da superficie. Sai 1 quando alguma "
                "checagem falha. Nao testa conectividade de internet."
            ),
        )
    )

    _code_comum(
        code_sub.add_parser(
            "purge",
            help=(
                "Apaga SOMENTE .sparkforge/local/codeintel/. Qualquer outro diretorio e recusado."
            ),
        )
    )

    # knowledge path --------------------------------------------------------
    # pack ----------------------------------------------------------------------
    # Forge Pack (§5): regras, knowledge e fixtures de terceiro, ativados por
    # SPARKFORGE_PACKS. `list` e o que a tool MCP expoe; `check` e do autor do pack.
    pack_p = sub.add_parser(
        "pack",
        help="Forge Packs: regras, knowledge e fixtures de terceiro (SPARKFORGE_PACKS).",
    )
    pack_sub = pack_p.add_subparsers(dest="pack_action", required=True)
    pack_sub.add_parser(
        "list", help="Packs ativos, recusados com o motivo, e o mapa prefixo -> pack."
    )
    pack_check_p = pack_sub.add_parser(
        "check",
        help=(
            "Roda cada fixture do pack pelo judge. Sai 1 quando uma regra do pack nao "
            "dispara no fixture que a declara, ou quando o pack e recusado."
        ),
    )
    pack_check_p.add_argument("dir", help="Diretorio do pack (com pack.yaml).")

    knowledge_p = sub.add_parser(
        "knowledge", help="Localiza os arquivos de conhecimento versionado."
    )
    knowledge_sub = knowledge_p.add_subparsers(dest="knowledge_action", required=True)
    knowledge_path_p = knowledge_sub.add_parser(
        "path", help="Imprime a raiz de knowledge e, com --file, um arquivo dentro dela."
    )
    knowledge_path_p.add_argument("--file")
    knowledge_path_p.add_argument(
        "--source-freshness",
        action="store_true",
        help=(
            "Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), "
            "calculado sobre knowledge/sources.lock.json. Depende do lock e do dia."
        ),
    )
    knowledge_path_p.add_argument(
        "--as-of", help="Dia de referencia do estado das fontes (AAAA-MM-DD)."
    )
    knowledge_drift_p = knowledge_sub.add_parser(
        "drift",
        help=(
            "Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), "
            "as regras e documentos que a leram antes da mudanca e os goldens, evals e "
            "agentes dessas regras. Sem rede."
        ),
    )
    knowledge_drift_p.add_argument("--source", help="So esta fonte do lock (a chave do lock).")
    knowledge_drift_p.add_argument(
        "--as-of", help="Dia de referencia do estado das fontes (AAAA-MM-DD)."
    )

    # rules lookup --------------------------------------------------------
    # debate referee ---------------------------------------------------
    #
    # O §27 do prompt de origem pede o protocolo de debate e fecha com "nenhum
    # agente pode declarar root cause final apenas com hipotese". Essa frase e
    # uma RECUSA, e recusa e verificacao -- que se constroi sem provider.
    #
    # O que NAO esta aqui e a GERACAO: argumento exige modelo, e `sparkforge/`
    # nao chama provider (regra 23). `arbitrate` emite `debate_plan` e para;
    # `referee` arbitra o que o host preencheu.
    #
    # `start`, `next` e `submit` sao o executor de debate: uma maquina de
    # estados sobre arquivos do case que diz de quem e a vez, recusa por nome a
    # submissao que fere o protocolo e fecha pelo `referee`. Continua sem gerar
    # uma palavra de argumento -- quem escreve a submissao e o host.
    ref_p = sub.add_parser(
        "debate",
        help=(
            "Conduz e arbitra o protocolo de debate do case. Nao gera argumento: "
            "quem escreve cada submissao e o host."
        ),
    )
    ref_sub = ref_p.add_subparsers(dest="debate_action", required=True)
    ref_r = ref_sub.add_parser(
        "referee",
        help=(
            "Diz se o fechamento declarado pode ser publicado: hipotese que "
            "sobrevive, claim sem evidencia, objecao sem replica, referencia "
            "pendurada."
        ),
    )
    ref_r.add_argument("--repo", required=True)

    deb_start = ref_sub.add_parser(
        "start",
        help=(
            "Congela o plano de debate do par --rules A,B em "
            "<repo>/.sparkforge/debate/<debate_id>/, a partir dos MESMOS insumos "
            "do `arbitrate`. Recusa `budget_undeclared` sem `budget:` no case.yaml."
        ),
    )
    deb_start.add_argument(
        "--rules",
        required=True,
        help="As duas regras em contradicao, `A,B`. O lado A defende a primeira.",
    )
    deb_start.add_argument(
        "--findings",
        required=True,
        help="Arquivo de findings (JSON) gerado por `judge --out` -- o mesmo do `arbitrate`.",
    )
    deb_start.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Arquivo de facts (JSON). Repetivel: o plano e recalculado sobre a UNIAO "
            "dos facts do case, o mesmo conjunto que `arbitrate` recebeu."
        ),
    )
    deb_start.add_argument("--repo", default=".", help="Raiz do case.")
    deb_start.add_argument("--glue")
    deb_start.add_argument("--emr", help=_EMR_FLAG_HELP)
    deb_start.add_argument("--spark")
    deb_start.add_argument("--python")
    deb_start.add_argument("--iceberg")
    deb_start.add_argument("--athena")

    deb_next = ref_sub.add_parser(
        "next",
        help=(
            "O brief do lado da vez, ou `done` com a Decision. Grava a Decision no "
            "fechamento; depois dele devolve sempre o mesmo `done`."
        ),
    )
    deb_next.add_argument("--repo", default=".", help="Raiz do case.")
    deb_next.add_argument("--debate", required=True, help="O `debate_id` que `start` devolveu.")

    deb_submit = ref_sub.add_parser(
        "submit",
        help=(
            "Valida e grava a submissao do lado da vez. Recusa por nome e deixa o "
            "estado igual."
        ),
    )
    deb_submit.add_argument("--repo", default=".", help="Raiz do case.")
    deb_submit.add_argument("--debate", required=True, help="O `debate_id` que `start` devolveu.")
    deb_submit.add_argument(
        "--file",
        required=True,
        help="A submissao (objeto JSON), no schema que o brief publica em `submission_schema`.",
    )

    # root-cause -------------------------------------------------------
    #
    # Verbo de TOPO, no mesmo genero de `workload`, `capacity` e `finops`:
    # compoe sobre facts e nao le artefato. Ele roda `judge` por dentro, e o que
    # publica de novo nao sao os achados -- e a LACUNA: as regras que ficaram
    # mudas por falta de artefato, com o kind que falta e o modulo que o emite.
    #
    # Ele NAO se chama `lakeformation diagnose`. A ordem dos quatro passos de
    # diagnostico de acesso mora na skill `diagnose-lakeformation-access`, que e
    # nao-despachavel porque coleta AWS ao vivo; este verbo nao coleta nada e
    # serve a qualquer area do catalogo.
    rc_p = sub.add_parser(
        "root-cause",
        help=(
            "Ordena os achados por consequencia declarada e nomeia a lacuna. "
            "Nao calcula confianca e nao estima ganho."
        ),
    )
    rc_p.add_argument(
        "--facts",
        action="append",
        dest="facts_paths",
        required=True,
        help=(
            "Arquivo de facts. REPETIVEL, e a repeticao e o contrato: uma regra "
            "pode exigir facts de mais de um extrator, e a lacuna publicada e "
            "sobre a UNIAO."
        ),
    )
    rc_p.add_argument("--glue")
    rc_p.add_argument("--spark")
    rc_p.add_argument("--python")
    rc_p.add_argument("--iceberg")
    rc_p.add_argument("--athena")
    rc_p.add_argument("--emr")
    rc_p.add_argument(
        "--all-missing",
        action="store_true",
        help=(
            "Lista as regras nao avaliadas de TODAS as areas, e nao so das que "
            "ja tem achado. O TOTAL sai nos dois casos -- medido: 129 num case de "
            "Terraform sozinho, contra 5 no recorte."
        ),
    )
    rc_p.add_argument(
        "--detail-level",
        choices=["summary", "normal", "full"],
        default="full",
        help=(
            "`summary` corta remediacao, validacao, rollback e os riscos da regra. "
            "Nunca corta `rule_id`, severidade, evidencia nem a lacuna."
        ),
    )

    # lakeformation ----------------------------------------------------
    #
    # UM subcomando, e nao os nove que o prompt de origem pede. `matrix` esta
    # aqui porque acrescenta CAPACIDADE: o eixo de versao existia so como tabela
    # markdown, e nenhum verbo o lia. Os outros oito seriam alias sobre verbo que
    # ja existe -- `permissions` e `analyze lakeformation-grants`,
    # `explain-error` e `troubleshoot` sao `analyze error-signatures`,
    # `cross-account` mora em `forge lakeformation diagnose-cross-account`,
    # `migration` e `migrate assess`. Alias move a superficie (regra 26) sem
    # mover capacidade, e a razao de cada recusa esta em
    # `docs/superpowers/STATUS.md`.
    #
    # `diagnose` e o unico dos oito que NAO seria alias, e ele nao esta aqui de
    # proposito: a ordem dos quatro passos e procedimento e mora na skill
    # `diagnose-lakeformation-access`, que e nao-despachavel porque coleta AWS ao
    # vivo. Um verbo com esse nome sem essa ordem prometeria o que nao faz.
    lf_matrix_p = sub.add_parser(
        "lakeformation",
        help=(
            "Eixo de VERSAO de Lake Formation por runtime Glue -- capacidade, "
            "nao versao de componente."
        ),
    )
    lf_matrix_sub = lf_matrix_p.add_subparsers(dest="lakeformation_action", required=True)
    lf_g = lf_matrix_sub.add_parser(
        "access-graph",
        help=(
            "O caminho de acesso como GRAFO, a partir de facts. `is_accessible` e "
            "TERNARIO -- `null` e 'o que olhei nao impede', nao 'funciona'."
        ),
    )
    lf_g.add_argument("--facts", action="append", dest="facts_paths", required=True)
    lf_g.add_argument("--principal-arn", default="")
    lf_g.add_argument("--target-table", default="")

    lf_mx = lf_matrix_sub.add_parser(
        "matrix",
        help=(
            "Imprime o eixo: filesystem S3 default, FGAC por caminho, DDL/DML e "
            "FTA, com a frase da fonte quando ela existe."
        ),
    )
    lf_mx.add_argument(
        "--runtime",
        help=(
            "Versao de Glue. Sem ela, todas as que a matriz cobre. Versao fora "
            "da matriz sai `unresolved` com o que destravaria -- nunca palpite "
            "por analogia com a versao vizinha."
        ),
    )
    lf_mx.add_argument(
        "--axis",
        help="Eixo especifico (ex.: `fgac_spark_native_write`). Sem ele, todos.",
    )
    lf_mx.add_argument(
        "--detail-level",
        choices=["summary", "normal", "full"],
        default="full",
        help="`summary` omite fonte, frase e nota. Ver a regra 28 do CLAUDE.md.",
    )

    rules_p = sub.add_parser("rules", help="Consulta o catalogo de regras versionado.")
    rules_sub = rules_p.add_subparsers(dest="rules_action", required=True)
    lookup_p = rules_sub.add_parser(
        "lookup", help="Busca regras por id ou categoria (thresholds, fontes, severidade)."
    )
    lookup_p.add_argument("--id", action="append")
    lookup_p.add_argument("--category")
    lookup_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    lookup_p.add_argument("--cursor")
    lookup_p.add_argument(
        "--source-freshness",
        action="store_true",
        help=(
            "Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), "
            "calculado sobre knowledge/sources.lock.json. Depende do lock e do dia."
        ),
    )
    lookup_p.add_argument(
        "--as-of", help="Dia de referencia do estado das fontes (AAAA-MM-DD)."
    )

    # validate --------------------------------------------------------
    validate_p = sub.add_parser(
        "validate",
        help="Valida findings contra o JSON Schema e a regra de ganho sem benchmark_ref.",
    )
    validate_p.add_argument("--findings", required=True)
    validate_p.add_argument(
        "--facts",
        help=(
            "Opcional. Arquivo de facts (tipicamente `sparkforge benchmark --out`). "
            "Sem ele, `benchmark_ref` so e cobrado na FORMA (`f_` + 6 hex); com ele, "
            "o `fact_id` citado precisa existir no conjunto -- achado que cita "
            "medicao ausente da evidencia passa a ser rejeitado."
        ),
    )

    # report sign / verify ----------------------------------------------
    report_p = sub.add_parser(
        "report",
        help=(
            "Assinatura de CORRESPONDENCIA do relatorio: prova que o texto foi "
            "derivado daquela evidencia com aquele catalogo. Nunca autoria."
        ),
    )
    report_sub = report_p.add_subparsers(dest="report_action", required=True)

    report_sign_p = report_sub.add_parser(
        "sign",
        help=(
            "Escreve o bloco de assinatura no fim do relatorio. Reassinar e "
            "barato e devolve o mesmo arquivo quando nada mudou."
        ),
    )
    report_sign_p.add_argument(
        "--report", required=True, help="Markdown do relatorio. E reescrito no lugar."
    )
    report_sign_p.add_argument(
        "--findings",
        required=True,
        help=(
            "Arquivo de findings (JSON) gerado por `judge --out`. E dele que saem "
            "os quatro campos nao-corpo da assinatura: `evidence` (os fact_id "
            "citados), `rule_id`, `catalog_version` e `schema_version`. O arquivo "
            "de FACTS nao tem os tres ultimos -- por isso o verbo pede findings, "
            "e nao facts."
        ),
    )

    report_verify_p = report_sub.add_parser(
        "verify",
        help=(
            "Confere a assinatura e diz QUAL parte divergiu: evidencia, catalogo "
            "ou corpo. Sai com codigo 1 quando nao corresponde."
        ),
    )
    report_verify_p.add_argument("--report", required=True)
    report_verify_p.add_argument(
        "--findings",
        required=True,
        help="O mesmo arquivo de findings contra o qual o relatorio foi assinado.",
    )

    report_github_p = report_sub.add_parser(
        "github",
        help=(
            "Projeta findings ja julgados para o GitHub: SARIF para o Code Scanning e "
            "resumo Markdown para o PR, em .sparkforge/report/ (nomes fixos), e uma "
            "anotacao ::error/::warning/::notice por finding com linha no stdout. "
            "Finding sem linha no repositorio sai no resumo com o motivo. Nao chama rede."
        ),
    )
    report_github_p.add_argument(
        "--findings", required=True, help="Saida de `judge --out` (findings.json)."
    )
    report_github_p.add_argument(
        "--facts",
        required=True,
        action="append",
        help=(
            "Facts da UNIAO do case (repetivel): o fact de evidencia de codigo empresta "
            "a linha a um finding que nao tem a propria."
        ),
    )
    report_github_p.add_argument(
        "--repo",
        default=".",
        help="Raiz do repositorio git. A saida vai para <repo>/.sparkforge/report/.",
    )
    report_github_p.add_argument(
        "--source-root",
        action="append",
        dest="source_roots",
        help=(
            "Diretorio (relativo a --repo) que foi passado a um `analyze --path`, "
            "repetivel, na mesma ordem. O caminho dos findings e relativo a ele."
        ),
    )
    report_github_p.add_argument(
        "--fail-on",
        choices=["P0", "P1"],
        default=None,
        help="Sai com codigo 1 quando ha finding desta severidade ou pior.",
    )
    report_github_p.add_argument(
        "--category",
        default=None,
        help="Categoria do upload no Code Scanning (automationDetails.id).",
    )
    report_github_p.add_argument(
        "--source-freshness",
        action="store_true",
        help=(
            "Secao Fontes que pedem releitura no resumo, com o estado das fontes citadas "
            "(fixed, unverified, stale, aging, fresh), calculado sobre "
            "knowledge/sources.lock.json. Depende do lock e do dia."
        ),
    )
    report_github_p.add_argument(
        "--as-of", help="Dia de referencia do estado das fontes (AAAA-MM-DD)."
    )

    # telemetry ---------------------------------------------------------------
    # Verbo de TOPO pela mesma razao de `economy report`: compoe sobre o ledger.
    telemetry_p = sub.add_parser(
        "telemetry",
        help="Os spans de tool e o transcript do host em OTLP/JSON, para um OTLP Collector.",
    )
    telemetry_sub = telemetry_p.add_subparsers(dest="subcommand", required=True)
    telemetry_export_p = telemetry_sub.add_parser(
        "export",
        help=(
            "Grava .sparkforge/telemetry/<run_id>.traces.jsonl e .metrics.jsonl (nomes "
            "fixos), com gen_ai.* e mcp.* da semconv GenAI (Development). O Collector le "
            "com o receiver otlp_json_file. Nao chama rede; token so com transcript do host."
        ),
    )
    telemetry_export_p.add_argument("--run-id", required=True)
    telemetry_export_p.add_argument(
        "--host-transcript",
        default="",
        help="Transcript JSONL do host, quando houver: vira o span invoke_agent com tokens.",
    )
    telemetry_export_p.add_argument(
        "--provider",
        default=None,
        help=(
            "Provider do host (gen_ai.provider.name), DECLARADO: anthropic, aws.bedrock, "
            "gcp.vertex_ai. Sem ele o atributo fica em unresolved e a metrica de token nao sai."
        ),
    )
    telemetry_export_p.add_argument(
        "--repo",
        default=".",
        help="Raiz do repositorio. A saida vai para <repo>/.sparkforge/telemetry/.",
    )

    # receipt -------------------------------------------------------------------
    # Verbo de TOPO: compoe sobre artefatos que outros verbos gravaram e sobre o
    # ledger, e nao le artefato de job.
    receipt_p = sub.add_parser(
        "receipt",
        help=(
            "Recibo content-addressed da execucao do case: prova CORRESPONDENCIA entre "
            "o recibo e os artefatos, nunca autoria."
        ),
    )
    receipt_sub = receipt_p.add_subparsers(dest="subcommand", required=True)
    receipt_emit_p = receipt_sub.add_parser(
        "emit",
        help=(
            "Grava .sparkforge/receipts/<receipt_id>.json com caminho e sha256 do case, "
            "dos facts, dos findings, do report, do blackboard, dos ADRs e dos debates, os "
            "spans do run declarado e o host declarado. Sem conteudo de caso."
        ),
    )
    receipt_emit_p.add_argument(
        "--facts",
        action="append",
        required=True,
        help="Arquivo de facts. Repetivel, e a repeticao e o contrato: a UNIAO do case.",
    )
    receipt_emit_p.add_argument(
        "--findings", required=True, help="Findings (JSON) gerados por `judge --out`."
    )
    receipt_emit_p.add_argument(
        "--now", required=True, help="Instante ISO 8601 da emissao. Entra no hash."
    )
    receipt_emit_p.add_argument("--report", default=None, help="Relatorio assinado, se houver.")
    receipt_emit_p.add_argument(
        "--run-id",
        default=None,
        help="Run cujos spans de tool entram. Sem ele, a parte tools sai em unresolved.",
    )
    receipt_emit_p.add_argument(
        "--host-transcript",
        default="",
        help="Transcript JSONL do host. So o sha256 entra; modelo e agente saem dele.",
    )
    receipt_emit_p.add_argument(
        "--provider", default=None, help="Provider do host, DECLARADO (anthropic)."
    )
    receipt_emit_p.add_argument(
        "--repo", default=".", help="Raiz do case. Caminhos relativos resolvem contra ela."
    )
    receipt_verify_p = receipt_sub.add_parser(
        "verify",
        help=(
            "Recalcula cada parte contra o disco e diz qual divergiu. Sai com codigo 1 "
            "quando o recibo nao corresponde."
        ),
    )
    receipt_verify_p.add_argument("--receipt", required=True)
    receipt_verify_p.add_argument(
        "--host-transcript",
        default="",
        help="O mesmo transcript da emissao; sem ele a parte host sai not_rechecked.",
    )
    receipt_verify_p.add_argument("--repo", default=".")

    # proof -------------------------------------------------------------------
    # Verbo de TOPO: compoe sobre findings e facts ja extraidos, e julga no
    # processo; nao le artefato de job.
    proof_p = sub.add_parser(
        "proof",
        help=(
            "Obrigacoes de prova de cada recomendacao APLICADA: resolucao (a regra "
            "deixou de disparar no depois?) e um eixo por item de action.moves "
            "(funcval, benchmark ou sem comparador). Desfechos: refuted, not_refuted, "
            "inconclusive, unproven -- nunca provado."
        ),
    )
    proof_p.add_argument("--findings", required=True, help="Findings do antes (`judge --out`).")
    proof_p.add_argument(
        "--facts",
        action="append",
        required=True,
        help="Uniao de facts do case, com os de funcval e benchmark. Repetivel.",
    )
    proof_p.add_argument(
        "--after-facts",
        action="append",
        required=True,
        help="Facts extraidos dos artefatos do depois. Repetivel.",
    )
    proof_p.add_argument(
        "--applied",
        action="append",
        required=True,
        help="RULE_ID ou RULE_ID:simbolo de cada recomendacao aplicada. Repetivel.",
    )
    for flag in ("--glue", "--spark", "--python", "--iceberg", "--athena", "--emr"):
        proof_p.add_argument(flag, default=None)

    # simulate ----------------------------------------------------------------
    # Verbo de TOPO: altera facts de configuracao ja extraidos e julga os dois
    # lados no processo; nao le artefato de job.
    simulate_p = sub.add_parser(
        "simulate",
        help=(
            "O que uma mudanca de configuracao move, estruturalmente: altera o valor "
            "de facts que ja existem, rederiva e julga os dois lados, e diz que "
            "achados somem e aparecem. Nunca preve spill, tempo ou custo."
        ),
    )
    simulate_p.add_argument(
        "--facts", action="append", required=True, help="Facts do case. Repetivel."
    )
    simulate_p.add_argument(
        "--set",
        dest="sets",
        action="append",
        required=True,
        help="camada:chave=valor, camada em tf, code, effective, emr. Repetivel.",
    )
    for flag in ("--glue", "--spark", "--python", "--iceberg", "--athena", "--emr"):
        simulate_p.add_argument(flag, default=None)

    # gain --------------------------------------------------------------------
    # Verbo de TOPO: compara runs ja medidos; nao le artefato de job.
    gain_p = sub.add_parser(
        "gain",
        help=(
            "Ganho OBSERVADO entre runs medidos antes e depois de uma mudanca: por lado, "
            "N, mediana, minimo e maximo de tempo, DPU-segundos e custo, e o delta das "
            "medianas. Nunca projeta economia nem atribui causa."
        ),
    )
    gain_p.add_argument(
        "--baseline", action="append", required=True, help="Facts de runs do antes. Repetivel."
    )
    gain_p.add_argument(
        "--candidate", action="append", required=True, help="Facts de runs do depois. Repetivel."
    )

    # scan --------------------------------------------------------------------
    # Verbo de TOPO que encadeia: plano por manifesto e extensao, um analyze por
    # arquivo, fuse e judge sobre a uniao. Nao coleta: so o que esta no disco.
    scan_p = sub.add_parser(
        "scan",
        help=(
            "Roda sozinho os analyzes que cabem num repositorio: artefato coletado pelo "
            "manifesto, codigo pela extensao; depois fuse, judge e um resumo em "
            ".sparkforge/scan/. Sem rede."
        ),
    )
    scan_p.add_argument("raiz", nargs="?", default=".", help="Pasta a varrer (padrao: .).")
    scan_p.add_argument(
        "--dry-run", action="store_true", help="So mostra o plano; nao roda nem grava nada."
    )
    scan_p.add_argument(
        "--format", choices=["json", "sarif"], default="json",
        help="sarif grava tambem o SARIF e o resumo de PR, como `report github`.",
    )
    scan_p.add_argument(
        "--fail-on", choices=["P0", "P1"], default=None,
        help="Sai 1 se houver finding nesta severidade (P1 inclui P0).",
    )
    for flag in ("--glue", "--spark", "--python", "--iceberg", "--athena", "--emr"):
        scan_p.add_argument(flag, default=None)

    # doctor ------------------------------------------------------------------
    doctor_p = sub.add_parser(
        "doctor",
        help=(
            "Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, "
            "knowledge, indice de codigo, artefatos e credencial AWS. Sai 1 com alguma falha."
        ),
    )
    doctor_p.add_argument("--repo", default=".", help="Raiz do repositorio (padrao: .).")
    doctor_p.add_argument(
        "--online", action="store_true",
        help="Confirma a credencial na AWS (STS get_caller_identity). Unico modo com rede.",
    )

    # policy ------------------------------------------------------------------
    # §16: `.sparkforge/policy.yaml`, imposta pelo servidor MCP, pelo hook
    # PreToolUse (deny) e por `permissions.ask` gerado (ask).
    policy_p = sub.add_parser(
        "policy",
        help=(
            "Politica de seguranca do repositorio (.sparkforge/policy.yaml): validar, "
            "explicar uma decisao e gerar as regras ask do .claude/settings.json."
        ),
    )
    policy_sub = policy_p.add_subparsers(dest="policy_action", required=True)
    policy_check_p = policy_sub.add_parser(
        "check", help="Valida a policy e lista as regras; sai 2 se ela for invalida."
    )
    policy_check_p.add_argument("--repo", default=".", help="Raiz do repositorio (padrao: .).")
    policy_explain_p = policy_sub.add_parser(
        "explain",
        help="Diz a decisao (allow, ask, deny), a regra que casou e qual porta a impoe.",
    )
    policy_explain_p.add_argument("--repo", default=".", help="Raiz do repositorio (padrao: .).")
    policy_explain_p.add_argument("--bash", default=None, help="Comando de shell a conferir.")
    policy_explain_p.add_argument("--path", default=None, help="Caminho de escrita a conferir.")
    policy_explain_p.add_argument("--tool", default=None, help="Nome de tool MCP a conferir.")
    policy_sync_p = policy_sub.add_parser(
        "sync-settings",
        help=(
            "Gera permissions.ask no .claude/settings.json a partir das regras ask; "
            "--check so confere e sai 1 se divergir."
        ),
    )
    policy_sync_p.add_argument("--repo", default=".", help="Raiz do repositorio (padrao: .).")
    policy_sync_p.add_argument(
        "--check", action="store_true", help="So confere; nao grava. Sai 1 se divergir."
    )

    # collect -----------------------------------------------------------
    collect_p = sub.add_parser(
        "collect",
        help="Coleta artefatos AWS reais (event log, job Glue, CloudWatch, metadata Iceberg).",
    )
    collect_sub = collect_p.add_subparsers(dest="collect_action", required=True)

    event_log_p = collect_sub.add_parser(
        "event-log", help="Baixa o Spark event log de um job run via S3."
    )
    event_log_p.add_argument("--repo", required=True)
    event_log_p.add_argument("--job-run", required=True)
    event_log_p.add_argument("--bucket", required=True)
    event_log_p.add_argument("--prefix", required=True)
    event_log_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    glue_job_p = collect_sub.add_parser(
        "glue-job", help="Baixa a definicao de um job via a API do Glue."
    )
    glue_job_p.add_argument("--repo", required=True)
    glue_job_p.add_argument("--job-name", required=True)
    glue_job_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    cloudwatch_p = collect_sub.add_parser(
        "cloudwatch", help="Baixa metricas de observabilidade Glue via CloudWatch."
    )
    cloudwatch_p.add_argument("--repo", required=True)
    cloudwatch_p.add_argument("--job-name", required=True)
    cloudwatch_p.add_argument("--job-run", required=True)
    cloudwatch_p.add_argument("--start", required=True, help="Inicio ISO 8601.")
    cloudwatch_p.add_argument("--end", required=True, help="Fim ISO 8601.")
    cloudwatch_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    iam_p = collect_sub.add_parser(
        "iam-access",
        help="Simula acoes contra um role via SimulatePrincipalPolicy e grava a decisao.",
    )
    iam_p.add_argument("--repo", required=True)
    iam_p.add_argument(
        "--role-arn", required=True,
        help="ARN do role a simular -- tipicamente o runtime role do job.",
    )
    iam_p.add_argument(
        "--action", action="append", dest="actions",
        help=(
            "Acao a simular. Repetivel. Sem ela, a lista default de Lake Formation e "
            "Glue -- e passar a lista inteira quando a pergunta e sobre UMA escrita "
            "produz decisoes que nao dizem nada sobre o caso."
        ),
    )
    iam_p.add_argument(
        "--resource-arn", action="append", dest="resource_arns",
        help="Recurso contra o qual simular. Repetivel. Sem ele a resposta e sobre `*`.",
    )
    iam_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    rlink_p = collect_sub.add_parser(
        "glue-resource-link",
        help="Le o resource link na conta consumidora e o recurso de origem que ele declara.",
    )
    rlink_p.add_argument("--repo", required=True)
    rlink_p.add_argument("--database", required=True, help="Banco do link na conta consumidora.")
    rlink_p.add_argument(
        "--table",
        default="",
        help=(
            "Nome do link de TABELA. Sem ele o alvo e um BANCO -- e a comparacao de nome "
            "muda, porque `TargetDatabase` nao tem campo `Name`."
        ),
    )
    rlink_p.add_argument(
        "--catalog-id",
        default="",
        help=(
            "Id da conta CONSUMIDORA, onde o link mora. O catalogo de origem sai medido "
            "do proprio link e nunca e passado a mao."
        ),
    )
    rlink_p.add_argument(
        "--no-verify-target",
        action="store_true",
        help=(
            "Pula a leitura do recurso de ORIGEM. O default e conferir: link que aponta "
            "para lugar nenhum e o defeito que este coletor existe para achar."
        ),
    )
    rlink_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    lf_p = collect_sub.add_parser(
        "lakeformation",
        help="Coleta grant, registro de localizacao S3 e data lake settings de UMA tabela.",
    )
    lf_p.add_argument("--repo", required=True)
    lf_p.add_argument("--database", required=True, help="Banco da tabela no catalogo.")
    lf_p.add_argument("--table", required=True, help="Nome da tabela.")
    lf_p.add_argument(
        "--catalog-id",
        default="",
        help=(
            "Id da conta dona do catalogo. Obrigatorio em cross-account: a MESMA "
            "`db.tabela` existe em contas diferentes, e sem ele as duas coletas se "
            "sobrescrevem no manifesto."
        ),
    )
    lf_p.add_argument(
        "--resource-arn",
        default="",
        help=(
            "Localizacao S3 a conferir em `describe_resource`. Sem ela o bloco sai "
            "`nao_coletado` em vez de sumir -- bloco ausente e indistinguivel de vazio."
        ),
    )
    lf_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    cw_logs_p = collect_sub.add_parser(
        "cloudwatch-logs",
        help="Baixa o LOG do run no CloudWatch Logs (o caminho das assinaturas de mensagem).",
    )
    cw_logs_p.add_argument("--repo", required=True)
    cw_logs_p.add_argument("--job-name", required=True)
    cw_logs_p.add_argument("--job-run", required=True)
    cw_logs_p.add_argument(
        "--log-group",
        required=True,
        help=(
            "Log group. Sem default -- `/aws-glue/jobs/error`, `/aws-glue/jobs/output` e "
            "`/aws-glue/jobs/logs-v2` tem conteudo diferente."
        ),
    )
    cw_logs_p.add_argument("--start", required=True, help="Inicio ISO 8601.")
    cw_logs_p.add_argument("--end", required=True, help="Fim ISO 8601.")
    cw_logs_p.add_argument(
        "--filter-pattern",
        default="",
        help="Filtro do CloudWatch Logs, aplicado no servidor. Declara a relevancia.",
    )
    cw_logs_p.add_argument(
        "--max-events",
        type=int,
        default=500,
        help="Teto de eventos. Quando morde, o artefato sai com truncated: true.",
    )
    cw_logs_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    job_runs_p = collect_sub.add_parser(
        "glue-job-runs",
        help="Baixa o historico de execucoes de um job, um artefato por run terminal.",
    )
    job_runs_p.add_argument("--repo", required=True)
    job_runs_p.add_argument("--job-name", required=True)
    job_runs_p.add_argument(
        "--max-runs",
        type=int,
        default=30,
        help="Teto de paginacao. A API devolve do mais recente para tras.",
    )
    job_runs_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    iceberg_p = collect_sub.add_parser(
        "iceberg-metadata", help="Consulta metadata tables Iceberg de uma tabela via Athena."
    )
    iceberg_p.add_argument("--repo", required=True)
    iceberg_p.add_argument("--table", required=True, help="db.tabela")
    iceberg_p.add_argument("--workgroup", required=True)
    iceberg_p.add_argument("--output-location", required=True)
    iceberg_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    athena_wg_collect_p = collect_sub.add_parser(
        "athena-workgroup", help="Baixa a configuracao de um workgroup via a API do Athena."
    )
    athena_wg_collect_p.add_argument("--repo", required=True)
    athena_wg_collect_p.add_argument("--workgroup", required=True)
    athena_wg_collect_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    emr_collect_p = collect_sub.add_parser(
        "emr-cluster",
        help="Baixa describe-cluster, grupos/fleets, bootstrap actions e as politicas de "
        "scaling de um cluster EMR on EC2.",
    )
    emr_collect_p.add_argument("--repo", required=True)
    emr_collect_p.add_argument("--cluster-id", required=True, help="j-XXXXXXXXXXXXX")
    emr_collect_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    emrs_collect_p = collect_sub.add_parser(
        "emr-serverless",
        help="Baixa get-application de uma application EMR Serverless. Uma chamada, "
        "nao seis: capacidade, auto-stop, runtimeConfiguration e monitoramento chegam "
        "no mesmo objeto.",
    )
    emrs_collect_p.add_argument("--repo", required=True)
    emrs_collect_p.add_argument(
        "--application-id",
        required=True,
        help="Id da application (`00fXXXXXXXXXXXXX`). Nome NAO serve: e opcional na API "
        "e nao ha fonte que o declare unico.",
    )
    emrs_collect_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    emrc_collect_p = collect_sub.add_parser(
        "emr-eks",
        help="Baixa describe-virtual-cluster e describe-job-run de uma execucao Amazon "
        "EMR on EKS e grava as duas respostas num arquivo so. Duas chamadas, nao uma: "
        "no `emr-containers` cluster virtual e execucao sao APIs separadas.",
    )
    emrc_collect_p.add_argument("--repo", required=True)
    emrc_collect_p.add_argument(
        "--virtual-cluster-id",
        required=True,
        help="Id do cluster virtual. Nome NAO serve: `DescribeJobRun` exige o id.",
    )
    emrc_collect_p.add_argument(
        "--job-run-id",
        required=True,
        help="Id da execucao. Os DOIS ids sao obrigatorios porque `DescribeJobRun` "
        "exige `virtualClusterId` junto do `id`.",
    )
    emrc_collect_p.add_argument("--now", required=True, help="Timestamp ISO 8601.")

    verify_p = collect_sub.add_parser(
        "verify", help="Verifica presenca e integridade de todos os artefatos do manifesto."
    )
    verify_p.add_argument("--repo", required=True)

    return parser


# --------------------------------------------------------------------------- #
# handlers
# --------------------------------------------------------------------------- #


def _cmd_analyze_pyspark(args: argparse.Namespace) -> int:
    full = _core.analyze_pyspark(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_catalog_schema(args: argparse.Namespace) -> int:
    full = _core.analyze_catalog_schema(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_event_log(args: argparse.Namespace) -> int:
    full = _core.analyze_event_log(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_sql_metrics(args: argparse.Namespace) -> int:
    full = _core.analyze_sql_metrics(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_parquet_footer(args: argparse.Namespace) -> int:
    full = _core.analyze_parquet_footer(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_cloudwatch_logs(args: argparse.Namespace) -> int:
    full = _core.analyze_cloudwatch_logs(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_glue_resource_link(args: argparse.Namespace) -> int:
    full = _core.analyze_glue_resource_link(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_iam_access(args: argparse.Namespace) -> int:
    full = _core.analyze_iam_access(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_lakeformation_grants(args: argparse.Namespace) -> int:
    full = _core.analyze_lakeformation_grants(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_error_signatures(args: argparse.Namespace) -> int:
    full = _core.analyze_error_signatures(args.facts, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _emit_facts_page(full: dict, args: argparse.Namespace) -> int:
    """A paginacao e o `--out` dos dois verbos novos, numa funcao so.

    Os verbos antigos repetem este bloco cada um, e nao foram tocados: reescreve-
    los seria mudanca sem medida num caminho que ninguem pediu. Os dois novos
    nascem sem a repeticao.
    """
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_cloudwatch(args: argparse.Namespace) -> int:
    full = _core.analyze_cloudwatch(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_glue_job_runs(args: argparse.Namespace) -> int:
    full = _core.analyze_glue_job_runs(
        args.path,
        job_name=args.job_name,
        cloudwatch=args.cloudwatch,
        kind=args.kind,
        limit=None,
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_plan(args: argparse.Namespace) -> int:
    full = _core.analyze_plan(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_terraform(args: argparse.Namespace) -> int:
    full = _core.analyze_terraform(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_iceberg(args: argparse.Namespace) -> int:
    full = _core.analyze_iceberg(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_sql(args: argparse.Namespace) -> int:
    full = _core.analyze_sql(args.path, from_pyspark=args.from_pyspark, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_s3_listing(args: argparse.Namespace) -> int:
    full = _core.analyze_s3_listing(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_consumers(args: argparse.Namespace) -> int:
    full = _core.analyze_consumers(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_terraform_diff(args: argparse.Namespace) -> int:
    full = _core.analyze_terraform_diff(args.before, args.after, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _migrate(args: argparse.Namespace, platform: str) -> int:
    """O corpo comum dos dois verbos de `migrate`. Um motor, nao dois."""
    payload = _core.migration_assess(
        args.path, source=args.from_runtime, target=args.to_runtime, platform=platform
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_migrate_glue(args: argparse.Namespace) -> int:
    return _migrate(args, _core.MIGRATION_DEFAULT_PLATFORM)


def _cmd_migrate_controlm(args: argparse.Namespace) -> int:
    """Reusa `_migrate`, que ja trata `--out` e a saida, como os outros dois.

    Duplicar a escrita aqui criaria uma segunda forma de gravar o mesmo
    assessment, e as duas divergiriam no primeiro ajuste.
    """
    return _migrate(args, _core.MIGRATION_CONTROLM_PLATFORM)


def _cmd_migrate_emr(args: argparse.Namespace) -> int:
    return _migrate(args, args.platform)


def _cmd_glue_dependency_audit(args: argparse.Namespace) -> int:
    _print(_core.glue_dependency_audit(args.path, glue=args.glue_version))
    return 0


def _cmd_iceberg_assess_upgrade(args: argparse.Namespace) -> int:
    _print(_core.iceberg_assess_upgrade(args.path, source=args.from_spec, target=args.to_spec))
    return 0


def _cmd_controlm_describe(args: argparse.Namespace) -> int:
    _print(_core.controlm_describe(args.version, detail_level=args.detail_level))
    return 0


def _cmd_release_describe(args: argparse.Namespace) -> int:
    _print(_core.release_describe(args.platform, args.release))
    return 0


def _cmd_release_diff(args: argparse.Namespace) -> int:
    _print(
        _core.release_diff(
            args.left_platform,
            args.left_release,
            args.right_platform,
            args.right_release,
        )
    )
    return 0


def _cmd_analyze_athena_workgroup(args: argparse.Namespace) -> int:
    full = _core.analyze_athena_workgroup(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_emr_cluster(args: argparse.Namespace) -> int:
    full = _core.analyze_emr_cluster(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_emr_eks(args: argparse.Namespace) -> int:
    full = _core.analyze_emr_eks(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_controlm_jobs(args: argparse.Namespace) -> int:
    full = _core.analyze_controlm_jobs(args.path, version=args.version, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        # `version` entra em `filters_applied` junto de kind/limit/cursor porque
        # ela MUDA a saida, e quem le o JSON meses depois precisa saber qual
        # declaracao produziu aquele conjunto de facts. Sem ela ali, dois
        # relatorios do mesmo artefato com vereditos opostos seriam
        # indistinguiveis.
        "filters_applied": {
            "kind": args.kind,
            "limit": args.limit,
            "cursor": args.cursor,
            "version": args.version,
        },
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_emr_serverless(args: argparse.Namespace) -> int:
    full = _core.analyze_emr_serverless(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_data_quality(args: argparse.Namespace) -> int:
    full = _core.analyze_data_quality(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_graph(args: argparse.Namespace) -> int:
    full = _core.analyze_graph(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_analyze_call_graph(args: argparse.Namespace) -> int:
    full = _core.analyze_call_graph(args.facts, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    full = _core.benchmark_runs(
        args.before,
        args.after,
        kind=args.kind,
        limit=None,
        before_runtime=args.before_runtime,
        after_runtime=args.after_runtime,
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_workload(args: argparse.Namespace) -> int:
    payload = _core.workload_fingerprint(
        args.facts,
        job_name=args.job_name,
        job_run_id=args.job_run,
        history_path=args.history or "",
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_capacity(args: argparse.Namespace) -> int:
    payload = _core.capacity_plan(
        args.facts,
        job_name=args.job_name,
        job_run_id=args.job_run,
        history_path=args.history or "",
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_finops(args: argparse.Namespace) -> int:
    payload = _core.finops_report(args.facts, job_name=args.job_name)
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_tune(args: argparse.Namespace) -> int:
    payload = _core.tune_conf(args.facts)
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_economy_report(args: argparse.Namespace) -> int:
    payload = _core.economy_report(args.run_id, host_transcript=args.host_transcript)
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_funcval_plan(args: argparse.Namespace) -> int:
    """Sem escrita aqui: `_core.funcval_plan` grava o `--out`.

    Os verbos de `analyze` escrevem na CLI porque o `--out` deles e opcional e
    so a CLI o conhece. Aqui o arquivo e o artefato que o proximo verbo consome,
    e ele tem que sair identico pela CLI e pelo MCP -- gravar nos dois lugares
    seria a mesma escrita mantida a mao em duas copias.
    """
    full = _core.funcval_plan(args.facts, args.out, keys=args.key, kind=args.kind, limit=None)
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_funcval_compare(args: argparse.Namespace) -> int:
    """Sem escrita aqui, pela mesma razao de `_cmd_funcval_plan`: `_core` grava.

    Os verbos de `analyze` e o `fuse` escrevem na CLI porque o `--out` deles so
    existe na CLI. Este existe nas DUAS superficies (D-4c-26), e escrever nos
    dois lugares seria a mesma escrita mantida a mao em duas copias.
    """
    full = _core.funcval_compare(
        args.plan, args.before, args.after, out_path=args.out, kind=args.kind, limit=None
    )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_fuse(args: argparse.Namespace) -> int:
    full = _core.fuse_facts(args.facts, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "summary": full["summary"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_judge(args: argparse.Namespace) -> int:
    full = _core.judge_findings(
        facts_path=args.facts,
        glue=args.glue,
        emr=args.emr,
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
        severity=args.severity,
        limit=None,
        show_skipped=args.show_skipped,
    )
    if args.out:
        # O arquivo grava o item COMPLETO, e desde a T4 isso inclui
        # `evidence_standing`. Ele e REGISTRO do que o `judge` viu naquele
        # momento, nunca ENTRADA de quem le o arquivo depois: `arbitrate`
        # RECOMPUTA o lastro por `claims.standing_for_finding`, a partir de
        # `sources`, `runtime_scope` e dos `fact_id` que o achado declara em
        # `evidence` -- ele nao le esta chave em lugar nenhum. Editar o campo no
        # arquivo a mao nao move decisao nenhuma rio abaixo, e por isso o campo
        # extra e inocuo para `arbitrate` e para `report sign`.
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"severity": args.severity, "limit": args.limit, "cursor": args.cursor},
        "by_severity": full["by_severity"],
        # O runtime que filtrou por versao, sempre. Ele agora pode vir dos
        # facts e nao so das flags: sem ele na saida, "por que SF-GLUE-001 nao
        # apareceu?" nao tem resposta -- e uma divergencia entre flag e fact
        # seria resolvida em silencio para quem le a CLI.
        "runtime": full["runtime"],
        # O bloco sai tambem pela CLI, e nao so pelo MCP. `TestCliMcpEquivalence`
        # fixa a garantia da Fase 1 -- mesmo input, payload identico, "nunca um
        # subconjunto de campos" --, e `parity.yaml` declara `judge` para
        # `codex` e `copilot_ci` como `[cli, files]`, sem `mcp`: plano so no MCP
        # seria capacidade que duas das cinco plataformas nao alcancam por
        # caminho nenhum.
        #
        # Ele NAO e recortado pela paginacao, de proposito: a ordem e do CASO,
        # e `full` foi julgado com `limit=None`. Ordem parcial apresentada como
        # ordem e a familia de afirmacao que este projeto recusa -- por isso
        # `plan.scope` carrega a contagem do conjunto, e nao a da pagina.
        "plan": full["plan"],
        "items": page,
    }
    if args.show_skipped:
        payload["skipped"] = full.get("skipped", [])
    if args.source_freshness:
        payload.update(_core.source_freshness_de(page, args.as_of))
    _print(payload)
    return 0


def _cmd_arbitrate(args: argparse.Namespace) -> int:
    """Arbitra findings ja julgados e grava no blackboard do case.

    Sem escrita aqui: quem grava e `run_executor`, dentro do `--repo`. A CLI so
    imprime o pacote, e ele sai identico pela CLI e pelo MCP -- a gravacao e o
    produto do verbo, nao um `--out` que so uma das superficies conhece.

    `persisted: false` NAO e falha da chamada (regra 27): o pacote e montado
    antes da gravacao e sai igual com o blackboard indisponivel. O que falhou
    aparece nomeado em `persistence.errors`.
    """
    _print(
        _core.arbitrate_findings(
            args.repo,
            findings_path=args.findings,
            facts_path=args.facts,
            glue=args.glue,
            emr=args.emr,
            spark=args.spark,
            python=args.python,
            iceberg=args.iceberg,
            athena=args.athena,
        )
    )
    return 0


def _cmd_case_open(args: argparse.Namespace) -> int:
    case = _core.case_open(
        args.repo,
        args.case_id,
        args.now,
        glue=args.glue,
        emr=args.emr,
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
        facts_path=args.facts,
        strict_gates=args.strict_gates,
        reopen=args.reopen,
    )
    _print(case)
    return 0


def _cmd_case_get(args: argparse.Namespace) -> int:
    _print(_core.case_get(args.repo))
    return 0


def _cmd_case_update(args: argparse.Namespace) -> int:
    case = _core.case_update(
        args.repo,
        phase=args.phase,
        gate=args.gate,
        gate_value=(args.gate_value == "true"),
        skill=args.skill,
        now=args.now,
        outcome=args.outcome,
        override_gate=args.override_gate,
        reason=args.reason,
        facts_path=args.facts,
        hypothesis=args.hypothesis,
        prediction=args.prediction,
        experiment=args.experiment,
        close_hypothesis=args.close_hypothesis,
        hypothesis_outcome=args.hypothesis_outcome,
        evidence=args.evidence,
    )
    _print(case)
    return 0


def _cmd_next_step(args: argparse.Namespace) -> int:
    findings = _load_json_list(args.findings) if args.findings else []
    _print(_core.next_step(args.repo, findings))
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    findings = _load_json_list(args.findings) if args.findings else []
    payload = _core.resume_case(
        args.repo,
        findings,
        unresolved=args.unresolved,
        in_flight=args.in_flight,
        root=Path(args.repo),
    )
    _print(payload)
    return 0


def _cmd_handoff(args: argparse.Namespace) -> int:
    findings = _load_json_list(args.findings) if args.findings else []
    payload = _core.handoff(
        args.repo,
        findings,
        unresolved=args.unresolved,
        in_flight=args.in_flight,
        root=Path(args.repo),
    )
    _print(payload)
    return 0


def _cmd_playbook(args: argparse.Namespace) -> int:
    findings = _load_json_list(args.findings) if args.findings else []
    _print(_core.playbook(args.coordinator, repo=args.repo, findings=findings))
    return 0


def _cmd_runtime_detect(args: argparse.Namespace) -> int:
    payload = _core.runtime_detect(
        glue=args.glue,
        emr=args.emr,
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
        facts_path=args.facts,
    )
    _print(payload)
    return 0


def _cmd_pack_list(args: argparse.Namespace) -> int:
    _print(_core.pack_list())
    return 0


def _cmd_pack_check(args: argparse.Namespace) -> int:
    payload = _core.pack_check(args.dir)
    _print(payload)
    return 0 if payload["ok"] else 1


def _cmd_knowledge_drift(args: argparse.Namespace) -> int:
    _print(_core.knowledge_drift(url=args.source, as_of=args.as_of))
    return 0


def _cmd_knowledge_path(args: argparse.Namespace) -> int:
    _print(
        _core.knowledge_path(
            file=args.file, source_freshness=args.source_freshness, as_of=args.as_of
        )
    )
    return 0


def _cmd_debate_referee(args: argparse.Namespace) -> int:
    _print(_core.debate_referee(args.repo))
    return 0


# Recusa nomeada sai em stdout e com exit 0, como o `upheld: false` do
# `referee`: e resposta do protocolo, nao erro de fronteira. O driver decide o
# proximo passo por `status` e `reason`, e um exit != 0 so para `AdapterError`
# (arquivo ausente, JSON invalido) mantem os dois casos separaveis.
def _cmd_debate_start(args: argparse.Namespace) -> int:
    _print(
        _core.debate_start(
            args.repo,
            args.rules,
            findings_path=args.findings,
            facts_path=args.facts,
            glue=args.glue,
            emr=args.emr,
            spark=args.spark,
            python=args.python,
            iceberg=args.iceberg,
            athena=args.athena,
        )
    )
    return 0


def _cmd_debate_next(args: argparse.Namespace) -> int:
    _print(_core.debate_next(args.repo, args.debate))
    return 0


def _cmd_debate_submit(args: argparse.Namespace) -> int:
    _print(_core.debate_submit(args.repo, args.debate, payload_path=args.file))
    return 0


def _cmd_root_cause(args: argparse.Namespace) -> int:
    payload = _core.root_cause(
        facts_path=args.facts_paths,
        glue=args.glue,
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
        emr=args.emr,
        all_missing=args.all_missing,
        detail_level=args.detail_level,
    )
    _print(payload)
    return 0


def _cmd_lakeformation_access_graph(args: argparse.Namespace) -> int:
    _print(
        _core.lakeformation_access_graph(
            facts_path=args.facts_paths,
            principal_arn=args.principal_arn,
            target_table=args.target_table,
        )
    )
    return 0


def _cmd_lakeformation_matrix(args: argparse.Namespace) -> int:
    payload = _core.lakeformation_matrix(
        runtime=args.runtime, axis=args.axis, detail_level=args.detail_level
    )
    _print(payload)
    return 0


def _cmd_rules_lookup(args: argparse.Namespace) -> int:
    payload = _core.rules_lookup(
        id=args.id,
        category=args.category,
        limit=args.limit,
        cursor=args.cursor,
        source_freshness=args.source_freshness,
        as_of=args.as_of,
    )
    _print(payload)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    findings = _load_json_list(args.findings)
    errors: list[str] = []
    for index, finding in enumerate(findings):
        rule_id = finding.get("rule_id", "?") if isinstance(finding, dict) else "?"
        result = _core.validate_output(
            finding if isinstance(finding, dict) else {}, facts_path=args.facts
        )
        for message in result["errors"]:
            errors.append(f"finding[{index}] ({rule_id}): {message}")

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    _print({"valid": True, "count": len(findings)})
    return 0


def _cmd_report_sign(args: argparse.Namespace) -> int:
    _print(_core.report_sign(args.report, args.findings))
    return 0


def _cmd_report_github(args: argparse.Namespace) -> int:
    """O unico verbo cujo stdout NAO e JSON, e a razao e o consumidor.

    O GitHub transforma em anotacao a linha `::error file=..::msg` inteira no
    stdout do step; misturar com JSON quebraria o parser dos workflow commands.
    Por isso o stdout leva so as anotacoes, a contagem vai para o stderr, e o
    SARIF e o resumo vao para arquivo de nome fixo, que o workflow le.
    Codigo 1 so pelo gate (`--fail-on`), como `report verify`; erro de uso e 2.
    """
    payload = _core.report_github(
        args.findings,
        args.facts,
        repo=args.repo,
        source_roots=args.source_roots,
        category=args.category,
        fail_on=args.fail_on,
        source_freshness=args.source_freshness,
        as_of=args.as_of,
    )
    gravados = _core.report_github_write(args.repo, payload)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for linha in payload["annotations"]:
        sys.stdout.write(linha + "\n")
    counts, gate = payload["counts"], payload["gate"]
    estado = "off" if gate["fail_on"] is None else f"{gate['fail_on']}: " + (
        "disparou" if gate["tripped"] else "ok"
    )
    print(
        f"sparkforge report github: {counts['located']} no SARIF, {counts['refused']} sem "
        f"localizacao, gate {estado} ({gravados['sparkforge.sarif']}, {gravados['summary.md']})",
        file=sys.stderr,
    )
    return 1 if gate["tripped"] else 0


def _cmd_telemetry_export(args: argparse.Namespace) -> int:
    """Grava os dois arquivos e imprime o resumo (sem os spans, que ja estao no
    arquivo): contagens, recusas, lacunas e os caminhos gravados."""
    payload = _core.telemetry_export(
        args.run_id, host_transcript=args.host_transcript, provider=args.provider
    )
    gravados = _core.telemetry_export_write(args.repo, payload)
    _print(
        {
            "run_id": payload["run_id"],
            "files": sorted(gravados.values()),
            "counts": payload["counts"],
            "refused": payload["refused"],
            "unresolved": payload["unresolved"],
            "semconv_genai_commit": payload["semconv_genai_commit"],
            "otlp_version": payload["otlp_version"],
        }
    )
    return 0


def _cmd_proof(args: argparse.Namespace) -> int:
    _print(
        _core.proof_change(
            args.findings,
            args.facts,
            args.after_facts,
            args.applied,
            glue=args.glue,
            spark=args.spark,
            python=args.python,
            iceberg=args.iceberg,
            athena=args.athena,
            emr=args.emr,
        )
    )
    return 0


def _cmd_gain(args: argparse.Namespace) -> int:
    _print(_core.gain(args.baseline, args.candidate))
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    resultado = _core.scan(
        args.raiz, dry_run=args.dry_run, output_format=args.format, fail_on=args.fail_on,
        glue=args.glue, spark=args.spark, python=args.python, iceberg=args.iceberg,
        athena=args.athena, emr=args.emr,
    )
    _print(resultado)
    return 1 if (resultado.get("gate") or {}).get("tripped") else 0


def _cmd_policy_check(args: argparse.Namespace) -> int:
    _print(_core.policy_check(args.repo))
    return 0


def _cmd_policy_explain(args: argparse.Namespace) -> int:
    _print(_core.policy_explain(args.repo, command=args.bash, file_path=args.path, tool=args.tool))
    return 0


def _cmd_policy_sync_settings(args: argparse.Namespace) -> int:
    resultado = _core.policy_sync_settings(args.repo, check=args.check)
    _print(resultado)
    return 1 if args.check and not resultado["in_sync"] else 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    resultado = _core.doctor(args.repo, online=args.online)
    _print(resultado)
    return 0 if resultado["healthy"] else 1


def _cmd_simulate(args: argparse.Namespace) -> int:
    _print(
        _core.simulate_change(
            args.facts,
            args.sets,
            glue=args.glue,
            spark=args.spark,
            python=args.python,
            iceberg=args.iceberg,
            athena=args.athena,
            emr=args.emr,
        )
    )
    return 0


def _cmd_receipt_emit(args: argparse.Namespace) -> int:
    """Grava o recibo e imprime onde, sem o corpo inteiro: o arquivo ja o tem."""
    payload = _core.receipt_emit_and_write(
        args.repo,
        facts_path=args.facts,
        findings_path=args.findings,
        now=args.now,
        report_path=args.report,
        run_id=args.run_id,
        host_transcript=args.host_transcript,
        provider=args.provider,
    )
    _print({chave: valor for chave, valor in payload.items() if chave != "receipt"})
    return 0


def _cmd_receipt_verify(args: argparse.Namespace) -> int:
    payload = _core.receipt_verify(args.repo, args.receipt, host_transcript=args.host_transcript)
    _print(payload)
    return 0 if payload["valid"] else 1


def _cmd_report_verify(args: argparse.Namespace) -> int:
    payload = _core.report_verify(args.report, args.findings)
    _print(payload)
    # Codigo 1, nunca 0: relatorio que nao corresponde precisa parar um pipeline,
    # e `validate` ja estabeleceu esse contrato para o gate de saida.
    return 0 if payload["valid"] else 1


def _cmd_collect_event_log(args: argparse.Namespace) -> int:
    payload = _core.collect_event_log(
        args.repo, job_run_id=args.job_run, bucket=args.bucket, prefix=args.prefix, now=args.now
    )
    _print(payload)
    return 0


def _cmd_collect_glue_job(args: argparse.Namespace) -> int:
    payload = _core.collect_glue_job(args.repo, job_name=args.job_name, now=args.now)
    _print(payload)
    return 0


def _cmd_collect_cloudwatch(args: argparse.Namespace) -> int:
    payload = _core.collect_cloudwatch(
        args.repo,
        job_name=args.job_name,
        job_run_id=args.job_run,
        start=args.start,
        end=args.end,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_cloudwatch_logs(args: argparse.Namespace) -> int:
    payload = _core.collect_cloudwatch_logs(
        args.repo,
        job_name=args.job_name,
        job_run_id=args.job_run,
        log_group=args.log_group,
        start=args.start,
        end=args.end,
        filter_pattern=args.filter_pattern,
        max_events=args.max_events,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_glue_resource_link(args: argparse.Namespace) -> int:
    payload = _core.collect_glue_resource_link(
        args.repo,
        database=args.database,
        table=args.table,
        catalog_id=args.catalog_id,
        verify_target=not args.no_verify_target,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_iam_access(args: argparse.Namespace) -> int:
    payload = _core.collect_iam_access(
        args.repo,
        role_arn=args.role_arn,
        actions=args.actions,
        resource_arns=args.resource_arns,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_lakeformation(args: argparse.Namespace) -> int:
    payload = _core.collect_lakeformation(
        args.repo,
        database=args.database,
        table=args.table,
        catalog_id=args.catalog_id,
        resource_arn=args.resource_arn,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_glue_job_runs(args: argparse.Namespace) -> int:
    payload = _core.collect_glue_job_runs(
        args.repo, job_name=args.job_name, max_runs=args.max_runs, now=args.now
    )
    _print(payload)
    return 0


def _cmd_collect_iceberg_metadata(args: argparse.Namespace) -> int:
    payload = _core.collect_iceberg_metadata(
        args.repo,
        table=args.table,
        workgroup=args.workgroup,
        output_location=args.output_location,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_athena_workgroup(args: argparse.Namespace) -> int:
    payload = _core.collect_athena_workgroup(args.repo, workgroup=args.workgroup, now=args.now)
    _print(payload)
    return 0


def _cmd_collect_emr_cluster(args: argparse.Namespace) -> int:
    payload = _core.collect_emr_cluster(args.repo, cluster_id=args.cluster_id, now=args.now)
    _print(payload)
    return 0


def _cmd_collect_emr_serverless(args: argparse.Namespace) -> int:
    payload = _core.collect_emr_serverless(
        args.repo, application_id=args.application_id, now=args.now
    )
    _print(payload)
    return 0


def _cmd_collect_emr_eks(args: argparse.Namespace) -> int:
    payload = _core.collect_emr_eks(
        args.repo,
        virtual_cluster_id=args.virtual_cluster_id,
        job_run_id=args.job_run_id,
        now=args.now,
    )
    _print(payload)
    return 0


def _cmd_collect_verify(args: argparse.Namespace) -> int:
    _print(_core.collect_verify(args.repo))
    return 0


def _cmd_code_init(args: argparse.Namespace) -> int:
    _print(_core.code_init(args.root, db=args.db))
    return 0


def _cmd_code_sync(args: argparse.Namespace) -> int:
    _print(_core.code_sync(args.root, db=args.db))
    return 0


def _cmd_code_status(args: argparse.Namespace) -> int:
    _print(_core.code_status(args.root, detail_level=args.detail_level, db=args.db))
    return 0


def _cmd_code_search(args: argparse.Namespace) -> int:
    _print(
        _core.code_search(
            args.root,
            query=args.term,
            kind=args.kind,
            path_prefix=args.path_prefix,
            limit=args.limit,
            db=args.db,
        )
    )
    return 0


def _cmd_code_export(args: argparse.Namespace) -> int:
    _print(
        _core.code_export(
            args.root,
            communities=args.communities,
            detail_level=args.detail_level,
            db=args.db,
        )
    )
    return 0


def _cmd_code_shape(args: argparse.Namespace) -> int:
    _print(
        _core.code_shape(
            args.root,
            top=args.top,
            detail_level=args.detail_level,
            db=args.db,
        )
    )
    return 0


def _cmd_code_path(args: argparse.Namespace) -> int:
    _print(
        _core.code_path(
            args.root,
            origem=args.origem,
            destino=args.destino,
            depth=args.depth,
            detail_level=args.detail_level,
            db=args.db,
        )
    )
    return 0


def _cmd_code_symbol(args: argparse.Namespace) -> int:
    _print(
        _core.code_symbol(
            args.root,
            node_id=args.node_id,
            depth=args.depth,
            detail_level=args.detail_level,
            db=args.db,
        )
    )
    return 0


def _cmd_code_read(args: argparse.Namespace) -> int:
    _print(
        _core.code_read(
            args.root,
            node_id=args.node_id,
            file=args.file,
            start_line=args.start_line,
            end_line=args.end_line,
            context_lines=args.context_lines,
            max_tokens=args.max_tokens,
            db=args.db,
        )
    )
    return 0


def _cmd_code_context(args: argparse.Namespace) -> int:
    _print(
        _core.code_context(
            args.root,
            task=args.task,
            max_tokens=args.max_tokens,
            include=args.include,
            db=args.db,
        )
    )
    return 0


def _cmd_code_doctor(args: argparse.Namespace) -> int:
    relatorio = _core.code_doctor(args.root, db=args.db)
    _print(relatorio)
    # Exit code 1 quando alguma checagem falhou, e nao 0 com o relatorio bonito:
    # doctor que sempre sai 0 nao serve num gate de CI -- ninguem le o JSON,
    # todo mundo le o codigo de saida.
    return 0 if relatorio["ok"] else 1


def _cmd_code_purge(args: argparse.Namespace) -> int:
    _print(_core.code_purge(args.root, db=args.db))
    return 0


# ======================================================================
# Agentic CLI handlers
# ======================================================================


def _cmd_agents_list(args: argparse.Namespace) -> int:
    """Lista agentes disponíveis no diretório agents/."""
    from pathlib import Path

    agents_dir = Path(args.repo) / "agents"
    if not agents_dir.exists():
        _print({"agents": [], "count": 0, "error": "agents/ directory not found"})
        return 0

    agents: list[dict[str, str]] = []
    # Use iterdir + filter instead of glob to avoid raw glob gate.
    # The gate in test_facts_scan.py forbids bare .glob()/.rglob() in
    # sparkforge/ — iterdir is the sanctioned alternative for directory listing.
    for f in sorted(agents_dir.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        name = f.stem
        try:
            content = f.read_text(encoding="utf-8")
            description = ""
            if "description:" in content:
                for line in content.split("\n"):
                    if line.strip().startswith("description:"):
                        description = line.split("description:", 1)[1].strip().strip('"').strip("'")
                        break
            agents.append({"name": name, "description": description, "file": str(f)})
        except Exception:
            agents.append({"name": name, "description": "", "file": str(f)})

    _print({"agents": agents, "count": len(agents)})
    return 0


def _cmd_agents_inspect(args: argparse.Namespace) -> int:
    """Inspeciona um agente específico.

    O `--id` vira nome de arquivo, então ele não pode conter separador nem
    `..`: sem isso, `--id ../../etc/passwd` leria fora de `agents/`.
    """
    from pathlib import Path

    if "/" in args.id or "\\" in args.id or args.id in ("", ".", ".."):
        print(
            f"id invalido: {args.id!r} — esperado o nome do agente, sem caminho.",
            file=sys.stderr,
        )
        return 1

    agents_dir = (Path(args.repo) / "agents").resolve()
    agent_file = (agents_dir / f"{args.id}.md").resolve()
    if agents_dir not in agent_file.parents:
        print(f"id invalido: {args.id!r} — resolve fora de {agents_dir}.", file=sys.stderr)
        return 1
    if not agent_file.exists():
        print(f"Agent not found: {args.id}", file=sys.stderr)
        return 1

    content = agent_file.read_text(encoding="utf-8")
    _print({"id": args.id, "file": str(agent_file), "content": content})
    return 0


def _cmd_blackboard_summary(args: argparse.Namespace) -> int:
    """Resumo contável do blackboard."""
    from sparkforge.agentic.blackboard import summarize

    s = summarize(args.repo)
    _print(
        {
            "claims": s.claims,
            "evidence": s.evidence,
            "hypotheses": s.hypotheses,
            "objections": s.objections,
            "rebuttals": s.rebuttals,
            "contradictions": s.contradictions,
            "experiments": s.experiments,
            "decisions": s.decisions,
            "unknowns": s.unknowns,
            "open_unknowns": s.open_unknowns,
            "open_hypotheses": s.open_hypotheses,
            "unresolved_contradictions": s.unresolved_contradictions,
        }
    )
    return 0


def _cmd_blackboard_list(args: argparse.Namespace) -> int:
    """Lista entidades de um tipo do blackboard."""
    from sparkforge.agentic import blackboard as bb

    readers = {
        "claims": bb.read_claims,
        "evidence": bb.read_evidence,
        "hypotheses": bb.read_hypotheses,
        "objections": bb.read_objections,
        "rebuttals": bb.read_rebuttals,
        "contradictions": bb.read_contradictions,
        "experiments": bb.read_experiments,
        "decisions": bb.read_decisions,
        "unknowns": bb.read_unknowns,
    }
    reader = readers.get(args.type)
    if reader is None:
        print(f"Unknown type: {args.type}", file=sys.stderr)
        return 1

    records = reader(args.repo)
    _print({"type": args.type, "count": len(records), "records": records})
    return 0


def _cmd_decisions_list(args: argparse.Namespace) -> int:
    """Lista decisões do blackboard e da memória institucional."""
    from sparkforge.agentic.blackboard import read_decisions
    from sparkforge.agentic.memory import get_decision_history

    bb_decisions = read_decisions(args.repo)
    mem_decisions = get_decision_history(args.repo)

    _print(
        {
            "blackboard_decisions": bb_decisions,
            "blackboard_count": len(bb_decisions),
            "institutional_decisions": mem_decisions,
            "institutional_count": len(mem_decisions),
        }
    )
    return 0


def _cmd_decisions_explain(args: argparse.Namespace) -> int:
    """Explica uma decisão específica."""
    from sparkforge.agentic.blackboard import get_entity_by_id

    decision = get_entity_by_id(args.id, args.repo)
    if decision is None:
        print(f"Decision not found: {args.id}", file=sys.stderr)
        return 1

    _print(decision)
    return 0


def _cmd_budget_show(args: argparse.Namespace) -> int:
    """Mostra o budget DECLARADO do case, ou `unresolved` nomeando a lacuna.

    Nunca devolve o default do codigo como se fosse estado do case: ate
    2026-09-03 este verbo imprimia `CaseBudget()` com `tokens_used: 0` e
    `status: within` sem nenhuma marca de que o numero era de fabrica. Fake
    de leitura e o defeito que os dois commits anteriores deste branch
    removeram da coleta.

    Consumo tambem nao e inventado: ele vive no ledger de spans, e quem o le e
    `sparkforge economy report --run-id <id>`. Token de provider so existe com
    transcript do host (regra 24), e custo em dolar exige `cost_basis`
    (regra 25) -- por isso os dois saem `unresolved` aqui.
    """
    from sparkforge.agentic.budget import CASE_BUDGET_KEY, CaseBudget, case_budget_from_case
    from sparkforge.case.store import CaseError, case_path, load_case

    if args.template:
        _print(
            {
                "kind": "template",
                "note": (
                    "Valores padrao do codigo (CaseBudget). NAO e o estado de "
                    "nenhum case -- para o estado, rode sem --template."
                ),
                "limits": CaseBudget().to_dict(),
            }
        )
        return 0

    try:
        case = load_case(args.repo)
    except (CaseError, FileNotFoundError) as exc:
        print(f"case ausente ou invalido em {case_path(args.repo)}: {exc}", file=sys.stderr)
        return 1

    try:
        declared = case_budget_from_case(case)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if declared is None:
        limits: dict[str, Any] = {
            "status": "unresolved",
            "reason": (
                f"case.yaml nao declara o bloco `{CASE_BUDGET_KEY}:`. Sem teto "
                f"declarado nao ha budget deste case -- o default do codigo e "
                f"template, nao medida. Veja `budget show --template`."
            ),
        }
    else:
        limits = {"status": "declared", "source": str(case_path(args.repo))}
        limits.update(
            {k: v for k, v in declared.to_dict().items() if k.startswith("max_")},
        )

    _print(
        {
            "case_id": case.get("case_id", ""),
            "limits": limits,
            "consumption": {
                "status": "unresolved",
                "payload_bytes": "medido por run, nao por case: "
                "`sparkforge economy report --run-id <run_id>`",
                "tokens": "tokens_unresolved -- exige transcript do host (regra 24)",
                "cost_usd": "unresolved -- exige cost_basis nomeado (regra 25)",
            },
        }
    )
    return 0


def _cmd_autonomy_show(args: argparse.Namespace) -> int:
    """Mostra perfil de um nível de autonomia."""
    from sparkforge.agentic.autonomy import AutonomyLevel, get_profile

    level_map = {
        "L0": AutonomyLevel.L0_DETERMINISTIC,
        "L1": AutonomyLevel.L1_SPECIALIST,
        "L2": AutonomyLevel.L2_COOPERATIVE,
        "L3": AutonomyLevel.L3_DEBATE,
        "L4": AutonomyLevel.L4_EXPERIMENTAL,
        "L5": AutonomyLevel.L5_AUTONOMOUS,
    }
    level = level_map.get(args.level)
    if level is None:
        print(f"Unknown level: {args.level}", file=sys.stderr)
        return 1

    profile = get_profile(level)
    _print(
        {
            "level": profile.level.value,
            "name": profile.name,
            "description": profile.description,
            "allowed_actions": profile.allowed_actions,
            "forbidden_actions": profile.forbidden_actions,
            "max_budget_tokens": profile.max_budget_tokens,
            "max_agents": profile.max_agents,
            "max_debates": profile.max_debates,
            "max_experiments": profile.max_experiments,
            "approval_policy": profile.approval_policy,
            "required_validation": profile.required_validation,
            "risk_level": profile.risk_level,
        }
    )
    return 0


_DISPATCH = {
    ("analyze", "pyspark"): _cmd_analyze_pyspark,
    ("analyze", "catalog-schema"): _cmd_analyze_catalog_schema,
    ("analyze", "event-log"): _cmd_analyze_event_log,
    ("analyze", "sql-metrics"): _cmd_analyze_sql_metrics,
    ("analyze", "cloudwatch"): _cmd_analyze_cloudwatch,
    ("analyze", "cloudwatch-logs"): _cmd_analyze_cloudwatch_logs,
    ("analyze", "lakeformation-grants"): _cmd_analyze_lakeformation_grants,
    ("analyze", "glue-resource-link"): _cmd_analyze_glue_resource_link,
    ("analyze", "iam-access"): _cmd_analyze_iam_access,
    ("analyze", "parquet-footer"): _cmd_analyze_parquet_footer,
    ("analyze", "error-signatures"): _cmd_analyze_error_signatures,
    ("analyze", "glue-job-runs"): _cmd_analyze_glue_job_runs,
    ("analyze", "plan"): _cmd_analyze_plan,
    ("analyze", "terraform"): _cmd_analyze_terraform,
    ("analyze", "iceberg"): _cmd_analyze_iceberg,
    ("analyze", "sql"): _cmd_analyze_sql,
    ("analyze", "athena-workgroup"): _cmd_analyze_athena_workgroup,
    ("analyze", "emr-cluster"): _cmd_analyze_emr_cluster,
    ("analyze", "emr-serverless"): _cmd_analyze_emr_serverless,
    ("analyze", "emr-eks"): _cmd_analyze_emr_eks,
    ("analyze", "controlm-jobs"): _cmd_analyze_controlm_jobs,
    ("analyze", "data-quality"): _cmd_analyze_data_quality,
    ("analyze", "graph"): _cmd_analyze_graph,
    ("analyze", "call-graph"): _cmd_analyze_call_graph,
    ("analyze", "s3-listing"): _cmd_analyze_s3_listing,
    ("analyze", "consumers"): _cmd_analyze_consumers,
    ("analyze", "terraform-diff"): _cmd_analyze_terraform_diff,
    ("migrate", "glue"): _cmd_migrate_glue,
    ("migrate", "emr"): _cmd_migrate_emr,
    ("migrate", "controlm"): _cmd_migrate_controlm,
    ("glue", "dependency-audit"): _cmd_glue_dependency_audit,
    ("iceberg", "assess-upgrade"): _cmd_iceberg_assess_upgrade,
    ("release", "describe"): _cmd_release_describe,
    ("release", "diff"): _cmd_release_diff,
    ("controlm", "describe"): _cmd_controlm_describe,
    ("benchmark", None): _cmd_benchmark,
    ("workload", None): _cmd_workload,
    ("capacity", None): _cmd_capacity,
    ("finops", None): _cmd_finops,
    ("tune", None): _cmd_tune,
    ("economy", "report"): _cmd_economy_report,
    ("telemetry", "export"): _cmd_telemetry_export,
    ("receipt", "emit"): _cmd_receipt_emit,
    ("receipt", "verify"): _cmd_receipt_verify,
    ("proof", None): _cmd_proof,
    ("simulate", None): _cmd_simulate,
    ("gain", None): _cmd_gain,
    ("scan", None): _cmd_scan,
    ("doctor", None): _cmd_doctor,
    ("policy", "check"): _cmd_policy_check,
    ("policy", "explain"): _cmd_policy_explain,
    ("policy", "sync-settings"): _cmd_policy_sync_settings,
    ("funcval", "plan"): _cmd_funcval_plan,
    ("funcval", "compare"): _cmd_funcval_compare,
    ("fuse", None): _cmd_fuse,
    ("judge", None): _cmd_judge,
    ("arbitrate", None): _cmd_arbitrate,
    ("case", "open"): _cmd_case_open,
    ("case", "get"): _cmd_case_get,
    ("case", "update"): _cmd_case_update,
    ("next-step", None): _cmd_next_step,
    ("resume", None): _cmd_resume,
    ("handoff", None): _cmd_handoff,
    ("playbook", None): _cmd_playbook,
    ("runtime", "detect"): _cmd_runtime_detect,
    # `index` e alias historico de `init` (argparse `aliases=`): mesmo parser,
    # mesmo handler. Duas entradas porque `args.code_action` guarda o nome
    # DIGITADO, nao o canonico.
    ("code", "init"): _cmd_code_init,
    ("code", "index"): _cmd_code_init,
    ("code", "sync"): _cmd_code_sync,
    ("code", "status"): _cmd_code_status,
    ("code", "search"): _cmd_code_search,
    ("code", "export"): _cmd_code_export,
    ("code", "shape"): _cmd_code_shape,
    ("code", "path"): _cmd_code_path,
    ("code", "symbol"): _cmd_code_symbol,
    ("code", "read"): _cmd_code_read,
    ("code", "context"): _cmd_code_context,
    ("code", "doctor"): _cmd_code_doctor,
    ("code", "purge"): _cmd_code_purge,
    ("knowledge", "path"): _cmd_knowledge_path,
    ("knowledge", "drift"): _cmd_knowledge_drift,
    ("pack", "list"): _cmd_pack_list,
    ("pack", "check"): _cmd_pack_check,
    ("debate", "referee"): _cmd_debate_referee,
    ("debate", "start"): _cmd_debate_start,
    ("debate", "next"): _cmd_debate_next,
    ("debate", "submit"): _cmd_debate_submit,
    ("root-cause", None): _cmd_root_cause,
    ("lakeformation", "matrix"): _cmd_lakeformation_matrix,
    ("lakeformation", "access-graph"): _cmd_lakeformation_access_graph,
    ("rules", "lookup"): _cmd_rules_lookup,
    ("validate", None): _cmd_validate,
    ("report", "sign"): _cmd_report_sign,
    ("report", "verify"): _cmd_report_verify,
    ("report", "github"): _cmd_report_github,
    ("collect", "event-log"): _cmd_collect_event_log,
    ("collect", "glue-job"): _cmd_collect_glue_job,
    ("collect", "cloudwatch"): _cmd_collect_cloudwatch,
    ("collect", "cloudwatch-logs"): _cmd_collect_cloudwatch_logs,
    ("collect", "lakeformation"): _cmd_collect_lakeformation,
    ("collect", "glue-resource-link"): _cmd_collect_glue_resource_link,
    ("collect", "iam-access"): _cmd_collect_iam_access,
    ("collect", "glue-job-runs"): _cmd_collect_glue_job_runs,
    ("collect", "iceberg-metadata"): _cmd_collect_iceberg_metadata,
    ("collect", "athena-workgroup"): _cmd_collect_athena_workgroup,
    ("collect", "emr-cluster"): _cmd_collect_emr_cluster,
    ("collect", "emr-serverless"): _cmd_collect_emr_serverless,
    ("collect", "emr-eks"): _cmd_collect_emr_eks,
    ("collect", "verify"): _cmd_collect_verify,
    # agentic
    ("agents", "list"): _cmd_agents_list,
    ("agents", "inspect"): _cmd_agents_inspect,
    ("blackboard", "summary"): _cmd_blackboard_summary,
    ("blackboard", "list"): _cmd_blackboard_list,
    ("decisions", "list"): _cmd_decisions_list,
    ("decisions", "explain"): _cmd_decisions_explain,
    ("budget", "show"): _cmd_budget_show,
    ("autonomy", "show"): _cmd_autonomy_show,
}


def _dispatch(args: argparse.Namespace) -> int:
    sub_action = (
        getattr(args, "analyze_target", None)
        or getattr(args, "case_action", None)
        or getattr(args, "funcval_action", None)
        or getattr(args, "runtime_action", None)
        or getattr(args, "code_action", None)
        or getattr(args, "knowledge_action", None)
        or getattr(args, "policy_action", None)
        or getattr(args, "pack_action", None)
        or getattr(args, "debate_action", None)
        or getattr(args, "lakeformation_action", None)
        or getattr(args, "rules_action", None)
        or getattr(args, "report_action", None)
        or getattr(args, "collect_action", None)
        or getattr(args, "migrate_action", None)
        or getattr(args, "glue_action", None)
        or getattr(args, "iceberg_action", None)
        or getattr(args, "release_action", None)
        or getattr(args, "controlm_action", None)
        or getattr(args, "agents_action", None)
        or getattr(args, "blackboard_action", None)
        or getattr(args, "decisions_action", None)
        or getattr(args, "budget_action", None)
        or getattr(args, "autonomy_action", None)
        or getattr(args, "subcommand", None)
    )
    handler = _DISPATCH.get((args.command, sub_action))
    if handler is None:
        handler = _DISPATCH.get((args.command, None))
    if handler is None:
        raise _core.AdapterError(f"comando desconhecido: {args.command} {sub_action}", exit_code=2)
    return handler(args)


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except _core.AdapterError as exc:
        print(exc.message, file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
