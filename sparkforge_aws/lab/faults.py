"""Allowlisted fault plans; execution belongs to an explicitly confirmed backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import LabContractError

FAULT_TARGETS = {
    "none": "application",
    "latency": "network",
    "jitter": "network",
    "bandwidth_limit": "network",
    "timeout": "network",
    "connection_cut": "network",
    "kill_container": "process",
    "pause_process": "process",
    "cpu_throttle": "compute",
    "memory_constrain": "compute",
    "disk_full_simulation": "data",
    "restart_taskmanager": "application",
    "restart_broker": "application",
    "stop_connect": "application",
    "consumer_slowdown": "application",
    "schema_change": "data",
}


def compile_fault(spec: Mapping[str, Any]) -> dict[str, Any]:
    fault_type = spec.get("type", "none")
    if not isinstance(fault_type, str) or fault_type not in FAULT_TARGETS:
        raise LabContractError(f"unsupported fault type: {fault_type}")
    duration = spec.get("duration", "")
    if duration and not isinstance(duration, str):
        raise LabContractError("fault.duration must be a duration string")
    return {
        "type": fault_type,
        "target_kind": FAULT_TARGETS[fault_type],
        "parameters": {
            str(key): value for key, value in spec.items() if key not in {"type", "duration"}
        },
        "duration": duration,
        "mechanism": "toxiproxy"
        if FAULT_TARGETS[fault_type] == "network"
        else "declared_backend_action",
        "requires_confirmation": fault_type != "none",
    }


__all__ = ["FAULT_TARGETS", "compile_fault"]
