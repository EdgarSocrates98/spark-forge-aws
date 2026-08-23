"""SparkForge Workflows and Waves Package."""
from __future__ import annotations

from sparkforge.workflows.dag import DAGNode, ExecutionDAG
from sparkforge.workflows.handoff import StructuredHandoff
from sparkforge.workflows.spec import TaskSpec

__all__ = [
    "DAGNode",
    "ExecutionDAG",
    "StructuredHandoff",
    "TaskSpec",
]
