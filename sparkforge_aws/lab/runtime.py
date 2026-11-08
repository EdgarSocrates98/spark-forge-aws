"""Guarded runtime plans shared by Compose and Testcontainers backends."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import LabContractError, VersionRegistry, load_version_registry
from .generators import generate_records, write_jsonl
from .scenario import ScenarioAction, ScenarioSpec

COMPOSE_PROFILES = {
    "core": "lakehouse",
    "spark": "batch",
    "kafka": "streaming",
    "streaming": "streaming",
    "flink": "streaming",
    "lakehouse": "lakehouse",
    "cdc": "cdc",
    "polaris": "lakehouse",
    "observability": "observability",
    "chaos": "chaos",
    "full": "full",
}

_IMAGE_ENV = {
    "kafka": "LAB_KAFKA_IMAGE",
    "spark": "LAB_SPARK_IMAGE",
    "flink": "LAB_FLINK_IMAGE",
    "iceberg_rest": "LAB_ICEBERG_REST_IMAGE",
    "polaris": "LAB_POLARIS_IMAGE",
    "postgres": "LAB_POSTGRES_IMAGE",
    "debezium": "LAB_DEBEZIUM_IMAGE",
    "minio": "LAB_MINIO_IMAGE",
    "prometheus": "LAB_PROMETHEUS_IMAGE",
    "otel_collector": "LAB_OTEL_IMAGE",
    "toxiproxy": "LAB_TOXIPROXY_IMAGE",
    "grafana": "LAB_GRAFANA_IMAGE",
    "trino": "LAB_TRINO_IMAGE",
}
_CLOUD_ENV_KEYS = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
}


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    scenario_id: str
    backend: str
    profile: str
    mode: str
    project_name: str
    actions: tuple[ScenarioAction, ...]
    command: tuple[str, ...]
    requires_confirmation: bool
    execute: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario_id,
            "backend": self.backend,
            "profile": self.profile,
            "mode": self.mode,
            "project_name": self.project_name,
            "actions": [action.to_dict() for action in self.actions],
            "command": list(self.command),
            "requires_confirmation": self.requires_confirmation,
            "execute": self.execute,
            "mutated": self.execute,
        }


def build_runtime_plan(
    scenario: ScenarioSpec,
    *,
    backend: str = "compose",
    execute: bool = False,
    confirm: bool = False,
) -> RuntimePlan:
    if backend not in {"compose", "testcontainers"}:
        raise LabContractError(f"unsupported lab runtime backend: {backend}")
    if execute and not confirm:
        raise LabContractError("runtime execution requires --execute and --confirm")
    project_name = _project_name(scenario.slug)
    profile = COMPOSE_PROFILES[scenario.resource.profile]
    if backend == "compose":
        command = (
            "docker",
            "compose",
            "--project-name",
            project_name,
            "--profile",
            profile,
            "-f",
            "labs/forge-lab/compose.yaml",
            "up",
            "--detach",
        )
    else:
        command = (
            "python",
            "-m",
            "sparkforge_aws.lab.testcontainers_backend",
            "--scenario",
            scenario.scenario_id,
            "--profile",
            scenario.resource.profile,
        )
    return RuntimePlan(
        scenario_id=scenario.scenario_id,
        backend=backend,
        profile=profile,
        mode=scenario.resource.mode,
        project_name=project_name,
        actions=scenario.compile_actions(),
        command=command,
        requires_confirmation=True,
        execute=execute,
    )


def build_lifecycle_command(
    action: str, *, project_name: str, profile: str = "", service: str = ""
) -> tuple[str, ...]:
    if action not in {"up", "down", "status", "shell", "gc"}:
        raise LabContractError(f"unsupported lab lifecycle action: {action}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", project_name):
        raise LabContractError("invalid lab project name")
    base = [
        "docker",
        "compose",
        "--project-name",
        project_name,
        "-f",
        "labs/forge-lab/compose.yaml",
    ]
    if action == "up":
        if not profile:
            raise LabContractError("lab up requires a profile")
        return tuple(base + ["--profile", profile, "up", "--detach"])
    if action == "down":
        if profile:
            base += ["--profile", profile]
        return tuple(base + ["down", "--remove-orphans"])
    if action == "status":
        return tuple(base + ["ps"])
    if action == "shell":
        if not service:
            raise LabContractError("lab shell requires a service")
        return tuple(base + ["exec", service, "sh"])
    return tuple(base + ["config", "--services"])


def build_runtime_environment(
    repo: str | Path, *, registry_path: str | Path = "lab/versions.yaml"
) -> tuple[dict[str, str], VersionRegistry]:
    """Resolve Compose image variables from the checked-in version registry.

    Compose interpolates every service before it filters profiles, so all image
    variables are supplied even for a small profile.  Credentials are local,
    ephemeral defaults and can be overridden by the operator environment.
    Nothing is written to disk and no cloud credentials are copied.
    """

    root = Path(repo).expanduser().resolve()
    registry = load_version_registry(root / registry_path)
    environment = {key: value for key, value in os.environ.items()}
    for key in _CLOUD_ENV_KEYS:
        environment.pop(key, None)
    for component, variable in _IMAGE_ENV.items():
        entry = registry.component(component)
        image = str(entry["image"])
        tag = str(entry["tag"])
        digest = entry.get("digest")
        environment[variable] = f"{image}@{digest}" if digest else f"{image}:{tag}"
    environment.setdefault("LAB_MINIO_ROOT_USER", "forge-lab")
    environment.setdefault("LAB_MINIO_ROOT_PASSWORD", "forge-lab-local-only")
    environment.setdefault("LAB_POSTGRES_PASSWORD", "forge-lab-local-only")
    return environment, registry


def execute_runtime_command(
    command: tuple[str, ...],
    *,
    repo: str | Path,
    registry_path: str | Path = "lab/versions.yaml",
    timeout: float = 300.0,
    probe_service: str = "",
) -> dict[str, Any]:
    """Execute an allow-listed Compose command and return bounded evidence.

    The command must have been produced by this module.  It is passed as an
    argv list with ``shell=False`` so user input cannot become a shell script.
    A successful ``up`` is only reported as live after Compose reports running
    services; Spark scenarios additionally run ``spark-submit --version``.
    """

    if not command or command[:2] != ("docker", "compose"):
        raise LabContractError("runtime executor accepts only docker compose commands")
    docker = shutil.which("docker")
    base: dict[str, Any] = {"command": list(command), "backend": "compose", "mutated": True}
    if not docker:
        return {
            **base,
            "status": "INFRA_FAILURE",
            "classification": "INFRA_FAILURE",
            "reason": "docker executable unavailable",
        }
    try:
        environment, registry = build_runtime_environment(repo, registry_path=registry_path)
    except LabContractError as exc:
        return {
            **base,
            "status": "INVALID_SCENARIO",
            "classification": "INVALID_SCENARIO",
            "reason": str(exc),
        }
    root = Path(repo).expanduser().resolve()
    try:
        completed = subprocess.run(  # noqa: S603 - command is produced by this module
            list(command),
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            **base,
            "status": "INFRA_FAILURE",
            "classification": "INFRA_FAILURE",
            "reason": f"docker compose timed out after {timeout:g}s",
            "stdout": _output(exc.stdout),
            "stderr": _output(exc.stderr),
        }
    if completed.returncode != 0:
        return {
            **base,
            "status": "INFRA_FAILURE",
            "classification": "INFRA_FAILURE",
            "reason": "docker compose returned a non-zero exit code",
            "exit_code": completed.returncode,
            "stdout": _output(completed.stdout),
            "stderr": _output(completed.stderr),
        }

    result: dict[str, Any] = {
        **base,
        "status": "EXECUTED",
        "classification": "PASS",
        "exit_code": completed.returncode,
        "stdout": _output(completed.stdout),
        "stderr": _output(completed.stderr),
        "registry": registry.to_dict(),
    }
    if "up" not in command:
        result["status"] = "STOPPED" if "down" in command else "EXECUTED"
        return result

    compose_prefix = command[: command.index("up")]
    status_command = tuple((*compose_prefix, "ps", "--format", "json"))
    status_run = _run_process(status_command, root, environment, timeout)
    result["status_command"] = list(status_command)
    result["services"] = _parse_compose_ps(status_run.get("stdout", ""))
    if status_run.get("returncode") != 0 or not _all_services_running(result["services"]):
        result.update(
            {
                "status": "INFRA_FAILURE",
                "classification": "INFRA_FAILURE",
                "reason": "Compose started without a readable running-service report",
                "status_stderr": status_run.get("stderr", ""),
            }
        )
        return result

    result["image_digests"] = _resolve_digests(
        registry, root, environment, timeout=timeout
    )
    if probe_service:
        probe_command = tuple(
            (
                *compose_prefix,
                "exec",
                "-T",
                probe_service,
                "/opt/spark/bin/spark-submit",
                "--version",
            )
        )
        probe = _run_process(probe_command, root, environment, timeout)
        result["engine_probe"] = {
            "command": list(probe_command),
            "service": probe_service,
            "exit_code": probe.get("returncode"),
            "stdout": probe.get("stdout", ""),
            "stderr": probe.get("stderr", ""),
            "status": "PASS" if probe.get("returncode") == 0 else "FAIL",
        }
        if probe.get("returncode") != 0:
            result.update(
                {
                    "status": "INFRA_FAILURE",
                    "classification": "INFRA_FAILURE",
                    "reason": "Spark engine probe failed inside the live container",
                }
            )
            return result
    result["status"] = "LIVE_STARTED"
    result["fidelity"] = {
        "tier": "L1",
        "name": "real_local_engine",
        "scenario_actions_executed": False,
        "does_not_prove": [
            "scenario oracle pass",
            "cloud-provider behavior",
            "production-scale performance",
        ],
    }
    return result


def execute_scenario(
    scenario: ScenarioSpec,
    plan: RuntimePlan,
    *,
    repo: str | Path,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Execute the implemented local golden path and preserve its receipt.

    LAB-002 is the first real L1 scenario: it generates a bounded dataset,
    submits a deterministic PySpark job to the live Compose service, copies
    the event log out, runs the existing analyzer and rule judge, compares the
    observed evidence with the independent oracle, and finally stops the lab
    while preserving the run directory.
    """

    if plan.backend != "compose":
        return {
            "status": "UNRESOLVED",
            "classification": "UNRESOLVED",
            "reason": "live scenario execution is currently implemented for Compose only",
            "scenario_actions_executed": False,
        }
    probe_service = (
        "spark" if scenario.resource.profile in {"spark", "streaming", "lakehouse"} else ""
    )
    runtime = execute_runtime_command(
        plan.command,
        repo=repo,
        timeout=timeout,
        probe_service=probe_service,
    )
    if runtime.get("status") != "LIVE_STARTED":
        runtime["scenario_actions_executed"] = False
        return runtime
    if scenario.scenario_id != "LAB-002":
        runtime.update(
            {
                "status": "LIVE_STARTED",
                "scenario_actions_executed": False,
                "reason": "live engine bootstrap is proven; this scenario has no executor yet",
            }
        )
        return runtime

    from .evidence import compare_oracle, create_run, finalize_receipt, verify_receipt
    from .oracle import ExpectedOracle

    root = Path(repo).expanduser().resolve()
    registry = runtime.get("registry", {})
    run = create_run(
        root,
        scenario,
        seed=int(scenario.dataset["seed"]),
        environment={
            "backend": "docker-compose",
            "fidelity": "L1",
            "scenario_actions": "live_local_spark",
        },
        versions={"registry": registry, "image_digests": runtime.get("image_digests", {})},
    )
    input_path = run / "input" / "dataset.jsonl"
    write_jsonl(
        input_path,
        generate_records(
            str(scenario.dataset["schema"]),
            seed=int(scenario.dataset["seed"]),
            record_count=int(scenario.dataset["records"]),
            key_cardinality=int(scenario.dataset["key_cardinality"]),
            skew=float(scenario.dataset["skew"]),
            late_event_ratio=float(scenario.dataset.get("late_event_ratio", 0)),
            duplicate_ratio=float(scenario.dataset.get("duplicate_ratio", 0)),
        ),
    )
    compose_prefix = plan.command[: plan.command.index("up")]
    run_token = run.name
    remote_job = f"/tmp/forge-lab-{run_token}.py"  # noqa: S108 - unique in isolated container
    remote_output = f"/tmp/forge-lab-{run_token}.json"  # noqa: S108 - unique in isolated container
    remote_events = f"/tmp/forge-lab-events-{run_token}"  # noqa: S108 - unique in isolated container
    job_source = Path(__file__).parent / "jobs" / "skew.py"
    environment, _ = build_runtime_environment(root)
    copy_job = _run_process(
        tuple((*compose_prefix, "cp", str(job_source), f"spark:{remote_job}")),
        root,
        environment,
        timeout,
    )
    if copy_job.get("returncode") != 0:
        return _scenario_failure(
            runtime,
            run,
            copy_job,
            "failed to copy the Spark scenario job",
            repo=root,
            project_name=plan.project_name,
            timeout=timeout,
        )

    partitions = int(scenario.setup.get("spark", {}).get("partitions", 4))
    submit_command = tuple(
        (
            *compose_prefix,
            "exec",
            "-T",
            "spark",
            "/opt/spark/bin/spark-submit",
            "--master",
            "local[2]",
            remote_job,
            "--output",
            remote_output,
            "--event-dir",
            remote_events,
            "--records",
            str(scenario.dataset["records"]),
            "--cardinality",
            str(scenario.dataset["key_cardinality"]),
            "--skew",
            str(scenario.dataset["skew"]),
            "--partitions",
            str(partitions),
            "--seed",
            str(scenario.dataset["seed"]),
        )
    )
    submitted = _run_process(submit_command, root, environment, timeout)
    (run / "logs" / "spark-submit.txt").write_text(
        json.dumps(submitted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if submitted.get("returncode") != 0:
        return _scenario_failure(
            runtime,
            run,
            submitted,
            "Spark scenario job failed",
            repo=root,
            project_name=plan.project_name,
            timeout=timeout,
        )

    observed_path = run / "metrics" / "observed.json"
    copied_observed = _run_process(
        tuple((*compose_prefix, "cp", f"spark:{remote_output}", str(observed_path))),
        root,
        environment,
        timeout,
    )
    if copied_observed.get("returncode") != 0 or not observed_path.is_file():
        return _scenario_failure(
            runtime,
            run,
            copied_observed,
            "Spark observation artifact was not copied",
            repo=root,
            project_name=plan.project_name,
            timeout=timeout,
        )
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    if not isinstance(observed, dict) or not isinstance(observed.get("facts"), list):
        return _scenario_failure(
            runtime,
            run,
            {},
            "Spark observation artifact has invalid shape",
            repo=root,
            project_name=plan.project_name,
            timeout=timeout,
        )

    event_destination = run / "spark" / "event-log"
    event_destination.mkdir(parents=True, exist_ok=True)
    copied_events = _run_process(
        tuple((*compose_prefix, "cp", f"spark:{remote_events}", str(event_destination))),
        root,
        environment,
        timeout,
    )
    event_files = sorted(
        path
        for path in event_destination.rglob("*")
        if path.is_file() and not path.name.endswith(".crc") and path.stat().st_size > 0
    )
    if copied_events.get("returncode") != 0 or not event_files:
        return _scenario_failure(
            runtime,
            run,
            copied_events,
            "Spark event log was not copied",
            repo=root,
            project_name=plan.project_name,
            timeout=timeout,
        )

    from sparkforge_aws.adapters import _core

    event_files.sort(key=lambda path: path.stat().st_size, reverse=True)
    event_analysis = _core.analyze_event_log(str(event_files[0]), kind=None, limit=None)
    event_facts = list(event_analysis.get("items", []))
    facts = [*event_facts, *observed["facts"]]
    facts_path = run / "facts" / "event-log.json"
    facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    judged = _core.judge_findings(facts_path=str(facts_path), limit=None)
    findings = list(judged.get("items", []))
    oracle = ExpectedOracle.from_scenario(scenario)
    unresolved = event_analysis.get("unresolved", [])
    if not isinstance(unresolved, list):
        unresolved = [f"event_log_unresolved:{unresolved}"] if unresolved else []
    oracle_result = compare_oracle(
        oracle,
        facts=facts,
        findings=findings,
        unresolved=unresolved,
    )
    receipt = finalize_receipt(run, oracle_result, facts=facts, findings=findings)
    cleanup = execute_runtime_command(
        build_lifecycle_command("down", project_name=plan.project_name, profile="*"),
        repo=root,
        timeout=timeout,
    )
    return {
        **runtime,
        "status": oracle_result.classification,
        "classification": oracle_result.classification,
        "runtime_status": "LIVE_STARTED",
        "scenario_actions_executed": True,
        "run": run.as_posix(),
        "oracle": oracle_result.to_dict(),
        "receipt": {
            "path": (run / "receipt.json").as_posix(),
            "verification": verify_receipt(run / "receipt.json"),
            "sha256": receipt["receipt_sha256"],
        },
        "cleanup": cleanup,
        "fidelity": {
            "tier": "L1",
            "name": "real_local_engine",
            "scenario_actions_executed": True,
            "does_not_prove": [
                "cloud-provider behavior",
                "production-scale performance",
                "L3 AWS identity or authorization",
            ],
        },
    }


def _scenario_failure(
    runtime: dict[str, Any],
    run: Path,
    evidence: dict[str, Any],
    reason: str,
    *,
    repo: Path,
    project_name: str,
    timeout: float,
) -> dict[str, Any]:
    cleanup = execute_runtime_command(
        build_lifecycle_command("down", project_name=project_name, profile="*"),
        repo=repo,
        timeout=timeout,
    )
    return {
        **runtime,
        "status": "INFRA_FAILURE",
        "classification": "INFRA_FAILURE",
        "reason": reason,
        "scenario_actions_executed": False,
        "run": run.as_posix(),
        "evidence": evidence,
        "cleanup": cleanup,
    }


def _run_process(
    command: tuple[str, ...], root: Path, environment: dict[str, str], timeout: float
) -> dict[str, Any]:
    try:
        executable = shutil.which(command[0]) or command[0]
        completed = subprocess.run(  # noqa: S603 - command is produced by this module
            [executable, *command[1:]],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {"returncode": None, "stdout": _output(exc.stdout), "stderr": _output(exc.stderr)}
    return {
        "returncode": completed.returncode,
        "stdout": _output(completed.stdout),
        "stderr": _output(completed.stderr),
    }


def _parse_compose_ps(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            rows.append(value)
    return rows


def _all_services_running(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    for row in rows:
        state = str(row.get("State") or row.get("Status") or "").lower()
        if "running" not in state and not state.startswith("up"):
            return False
    return True


def _resolve_digests(
    registry: VersionRegistry, root: Path, environment: dict[str, str], *, timeout: float
) -> dict[str, str]:
    digests: dict[str, str] = {}
    for component, _entry in registry.defaults.items():
        variable = _IMAGE_ENV.get(component)
        if not variable:
            continue
        reference = environment[variable]
        inspect = _run_process(
            ("docker", "image", "inspect", reference, "--format", "{{json .RepoDigests}}"),
            root,
            environment,
            min(timeout, 30.0),
        )
        if inspect.get("returncode") != 0:
            continue
        try:
            values = json.loads(inspect.get("stdout", ""))
        except json.JSONDecodeError:
            continue
        if isinstance(values, list) and values:
            digests[component] = str(values[0]).split("@", 1)[-1]
    return digests


def _output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[-12000:]
    return str(value)[-12000:]


def guard_mutation(*, execute: bool, confirm: bool, target: str = "local") -> None:
    if target not in {"local", "aws"}:
        raise LabContractError(f"unsupported lab target: {target}")
    if execute and not confirm:
        raise LabContractError("mutating Lab action refused: --confirm is required")
    if target == "aws" and execute:
        raise LabContractError("AWS Lab execution is a separate explicit validation tier")


def _project_name(slug: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return f"forge-lab-{value[:48]}"


__all__ = [
    "COMPOSE_PROFILES",
    "RuntimePlan",
    "build_lifecycle_command",
    "build_runtime_environment",
    "build_runtime_plan",
    "execute_runtime_command",
    "execute_scenario",
    "guard_mutation",
]
