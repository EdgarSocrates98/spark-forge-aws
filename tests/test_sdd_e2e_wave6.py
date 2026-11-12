"""Onda 6 — E2E sintetico do SDD, inteiro offline.

`W6E2E` sobe a cadeia completa (explore → define → design → plan →
build_report → ship) e cada fase nova segue `ok` — depois a remocao do
recibo derruba o ship por nome, sem tocar mais nada. `W6GLUE` declara
`data_persistence` e responde o checklist de dominio no design e no plan;
remover `recovery` vira lacuna nomeada e tirar o registro do ship vira
recusa nomeada. Falha entre etapas preserva integridade: a recusa fica na
feature dela e a vizinha segue `ok`. Nada aqui toca rede, nuvem ou producao.
"""

from __future__ import annotations

import json
from pathlib import Path

from sparkforge_aws.receipt._hash import text_sha256
from sparkforge_aws.sdd import DEFAULT_ROOT
from sparkforge_aws.sdd.checks import check
from sparkforge_aws.sdd.converge import converge
from sparkforge_aws.sdd.stamp import stamp
from tests.test_sdd_wave4 import _codigos, _grava, _reescreve, _restampa

# o checklist de `data_persistence` em sparkforge_aws/sdd/change_kinds.yaml
PERSISTENCIA = (
    "atomicity", "isolation", "consistency", "idempotency", "concurrency",
    "versioning", "schema_evolution", "business_key", "reprocessing",
    "retry", "snapshot_commit_rollback", "recovery", "partial_update",
    "negative_tests", "functional_metrics",
)

FASES = ("explore", "define", "design", "plan", "build_report", "ship")


def _repo_base(repo: Path) -> None:
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "test_w6.py").write_bytes(
        b"def test_w6_ingere():\n    assert True\n\n"
        b"def test_w6_publica():\n    assert True\n"
    )
    (repo / "jobs").mkdir(exist_ok=True)
    (repo / "jobs" / "w6e2e_job.py").write_bytes(b"def main():\n    pass\n")


def _escreve(repo: Path, feature: str, fase: str, meta: dict,
             anterior: str | None = None) -> Path:
    """Grava a fase e carimba o upstream de verdade (`sdd stamp`)."""
    if anterior is not None:
        meta["upstream"] = {
            "path": f"{DEFAULT_ROOT}/{feature}/{anterior}.md",
            "sha256": "",
        }
    caminho = _grava(repo, feature, fase, meta)
    if anterior is not None:
        stamp(repo, f"{DEFAULT_ROOT}/{feature}/{fase}.md")
    return caminho


def _decisions_json(repo: Path, feature: str) -> Path:
    caminho = repo / DEFAULT_ROOT / feature / "decisions.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(json.dumps({
        "schema": "forge/DecisionTree/v1",
        "feature": feature,
        "decisions": [{
            "id": "DEC-1",
            "question": "Iceberg ou Parquet puro?",
            "type": "technical",
            "status": "decided",
            "alternatives": [
                {"id": "A", "label": "Iceberg"},
                {"id": "B", "label": "Parquet puro"},
            ],
            "answer": "A",
        }],
    }).encode("utf-8"))
    return caminho


def _recibo(repo: Path, feature: str) -> Path:
    out = repo / DEFAULT_ROOT / feature / "run.out"
    out.write_bytes(b"2 passed, 0 failed\n")
    recibo = {
        "schema": "forge/TestExecutionReceipt/v1",
        "executor": "e2e",
        "command": ["python", "-m", "pytest", "tests/test_w6.py", "-q"],
        "exit_code": 0,
        "baseline_sha": None,
        "baseline_reason": "primeira execucao da feature",
        "tests": [
            {"name": "tests/test_w6.py::test_w6_ingere", "outcome": "passed"},
            {"name": "tests/test_w6.py::test_w6_publica", "outcome": "passed"},
        ],
        "output_path": out.relative_to(repo).as_posix(),
        "artifact_sha256": text_sha256(out),
    }
    caminho = repo / DEFAULT_ROOT / feature / "receipt.json"
    caminho.write_bytes(json.dumps(recibo).encode("utf-8"))
    return caminho


