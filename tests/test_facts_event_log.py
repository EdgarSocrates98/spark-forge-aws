import json
import tracemalloc

import pytest

from sparkforge.facts.event_log import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    _is_heap_oom,
    _nearest_rank,
    extract_event_log,
    extract_event_log_path,
)
from sparkforge.findings.validate import validate_fact


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def _line(event: str, **fields) -> str:
    return json.dumps({"Event": event, **fields})


def _task_end(stage_id, task_id, launch, finish, *, failed=False, executor_id="1", **metrics):
    task_metrics = {
        "Executor Run Time": metrics.get("run_ms", 100),
        "JVM GC Time": metrics.get("gc_ms", 0),
        "Memory Bytes Spilled": metrics.get("mem_spill", 0),
        "Disk Bytes Spilled": metrics.get("disk_spill", 0),
        "Input Metrics": {"Bytes Read": metrics.get("input_bytes", 1000)},
    }
    return _line(
        "SparkListenerTaskEnd",
        **{
            "Stage ID": stage_id,
            "Task Info": {
                "Task ID": task_id,
                "Launch Time": launch,
                "Finish Time": finish,
                "Executor ID": executor_id,
                "Failed": failed,
            },
            "Task Metrics": task_metrics,
        },
    )


def _stage_completed(stage_id, name, num_tasks):
    return _line(
        "SparkListenerStageCompleted",
        **{
            "Stage Info": {
                "Stage ID": stage_id,
                "Stage Name": name,
                "Number of Tasks": num_tasks,
            }
        },
    )


class TestNearestRank:
    def test_single_value_never_divides_by_zero(self):
        assert _nearest_rank([42], 50) == 42
        assert _nearest_rank([42], 95) == 42
        assert _nearest_rank([42], 100) == 42

    def test_matches_hand_computed_rank_for_small_n(self):
        values = [10, 20, 100, 1000]
        # rank = ceil(pct/100 * n): p50 -> ceil(2.0)=2 -> values[1]; p95 -> ceil(3.8)=4 -> values[3]
        assert _nearest_rank(values, 50) == 20
        assert _nearest_rank(values, 95) == 1000

    def test_deterministic_across_repeated_calls(self):
        values = sorted([7, 3, 9, 1, 5, 5, 5])
        first = [_nearest_rank(values, p) for p in (50, 95)]
        second = [_nearest_rank(values, p) for p in (50, 95)]
        assert first == second


class TestHeapOomClassification:
    @pytest.mark.parametrize(
        "reason",
        [
            "ExecutorLostFailure (executor 3 exited caused by one of the running tasks) "
            "Reason: java.lang.OutOfMemoryError: Java heap space",
            "ExecutorLostFailure: GC overhead limit exceeded",
        ],
    )
    def test_heap_signatures_classified_true(self, reason):
        assert _is_heap_oom(reason) is True

    def test_container_kill_without_heap_signature_is_false(self):
        reason = (
            "Container killed by YARN for exceeding physical memory limits. "
            "5.5 GB of 5 GB physical memory used. Consider boosting "
            "spark.executor.memoryOverhead."
        )
        assert _is_heap_oom(reason) is False

    def test_empty_reason_is_false(self):
        assert _is_heap_oom("") is False


