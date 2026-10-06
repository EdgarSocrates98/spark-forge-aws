"""Suite de cenarios do circuito de recuperacao — `evals/agentic/recovery/`.

Cada caso e um diretorio com `case.yaml` (a entrada declarada: classe de
falha, tentativa, fingerprint, historico e, quando ha, o `gain_state` do
gate de parada) e `expected.yaml` (o desfecho). O driver repete o caso por
`RecoveryGovernor.resolve` — a mesma funcao do circuito em producao — e
confere acao, terminalidade e prefixo do motivo.

O gabarito NAO e copia do que o codigo emite hoje: cada `expected.yaml` e o
desfecho declarado pelo cenario, e o teste `test_gabarito_e_derived_do_policy`
reconfere o desfecho esperado pela composicao das duas politicas
(`RecoveryPolicy` para a classe de falha, `StopPolicy` para o gain_state),
sem passar pelo governador — se o driver e a derivacao divergirem, o
cenario nao vale.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sparkforge.agentic.control import RecoveryGovernor
from sparkforge.agentic.recovery import FailureClass, RecoveryPolicy
from sparkforge.agentic.stop import ExpectedGainState, StopPolicy

SUITE = Path(__file__).resolve().parents[1] / "evals" / "agentic" / "recovery"

CAMPOS_CASE = {
    "schema_version",
    "case_id",
    "failure",
    "attempt",
    "strategy_fingerprint",
    "history",
    "profile",
    "risk",
    "gain_state",
}
CAMPOS_EXPECTED = {"schema_version", "action", "terminal", "reason_prefix"}


def _casos() -> list[str]:
    return sorted(p.name for p in SUITE.iterdir() if p.is_dir())


def _carrega(caso: str) -> tuple[dict, dict]:
    pasta = SUITE / caso
    case = yaml.safe_load((pasta / "case.yaml").read_text(encoding="utf-8"))
    expected = yaml.safe_load((pasta / "expected.yaml").read_text(encoding="utf-8"))
    return case, expected


def _resolve(case: dict):
    gain = case.get("gain_state")
    state = ExpectedGainState(**gain) if gain else None
    return RecoveryGovernor().resolve(
        case["failure"],
        attempt=case["attempt"],
        strategy_fingerprint=case["strategy_fingerprint"],
        history=tuple(case.get("history") or ()),
        profile=case.get("profile", "economy"),
        risk=case.get("risk", "low"),
        gain_state=state,
    )


def test_a_suite_tem_os_casos_declarados() -> None:
    assert set(_casos()) == {
        "security_refusal",
        "loop_fingerprint",
        "budget_exhausted_gate",
        "continue_on_gaps",
        "debate_sem_contradicao",
        "provider_bounded_retry",
        "context_insufficient_replan",
        "missing_evidence_abstain",
    }


@pytest.mark.parametrize("caso", _casos())
def test_case_e_expected_bem_formados(caso: str) -> None:
    case, expected = _carrega(caso)
    assert case["schema_version"] == 1
    assert expected["schema_version"] == 1
    assert set(case) <= CAMPOS_CASE
    assert set(expected) == CAMPOS_EXPECTED
    assert case["case_id"].startswith("recovery-")
    assert FailureClass(case["failure"]) in FailureClass


@pytest.mark.parametrize("caso", _casos())
def test_o_desfecho_replayado_confere_com_o_gabarito(caso: str) -> None:
    case, expected = _carrega(caso)
    governed = _resolve(case)
    assert governed.decision.action == expected["action"], caso
    assert governed.decision.terminal is expected["terminal"], caso
    assert governed.decision.reason.startswith(expected["reason_prefix"]), caso


@pytest.mark.parametrize("caso", _casos())
def test_gabarito_e_derived_do_policy(caso: str) -> None:
    """Recomputa o desfecho pelas politicas, sem o governador."""
    case, expected = _carrega(caso)
    gain = case.get("gain_state")
    stop = (
        StopPolicy().evaluate(ExpectedGainState(**gain)) if gain else None
    )
    if stop is not None and stop.stops:
        derived = ("stop", True, f"stop_gate:{stop.action.value}")
    else:
        decision = RecoveryPolicy().next(
            case["failure"],
            attempt=case["attempt"],
            strategy_fingerprint=case["strategy_fingerprint"],
            history=tuple(case.get("history") or ()),
        )
        derived = (decision.action, decision.terminal, decision.reason)
    assert derived[0] == expected["action"], caso
    assert derived[1] is expected["terminal"], caso
    assert expected["reason_prefix"] in derived[2] or derived[2].startswith(
        expected["reason_prefix"]
    ), caso
