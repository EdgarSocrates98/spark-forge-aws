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

from sparkforge.adapters import _core

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        __version__ = _pkg_version("sparkforge-aws")
    except PackageNotFoundError:
        __version__ = "0.4.0"
except ImportError:  # pragma: no cover -- importlib.metadata sempre existe em py>=3.10
    __version__ = "0.4.0"


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

    # judge ------------------------------------------------------------
    judge_p = sub.add_parser(
        "judge", help="Aplica o catalogo de regras versionado sobre facts ja extraidos."
    )
    judge_p.add_argument(
        "--facts", required=True, help="Arquivo de facts gerado por `analyze pyspark --out`."
    )
    judge_p.add_argument("--glue")
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
    open_p.add_argument("--spark")
    open_p.add_argument("--python")
    open_p.add_argument("--iceberg")
    open_p.add_argument("--athena")

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

    # runtime detect ----------------------------------------------------
    runtime_p = sub.add_parser(
        "runtime", help="Deteccao de runtime Glue/Spark/Python/Iceberg/Athena."
    )
    runtime_sub = runtime_p.add_subparsers(dest="runtime_action", required=True)
    detect_p = runtime_sub.add_parser(
        "detect", help="Deriva a matriz de runtime a partir de flags."
    )
    detect_p.add_argument("--glue")
    detect_p.add_argument("--spark")
    detect_p.add_argument("--python")
    detect_p.add_argument("--iceberg")
    detect_p.add_argument("--athena")

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


def _cmd_judge(args: argparse.Namespace) -> int:
    full = _core.judge_findings(
        facts_path=args.facts,
        glue=args.glue,
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
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
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


def _cmd_runtime_detect(args: argparse.Namespace) -> int:
    payload = _core.runtime_detect(
        glue=args.glue,
        spark=args.spark,
        python=args.python,
        iceberg=args.iceberg,
        athena=args.athena,
    )
    _print(payload)
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
        result = _core.validate_output(finding if isinstance(finding, dict) else {})
        for message in result["errors"]:
            errors.append(f"finding[{index}] ({rule_id}): {message}")

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    _print({"valid": True, "count": len(findings)})
    return 0


_DISPATCH = {
    ("analyze", "pyspark"): _cmd_analyze_pyspark,
    ("judge", None): _cmd_judge,
    ("case", "open"): _cmd_case_open,
    ("case", "get"): _cmd_case_get,
    ("case", "update"): _cmd_case_update,
    ("next-step", None): _cmd_next_step,
    ("resume", None): _cmd_resume,
    ("handoff", None): _cmd_handoff,
    ("runtime", "detect"): _cmd_runtime_detect,
    ("rules", "lookup"): _cmd_rules_lookup,
    ("validate", None): _cmd_validate,
}


def _dispatch(args: argparse.Namespace) -> int:
    sub_action = getattr(args, "analyze_target", None) or getattr(args, "case_action", None) or (
        getattr(args, "runtime_action", None) or getattr(args, "rules_action", None)
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
