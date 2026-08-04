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


def _stage_spill(
    symbol: str, stage_id: int, memory: int, disk: int, artifact: str = "a.jsonl"
) -> Fact:
    return Fact(
        kind="spark.stage.spill",
        subject={"type": "stage", "symbol": symbol, "stage_id": stage_id},
        measures={
            "memory_spill_bytes": memory,
            "disk_spill_bytes": disk,
            "input_bytes": 1000,
        },
        provenance=_prov(artifact),
    )


def _sem_nome(stage_id, artifact: str = "a.jsonl") -> Fact:
    """Stage sem `symbol` e com `stage_id` de tipo livre -- o que um arquivo de
    facts editado a mao entrega, e que `_facts_from_dicts` copia verbatim."""
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": "", "stage_id": stage_id},
        measures={"mean_ms": 100, "task_count": 10},
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
            f
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["measure"] == "total_gc_ms"
            and f.attrs["reason"] == "measure_absent_one_side"
        ]
        assert len(de_um_lado) == 1
        assert de_um_lado[0].attrs["sides"] == ["after"]
        # O simbolo `scan` casa nos dois lados e e ELE que perdeu o gc, entao o
        # furo tambem sai nomeado por simbolo -- e o que impede o total do run de
        # afirmar uma queda que ninguem observou.
        assert [
            f.attrs["symbol"]
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["reason"] == "measure_absent_for_matched_symbol"
        ] == ["scan"]

    def test_kind_presente_sem_a_chave_da_medida_nao_vira_zero(self):
        """Presenca e por CHAVE, nao por kind. `spark.stage.task_duration` sem
        `task_count` nao sustenta `total_task_ms`; somar o que sobrou daria zero,
        e zero de um lado contra total do outro fabrica melhora de 100%."""
        sem_chave = Fact(
            kind="spark.stage.task_duration",
            subject={"type": "stage", "symbol": "scan", "stage_id": 0},
            measures={"mean_ms": 200},
            provenance=_prov("a.jsonl"),
        )
        before = [_analyzed("a.jsonl"), sem_chave]
        after = [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100, task_count=10)]

        facts = build_benchmark(before, after)

        delta = only_delta(facts)
        assert "total_task_ms_before" not in delta.measures
        assert delta.measures["total_task_ms_after"] == 1000
        assert "total_task_ms_delta_pct" not in delta.measures
        furo = [
            f
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["measure"] == "total_task_ms"
            and f.attrs["reason"] == "measure_absent_one_side"
        ]
        assert len(furo) == 1
        assert furo[0].attrs["sides"] == ["before"]
        assert furo[0].attrs["missing_key_fact_count"] == {"before": 1, "after": 0}

    def test_chave_faltando_nos_dois_lados_e_ausencia_apesar_do_kind_existir(self):
        def _sem_chave(artifact: str) -> Fact:
            return Fact(
                kind="spark.stage.gc",
                subject={"type": "stage", "symbol": "scan", "stage_id": 0},
                measures={"executor_run_ms": 1000},
                provenance=_prov(artifact),
            )

        facts = build_benchmark(
            [_analyzed("a.jsonl"), _sem_chave("a.jsonl")],
            [_analyzed("b.jsonl"), _sem_chave("b.jsonl")],
        )

        gc = [f for f in by_kind(facts, "bench.unresolved") if f.attrs["measure"] == "total_gc_ms"]
        assert [f.attrs["reason"] for f in gc] == ["measure_absent_both_sides"]
        assert gc[0].attrs["sides"] == ["before", "after"]
        assert "total_gc_ms_before" not in only_delta(facts).measures

    def test_lado_parcial_nao_vira_piso(self):
        """Alguns facts do kind com a chave e outros sem: somar so os presentes
        produz PISO, e piso de um lado contra total do outro fabrica melhora."""
        parcial = Fact(
            kind="spark.stage.task_input",
            subject={"type": "stage", "symbol": "join", "stage_id": 1},
            measures={"max_bytes": 10},
            provenance=_prov("a.jsonl"),
        )
        before = [_analyzed("a.jsonl"), _task_input("scan", 0, 1000), parcial]
        after = [_analyzed("b.jsonl"), _task_input("scan", 0, 1500, artifact="b.jsonl")]

        facts = build_benchmark(before, after)

        delta = only_delta(facts)
        assert "total_input_bytes_before" not in delta.measures
        assert delta.measures["total_input_bytes_after"] == 1500
        assert "total_input_bytes_delta_pct" not in delta.measures
        furo = [
            f
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["measure"] == "total_input_bytes"
        ]
        assert [f.attrs["reason"] for f in furo] == ["measure_partial_keys"]
        assert furo[0].attrs["sides"] == ["before"]
        assert furo[0].attrs["missing_key_fact_count"] == {"before": 1, "after": 0}

    def test_valor_nao_numerico_conta_como_chave_ausente(self):
        texto = Fact(
            kind="spark.stage.gc",
            subject={"type": "stage", "symbol": "scan", "stage_id": 0},
            measures={"gc_ms": "400", "executor_run_ms": 1000},
            provenance=_prov("a.jsonl"),
        )
        facts = build_benchmark(
            [_analyzed("a.jsonl"), texto],
            [_analyzed("b.jsonl"), _gc("scan", 0, 200, artifact="b.jsonl")],
        )

        assert "total_gc_ms_before" not in only_delta(facts).measures
        gc = [f for f in by_kind(facts, "bench.unresolved") if f.attrs["measure"] == "total_gc_ms"]
        assert gc[0].attrs["sides"] == ["before"]

    def test_a_medida_declara_as_chaves_que_ela_exige(self):
        facts = build_benchmark([_analyzed("a.jsonl")], [_analyzed("b.jsonl")])
        por_medida = {
            f.attrs["measure"]: f.attrs["keys"] for f in by_kind(facts, "bench.unresolved")
        }
        assert por_medida["total_task_ms"] == ["mean_ms", "task_count"]
        assert por_medida["total_spill_bytes"] == [
            "total_memory_spill_bytes",
            "total_disk_spill_bytes",
        ]

    def test_cada_unresolved_tem_id_proprio(self):
        """`Fact.id` e sha1 de (kind, subject, measures) -- `attrs` fica de fora.
        Unresolved sem subject proprio colidiria com os outros quatro."""
        facts = build_benchmark([_analyzed("a.jsonl")], [_analyzed("b.jsonl")])
        unresolved = by_kind(facts, "bench.unresolved")
        assert len(unresolved) == 5
        assert len({f.id for f in unresolved}) == 5


