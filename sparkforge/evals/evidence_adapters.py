"""Offline adapters for canonical evaluation evidence bundles."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from sparkforge.evals.evidence import EvaluationEvidenceBundle, EvidenceBundleError


class EvidenceAdapterError(EvidenceBundleError):
    """Named file and authorized-command adapter failure."""


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
        spec = self.commands[command_id]
        executable, configured_args, declared_sha256, timeout, output_limit = self._spec(spec)
        command = (executable, *configured_args, *tuple(str(item) for item in argv))
        executable_path = Path(executable).expanduser().resolve()
        if not executable_path.is_file():
            raise EvidenceAdapterError(f"external_command_not_found:{executable_path}")
        if declared_sha256:
            actual = hashlib.sha256(executable_path.read_bytes()).hexdigest()
            if actual != declared_sha256.removeprefix("sha256:"):
                raise EvidenceAdapterError("external_command_executable_digest_mismatch")
        temp_dir = self.repo / ".sparkforge" / "evidence-input"
        temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", dir=temp_dir, delete=False
        ) as handle:
            json.dump(dict(input_mapping or {}), handle, ensure_ascii=False, sort_keys=True)
            input_path = Path(handle.name)
        try:
            completed = subprocess.run(  # noqa: S603
                (*command, "--input", str(input_path)),
                cwd=self.repo,
                env={"PATH": str(executable_path.parent), "PYTHONIOENCODING": "utf-8"},
                capture_output=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise EvidenceAdapterError("external_command_timeout") from exc
        finally:
            try:
                input_path.unlink()
            except OSError:
                pass
        if len(completed.stdout) > output_limit or len(completed.stderr) > output_limit:
            raise EvidenceAdapterError("external_command_output_too_large")
        if completed.returncode != 0:
            raise EvidenceAdapterError(f"external_command_failed:exit_{completed.returncode}")
        try:
            raw = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceAdapterError("external_command_invalid_output:json") from exc
        if not isinstance(raw, Mapping):
            raise EvidenceAdapterError("external_command_invalid_output:object")
        return EvaluationEvidenceBundle.from_mapping(raw)

    execute = run

    def _spec(self, value: Any) -> tuple[str, tuple[str, ...], str | None, float, int]:
        if isinstance(value, Mapping):
            executable = value.get("executable")
            args = value.get("args", ())
            sha256 = value.get("sha256") or value.get("executable_sha256")
            timeout = value.get("timeout_seconds", self.timeout_seconds)
            output_limit = value.get("max_output_bytes", self.max_output_bytes)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            executable, *args = value
            sha256 = None
            timeout = self.timeout_seconds
            output_limit = self.max_output_bytes
        else:
            executable, args, sha256 = value, (), None
            timeout, output_limit = self.timeout_seconds, self.max_output_bytes
        if not isinstance(executable, str) or not executable.strip():
            raise EvidenceAdapterError("external_command_invalid:executable")
        if isinstance(args, (str, bytes)) or not isinstance(args, Sequence):
            raise EvidenceAdapterError("external_command_invalid:args")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise EvidenceAdapterError("external_command_invalid:timeout")
        if not isinstance(output_limit, int) or output_limit < 1:
            raise EvidenceAdapterError("external_command_invalid:max_output_bytes")
        return executable, tuple(str(item) for item in args), sha256, float(timeout), output_limit


__all__ = ["AuthorizedCommandAdapter", "BundleFileAdapter", "EvidenceAdapterError"]
