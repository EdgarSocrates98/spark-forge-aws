"""O SDD no perfil operator (feature SDD_OPERATOR).

O fluxo ponta a ponta usa as tools reais: `sparkforge_case_open` grava o case e
`sparkforge_change_sandbox` cria o sandbox cujo id vira `change_id`. Nada de
`.sparkforge/` fabricado a mao -- isso o teste do nucleo ja faz.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from sparkforge.adapters.tools import call_tool
from sparkforge.sdd.checks import check
from sparkforge.sdd.stamp import stamp

ROOT = Path(__file__).resolve().parents[1]
FEATURE = "JOB_SHUFFLE"
_NOW = "2026-09-16T00:00:00Z"

_JOB = b'def configurar(spark):\n    spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
_TESTE_DO_JOB = b"def test_configurar():\n    assert True\n"
_DIFF = (
    b"--- a/lib/job.py\n"
    b"+++ b/lib/job.py\n"
    b"@@ -1,2 +1,2 @@\n"
    b" def configurar(spark):\n"
    b'-    spark.conf.set("spark.sql.shuffle.partitions", "800")\n'
    b"+    return spark\n"
)

# a forma de `sparkforge/facts/funcval.py::_check_delta`
_DELTA = {
    "id": "d1",
    "kind": "funcval.check_delta",
    "subject": {"type": "table", "symbol": "db.vendas#row_count"},
    "measures": {"before": 10, "after": 10},
    "attrs": {"axis": "count", "check": "row_count", "comparison": "exact",
              "planned": True, "target": "db.vendas", "type": "bigint"},
    "provenance": {"artifact": "compare", "artifact_sha256": "", "extractor": "funcval"},
}


def _grava(repo: Path, fase: str, meta: dict) -> Path:
    pasta = repo / "docs" / "sdd" / FEATURE
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    texto = "---\n" + yaml.safe_dump(meta, sort_keys=False) + "---\ncorpo\n"
    arquivo.write_bytes(texto.encode("utf-8"))
    if "upstream" in meta:
        stamp(repo, f"docs/sdd/{FEATURE}/{fase}.md")
    return arquivo


def _upstream(fase: str) -> dict:
    return {"path": f"docs/sdd/{FEATURE}/{fase}.md", "sha256": ""}


def _repositorio_do_operador(repo: Path) -> Path:
    (repo / "lib").mkdir(parents=True)
    (repo / "lib" / "job.py").write_bytes(_JOB)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_job.py").write_bytes(_TESTE_DO_JOB)
    diff = repo.parent / "d.patch"
    diff.write_bytes(_DIFF)
    return diff


def _feature_operator(repo: Path, case_id: str, change_id: str) -> None:
    comum = {"sdd": 1, "feature": FEATURE, "profile": "operator", "status": "done"}
    _grava(repo, "define", {
        **comum,
        "phase": "define",
        "case_id": case_id,
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [{
            "id": "AC1",
            "statement": "o resultado nao muda",
            "verified_by": {"kind": "funcval", "ref": "out/compare.json"},
        }],
        "success": [{"id": "SC1", "metric": "m", "source": "out/compare.json"}],
        "out_of_scope": [],
        "change_kinds": ["tool_or_verb"],
    })
    _grava(repo, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream("define"),
        "files": [{"path": "lib/job.py", "action": "modify", "reason": "r"}],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "rollback.patch"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    })
    _grava(repo, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream("design"),
        "tasks": [{
            "id": "T1",
            "files": ["lib/job.py"],
            "covers": ["AC1"],
            "test": {"path": "tests/test_job.py", "name": "test_configurar"},
        }],
    })
    _grava(repo, "build_report", {
        **comum,
        "phase": "build_report",
        "upstream": _upstream("plan"),
        "change_id": change_id,
        "tasks": [{
            "id": "T1",
            "status": "done",
            "red": {"command": "pytest tests/test_job.py", "exit": 1},
            "green": {"command": "pytest tests/test_job.py", "exit": 0},
        }],
        "claims": [{"text": "resultado igual", "evidence_ref": "out/compare.json"}],
    })
    _grava(repo, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream("build_report"),
        "hypothesis_outcome": "confirmed",
        "registries": ["surface_lock", "generated_reference"],
        "deviations": [],
    })


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(r["code"] for r in relatorio["unresolved"]),
    )


def test_fluxo_operator_ponta_a_ponta(tmp_path):
    repo = tmp_path / "repo"
    diff = _repositorio_do_operador(repo)

    caso = call_tool("sparkforge_case_open", {"repo": str(repo), "case_id": "C-42", "now": _NOW})
    assert caso.get("case_id") == "C-42", caso
    sandbox = call_tool("sparkforge_change_sandbox", {"repo": str(repo), "diff_path": str(diff)})
    change_id = sandbox.get("id")
    assert change_id and (repo / ".sparkforge" / "sandbox" / change_id).is_dir(), sandbox
    # o sandbox nunca escreve na arvore do operador
    assert (repo / "lib" / "job.py").read_bytes() == _JOB

    (repo / "out").mkdir()
    comparacao = repo / "out" / "compare.json"
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))
    _feature_operator(repo, caso["case_id"], change_id)

    relatorio = check(repo, feature=FEATURE)
    assert _codigos(relatorio) == ([], []), relatorio
    assert relatorio["ok"] is True

    # comparacao sem nenhum check_delta nao e comparacao
    comparacao.write_bytes(json.dumps({"items": [{"id": "x", "kind": "funcval.analyzed"}]})
                           .encode("utf-8"))
    assert _codigos(check(repo, feature=FEATURE)) == (["funcval_not_comparison"], [])
    comparacao.write_bytes(json.dumps({"items": [_DELTA]}).encode("utf-8"))

    # sem o sandbox (a propria tool o apaga), o build do operador e recusado
    call_tool("sparkforge_change_sandbox", {"repo": str(repo), "clean": True})
    assert not (repo / ".sparkforge" / "sandbox" / change_id).exists()
    assert _codigos(check(repo, feature=FEATURE)) == (["change_missing"], [])


COORDENADORES = (
    "spark-performance-architect",
    "glue-incremental-performance-architect",
    "glue-infra-reviewer",
    "pyspark-code-reviewer",
)


def test_coordenadores_apontam_o_sdd():
    # as sdd-* sao nao-despachaveis (scripts/sync_skills.py::NON_DISPATCHABLE_SKILLS):
    # o coordenador as cita na prosa e fica sem elas no `skills:`
    for nome in COORDENADORES:
        texto = (ROOT / "agents" / f"{nome}.md").read_text(encoding="utf-8")
        frente, corpo = texto.split("\n---\n", 1)
        assert "sdd-" not in frente, nome
        assert "`sdd-define`" in corpo and "`sdd-build`" in corpo, nome
        assert "sparkforge sdd check" in corpo, nome
        assert "sparkforge case open" in corpo, nome
