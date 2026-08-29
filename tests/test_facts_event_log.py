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


def _stage_completed(stage_id, name, num_tasks, failure_reason=None):
    stage_info = {
        "Stage ID": stage_id,
        "Stage Name": name,
        "Number of Tasks": num_tasks,
    }
    # A chave ausente e a chave vazia sao casos DIFERENTES, e os dois tem
    # teste: o Spark escreve `Failure Reason` so quando a stage falhou.
    if failure_reason is not None:
        stage_info["Failure Reason"] = failure_reason
    return _line("SparkListenerStageCompleted", **{"Stage Info": stage_info})


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


class TestRuntimeVersion:
    def _log_start(self, version, key="Spark Version"):
        return _line("SparkListenerLogStart", **{key: version})

    def test_log_start_emits_runtime_version_anchored_no_app_id(self):
        lines = [
            self._log_start("3.5.4"),
            _line("SparkListenerApplicationStart", **{"App ID": "application_1_0001"}),
        ]
        facts = extract_event_log(lines, "log.jsonl")
        version = facts_of("spark.runtime_version", facts)
        assert len(version) == 1
        assert version[0].attrs["version"] == "3.5.4"
        assert version[0].attrs["component"] == "spark"
        assert version[0].attrs["source_event"] == "SparkListenerLogStart"
        assert version[0].subject == {"type": "job_run", "symbol": "application_1_0001"}
        assert version[0].provenance["extractor"] == EXTRACTOR_ID
        validate_fact(version[0].to_dict())

    def test_vendor_suffixed_version_is_preserved_verbatim(self):
        """Glue reporta '3.5.4-amzn-0'. Truncar para '3.5.4' seria normalizar
        uma observacao -- o extrator reporta o que o run reportou."""
        facts = extract_event_log([self._log_start("3.5.4-amzn-0")], "log.jsonl")
        assert facts_of("spark.runtime_version", facts)[0].attrs["version"] == "3.5.4-amzn-0"

    def test_absent_log_start_emits_nothing_and_is_not_an_error(self):
        """Event log sem SparkListenerLogStart e event log valido (log
        truncado pelo inicio, log sintetico, recorte). Ausencia de versao nao
        e ponto cego: e simplesmente silencio."""
        lines = [_task_end(0, 0, 1000, 1500), _stage_completed(0, "s", 1)]
        facts = extract_event_log(lines, "log.jsonl")
        assert facts_of("spark.runtime_version", facts) == []
        assert facts_of("spark.unresolved", facts) == []
        assert facts_of("spark.log_analyzed", facts)[0].measures["unresolved_count"] == 0

    @pytest.mark.parametrize(
        "version",
        ["", "   ", "unknown", "v3.5.4", "3.5.4 (amzn)"],
        ids=["empty", "blank", "not_a_version", "prefixed", "with_space"],
    )
    def test_malformed_or_empty_version_becomes_unresolved(self, version):
        facts = extract_event_log([self._log_start(version)], "log.jsonl")
        assert facts_of("spark.runtime_version", facts) == []
        unresolved = facts_of("spark.unresolved", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "missing_event_field"
        assert unresolved[0].subject["line"] == 1
        assert facts_of("spark.log_analyzed", facts)[0].measures["unresolved_count"] == 1

    def test_non_string_version_becomes_unresolved(self):
        facts = extract_event_log([self._log_start(3.5)], "log.jsonl")
        assert facts_of("spark.runtime_version", facts) == []
        assert facts_of("spark.unresolved", facts)[0].attrs["reason"] == "missing_event_field"

    def test_log_start_without_the_version_key_becomes_unresolved(self):
        """Evento presente mas sem o campo esperado e estrutura interna
        quebrada -- categoria diferente de evento ausente."""
        facts = extract_event_log([_line("SparkListenerLogStart")], "log.jsonl")
        assert facts_of("spark.runtime_version", facts) == []
        assert facts_of("spark.unresolved", facts)[0].attrs["reason"] == "missing_event_field"

    def test_repeated_log_start_with_same_version_is_idempotent(self):
        """Event log rolante (`spark.eventLog.rolling.enabled`) e escrito em
        varios arquivos, cada um comecando por SparkListenerLogStart. Quem
        concatena as partes ve o cabecalho repetido: repeticao com o MESMO
        valor e o caso normal, nao anomalia."""
        lines = [self._log_start("3.5.4"), _task_end(0, 0, 1, 2), self._log_start("3.5.4")]
        facts = extract_event_log(lines, "log.jsonl")
        assert len(facts_of("spark.runtime_version", facts)) == 1
        assert facts_of("spark.unresolved", facts) == []

    def test_conflicting_log_start_keeps_the_first_and_flags_the_conflict(self):
        """Duas versoes diferentes num unico log significam partes de runs
        distintos concatenadas: um unico fact nao consegue afirmar as duas.
        Escolher em silencio deixaria uma versao errada gatilhar as regras
        versionadas de `judge`; abortar jogaria fora o log inteiro. O primeiro
        cabecalho vence (e o que o arquivo abriu) e a divergencia vira ponto
        cego explicito, ancorado na linha que discordou."""
        lines = [self._log_start("3.5.4"), self._log_start("3.3.0")]
        facts = extract_event_log(lines, "log.jsonl")
        version = facts_of("spark.runtime_version", facts)
        assert len(version) == 1
        assert version[0].attrs["version"] == "3.5.4"
        unresolved = facts_of("spark.unresolved", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "conflicting_runtime_version"
        assert unresolved[0].subject["line"] == 2
        assert "3.5.4" in unresolved[0].attrs["detail"]
        assert "3.3.0" in unresolved[0].attrs["detail"]

    def test_kind_is_declared_in_the_namespace(self):
        assert "spark.runtime_version" in EMITTED_KINDS


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


class TestShuffleMetrics:
    def _task_end(self, stage_id, read_bytes=None, write_bytes=None):
        metrics = {
            "Executor Run Time": 1000,
            "JVM GC Time": 10,
            "Memory Bytes Spilled": 0,
            "Disk Bytes Spilled": 0,
            "Input Metrics": {"Bytes Read": 100},
        }
        if read_bytes is not None:
            metrics["Shuffle Read Metrics"] = {
                "Remote Bytes Read": read_bytes,
                "Local Bytes Read": 0,
                "Total Records Read": 7,
                "Fetch Wait Time": 3,
            }
        if write_bytes is not None:
            metrics["Shuffle Write Metrics"] = {
                "Shuffle Bytes Written": write_bytes,
                "Shuffle Records Written": 5,
                "Shuffle Write Time": 2_000_000,
            }
        return json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": stage_id,
                "Task Info": {"Launch Time": 0, "Finish Time": 500, "Failed": False},
                "Task Metrics": metrics,
            }
        )

    def _stage_completed(self, stage_id):
        return json.dumps(
            {
                "Event": "SparkListenerStageCompleted",
                "Stage Info": {
                    "Stage ID": stage_id,
                    "Stage Name": "stage-x",
                    "Number of Tasks": 1,
                },
            }
        )

    def test_stage_that_moved_data_gets_a_shuffle_fact(self):
        facts = extract_event_log(
            [self._task_end(1, read_bytes=4096, write_bytes=8192), self._stage_completed(1)],
            "log.jsonl",
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"]

        assert len(shuffle) == 1
        assert shuffle[0].subject["type"] == "stage"
        assert shuffle[0].measures["read_bytes"] == 4096
        assert shuffle[0].measures["write_bytes"] == 8192
        assert shuffle[0].measures["read_records"] == 7
        assert shuffle[0].measures["write_records"] == 5

    def test_stage_without_shuffle_produces_no_fact(self):
        facts = extract_event_log([self._task_end(1), self._stage_completed(1)], "log.jsonl")

        assert not [f for f in facts if f.kind == "spark.stage.shuffle"]

    def test_bytes_are_summed_across_tasks(self):
        facts = extract_event_log(
            [
                self._task_end(1, write_bytes=1000),
                self._task_end(1, write_bytes=500),
                self._stage_completed(1),
            ],
            "log.jsonl",
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"][0]

        assert shuffle.measures["write_bytes"] == 1500

    def test_read_only_stage_omits_the_write_measures(self):
        facts = extract_event_log(
            [self._task_end(1, read_bytes=2048), self._stage_completed(1)], "log.jsonl"
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"][0]

        assert shuffle.measures["read_bytes"] == 2048
        assert "write_bytes" not in shuffle.measures


class TestStageFailureReason:
    """A razao da stage que falhou -- a fonte que o diagnostico de timeout usa.

    Duas das quatro categorias de timeout (broadcast e network) nao tem outra
    fonte no event log: a frase que as separa e escrita em
    `Stage Info["Failure Reason"]`, e o handler descartava aquela chave.
    """

    def test_a_failed_stage_carries_the_literal_reason(self):
        linhas = [
            _task_end(1, 1, 0, 1000),
            _stage_completed(
                1,
                "stage-1",
                1,
                failure_reason="Could not execute broadcast in 300 secs.",
            ),
        ]
        falhas = facts_of("spark.stage.failure", extract_event_log(linhas, "log.json"))

        assert len(falhas) == 1
        assert falhas[0].attrs["reason"] == "Could not execute broadcast in 300 secs."
        assert falhas[0].subject["stage_id"] == 1
        assert falhas[0].subject["type"] == "stage"

    def test_a_stage_without_a_failure_reason_produces_nothing(self):
        """Ausencia de falha nao e falha vazia."""
        linhas = [_task_end(1, 1, 0, 1000), _stage_completed(1, "stage-1", 1)]

        assert not facts_of("spark.stage.failure", extract_event_log(linhas, "log.json"))

    def test_an_empty_failure_reason_produces_nothing(self):
        linhas = [_task_end(1, 1, 0, 1000), _stage_completed(1, "stage-1", 1, failure_reason="")]

        assert not facts_of("spark.stage.failure", extract_event_log(linhas, "log.json"))

    def test_a_credential_inside_the_reason_is_redacted(self):
        """`facts.json` e commitado como barramento de handoff.

        Razao de falha carrega URL de JDBC com senha dentro com a mesma
        facilidade que configuracao carrega, e passa pelo mesmo `redact`.
        """
        segredo = (
            "Job aborted: connection to jdbc:postgresql://usuario:s3nh4_secreta@host/db failed"
        )
        linhas = [
            _task_end(1, 1, 0, 1000),
            _stage_completed(1, "stage-1", 1, failure_reason=segredo),
        ]
        falhas = facts_of("spark.stage.failure", extract_event_log(linhas, "log.json"))

        assert len(falhas) == 1
        assert "s3nh4_secreta" not in falhas[0].attrs["reason"]
        assert falhas[0].attrs["redacted"] is True

    def test_the_kind_is_declared_and_validates(self):
        linhas = [
            _task_end(1, 1, 0, 1000),
            _stage_completed(1, "stage-1", 1, failure_reason="Futures timed out after [120 s]"),
        ]
        facts = extract_event_log(linhas, "log.json")

        assert "spark.stage.failure" in EMITTED_KINDS
        for fact in facts:
            validate_fact(fact.to_dict())