class TestCasamentoDeStage:
    def test_stage_com_symbol_identico_casa_e_o_resto_e_contado(self):
        before = [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=200), _stage("join_antigo", 1)]
        after = [_analyzed("b.jsonl"), _stage("scan", 7, mean_ms=100), _stage("join_novo", 8)]

        facts = build_benchmark(before, after)

        matched = by_kind(facts, "bench.stage_delta")
        assert [f.subject["symbol"] for f in matched] == ["scan"]
        assert matched[0].measures["total_task_ms_delta_pct"] == -50.0

        unmatched = sorted(f.attrs["symbol"] for f in by_kind(facts, "bench.unmatched"))
        assert unmatched == ["join_antigo", "join_novo"]

        sentinela = by_kind(facts, "bench.analyzed")[0]
        # Contagem de STAGE, dos dois lados: `scan` casou com um stage de cada
        # lado, entao dois stages estao cobertos por um delta. O plano dizia 1
        # aqui -- ver D-4a-8.
        assert sentinela.measures["matched_stage_count"] == 2
        assert sentinela.measures["unmatched_stage_count"] == 2

    def test_stage_id_diferente_nao_impede_o_casamento(self):
        """`stage_id` NAO e estavel entre execucoes -- o mesmo stage sai com id
        diferente em cada run. Casar por id produziria pares errados."""
        before = [_analyzed("a.jsonl"), _stage("scan", 0)]
        after = [_analyzed("b.jsonl"), _stage("scan", 99)]
        assert len(by_kind(build_benchmark(before, after), "bench.stage_delta")) == 1

    def test_o_subject_do_delta_nao_carrega_stage_id(self):
        """`stage_id` no subject faria o `Fact.id` do delta depender de um numero
        instavel: o mesmo par de execucoes daria ids diferentes so porque o
        scheduler numerou os stages de outro jeito."""
        def _delta(antes: int, depois: int) -> Fact:
            facts = build_benchmark(
                [_analyzed("a.jsonl"), _stage("scan", antes)],
                [_analyzed("b.jsonl"), _stage("scan", depois)],
            )
            return by_kind(facts, "bench.stage_delta")[0]

        um, outro = _delta(0, 1), _delta(4, 9)

        assert "stage_id" not in um.subject
        assert um.subject == {"type": "stage", "symbol": "scan"}
        assert um.id == outro.id

    def test_symbol_vazio_nunca_casa(self):
        """Casar dois vazios juntaria stages que so tem em comum o fato de nao
        terem nome."""
        before = [_analyzed("a.jsonl"), _stage("", 0)]
        after = [_analyzed("b.jsonl"), _stage("", 0)]

        facts = build_benchmark(before, after)

        assert by_kind(facts, "bench.stage_delta") == []
        unmatched = by_kind(facts, "bench.unmatched")
        assert [f.attrs["reason"] for f in unmatched] == ["empty_symbol", "empty_symbol"]
        assert sorted(f.attrs["side"] for f in unmatched) == ["after", "before"]
        sentinela = by_kind(facts, "bench.analyzed")[0]
        assert sentinela.measures["matched_stage_count"] == 0
        assert sentinela.measures["unmatched_stage_count"] == 2

    def test_stage_sem_nome_dos_dois_lados_nao_colide_no_id(self):
        """`Fact.id` e sha1 de (kind, subject, measures) e ignora `attrs`: sem o
        lado no subject, o mesmo stage sem nome nos dois runs sairia com um id
        so, e um dos dois sumiria da saida."""
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _stage("", 0), _stage("", 1)],
            [_analyzed("b.jsonl"), _stage("", 0)],
        )
        unmatched = by_kind(facts, "bench.unmatched")
        assert len(unmatched) == 3
        assert len({f.id for f in unmatched}) == 3

    def test_stage_sem_nome_com_id_nao_numerico_nao_colide_nem_quebra_o_schema(self):
        """O `stage_id` de um arquivo de facts nao e necessariamente inteiro, e o
        schema recusa `stage_id` que nao seja inteiro >= 0 -- entao a identidade
        do stage sem nome vive no `symbol` do subject, nao numa chave que ora
        entra ora nao."""
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _sem_nome("a"), _sem_nome("b")],
            [_analyzed("b.jsonl"), _sem_nome("a", artifact="b.jsonl")],
        )

        unmatched = by_kind(facts, "bench.unmatched")
        assert len(unmatched) == 3
        assert len({f.id for f in unmatched}) == 3
        assert sorted(f.attrs["stage_ids"][0] for f in unmatched) == ["a", "a", "b"]
        for fact in facts:
            validate_fact(fact.to_dict())

    def test_o_subject_do_unmatched_com_nome_nao_mutila_o_symbol(self):
        """Simbolo nomeado aparece num lado so por construcao -- nao ha colisao
        para resolver ali, e `"join#before"` no subject seria mutilacao sem
        ganho."""
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _stage("join", 1)], [_analyzed("b.jsonl"), _stage("scan", 2)]
        )
        assert sorted(f.subject["symbol"] for f in by_kind(facts, "bench.unmatched")) == [
            "join",
            "scan",
        ]

    def test_dois_stages_com_o_mesmo_symbol_no_mesmo_lado_somam_juntos(self):
        """O mesmo `symbol` pode nascer varias vezes num run (linha dentro de
        laco, funcao chamada duas vezes). O recorte e o SIMBOLO: as medidas somam
        os stages dele, e as duas contagens dizem quantos stages entraram de cada
        lado -- sem elas, um stage que sumiu seria lido como stage que acelerou."""
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0, mean_ms=100),
            _stage("scan", 1, mean_ms=100),
        ]
        after = [_analyzed("b.jsonl"), _stage("scan", 5, mean_ms=100)]

        facts = build_benchmark(before, after)

        delta = by_kind(facts, "bench.stage_delta")[0]
        assert delta.measures["total_task_ms_before"] == 2000
        assert delta.measures["total_task_ms_after"] == 1000
        assert delta.measures["before_stage_count"] == 2
        assert delta.measures["after_stage_count"] == 1
        assert delta.attrs["before_stage_ids"] == ["0", "1"]
        assert delta.attrs["after_stage_ids"] == ["5"]
        assert by_kind(facts, "bench.analyzed")[0].measures["matched_stage_count"] == 3

    def test_nenhum_stage_fica_fora_da_contagem(self):
        """Casados mais nao casados fecham a conta dos dois lados: e a disciplina
        de `opaque_caller_function_count` da Fase 5b, aritmetica."""
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0),
            _stage("scan", 1),
            _stage("so_no_antes", 2),
            _stage("", 3),
        ]
        after = [_analyzed("b.jsonl"), _stage("scan", 9), _stage("so_no_depois", 8)]

        sentinela = by_kind(build_benchmark(before, after), "bench.analyzed")[0]

        assert sentinela.measures["before_stage_count"] == 4
        assert sentinela.measures["after_stage_count"] == 2
        assert sentinela.measures["matched_stage_count"] == 3
        assert sentinela.measures["unmatched_stage_count"] == 3
        assert (
            sentinela.measures["matched_stage_count"]
            + sentinela.measures["unmatched_stage_count"]
            == sentinela.measures["before_stage_count"] + sentinela.measures["after_stage_count"]
        )

    def test_o_unmatched_nomeia_o_lado_e_os_stages(self):
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _stage("sumiu", 10), _stage("sumiu", 2)],
            [_analyzed("b.jsonl"), _stage("nasceu", 1)],
        )

        por_symbol = {f.attrs["symbol"]: f for f in by_kind(facts, "bench.unmatched")}
        assert por_symbol["sumiu"].attrs["side"] == "before"
        assert por_symbol["sumiu"].attrs["reason"] == "symbol_absent_on_other_side"
        # Ordem numerica, nao lexica: `["10", "2"]` seria deterministico e
        # ilegivel na evidencia.
        assert por_symbol["sumiu"].attrs["stage_ids"] == ["2", "10"]
        assert por_symbol["sumiu"].measures["stage_count"] == 2
        assert por_symbol["nasceu"].attrs["side"] == "after"