def _w6e2e_fase(repo: Path, fase: str, caminhos: dict[str, Path]) -> Path:
    """Uma fase da W6E2E por chamada — a cadeia sobe sob controle do teste."""
    comum = {"sdd": 1, "feature": "W6E2E", "profile": "dev", "status": "ready"}
    if fase == "explore":
        caminhos[fase] = _escreve(repo, "W6E2E", "explore", {
            **comum, "phase": "explore",
            "approaches": [
                {"id": "A", "summary": "Glue job + tabela Iceberg"},
                {"id": "B", "summary": "EMR + Delta"},
            ],
            "chosen": "A",
            "decisions_ref": "docs/sdd/W6E2E/decisions.json",
        })
    elif fase == "define":
        caminhos[fase] = _escreve(repo, "W6E2E", "define", {
            **comum, "phase": "define",
            "hypothesis": {
                "claim": "o job Glue grava a tabela Iceberg particionada",
                "prediction": "os 2 testes do job passam",
                "experiment": "pytest tests/test_w6.py",
            },
            "acceptance": [
                {"id": "AC1", "statement": "a ingestao grava a tabela",
                 "verified_by": {"kind": "test",
                                 "ref": "tests/test_w6.py::test_w6_ingere"}},
                {"id": "AC2", "statement": "a publicacao fecha o commit",
                 "verified_by": {"kind": "test",
                                 "ref": "tests/test_w6.py::test_w6_publica"}},
            ],
            "success": [{"id": "SC1", "metric": "2 testes verdes",
                         "source": "tests/test_w6.py"}],
            "out_of_scope": ["migrar dados historicos"],
            "change_kinds": [],
            "requirements": [{
                "id": "REQ-1", "kind": "functional",
                "text": "o job escreve a tabela Iceberg particionada por data",
                "acceptance": "o teste tests/test_w6.py::test_w6_ingere passa",
                "source": "suite pytest da feature",
                "decision_refs": ["DEC-1"],
            }],
        }, anterior="explore")
    elif fase == "design":
        caminhos[fase] = _escreve(repo, "W6E2E", "design", {
            **comum, "phase": "design",
            "files": [
                {"path": "jobs/w6e2e_job.py", "action": "modify",
                 "reason": "ponto de entrada do job"},
                {"path": "jobs/w6e2e_iceberg.py", "action": "create",
                 "reason": "escrita Iceberg"},
            ],
            "decisions": [{
                "id": "D1", "choice": "Iceberg via Glue catalog",
                "rejected": ["Delta externo"],
                "rollback": "reverter o commit e derrubar a tabela staging",
            }],
            "covers": [
                {"part": "ingestao", "acceptance": ["AC1"]},
                {"part": "publicacao", "acceptance": ["AC2"]},
            ],
        }, anterior="define")
    elif fase == "plan":
        caminhos[fase] = _escreve(repo, "W6E2E", "plan", {
            **comum, "phase": "plan",
            "tasks": [
                {"id": "T1", "files": ["jobs/w6e2e_iceberg.py"],
                 "covers": ["AC1", "REQ-1"],
                 "test": {"path": "tests/test_w6.py", "name": "test_w6_ingere"}},
                {"id": "T2", "files": ["jobs/w6e2e_job.py"],
                 "covers": ["AC2"], "depends_on": ["T1"],
                 "test": {"path": "tests/test_w6.py", "name": "test_w6_publica"}},
            ],
        }, anterior="design")
    elif fase == "build_report":
        _recibo(repo, "W6E2E")
        caminhos[fase] = _escreve(repo, "W6E2E", "build_report", {
            **comum, "phase": "build_report",
            "tasks": [
                {"id": "T1", "status": "done",
                 "red": {"command": "pytest tests/test_w6.py::test_w6_ingere",
                         "exit": 1},
                 "green": {"command": "pytest tests/test_w6.py", "exit": 0}},
                {"id": "T2", "status": "done",
                 "red": {"command": "pytest tests/test_w6.py::test_w6_publica",
                         "exit": 1},
                 "green": {"command": "pytest tests/test_w6.py", "exit": 0}},
            ],
            "claims": [{"text": "tabela gravada e commit publicado",
                        "evidence_ref": "tests/test_w6.py::test_w6_ingere"}],
            "receipts": ["docs/sdd/W6E2E/receipt.json"],
        }, anterior="plan")
    elif fase == "ship":
        caminhos[fase] = _escreve(repo, "W6E2E", "ship", {
            **comum, "phase": "ship",
            "hypothesis_outcome": "confirmed",
            "registries": [],
            "deviations": [],
        }, anterior="build_report")
    return caminhos[fase]


def _w6e2e(repo: Path) -> dict[str, Path]:
    _repo_base(repo)
    _decisions_json(repo, "W6E2E")
    caminhos: dict[str, Path] = {}
    for fase in FASES:
        _w6e2e_fase(repo, fase, caminhos)
    return caminhos


def test_e2e_w6e2e_cadeia_completa_ok_por_fase(tmp_path):
    """Cada fase nova segue `ok`; remover o recibo derruba por nome, e so ele —
    os artefatos carimbados nao se movem (integridade preservada)."""
    _repo_base(tmp_path)
    _decisions_json(tmp_path, "W6E2E")
    caminhos: dict[str, Path] = {}
    for fase in FASES:
        _w6e2e_fase(tmp_path, fase, caminhos)
        relatorio = check(tmp_path, feature="W6E2E")
        assert relatorio["ok"] is True, (fase, relatorio)
    assert converge(tmp_path, feature="W6E2E")["ok"] is True

    (tmp_path / DEFAULT_ROOT / "W6E2E" / "receipt.json").unlink()
    relatorio = check(tmp_path, feature="W6E2E")
    assert relatorio["ok"] is False
    # a falha e precisamente a do recibo: nenhum upstream ou schema quebra junto
    recusas, lacunas = _codigos(relatorio)
    assert recusas == ["receipt_missing"] and lacunas == []
    itens = converge(tmp_path, feature="W6E2E")["items"]
    assert any(
        i["class"] == "missing" and i["item"] == "receipts/0"
        and i["covered_by"] == "receipt_missing" for i in itens
    )


