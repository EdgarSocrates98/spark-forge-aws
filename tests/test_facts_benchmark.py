from sparkforge.facts.benchmark import EMITTED_KINDS, EXTRACTOR_ID, build_benchmark
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact


def _prov(artifact: str) -> dict:
    return {"artifact": artifact, "artifact_sha256": "", "extractor": "event_log@0.1.0"}


def _stage(symbol: str, stage_id: int, **measures) -> Fact:
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={
            "mean_ms": measures.get("mean_ms", 100),
            "task_count": measures.get("task_count", 10),
        },
        provenance=_prov(measures.get("artifact", "a.jsonl")),
    )


def _task_input(symbol: str, stage_id: int, total_bytes: int, artifact: str = "a.jsonl") -> Fact:
    return Fact(
        kind="spark.stage.task_input",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={"total_bytes": total_bytes},
        provenance=_prov(artifact),
    )


def _gc(symbol: str, stage_id: int, gc_ms: int, artifact: str = "a.jsonl") -> Fact:
    return Fact(
        kind="spark.stage.gc",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={"gc_ms": gc_ms, "executor_run_ms": 1000},
        provenance=_prov(artifact),
    )


def _task_count(symbol: str, stage_id: int, task_count: int, artifact: str = "a.jsonl") -> Fact:
    return Fact(
        kind="spark.stage.task_count",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={"task_count": task_count, "available_cores": 8},
        provenance=_prov(artifact),
    )


def _spill_summary(app_id: str, memory: int, disk: int, artifact: str = "a.jsonl") -> Fact:
    return Fact(
        kind="spark.job.spill_summary",
        subject={"type": "job_run", "symbol": app_id},
        measures={
            "stages_with_spill": 1 if (memory or disk) else 0,
            "total_memory_spill_bytes": memory,
            "total_disk_spill_bytes": disk,
        },
        provenance=_prov(artifact),
    )


def _analyzed(artifact: str) -> Fact:
    return Fact(
        kind="spark.log_analyzed",
        subject={
            "type": "source_location",
            "file": artifact,
            "line": 0,
            "col": 0,
            "symbol": "",
            "snippet": "",
        },
        measures={"line_count": 10, "event_count": 10, "unresolved_count": 0},
        provenance=_prov(artifact),
    )


def by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def only_delta(facts):
    return by_kind(facts, "bench.run_delta")[0]


def test_o_total_de_tempo_de_task_e_somado_dos_dois_lados():
    before = [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=200, task_count=10)]
    after = [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100, task_count=10)]

    facts = build_benchmark(before, after)

    delta = only_delta(facts)
    assert delta.measures["total_task_ms_before"] == 2000
    assert delta.measures["total_task_ms_after"] == 1000
    assert delta.measures["total_task_ms_delta_pct"] == -50.0


def test_um_lado_sem_log_analyzed_vira_unresolved():
    facts = build_benchmark([_analyzed("a.jsonl")], [])
    assert [f.kind for f in facts if f.kind == "bench.unresolved"] == ["bench.unresolved"]
    assert [f for f in facts if f.kind == "bench.run_delta"] == []
    assert by_kind(facts, "bench.unresolved")[0].attrs == {
        "reason": "missing_log_analyzed",
        "sides": ["after"],
        "measure": "",
    }


def test_o_namespace_declarado_cobre_os_cinco_kinds():
    assert EMITTED_KINDS == {
        "bench.run_delta",
        "bench.stage_delta",
        "bench.unmatched",
        "bench.analyzed",
        "bench.unresolved",
    }


def test_o_id_do_deriver_segue_a_convencao_do_repositorio():
    assert EXTRACTOR_ID.startswith("benchmark@")


class TestAsCincoMedidasDoRun:
    def _par(self):
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0, mean_ms=200, task_count=10),
            _task_input("scan", 0, 1000),
            _gc("scan", 0, 400),
            _task_count("scan", 0, 10),
            _spill_summary("app-1", 600, 400),
        ]
        after = [
            _analyzed("b.jsonl"),
            _stage("scan", 0, mean_ms=100, task_count=10),
            _task_input("scan", 0, 1500, artifact="b.jsonl"),
            _gc("scan", 0, 200, artifact="b.jsonl"),
            _task_count("scan", 0, 20, artifact="b.jsonl"),
            _spill_summary("app-2", 300, 200, artifact="b.jsonl"),
        ]
        return before, after

    def test_input_bytes_soma_o_total_por_stage(self):
        delta = only_delta(build_benchmark(*self._par()))
        assert delta.measures["total_input_bytes_before"] == 1000
        assert delta.measures["total_input_bytes_after"] == 1500
        assert delta.measures["total_input_bytes_delta_pct"] == 50.0

    def test_spill_soma_memoria_e_disco_do_resumo_do_job(self):
        delta = only_delta(build_benchmark(*self._par()))
        assert delta.measures["total_spill_bytes_before"] == 1000
        assert delta.measures["total_spill_bytes_after"] == 500
        assert delta.measures["total_spill_bytes_delta_pct"] == -50.0

    def test_gc_soma_o_gc_de_cada_stage(self):
        delta = only_delta(build_benchmark(*self._par()))
        assert delta.measures["total_gc_ms_before"] == 400
        assert delta.measures["total_gc_ms_after"] == 200
        assert delta.measures["total_gc_ms_delta_pct"] == -50.0

    def test_task_count_vem_do_kind_proprio_e_nao_do_de_duracao(self):
        delta = only_delta(build_benchmark(*self._par()))
        assert delta.measures["total_task_count_before"] == 10
        assert delta.measures["total_task_count_after"] == 20
        assert delta.measures["total_task_count_delta_pct"] == 100.0

    def test_varios_resumos_de_job_no_mesmo_lado_somam(self):
        before, after = self._par()
        before.append(_spill_summary("app-1b", 1000, 0))
        delta = only_delta(build_benchmark(before, after))
        assert delta.measures["total_spill_bytes_before"] == 2000