class TestOStageHerdaAsRegrasDePresenca:
    def test_chave_ausente_no_recorte_do_stage_nao_vira_zero(self):
        sem_chave = Fact(
            kind="spark.stage.task_duration",
            subject={"type": "stage", "symbol": "scan", "stage_id": 0},
            measures={"mean_ms": 200},
            provenance=_prov("a.jsonl"),
        )
        facts = build_benchmark(
            [_analyzed("a.jsonl"), sem_chave],
            [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100)],
        )

        delta = by_kind(facts, "bench.stage_delta")[0]
        assert "total_task_ms_before" not in delta.measures
        assert delta.measures["total_task_ms_after"] == 1000
        assert "total_task_ms_delta_pct" not in delta.measures

    def test_lado_parcial_no_recorte_do_stage_tambem_e_ausencia(self):
        parcial = Fact(
            kind="spark.stage.task_input",
            subject={"type": "stage", "symbol": "scan", "stage_id": 1},
            measures={"max_bytes": 10},
            provenance=_prov("a.jsonl"),
        )
        before = [_analyzed("a.jsonl"), _stage("scan", 0), _task_input("scan", 0, 1000), parcial]
        after = [
            _analyzed("b.jsonl"),
            _stage("scan", 0),
            _task_input("scan", 0, 1500, artifact="b.jsonl"),
        ]

        delta = by_kind(build_benchmark(before, after), "bench.stage_delta")[0]

        assert "total_input_bytes_before" not in delta.measures
        assert delta.measures["total_input_bytes_after"] == 1500
        assert "total_input_bytes_delta_pct" not in delta.measures

    def test_delta_pct_do_stage_some_quando_o_lado_antes_e_zero(self):
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=0)],
            [_analyzed("b.jsonl"), _stage("scan", 0, mean_ms=100)],
        )
        delta = by_kind(facts, "bench.stage_delta")[0]
        assert delta.measures["total_task_ms_before"] == 0
        assert "total_task_ms_delta_pct" not in delta.measures

    def test_o_resumo_de_spill_do_job_nao_vaza_para_o_recorte_de_stage(self):
        """`spark.job.spill_summary` tem subject de JOB: rateá-lo entre os stages
        inventaria atribuicao que o event log nao da. O spill por stage existe --
        `spark.stage.spill` --, e e de la que o recorte de stage le."""
        before = [_analyzed("a.jsonl"), _stage("scan", 0), _spill_summary("app-1", 600, 400)]
        after = [
            _analyzed("b.jsonl"),
            _stage("scan", 0),
            _spill_summary("app-2", 300, 200, artifact="b.jsonl"),
        ]

        delta = by_kind(build_benchmark(before, after), "bench.stage_delta")[0]

        assert not [k for k in delta.measures if k.startswith("total_spill_bytes")]

    def test_o_stage_carrega_o_spill_do_kind_de_stage(self):
        """Sem isto, `SF-BENCH-003` -- "mais rapido mas derramando" -- fica sem
        evidencia no unico recorte onde ela e acionavel."""
        before = [_analyzed("a.jsonl"), _stage_spill("scan", 0, 900, 100)]
        after = [_analyzed("b.jsonl"), _stage_spill("scan", 7, 5, 5, artifact="b.jsonl")]

        delta = by_kind(build_benchmark(before, after), "bench.stage_delta")[0]

        assert delta.measures["total_spill_bytes_before"] == 1000
        assert delta.measures["total_spill_bytes_after"] == 10
        assert delta.measures["total_spill_bytes_delta_pct"] == -99.0

    def test_delta_pct_do_stage_some_quando_a_populacao_de_stages_muda(self):
        """Dois stages antes contra um depois, custo identico em cada um: o -50%
        seria queda de trabalho por stage que ninguem observou. Em todo outro
        caso onde a comparacao nao se sustenta -- chave parcial, medida de um lado
        so, base zero -- este modulo OMITE o `_delta_pct`; populacao diferente e o
        mesmo caso, e a razao vai em `attrs` para nao virar chave que sumiu sem
        explicacao."""
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0, mean_ms=100),
            _stage("scan", 1, mean_ms=100),
        ]
        after = [_analyzed("b.jsonl"), _stage("scan", 5, mean_ms=100)]

        delta = by_kind(build_benchmark(before, after), "bench.stage_delta")[0]

        assert delta.measures["total_task_ms_before"] == 2000
        assert delta.measures["total_task_ms_after"] == 1000
        assert "total_task_ms_delta_pct" not in delta.measures
        assert delta.attrs["delta_pct_omitted"] == "stage_count_changed"

    def test_delta_pct_do_stage_fica_quando_a_populacao_e_a_mesma(self):
        delta = by_kind(
            build_benchmark(
                [_analyzed("a.jsonl"), _stage("scan", 0, mean_ms=200)],
                [_analyzed("b.jsonl"), _stage("scan", 9, mean_ms=100)],
            ),
            "bench.stage_delta",
        )[0]
        assert delta.measures["total_task_ms_delta_pct"] == -50.0
        assert "delta_pct_omitted" not in delta.attrs

    def test_medida_que_some_de_um_simbolo_casado_e_nomeada(self):
        """O simbolo `y` casa nos dois lados e perdeu o fact de gc no depois:
        `_side_totals` afere presenca DENTRO dos facts que existem, entao o depois
        sai `usable` e o run afirma -75% que ninguem observou. So a partir do
        casamento da Task 2 o modulo sabe quais simbolos existem nos dois lados --
        e portanto so agora isso e detectavel."""
        before = [_analyzed("a.jsonl"), _gc("x", 0, 10), _gc("y", 1, 10), _stage("y", 1)]
        after = [
            _analyzed("b.jsonl"),
            _gc("x", 0, 5, artifact="b.jsonl"),
            _stage("y", 1, artifact="b.jsonl"),
        ]

        facts = build_benchmark(before, after)

        furo = [
            f
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["reason"] == "measure_absent_for_matched_symbol"
        ]
        assert [(f.attrs["symbol"], f.attrs["measure"], f.attrs["sides"]) for f in furo] == [
            ("y", "total_gc_ms", ["after"])
        ]

    def test_o_furo_de_simbolo_casado_tira_o_percentual_do_run(self):
        """Os totais ficam -- foram observados --, mas a razao entre eles some:
        o lado furado e piso, e piso contra total fabrica melhora. A medida sem
        furo no mesmo par mantem o percentual."""
        before = [_analyzed("a.jsonl"), _gc("x", 0, 10), _gc("y", 1, 10), _stage("y", 1)]
        after = [
            _analyzed("b.jsonl"),
            _gc("x", 0, 5, artifact="b.jsonl"),
            _stage("y", 1, artifact="b.jsonl"),
        ]

        delta = only_delta(build_benchmark(before, after))

        assert delta.measures["total_gc_ms_before"] == 20
        assert delta.measures["total_gc_ms_after"] == 5
        assert "total_gc_ms_delta_pct" not in delta.measures
        assert delta.measures["total_task_ms_delta_pct"] == 0.0

    def test_simbolo_nao_casado_nao_tira_o_percentual_do_run(self):
        """Assimetria deliberada: stage que sumiu entre os runs e mudanca de
        TRABALHO, que e o que o benchmark existe para relatar. `bench.unmatched`
        ja o nomeia."""
        before = [_analyzed("a.jsonl"), _gc("x", 0, 10), _gc("sumiu", 1, 10)]
        after = [_analyzed("b.jsonl"), _gc("x", 0, 5, artifact="b.jsonl")]

        facts = build_benchmark(before, after)

        assert only_delta(facts).measures["total_gc_ms_delta_pct"] == -75.0
        assert [f.attrs["symbol"] for f in by_kind(facts, "bench.unmatched")] == ["sumiu"]

    def test_o_furo_por_simbolo_casado_tem_id_proprio(self):
        before = [_analyzed("a.jsonl"), _gc("x", 0, 10), _gc("y", 1, 10)]
        after = [
            _analyzed("b.jsonl"),
            _stage("x", 0, artifact="b.jsonl"),
            _stage("y", 1, artifact="b.jsonl"),
        ]

        furo = [
            f
            for f in by_kind(build_benchmark(before, after), "bench.unresolved")
            if f.attrs["reason"] == "measure_absent_for_matched_symbol"
        ]

        # Dois simbolos, e em cada um a medida que so o antes tem (gc) e a que so
        # o depois tem (duracao): quatro furos, e o subject precisa do simbolo E
        # da medida para os quatro terem id proprio.
        assert sorted((f.attrs["symbol"], f.attrs["measure"]) for f in furo) == [
            ("x", "total_gc_ms"),
            ("x", "total_task_ms"),
            ("y", "total_gc_ms"),
            ("y", "total_task_ms"),
        ]
        assert len({f.id for f in furo}) == 4

    def test_medida_ausente_dos_dois_lados_do_simbolo_nao_vira_furo(self):
        """Ausente nos dois lados nao fabrica nada: nao ha piso contra total."""
        facts = build_benchmark(
            [_analyzed("a.jsonl"), _stage("scan", 0)],
            [_analyzed("b.jsonl"), _stage("scan", 0)],
        )
        assert not [
            f
            for f in by_kind(facts, "bench.unresolved")
            if f.attrs["reason"] == "measure_absent_for_matched_symbol"
        ]

    def test_o_recorte_de_stage_nao_multiplica_o_unresolved(self):
        """Um `bench.unresolved` por medida ausente, nao um por medida por stage:
        o furo e da comparacao, e repeti-lo por stage seria ruido proporcional ao
        numero de stages, escondendo os outros achados."""
        before = [_analyzed("a.jsonl"), _stage("a", 0), _stage("b", 1), _stage("c", 2)]
        after = [_analyzed("b.jsonl"), _stage("a", 0), _stage("b", 1), _stage("c", 2)]

        facts = build_benchmark(before, after)

        gc = [f for f in by_kind(facts, "bench.unresolved") if f.attrs["measure"] == "total_gc_ms"]
        assert len(gc) == 1


