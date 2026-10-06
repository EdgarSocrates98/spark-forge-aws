"""FASE 15 — knowledge impact graph: o salto `skills` (§147).

"Se o conhecimento X ficar stale → que skill/agente/regra/eval?" — o radar
propagava para goldens/evals/agents mas skills citam `SF-*` no corpo do
SKILL.md e ficavam fora do grafo. Skills entram pelo mesmo mecanismo dos
agentes: citacao textual de rule_id, sem heuristica.
"""

from __future__ import annotations

from pathlib import Path

from sparkforge_aws.knowledge_drift import (
    IMPACTO,
    SALTOS_DO_REPOSITORIO,
    build_index,
    drift,
)

ROOT = Path(__file__).resolve().parents[1]


def test_skills_e_salto_declarado() -> None:
    assert "skills" in SALTOS_DO_REPOSITORIO
    assert "skills" in IMPACTO


def test_build_index_varre_skills() -> None:
    index = build_index(ROOT)
    assert isinstance(index.skill_citations, dict)
    # skills/analyze-batch-loop/SKILL.md cita SF-PY-004 no corpo — medido.
    citam_py004 = index.skill_citations.get("SF-PY-004", frozenset())
    assert any("skills/analyze-batch-loop" in s for s in citam_py004)


def test_impacto_reporta_skills_quando_regra_fica_stale() -> None:
    index = build_index(ROOT)
    lock = {
        "https://example.com/mudou": {
            "checked_at": "2026-01-01",
            "changed_at": "2026-02-01",
        }
    }
    rules = [
        {
            "id": "SF-PY-004",
            "sources": [
                {"url": "https://example.com/mudou", "retrieved": "2026-01-15"}
            ],
        }
    ]
    out = drift(lock, None, rules, {}, index, __import__("datetime").date(2026, 2, 10))
    [fonte] = out["changed_sources"]
    impacto = fonte["impact"]
    assert "skills" in impacto
    assert any("analyze-batch-loop" in s for s in impacto["skills"])


def test_sem_repositorio_skills_sai_unresolved() -> None:
    out = drift(
        {"https://x": {"checked_at": "2026-01-01", "changed_at": "2026-02-01"}},
        None,
        [],
        {},
        None,
        __import__("datetime").date(2026, 2, 10),
    )
    campos = {u["field"] for u in out["unresolved"]}
    assert "skills" in campos


def test_checkout_sem_diretorio_skills_reporta_unresolved_nao_vazio(tmp_path: Path) -> None:
    """Repo presente mas `skills/` ausente: o salto e `unresolved`, nunca `[]`
    fingindo que nenhuma skill cita a regra."""
    (tmp_path / "fixtures").mkdir()
    (tmp_path / "evals").mkdir()
    (tmp_path / "agents").mkdir()
    index = build_index(tmp_path)
    assert index.skill_citations is None
    out = drift(
        {"https://x": {"checked_at": "2026-01-01", "changed_at": "2026-02-01"}},
        None,
        [
            {
                "id": "SF-PY-004",
                "sources": [
                    {"url": "https://x", "retrieved": "2026-01-15"}
                ],
            }
        ],
        {},
        index,
        __import__("datetime").date(2026, 2, 10),
    )
    [fonte] = out["changed_sources"]
    assert fonte["impact"]["skills"] is None
    assert {"field": "skills", "reason": "sem_diretorio_skills"} in out["unresolved"]
