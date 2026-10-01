"""Experiment Engine — designer de experimentos para resolver desacordo.

Um experimento muda UMA variável, mantém controls, e declara:
- expected_results
- success_criteria (machine-checkable quando possível)
- failure_criteria
- rollback
- cost_estimate
- time_estimate

O engine gera experimentos a partir de:
- hipóteses conflitantes
- debates deadlockados
- unknowns blocking
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sparkforge.agentic.models import Experiment, ExperimentStatus, Hypothesis


@dataclass
class ExperimentPlan:
    """Plano de experimento gerado pelo engine.

    Um plano pode gerar múltiplos Experiment objects (um por variável testada).
    """

    hypothesis_id: str
    rationale: str  # por que este experimento
    experiments: list[Experiment] = field(default_factory=list)
    total_cost_estimate: str = ""
    total_time_estimate: str = ""
    risk_level: str = "low"  # low/medium/high/critical


def design_experiment(
    hypothesis: Hypothesis,
    variable: str,
    baseline: str,
    controls: list[str] | None = None,
    proposed_by: str = "",
    cost_estimate: str = "",
    time_estimate: str = "",
) -> Experiment:
    """Design um experimento para testar uma hipótese.

    Uma variável mudada. Baseline e controls explícitos.
    Success e failure criteria derivados da hipótese.

    `cost_estimate` e `time_estimate` vêm de QUEM CHAMA, e ficam vazios se
    ninguém mediu. Até 2026-09-03 esta função escrevia "1 Glue job run
    (DPU-hours)" e "15-30 minutes" fixos em todo experimento — números
    inventados dentro de um repositório cuja regra 14 diz que sem
    `dpu_seconds` não há custo. Vazio é `unresolved`; texto fixo é ficção.
    """
    if not hypothesis.expected_outcome:
        raise ValueError("design_experiment: hipótese deve ter expected_outcome declarado")

    return Experiment(
        hypothesis_id=hypothesis.id,
        variable=variable,
        baseline=baseline,
        controls=controls or [],
        expected_results=hypothesis.expected_outcome,
        success_criteria=f"Measure: {hypothesis.expected_outcome}",
        failure_criteria=(
            f"Negation: "
            f"{hypothesis.failure_modes[0] if hypothesis.failure_modes else 'outcome not observed'}"
        ),
        rollback=f"Revert {variable} to baseline: {baseline}",
        cost_estimate=cost_estimate,
        time_estimate=time_estimate,
        proposed_by=proposed_by,
    )


def design_experiment_from_deadlock(
    hypothesis_a: Hypothesis,
    hypothesis_b: Hypothesis,
    variable: str,
    baseline: str,
    controls: list[str] | None = None,
    proposed_by: str = "",
    cost_estimate_per_run: str = "",
    time_estimate_per_run: str = "",
) -> ExperimentPlan:
    """Design experimentos para resolver deadlock entre duas hipóteses.

    Gera dois experimentos: um para cada hipótese, mesma variável,
    mesmo baseline. O que reproduzir o expected_outcome confirma a hipótese.

    Custo e tempo, quando o chamador os declara, aparecem por execução e no
    total como "2 × <o que ele declarou>" — a soma é aritmética sobre o que
    ele mediu, nunca um número novo inventado aqui.
    """
    exp_a = design_experiment(
        hypothesis_a,
        variable,
        baseline,
        controls,
        proposed_by,
        cost_estimate_per_run,
        time_estimate_per_run,
    )
    exp_b = design_experiment(
        hypothesis_b,
        variable,
        baseline,
        controls,
        proposed_by,
        cost_estimate_per_run,
        time_estimate_per_run,
    )

    return ExperimentPlan(
        hypothesis_id=hypothesis_a.id,
        rationale=(
            f"Deadlock between '{hypothesis_a.statement}' and "
            f"'{hypothesis_b.statement}'. Same variable, same baseline: "
            f"whichever reproduces its expected_outcome wins."
        ),
        experiments=[exp_a, exp_b],
        total_cost_estimate=f"2 x {cost_estimate_per_run}" if cost_estimate_per_run else "",
        total_time_estimate=f"2 x {time_estimate_per_run}" if time_estimate_per_run else "",
        risk_level="low",
    )


def design_experiment_for_unknown(
    unknown_question: str,
    variable: str,
    baseline: str,
    evidence_needed: list[str] | None = None,
    proposed_by: str = "",
) -> Experiment:
    """Design um experimento para resolver um unknown.

    O unknown vira hipótese: "se mudarmos X, esperamos Y".
    """
    # Cria hipótese implícita
    h = Hypothesis(
        statement=f"Resolving unknown: {unknown_question}",
        expected_outcome=f"Answer to: {unknown_question}",
        failure_modes=["Variable does not affect outcome"],
        confidence="low",
        falsification_method=f"Change {variable} and observe no effect",
        proposed_by=proposed_by,
    )

    return design_experiment(
        h,
        variable=variable,
        baseline=baseline,
        controls=evidence_needed,
        proposed_by=proposed_by,
    )


def evaluate_experiment_result(
    experiment: Experiment,
    observed_result: str,
    success_criteria_met: bool,
) -> tuple[ExperimentStatus, str]:
    """Avalia o resultado de um experimento executado.

    Retorna (new_status, reasoning).
    """
    if experiment.status != ExperimentStatus.RUNNING:
        raise ValueError(
            f"evaluate_experiment_result: experiment status={experiment.status.value}, "
            f"esperado=running"
        )

    if success_criteria_met:
        return (
            ExperimentStatus.SUCCEEDED,
            f"Success criteria met. Observed: {observed_result}. "
            f"Expected: {experiment.expected_results}.",
        )
    else:
        return (
            ExperimentStatus.FAILED,
            f"Success criteria NOT met. Observed: {observed_result}. "
            f"Expected: {experiment.expected_results}. "
            f"Hypothesis {experiment.hypothesis_id} may be refuted.",
        )