class TestSentinela:
    def test_a_sentinela_conta_os_stages_dos_dois_lados(self):
        before = [_analyzed("a.jsonl"), _stage("scan", 0), _stage("join", 1), _gc("scan", 0, 1)]
        after = [_analyzed("b.jsonl"), _stage("scan", 7)]

        sentinela = by_kind(build_benchmark(before, after), "bench.analyzed")[0]

        assert sentinela.measures["before_stage_count"] == 2
        assert sentinela.measures["after_stage_count"] == 1
        assert sentinela.measures["matched_stage_count"] == 2
        assert sentinela.measures["unmatched_stage_count"] == 1

    def test_a_sentinela_separa_stage_casado_de_delta_emitido(self):
        """`matched_stage_count` conta STAGE e `stage_delta_count` conta FACT: com
        simbolo homonimo os dois divergem, e contar os `bench.stage_delta` da
        pagina nao serve -- `_facts_page` pagina, entao a pagina nao e o total."""
        before = [
            _analyzed("a.jsonl"),
            _stage("scan", 0),
            _stage("scan", 1),
            _stage("join", 2),
        ]
        after = [_analyzed("b.jsonl"), _stage("scan", 5), _stage("join", 6)]

        facts = build_benchmark(before, after)

        sentinela = by_kind(facts, "bench.analyzed")[0]
        assert sentinela.measures["matched_stage_count"] == 5
        assert sentinela.measures["stage_delta_count"] == 2
        assert len(by_kind(facts, "bench.stage_delta")) == 2

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
            # Um stage que so existe no antes e um sem nome: os cinco kinds do
            # namespace precisam passar pelo schema, nao so os tres do caminho
            # feliz.
            _stage("sumiu", 4),
            _stage("", 5),
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
