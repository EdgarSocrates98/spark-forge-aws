from __future__ import annotations

import copy
from pathlib import Path

from sparkforge.adapters.tools import TOOLS
from sparkforge.context.gateway import ContextGateway
from sparkforge.evals.token_benchmark import (
    compare_benchmark_matrix,
    load_benchmark_suite,
    run_benchmark_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


def _suite() -> dict:
    return load_benchmark_suite(ROOT / "evals" / "token_efficient")


def test_suite_ampla_tem_eixos_e_casos_unicos() -> None:
    suite = _suite()
    assert len(suite["cases"]) >= 12
    assert len({case["id"] for case in suite["cases"]}) == len(suite["cases"])
    assert any("max_bytes" not in case for case in suite["cases"])
    assert set(suite["quality_axes"]) >= {
        "status",
        "evidence_recall",
        "false_positive_rate",
        "unresolved",
        "execution_plan",
    }
    assert "fixtures/decision_control_plane_cases.yaml" in suite["fixture_paths"]
    assert "fixtures/calibration_history.yaml" in suite["fixture_paths"]
    assert "fixtures/host_replay.yaml" in suite["fixture_paths"]
    assert len(suite["fixture_paths"]) >= 6


def test_matriz_preserva_eixos_e_bytes_separados() -> None:
    matrix = run_benchmark_matrix(_suite(), gateway=ContextGateway(TOOLS))
    assert len(matrix["results"]) == 45
    assert set(matrix["summary"]) == {"economy", "balanced", "deep"}
    assert all("payload_bytes" in item and "provider_tokens" in item for item in matrix["results"])
    assert all("score" not in item for item in matrix["results"])


def test_compare_matriz_por_eixo_sem_score_composto() -> None:
    before = run_benchmark_matrix(_suite(), gateway=ContextGateway(TOOLS))
    after = copy.deepcopy(before)
    after["results"][0]["payload_bytes"] += 7
    comparison = compare_benchmark_matrix(before, after)
    assert "refused" not in comparison
    changed = next(
        cell
        for cell in comparison["cells"]
        if cell["case_id"] == before["results"][0]["case_id"]
        and cell["profile"] == before["results"][0]["profile"]
    )
    assert changed["payload_bytes"]["delta"] == 7
    assert "score" not in comparison
    assert set(comparison["cells"][0]["quality"]) >= {
        "status", "evidence_recall", "false_positive_rate", "unresolved", "execution_plan"
    }
