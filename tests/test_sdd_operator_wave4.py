"""Onda 4 no perfil operator: robustez fora do caminho feliz.

Os cenarios sao os que a Onda 4 nao pode deixar sem nome: repositorio sem
`.git`, a estrutura `docs/sdd` copiada para outro repo (o que vem junto e
prova; nenhum estado escondido), a raiz `.sparkforge_aws/sdd` independente do
sandbox, runtime de teste ausente dentro de um recibo e evidencia
inconclusiva. Todos respondem com codigo nomeado -- nunca traceback.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml

from sparkforge_aws.receipt._hash import text_sha256
from sparkforge_aws.sdd.checks import check
from sparkforge_aws.sdd.converge import converge
from sparkforge_aws.sdd.load import split_frontmatter

ROOT = Path(__file__).resolve().parents[1]
RAIZ = ".sparkforge_aws/sdd"
FEATURE = "JOB_VENDAS"
_LINHA_SHA = re.compile(r"^(?P<recuo>[ \t]+)sha256: ['\"]?(?P<hex>[0-9a-f]*)['\"]?$", re.M)


def _dump(meta: dict) -> str:
    texto = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return _LINHA_SHA.sub(lambda m: f'{m["recuo"]}sha256: "{m["hex"]}"', texto)


def _grava(repo: Path, feature: str, fase: str, meta: dict, raiz: str = "docs/sdd") -> Path:
    pasta = repo / raiz / feature
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    arquivo.write_bytes(("---\n" + _dump(meta) + "---\ncorpo\n").encode("utf-8"))
    return arquivo


def _reescreve(arquivo: Path, **mudancas) -> None:
    texto = arquivo.read_bytes().decode("utf-8")
    bloco, corpo = split_frontmatter(texto)
    meta = yaml.safe_load(bloco)
    for chave, valor in mudancas.items():
        if valor is None:
            meta.pop(chave, None)
        else:
            meta[chave] = valor
    arquivo.write_bytes(("---\n" + _dump(meta) + "---\n" + corpo).encode("utf-8"))


def _upstream(repo: Path, anterior: Path) -> dict:
    return {"path": anterior.relative_to(repo).as_posix(), "sha256": text_sha256(anterior)}


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(u["code"] for u in relatorio["unresolved"]),
    )


def _repo_de_job(repo: Path) -> None:
    """Job de dados + runtime minimo, sem `.git` nenhum (o cenario base)."""
    (repo / "jobs").mkdir(parents=True, exist_ok=True)
    (repo / "jobs" / "loader.py").write_bytes(b"def main():\n    pass\n")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_job.py").write_bytes(b"def test_job():\n    assert True\n")
    (repo / ".sparkforge_aws" / "sandbox" / "S1").mkdir(parents=True, exist_ok=True)
    (repo / ".sparkforge_aws" / "case.yaml").write_bytes(b"case_id: C1\n")


def _feature_operator(repo: Path, raiz: str = "docs/sdd") -> dict[str, Path]:
    """Feature operator inteira em `ready`, com `moved` no lugar de red/green."""
    _repo_de_job(repo)
    comum = {"sdd": 1, "feature": FEATURE, "profile": "operator", "status": "ready"}
    caminhos: dict[str, Path] = {}
    caminhos["define"] = _grava(repo, FEATURE, "define", {
        **comum,
        "phase": "define",
        "case_id": "C1",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [{
            "id": "AC1",
            "statement": "o job continua verde",
            "verified_by": {"kind": "test", "ref": "tests/test_job.py::test_job"},
        }],
        "success": [],
        "out_of_scope": [],
        "change_kinds": [],
    }, raiz)
    caminhos["design"] = _grava(repo, FEATURE, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream(repo, caminhos["define"]),
        "files": [{"path": "jobs/loader.py", "action": "modify", "reason": "r"}],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "r"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    }, raiz)
    caminhos["plan"] = _grava(repo, FEATURE, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream(repo, caminhos["design"]),
        "tasks": [{
            "id": "T1",
            "files": ["jobs/loader.py"],
            "covers": ["AC1"],
            "proof": {"kind": "fact", "ref": f"{raiz}/{FEATURE}/facts.json#kind:x"},
        }],
    }, raiz)
    # os facts do job, dentro da propria raiz de evidencia
    (repo / raiz / FEATURE / "facts.json").write_bytes(
        json.dumps({"items": [{"id": "f1", "kind": "x"}]}).encode("utf-8")
    )
    caminhos["build_report"] = _grava(repo, FEATURE, "build_report", {
        **comum,
        "phase": "build_report",
        "upstream": _upstream(repo, caminhos["plan"]),
        "change_id": "S1",
        "tasks": [{"id": "T1", "status": "blocked"}],
        "claims": [{"text": "t", "evidence_ref": f"{raiz}/{FEATURE}/facts.json"}],
    }, raiz)
    caminhos["ship"] = _grava(repo, FEATURE, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream(repo, caminhos["build_report"]),
        "hypothesis_outcome": "confirmed",
        "registries": [],
        "deviations": [],
        "evidence": [{"change_id": "S1", "report_sha256": "0" * 64}],
    }, raiz)
    return caminhos


def _receipt(repo: Path, raiz: str, tests: list[dict], exit_code: int = 0) -> Path:
    out = repo / raiz / FEATURE / "run.out"
    out.write_bytes(b"saida capturada\n")
    recibo = {
        "schema": "forge/TestExecutionReceipt/v1",
        "executor": "operator",
        "command": ["spark", "--version"],
        "exit_code": exit_code,
        "baseline_sha": None,
        "baseline_reason": "sem baseline no cenario",
        "tests": tests,
        "output_path": out.relative_to(repo).as_posix(),
        "artifact_sha256": text_sha256(out),
    }
    caminho = repo / raiz / FEATURE / "receipt.json"
    caminho.write_bytes(json.dumps(recibo).encode("utf-8"))
    return caminho


def test_repo_sem_git_converge_honesto(tmp_path):
    _feature_operator(tmp_path)
    relatorio = converge(tmp_path, feature=FEATURE)
    assert relatorio["git"]["available"] is False
    # sem .git nao tem traceback nem diff inventado: o item sai pelo artefato
    assert any(i["class"] == "partial" and i["item"] == "T1" for i in relatorio["items"])


def test_estrutura_copiada_para_outro_repo(tmp_path):
    origem = tmp_path / "origem"
    origem.mkdir()
    _feature_operator(origem, raiz="docs/sdd")
    destino = tmp_path / "destino"
    shutil.copytree(origem / "docs", destino / "docs")
    shutil.copytree(origem / ".sparkforge_aws", destino / ".sparkforge_aws")
    shutil.copytree(origem / "jobs", destino / "jobs")
    shutil.copytree(origem / "tests", destino / "tests")
    recusas, lacunas = _codigos(check(destino))
    # a copia e byte a byte: os upstream carimbados seguem valendo, e nada
    # depende do caminho absoluto nem de estado fora da arvore
    assert "upstream_stale" not in recusas and "upstream_missing" not in recusas
    assert "traceback" not in json.dumps(lacunas).lower()


def test_raiz_de_evidencia_independente_do_sandbox(tmp_path):
    _feature_operator(tmp_path, raiz=RAIZ)
    # a raiz .sparkforge_aws/sdd vive DENTRO da area que o sandbox poda; o check
    # a le direto pelo --root e nao depende do sandbox para descobrir a feature
    relatorio = check(tmp_path, root=RAIZ, feature=FEATURE)
    assert relatorio["features"] == [FEATURE]
    # o sandbox S1 existe mas esta vazio: o moved nem se aplica (T1 blocked)
    recusas, _ = _codigos(relatorio)
    assert "change_missing" not in recusas


def test_runtime_ausente_no_recibo_e_inconclusivo(tmp_path):
    caminhos = _feature_operator(tmp_path)
    # exit 127 = runtime que nao existe; sem teste contado, nada de verde inventado
    _receipt(tmp_path, "docs/sdd", tests=[], exit_code=127)
    _reescreve(caminhos["build_report"], receipts=["docs/sdd/JOB_VENDAS/receipt.json"])
    recusas, lacunas = _codigos(check(tmp_path))
    assert "receipt_inconclusive" in lacunas
    assert "receipt_failed" not in recusas and "receipt_stale" not in recusas


def test_evidencia_inconclusiva_tudo_skipped(tmp_path):
    caminhos = _feature_operator(tmp_path)
    _receipt(tmp_path, "docs/sdd", tests=[
        {"name": "a", "outcome": "skipped"},
        {"name": "b", "outcome": "skipped"},
    ])
    _reescreve(caminhos["build_report"], receipts=["docs/sdd/JOB_VENDAS/receipt.json"])
    _, lacunas = _codigos(check(tmp_path))
    assert "receipt_inconclusive" in lacunas


def test_recibo_verde_valido_no_operator(tmp_path):
    caminhos = _feature_operator(tmp_path)
    _receipt(tmp_path, "docs/sdd", tests=[{"name": "t", "outcome": "passed"}])
    _reescreve(caminhos["build_report"], receipts=["docs/sdd/JOB_VENDAS/receipt.json"])
    recusas, lacunas = _codigos(check(tmp_path))
    assert "receipt_inconclusive" not in lacunas
    assert not [c for c in recusas if c.startswith("receipt_")]