class TestOQueOModuloRecusaAAfirmar:
    def test_delta_pct_some_quando_o_lado_antes_e_zero(self):
        """Dividir por zero nao produz "infinito por cento", produz afirmacao sem
        sentido -- e chave ausente e como este motor diz "nao sei"."""
        before = [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=0, task_count=10)]
        after = [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100, task_count=10)]

        delta = only_delta(build_benchmark(before, after))

        assert delta.measures["total_task_ms_before"] == 0
        assert delta.measures["total_task_ms_after"] == 1000
        assert "total_task_ms_delta_pct" not in delta.measures

    def test_medida_ausente_dos_dois_lados_vira_unresolved_nomeado(self):
        before = [_analyzed("a.jsonl"), _stage("scan", 0)]
        after = [_analyzed("b.jsonl"), _stage("scan", 0)]

        facts = build_benchmark(before, after)

        delta = only_delta(facts)
        ausentes = {
            f.attrs["measure"]
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["reason"] == "measure_absent_both_sides"
        }
        assert ausentes == {
            "total_input_bytes",
            "total_spill_bytes",
            "total_gc_ms",
            "total_task_count",
        }
        for name in ausentes:
            assert f"{name}_before" not in delta.measures
            assert f"{name}_after" not in delta.measures

    def test_medida_ausente_de_um_lado_so_nao_vira_zero(self):
        before = [_analyzed("a.jsonl"), _stage("scan", 0), _gc("scan", 0, 400)]
        after = [_analyzed("b.jsonl"), _stage("scan", 0)]

        facts = build_benchmark(before, after)

        delta = only_delta(facts)
        assert delta.measures["total_gc_ms_before"] == 400
        assert "total_gc_ms_after" not in delta.measures
        assert "total_gc_ms_delta_pct" not in delta.measures
        de_um_lado = [
            f for f in by_kind(facts, "bench.unresolved") if f.attrs["measure"] == "total_gc_ms"
        ]
        assert [f.attrs["reason"] for f in de_um_lado] == ["measure_absent_one_side"]
        assert de_um_lado[0].attrs["sides"] == ["after"]

    def test_cada_unresolved_tem_id_proprio(self):
        """`Fact.id` e sha1 de (kind, subject, measures) -- `attrs` fica de fora.
        Unresolved sem subject proprio colidiria com os outros quatro."""
        facts = build_benchmark([_analyzed("a.jsonl")], [_analyzed("b.jsonl")])
        unresolved = by_kind(facts, "bench.unresolved")
        assert len(unresolved) == 5
        assert len({f.id for f in unresolved}) == 5


class TestSentinela:
    def test_a_sentinela_conta_os_stages_dos_dois_lados(self):
        before = [_analyzed("a.jsonl"), _stage("scan", 0), _stage("join", 1), _gc("scan", 0, 1)]
        after = [_analyzed("b.jsonl"), _stage("scan", 7)]

        sentinela = by_kind(build_benchmark(before, after), "bench.analyzed")[0]

        assert sentinela.measures["before_stage_count"] == 2
        assert sentinela.measures["after_stage_count"] == 1
        # Casamento de stage e a Task 2; ate la os dois contadores sao zero.
        assert sentinela.measures["matched_stage_count"] == 0
        assert sentinela.measures["unmatched_stage_count"] == 0

    def test_a_sentinela_nomeia_os_artefatos_de_cada_lado(self):
        before = [_analyzed("a.jsonl"), _analyzed("a2.jsonl"), _stage("scan", 0)]
        after = [_analyzed("b.jsonl"), _stage("scan", 0)]

        sentinela = by_kind(build_benchmark(before, after), "bench.analyzed")[0]

        assert sentinela.attrs["before_artifacts"] == ["a.jsonl", "a2.jsonl"]
        assert sentinela.attrs["after_artifacts"] == ["b.jsonl"]


class TestFormaDaSaida:
    def _facts(self):
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0, mean_ms=200),
            _task_input("scan", 0, 10),
            _gc("scan", 0, 5),
            _task_count("scan", 0, 10),
            _spill_summary("app-1", 0, 0),
        ]
        after = [
            _analyzed("b.jsonl"),
            _stage("scan", 3, mean_ms=100, artifact="b.jsonl"),
            _task_input("scan", 3, 10, artifact="b.jsonl"),
            _gc("scan", 3, 5, artifact="b.jsonl"),
            _task_count("scan", 3, 10, artifact="b.jsonl"),
            _spill_summary("app-2", 0, 0, artifact="b.jsonl"),
        ]
        return build_benchmark(before, after, path_hint="a.jsonl..b.jsonl")

    def test_todo_kind_emitido_esta_no_namespace_declarado(self):
        assert {f.kind for f in self._facts()} <= EMITTED_KINDS

    def test_todo_fact_passa_pelo_schema(self):
        for fact in self._facts():
            validate_fact(fact.to_dict())

    def test_a_saida_e_deterministica_e_ordenada(self):
        primeira = self._facts()
        assert [f.id for f in primeira] == [f.id for f in self._facts()]
        assert primeira == sort_facts(primeira)

    def test_a_procedencia_aponta_para_o_deriver(self):
        for fact in self._facts():
            assert fact.provenance["extractor"] == EXTRACTOR_ID
