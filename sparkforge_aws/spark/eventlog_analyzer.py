"""Spark Event Log Analyzer for Bottleneck and Skew Detection."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SparkEventLogMetric:
    total_stages: int = 0
    failed_stages: int = 0
    total_tasks: int = 0
    failed_tasks: int = 0
    total_shuffle_read_bytes: int = 0
    total_shuffle_write_bytes: int = 0
    total_spill_memory_bytes: int = 0
    total_spill_disk_bytes: int = 0
    max_stage_duration_ms: float = 0.0
    has_skew: bool = False
    has_spill: bool = False
    bottlenecks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SparkEventLogAnalyzer:
    """Deterministic parser for Spark EventLog (.jsonl) dumps."""

    def analyze_event_log(self, log_lines: list[str]) -> SparkEventLogMetric:
        metrics = SparkEventLogMetric()
        stage_task_durations: dict[int, list[float]] = {}

        for line in log_lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:  # noqa: S112 -- linha malformada e pulada, como no extrator canonico
                continue

            event_type = event.get("Event", "")

            if event_type == "SparkListenerStageCompleted":
                stage_info = event.get("Stage Info", {})
                metrics.total_stages += 1
                if stage_info.get("Failure Reason"):
                    metrics.failed_stages += 1

                # Check submission / completion time
                submit = stage_info.get("Submission Time", 0)
                complete = stage_info.get("Completion Time", 0)
                if complete and submit:
                    dur = complete - submit
                    if dur > metrics.max_stage_duration_ms:
                        metrics.max_stage_duration_ms = dur

            elif event_type == "SparkListenerTaskEnd":
                metrics.total_tasks += 1
                task_info = event.get("Task Info", {})
                if task_info.get("Failed", False):
                    metrics.failed_tasks += 1

                stage_id = event.get("Stage ID", 0)
                dur = task_info.get("Duration", 0)
                stage_task_durations.setdefault(stage_id, []).append(dur)

                # Metrics
                task_metrics = event.get("Task Metrics", {})
                metrics.total_spill_memory_bytes += task_metrics.get("Memory Bytes Spilled", 0)
                metrics.total_spill_disk_bytes += task_metrics.get("Disk Bytes Spilled", 0)
                shuffle_read = task_metrics.get("Shuffle Read Metrics", {})
                metrics.total_shuffle_read_bytes += shuffle_read.get("Remote Bytes Read", 0)

        # Check for skew: if max task duration > 4x median in any stage with > 10 tasks
        for stage_id, durations in stage_task_durations.items():
            if len(durations) >= 5:
                durations.sort()
                median = durations[len(durations) // 2]
                max_d = durations[-1]
                if median > 0 and (max_d / median) > 3.0:
                    metrics.has_skew = True
                    metrics.bottlenecks.append(
                        f"Task duration skew in Stage {stage_id}: max {max_d}ms vs "
                        f"median {median}ms."
                    )

        if metrics.total_spill_disk_bytes > 0:
            metrics.has_spill = True
            mb_spilled = metrics.total_spill_disk_bytes / (1024 * 1024)
            metrics.bottlenecks.append(f"Memory spill to disk detected: {mb_spilled:.1f} MB.")

        if metrics.failed_tasks > 0:
            metrics.bottlenecks.append(f"{metrics.failed_tasks} task retries / failures observed.")

        return metrics