def _w6glue(repo: Path) -> tuple[dict[str, Path], dict[str, str]]:
    _repo_base(repo)
    comum = {"sdd": 1, "feature": "W6GLUE", "profile": "dev", "status": "ready"}
    tratamento = {item: f"{item} tratado no desenho" for item in PERSISTENCIA}
    caminhos: dict[str, Path] = {}
    caminhos["define"] = _escreve(repo, "W6GLUE", "define", {
        **comum, "phase": "define",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [{"id": "AC1", "statement": "a tabela Glue grava",
                        "verified_by": {"kind": "test",
                                        "ref": "tests/test_w6.py::test_w6_ingere"}}],
        "success": [{"id": "SC1", "metric": "m", "source": "s"}],
        "out_of_scope": [],
        "change_kinds": ["data_persistence"],
    })
    caminhos["design"] = _escreve(repo, "W6GLUE", "design", {
        **comum, "phase": "design",
        "files": [{"path": "jobs/w6glue_loader.py", "action": "create",
                   "reason": "loader Glue + Iceberg"}],
        "decisions": [{"id": "D1", "choice": "c", "rollback": "r"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
        "persistence": dict(tratamento),
    }, anterior="define")
    caminhos["plan"] = _escreve(repo, "W6GLUE", "plan", {
        **comum, "phase": "plan",
        "tasks": [{"id": "T1", "files": ["jobs/w6glue_loader.py"],
                   "covers": ["AC1"],
                   "test": {"path": "tests/test_w6.py",
                            "name": "test_w6_ingere"}}],
        "persistence": dict(tratamento),
    }, anterior="design")
    caminhos["build_report"] = _escreve(repo, "W6GLUE", "build_report", {
        **comum, "phase": "build_report",
        "tasks": [{"id": "T1", "status": "done",
                   "red": {"command": "pytest tests/test_w6.py::test_w6_ingere",
                           "exit": 1},
                   "green": {"command": "pytest tests/test_w6.py", "exit": 0}}],
        "claims": [{"text": "t", "evidence_ref": "tests/test_w6.py"}],
    }, anterior="plan")
    caminhos["ship"] = _escreve(repo, "W6GLUE", "ship", {
        **comum, "phase": "ship",
        "hypothesis_outcome": "confirmed",
        "registries": ["sdd_persistence_check"],
        "deviations": [],
    }, anterior="build_report")
    return caminhos, tratamento


def test_e2e_w6glue_checklist_persistencia(tmp_path):
    """`data_persistence` exige o checklist no design e no plan: com os 15
    itens declarados nenhuma lacuna sobe; remover `recovery` vira
    `persistence_undeclared` nomeando o item, e tirar o registro do ship vira
    `registry_unchecked`."""
    caminhos, tratamento = _w6glue(tmp_path)
    relatorio = check(tmp_path, feature="W6GLUE")
    assert relatorio["ok"] is True, relatorio
    _, lacunas = _codigos(relatorio)
    assert "persistence_undeclared" not in lacunas

    # quebra 1: item do checklist some do design -> lacuna nomeada
    sem_recovery = {k: v for k, v in tratamento.items() if k != "recovery"}
    _reescreve(caminhos["design"], persistence=sem_recovery)
    _restampa(tmp_path, "W6GLUE")
    relatorio = check(tmp_path, feature="W6GLUE")
    assert relatorio["ok"] is False
    [lacuna] = [u for u in relatorio["unresolved"]
                if u["code"] == "persistence_undeclared"]
    assert "recovery" in lacuna["unlock"]

    # quebra 2: o ship nao lista o registro do kind -> recusa nomeada
    caminhos, _ = _w6glue(tmp_path / "dois")
    _reescreve(caminhos["ship"], registries=[])
    _restampa(tmp_path / "dois", "W6GLUE")
    relatorio = check(tmp_path / "dois", feature="W6GLUE")
    assert relatorio["ok"] is False
    recusas, _ = _codigos(relatorio)
    assert "registry_unchecked" in recusas


def test_e2e_falha_numa_feature_nao_contamina_a_vizinha(tmp_path):
    """Falha entre etapas preserva integridade: o recibo da W6E2E some — a
    recusa fica nela, a W6GLUE segue `ok`, e o check do repo inteiro nomeia a
    dona da falha."""
    _w6e2e(tmp_path)
    _w6glue(tmp_path)
    (tmp_path / DEFAULT_ROOT / "W6E2E" / "receipt.json").unlink()
    relatorio = check(tmp_path)
    assert relatorio["ok"] is False
    assert sorted(relatorio["features"]) == ["W6E2E", "W6GLUE"]
    assert {r["feature"] for r in relatorio["refused"]} == {"W6E2E"}
    assert any(r["code"] == "receipt_missing" for r in relatorio["refused"])
    assert check(tmp_path, feature="W6GLUE")["ok"] is True
    assert check(tmp_path, feature="W6E2E")["ok"] is False
