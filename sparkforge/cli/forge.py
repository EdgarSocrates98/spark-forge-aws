"""Unified CLI for SparkForge AWS Data Platform Engineering Agent Factory."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sparkforge.adapters import _core
from sparkforge.databases.dynamodb import DynamoDBSpecialist
from sparkforge.databases.neptune import NeptuneSpecialist
from sparkforge.errors.matcher import DeterministicErrorMatcher
from sparkforge.iceberg.doctor import IcebergTableDoctor
from sparkforge.lakeformation.doctor import LakeFormationDoctor
from sparkforge.lakeformation.graph import LakeFormationPermissionGraph
from sparkforge.registry.loader import CanonicalRegistry
from sparkforge.spark.eventlog_analyzer import SparkEventLogAnalyzer
from sparkforge.spark.plan_profiler import SparkPlanProfiler
from sparkforge.streaming.kafka import KafkaMSKSpecialist
from sparkforge.streaming.kinesis import KinesisSpecialist
from sparkforge.terraform.plan_analyzer import TerraformPlanAnalyzer


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def cmd_doctor(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo)
    checks = {
        "python_version": sys.version.split()[0],
        "registry_valid": False,
        "skills_count": 0,
        "agents_count": 0,
        "error_signatures_count": 0,
        "platforms_supported": ["antigravity", "cursor", "claude", "devin", "windsurf", "copilot", "generic"],
        "status": "PASS",
    }

    registry = CanonicalRegistry(repo_root)
    registry.load_from_configs()
    checks["registry_valid"] = True
    checks["agents_count"] = len(registry.agents)
    checks["skills_count"] = len(registry.skills)

    matcher = DeterministicErrorMatcher()
    checks["error_signatures_count"] = len(matcher.signatures)

    _print(checks)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    repo_root = Path(".")
    registry = CanonicalRegistry(repo_root)
    registry.load_from_configs()
    target_type = args.type.lower()
    name = args.name

    if target_type == "agent":
        agent = registry.get_agent(name)
        if not agent:
            # Fallback search by id/name
            for a in registry.agents.values():
                if a.name == name or a.id == name:
                    agent = a
                    break
        if not agent:
            _print({"error": f"Agent '{name}' not found in registry."})
            return 1
        _print(agent.to_dict())
    elif target_type == "skill":
        skill = registry.get_skill(name)
        if not skill:
            for s in registry.skills.values():
                if s.name == name or s.id == name:
                    skill = s
                    break
        if not skill:
            _print({"error": f"Skill '{name}' not found in registry."})
            return 1
        _print(skill.to_dict())
    else:
        _print({"error": f"Unknown inspect target type: {target_type}"})
        return 1
    return 0


def cmd_errors_match(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        _print({"error": f"File not found: {args.path}"})
        return 1
    content = path.read_text(encoding="utf-8")
    matcher = DeterministicErrorMatcher()
    matches = matcher.match_log(content)
    _print([m.to_dict() for m in matches])
    return 0


def cmd_migrate_glue(args: argparse.Namespace) -> int:
    """Avalia a migracao com o catalogo de regras, nao com correspondencia de
    substring.

    Aceita DIRETORIO ou ARQUIVO. O diretorio e o caso que interessa: uma
    migracao de Glue e julgada sobre o conjunto de artefatos do job -- codigo,
    `requirements*.txt` e `.jar` --, e o analisador antigo, que lia um `.py`
    por vez, nao enxergava nem a dependencia pinada nem o binario que quebram
    a migracao. O `.py` continua aceito porque era a interface publicada deste
    comando, e quebra-la em silencio trocaria um defeito por outro.

    O par de versoes vem de quem chama, sempre. Ver o `required=True` no
    parser: o default `"5.1"` que morava aqui respondia sobre um alvo que
    ninguem declarou.
    """
    try:
        resultado = _core.migration_assess(
            args.path, source=args.from_runtime, target=args.to_runtime
        )
    except _core.AdapterError as exc:
        _print({"error": exc.message})
        return 1
    _print(resultado)
    return 0


def cmd_iceberg_doctor(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        _print({"error": f"File not found: {args.path}"})
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    doctor = IcebergTableDoctor()
    res = doctor.diagnose_table(data)
    _print(res.to_dict())
    return 0


def cmd_lakeformation_doctor(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        _print({"error": f"File not found: {args.path}"})
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    doctor = LakeFormationDoctor()
    res = doctor.diagnose_cross_account(data)
    _print(res.to_dict())
    return 0


def cmd_terraform_plan(args: argparse.Namespace) -> int:
    path = Path(args.plan_file)
    if not path.is_file():
        _print({"error": f"File not found: {args.plan_file}"})
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    analyzer = TerraformPlanAnalyzer()
    res = analyzer.analyze_plan_json(data)
    _print(res.to_dict())
    return 0


def cmd_spark_eventlog(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        _print({"error": f"File not found: {args.path}"})
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()
    analyzer = SparkEventLogAnalyzer()
    res = analyzer.analyze_event_log(lines)
    _print(res.to_dict())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge", description="SparkForge AWS Data Platform Engineering CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # forge doctor
    doc_p = sub.add_parser("doctor", help="Run factory health checks")
    doc_p.add_argument("--repo", default=".", help="Repository root path")

    # forge inspect
    insp_p = sub.add_parser("inspect", help="Inspect registry manifest")
    insp_p.add_argument("type", choices=["agent", "skill", "tool"])
    insp_p.add_argument("name", help="Name of agent or skill")

    # forge errors match
    err_p = sub.add_parser("errors", help="Error KB operations")
    err_sub = err_p.add_subparsers(dest="subcommand", required=True)
    err_m = err_sub.add_parser("match", help="Match log against error signatures")
    err_m.add_argument("path", help="Log or stacktrace file")

    # forge migrate glue
    mig_p = sub.add_parser("migrate", help="Migration intelligence")
    mig_sub = mig_p.add_subparsers(dest="subcommand", required=True)
    mig_g = mig_sub.add_parser("glue", help="Analyze Glue migration")
    mig_g.add_argument("path", help="Diretorio do job (ou um arquivo .py)")
    # Sem default, os dois. O `--to` default `"5.1"` que ficava aqui devolvia
    # um veredito sobre um alvo que ninguem pediu.
    mig_g.add_argument("--from", dest="from_runtime", required=True)
    mig_g.add_argument("--to", dest="to_runtime", required=True)

    # forge iceberg doctor
    ice_p = sub.add_parser("iceberg", help="Iceberg intelligence")
    ice_sub = ice_p.add_subparsers(dest="subcommand", required=True)
    ice_d = ice_sub.add_parser("doctor", help="Diagnose Iceberg table health")
    ice_d.add_argument("path", help="Table metadata JSON dump")

    # forge lakeformation diagnose-cross-account
    lf_p = sub.add_parser("lakeformation", help="Lake Formation intelligence")
    lf_sub = lf_p.add_subparsers(dest="subcommand", required=True)
    lf_c = lf_sub.add_parser("diagnose-cross-account", help="Diagnose cross-account setup")
    lf_c.add_argument("path", help="Lake Formation config JSON dump")

    # forge terraform analyze-plan
    tf_p = sub.add_parser("terraform", help="Terraform plan risk intelligence")
    tf_sub = tf_p.add_subparsers(dest="subcommand", required=True)
    tf_a = tf_sub.add_parser("analyze-plan", help="Analyze terraform plan JSON")
    tf_a.add_argument("plan_file", help="Terraform plan JSON file")

    # forge spark analyze-eventlog
    sp_p = sub.add_parser("spark", help="Spark performance intelligence")
    sp_sub = sp_p.add_subparsers(dest="subcommand", required=True)
    sp_e = sp_sub.add_parser("analyze-eventlog", help="Analyze spark eventlog")
    sp_e.add_argument("path", help="Spark eventlog .jsonl file")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return cmd_doctor(args)
    elif args.command == "inspect":
        return cmd_inspect(args)
    elif args.command == "errors" and args.subcommand == "match":
        return cmd_errors_match(args)
    elif args.command == "migrate" and args.subcommand == "glue":
        return cmd_migrate_glue(args)
    elif args.command == "iceberg" and args.subcommand == "doctor":
        return cmd_iceberg_doctor(args)
    elif args.command == "lakeformation" and args.subcommand == "diagnose-cross-account":
        return cmd_lakeformation_doctor(args)
    elif args.command == "terraform" and args.subcommand == "analyze-plan":
        return cmd_terraform_plan(args)
    elif args.command == "spark" and args.subcommand == "analyze-eventlog":
        return cmd_spark_eventlog(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
