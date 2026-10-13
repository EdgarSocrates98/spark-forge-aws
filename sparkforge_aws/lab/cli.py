"""CLI-first Forge Lab lifecycle and inspection operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compatibility import build_equivalence_plan
from .contract import LabContractError, load_version_registry
from .doctor import PROFILE_REQUIREMENTS, run_doctor
from .evidence import promote_fixture, verify_receipt
from .runtime import build_lifecycle_command, build_runtime_plan, guard_mutation
from .scenario import load_scenario_suite


def dispatch(args: Any) -> dict[str, Any]:
    repo = Path(args.repo).expanduser().resolve()
    if args.lab_action == "doctor":
        return run_doctor(repo).to_dict()
    if args.lab_action == "profiles":
        return {
            "profiles": [{"name": name, **value} for name, value in PROFILE_REQUIREMENTS.items()]
        }
    if args.lab_action == "verify":
        registry = load_version_registry(repo / "lab" / "versions.yaml")
        suite = load_scenario_suite(repo / "lab" / "scenarios" / "golden.yaml")
        for scenario in suite.scenarios:
            scenario.compile_actions()
        required = (
            repo / "lab" / "contracts" / "scenario-v1.schema.json",
            repo / "lab" / "contracts" / "run-v1.schema.json",
            repo / "lab" / "contracts" / "receipt-v1.schema.json",
            repo / "lab" / "probes" / "catalog.yaml",
        )
        missing = [path.as_posix() for path in required if not path.is_file()]
        return {
            "valid": not missing,
            "registry_components": len(registry.defaults),
            "scenario_count": len(suite.scenarios),
            "action_count": sum(len(scenario.compile_actions()) for scenario in suite.scenarios),
            "missing": missing,
            "provider_tokens": "unresolved_without_host_transcript",
        }
    suite = load_scenario_suite(repo / "lab" / "scenarios" / "golden.yaml")
    if args.lab_action == "scenarios":
        return {
            "suite": suite.fingerprint,
            "scenario_count": len(suite.scenarios),
            "scenarios": [
                {
                    "id": item.scenario_id,
                    "slug": item.slug,
                    "title": item.title,
                    "fingerprint": item.fingerprint,
                    "fidelity": item.fidelity.to_dict(),
                }
                for item in suite.scenarios
            ],
        }
    if args.lab_action in {"describe", "plan", "run"}:
        scenario = suite.by_id(args.scenario)
        if args.lab_action == "describe":
            return scenario.to_dict()
        plan = build_runtime_plan(
            scenario, backend=args.backend, execute=args.execute, confirm=args.confirm
        )
        payload = {
            "plan": plan.to_dict(),
            "equivalence": build_equivalence_plan(
                table="forge_lab.synthetic", catalog="polaris"
            ).to_dict(),
        }
        if args.lab_action == "run":
            if args.execute:
                guard_mutation(execute=True, confirm=args.confirm)
                payload["execution"] = {
                    "status": "unresolved",
                    "reason": "runtime execution adapter must be enabled on host",
                }
            else:
                payload["execution"] = {
                    "status": "planned",
                    "reason": "dry-run default; use --execute --confirm on an operator host",
                }
        return payload
    if args.lab_action == "inspect":
        return _inspect(Path(args.path))
    if args.lab_action == "analyze":
        return {
            "run": str(Path(args.path).expanduser().resolve()),
            "status": "unresolved",
            "reason": "analyze consumes captured artifacts; no provider is called by CLI plan",
        }
    if args.lab_action == "compare":
        return _compare(Path(args.before), Path(args.after))
    if args.lab_action == "promote-fixture":
        if not args.reviewed:
            raise LabContractError("fixture promotion requires --reviewed")
        return promote_fixture(args.run, args.destination, reviewed=True)
    if args.lab_action == "reproduce":
        receipt = Path(args.receipt).expanduser().resolve()
        verification = verify_receipt(receipt)
        return {
            "receipt": receipt.as_posix(),
            "verification": verification,
            "reproducible": verification["valid"],
            "execution": "operator_confirmation_required",
        }
    if args.lab_action in {"up", "down", "shell", "gc"}:
        guard_mutation(execute=args.execute, confirm=args.confirm)
        if args.lab_action == "up":
            command = build_lifecycle_command("up", project_name=args.project, profile=args.profile)
        elif args.lab_action == "down":
            command = build_lifecycle_command("down", project_name=args.project)
        elif args.lab_action == "shell":
            command = build_lifecycle_command(
                "shell", project_name=args.project, service=args.service
            )
        else:
            command = build_lifecycle_command("gc", project_name=args.project)
        return {
            "action": args.lab_action,
            "command": list(command),
            "execute": args.execute,
            "status": "planned" if not args.execute else "unresolved_host_execution",
        }
    raise LabContractError(f"unknown lab action: {args.lab_action}")


def _inspect(path: Path) -> dict[str, Any]:
    if path.is_dir():
        run_json = path / "run.json"
        receipt = path / "receipt.json"
    else:
        run_json = path.parent / "run.json"
        receipt = path
    if not run_json.is_file():
        raise LabContractError(f"run.json not found: {run_json}")
    payload = {"run": json.loads(run_json.read_text(encoding="utf-8"))}
    if receipt.is_file():
        payload["receipt"] = json.loads(receipt.read_text(encoding="utf-8"))
        payload["receipt_verification"] = verify_receipt(receipt)
    return payload


def _compare(before: Path, after: Path) -> dict[str, Any]:
    left = _inspect(before)
    right = _inspect(after)
    return {
        "before": left.get("run", {}),
        "after": right.get("run", {}),
        "status": "declared_comparison",
        "performance_claim": False,
    }


__all__ = ["dispatch"]
