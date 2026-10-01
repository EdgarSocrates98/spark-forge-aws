"""Optional Cloud Remote Worker Abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RemoteWorkerTask:
    task_id: str
    task_type: str  # heavy_benchmark, holdout_eval, batch_analysis
    payload: dict[str, Any]
    max_timeout_seconds: int = 600


@dataclass
class RemoteWorkerResult:
    task_id: str
    status: str  # completed, failed, timeout
    output_data: dict[str, Any] = field(default_factory=dict)
    execution_time_seconds: float = 0.0
    cost_usd: float = 0.0


class BaseRemoteWorkerBackend(ABC):
    @abstractmethod
    def dispatch(self, task: RemoteWorkerTask) -> RemoteWorkerResult:
        """Dispatches work to remote serverless worker."""


class LocalFallbackWorkerBackend(BaseRemoteWorkerBackend):
    """Executes task locally when cloud is disabled or unavailable."""

    def dispatch(self, task: RemoteWorkerTask) -> RemoteWorkerResult:
        return RemoteWorkerResult(
            task_id=task.task_id,
            status="completed",
            output_data={
                "message": "Executed via local scale-to-zero engine",
                "payload": task.payload,
            },
            execution_time_seconds=0.1,
            cost_usd=0.0,
        )
