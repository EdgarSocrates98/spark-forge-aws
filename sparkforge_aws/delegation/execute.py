"""Governed subprocess execution for peer delegation (lf-0029).

The single execution substrate for delegated calls. Mirrors the guarantees
of ``theforge``'s adapter ``run_native`` (``_shell.py``) at peer scale:

- **argv only, never a shell.** ``subprocess.run`` receives a list and
  ``shell=False``; a template-resolved argv arrives already validated by
  ``governance.argv_problems``.
- **Scrubbed environment.** The child sees ``env.safe_env()`` — credentials
  never propagate through env (``^AWS_``, ``*_TOKEN``, ``*_SECRET``, …).
  EXTERNAL_READ capabilities authenticate inside the delegatee's own
  credential chain (a ``--profile`` argv flag → shared config files), never
  through forwarded variables.
- **Timeout with a guaranteed kill.** ``subprocess.run(timeout=…)`` kills
  the direct child on expiry (``proc.kill()``). Limitation, recorded
  honestly: grandchildren of the delegatee are not tree-killed here — the
  delegatees we invoke are leaf CLIs.
- **Bounded output.** stdout/stderr are read with byte caps; an overrun is
  truncated and flagged on ``ExecResult`` — never unbounded memory.

Failures are named, never anonymous: spawn failure → ``provider-absent``;
timeout → ``timeout``; OS error → ``runtime-error``. A non-zero exit is NOT
a refusal at this layer — ``ExecResult.returncode`` is data; the output
parser of each peer decides which codes are findings vs failure.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

from sparkforge_aws.delegation.contracts import (
    DelegationRefusal,
    ExecResult,
)
from sparkforge_aws.delegation.env import is_credential_name, safe_env

__all__ = [
    "MAX_STDOUT_BYTES",
    "MAX_STDERR_BYTES",
    "DEFAULT_TIMEOUT_S",
    "run_governed",
]

MAX_STDOUT_BYTES = 4 * 1024 * 1024  # 4 MiB — fits any --json diagnostic
MAX_STDERR_BYTES = 512 * 1024       # 512 KiB tail of diagnostics
DEFAULT_TIMEOUT_S = 300.0


def run_governed(
    argv: list[str],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    env_extra: dict[str, str] | None = None,
    cwd: str | None = None,
    _popen_run: Any = None,  # test seam — a callable matching subprocess.run
) -> ExecResult | DelegationRefusal:
    """Run ``argv`` under the governed boundary, or refuse before spawning.

    Returns ``ExecResult`` whenever the child produced an outcome (any
    returncode); returns ``DelegationRefusal`` only when no governed
    execution could happen (empty argv, credential-shaped env override,
    spawn failure, timeout).
    """
    if not argv:
        return DelegationRefusal(code="invalid-input", detail="empty argv")
    if env_extra:
        bad = [k for k in env_extra if is_credential_name(k)]
        if bad:
            return DelegationRefusal(
                code="policy-refusal",
                detail=(
                    "env override carries credential-shaped names "
                    f"{sorted(bad)} — credentials never reach a delegatee"
                ),
            )
    run = _popen_run or subprocess.run
    started = time.monotonic()
    try:
        proc = run(
            argv,
            capture_output=True,
            timeout=timeout_s,
            env=safe_env(extra=env_extra),
            cwd=cwd,
        )
    except FileNotFoundError:
        return DelegationRefusal(
            code="provider-absent",
            detail=f"executable {argv[0]!r} not found on PATH",
        )
    except subprocess.TimeoutExpired:
        return DelegationRefusal(
            code="timeout",
            detail=f"{argv[0]!r} exceeded timeout {timeout_s:g}s",
        )
    except OSError as exc:
        return DelegationRefusal(
            code="runtime-error",
            detail=f"{argv[0]!r} failed to start: {exc}",
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    raw_out = proc.stdout if isinstance(proc.stdout, bytes) else str(proc.stdout).encode()
    raw_err = proc.stderr if isinstance(proc.stderr, bytes) else str(proc.stderr).encode()
    return ExecResult(
        argv=list(argv),
        returncode=int(proc.returncode),
        stdout=raw_out[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace"),
        stderr=raw_err[:MAX_STDERR_BYTES].decode("utf-8", errors="replace"),
        elapsed_ms=elapsed_ms,
        stdout_bytes=len(raw_out),
        stderr_bytes=len(raw_err),
        stdout_truncated=len(raw_out) > MAX_STDOUT_BYTES,
        stderr_truncated=len(raw_err) > MAX_STDERR_BYTES,
    )
