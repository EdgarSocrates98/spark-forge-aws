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


# Uma unica redacao para os tres verbos que aceitam a flag. Repetir o texto tres
# vezes e como uma delas fica desatualizada.
_EMR_FLAG_HELP = (
    "Release do EMR on EC2. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. "
    "E DECLARACAO, nao observacao: perde para o event log e para um dump de "
    "`describe-cluster`, e discordar de um deles vira divergencia reportada, "
    "nunca valor substituido em silencio. Serve a quem sabe a release e nao tem "
    "o dump -- com o dump, `--facts` ja resolve sozinho."
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

    plan_p = analyze_sub.add_parser(
        "plan",
        help=(
            "Extrai facts do texto de um plano fisico "
            "(`df.explain(\"formatted\")` / EXPLAIN FORMATTED)."
        ),
    )
    plan_p.add_argument("--path", required=True, help="Arquivo de texto com a saida de explain.")
    plan_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    plan_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    plan_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    plan_p.add_argument("--cursor")

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

    dq_p = analyze_sub.add_parser(
        "data-quality",
        help="Extrai facts de validacao de dado no codigo PySpark (PyDeequ, Great "
        "Expectations e validacao artesanal): onde o check roda, se tem consequencia, "
        "e quantas passadas custa.",
    )
    dq_p.add_argument(
        "--path", required=True, help="Arquivo .py ou diretorio com codigo PySpark."
    )
    dq_p.add_argument("--out", help="Escreve a lista completa de facts (JSON) neste arquivo.")
    dq_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    dq_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    dq_p.add_argument("--cursor")

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
    benchmark_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    benchmark_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    benchmark_p.add_argument("--cursor")

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
            "Decomposicao de um coordenador em passos sequenciais -- o espelho de "
            "orquestracao para plataforma sem despacho de subagente (Devin, Codex, "
            "Copilot). Le agents/, nunca repete a lista de executores."
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

    # knowledge path --------------------------------------------------------
    knowledge_p = sub.add_parser(
        "knowledge", help="Localiza os arquivos de conhecimento versionado."
    )
    knowledge_sub = knowledge_p.add_subparsers(dest="knowledge_action", required=True)
    knowledge_path_p = knowledge_sub.add_parser(
        "path", help="Imprime a raiz de knowledge e, com --file, um arquivo dentro dela."
    )
    knowledge_path_p.add_argument("--file")

    # rules lookup --------------------------------------------------------
    rules_p = sub.add_parser("rules", help="Consulta o catalogo de regras versionado.")
    rules_sub = rules_p.add_subparsers(dest="rules_action", required=True)
    lookup_p = rules_sub.add_parser(
        "lookup", help="Busca regras por id ou categoria (thresholds, fontes, severidade)."
    )
    lookup_p.add_argument("--id", action="append")
    lookup_p.add_argument("--category")
    lookup_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    lookup_p.add_argument("--cursor")

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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
    return 0


def _cmd_analyze_terraform_diff(args: argparse.Namespace) -> int:
    full = _core.analyze_terraform_diff(
        args.before, args.after, kind=args.kind, limit=None
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
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
    _print(payload)
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    full = _core.benchmark_runs(args.before, args.after, kind=args.kind, limit=None)
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
    _print(payload)
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
    _print(payload)
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
        "items": page,
    }
    if args.show_skipped:
        payload["skipped"] = full.get("skipped", [])
    _print(payload)
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


def _cmd_knowledge_path(args: argparse.Namespace) -> int:
    _print(_core.knowledge_path(file=args.file))
    return 0


def _cmd_rules_lookup(args: argparse.Namespace) -> int:
    payload = _core.rules_lookup(
        id=args.id, category=args.category, limit=args.limit, cursor=args.cursor
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


def _cmd_collect_verify(args: argparse.Namespace) -> int:
    _print(_core.collect_verify(args.repo))
    return 0


_DISPATCH = {
    ("analyze", "pyspark"): _cmd_analyze_pyspark,
    ("analyze", "catalog-schema"): _cmd_analyze_catalog_schema,
    ("analyze", "event-log"): _cmd_analyze_event_log,
    ("analyze", "plan"): _cmd_analyze_plan,
    ("analyze", "terraform"): _cmd_analyze_terraform,
    ("analyze", "iceberg"): _cmd_analyze_iceberg,
    ("analyze", "sql"): _cmd_analyze_sql,
    ("analyze", "athena-workgroup"): _cmd_analyze_athena_workgroup,
    ("analyze", "emr-cluster"): _cmd_analyze_emr_cluster,
    ("analyze", "data-quality"): _cmd_analyze_data_quality,
    ("analyze", "call-graph"): _cmd_analyze_call_graph,
    ("analyze", "s3-listing"): _cmd_analyze_s3_listing,
    ("analyze", "consumers"): _cmd_analyze_consumers,
    ("analyze", "terraform-diff"): _cmd_analyze_terraform_diff,
    ("benchmark", None): _cmd_benchmark,
    ("fuse", None): _cmd_fuse,
    ("judge", None): _cmd_judge,
    ("case", "open"): _cmd_case_open,
    ("case", "get"): _cmd_case_get,
    ("case", "update"): _cmd_case_update,
    ("next-step", None): _cmd_next_step,
    ("resume", None): _cmd_resume,
    ("handoff", None): _cmd_handoff,
    ("playbook", None): _cmd_playbook,
    ("runtime", "detect"): _cmd_runtime_detect,
    ("knowledge", "path"): _cmd_knowledge_path,
    ("rules", "lookup"): _cmd_rules_lookup,
    ("validate", None): _cmd_validate,
    ("collect", "event-log"): _cmd_collect_event_log,
    ("collect", "glue-job"): _cmd_collect_glue_job,
    ("collect", "cloudwatch"): _cmd_collect_cloudwatch,
    ("collect", "iceberg-metadata"): _cmd_collect_iceberg_metadata,
    ("collect", "athena-workgroup"): _cmd_collect_athena_workgroup,
    ("collect", "emr-cluster"): _cmd_collect_emr_cluster,
    ("collect", "verify"): _cmd_collect_verify,
}


def _dispatch(args: argparse.Namespace) -> int:
    sub_action = (
        getattr(args, "analyze_target", None)
        or getattr(args, "case_action", None)
        or getattr(args, "runtime_action", None)
        or getattr(args, "knowledge_action", None)
        or getattr(args, "rules_action", None)
        or getattr(args, "collect_action", None)
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
