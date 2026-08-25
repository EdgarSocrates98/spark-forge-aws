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
    payload["items"], procedencias, versao = _core.project_items(
        payload["items"], detail_level
    )
    return _core.declarar_no_envelope(payload, procedencias, versao)


# Uma unica redacao para os tres verbos que aceitam a flag. Repetir o texto tres
# vezes e como uma delas fica desatualizada.
_EMR_FLAG_HELP = (
    "Release do EMR on EC2. Aceita as duas grafias -- `emr-7.5.0` e `7.5.0`. "
    "E DECLARACAO, nao observacao: perde para o event log e para um dump de "
    "`describe-cluster`, e discordar de um deles vira divergencia reportada, "
    "nunca valor substituido em silencio. Serve a quem sabe a release e nao tem "
    "o dump -- com o dump, `--facts` ja resolve sozinho."
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
    migrate_glue_p.add_argument(
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
        "--before-runtime", dest="before_runtime", default="",
        help="Versao de runtime em que a execucao ANTES rodou (ex.: 5.1).",
    )
    benchmark_p.add_argument(
        "--after-runtime", dest="after_runtime", default="",
        help="Versao de runtime em que a execucao DEPOIS rodou (ex.: 6.0).",
    )
    benchmark_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    benchmark_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    benchmark_p.add_argument("--cursor")
    _add_detail_level(benchmark_p)

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
    code_read_p.add_argument(
        "--max-tokens", type=int, default=_core.CODE_READ_DEFAULT_TOKENS
    )

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
                "Apaga SOMENTE .sparkforge/local/codeintel/. Qualquer outro "
                "diretorio e recusado."
            ),
        )
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
    _print(_apply_detail_level(payload, args.detail_level))
    return 0


def _cmd_migrate_glue(args: argparse.Namespace) -> int:
    payload = _core.migration_assess(
        args.path, source=args.from_runtime, target=args.to_runtime
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0


def _cmd_glue_dependency_audit(args: argparse.Namespace) -> int:
    _print(_core.glue_dependency_audit(args.path, glue=args.glue_version))
    return 0


def _cmd_iceberg_assess_upgrade(args: argparse.Namespace) -> int:
    _print(
        _core.iceberg_assess_upgrade(args.path, source=args.from_spec, target=args.to_spec)
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


def _cmd_report_sign(args: argparse.Namespace) -> int:
    _print(_core.report_sign(args.report, args.findings))
    return 0


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
    ("analyze", "emr-serverless"): _cmd_analyze_emr_serverless,
    ("analyze", "data-quality"): _cmd_analyze_data_quality,
    ("analyze", "graph"): _cmd_analyze_graph,
    ("analyze", "call-graph"): _cmd_analyze_call_graph,
    ("analyze", "s3-listing"): _cmd_analyze_s3_listing,
    ("analyze", "consumers"): _cmd_analyze_consumers,
    ("analyze", "terraform-diff"): _cmd_analyze_terraform_diff,
    ("migrate", "glue"): _cmd_migrate_glue,
    ("glue", "dependency-audit"): _cmd_glue_dependency_audit,
    ("iceberg", "assess-upgrade"): _cmd_iceberg_assess_upgrade,
    ("benchmark", None): _cmd_benchmark,
    ("funcval", "plan"): _cmd_funcval_plan,
    ("funcval", "compare"): _cmd_funcval_compare,
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
    # `index` e alias historico de `init` (argparse `aliases=`): mesmo parser,
    # mesmo handler. Duas entradas porque `args.code_action` guarda o nome
    # DIGITADO, nao o canonico.
    ("code", "init"): _cmd_code_init,
    ("code", "index"): _cmd_code_init,
    ("code", "sync"): _cmd_code_sync,
    ("code", "status"): _cmd_code_status,
    ("code", "search"): _cmd_code_search,
    ("code", "symbol"): _cmd_code_symbol,
    ("code", "read"): _cmd_code_read,
    ("code", "context"): _cmd_code_context,
    ("code", "doctor"): _cmd_code_doctor,
    ("code", "purge"): _cmd_code_purge,
    ("knowledge", "path"): _cmd_knowledge_path,
    ("rules", "lookup"): _cmd_rules_lookup,
    ("validate", None): _cmd_validate,
    ("report", "sign"): _cmd_report_sign,
    ("report", "verify"): _cmd_report_verify,
    ("collect", "event-log"): _cmd_collect_event_log,
    ("collect", "glue-job"): _cmd_collect_glue_job,
    ("collect", "cloudwatch"): _cmd_collect_cloudwatch,
    ("collect", "iceberg-metadata"): _cmd_collect_iceberg_metadata,
    ("collect", "athena-workgroup"): _cmd_collect_athena_workgroup,
    ("collect", "emr-cluster"): _cmd_collect_emr_cluster,
    ("collect", "emr-serverless"): _cmd_collect_emr_serverless,
    ("collect", "verify"): _cmd_collect_verify,
}


def _dispatch(args: argparse.Namespace) -> int:
    sub_action = (
        getattr(args, "analyze_target", None)
        or getattr(args, "case_action", None)
        or getattr(args, "funcval_action", None)
        or getattr(args, "runtime_action", None)
        or getattr(args, "code_action", None)
        or getattr(args, "knowledge_action", None)
        or getattr(args, "rules_action", None)
        or getattr(args, "report_action", None)
        or getattr(args, "collect_action", None)
        or getattr(args, "migrate_action", None)
        or getattr(args, "glue_action", None)
        or getattr(args, "iceberg_action", None)
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
