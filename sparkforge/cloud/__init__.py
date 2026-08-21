"""SparkForge Optional Cloud Extension Package."""
from __future__ import annotations

from sparkforge.cloud.worker import (
    BaseRemoteWorkerBackend,
    LocalFallbackWorkerBackend,
    RemoteWorkerResult,
    RemoteWorkerTask,
)

__all__ = [
    "BaseRemoteWorkerBackend",
    "LocalFallbackWorkerBackend",
    "RemoteWorkerResult",
    "RemoteWorkerTask",
]