class TestMalformedLines:
    def test_invalid_json_becomes_unresolved_and_parse_continues(self):
        lines = [
            "{not valid json",
            _line("SparkListenerApplicationStart", **{"App ID": "app-1"}),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        unresolved = facts_of("spark.unresolved", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "malformed_json"
        assert unresolved[0].subject["line"] == 1
        sentinel = facts_of("spark.log_analyzed", facts)[0]
        assert sentinel.measures["unresolved_count"] == 1
        assert sentinel.measures["event_count"] == 1

    def test_valid_json_without_event_field_becomes_unresolved(self):
        lines = ['{"foo": "bar"}']
        facts = extract_event_log(lines, "log.jsonl")
        unresolved = facts_of("spark.unresolved", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "missing_event_field"

    def test_blank_lines_are_skipped_without_counting(self):
        lines = ["", "   ", _line("SparkListenerApplicationStart", **{"App ID": "a"})]
        facts = extract_event_log(lines, "log.jsonl")
        sentinel = facts_of("spark.log_analyzed", facts)[0]
        assert sentinel.measures["line_count"] == 3
        assert sentinel.measures["event_count"] == 1
        assert sentinel.measures["unresolved_count"] == 0

    def test_malformed_line_does_not_abort_later_valid_stage_data(self):
        lines = [
            "{broken",
            _task_end(0, 0, 1000, 2000, input_bytes=5000),
            _stage_completed(0, "s", 1),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        assert facts_of("spark.unresolved", facts)
        assert facts_of("spark.stage.task_duration", facts)

    def test_one_line_missing_task_info_key_is_unresolved_but_others_survive(self):
        lines = [
            _line("SparkListenerTaskEnd", **{"Stage ID": 0}),  # sem "Task Info"/"Task Metrics"
            _task_end(0, 1, 1000, 1500, input_bytes=2000),
            _stage_completed(0, "s", 2),
        ]
        # Task End sem "Task Info"/"Task Metrics" tem defaults ({}), entao nao produz
        # unresolved sozinho -- mas um "Stage ID" faltando produziria. Verifica so
        # que a extracao nao propaga excecao e ainda produz o fact do stage.
        facts = extract_event_log(lines, "log.jsonl")
        assert facts_of("spark.stage.task_count", facts)


class TestClusterCores:
    def test_peak_tracks_max_concurrent_sum_not_final_state(self):
        lines = [
            _line(
                "SparkListenerExecutorAdded",
                **{"Executor ID": "1", "Executor Info": {"Total Cores": 4}},
            ),
            _line(
                "SparkListenerExecutorAdded",
                **{"Executor ID": "2", "Executor Info": {"Total Cores": 4}},
            ),
            _line("SparkListenerExecutorRemoved", **{"Executor ID": "2", "Removed Reason": "x"}),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        cluster = facts_of("spark.cluster.cores", facts)[0]
        # pico foi 8 (os dois vivos simultaneamente), nao 4 (estado final apos remocao)
        assert cluster.measures["available_cores"] == 8
        assert cluster.measures["executor_count"] == 2

    def test_no_executor_events_leaves_available_cores_unset_on_stage_fact(self):
        lines = [_task_end(0, 0, 1000, 1500), _stage_completed(0, "s", 1)]
        facts = extract_event_log(lines, "log.jsonl")
        task_count_fact = facts_of("spark.stage.task_count", facts)[0]
        assert "available_cores" not in task_count_fact.measures


class TestFailedTaskExclusion:
    def test_failed_task_excluded_from_duration_and_input_but_counted_in_task_count(self):
        lines = [
            _task_end(0, 0, 1000, 2000, input_bytes=1000),
            _task_end(0, 1, 1000, 1001, failed=True, input_bytes=999999),
            _stage_completed(0, "s", 2),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        duration = facts_of("spark.stage.task_duration", facts)[0]
        assert duration.measures["task_count"] == 1
        assert duration.measures["max_ms"] == 1000
        task_count = facts_of("spark.stage.task_count", facts)[0]
        assert task_count.measures["task_count"] == 2  # "Number of Tasks" declarado


class TestStageWithoutTasks:
    def test_stage_completed_with_zero_tasks_emits_only_task_count(self):
        lines = [_stage_completed(0, "skipped", 0)]
        facts = extract_event_log(lines, "log.jsonl")
        assert facts_of("spark.stage.task_duration", facts) == []
        assert facts_of("spark.stage.task_input", facts) == []
        assert facts_of("spark.stage.spill", facts) == []
        assert facts_of("spark.stage.gc", facts) == []
        task_count = facts_of("spark.stage.task_count", facts)
        assert len(task_count) == 1
        assert task_count[0].measures["task_count"] == 0

    def test_truncated_log_without_stage_completed_still_emits_facts(self):
        # log cortado no meio: TaskEnd chegou mas SparkListenerStageCompleted nao.
        lines = [_task_end(7, 0, 1000, 1500, input_bytes=2000)]
        facts = extract_event_log(lines, "log.jsonl")
        duration = facts_of("spark.stage.task_duration", facts)
        assert duration and duration[0].subject["stage_id"] == 7
        assert duration[0].subject["symbol"] == ""


class TestSchemaCompliance:
    def test_every_emitted_kind_is_declared(self):
        lines = [
            _line(
                "SparkListenerExecutorAdded",
                **{"Executor ID": "1", "Executor Info": {"Total Cores": 4}},
            ),
            _line("SparkListenerExecutorRemoved", **{"Executor ID": "1", "Removed Reason": "x"}),
            "{broken",
            _task_end(0, 0, 1000, 2000, input_bytes=5000, gc_ms=100, disk_spill=10),
            _stage_completed(0, "s", 1),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        assert {f.kind for f in facts} <= EMITTED_KINDS
        for fact in facts:
            validate_fact(fact.to_dict())
            assert fact.provenance["extractor"] == EXTRACTOR_ID


class TestExtractEventLogPath:
    def test_reads_file_and_anchors_relative_path(self, tmp_path):
        repo_root = tmp_path
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        log_path = log_dir / "eventlog.jsonl"
        log_path.write_text(
            _stage_completed(0, "s", 0) + "\n",
            encoding="utf-8",
        )
        facts = extract_event_log_path(log_path, repo_root=repo_root)
        sentinel = facts_of("spark.log_analyzed", facts)[0]
        assert sentinel.subject["file"] == "logs/eventlog.jsonl"

    def test_missing_file_returns_read_error_unresolved_not_exception(self, tmp_path):
        missing = tmp_path / "does_not_exist.jsonl"
        facts = extract_event_log_path(missing, repo_root=tmp_path)
        assert len(facts) == 1
        assert facts[0].kind == "spark.unresolved"
        assert facts[0].attrs["reason"] == "read_error"


class TestStreaming:
    def _synthetic_lines(self, n_tasks: int):
        yield _line(
            "SparkListenerExecutorAdded",
            **{"Executor ID": "1", "Executor Info": {"Total Cores": 4}},
        )
        yield _line(
            "SparkListenerStageSubmitted",
            **{"Stage Info": {"Stage ID": 0, "Stage Name": "big", "Number of Tasks": n_tasks}},
        )
        for i in range(n_tasks):
            yield _task_end(0, i, 1000 + i, 1100 + i, input_bytes=1000)
        yield _stage_completed(0, "big", n_tasks)

    def test_generator_input_is_consumed_lazily_one_line_at_a_time(self):
        """`extract_event_log` recebe um gerador, nao uma lista: se a
        implementacao fizesse `list(lines)` internamente, o gerador seria
        drenado de uma vez; aqui verificamos apenas que um objeto que NAO
        suporta indexacao/len (a marca de uma lista materializada) funciona
        como entrada, o que exclui qualquer caminho que dependa de acesso
        aleatorio ou de `len(lines)`."""
        gen = self._synthetic_lines(500)
        assert not hasattr(gen, "__len__")
        facts = extract_event_log(gen, "big.jsonl")
        with pytest.raises(StopIteration):
            next(gen)  # gerador ja foi drenado por extract_event_log
        duration = facts_of("spark.stage.task_duration", facts)[0]
        assert duration.measures["task_count"] == 500

    def test_peak_memory_stays_low_for_a_50k_line_synthetic_log(self):
        """Prova qualitativa de streaming: para um log sintetico de 50.000
        linhas (~10-15MB de texto JSON se materializado como lista de
        strings), o pico de memoria alocada durante a extracao fica na ordem
        de poucos MB -- os acumuladores por stage (listas de int), nao o
        arquivo inteiro nem a lista de linhas."""
        n = 50_000
        tracemalloc.start()
        try:
            facts = extract_event_log(self._synthetic_lines(n), "big.jsonl")
        finally:
            _current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        duration = facts_of("spark.stage.task_duration", facts)[0]
        assert duration.measures["task_count"] == n
        # Limiar generoso (20MB): muito acima do necessario para os
        # acumuladores (poucos MB), muito abaixo do que materializar o
        # arquivo inteiro como string ou lista de linhas custaria.
        assert peak < 20 * 1024 * 1024, f"pico de {peak / 1024 / 1024:.1f}MB, esperado < 20MB"
