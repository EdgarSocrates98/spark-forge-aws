"""Offline adapters for canonical evaluation evidence bundles."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge_aws.evals.evidence import (
    EvaluationEvidenceBundle,
    EvidenceBundleError,
    canonical_digest,
)


class EvidenceAdapterError(EvidenceBundleError):
    """Named file and authorized-command adapter failure."""


@dataclass(frozen=True, slots=True)
class ExternalCommandIdentity:
    """Canonical identity of one authorized external producer."""

    command_id: str
    executable_sha256: str
    artifact_sha256: str | None
    args: tuple[str, ...]
    cwd: str
    timeout_seconds: float
    max_output_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "executable_sha256": self.executable_sha256,
            "artifact_sha256": self.artifact_sha256,
            "args": list(self.args),
            "cwd": self.cwd,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
        }

    @property
    def sha256(self) -> str:
        return canonical_digest(self.to_dict())


def _confined_path(repo: Path, value: Path | str) -> Path:
    target = Path(value)
    if target.is_absolute():
        resolved = target.resolve()
    else:
        resolved = (repo / target).resolve()
    if repo != resolved and repo not in resolved.parents:
        raise EvidenceAdapterError("evidence_adapter_path_escape")
    return resolved


class BundleFileAdapter:
    """Load JSON/YAML evidence from a repository-confined path."""

    def __init__(self, repo: Path | str = ".") -> None:
        self.repo = Path(repo).expanduser().resolve()

    def load(self, path: Path | str) -> EvaluationEvidenceBundle:
        target = _confined_path(self.repo, path)
        try:
            raw_text = target.read_text(encoding="utf-8")
        except OSError as exc:
            raise EvidenceAdapterError(f"evidence_bundle_unreadable:{target}") from exc
        try:
            raw = (
                json.loads(raw_text)
                if target.suffix.lower() == ".json"
                else yaml.safe_load(raw_text)
            )
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise EvidenceAdapterError(f"evidence_bundle_invalid:syntax:{target}") from exc
        try:
            return EvaluationEvidenceBundle.from_mapping(raw)
        except EvidenceBundleError:
            raise

    read = load


class AuthorizedCommandAdapter:
    """Run one configured executable and validate its JSON bundle output."""

    def __init__(
        self,
        commands: Mapping[str, Any] | None = None,
        *,
        repo: Path | str = ".",
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 1_048_576,
    ) -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.commands = dict(commands or {})
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def run(
        self,
        command_id: str,
        *,
        input_mapping: Mapping[str, Any] | None = None,
        argv: Sequence[str] = (),
    ) -> EvaluationEvidenceBundle:
        if command_id not in self.commands:
            raise EvidenceAdapterError(f"external_command_not_authorized:{command_id}")
        identity = self.identity(command_id)
        spec = self.commands[command_id]
        (
            executable,
            configured_args,
            _declared_sha256,
            _artifact,
            _artifact_sha256,
            timeout,
            output_limit,
        ) = self._spec(spec)
        if argv:
            raise EvidenceAdapterError("external_command_identity_mismatch:runtime_args")
        command = (executable, *configured_args)
        executable_path = Path(executable).expanduser().resolve()
        if not executable_path.is_file():
            raise EvidenceAdapterError(f"external_command_not_found:{executable_path}")
        temp_dir = self.repo / ".sparkforge_aws" / "evidence-input"
        temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_dir) as run_dir:
            input_path = Path(run_dir) / "input.json"
            stdout_path = Path(run_dir) / "stdout.bin"
            stderr_path = Path(run_dir) / "stderr.bin"
            input_path.write_text(
                json.dumps(dict(input_mapping or {}), ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                process = subprocess.Popen(  # noqa: S603
                    (*command, "--input", str(input_path)),
                    cwd=self.repo,
                    env={"PATH": str(executable_path.parent), "PYTHONIOENCODING": "utf-8"},
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                )
                deadline = time.monotonic() + timeout
                failure: str | None = None
                while process.poll() is None:
                    if (
                        stdout_path.stat().st_size > output_limit
                        or stderr_path.stat().st_size > output_limit
                    ):
                        process.kill()
                        process.wait()
                        time.sleep(0.05)
                        failure = "external_command_output_too_large"
                        break
                    if time.monotonic() >= deadline:
                        process.kill()
                        process.wait()
                        time.sleep(0.05)
                        failure = "external_command_timeout"
                        break
                    time.sleep(0.01)
                returncode = process.returncode
            if failure is not None:
                raise EvidenceAdapterError(failure)
            if (
                stdout_path.stat().st_size > output_limit
                or stderr_path.stat().st_size > output_limit
            ):
                raise EvidenceAdapterError("external_command_output_too_large")
            stdout_bytes = stdout_path.read_bytes()
            if returncode != 0:
                raise EvidenceAdapterError(f"external_command_failed:exit_{returncode}")
        try:
            raw = json.loads(stdout_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceAdapterError("external_command_invalid_output:json") from exc
        if not isinstance(raw, Mapping):
            raise EvidenceAdapterError("external_command_invalid_output:object")
        bundle = EvaluationEvidenceBundle.from_mapping(raw)
        execution = dict(bundle.execution)
        execution["command_identity_sha256"] = identity.sha256
        producer = execution.get("producer_identity")
        if isinstance(producer, Mapping):
            producer_identity = dict(producer)
        else:
            producer_identity = {"declared_identity": producer}
        producer_identity["command_id"] = command_id
        producer_identity["command_identity_sha256"] = identity.sha256
        execution["producer_identity"] = producer_identity
        body = bundle.to_dict()
        body["execution"] = execution
        body.pop("bundle_id", None)
        return EvaluationEvidenceBundle.from_mapping(body)

    execute = run

    def identity(self, command_id: str) -> ExternalCommandIdentity:
        if command_id not in self.commands:
            raise EvidenceAdapterError(f"external_command_not_authorized:{command_id}")
        spec = self.commands[command_id]
        (
            executable,
            configured_args,
            declared_sha256,
            artifact,
            artifact_sha256,
            timeout,
            output_limit,
        ) = self._spec(spec)
        executable_path = Path(executable).expanduser().resolve()
        if not executable_path.is_file():
            raise EvidenceAdapterError(f"external_command_not_found:{executable_path}")
        if not declared_sha256:
            raise EvidenceAdapterError("external_command_identity_missing:executable")
        actual = hashlib.sha256(executable_path.read_bytes()).hexdigest()
        if actual != declared_sha256.removeprefix("sha256:"):
            raise EvidenceAdapterError("external_command_executable_digest_mismatch")
        file_args = self._fixed_file_args(configured_args)
        artifact_path = (
            _confined_path(self.repo, artifact) if artifact is not None else None
        )
        if file_args and artifact_path is None:
            raise EvidenceAdapterError(
                "external_command_identity_missing:artifact_declaration"
            )
        if artifact_path is not None and file_args and artifact_path not in file_args:
            raise EvidenceAdapterError("external_command_artifact_not_in_args")
        actual_artifact: str | None = None
        if artifact_path is not None:
            if not artifact_path.is_file():
                raise EvidenceAdapterError("external_command_artifact_not_found")
            if not artifact_sha256:
                raise EvidenceAdapterError("external_command_identity_missing:artifact")
            actual_artifact = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_artifact != artifact_sha256.removeprefix("sha256:"):
                raise EvidenceAdapterError("external_command_artifact_digest_mismatch")
        return ExternalCommandIdentity(
            command_id=command_id,
            executable_sha256=actual,
            artifact_sha256=actual_artifact,
            args=configured_args,
            cwd=".",
            timeout_seconds=timeout,
            max_output_bytes=output_limit,
        )

    def _fixed_file_args(self, args: Sequence[str]) -> tuple[Path, ...]:
        files: list[Path] = []
        for value in args:
            candidate = Path(value).expanduser()
            resolved = (candidate if candidate.is_absolute() else self.repo / candidate).resolve()
            if resolved.is_file():
                files.append(_confined_path(self.repo, resolved))
        return tuple(files)

    def _spec(
        self, value: Any
    ) -> tuple[str, tuple[str, ...], str | None, str | None, str | None, float, int]:
        if not isinstance(value, Mapping):
            raise EvidenceAdapterError("external_command_identity_missing:spec")
        executable = value.get("executable")
        args = value.get("args", ())
        sha256 = value.get("sha256") or value.get("executable_sha256")
        artifact = value.get("artifact") or value.get("script")
        artifact_sha256 = value.get("artifact_sha256") or value.get("script_sha256")
        timeout = value.get("timeout_seconds", self.timeout_seconds)
        output_limit = value.get("max_output_bytes", self.max_output_bytes)
        if not isinstance(executable, str) or not executable.strip():
            raise EvidenceAdapterError("external_command_invalid:executable")
        if isinstance(args, (str, bytes)) or not isinstance(args, Sequence):
            raise EvidenceAdapterError("external_command_invalid:args")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise EvidenceAdapterError("external_command_invalid:timeout")
        if not isinstance(output_limit, int) or output_limit < 1:
            raise EvidenceAdapterError("external_command_invalid:max_output_bytes")
        if artifact is not None and not isinstance(artifact, str):
            raise EvidenceAdapterError("external_command_invalid:artifact")
        if artifact_sha256 is not None and not isinstance(artifact_sha256, str):
            raise EvidenceAdapterError("external_command_invalid:artifact_sha256")
        return (
            executable,
            tuple(str(item) for item in args),
            str(sha256) if sha256 is not None else None,
            artifact,
            artifact_sha256,
            float(timeout),
            output_limit,
        )


__all__ = [
    "AuthorizedCommandAdapter",
    "BundleFileAdapter",
    "EvidenceAdapterError",
    "ExternalCommandIdentity",
]
