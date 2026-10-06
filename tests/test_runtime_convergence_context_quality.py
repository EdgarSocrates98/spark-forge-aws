"""FASE 8 do prompt_evo_runtime: Context Quality v3 -- semantica de metricas.

- §59-60: `useful_items_per_1k_tokens` (items de qualquer kind) e
  `useful_facts_per_1k_tokens` so conta kind=="fact" -- facts reais
  identificaveis, nao relevant renomeado.
- §58: `critical`, `used`, `cited`, `consumed` sao eixos distintos de
  `relevant`/`required`.
- §62: `usefulness_basis` registra de onde veio o julgamento de utilidade.
- §63-64: `CounterfactualContextBenchmark` para ablacao em eval/Lab.
"""

from __future__ import annotations

from sparkforge.context.quality import (
    ContextObservation,
    ContextQualityReport,
    CounterfactualContextBenchmark,
    MinimumSufficientContextBenchmark,
)


def _obs(item_id, *, kind="knowledge", relevant=True, bytes_=100, **kw):
    return ContextObservation(
        item_id=item_id,
        kind=kind,
        payload_bytes=bytes_,
        relevant=relevant,
        **kw,
    )


class TestUsefulItemsFacts:
    def test_items_conta_todo_kind_facts_so_fact(self):
        items = [
            _obs("i1", kind="fact"),
            _obs("i2", kind="rule"),
            _obs("i3", kind="code"),
        ]
        report = ContextQualityReport.from_items(items, observed_provider_tokens=1000)
        assert report.metrics["useful_items_per_1k_tokens"] == 3.0
        assert report.metrics["useful_facts_per_1k_tokens"] == 1.0

    def test_facts_metric_e_zero_sem_facts_nao_ausente(self):
        report = ContextQualityReport.from_items(
            [_obs("i1", kind="rule")], observed_provider_tokens=1000
        )
        assert report.metrics["useful_facts_per_1k_tokens"] == 0.0

    def test_sem_tokens_ambos_unresolved(self):
        report = ContextQualityReport.from_items([_obs("i1", kind="fact")])
        assert report.metrics["useful_items_per_1k_tokens"] == "tokens_unresolved"
        assert report.metrics["useful_facts_per_1k_tokens"] == "tokens_unresolved"


class TestEixosDistintos:
    def test_relevant_used_cited_consumed_sao_independentes(self):
        item = ContextObservation(
            item_id="x",
            kind="knowledge",
            payload_bytes=10,
            relevant=True,
            critical=True,
            used=True,
            cited=False,
            consumed=True,
        )
        report = ContextQualityReport.from_items([item])
        assert report.cited_count == 0
        assert report.consumed_count == 1
        assert report.used_count == 1

    def test_precision_registra_basis(self):
        report = ContextQualityReport.from_items(
            [_obs("i1")], usefulness_basis="evaluator_scored"
        )
        assert report.metrics["usefulness_basis"] == "evaluator_scored"
        padrao = ContextQualityReport.from_items([_obs("i1")])
        assert padrao.metrics["usefulness_basis"] == "caller_declared"


class TestCounterfactualAblation:
    def test_minimum_sufficient_empirico(self):
        # Cada ablacao remove um item; recall medido de verdade por passo.
        from sparkforge.context.quality import ContextObservation as C

        def report_sem(removidos):
            items = [i for i in full_items if i.item_id not in removidos]
            return ContextQualityReport.from_items(
                items,
                required_evidence_refs=["f1"],
                observed_provider_tokens=100 * len(items),
            )

        full_items = [
            C("a", "fact", 100, relevant=True, evidence_refs=("f1",)),
            C("b", "rule", 100, relevant=True),
            C("c", "code", 100, relevant=False),
        ]
        bench = CounterfactualContextBenchmark(
            full=ContextQualityReport.from_items(
                full_items,
                required_evidence_refs=["f1"],
                observed_provider_tokens=300,
            ),
            ablations=(
                (("c",), report_sem({"c"})),
                (("b", "c"), report_sem({"b", "c"})),
                (("a", "b", "c"), report_sem({"a", "b", "c"})),
            ),
            target_recall=1.0,
        )
        # Remover b+c preserva recall (f1 esta em a); tirar a quebra.
        assert bench.minimum_sufficient_removed() == ("b", "c")

    def test_sem_ablacao_suficiente_retorna_none(self):
        items = [ContextObservation("a", "fact", 10, relevant=True, evidence_refs=("f1",))]
        bench = CounterfactualContextBenchmark(
            full=ContextQualityReport.from_items(items, required_evidence_refs=["f1"]),
            ablations=(
                (("a",), ContextQualityReport.from_items((), required_evidence_refs=["f1"])),
            ),
            target_recall=1.0,
        )
        assert bench.minimum_sufficient_removed() is None


class TestMinimumSufficientPreservado:
    def test_statico_continua_funcionando(self):
        items = [ContextObservation("a", "fact", 10, relevant=True, evidence_refs=("f1",))]
        bench = MinimumSufficientContextBenchmark(
            levels=(
                ContextQualityReport.from_items(items, required_evidence_refs=["f1"]),
            )
        )
        assert bench.minimum_sufficient_level() == 0
