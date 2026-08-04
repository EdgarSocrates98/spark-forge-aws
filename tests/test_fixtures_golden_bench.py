"""Golden test do corpus de benchmark antes/depois.

Arquivo dedicado porque a fixture nao e extraida de UM artefato, e derivada de
DOIS: `extract_event_log_path` roda sobre `input/before.jsonl` e sobre
`input/after.jsonl`, e `build_benchmark` compara os dois conjuntos de facts. O
golden guarda so os derivados `bench.*` -- os facts de `event_log.py` que
serviram de entrada ja tem o corpus `fixtures/eventlog/`, e repeti-los aqui
faria uma mudanca no extrator quebrar dois goldens pelo mesmo motivo,
escondendo qual dos dois contratos regrediu. Mesma decisao de
`test_fixtures_golden_callgraph.py`.

Nesta fase os `expects_rules` sao todos `[]` e todo `findings.json` sai vazio:
as regras `SF-BENCH-*` nascem na Task 5 do plano da Fase 4a, que regenera este
corpus. Golden vazio aqui nao e pendencia -- e a linha de base contra a qual o
efeito das quatro regras vai ser lido.

`TestAdversarial` e a parte que impede a fixture de virar decoracao: cada
diretorio afirma no nome o que prova, e ali as medidas do golden sao lidas
contra essa afirmacao. Fixture cujo nome diz uma coisa e cujos numeros dizem
outra passa em todos os testes de igualdade acima e nao prova nada.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.benchmark import EMITTED_KINDS, build_benchmark
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "bench"

REQUIRED_FIXTURES = {
    "clean_improvement",
    "different_input_volume",
    "faster_but_spilling",
    "most_stages_renamed",
    "one_side_missing",
    "regression_slower",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    """Os dois lados extraidos e comparados, na MESMA ordem de chamada de
    `scripts/regen_fixtures.py::regen_bench`.

    `one_side_missing` nao tem `after.jsonl`, e a ausencia e o artefato:
    `extract_event_log_path` devolve um unico `spark.unresolved` quando nao
    consegue abrir o arquivo, e esse lado fica genuinamente sem
    `spark.log_analyzed` -- o unico caminho para isso, porque `extract_event_log`
    emite a sentinela para todo arquivo que ele consegue ler. Ver o `proves`
    daquele meta.yaml.
    """
    input_dir = directory / "input"
    before = extract_event_log_path(input_dir / "before.jsonl", repo_root=input_dir)
    after = extract_event_log_path(input_dir / "after.jsonl", repo_root=input_dir)
    return build_benchmark(before, after, path_hint=directory.name)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    derived = _derive(directory)
    findings, skipped = judge(derived, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, derived, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _one(facts, kind):
    matches = _by_kind(facts, kind)
    assert len(matches) == 1, f"esperado exatamente um {kind}, veio {len(matches)}"
    return matches[0]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_derivation_is_deterministic(self, directory):
        assert [f.to_dict() for f in _derive(directory)] == [
            f.to_dict() for f in _derive(directory)
        ]


class TestAdversarial:
    def test_the_corpus_exercises_every_kind_of_the_namespace(self):
        """Os cinco kinds de `EMITTED_KINDS` precisam nascer em algum diretorio
        daqui. `tests/test_fixtures_kind_coverage.py` faz a mesma pergunta sobre
        o corpus inteiro; esta copia local diz QUAL corpus deveria ter coberto,
        que e a informacao que falta quando aquele teste acende."""
        kinds = set()
        for directory in fixture_dirs():
            kinds |= {f.kind for f in _derive(directory)}
        assert kinds == set(EMITTED_KINDS)

    def test_clean_improvement_gives_the_four_rules_nothing_to_hold(self):
        """A metade negativa. Mesmo volume, mesmos stages, sem spill dos dois
        lados e menos tempo de task: nao ha nada aqui que uma regra SF-BENCH
        honesta possa acusar."""
        _, facts, _, _ = run_fixture(FIXTURES / "clean_improvement")
        delta = _one(facts, "bench.run_delta")
        analyzed = _one(facts, "bench.analyzed")
        assert delta.measures["total_input_bytes_delta_pct"] == 0.0
        assert delta.measures["total_task_ms_delta_pct"] < 0
        assert delta.measures["total_gc_ms_delta_pct"] < 0
        assert delta.measures["total_spill_bytes_before"] == 0
        assert delta.measures["total_spill_bytes_after"] == 0
        # Spill zero nos dois lados: o percentual e OMITIDO, nao zerado --
        # dividir por zero e "nao sei", e chave ausente e como este motor diz
        # isso. Uma regra sobre delta de spill simplesmente nao avalia aqui.
        assert "total_spill_bytes_delta_pct" not in delta.measures
        assert analyzed.measures["unmatched_stage_count"] == 0
        assert _by_kind(facts, "bench.unmatched") == []

    def test_regression_slower_sums_more_task_time_on_the_same_volume(self):
        _, facts, _, _ = run_fixture(FIXTURES / "regression_slower")
        delta = _one(facts, "bench.run_delta")
        assert delta.measures["total_task_ms_after"] > delta.measures["total_task_ms_before"]
        assert delta.measures["total_task_ms_delta_pct"] > 25
        # A piora nao e atribuivel ao dado nem a memoria: o volume e o mesmo e
        # ninguem derramou. Sem isso a fixture provaria "ficou mais lento por
        # algum motivo", que nao e o que o nome dela diz.
        assert delta.measures["total_input_bytes_delta_pct"] == 0.0
        assert delta.measures["total_spill_bytes_after"] == 0

    def test_different_input_volume_reads_twice_as_much_on_the_after_side(self):
        _, facts, _, _ = run_fixture(FIXTURES / "different_input_volume")
        delta = _one(facts, "bench.run_delta")
        assert delta.measures["total_input_bytes_delta_pct"] == 100.0

    def test_different_input_volume_still_carries_every_other_measure(self):
        """O D-4 do spec, no golden: volume divergente NAO cala as demais
        medidas. Elas afirmam sobre o que foi medido; o achado de volume diz que
        o que foi medido nao sustenta conclusao sobre a mudanca. Suprimir uma
        das duas leituras daria um quadro falso."""
        _, facts, _, _ = run_fixture(FIXTURES / "different_input_volume")
        delta = _one(facts, "bench.run_delta")
        for measure in ("total_task_ms", "total_gc_ms", "total_task_count"):
            assert f"{measure}_delta_pct" in delta.measures, measure
        assert delta.measures["total_task_ms_delta_pct"] > 0

    def test_faster_but_spilling_buys_the_time_with_memory(self):
        _, facts, _, _ = run_fixture(FIXTURES / "faster_but_spilling")
        delta = _one(facts, "bench.run_delta")
        assert delta.measures["total_task_ms_delta_pct"] < 0
        assert delta.measures["total_spill_bytes_delta_pct"] > 0
        assert delta.measures["total_gc_ms_delta_pct"] > 0
        # Volume identico: sem isso o ganho de tempo poderia ser so menos dado.
        assert delta.measures["total_input_bytes_delta_pct"] == 0.0

    def test_most_stages_renamed_leaves_the_majority_without_a_pair(self):
        _, facts, _, _ = run_fixture(FIXTURES / "most_stages_renamed")
        analyzed = _one(facts, "bench.analyzed")
        matched = analyzed.measures["matched_stage_count"]
        unmatched = analyzed.measures["unmatched_stage_count"]
        assert unmatched > matched
        assert unmatched / (matched + unmatched) > 0.5
        # A conta fecha dos dois lados: nenhum stage cai fora dela.
        assert matched + unmatched == (
            analyzed.measures["before_stage_count"] + analyzed.measures["after_stage_count"]
        )
        # `stage_delta_count` conta FACT emitido e diverge de `matched_stage_count`
        # -- ler o segundo como "quantos deltas" e o erro que o primeiro impede.
        assert analyzed.measures["stage_delta_count"] == len(_by_kind(facts, "bench.stage_delta"))
        assert analyzed.measures["stage_delta_count"] != matched

    def test_most_stages_renamed_shows_both_reasons_a_stage_has_no_pair(self):
        """Renomear e uma das razoes; a outra e nao ter nome nenhum. O stage 9
        do lado depois aparece so via TaskEnd -- log truncado --, sai com
        `symbol` vazio, e stage sem nome nao casa com nada: casar dois vazios
        juntaria stages que so tem em comum o fato de nao terem nome."""
        _, facts, _, _ = run_fixture(FIXTURES / "most_stages_renamed")
        reasons = {f.attrs["reason"] for f in _by_kind(facts, "bench.unmatched")}
        assert reasons == {"symbol_absent_on_other_side", "empty_symbol"}

    def test_one_side_missing_refuses_to_compare_at_all(self):
        """Um lado sem `spark.log_analyzed` nao vira delta com o lado zerado --
        isso afirmaria que aquela execucao nao fez trabalho nenhum. Vira um
        unico ponto cego, e sem `bench.run_delta` nenhuma regra SF-BENCH pode
        disparar sobre uma comparacao que nunca aconteceu."""
        _, facts, _, _ = run_fixture(FIXTURES / "one_side_missing")
        blind = _one(facts, "bench.unresolved")
        assert blind.attrs["reason"] == "missing_log_analyzed"
        assert blind.attrs["sides"] == ["after"]
        assert _by_kind(facts, "bench.run_delta") == []
        assert _by_kind(facts, "bench.analyzed") == []
        assert len(facts) == 1

    def test_the_before_side_of_one_side_missing_is_a_healthy_log(self):
        """Guarda do proprio caso negativo: se o lado ANTES tambem deixasse de
        produzir a sentinela, a fixture continuaria verde provando outra coisa
        -- "os dois lados faltaram" em vez de "um lado faltou"."""
        input_dir = FIXTURES / "one_side_missing" / "input"
        before = extract_event_log_path(input_dir / "before.jsonl", repo_root=input_dir)
        assert [f for f in before if f.kind == "spark.log_analyzed"]
        assert [f for f in before if f.kind == "spark.unresolved"] == []
